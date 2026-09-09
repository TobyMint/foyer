#!/usr/bin/env python3
"""Token-budget admission controller v0.5.

v0.4 post-mortem (load200): cap ratcheted 4 -> 64 because (a) the projection floor
used INSTANTANEOUS token_usage, which dips to near-zero after retraction storms —
fake slack, each dip leaked admits; (b) cap = active + fits can never decrease;
(c) no service-quality signal, so cache collapse went unnoticed while admission
continued. Hit rate fell to 0.3% and TTFT blew up 5x vs a static cap-4.

v0.5 fixes, still feed-forward (no cache-hit feedback):
  1. High-water floor: floor = max(usage, highwater) where highwater decays slowly
     (half-life ~5 min). A dip is only "free" after it persists for minutes.
  2. Single-flight admission: at most ONE newcomer per cycle, and only after the
     previous newcomer has completed >= 1 round (no stampedes).
  3. TTFT-SLO valve: if p50 first-token latency of recent steps > SLO, freeze
     admission regardless of the projection (quality guard, logged separately).
  4. Starve guard: rate-limited as in v0.4, but gated on the high-water floor
     (< 0.5), so post-retraction dips cannot trigger it.
"""
import argparse
import csv
import json
import math
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


def tail_jsonl(path, n_bytes=1 << 20):
    """Read roughly the last n_bytes of a growing JSONL (TTFT valve only needs recent steps)."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > n_bytes:
                f.seek(size - n_bytes)
                f.readline()  # drop the partial line
            data = f.read().decode(errors="replace")
        out = []
        for line in data.splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return out
    except FileNotFoundError:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-file", required=True)
    ap.add_argument("--step-log", required=True)
    ap.add_argument("--admission-log", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--decision-log", required=True)
    ap.add_argument("--pool-tokens", type=int, required=True)
    ap.add_argument("--metrics-port", type=int, default=30000)
    ap.add_argument("--hard-stop-usage", type=float, default=0.85)
    ap.add_argument("--target-util", type=float, default=0.75)
    ap.add_argument("--margin", type=float, default=1.15)
    ap.add_argument("--max-cap", type=int, default=64)
    ap.add_argument("--starve-seconds", type=float, default=240.0)
    ap.add_argument("--starve-cooldown", type=float, default=300.0)
    ap.add_argument("--highwater-decay", type=float, default=0.995,
                    help="per-cycle multiplicative decay of the usage high-water mark")
    ap.add_argument("--slo-ms", type=float, default=10000.0)
    ap.add_argument("--slo-window", type=int, default=20)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--max-minutes", type=float, default=300.0)
    # Ablation switches: each removes one v0.5 component (paper Section ablations).
    ap.add_argument("--disable-highwater", action="store_true",
                    help="use instantaneous usage as floor (v0.4 behavior: dip leak)")
    ap.add_argument("--disable-single-flight", action="store_true",
                    help="allow multi-admit per cycle, no prev-started gate (v0.4 stampedes)")
    ap.add_argument("--disable-slo-valve", action="store_true",
                    help="no TTFT-SLO admission freeze")
    args = ap.parse_args()

    budget = args.pool_tokens * args.target_util

    # Arrival-time-observable: per-session round appends/outputs/peaks from the trace CSV.
    order = []
    first_prompt = {}
    appends = {}
    outs = {}
    peaks = {}
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

    GROWTH_ROUNDS = 3

    def horizon(sid, last_seen_round, ctx_now):
        a, o = appends[sid], outs[sid]
        start = (last_seen_round + 1) if last_seen_round is not None else 1
        grow = sum(a[start:start + GROWTH_ROUNDS]) + sum(o[start:start + GROWTH_ROUNDS])
        base = ctx_now if ctx_now else first_prompt[sid]
        return max(0, min(peaks[sid], base + grow) - base)

    active = set()
    finished = set()
    last_round = {}
    active_ctx = {}
    waiting_since = {}
    ttfts = []          # recent first-token latencies (ms) for the SLO valve
    cap = 1
    last_forced_ts = 0.0
    highwater = 0.0
    last_admitted_sid = None
    last_admit_ts = 0.0
    cycle = 0
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
            cycle += 1
            for ev in read_jsonl(args.admission_log):
                sid = ev.get("session_id")
                if not sid:
                    continue
                if ev.get("event") == "admit" and sid not in active:
                    active.add(sid)
                    waiting_since.pop(sid, None)
                    last_admitted_sid = sid
                    last_admit_ts = ev.get("ts", now)
                elif ev.get("event") == "release":
                    active.discard(sid)
                    finished.add(sid)

            em = engine_metrics(metrics_url)
            usage = em.get("sglang:token_usage", 0.0)
            # High-water floor: instantaneous usage dips are fake slack after
            # retractions (evicted sessions re-prefill on their next round).
            # Only a dip that PERSISTS (high-water decayed for minutes) is real.
            highwater = max(usage, highwater * args.highwater_decay)
            floor = usage if args.disable_highwater else max(usage, highwater)
            resident = floor * args.pool_tokens
            queued = [sid for sid in order if sid not in active and sid not in finished]
            for sid in queued:
                waiting_since.setdefault(sid, now)

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

            # Recent TTFTs from the tail of the step log (SLO valve input).
            for rec in tail_jsonl(args.step_log):
                ft = rec.get("first_token_ms")
                if ft is not None and rec.get("status") == "SUCCESS":
                    ttfts.append(ft)
            ttfts = ttfts[-args.slo_window:]
            slo_breach = len(ttfts) >= max(5, args.slo_window // 2) and \
                sorted(ttfts)[len(ttfts) // 2] > args.slo_ms

            base_ctx = sum(active_ctx.get(sid, first_prompt[sid]) for sid in active)
            projection = max(resident, base_ctx) + sum(
                horizon(sid, last_round.get(sid), active_ctx.get(sid)) for sid in active)

            fits = 0
            forced = False
            oldest_wait = 0.0
            hard_stop = usage >= args.hard_stop_usage
            valve = hard_stop or (slo_breach and not args.disable_slo_valve)
            # Single-flight: <=1 newcomer per cycle, and only once the previous
            # newcomer has visibly started executing (>=1 completed round, or 60 s
            # elapsed — a stuck first round must not block admission forever).
            prev_started = True
            if not args.disable_single_flight:
                prev_started = (last_admitted_sid is None
                                or last_round.get(last_admitted_sid, -1) >= 0
                                or now - last_admit_ts > 60)
            if not valve and prev_started and queued:
                if args.disable_single_flight:
                    for sid in queued:  # v0.4-style: admit every session that fits
                        need = (first_prompt[sid] + horizon(sid, None, None)) * args.margin
                        if projection + need <= budget:
                            fits += 1
                            projection += need
                        else:
                            break
                else:
                    sid = queued[0]  # oldest waiter (trace order == arrival order)
                    need = (first_prompt[sid] + horizon(sid, None, None)) * args.margin
                    if projection + need <= budget:
                        fits = 1
                        projection += need
            for sid in queued:
                waiting_since.setdefault(sid, now)
                oldest_wait = max(oldest_wait, now - waiting_since[sid])
            # Starve guard: gated on the high-water floor, not the instant value.
            if (queued and oldest_wait >= args.starve_seconds and floor < 0.5
                    and (now - last_forced_ts) >= args.starve_cooldown):
                forced = True
                fits = max(fits, 1)
                last_forced_ts = now

            cap = max(1, min(args.max_cap, len(active) + fits))
            write_cap(args.cap_file, cap)
            log.write(json.dumps({
                "ts": round(now, 3), "cap": cap, "active_n": len(active),
                "queued_n": len(queued), "resident_est": round(resident),
                "usage": round(usage, 3), "highwater": round(highwater, 3),
                "budget": round(budget), "fits": fits, "forced": forced,
                "hard_stop": hard_stop, "slo_breach": slo_breach,
                "ttft_p50_ms": round(sorted(ttfts)[len(ttfts) // 2]) if ttfts else None,
                "oldest_wait_s": round(oldest_wait, 1),
            }) + "\n")
            log.flush()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
