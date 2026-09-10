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
RUN_TIMEOUT_S = 6 * 3600
MEMFRAC = os.environ.get("TURNSTILE_MEMFRAC", "0.88")
HEALTH_TIMEOUT_S = 420


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


def start_server(gpu, port, run_name="server"):
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
           "--mem-fraction-static", MEMFRAC, "--port", str(port),
           "--host", "0.0.0.0", "--enable-metrics", "--enable-cache-report"]
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True)
    ap.add_argument("--gpu", type=int, required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--runs", required=True, help="e.g. default,cap8:static=8,aimd")
    args = ap.parse_args()

    os.makedirs(OUT_ROOT, exist_ok=True)
    trace_md5 = hashlib.md5(open(TRACE, "rb").read()).hexdigest()[:10]
    runs = parse_runs(args.runs)
    log(f"lane {args.lane} gpu {args.gpu} port {args.port} runs {runs}")

    for name, mode in runs:
        run_dir = f"{OUT_ROOT}/{name}"
        os.makedirs(run_dir, exist_ok=True)
        meta = {"lane": args.lane, "policy": mode, "trace": TRACE, "trace_md5": trace_md5,
                "gpu": args.gpu, "port": args.port, "started": time.time()}
        log(f"=== run {name} (policy {mode}) ===")

        server = start_server(args.gpu, args.port, name)
        pool_tokens = get_pool_tokens(args.port)
        meta["pool_tokens"] = pool_tokens
        log(f"server healthy, pool={pool_tokens}")

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
        elif mode == "budget3":
            # Online-predictor Foyer: named-permit admission, no trace future.
            permitfile = f"{BASE}/permit_{args.lane}.json"
            with open(permitfile, "w") as f:
                json.dump({"admit": [], "paused": []}, f)
            controller = subprocess.Popen(
                [PY, f"{BASE}/TraceLab/replay/scripts/controller_budget3.py",
                 "--permit-file", permitfile,
                 "--step-log", f"{run_dir}/steps.jsonl",
                 "--admission-log", f"{run_dir}/admissions.jsonl",
                 "--decision-log", f"{run_dir}/controller.jsonl", "--pool-tokens", str(pool_tokens),
                 "--metrics-port", str(args.port)],
                 stdout=open(f"{run_dir}/ctrl.out", "w"), stderr=subprocess.STDOUT)
            cap_args = ["--permit-file", permitfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["controller_params"] = {"target_util": 0.75, "margin": 1.15,
                                         "horizon_rounds": 3, "highwater_decay": 0.995,
                                         "slo_ms": 10000}
        elif mode.startswith("aimd2"):
            # Faithful Concur: grow only below u_low, permit-based pause/resume.
            permitfile = f"{BASE}/permit_{args.lane}.json"
            with open(permitfile, "w") as f:
                json.dump({"admit": [], "paused": []}, f)
            extra = []
            if ":" in mode:  # e.g. aimd2:alpha=4,interval=2
                flagmap = {"alpha": "--alpha", "beta": "--beta", "interval": "--interval",
                           "u_low": "--u-low", "u_high": "--u-high",
                           "h_thresh": "--h-thresh", "initial": "--initial-cap"}
                for kv in mode.split(":", 1)[1].split(","):
                    k, v = kv.split("=", 1)
                    extra += [flagmap[k], v]
            controller = subprocess.Popen(
                [PY, f"{BASE}/TraceLab/replay/scripts/controller_aimd2.py",
                 "--permit-file", permitfile,
                 "--admission-log", f"{run_dir}/admissions.jsonl",
                 "--metrics-url", f"http://127.0.0.1:{args.port}/metrics",
                 "--decision-log", f"{run_dir}/controller.jsonl"] + extra,
                 stdout=open(f"{run_dir}/ctrl.out", "w"), stderr=subprocess.STDOUT)
            cap_args = ["--permit-file", permitfile, "--admission-log", f"{run_dir}/admissions.jsonl"]
            meta["controller_params"] = {"law": "u_low grow / thrash cut / pause-resume",
                                         "u_low": 0.35, "u_high": 0.75, "h_thresh": 0.03,
                                         "alpha": 2.0, "beta": 0.5, "interval": 30.0}

        cmd = [RUNNER, "--trace", TRACE, "--text-file", TEXT,
               "--tokenizer", f"{MODEL_DIR}/tokenizer.json", "--model", "qwen2.5-coder-7b",
               "--base-url", f"http://127.0.0.1:{args.port}/v1",
               "--log-path", f"{run_dir}/steps.jsonl",
               "--summary-path", f"{run_dir}/summary.json"] + cap_args
        if mode == "default":
            cmd += ["--admission-log", f"{run_dir}/admissions.jsonl"]
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
            controller.terminate()
        monitor.terminate()
        wait_port_dead(server, args.port)
        meta["finished"] = time.time()
        with open(f"{run_dir}/metadata.json", "w") as f:
            json.dump(meta, f, indent=1)
        log(f"run {name} done rc={meta['runner_rc']} wall={meta['wall_s']}s")

    with open(f"{OUT_ROOT}/lane_{args.lane}_DONE", "w") as f:
        f.write("done\n")
    log("lane complete")


if __name__ == "__main__":
    main()
