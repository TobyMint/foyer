#!/usr/bin/env python3
"""Regression test for defect B: the AIMD controller inherits stale state when a run
dir is reused across attempts.

Scenario (exactly what happened to aimd2_paper on 09-19): the previous attempt left an
admissions.jsonl in the run dir; the controller starts ~4 minutes before the new runner
and reads it; the trace replay reuses session ids, so the stale "done" entries survive
into the new run. The old state machine then never re-queues those sessions, the visible
queue collapses, and with the engine idle (`usage == 0` -> "hold") the window never
grows again: a deadlock that has nothing to do with the controller's parameters.

Run: python3 tests/test_aimd2_stale_state.py
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "scripts", "controller_aimd2.py")

spec = importlib.util.spec_from_file_location("controller_aimd2", SRC)
ctrl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctrl)

SIDS = [f"claude:{i:04d}" for i in range(200)]
T0 = 1_700_000_000.0          # previous attempt
T1 = T0 + 86_400.0            # this attempt starts a day later


def old_apply(sess, ev):
    """The pre-fix state machine (no admit branch, queued never re-queues, no guard)."""
    sid = ev["session_id"]
    s = sess.setdefault(sid, dict(arrived_ts=None, state="waiting"))
    e = ev["event"]
    if e == "queued":
        if s["arrived_ts"] is None:
            s["arrived_ts"] = ev["ts"]
    elif e == "release":
        s["state"] = "done" if s["state"] != "paused" else "paused"
    elif e == "pause":
        s["state"] = "paused"
    elif e == "resume":
        s["state"] = "active"


def waiting(sess):
    return [s for s, v in sess.items()
            if v["state"] == "waiting" and v["arrived_ts"] is not None]


def stale_events():
    """What the previous attempt's log looks like: everyone ran and released."""
    evs = []
    for i, sid in enumerate(SIDS):
        evs.append({"ts": T0 + i * 0.01, "event": "queued", "session_id": sid})
        evs.append({"ts": T0 + 5 + i * 0.01, "event": "admit", "session_id": sid})
        evs.append({"ts": T0 + 600 + i * 0.01, "event": "release", "session_id": sid})
    return evs


def new_events():
    """The new attempt: the runner truncates the file and re-emits queued for all."""
    return [{"ts": T1 + i * 0.001, "event": "queued", "session_id": sid}
            for i, sid in enumerate(SIDS)]


def main():
    fails = []

    # Old behaviour, old file then new file (the live poisoning).
    sess_old = {}
    for ev in stale_events() + new_events():
        old_apply(sess_old, ev)
    got_old = len(waiting(sess_old))
    if got_old != 0:
        fails.append(f"old logic should reproduce the deadlock (waiting=0), got {got_old}")

    # Fixed behaviour: the stale events are older than the controller start -> skipped.
    sess_new = {}
    started = T1 - 5.0
    for ev in stale_events() + new_events():
        ctrl.apply_event(sess_new, ev, started, now=T1)
    got_new = len(waiting(sess_new))
    if got_new != len(SIDS):
        fails.append(f"fixed logic should queue all {len(SIDS)} sessions, got {got_new}")

    # A session that is admitted must leave the queue (admit branch).
    sess_mid = {}
    ctrl.apply_event(sess_mid, {"ts": T1, "event": "queued", "session_id": SIDS[0]},
                     started, now=T1)
    ctrl.apply_event(sess_mid, {"ts": T1 + 1, "event": "admit", "session_id": SIDS[0]},
                     started, now=T1)
    if waiting(sess_mid):
        fails.append("admit branch missing: admitted session still counted as waiting")

    # Legitimate events from before the controller start are only those of the previous
    # attempt; a resume in the current attempt must still be honoured.
    sess_r = {}
    ctrl.apply_event(sess_r, {"ts": T1, "event": "queued", "session_id": SIDS[1]},
                     started, now=T1)
    ctrl.apply_event(sess_r, {"ts": T1 + 2, "event": "pause", "session_id": SIDS[1]},
                     started, now=T1)
    if sess_r[SIDS[1]]["state"] != "paused":
        fails.append("pause branch broken")
    ctrl.apply_event(sess_r, {"ts": T1 + 3, "event": "resume", "session_id": SIDS[1]},
                     started, now=T1)
    if sess_r[SIDS[1]]["state"] != "active":
        fails.append("resume branch broken")

    print(f"old logic with stale log : waiting={got_old}   (expect 0 -> deadlock)")
    print(f"fixed logic, same input  : waiting={got_new} (expect {len(SIDS)})")
    if fails:
        print("FAIL")
        for f in fails:
            print("  -", f)
        return 1
    print("ALL STALE-STATE TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
