#!/usr/bin/env python3
"""GPU-free smoke test for controller_foyer.py.

Runs the real controller as a subprocess against a scripted metrics endpoint and
hand-written admission/step logs, then asserts on the decision log. No GPU, no
server, no trace.

The load-bearing scenario is `engine_truth_beats_ctx_sum`: give the engine a LOW
measured usage and the sessions a HIGH logical context sum. v3 computed
max(resident, ctx_sum) and would refuse to admit; the new controller is supposed
to trust the measurement and let the session in. If that one regresses, the design
change did not happen.

    python3 tests/test_controller_foyer.py
"""
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROLLER = os.path.join(HERE, os.pardir, "scripts", "controller_foyer.py")
POOL = 101432

_failures = []


def check(cond, label, detail=""):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s   %s" % (label, detail))
        _failures.append(label)


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    usage = 0.0

    def do_GET(self):
        body = ("# HELP sglang:token_usage\n"
                "# TYPE sglang:token_usage gauge\n"
                "sglang:token_usage %.6f\n"
                "sglang:cached_tokens_total 1000\n"
                "sglang:prompt_tokens_total 2000\n" % MetricsHandler.usage).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def run_case(name, usage, admissions, steps, extra_args=(), cycles=6):
    """Run the controller once and return its last decision record."""
    tmp = tempfile.mkdtemp(prefix="foyer_smoke_")
    try:
        MetricsHandler.usage = usage
        port = free_port()
        srv = http.server.HTTPServer(("127.0.0.1", port), MetricsHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        adm = os.path.join(tmp, "admissions.jsonl")
        stp = os.path.join(tmp, "steps.jsonl")
        dec = os.path.join(tmp, "controller.jsonl")
        permit = os.path.join(tmp, "permit.json")
        with open(adm, "w") as f:
            for e in admissions:
                f.write(json.dumps(e) + "\n")
        with open(stp, "w") as f:
            for e in steps:
                f.write(json.dumps(e) + "\n")

        cmd = [sys.executable, CONTROLLER,
               "--permit-file", permit, "--admission-log", adm,
               "--step-log", stp, "--decision-log", dec,
               "--pool-tokens", str(POOL), "--metrics-port", str(port),
               "--interval", "0.15",
               "--max-minutes", str(cycles * 0.15 / 60.0 + 0.01)] + list(extra_args)
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        srv.shutdown()

        rows = [json.loads(l) for l in open(dec) if l.strip()]
        rows = [r for r in rows if "cycle_error" not in r]
        if not rows:
            raise AssertionError("controller wrote no decision rows")
        return rows[-1]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Real wall-clock timestamps. The controller drops a pending admission whose
# event timestamp is more than --pending-timeout-s behind `now`, and `now` is real
# time, so synthetic epoch-1000 stamps would be stale the instant they were read.
T0 = time.time()


def session_events(sid, prompt_tokens=20000, ts=None):
    return [{"ts": T0 if ts is None else ts, "event": "queued",
             "session_id": sid, "prompt_tokens": prompt_tokens}]


def admit_event(sid, prompt_tokens=20000, ts=None):
    return {"ts": T0 + 1 if ts is None else ts, "event": "admit",
            "session_id": sid, "prompt_tokens": prompt_tokens}


def step_record(sid, prompt_len, round_idx=0):
    return {"session_id": sid, "round_idx": round_idx, "prompt_len": prompt_len,
            "status": "SUCCESS", "first_token_ms": 1500, "complete_timestamp": T0 + 2}


def main():
    print("controller_foyer smoke test\n")

    # 1. The headline behavioural change. One session is ACTIVE and its context runs
    #    to 90k, but the engine reports only 30k of pool in use (prefix sharing), and
    #    a third session wants in. v3 computed max(resident, ctx_sum) = 90k and then
    #    added the newcomer times a margin, so it refused. This controller must trust
    #    the measurement and admit.
    print("engine_truth_beats_ctx_sum")
    adm = session_events("big") + [admit_event("big", 90000)] + session_events("new", 20000)
    steps = [step_record("big", 90000)]
    d = run_case("engine_truth", 0.30, adm, steps,
                 extra_args=["--growth-scale", "0", "--margin", "1.0"])
    check(d["measured"] == round(0.30 * POOL),
          "base is the measured usage, not the session contexts",
          "measured=%s expected=%s" % (d["measured"], round(0.30 * POOL)))
    old_style = max(d["measured"], 90000) + 20000 * 1.15
    check(old_style > d["red_line"],
          "the v3 formula would have refused (sanity check on the scenario)",
          "v3 projection=%d red=%d" % (old_style, d["red_line"]))
    check(d["n_admitted"] == 1,
          "admits anyway: 30k measured + 20k newcomer fits the 91k red line",
          "n=%s committed=%s red=%s" % (d["n_admitted"], d["committed"], d["red_line"]))

    # 2. the red line is what stops admission
    print("red_line_blocks")
    d = run_case("red_line", 0.92, session_events("s1"), [],
                 extra_args=["--target-util", "0.90", "--disable-starve-guard"])
    check(d["n_admitted"] == 0, "no admit above the red line", "n=%s" % d["n_admitted"])
    d = run_case("red_line", 0.50, session_events("s1"), [],
                 extra_args=["--target-util", "0.90"])
    check(d["n_admitted"] == 1, "admits below the red line", "n=%s" % d["n_admitted"])

    # 3. pending: an admitted session the engine cannot see yet must still be charged
    print("pending_admission_is_charged")
    adm = session_events("s1") + [admit_event("s1", 20000)]
    d = run_case("pending", 0.10, adm, [])
    check(d["pending_n"] == 1 and d["pending"] == 20000,
          "pending carries the admitted-but-unlanded session",
          "pending_n=%s pending=%s" % (d["pending_n"], d["pending"]))
    d = run_case("pending", 0.10, adm, [step_record("s1", 20000)])
    check(d["pending_n"] == 0 and d["pending"] == 0,
          "pending clears once a step record proves it landed",
          "pending_n=%s pending=%s" % (d["pending_n"], d["pending"]))

    # 4. growth reserve is a scale, and zero really means zero (needs the session
    #    ACTIVE, or there is nothing to reserve against and both arms read 0)
    print("growth_scale")
    sess = session_events("s1") + [admit_event("s1", 20000)]
    steps = [step_record("s1", 20000, 0), step_record("s1", 26000, 1),
             step_record("s1", 32000, 2)]
    d0 = run_case("growth0", 0.30, sess, steps, extra_args=["--growth-scale", "0"])
    d1 = run_case("growth1", 0.30, sess, steps, extra_args=["--growth-scale", "1.0"])
    check(d0["growth_reserve"] == 0, "growth_scale=0 disables the reserve",
          "reserve=%s" % d0["growth_reserve"])
    check(d1["growth_reserve"] > 0, "growth_scale=1.0 reserves something",
          "reserve=%s" % d1["growth_reserve"])

    # 5. the safety net still works: hard valve sheds the youngest. The two sessions
    #    must together exceed the shed limit (0.9 * red line) or there is nothing to
    #    revoke and the check would pass vacuously.
    print("valve_still_sheds")
    two = (session_events("s1") + session_events("s2", ts=T0 + 5)
           + [admit_event("s1", 50000), admit_event("s2", 50000, ts=T0 + 7)])
    d = run_case("shed", 0.99, two,
                 [step_record("s1", 50000, 0), step_record("s2", 50000, 0)],
                 extra_args=["--hard-stop-usage", "0.93", "--target-util", "0.90"])
    check(d["valve"] is True, "hard valve fires above --hard-stop-usage",
          "valve=%s usage=%s" % (d["valve"], d["usage"]))
    check(d["shed_n"] >= 1, "shedding revokes a permit on the valve",
          "shed_n=%s (2x50k must exceed 0.9*red=%d)" % (d["shed_n"], int(0.9 * d["red_line"])))

    # 6. the newcomer's own padding is a separate, default-off knob
    print("newcomer_margin")
    d = run_case("margin", 0.10, session_events("s1"), [step_record("s1", 20000)],
                 extra_args=["--margin", "1.0", "--growth-scale", "0",
                             "--target-util", "0.30"])
    check(d["n_admitted"] == 1, "admits when 20k fits under a 30k red line",
          "n=%s committed=%s red=%s" % (d["n_admitted"], d["committed"], d["red_line"]))
    d = run_case("margin", 0.10, session_events("s1"), [step_record("s1", 20000)],
                 extra_args=["--margin", "3.0", "--growth-scale", "0",
                             "--target-util", "0.30"])
    check(d["n_admitted"] == 0, "a 3x margin on the newcomer blocks it",
          "n=%s" % d["n_admitted"])

    print()
    if _failures:
        print("%d FAILED: %s" % (len(_failures), ", ".join(_failures)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
