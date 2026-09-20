#!/usr/bin/env python3
"""Offline replay of the AIMD controller's admission state machine (defect B).

What it does
------------
For one run dir, replay `admissions.jsonl` exactly the way `controller_aimd2.py`
does (queued -> arrived_ts, release -> done|paused, pause -> paused, resume ->
active, `admit` unhandled) and compare the resulting waiting/active/paused counts
with the numbers the controller actually logged.

Signature this looks for
------------------------
A controller that starts BEFORE the first event of the admissions log it is reading,
while already reporting non-zero waiting/active state, must have ingested events that
are no longer in the file — i.e. the stale log of a previous attempt in the same run
dir. Because the trace replay reuses session ids, those stale entries keep their old
states ("done"), so the sessions never re-enter the waiting set: the controller sees
an empty queue while the runner has hundreds of sessions queued.

Usage: replay_admission_state.py <run_dir> [...]
"""
import json
import os
import sys
import time


def read_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def replay_state(events, start_ts=None):
    """The controller's state machine as implemented, with the defect-B guard applied
    when start_ts is given (events older than the controller's own start are stale)."""
    sess = {}
    for ev in events:
        sid = ev.get("session_id")
        if not sid:
            continue
        if start_ts is not None and (ev.get("ts") or 0) < start_ts:
            continue
        s = sess.setdefault(sid, {"arrived_ts": None, "state": "waiting"})
        etype = ev.get("event")
        if etype == "queued":
            if s["arrived_ts"] is None:
                s["arrived_ts"] = ev.get("ts")
            if s["state"] not in ("active", "paused"):
                s["state"] = "waiting"
        elif etype == "admit":
            s["state"] = "active"
        elif etype == "release":
            s["state"] = "done" if s["state"] != "paused" else "paused"
        elif etype == "pause":
            s["state"] = "paused"
        elif etype == "resume":
            s["state"] = "active"
    waiting = [s for s, v in sess.items()
               if v["state"] == "waiting" and v["arrived_ts"] is not None]
    active = [s for s, v in sess.items() if v["state"] == "active"]
    paused = [s for s, v in sess.items() if v["state"] == "paused"]
    return sess, waiting, active, paused


def hhmmss(ts):
    return time.strftime("%m-%d %H:%M:%S", time.localtime(ts))


def check(run_dir):
    adm_p = os.path.join(run_dir, "admissions.jsonl")
    ctl_p = os.path.join(run_dir, "controller.jsonl")
    if not (os.path.isfile(adm_p) and os.path.isfile(ctl_p)):
        print(f"{os.path.basename(run_dir)}: missing logs — skip")
        return
    adm = read_jsonl(adm_p)
    ctl = read_jsonl(ctl_p)
    if not adm or not ctl:
        print(f"{os.path.basename(run_dir)}: empty logs — skip")
        return
    first_ev, first_dec = adm[0]["ts"], ctl[0]["ts"]
    early = [c for c in ctl if c["ts"] < first_ev]
    poisoned = bool(early) and any(
        (c.get("waiting_n") or 0) + (c.get("active_n") or 0) > 0 for c in early)
    _, waiting_old, _, _ = replay_state(adm)
    sess, waiting, active, paused = replay_state(adm, start_ts=first_dec - 5.0)
    queued = sum(1 for e in adm if e.get("event") == "queued")
    print(f"--- {os.path.basename(run_dir)} ---")
    print(f"  准入日志: {len(adm)} 事件, 首个 {hhmmss(first_ev)}, queued={queued}")
    print(f"  控制器:   {len(ctl)} 条决策, 首条 {hhmmss(first_dec)}")
    if early:
        w = max(c.get("waiting_n") or 0 for c in early)
        a = max(c.get("active_n") or 0 for c in early)
        print(f"  首条事件之前已有 {len(early)} 条决策 (waiting 峰值 {w}, active 峰值 {a})"
              f" → {'⚠ 读到过旧日志（污染）' if poisoned else '干净'}")
    else:
        print("  控制器首条决策不早于首个事件 → 干净")
    print(f"  重放（旧逻辑，含陈旧事件）: waiting={len(waiting_old)}")
    print(f"  重放（修复后，忽略早于控制器启动的事件）: waiting={len(waiting)} "
          f"active={len(active)} paused={len(paused)}  "
          f"[控制器实报末条 waiting={ctl[-1].get('waiting_n')} "
          f"active={ctl[-1].get('active_n')}]")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = ["/data/xbw/turnstile/results/night/" + n for n in
                ("aimd2_paper", "aimd2_ul35", "aimd2_uh75", "pois200_aimd2")]
    for d in args:
        check(d)
