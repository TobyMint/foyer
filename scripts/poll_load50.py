#!/usr/bin/env python3
"""Poll for a fully-free GPU on lab-3090; when one appears, launch the load50
graded tier on it. Exits after launching (one-shot)."""
import subprocess
import time
import urllib.request

BASE = "/data/xbw/turnstile"
PY = f"{BASE}/envs/main/bin/python"
LOG = f"{BASE}/logs/poll_load50.log"


def log(msg):
    line = f"[{time.strftime('%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def gpu_free_mib():
    out = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used",
                          "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    free = []
    for line in out.strip().splitlines():
        idx, used = [x.strip() for x in line.split(",")]
        if int(used) < 2000:  # essentially empty card
            free.append(int(idx))
    return free


def main():
    log("poller armed: waiting for a GPU with <2 GiB used")
    prev_free = []
    while True:
        free = gpu_free_mib()
        # Sustained-free check: the card must be empty in two consecutive polls
        # (10 min apart). A <2 GB snapshot alone is not enough — 800 MB stragglers
        # landing after launch OOM the server at CUDA-graph capture.
        if free and set(free) & set(prev_free):
            gpu = free[0]
            log(f"GPU{gpu} sustained-free across two polls; launching load50 tier")
            env = dict(os.environ)
            env["TURNSTILE_TRACE"] = f"{BASE}/data/replay_night50.csv"
            env["TURNSTILE_MEMFRAC"] = "0.85"
            subprocess.run([PY, f"{BASE}/TraceLab/replay/scripts/run_matrix.py",
                            "--lane", "graded50", "--gpu", str(gpu), "--port", "30000",
                            "--runs", "load50_default:default,load50_cap6:static=6,load50_budget:budget"],
                           env=env)
            log("load50 tier finished")
            return
        prev_free = free
        time.sleep(300)


if __name__ == "__main__":
    import os
    main()
