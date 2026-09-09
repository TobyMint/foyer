#!/usr/bin/env python3
"""End-to-end smoke test for --permit-file admission (P0 named-permit redesign).

Verifies, against a real SGLang on an idle GPU:
  1. named admission: only sessions named in admit[] ever enter
  2. step-boundary pause: a paused session releases its slot AFTER its current round
  3. resume: a re-admitted paused session continues (event "resume")
  4. admit/resume events carry prompt_tokens (arrival payload size)
"""
import csv, json, os, signal, subprocess, sys, time, urllib.request

BASE = "/data/xbw/turnstile"
MODEL = f"{BASE}/models/qwen25-coder-7b-yarn96k"
PORT = 30002
GPU = 0
TRACE = f"{BASE}/data/smoke_permit4.csv"
PERMIT = f"{BASE}/smoke_permit.json"
OUT = f"{BASE}/results/smoke_permit"
os.makedirs(OUT, exist_ok=True)

# --- 4 sessions x 6 rounds, tiny; tool_wait 3s keeps sessions alive long enough to pause
with open(TRACE, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["session_id", "round_idx", "prefix_len", "input_len", "output_len", "tool_wait_after_ms", "arrival_time_ms"])
    for s in range(1, 5):
        for r in range(6):
            w.writerow([f"s{s}", r, r * 100, 100, 50, 3000, 0])


def write_permit(admit, paused):
    tmp = PERMIT + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"admit": admit, "paused": paused}, f)
    os.replace(tmp, PERMIT)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --- start server (same env recipe as run_matrix)
env = dict(os.environ)
env["PATH"] = f"{BASE}/envs/main/bin:{env.get('PATH', '')}"
env["CUDA_HOME"] = "/usr/local/cuda-12.1"
env["CUDA_VISIBLE_DEVICES"] = str(GPU)
env["PATH"] = f"{BASE}/envs/cxx/compiler-bin:{env['PATH']}"
env["NVCC_CCBIN"] = f"{BASE}/envs/cxx/bin/x86_64-conda-linux-gnu-g++"
env["CCACHE_DISABLE"] = "1"
srv_log = open(f"{OUT}/server.log", "w")
srv = subprocess.Popen(
    [sys.executable, "-m", "sglang.launch_server", "--model-path", MODEL,
     "--context-length", "98304", "--mem-fraction-static", "0.85", "--port", str(PORT),
     "--host", "0.0.0.0", "--enable-cache-report"],
    env=env, stdout=srv_log, stderr=subprocess.STDOUT)
log("server launching on gpu0")
t0 = time.time()
while time.time() - t0 < 420:
    if srv.poll() is not None:
        sys.exit("server died at startup")
    try:
        if urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3).status == 200:
            break
    except Exception:
        pass
    time.sleep(5)
else:
    sys.exit("server never became healthy")
log("server healthy")

# --- permit timeline + runner
write_permit(["s1"], [])
runner = subprocess.Popen(
    [f"{BASE}/TraceLab/replay/target/release/session_runner",
     "--trace", TRACE, "--text-file", f"{BASE}/data/enwik9",
     "--tokenizer", f"{MODEL}/tokenizer.json", "--model", "qwen2.5-coder-7b",
     "--base-url", f"http://127.0.0.1:{PORT}/v1",
     "--log-path", f"{OUT}/steps.jsonl", "--summary-path", f"{OUT}/summary.json",
     "--permit-file", PERMIT, "--admission-log", f"{OUT}/admissions.jsonl"],
    stdout=open(f"{OUT}/runner.out", "w"), stderr=subprocess.STDOUT)

updates = []


def update(admit, paused):
    write_permit(admit, paused)
    updates.append((time.time(), list(admit), list(paused)))
    log(f"permit -> admit={admit} paused={paused}")


T0 = time.time()
time.sleep(10)   # s1 running solo
update(["s2", "s3"], ["s1"])   # pause s1 at its next step boundary
time.sleep(8)
update(["s1", "s2", "s3", "s4"], [])  # resume everyone

rc = runner.wait(timeout=300)
log(f"runner rc={rc}")

events = [json.loads(l) for l in open(f"{OUT}/admissions.jsonl")]
fails = []
# 1. named admission: s2/s3/s4 must not admit before the first update naming them
first_update_ts = updates[0][0] if updates else float("inf")
early = [e for e in events if e["session_id"] in ("s2", "s3", "s4")
         and e["event"] == "admit" and e["ts"] < first_update_ts]
if early:
    fails.append(f"premature admits before being named: {early}")
# 2. exactly one pause for s1, followed by a resume
pauses = [e for e in events if e["event"] == "pause"]
resumes = [e for e in events if e["event"] == "resume"]
if len(pauses) != 1:
    fails.append(f"expected 1 pause event, got {len(pauses)}")
if len(resumes) != 1:
    fails.append(f"expected 1 resume event, got {len(resumes)}")
# 3. prompt_tokens on s1's first admit
s1_admit = [e for e in events if e["session_id"] == "s1" and e["event"] == "admit"]
if not s1_admit or s1_admit[0].get("prompt_tokens") != 100:
    fails.append(f"s1 first admit missing prompt_tokens=100: {s1_admit[:1]}")
# 4. all steps succeeded
summary = json.load(open(f"{OUT}/summary.json"))
ok = summary["replay"]["success_steps"]
total = summary["replay"]["attempted_steps"]
if ok != total:
    fails.append(f"steps {ok}/{total} succeeded")
# 5. pause happened AFTER a round completed (steps of s1 exist before pause ts)
if pauses:
    s1_steps = [json.loads(l) for l in open(f"{OUT}/steps.jsonl")
                if json.loads(l).get("session_id") == "s1"]
    pre = [s for s in s1_steps if s.get("complete_timestamp", 0) < pauses[0]["ts"]]
    if not pre:
        fails.append("no s1 round completed before pause")

print("\n=== admission events ===")
for e in events:
    print(e)
print(f"\nsteps ok/total: {ok}/{total}")
print("\nSMOKE " + ("FAIL:\n" + "\n".join(fails) if fails else "PASS"))
srv.send_signal(signal.SIGTERM)
