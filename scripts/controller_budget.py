#!/usr/bin/env python3
"""Token-budget (feed-forward) admission controller — the paper's mechanism, v0.

Admission rule: a queued session may be admitted while the projected resident KV
working set fits the budget:
  projected = resident_est + margin * first_prompt(newcomer) <= target_util * pool_tokens
where resident_est sums each ACTIVE session's last-seen context length (from the
runner's step log) — newcomers' sizes are known at arrival from the trace CSV, so
the decision anticipates the newcomer's demand instead of reacting to pressure.

The number of sessions that fit is expressed as a count-window cap on the runner's
gate (one control variable across all policies: static / AIMD / budget).
A starvation guard force-admits the oldest waiter after --starve-seconds.
"""
import argparse
import csv
import json
import os
import time


def write_cap(path, cap):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(str(int(cap)))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-file", required=True)
    ap.add_argument("--step-log", required=True, help="runner --log-path JSONL")
    ap.add_argument("--admission-log", required=True, help="runner --admission-log JSONL")
    ap.add_argument("--trace", required=True, help="same CSV the runner replays")
    ap.add_argument("--decision-log", required=True)
    ap.add_argument("--pool-tokens", type=int, required=True)
    ap.add_argument("--metrics-port", type=int, default=30000)
    ap.add_argument("--hard-stop-usage", type=float, default=0.80,
                    help="engine usage at which no new session fits, regardless of estimate")
    ap.add_argument("--target-util", type=float, default=0.75)
    ap.add_argument("--margin", type=float, default=1.15)
    ap.add_argument("--max-cap", type=int, default=64)
    ap.add_argument("--starve-seconds", type=float, default=180.0)
    ap.add_argument("--starve-cooldown", type=float, default=120.0)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--max-minutes", type=float, default=300.0)
    args = ap.parse_args()

    budget = args.pool_tokens * args.target_util

    # Arrival-time-observable: per-session round appends/outputs/peaks from the trace CSV.
    order = []
    first_prompt = {}
    appends = {}   # sid -> [input_len per round]
    outs = {}      # sid -> [output_len per round]
    peaks = {}     # sid -> max(prefix+input+output) — the session's KV ceiling
    with open(args.trace) as f:
        for row in csv.DictReader(f):
            sid = row["session_id"]
            if sid not in first_prompt:
                first_prompt[sid] = int(row["prefix_len"]) + int(row["input_len"])
                appends[sid] = []
                outs[sid] = []
                peaks[sid] = 0
                order.append(sid)
            appends[sid].append(int(row["input_len"]))
            outs[sid].append(int(row["output_len"]))
            footprint = int(row["prefix_len"]) + int(row["input_len"]) + int(row["output_len"])
            peaks[sid] = max(peaks[sid], footprint)

    GROWTH_ROUNDS = 3  # reserve appends+outputs of the next K rounds of every session

    def horizon(sid, last_seen_round, ctx_now):
        """Expected KV growth of `sid` over the next GROWTH_ROUNDS rounds, capped at peak."""
        a, o = appends[sid], outs[sid]
        start = (last_seen_round + 1) if last_seen_round is not None else 1
        grow = sum(a[start:start + GROWTH_ROUNDS]) + sum(o[start:start + GROWTH_ROUNDS])
        base = ctx_now if ctx_now else first_prompt[sid]
        return max(0, min(peaks[sid], base + grow) - base)

    last_round = {}  # sid -> last completed round_idx (from step log)

    active = set()
    finished = set()
    last_round = {}     # sid -> last completed round_idx (from step log)
    active_ctx = {}     # sid -> largest observed prompt_len (from step log)
    waiting_since = {}  # sid -> ts first observed waiting
    cap = 1
    last_forced_ts = 0.0
    write_cap(args.cap_file, cap)
    deadline = time.time() + args.max_minutes * 60

    import re, urllib.request
    pat = re.compile(r"^(\S+?)(\{.*\})?\s+(\S+)$")

    def engine_metrics(url):
        vals = {}
        try:
            text = urllib.request.urlopen(url, timeout=5).read().decode()
        except Exception:
            return vals
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            m = pat.match(line.strip())
            if not m:
                continue
            if "quantile" in (m.group(2) or ""):
                continue
            try:
                vals[m.group(1)] = float(m.group(3))
            except ValueError:
                pass
        return vals

    metrics_url = f"http://127.0.0.1:{args.metrics_port}/metrics"
    with open(args.decision_log, "w") as log:
        while time.time() < deadline:
            now = time.time()
            for ev in read_jsonl(args.admission_log):
                sid = ev.get("session_id")
                if not sid:
                    continue
                if ev.get("event") == "admit" and sid not in active:
                    active.add(sid)
                    waiting_since.pop(sid, None)
                elif ev.get("event") == "release":
                    active.discard(sid)
                    finished.add(sid)

            em = engine_metrics(metrics_url)
            usage = em.get("sglang:token_usage", 0.0)
            # Resident KV from engine ground truth (used tokens incl. radix-cached blocks),
            # not a lagging client-side estimate.
            resident = usage * args.pool_tokens
            queued = [sid for sid in order if sid not in active and sid not in finished]
            for sid in queued:
                waiting_since.setdefault(sid, now)

            # Feed-forward projection over a short horizon: every active session reserves
            # its current context plus growth toward its peak over the next few rounds;
            # newcomers reserve their first prompt plus the same horizon growth (all
            # arrival-time observable from the trace).
            for rec in read_jsonl(args.step_log):
                sid = rec.get("session_id")
                if not sid:
                    continue
                if sid in active:
                    ri = rec.get("round_idx")
                    if ri is not None:
                        last_round[sid] = max(last_round.get(sid, -1), ri)
                    if rec.get("prompt_len"):
                        active_ctx[sid] = max(active_ctx.get(sid, 0), rec["prompt_len"])

            base_ctx = sum(active_ctx.get(sid, first_prompt[sid]) for sid in active)
            projection = max(resident, base_ctx) + sum(
                horizon(sid, last_round.get(sid), active_ctx.get(sid)) for sid in active)
            fits = 0
            forced = False
            oldest_wait = 0.0
            hard_stop = usage >= args.hard_stop_usage
            if not hard_stop:
                for sid in queued:
                    need = (first_prompt[sid] + horizon(sid, None, None)) * args.margin
                    if projection + need <= budget:
                        fits += 1
                        projection += need
                    else:
                        waiting_since.setdefault(sid, now)
                        oldest_wait = max(oldest_wait, now - waiting_since[sid])
            # Starvation guard, rate-limited: post-retraction usage dips are FAKE slack
            # (evicted sessions re-prefill their full contexts on the next round), so a
            # time-triggered forced admit here ratchets the system into permanent thrash.
            # Force at most one session per 120 s, and only when usage is genuinely low.
            if (queued and oldest_wait >= args.starve_seconds and usage < 0.5
                    and (now - last_forced_ts) >= args.starve_cooldown):
                forced = True
                fits = max(fits, 1)
                last_forced_ts = now

            cap = max(1, min(args.max_cap, len(active) + fits))
            write_cap(args.cap_file, cap)
            log.write(json.dumps({
                "ts": round(now, 3), "cap": cap, "active_n": len(active),
                "queued_n": len(queued), "resident_est": round(resident),
                "usage": round(usage, 3), "budget": round(budget),
                "fits": fits, "forced": forced, "hard_stop": hard_stop,
                "oldest_wait_s": round(oldest_wait, 1),
            }) + "\n")
            log.flush()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
