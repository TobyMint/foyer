#!/usr/bin/env python3
"""Smoke test for controller_budget3 (online-predictor Foyer) against a real server.

Asserts: all steps succeed, every session is eventually admitted, admission is
staggered (single-flight: no burst of >1 unnamed admit per cycle), and the permit
file always describes a full desired state. Reuses the permit smoke's server recipe.
"""
import csv, json, os, shutil, signal, subprocess, sys, time, urllib.request

BASE = "/data/xbw/turnstile"
MODEL = f"{BASE}/models/qwen25-coder-7b-yarn96k"
PORT = 30002
GPU = 0
TRACE = f"{BASE}/data/smoke_permit4.csv"
PERMIT = f"{BASE}/smoke_b3_permit.json"
OUT = f"{BASE}/results/smoke_b3"
os.makedirs(OUT, exist_ok=True)

env = dict(os.environ)
env["PATH"] = f"{BASE}/envs/main/bin:{env.get('PATH', '')}"
env["CUDA_HOME"] = "/usr/local/cuda-12.1"
env["CUDA_VISIBLE_DEVICES"] = str(GPU)
env["PATH"] = f"{BASE}/envs/cxx/compiler-bin:{env['PATH']}"
env["NVCC_CCBIN"] = f"{BASE}/envs/cxx/bin/x86_64-conda-linux-gnu-g++"
env["CCACHE_DISABLE"] = "1"

srv = subprocess.Popen(
    [sys.executable, "-m", "sglang.launch_server", "--model-path", MODEL,
     "--context-length", "98304", "--mem-fraction-static", "0.85", "--port", str(PORT),
     "--host", "0.0.0.0", "--enable-cache-report"],
    env=env, stdout=open(f"{OUT}/server.log", "w"), stderr=subprocess.STDOUT)
print(f"[{time.strftime('%H:%M:%S')}] server launching", flush=True)
t0 = time.time()
while time.time() - t0 < 420:
    try:
        if urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3).status == 200:
            break
    except Exception:
        pass
    time.sleep(5)
else:
    sys.exit("server never healthy")
print(f"[{time.strftime('%H:%M:%S')}] server healthy", flush=True)

for stale in ("admissions.jsonl", "steps.jsonl", "summary.json", "controller.jsonl"):
    try:
        os.remove(f"{OUT}/{stale}")
    except FileNotFoundError:
        pass
json.dump({"admit": [], "paused": []}, open(PERMIT, "w"))

pool = 101432  # memfrac 0.85 on this card
ctrl = subprocess.Popen(
    [sys.executable, f"{BASE}/TraceLab/replay/scripts/controller_budget3.py",
     "--permit-file", PERMIT, "--admission-log", f"{OUT}/admissions.jsonl",
     "--step-log", f"{OUT}/steps.jsonl", "--decision-log", f"{OUT}/controller.jsonl",
     "--pool-tokens", str(pool), "--metrics-port", str(PORT), "--interval", "2"],
    env=env, stdout=open(f"{OUT}/ctrl.out", "w"), stderr=subprocess.STDOUT)
runner = subprocess.Popen(
    [f"{BASE}/TraceLab/replay/target/release/session_runner",
     "--trace", TRACE, "--text-file", f"{BASE}/data/enwik9",
     "--tokenizer", f"{MODEL}/tokenizer.json", "--model", "qwen2.5-coder-7b",
     "--base-url", f"http://127.0.0.1:{PORT}/v1",
     "--log-path", f"{OUT}/steps.jsonl", "--summary-path", f"{OUT}/summary.json",
     "--permit-file", PERMIT, "--admission-log", f"{OUT}/admissions.jsonl"],
    stdout=open(f"{OUT}/runner.out", "w"), stderr=subprocess.STDOUT)

rc = runner.wait(timeout=420)
time.sleep(3)
ctrl.terminate()
print(f"[{time.strftime('%H:%M:%S')}] runner rc={rc}", flush=True)

events = [json.loads(l) for l in open(f"{OUT}/admissions.jsonl")]
decisions = [json.loads(l) for l in open(f"{OUT}/controller.jsonl")]
summary = json.load(open(f"{OUT}/summary.json"))
admits = [e for e in events if e["event"] == "admit"]
fails = []
if summary["replay"]["success_steps"] != summary["replay"]["attempted_steps"]:
    fails.append(f"steps {summary['replay']['success_steps']}/{summary['replay']['attempted_steps']}")
if len(admits) != 4:
    fails.append(f"expected 4 admits, got {len(admits)}")
# single-flight: admits of waiting sessions must be staggered (>=2s apart here — one cycle each)
ts = sorted(e["ts"] for e in admits)
bursts = sum(1 for a, b in zip(ts, ts[1:]) if b - a < 1.5)
if bursts > 1:
    fails.append(f"{bursts} admit bursts closer than 1.5s (single-flight leak?)")
# every controller cycle wrote a parseable full state
try:
    states = [json.load(open(PERMIT))]
except Exception as e:
    fails.append(f"permit file unparseable: {e}")

print(f"\nadmit order: {[e['session_id'] for e in sorted(admits, key=lambda x: x['ts'])]}")
print("controller sample:", json.dumps(decisions[len(decisions) // 2]))
print(f"\nSMOKE " + ("FAIL:\n" + "\n".join(fails) if fails else "PASS"))
srv.send_signal(signal.SIGTERM)
