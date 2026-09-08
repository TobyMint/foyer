#!/usr/bin/env python3
"""Wait for lane A to finish its night runs, then run the graded-load matrix
(50-session subset) on the freed GPU3: default vs cap8 vs budget at moderate load.

Hypothesis: at moderate load (system not fundamentally oversubscribed), gated
policies dominate default — no thrash, short queues, far fewer failures.
"""
import os
import subprocess
import time

BASE = "/data/xbw/turnstile"
PY = f"{BASE}/envs/main/bin/python"
DONE = f"{BASE}/results/night/lane_A_DONE"
LOG = f"{BASE}/logs/graded.log"

while not os.path.exists(DONE):
    time.sleep(60)

with open(LOG, "a") as f:
    f.write(f"[{time.strftime('%H:%M:%S')}] lane A done, launching graded 50-session matrix\n")

env = dict(os.environ)
env["TURNSTILE_TRACE"] = f"{BASE}/data/replay_night50.csv"
subprocess.run([PY, f"{BASE}/TraceLab/replay/scripts/run_matrix.py",
                "--lane", "graded50", "--gpu", "3", "--port", "30000",
                "--runs", "load50_default:default,load50_cap8:static=8,load50_budget:budget"],
               env=env)
with open(LOG, "a") as f:
    f.write(f"[{time.strftime('%H:%M:%S')}] graded matrix complete\n")
