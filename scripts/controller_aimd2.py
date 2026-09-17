#!/usr/bin/env python3
"""Faithful Concur-style AIMD admission controller (permit-based).

Control law (per the Concur paper — the v0.x controller_aimd.py grew the window at any
usage<0.90 and never used u_low; that baseline was unfaithful and is retired):
  U < u_low                    -> W += alpha   (additive growth probe)
  U > u_high and H < h_thresh  -> W = ceil(W*beta)  (multiplicative cut on cache thrash)
  otherwise                    -> hold
Window changes are enforced on NAMED SESSIONS via the permit file:
  cut  -> the youngest active sessions are PAUSED (revoke permit; they release their
          slot at their next step boundary — Concur's step-boundary pause/resume)
  grow -> paused sessions resume first (FIFO), then the oldest waiting session is
          admitted (FIFO).
Every quantity is runtime-observable (metrics + admission/step logs); nothing is read
from the trace.
"""
import argparse
import json
import math
import os
import time


def write_permit(path, admitted, paused):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"admit": sorted(admitted), "paused": sorted(paused)}, f)
    os.replace(tmp, path)


def read_jsonl(path):
    out = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return out


def get_metrics(url):
    import re, urllib.request
    vals = {}
    pat = re.compile(r"^(\S+?)(\{.*\})?\s+(\S+)$")
    try:
        text = urllib.request.urlopen(url, timeout=5).read().decode()
    except Exception:
        return vals
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = pat.match(line.strip())
        if not m or "quantile" in (m.group(2) or ""):
            continue
        try:
            vals[m.group(1)] = float(m.group(3))
        except ValueError:
            pass
    return vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--permit-file", required=True)
    ap.add_argument("--admission-log", required=True)
    ap.add_argument("--decision-log", required=True)
    ap.add_argument("--metrics-url", default="http://127.0.0.1:30000/metrics")
    ap.add_argument("--initial-cap", type=int, default=1)
    ap.add_argument("--u-low", type=float, default=0.35)
    ap.add_argument("--u-high", type=float, default=0.75)
    ap.add_argument("--h-thresh", type=float, default=0.03)
    # "windowed" computes H from the engine's cumulative counters (see below); "raw"
    # reads the sglang:cache_hit_rate gauge verbatim, which is what the first
    # generation of this controller did and is kept only to reproduce that arm.
    ap.add_argument("--h-mode", choices=["windowed", "raw"], default="windowed")
    ap.add_argument("--alpha", type=float, default=2.0)
    ap.add_argument("--beta", type=float, default=0.5)
    ap.add_argument("--max-cap", type=int, default=64)
    ap.add_argument("--interval", type=float, default=30.0)
    ap.add_argument("--max-minutes", type=float, default=300.0)
    args = ap.parse_args()

    # sessions: sid -> dict(arrived_ts, state in {waiting, active, paused, done})
    sess = {}
    h_prev = [0.0, 0.0]   # last read of (cached_tokens_total, prompt_tokens_total)
    window = float(args.initial_cap)
    write_permit(args.permit_file, [], [])
    deadline = time.time() + args.max_minutes * 60

    with open(args.decision_log, "w") as log:
        while time.time() < deadline:
            now = time.time()
            for ev in read_jsonl(args.admission_log):
                sid = ev.get("session_id")
                if not sid:
                    continue
                s = sess.setdefault(sid, dict(arrived_ts=None, state="waiting"))
                etype = ev.get("event")
                if etype == "queued":
                    if s["arrived_ts"] is None:
                        s["arrived_ts"] = ev.get("ts", now)
                elif etype == "release":
                    # finished or externally paused; classify by permit state below
                    s["state"] = "done" if s["state"] != "paused" else "paused"
                elif etype == "pause":
                    s["state"] = "paused"
                elif etype == "resume":
                    s["state"] = "active"

            active = sorted((sid for sid, s in sess.items() if s["state"] == "active"),
                            key=lambda sid: sess[sid]["arrived_ts"] or now)
            paused = sorted((sid for sid, s in sess.items() if s["state"] == "paused"),
                            key=lambda sid: sess[sid]["arrived_ts"] or now)
            waiting = sorted((sid for sid, s in sess.items() if s["state"] == "waiting"
                              and s["arrived_ts"] is not None),
                             key=lambda sid: sess[sid]["arrived_ts"])

            m = get_metrics(args.metrics_url)
            usage = m.get("sglang:token_usage", 0.0)

            # H_t must be the cache hit rate *observed during interval t*. The
            # sglang:cache_hit_rate gauge is zeroed on its own (shorter) timer, so a 30s
            # poll reads 0 whenever nothing finished in that sub-window — and 0 < h_thresh
            # is true for every h_thresh, which silently deletes the gate: the cut
            # condition degenerates to `usage > u_high` and h_thresh stops mattering.
            # Take the delta of the cumulative counters instead, so H is defined whenever
            # there was traffic. No traffic => no failure signal => the gate cannot fire
            # (the formula requires H_t < H_thresh to hold, and an unmeasured H_t does not).
            hit, hit_measured = None, False
            if args.h_mode == "raw":
                hit, hit_measured = m.get("sglang:cache_hit_rate", 1.0), True
            else:
                cached = m.get("sglang:cached_tokens_total")
                prompt = m.get("sglang:prompt_tokens_total")
                if cached is not None and prompt is not None:
                    dc, dp = cached - h_prev[0], prompt - h_prev[1]
                    h_prev[0], h_prev[1] = cached, prompt
                    if dp > 0:
                        hit, hit_measured = max(0.0, min(1.0, dc / dp)), True

            prev = window
            action = "hold"
            if usage == 0.0:
                action = "hold"   # engine idle: no information
            elif usage > args.u_high and hit_measured and hit < args.h_thresh:
                window = max(math.ceil(window * args.beta), 1.0)
                action = "cut"
            elif usage < args.u_low:
                window = min(window + args.alpha, float(args.max_cap))
                action = "grow"

            # enforce the window on named sessions: cut pauses the youngest active;
            # grow resumes the oldest paused, then admits the oldest waiting.
            w = int(window)
            newly = []
            if len(active) > w:
                for sid in active[w:]:
                    sess[sid]["state"] = "paused"
                    paused.append(sid)
            active = active[:w]
            room = w - len(active)
            while room > 0 and paused:
                sid = paused.pop(0)
                sess[sid]["state"] = "active"
                active.append(sid)
                room -= 1
                newly.append(sid)
            while room > 0 and waiting:
                sid = waiting.pop(0)
                sess[sid]["state"] = "active"
                active.append(sid)
                room -= 1
                newly.append(sid)

            write_permit(args.permit_file, active, paused)
            log.write(json.dumps({
                "ts": round(now, 3), "W": window, "prev": prev, "action": action,
                "U": usage, "H": hit, "H_measured": hit_measured,
                "active_n": len(active), "paused_n": len(paused),
                "waiting_n": len(waiting), "newly_admitted": newly,
            }) + "\n")
            log.flush()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
