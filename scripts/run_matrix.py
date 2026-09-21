#!/usr/bin/env python3
"""Run one lane of the admission-policy matrix: per run, restart a dedicated SGLang
server on this lane's GPU, then replay the night workload under one policy.

Usage: run_matrix.py --lane A --gpu 3 --port 30000 --runs default,cap8:static=8,aimd
Policies:
  default      no gate (all sessions admitted immediately)
  static=N     cap-file pinned to N (uniform instrumentation across gated runs)
  aimd         Concur-style cache-feedback AIMD controller sets the cap
  budget       token-budget feed-forward controller sets the cap
  budget2      v0.5: high-water floor + single-flight admission + TTFT-SLO valve
  budget3      online-predictor Foyer: named-permit admission, no trace future
  aimd2        faithful Concur: u_low-grow law, permit pause/resume (aimd2:k=v,... to tune)
"""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

BASE = "/data/xbw/turnstile"
PY = f"{BASE}/envs/main/bin/python"
RUNNER = f"{BASE}/TraceLab/replay/target/release/session_runner"
MODEL_DIR = f"{BASE}/models/qwen25-coder-7b-yarn96k"
TRACE = os.environ.get("TURNSTILE_TRACE", f"{BASE}/data/replay_night200.csv")
TEXT = f"{BASE}/data/enwik9"
OUT_ROOT = f"{BASE}/results/night"
RUN_TIMEOUT_S = int(os.environ.get("TURNSTILE_RUN_TIMEOUT_H", "6")) * 3600
MEMFRAC = os.environ.get("TURNSTILE_MEMFRAC", "0.88")
HEALTH_TIMEOUT_S = 420
# Every lane must land on the aligned KV pool; a smaller pool means another job
# held VRAM at server start (silently un-comparable results). Override the env var
# only for a deliberate different pool.
EXPECT_POOL = int(os.environ.get("TURNSTILE_EXPECT_POOL", "101432"))
# How far the pool may sit from EXPECT_POOL and still count as aligned. See the
# comment at the retry loop: the harm being guarded against is thousands of tokens,
# while SGLang cannot always land the pool on an exact value.
POOL_TOLERANCE = int(os.environ.get("TURNSTILE_POOL_TOL", "20"))
# Ceiling for the memfrac solve. 0.88 is the module default and still leaves several
# GB of headroom on a 24 GB card, so the solve can compensate for a neighbour's
# residue without the server being at risk of an allocation failure.
MAX_MEMFRAC = float(os.environ.get("TURNSTILE_MAX_MEMFRAC", "0.90"))
MAX_POOL_ATTEMPTS = 4
# Learned by the first solve in a lane and reused: the free-VRAM state that pushed
# the pool off target is a property of the card, not of the arm being run.
MEMFRAC_HINT = None


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def port_free(port):
    import socket
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def dump_meta(run_dir, meta):
    """Write metadata.json atomically-ish, and MORE THAN ONCE per run.

    It used to be written only after the runner returned. On 2026-09-18 an
    external kill took the whole lane at 03:35: aimd2_ul35 had finished all 999
    steps and written summary.json, but died in the gap before metadata — so a
    complete result lost its provenance (pool, memfrac, code hashes, controller
    params), and aimd2_paper lost 912 steps outright. Writing the config as soon
    as it is known means a kill costs the run, not the ability to say what the
    run was.
    """
    tmp = f"{run_dir}/metadata.json.tmp"
    with open(tmp, "w") as f:
        json.dump(meta, f, indent=1)
    os.replace(tmp, f"{run_dir}/metadata.json")


def _digest(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:12]
    except OSError:
        return "unknown"


