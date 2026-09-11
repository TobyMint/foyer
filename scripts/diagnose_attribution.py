#!/usr/bin/env python3
"""Attribution diagnosis over existing run logs — quantifies the headroom for:
  (1) recompute waste (uncached prompt tokens that prefix caching should have saved)
  (2) wrong-victim eviction (full-recompute rounds on sessions whose cache was
      needed again quickly — short inter-round gap)
  (3) shed cost (budget3: pause duration + first-round TTFT penalty after resume)
"""
import json, statistics, sys
from collections import defaultdict

NIGHT = "/data/xbw/turnstile/results/night"

def load_steps(run):
    per_sess = defaultdict(list)
    uncached_total = prompt_total = 0
    full_recompute_events = []  # (sid, gap_s, ts, prompt_len)
    healthy_gaps = []
    for line in open(f"{NIGHT}/{run}/steps.jsonl"):
        r = json.loads(line)
        if r.get("status") != "SUCCESS":
            continue
        sid = r.get("session_id")
        unc = r.get("server_uncached_prompt_tokens") or 0
        plen = r.get("prompt_len") or 0
        uncached_total += unc
        prompt_total += plen
        hist = per_sess[sid]
        prev = hist[-1] if hist else None
        gap = (r["submit_timestamp"] - prev["ts"]) if prev else None
        rec = dict(ts=r["submit_timestamp"], ttft=r.get("first_token_ms"), gap=gap)
        hist.append(rec)
        if prev and plen and unc > 0.8 * plen:
            full_recompute_events.append((sid, gap, r["submit_timestamp"], plen))
        elif prev and gap is not None:
            healthy_gaps.append(gap)
    return per_sess, uncached_total, prompt_total, full_recompute_events, healthy_gaps

def shed_costs(run):
    evs = [json.loads(l) for l in open(f"{NIGHT}/{run}/admissions.jsonl")]
    pause_ts = {}
    durations = []
    for e in evs:
        sid, et = e.get("session_id"), e.get("event")
        if et == "pause":
            pause_ts[sid] = e["ts"]
        elif et == "resume" and sid in pause_ts:
            durations.append(e["ts"] - pause_ts[sid])
            del pause_ts[sid]
    stuck = len(pause_ts)
    return durations, stuck

def ttft_penalty(run, per_sess):
    evs = [json.loads(l) for l in open(f"{NIGHT}/{run}/admissions.jsonl")]
    pause_ts = {}
    first_after_resume = {}
    for e in evs:
        sid, et = e.get("session_id"), e.get("event")
        if et == "pause":
            pause_ts[sid] = e["ts"]
        elif et == "resume":
            pause_ts[sid] = ("resume", e["ts"])
    for sid, hist in per_sess.items():
        if sid not in pause_ts:
            continue
        entry = pause_ts[sid]
        if not (isinstance(entry, tuple) and entry[0] == "resume"):
            continue
        rts = entry[1]
        after = [h["ttft"] for h in hist if h["ts"] > rts and h["ttft"]]
        own = [h["ttft"] for h in hist if h["ttft"]]
        if after and len(own) > 1:
            first_after_resume[sid] = (after[0], statistics.median(own))
    vals = [(a / m if m else 0) for a, m in first_after_resume.values()]
    return vals

for run in sys.argv[1:]:
    per_sess, unc, ptot, fullrec, healthy_gaps = load_steps(run)
    hit_eff = 100 * (1 - unc / ptot) if ptot else 0
    gaps_fr = [g for _, g, _, _ in fullrec if g is not None]
    line = f"{run}: recompute={unc/1e6:.2f}M tokens ({100*unc/ptot:.1f}% of {ptot/1e6:.1f}M prompt)"
    if gaps_fr:
        line += f" | full-recompute rounds={len(fullrec)}, their gap median={statistics.median(gaps_fr):.0f}s"
    if healthy_gaps:
        line += f" vs healthy-gap median={statistics.median(healthy_gaps):.0f}s"
    print(line)
    if run in ("budget200c_budget3", "load25c_budget3"):
        durs, stuck = shed_costs(run)
        if durs:
            print(f"  shed: {len(durs)} completed pauses, median {statistics.median(durs):.0f}s, "
                  f"max {max(durs):.0f}s, stuck-now {stuck}")
        pen = ttft_penalty(run, per_sess)
        if pen:
            print(f"  resume TTFT penalty: median x{statistics.median(pen):.2f} of own baseline "
                  f"({len(pen)} resumes)")
