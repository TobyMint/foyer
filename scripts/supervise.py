#!/usr/bin/env python3
"""Lane supervisor: runs run_matrix for a set of runs, then validates each run dir
(steps recorded >= 90% of trace rows AND summary.json present). Incomplete runs —
e.g. killed by the box's periodic process-reaper — are archived and retried, up to
--passes times. Usage:
  supervise.py --lane p0x --gpu 1 --port 30001 --trace <csv> \
               --runs 'a:static=1,b:budget3:target=0.8' [--passes 3]
"""
import argparse
import json
import os
import subprocess
import sys
import time

BASE = "/data/xbw/turnstile"
NIGHT = f"{BASE}/results/night"
PY = f"{BASE}/envs/main/bin/python"
RM = f"{BASE}/TraceLab/replay/scripts/run_matrix.py"


def steps_recorded(run_dir):
    f = os.path.join(run_dir, "steps.jsonl")
    if not os.path.exists(f):
        return 0
    with open(f, "rb") as fh:
        return sum(1 for _ in fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True)
    ap.add_argument("--gpu", type=int, required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--memfrac", default="0.85")
    ap.add_argument("--timeout-h", default="12")
    ap.add_argument("--passes", type=int, default=3)
    a = ap.parse_args()

    expected = sum(1 for _ in open(a.trace))
    threshold = expected * 9 // 10
    print(f"[supervisor] trace rows={expected}, completion threshold={threshold}")

    items = [x.strip() for x in a.runs.split(",") if x.strip()]
    done, queue = {}, list(items)
    for p in range(1, a.passes + 1):
        if not queue:
            break
        print(f"[supervisor] pass {p}: {queue}")
        env = dict(os.environ,
                   TURNSTILE_RUN_TIMEOUT_H=a.timeout_h,
                   TURNSTILE_MEMFRAC=a.memfrac,
                   TURNSTILE_TRACE=a.trace)
        rc = subprocess.run([PY, RM, "--lane", a.lane, "--gpu", str(a.gpu),
                             "--port", str(a.port), "--runs", ",".join(queue)],
                            env=env).returncode
        print(f"[supervisor] run_matrix rc={rc}")
        queue = []
        for item in items:
            name = item.split(":", 1)[0]
            d = f"{NIGHT}/{name}"
            summary = os.path.join(d, "summary.json")
            ok = (os.path.exists(summary) and steps_recorded(d) >= threshold)
            done[name] = ok
            if not ok:
                print(f"[supervisor] {name} INCOMPLETE (pass {p}) — archiving")
                stamp = time.strftime("%H%M%S")
                try:
                    os.rename(d, f"{d}_incomplete_p{p}_{stamp}")
                except FileNotFoundError:
                    pass
                queue.append(item)
        print(f"[supervisor] status after pass {p}: "
              f"{ {k: ('OK' if v else 'REDO') for k, v in done.items()} }")
    still = [k for k, v in done.items() if not v]
    print(f"[supervisor] {'ALL COMPLETE' if not still else f'STILL INCOMPLETE: {still}'}")
    sys.exit(0 if not still else 1)


if __name__ == "__main__":
    main()