def code_version():
    """Content hashes of the code that is actually about to run.

    audit-3: results from different versions may share a table when the RELEVANT
    implementation is unchanged, but that argument needs the version recorded at
    launch — a SHA written in afterwards is a guess, not evidence.

    A git SHA is not available here: the lab working copy under BASE is not a git
    working copy at all (checked 2026-09-17). Hashing the files is verifiable
    regardless of version control, and it is what makes "these two runs used the
    same controller" a checkable claim instead of a promise.
    """
    # Hash what will ACTUALLY execute, not what we assume will. The lab keeps TWO
    # copies of these scripts (BASE/scripts and BASE/TraceLab/replay/scripts) and the
    # lanes launch the latter, so hashing a fixed relative path recorded the wrong
    # file — and a fix synced into the other copy looked applied while the runs went
    # on using the old one. __file__ is this running script; the controllers are the
    # paths the dispatch chain below actually passes to Popen.
    files = [os.path.abspath(__file__),
             f"{BASE}/TraceLab/replay/scripts/controller_budget3.py",
             f"{BASE}/TraceLab/replay/scripts/controller_foyer.py",
             f"{BASE}/TraceLab/replay/scripts/controller_aimd2.py",
             f"{BASE}/TraceLab/replay/scripts/controller_aimd.py",
             f"{BASE}/TraceLab/replay/target/release/session_runner"]
    out = {}
    for p in files:
        try:
            with open(p, "rb") as f:
                out[os.path.basename(p)] = hashlib.md5(f.read()).hexdigest()[:12]
        except OSError:
            out[os.path.basename(p)] = "unknown"
    # Make the two-copy split visible instead of silently trusting one of them.
    dupes = ["run_matrix.py", "controller_budget3.py", "controller_foyer.py",
             "controller_aimd2.py"]
    out["path_divergence"] = sorted(
        d for d in dupes
        if _digest(os.path.join(BASE, "scripts", d)) !=
           _digest(os.path.join(BASE, "TraceLab/replay/scripts", d))) or "none"
    try:
        sha = subprocess.run(["git", "-C", BASE, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        sha = ""
    out["git_sha"] = sha or "unknown (BASE is not a git working copy)"
    return out


def build_config():
    """The knobs that are NOT part of the run string but change what the run means.
    TURNSTILE_HICACHE_ARGS in particular was invisible in every past result: it is
    how the host tier gets enabled, so two runs with the same policy string could
    differ in whether eviction costs a recompute or a PCIe fetch."""
    keys = ["TURNSTILE_HICACHE_ARGS", "TURNSTILE_EXPECT_POOL", "TURNSTILE_MEMFRAC",
            "TURNSTILE_RUN_TIMEOUT_H", "TURNSTILE_TRACE"]
    out = {k: os.environ.get(k, "unset") for k in keys}
    out["hicache_enabled"] = bool(os.environ.get("TURNSTILE_HICACHE_ARGS", "").strip())
    return out


# Every value route_mode() can return EXCEPT the deliberately unimplemented
# "budget3_ablation" — main() must dispatch on all of these, or a run silently
# starts an ungated runner. tests/test_run_matrix_routing.py asserts this set
# against route_mode()'s reachable outputs, so adding a route without a branch
# fails the test rather than wasting a multi-hour GPU run.
HANDLED_ROUTES = {"static", "budget2_ablation", "budget3", "foyer", "aimd2",
                  "aimd_legacy"}


def route_mode(mode):
    """Single source of truth for mode → controller routing. Unit tests call THIS
    function (not a copy of its logic) — GPT/Codex audit-2 requirement."""
    if mode == "budget3" or mode.startswith("budget3:"):
        return "budget3"
    if mode == "foyer" or mode.startswith("foyer:"):
        return "foyer"
    if mode == "aimd2" or mode.startswith("aimd2:"):
        return "aimd2"
    if mode.startswith("budget3_"):
        return "budget3_ablation"
    if mode.startswith("budget2_"):
        return "budget2_ablation"
    if mode.startswith("static=") or mode == "default":
        return "static"
    if mode == "aimd":
        return "aimd_legacy"
    return None  # unknown mode = refuse to run (never silently ungated)


def foyer_param_args(mode):
    """Parse 'foyer:k=v;k2=v2' into controller_foyer.py argv.

    `target` is the red line and `gs` is the growth-reserve scale — the two knobs
    that define the aggressiveness spectrum this controller exists to expose.
    """
    extra = []
    if ":" in mode:
        flagmap = {"target": "--target-util", "gs": "--growth-scale",
                   "margin": "--margin", "horizon": "--horizon-rounds",
                   "hw": "--highwater-decay", "hs": "--hard-stop-usage",
                   "predictor": "--predictor", "pending": "--pending-timeout-s"}
        for kv in mode.split(":", 1)[1].split(";"):
            k, v = kv.split("=", 1)
            if k == "sf" and v == "0":
                extra.append("--disable-single-flight")
            elif k == "shed" and v == "0":
                extra.append("--disable-shedding")
            elif k == "slo" and v == "0":
                extra.append("--disable-slo-valve")
            elif k == "sg" and v == "0":
                extra.append("--disable-starve-guard")
            elif k == "hw" and v == "0":
                extra.append("--disable-highwater")
            else:
                extra += [flagmap[k], v]
    return extra


def budget3_param_args(mode):
    """Parse 'budget3:k=v;k2=v2' into controller argv. Params separated by ';'
    (comma is the run separator)."""
    extra = []
    if ":" in mode:
        flagmap = {"target": "--target-util", "margin": "--margin",
                   "horizon": "--horizon-rounds", "hw": "--highwater-decay",
                   "predictor": "--predictor"}
        for kv in mode.split(":", 1)[1].split(";"):
            k, v = kv.split("=", 1)
            if k == "sf" and v == "0":
                extra.append("--disable-single-flight")
            elif k == "shed" and v == "0":
                extra.append("--disable-shedding")
            elif k == "slo" and v == "0":
                extra.append("--disable-slo-valve")
            elif k == "sg" and v == "0":
                extra.append("--disable-starve-guard")
            else:
                extra += [flagmap[k], v]
    return extra


def aimd2_param_args(mode):
    extra = []
    if ":" in mode:
        flagmap = {"alpha": "--alpha", "beta": "--beta", "interval": "--interval",
                   "u_low": "--u-low", "u_high": "--u-high",
                   "h_thresh": "--h-thresh", "initial": "--initial-cap",
                   "h_mode": "--h-mode"}
        for kv in mode.split(":", 1)[1].split(";"):
            k, v = kv.split("=", 1)
            extra += [flagmap[k], v]
    return extra


def solve_memfrac(probe, target):
    """Pick the next mem_fraction_static to try, given {memfrac: pool} so far.

    The pool is linear in mem_fraction_static (measured: 431 tokens per 0.001 on a
    3090 / 7B / 96K setup, which is exactly 0.001 * 24,576 MiB / 57,344 B per token,
    so there is no coarse quantisation to fight). Two probes therefore determine the
    line and we can solve for the target directly.
    """
    # Drop a None key rather than crashing on it. `lane_memfrac` starts as
    # MEMFRAC_HINT (None), and start_server then runs at MEMFRAC — so the caller
    # records that probe under the real memfrac (see the retry block in main). A
    # None key here would reach `None + 0.01` and die, which is what happened on
    # 2026-09-21: the pool guard fired correctly, then crashed inside its own
    # recovery path and the lane aborted with a traceback instead of a verdict.
    pts = sorted((m, p) for m, p in probe.items() if m is not None)
    if len(pts) >= 2:
        (m0, p0), (m1, p1) = pts[0], pts[-1]
        if m1 != m0 and p1 != p0:
            cur_m, cur_p = pts[-1]
            return round(cur_m + (target - cur_p) * (m1 - m0) / (p1 - p0), 6)
    if not pts:
        # Nothing usable probed: step up from the module default, which is where
        # start_server actually put the dial.
        return round(float(MEMFRAC) + 0.01, 6)
    # one point is not enough to know the slope: step up by the measured 0.01 and
    # let the next call solve properly
    return round(pts[-1][0] + 0.01, 6)


def start_server(gpu, port, run_name="server", memfrac=None):
    # Kill anything already bound to this port (stale servers poison isolation).
    # SIGTERM alone is not enough: a draining sglang can hold the port for minutes,
    # and a health check against the OLD server passes while every replay request
    # gets its connection closed. Wait for an actual successful bind, escalating
    # to SIGKILL if the old process lingers.
    subprocess.run(["pkill", "-f", f"launch_server.*--port {port}"], check=False)
    time.sleep(3)
    t0 = time.time()
    while not port_free(port):
        if time.time() - t0 > 10:
            subprocess.run(["pkill", "-9", "-f", f"launch_server.*--port {port}"], check=False)
        time.sleep(3)
        if time.time() - t0 > 90:
            raise RuntimeError(f"port {port} still occupied after 90 s")
    # Port closed != VRAM released: a predecessor's 15 GB can take tens of seconds
    # to drain, and loading into the tail of it OOMs the new server (rc=-9 via the
    # launcher's watchdog). Wait until the card is actually empty.
    t0 = time.time()
    while time.time() - t0 < 180:
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used",
                 "--format=csv,noheader,nounits", "-i", str(gpu)],
                capture_output=True, text=True, timeout=10).stdout.strip()
            if out.isdigit() and int(out) < 2000:
                break
        except Exception:
            pass
        time.sleep(5)
    env = dict(os.environ)
    env["PATH"] = f"{BASE}/envs/main/bin:{env.get('PATH','')}"
    env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    env["CUDA_HOME"] = "/usr/local/cuda-12.1"
    env["PATH"] = f"{BASE}/envs/cxx/compiler-bin:{env['PATH']}"
    env["NVCC_CCBIN"] = f"{BASE}/envs/cxx/bin/x86_64-conda-linux-gnu-g++"
    env["CCACHE_DISABLE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [sys.executable, "-m", "sglang.launch_server",
           "--model-path", MODEL_DIR, "--context-length", "98304",
           "--mem-fraction-static", str(memfrac if memfrac is not None else MEMFRAC),
           "--port", str(port),
           "--host", "0.0.0.0", "--enable-metrics", "--enable-cache-report"]
    # optional hierarchical-cache (host tier) args, e.g.
    # TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2"
    cmd += os.environ.get("TURNSTILE_HICACHE_ARGS", "").split()
    proc = subprocess.Popen(cmd, env=env, stdout=open(f"{OUT_ROOT}/server_{port}_{run_name}.log", "w"),
                            stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/health"
    t0 = time.time()
    while time.time() - t0 < HEALTH_TIMEOUT_S:
        if proc.poll() is not None:
            raise RuntimeError(f"server on port {port} exited during startup (rc={proc.returncode})")
        try:
            if urllib.request.urlopen(url, timeout=3).status == 200:
                # Health can pass while the engine is still fragile; send one real
                # warm-up completion so a half-dead server fails HERE, not mid-run.
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/v1/completions",
                    data=json.dumps({"model": "x", "prompt": "warmup",
                                     "max_tokens": 1, "temperature": 0}).encode(),
                    headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=120)
                return proc
        except Exception:
            pass
        time.sleep(5)
    proc.terminate()
    raise RuntimeError(f"server on port {port} failed to become healthy")


