#!/usr/bin/env python3
"""Foyer controller v3: capacity-aware admission with ONLINE demand estimation.

Reads NO trace file — every quantity is observed at runtime:
  arrival size     "queued"/"admit" events in the admission log (prompt_tokens field)
  per-session ctx  prompt_len of completed rounds in the step log
  growth forecast  per-session EMA of observed round-to-round context growth, blended
                   with the running global prior for young sessions (no per-session
                   history yet)
  spare capacity   engine token_usage high-water floor — retraction storms dip the
                   instantaneous value; only a dip that persists for minutes is real
Safety valves: single-flight admission, hard usage stop, TTFT-SLO freeze, rate-limited
starve guard. Admission is by NAMED PERMIT: the controller writes the exact set of
session ids allowed to hold a slot, so the projection target and the admitted session
coincide by construction. v0.5 (trace-horizon reservation) is kept as the oracle upper
bound this controller is compared against.
"""
import argparse
import json
import os
import time
from collections import deque


def write_permit(path, admitted, paused=()):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--permit-file", required=True)
    ap.add_argument("--admission-log", required=True)
    ap.add_argument("--step-log", required=True)
    ap.add_argument("--decision-log", required=True)
    ap.add_argument("--pool-tokens", type=int, required=True)
    ap.add_argument("--metrics-port", type=int, default=30000)
    ap.add_argument("--target-util", type=float, default=0.75)
    ap.add_argument("--margin", type=float, default=1.15)
    ap.add_argument("--horizon-rounds", type=int, default=3,
                    help="reserve this many rounds of forecast growth per session")
    ap.add_argument("--ema-alpha", type=float, default=0.4,
                    help="weight of the newest observed growth in the per-session EMA")
    ap.add_argument("--young-blend", type=float, default=0.5,
                    help="sessions with <3 observations blend their EMA with the global prior")
    ap.add_argument("--hard-stop-usage", type=float, default=0.85)
    ap.add_argument("--highwater-decay", type=float, default=0.995)
    ap.add_argument("--slo-ms", type=float, default=10000.0)
    ap.add_argument("--slo-window", type=int, default=20)
    ap.add_argument("--starve-seconds", type=float, default=240.0)
    ap.add_argument("--starve-cooldown", type=float, default=300.0)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--max-minutes", type=float, default=300.0)
    ap.add_argument("--disable-highwater", action="store_true")
    ap.add_argument("--disable-single-flight", action="store_true")
    ap.add_argument("--disable-slo-valve", action="store_true")
    ap.add_argument("--disable-shedding", action="store_true",
                    help="never revoke active permits on valve (v0.5 behavior — r3 collapse)")
    args = ap.parse_args()

    budget = args.pool_tokens * args.target_util
    sess = {}          # sid -> dict(arrived_ts, prompt0, active, finished, ctx, last_round, ema, n_obs)
    highwater = 0.0
    ttfts = deque(maxlen=args.slo_window)
    glob_growth_sum = 0.0
    glob_growth_n = 0
    last_admitted_sid = None
    last_admit_ts = 0.0
    last_forced_ts = 0.0
    admitted_now = set()   # what we last wrote to the permit file
    deadline = time.time() + args.max_minutes * 60

    def forecast(s):
        """Forecast context growth over the next horizon rounds (tokens)."""
        if s["ema"] is not None:
            est = s["ema"]
            if s["n_obs"] < 3:
                prior = glob_growth_sum / glob_growth_n if glob_growth_n else est
                est = args.young_blend * est + (1 - args.young_blend) * prior
            return est * args.horizon_rounds
        prior = glob_growth_sum / glob_growth_n if glob_growth_n else 0.0
        return prior * args.horizon_rounds

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
            if not m or "quantile" in (m.group(2) or ""):
                continue
            try:
                vals[m.group(1)] = float(m.group(3))
            except ValueError:
                pass
        return vals

    metrics_url = f"http://127.0.0.1:{args.metrics_port}/metrics"
    # append: a supervised restart must not truncate the decision history
    with open(args.decision_log, "a") as log:
        while time.time() < deadline:
          try:
            now = time.time()
            now = time.time()

            # 1. arrivals / admission events
            for ev in read_jsonl(args.admission_log):
                sid = ev.get("session_id")
                if not sid:
                    continue
                s = sess.setdefault(sid, dict(arrived_ts=None, prompt0=0, active=False,
                                              finished=False, ctx=0, last_round=-1,
                                              ema=None, n_obs=0))
                etype = ev.get("event")
                if etype == "queued":
                    if s["arrived_ts"] is None:
                        s["arrived_ts"] = ev.get("ts", now)
                    s["prompt0"] = int(ev.get("prompt_tokens") or 0)
                elif etype == "admit":
                    s["active"] = True
                    if ev.get("prompt_tokens"):
                        s["prompt0"] = int(ev["prompt_tokens"])
                    last_admitted_sid = sid
                    last_admit_ts = ev.get("ts", now)
                elif etype == "resume":
                    s["active"] = True
                elif etype == "pause":
                    # a shed pause emits release+pause back-to-back; the release
                    # handler above marks finished — undo it, a paused session is
                    # NOT done and must be eligible for re-admission
                    s["active"] = False
                    s["finished"] = False
                elif etype == "release":
                    s["active"] = False
                    s["finished"] = True

            # 2. completed rounds: ctx + observed growth + TTFTs
            for rec in read_jsonl(args.step_log):
                sid = rec.get("session_id")
                if not sid or sid not in sess:
                    continue
                s = sess[sid]
                ri = rec.get("round_idx")
                pl = rec.get("prompt_len")
                if pl:
                    if s["ctx"] and pl > s["ctx"]:
                        obs = float(pl - s["ctx"])
                        s["ema"] = obs if s["ema"] is None else \
                            args.ema_alpha * obs + (1 - args.ema_alpha) * s["ema"]
                        s["n_obs"] += 1
                        glob_growth_sum += obs
                        glob_growth_n += 1
                    s["ctx"] = max(s["ctx"], int(pl))
                if ri is not None:
                    s["last_round"] = max(s["last_round"], ri)
                ft = rec.get("first_token_ms")
                if ft is not None and rec.get("status") == "SUCCESS":
                    ttfts.append(ft)
            ttfts = deque(sorted(ttfts), maxlen=args.slo_window)

            # 3. spare capacity: high-water floor over retraction dips
            em = engine_metrics(metrics_url)
            usage = em.get("sglang:token_usage", 0.0)
            highwater = max(usage, highwater * args.highwater_decay)
            floor = usage if args.disable_highwater else max(usage, highwater)

            active = [sid for sid, s in sess.items() if s["active"]]
            waiting = sorted(
                (sid for sid, s in sess.items()
                 if s["arrived_ts"] is not None and not s["active"] and not s["finished"]),
                key=lambda sid: sess[sid]["arrived_ts"])
            for sid in waiting:
                sess[sid].setdefault("first_seen", now)
            oldest_wait = max((now - sess[sid].get("first_seen", now) for sid in waiting),
                              default=0.0)

            # 4. projection: engine-truth floor vs observed ctx, plus forecast growth
            resident = floor * args.pool_tokens
            ctx_sum = sum(sess[sid]["ctx"] or sess[sid]["prompt0"] for sid in active)
            growth_sum = sum(forecast(sess[sid]) for sid in active)
            projection = max(resident, ctx_sum) + growth_sum

            # 5. admission decision (single-flight by default: one named permit per cycle)
            valve = usage >= args.hard_stop_usage
            if not args.disable_slo_valve and len(ttfts) >= max(5, args.slo_window // 2):
                valve = valve or sorted(ttfts)[len(ttfts) // 2] > args.slo_ms

            # 5b. SHEDDING: unlike v0.5 (whose cap could only grow — over-admitted
            # sessions stayed forever and the SLO valve was toothless), named permits
            # let us revoke. On valve, pause the YOUNGEST active sessions until the
            # oldest fit inside the budget; paused sessions re-enter via the normal
            # FIFO admission path once the valve clears and the projection has room.
            shed = []
            if valve and active and not args.disable_shedding:
                keep, acc = [], 0.0
                limit = budget * 0.90
                for sid in sorted(active, key=lambda s: sess[s]["arrived_ts"] or 0):
                    c = sess[sid]["ctx"] or sess[sid]["prompt0"]
                    if not keep or acc + c <= limit:
                        keep.append(sid)
                        acc += c
                shed = [sid for sid in active if sid not in set(keep)]
                if shed:
                    for sid in shed:
                        sess[sid]["active"] = False
            prev_started = (last_admitted_sid is None
                            or sess.get(last_admitted_sid, {}).get("last_round", -1) >= 0
                            or now - last_admit_ts > 60)
            candidates = []   # named sessions this cycle authorizes (explicit set —
                              # GPT audit 2: a scalar candidate dropped batch admits)
            need = 0.0
            if waiting and not valve and (prev_started or args.disable_single_flight):
                head = waiting if args.disable_single_flight else waiting[:1]
                for sid in head:
                    s = sess[sid]
                    # resume/shed survivors must be budgeted at their KNOWN current
                    # context, not their original arrival size (GPT audit 2: the
                    # prompt0-based need under-counted paused sessions massively)
                    base = s["ctx"] or s["prompt0"]
                    n = (base + forecast(s)) * args.margin
                    if projection + n <= budget:
                        candidates.append(sid)
                        projection += n
                        if not args.disable_single_flight:
                            break

            # 6. rate-limited starve guard (gated on the floor, not the instant value)
            forced = False
            if (waiting and not candidates and oldest_wait >= args.starve_seconds
                    and floor < 0.5 and now - last_forced_ts >= args.starve_cooldown):
                candidates = [waiting[0]]
                forced = True
                last_forced_ts = now

            # 7. write the full desired permit state (full-state semantics)
            active = [sid for sid in active if sid not in set(shed)]
            admitted_now = set(active) | set(candidates)
            write_permit(args.permit_file, admitted_now, shed)

            log.write(json.dumps({
                "ts": round(now, 3),
                "active_n": len(active), "waiting_n": len(waiting),
                "usage": round(usage, 3), "highwater": round(highwater, 3),
                "resident": round(resident), "ctx_sum": round(ctx_sum),
                "growth_sum": round(growth_sum), "budget": round(budget),
                "candidate": (candidates[0] if candidates else None),
                "n_admitted": len(candidates), "need": round(need), "forced": forced,
                "valve": valve, "shed_n": len(shed),
                "ttft_p50_ms": round(sorted(ttfts)[len(ttfts) // 2]) if ttfts else None,
                "glob_growth_prior": round(glob_growth_sum / glob_growth_n, 1) if glob_growth_n else None,
            }) + "\n")
            log.flush()
            time.sleep(args.interval)
          except Exception as exc:  # a transient fault must skip ONE cycle, not kill
            try:
                log.write(json.dumps({
                    "ts": round(time.time(), 3), "cycle_error": repr(exc),
                }) + "\n")
                log.flush()
            except Exception:
                pass
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
