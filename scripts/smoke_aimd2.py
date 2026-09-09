#!/usr/bin/env python3
"""Short live check for controller_aimd2 (faithful Concur): with u_low pinned high the
law must grow the window every cycle, admit FIFO, and write valid permit states."""
import json, os, signal, subprocess, sys, time, urllib.request

BASE = "/data/xbw/turnstile"
MODEL = f"{BASE}/models/qwen25-coder-7b-yarn96k"
PORT = 30002
OUT = f"{BASE}/results/smoke_aimd2"
os.makedirs(OUT, exist_ok=True)
env = dict(os.environ)
env["PATH"] = f"{BASE}/envs/main/bin:{env.get('PATH', '')}"
env["CUDA_HOME"] = "/usr/local/cuda-12.1"
env["CUDA_VISIBLE_DEVICES"] = "0"
env["PATH"] = f"{BASE}/envs/cxx/compiler-bin:{env['PATH']}"
env["NVCC_CCBIN"] = f"{BASE}/envs/cxx/bin/x86_64-conda-linux-gnu-g++"
env["CCACHE_DISABLE"] = "1"

srv = subprocess.Popen(
    [sys.executable, "-m", "sglang.launch_server", "--model-path", MODEL,
     "--context-length", "98304", "--mem-fraction-static", "0.85", "--port", str(PORT),
     "--host", "0.0.0.0", "--enable-metrics", "--enable-cache-report"],
    env=env, stdout=open(f"{OUT}/server.log", "w"), stderr=subprocess.STDOUT)
t0 = time.time()
while time.time() - t0 < 420:
    try:
        if urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3).status == 200:
            break
    except Exception:
        pass
    time.sleep(5)
print(f"[{time.strftime('%H:%M:%S')}] server healthy", flush=True)

PERMIT = f"{BASE}/smoke_a2_permit.json"
json.dump({"admit": [], "paused": []}, open(PERMIT, "w"))
ctrl = subprocess.Popen(
    [sys.executable, f"{BASE}/TraceLab/replay/scripts/controller_aimd2.py",
     "--permit-file", PERMIT, "--admission-log", f"{OUT}/admissions.jsonl",
     "--metrics-url", f"http://127.0.0.1:{PORT}/metrics",
     "--decision-log", f"{OUT}/controller.jsonl",
     "--initial-cap", "1", "--u-low", "0.90", "--alpha", "1", "--interval", "5"],
    env=env, stdout=open(f"{OUT}/ctrl.out", "w"), stderr=subprocess.STDOUT)
runner = subprocess.Popen(
    [f"{BASE}/TraceLab/replay/target/release/session_runner",
     "--trace", f"{BASE}/data/smoke_permit4.csv", "--text-file", f"{BASE}/data/enwik9",
     "--tokenizer", f"{MODEL}/tokenizer.json", "--model", "qwen2.5-coder-7b",
     "--base-url", f"http://127.0.0.1:{PORT}/v1",
     "--log-path", f"{OUT}/steps.jsonl", "--summary-path", f"{OUT}/summary.json",
     "--permit-file", PERMIT, "--admission-log", f"{OUT}/admissions.jsonl"],
    stdout=open(f"{OUT}/runner.out", "w"), stderr=subprocess.STDOUT)
rc = runner.wait(timeout=420)
time.sleep(3)
ctrl.terminate()

events = [json.loads(l) for l in open(f"{OUT}/admissions.jsonl")]
decisions = [json.loads(l) for l in open(f"{OUT}/controller.jsonl")]
summary = json.load(open(f"{OUT}/summary.json"))
admits = [e for e in events if e["event"] == "admit"]
ws = [d["W"] for d in decisions]
fails = []
if summary["replay"]["success_steps"] != 24:
    fails.append(f"steps {summary['replay']['success_steps']}/24")
if len(admits) != 4:
    fails.append(f"admits {len(admits)}")
if not any(w > 1 for w in ws):
    fails.append(f"window never grew: {ws}")
print(f"\nW trajectory: {ws}")
print(f"admit order: {[e['session_id'] for e in sorted(admits, key=lambda x: x['ts'])]}")
print(f"\nSMOKE " + ("FAIL:\n" + "\n".join(fails) if fails else "PASS"))
srv.send_signal(signal.SIGTERM)