def get_pool_tokens(port):
    for path in ("/server_info", "/get_server_info"):
        try:
            d = json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:{port}{path}", timeout=5).read().decode())
            for key in ("max_total_num_tokens",):
                if key in d:
                    return int(d[key])
        except Exception:
            pass
    raise RuntimeError("cannot read max_total_num_tokens from server info")


def wait_port_dead(proc, port):
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=60)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    time.sleep(3)


def parse_runs(spec):
    runs = []
    for item in spec.split(","):
        if ":" in item:
            name, mode = item.split(":", 1)
        else:
            name, mode = item, item
        runs.append((name.strip(), mode.strip()))
    return runs


def main():
    global MEMFRAC_HINT
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True)
    ap.add_argument("--gpu", type=int, required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--runs", required=True, help="e.g. default,cap8:static=8,aimd")
    args = ap.parse_args()

    os.makedirs(OUT_ROOT, exist_ok=True)
    trace_md5 = hashlib.md5(open(TRACE, "rb").read()).hexdigest()[:10]
    runs = parse_runs(args.runs)
    for name, mode in runs:
        r = route_mode(mode)
        if r is None:
            # audit-2: unknown modes must fail loudly — a silent fall-through means
            # an ungated runner (the t85/t90 incident)
            raise SystemExit(f"unknown policy mode {mode!r} (run {name!r}) — refusing to start")
        if r not in HANDLED_ROUTES:
            # Defense in depth, and the hole audit-3 found: route_mode can produce a
            # name that the dispatch chain below has no branch for ("budget3_…" →
            # "budget3_ablation"). That is not None, so the check above passes, no
            # branch matches, cap_args stays [] and the runner starts UNGATED.
            # Checking the route (not the mode string) is what closes it: any new
            # route_mode return value that nobody dispatches on now refuses to run.
            raise SystemExit(
                f"mode {mode!r} (run {name!r}) routes to {r!r}, which has no dispatch "
                f"branch in main() — refusing to start an ungated runner")
    log(f"lane {args.lane} gpu {args.gpu} port {args.port} runs {runs}")

    for name, mode in runs:
        run_dir = f"{OUT_ROOT}/{name}"
        os.makedirs(run_dir, exist_ok=True)
        # A lane that aborts part-way (pool guard) is retried wholesale by the queue
        # driver. Without this, the retry re-runs the arms that already succeeded —
        # hours of GPU per cycle. Only a real summary counts; an empty run dir left
        # by a guard abort must NOT look finished.
        if os.path.exists(f"{run_dir}/summary.json"):
            log(f"run {name} already has a summary — skipping")
            continue
        meta = {"lane": args.lane, "policy": mode, "trace": TRACE, "trace_md5": trace_md5,
                "gpu": args.gpu, "port": args.port, "started": time.time(),
                "code": code_version(), "build": build_config()}
        log(f"=== run {name} (policy {mode}) ===")

        # KV pool must match the intended size: SGLang sizes the pool from whatever
        # VRAM is free at startup, so a neighbour's job on the same card silently
        # halves it (caught 09-15: pool 48,234 vs 101,432 on a 200-tier run, which
        # faked a quality regression; 84,528 on another). Restart until the pool is
        # right; abort the lane rather than record a run we cannot compare.
        attempt, pool_tokens = 1, None
        probe = {}
        lane_memfrac = MEMFRAC_HINT
        while True:
            server = start_server(args.gpu, args.port, name, lane_memfrac)
            pool_tokens = get_pool_tokens(args.port)
            # Tolerance, not equality. The guard exists because mixing KV pool sizes
            # makes runs incomparable, and that was earned — pools of 48,234 / 84,528 /
            # 97,367 against the aligned 101,432 invalidated 7 runs. But incomparable
            # is a matter of magnitude, not of one token: the admission budget is
            # rho * pool, so a token moves it by 0.75 tokens while the contamination
            # moved it by thousands. SGLang derives the pool from free VRAM, so an
            # exact hit is not always reachable (0.85937 gives 101,433 where 0.85
            # gives 101,432); demanding equality would abort on a residue that cannot
            # change a single conclusion.
            if not EXPECT_POOL or abs(pool_tokens - EXPECT_POOL) <= POOL_TOLERANCE:
                break
            log(f"POOL MISMATCH: got {pool_tokens}, expected {EXPECT_POOL} "
                f"(±{POOL_TOLERANCE}) at memfrac={lane_memfrac} (attempt {attempt})")
            wait_port_dead(server, args.port)
            if attempt >= MAX_POOL_ATTEMPTS:
                raise SystemExit(
                    f"pool size {pool_tokens} != expected {EXPECT_POOL} after "
                    f"{attempt} attempts (another job is holding VRAM on gpu "
                    f"{args.gpu}) — aborting lane instead of recording a bad run")
            # A neighbour's residue shrinks the pool; raise memfrac to compensate
            # instead of aborting. The pool stays the invariant, memfrac is only the
            # dial that reaches it, so the experiment is unchanged.
            # Record the dial the server ACTUALLY ran at. On the first probe
            # lane_memfrac is still MEMFRAC_HINT (None) and start_server falls back
            # to MEMFRAC, so keying on the None would both lose the slope the solver
            # needs and hand solve_memfrac a None to do arithmetic on. float() is
            # load-bearing: MEMFRAC comes from os.environ and is a STRING.
            probe[lane_memfrac if lane_memfrac is not None else float(MEMFRAC)] = pool_tokens
            lane_memfrac = min(solve_memfrac(probe, EXPECT_POOL), MAX_MEMFRAC)
            log(f"  -> retrying at memfrac={lane_memfrac}")
            attempt += 1
            time.sleep(30)
        MEMFRAC_HINT = lane_memfrac
        meta["pool_tokens"] = pool_tokens
        meta["pool_attempts"] = attempt
        # The dial that reached the pool, not the pool itself: a lane that had to
        # compensate for a neighbour's residue will differ from the nominal 0.85,
        # and a reviewer comparing two runs needs to see that it was the memory
        # fraction that moved, never the aligned token count.
        meta["memfrac_used"] = lane_memfrac
        # write as soon as the run's configuration is settled: a kill from here on
        # costs the result but not the record of what the run was
        dump_meta(run_dir, meta)
        log(f"server healthy, pool={pool_tokens}" + (f" (attempt {attempt})" if attempt > 1 else ""))

        monitor = subprocess.Popen(
            [PY, f"{BASE}/TraceLab/replay/scripts/monitor.py",
             "--url", f"http://127.0.0.1:{args.port}/metrics",
             "--out", f"{run_dir}/metrics.csv", "--interval", "5"])

        cap_args = []
        controller = None
        capfile = f"{BASE}/cap_{args.lane}"
        if mode.startswith("static="):
            n = int(mode.split("=", 1)[1])
            with open(capfile, "w") as f:
                f.write(str(n))
            cap_args = ["--cap-file", capfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["cap"] = n
        elif mode == "aimd":
            controller = subprocess.Popen(
                [PY, f"{BASE}/TraceLab/replay/scripts/controller_aimd.py",
                 "--cap-file", capfile, "--metrics-url", f"http://127.0.0.1:{args.port}/metrics",
                 "--decision-log", f"{run_dir}/controller.jsonl", "--interval", "30"],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cap_args = ["--cap-file", capfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["controller_params"] = {"u_low": 0.35, "u_high": 0.75, "h_thresh": 0.03,
                                         "alpha": 2.0, "beta": 0.5, "initial": 2}
        elif mode == "budget":
            controller = subprocess.Popen(
                [PY, f"{BASE}/TraceLab/replay/scripts/controller_budget.py",
                 "--cap-file", capfile, "--step-log", f"{run_dir}/steps.jsonl",
                 "--admission-log", f"{run_dir}/admissions.jsonl", "--trace", TRACE,
                 "--decision-log", f"{run_dir}/controller.jsonl", "--pool-tokens", str(pool_tokens),
                 "--metrics-port", str(args.port)],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cap_args = ["--cap-file", capfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["controller_params"] = {"target_util": 0.75, "margin": 1.15,
                                         "starve_seconds": 180.0}
        elif mode == "budget2":
            controller = subprocess.Popen(
                [PY, f"{BASE}/TraceLab/replay/scripts/controller_budget2.py",
                 "--cap-file", capfile, "--step-log", f"{run_dir}/steps.jsonl",
                 "--admission-log", f"{run_dir}/admissions.jsonl", "--trace", TRACE,
                 "--decision-log", f"{run_dir}/controller.jsonl", "--pool-tokens", str(pool_tokens),
                 "--metrics-port", str(args.port)],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cap_args = ["--cap-file", capfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["controller_params"] = {"target_util": 0.75, "margin": 1.15,
                                         "hard_stop": 0.85, "highwater_decay": 0.995,
                                         "slo_ms": 10000, "starve_seconds": 240.0,
                                         "starve_cooldown": 300.0}
        elif mode.startswith("budget2_"):
            # Ablations: one removed component per mode (paper ablation table).
            flagmap = {"budget2_nohw": "--disable-highwater",       # dip leak back
                       "budget2_nosf": "--disable-single-flight",   # stampedes back
                       "budget2_nosv": "--disable-slo-valve"}       # no quality freeze
            controller = subprocess.Popen(
                [PY, f"{BASE}/TraceLab/replay/scripts/controller_budget2.py",
                 flagmap[mode],
                 "--cap-file", capfile, "--step-log", f"{run_dir}/steps.jsonl",
                 "--admission-log", f"{run_dir}/admissions.jsonl", "--trace", TRACE,
                 "--decision-log", f"{run_dir}/controller.jsonl", "--pool-tokens", str(pool_tokens),
                 "--metrics-port", str(args.port)],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cap_args = ["--cap-file", capfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["controller_params"] = {"ablation": mode}
        elif route_mode(mode) == "budget3":
            # Online-predictor Foyer: named-permit admission, no trace future.
            # Routing via route_mode() — GPT-audit-2: `== "budget3"` left param
            # variants ungated.
            permitfile = f"{BASE}/permit_{args.lane}.json"
            with open(permitfile, "w") as f:
                json.dump({"admit": [], "paused": []}, f)
            # Supervised: log-driven state → a dead controller is relaunched in
            # 20 s and resumes seamlessly, until the run's summary exists.
            ctrl_cmd = " ".join([
                PY, f"{BASE}/TraceLab/replay/scripts/controller_budget3.py",
                *budget3_param_args(mode),
                "--trace", TRACE,
                "--permit-file", permitfile,
                "--step-log", f"{run_dir}/steps.jsonl",
                "--admission-log", f"{run_dir}/admissions.jsonl",
                "--decision-log", f"{run_dir}/controller.jsonl",
                "--pool-tokens", str(pool_tokens),
                "--metrics-port", str(args.port),
                "--max-minutes", "600"])
            supervisor = (
                f'while [ ! -f {run_dir}/summary.json ]; do '
                f'{ctrl_cmd} >> {run_dir}/ctrl.out 2>&1; '
                f'echo "$(date +%H:%M:%S) controller exited, relaunching" >> {run_dir}/ctrl.out; '
                f'sleep 20; done')
            controller = subprocess.Popen(["bash", "-c", supervisor],
                                          start_new_session=True)
            cap_args = ["--permit-file", permitfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["controller_params"] = {"target_util": 0.75, "margin": 1.15,
                                         "horizon_rounds": 3, "highwater_decay": 0.995,
                                         "slo_ms": 10000,
                                         "tuned": (mode.split(":", 1)[1] if ":" in mode else "default")}
        elif route_mode(mode) == "foyer":
            # Foyer: the KV pool as a guardrail rather than the objective. The base
            # of the accounting is the engine's measured token_usage, so prefix
            # sharing counts in our favour instead of being discarded by a
            # max(measured, logical_sum); --target-util is the red line.
            permitfile = f"{BASE}/permit_{args.lane}.json"
            with open(permitfile, "w") as f:
                json.dump({"admit": [], "paused": []}, f)
            ctrl_cmd = " ".join([
                PY, f"{BASE}/TraceLab/replay/scripts/controller_foyer.py",
                *foyer_param_args(mode),
                "--trace", TRACE,
                "--permit-file", permitfile,
                "--step-log", f"{run_dir}/steps.jsonl",
                "--admission-log", f"{run_dir}/admissions.jsonl",
                "--decision-log", f"{run_dir}/controller.jsonl",
                "--pool-tokens", str(pool_tokens),
                "--metrics-port", str(args.port),
                "--max-minutes", "600"])
            supervisor = (
                f'while [ ! -f {run_dir}/summary.json ]; do '
                f'{ctrl_cmd} >> {run_dir}/ctrl.out 2>&1; '
                f'echo "$(date +%H:%M:%S) controller exited, relaunching" >> {run_dir}/ctrl.out; '
                f'sleep 20; done')
            controller = subprocess.Popen(["bash", "-c", supervisor],
                                          start_new_session=True)
            cap_args = ["--permit-file", permitfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["controller_params"] = {
                "target_util": 0.90, "growth_scale": 0.35, "margin": 1.0,
                "horizon_rounds": 3, "highwater_decay": 0.98,
                "hard_stop_usage": 0.93, "slo_ms": 10000,
                "tuned": (mode.split(":", 1)[1] if ":" in mode else "default")}
        elif route_mode(mode) == "aimd2":
            # Faithful Concur: grow only below u_low, permit-based pause/resume.
            permitfile = f"{BASE}/permit_{args.lane}.json"
            with open(permitfile, "w") as f:
                json.dump({"admit": [], "paused": []}, f)
            controller = subprocess.Popen(
                [PY, f"{BASE}/TraceLab/replay/scripts/controller_aimd2.py",
                 "--permit-file", permitfile,
                 "--admission-log", f"{run_dir}/admissions.jsonl",
                 "--metrics-url", f"http://127.0.0.1:{args.port}/metrics",
                 "--decision-log", f"{run_dir}/controller.jsonl"] + aimd2_param_args(mode),
                 stdout=open(f"{run_dir}/ctrl.out", "w"), stderr=subprocess.STDOUT)
            cap_args = ["--permit-file", permitfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            # Record the params the controller ACTUALLY ran with: the defaults are
            # Concur-retuned-for-3090, but "aimd2:u_low=..." overrides them, and a
            # hardcoded dict here would mislabel those runs in provenance.
            prm = {"u_low": 0.35, "u_high": 0.75, "h_thresh": 0.03,
                   "alpha": 2.0, "beta": 0.5, "interval": 30.0}
            if ":" in mode:
                for kv in mode.split(":", 1)[1].split(";"):
                    k, v = kv.split("=", 1)
                    if k in prm:
                        prm[k] = float(v)
                    elif k == "h_mode":
                        prm[k] = v
            meta["controller_params"] = {"law": "u_low grow / thrash cut / pause-resume", **prm}

        cmd = [RUNNER, "--trace", TRACE, "--text-file", TEXT,
               "--tokenizer", f"{MODEL_DIR}/tokenizer.json", "--model", "qwen2.5-coder-7b",
               "--base-url", f"http://127.0.0.1:{args.port}/v1",
               "--log-path", f"{run_dir}/steps.jsonl",
               "--summary-path", f"{run_dir}/summary.json"] + cap_args
        if mode == "default":
            cmd += ["--admission-log", f"{run_dir}/admissions.jsonl"]
        # The gating flags (--cap-file / --permit-file) live only in this argv: it is
        # the artefact that proves the run was actually gated rather than merely
        # labelled as such. audit-3 asked for exactly this.
        meta["runner_argv"] = cmd
        log("runner:", " ".join(cmd))

        t0 = time.time()
        try:
            runner = subprocess.Popen(cmd, stdout=open(f"{run_dir}/runner.out", "w"),
                                      stderr=subprocess.STDOUT)
            runner.wait(timeout=RUN_TIMEOUT_S)
            meta["runner_rc"] = runner.returncode
        except subprocess.TimeoutExpired:
            runner.kill()
            meta["runner_rc"] = "TIMEOUT"
            log("runner TIMEOUT after 4h")
        meta["wall_s"] = round(time.time() - t0, 1)

        if controller:
            try:  # supervised controllers lead their own process group
                os.killpg(os.getpgid(controller.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                controller.terminate()
        monitor.terminate()
        wait_port_dead(server, args.port)
        meta["finished"] = time.time()
        dump_meta(run_dir, meta)
        log(f"run {name} done rc={meta['runner_rc']} wall={meta['wall_s']}s")

    with open(f"{OUT_ROOT}/lane_{args.lane}_DONE", "w") as f:
        f.write("done\n")
    log("lane complete")


if __name__ == "__main__":
    main()
