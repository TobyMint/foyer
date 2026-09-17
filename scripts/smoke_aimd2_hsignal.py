#!/usr/bin/env python3
"""Signal-level smoke test for controller_aimd2's H gate. No GPU, no engine.

audit-3 asked for three things to be shown before spending GPU time on the Concur
reruns: that a valid low hit rate and a valid high hit rate are both observable,
that under high usage the H condition can both BLOCK and TRIGGER a cut, and that
"no samples" is not silently treated as zero hit rate.

The controller is driven against a scripted /metrics endpoint, so each assertion is
about the control law alone — not about what SGLang happened to report that day.

Run: python3 scripts/smoke_aimd2_hsignal.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
CTRL = os.path.join(HERE, "controller_aimd2.py")
PY = sys.executable

U_LOW, U_HIGH, H_THRESH = 0.2, 0.5, 0.2


class Metrics:
    """Scripted cumulative counters, advanced on a WALL-CLOCK step.

    Not per scrape: the controller hits /metrics twice per control tick (once for
    the high-water floor via engine_metrics(), once for the control law), so
    advancing per request consumed the whole script inside one tick and every later
    tick saw frozen counters — which is indistinguishable from "no traffic".
    """

    def __init__(self, steps, hold_s=0.6):
        self.steps = steps
        self.i = 0
        self.hold_s = hold_s
        self.t_last = time.time()

    def render(self):
        now = time.time()
        if now - self.t_last >= self.hold_s:
            self.i = min(self.i + 1, len(self.steps) - 1)
            self.t_last = now
        s = self.steps[self.i]
        return (
            "# TYPE sglang:token_usage gauge\n"
            f'sglang:token_usage{{engine_type="unified"}} {s["usage"]}\n'
            f'sglang:cached_tokens_total{{cache_source="device"}} {s["cached"]}\n'
            f'sglang:prompt_tokens_total{{model_name="m"}} {s["prompt"]}\n'
            # the gauge that zeroes on its own timer — the thing the old code read
            f'sglang:cache_hit_rate{{engine_type="unified"}} {s.get("gauge", 0.0)}\n'
        )


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_controller(steps, h_mode, seconds=6.0):
    metrics = Metrics(steps)
    port = free_port()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = metrics.render().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    d = tempfile.mkdtemp()
    dec = os.path.join(d, "decisions.jsonl")
    cmd = [PY, CTRL, "--permit-file", os.path.join(d, "permit.json"),
           "--admission-log", os.path.join(d, "admissions.jsonl"),
           "--decision-log", dec, "--metrics-url", f"http://127.0.0.1:{port}/metrics",
           "--u-low", str(U_LOW), "--u-high", str(U_HIGH), "--h-thresh", str(H_THRESH),
           "--interval", "1", "--max-minutes", str(seconds / 60.0), "--h-mode", h_mode]
    subprocess.run(cmd, capture_output=True, timeout=seconds + 20)
    srv.shutdown()
    out = []
    if os.path.exists(dec):
        for line in open(dec):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def actions_on(decisions, usage_gt=0.0):
    return [r for r in decisions if r.get("U", 0) > usage_gt]


FAILS = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else f"  <- {detail}"))
    if not cond:
        FAILS.append(name)


# counters: prompt_tokens always moves (there is traffic) unless a step says otherwise
def steps(usage, hit, gauge=0.0, n=6):
    """Counters advance every step so the delta is a real measurement, except when
    hit is None, which means 'no completed work this interval' (prompt delta zero)."""
    prompt, cached = 100_000, 40_000
    seq = [{"usage": 0.0, "cached": cached, "prompt": prompt, "gauge": gauge}]
    hs = hit if isinstance(hit, list) else [hit] * n
    for h in hs:
        if h is None:
            seq.append({"usage": usage, "cached": cached, "prompt": prompt, "gauge": gauge})
        else:
            prompt += 10_000
            cached += int(10_000 * h)
            seq.append({"usage": usage, "cached": cached, "prompt": prompt, "gauge": gauge})
    return seq


print("H-gate smoke (windowed mode, u_high=%.1f h_thresh=%.1f):" % (U_HIGH, H_THRESH))

# 1. valid LOW hit rate is observable, and under high usage it TRIGGERS a cut
d = run_controller(steps(0.8, 0.05), "windowed")
acts = actions_on(d)[1:]
check("low measured hit under high usage triggers a cut",
      any(r["action"] == "cut" for r in acts),
      f"actions={[r['action'] for r in acts]}")
check("measured hit is reported, not silently zero",
      any(r.get("H_measured") and r.get("H") is not None for r in acts),
      f"H={[r.get('H') for r in acts]}")

# 2. valid HIGH hit rate is observable, and under the SAME high usage BLOCKS the cut
d = run_controller(steps(0.8, 0.9), "windowed")
acts = actions_on(d)[1:]
check("high measured hit under high usage BLOCKS the cut",
      all(r["action"] != "cut" for r in acts),
      f"actions={[r['action'] for r in acts]} — the H gate is not deleted")

# 3. no traffic this interval (prompt delta zero) => no failure signal => no cut
d = run_controller(steps(0.8, None), "windowed")
acts = actions_on(d)[1:]
check("no samples is not treated as zero hit rate (no cut)",
      all(r["action"] != "cut" for r in acts),
      f"actions={[r['action'] for r in acts]}")
check("no-sample ticks are marked unmeasured",
      all(r.get("H_measured") is False for r in acts),
      f"H_measured={[r.get('H_measured') for r in acts]}")

# 4. the old behaviour is still reproducible for the ablation arm: with the raw
#    gauge reading 0, the gate always passes and the cut fires on usage alone
d = run_controller(steps(0.8, 0.9, gauge=0.0), "raw")
acts = actions_on(d)[1:]
check("raw mode reproduces the old delete-the-gate behaviour",
      any(r["action"] == "cut" for r in acts),
      f"actions={[r['action'] for r in acts]}")

print()
if FAILS:
    print("SMOKE FAILED: " + ", ".join(FAILS))
    sys.exit(1)
print("ALL H-GATE SMOKE CHECKS PASS")
