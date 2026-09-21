#!/usr/bin/env python3
"""Foyer controller: capacity-accounted admission with the KV pool as a GUARDRAIL.

Why this exists (measured, 2026-09-20, Poisson 200-session workload)
-------------------------------------------------------------------
v3 asked a FEASIBILITY question on every admission — "does the worst-case projected
working set fit the budget?" — and it answered with three stacked pessimisms:

    projection = max(engine_truth, sharing_blind_logical_sum)   # drops sharing gains
               + growth reserve for EVERY resident session      # mean, over 3 rounds
    admit if projection + newcomer * 1.15 <= target_util * pool

Instrumenting that live showed the controller believed it sat at 92% of budget
(p90: 157%) while the engine actually held 52% of the pool. Admission therefore
almost never fired — 98% of decision cycles admitted nobody — and concurrency
pinned near 2. A static cap-3/4, running ~3.5x the concurrency, finished the same
workload ~15% faster (259min vs 299min). The cost of that pessimism was the
primary metric.

This version inverts the framing: memory is not the objective, it is a red line.
  base          the engine's OWN sglang:token_usage (sharing-aware, measured, not
                modelled) — this is what makes prefix sharing count in our favour
  pending       sessions admitted but not yet visible in that number, so a burst of
                admits cannot outrun the measurement
  reserve       what the resident set will add before the next decision, scaled by
                --growth-scale (0 disables it entirely)
  red line      --target-util * pool_tokens, and this is THE knob: 0.75 reproduces
                the old conservatism, 0.95 runs deliberately near the edge

Everything else — named permits, hard usage valve, TTFT-SLO valve, shedding,
rate-limited starve guard — is carried over from v3 unchanged. Those are the safety
net this design deliberately leans on rather than a policy it hides behind.

Reads NO trace file. Every quantity is observed at runtime.
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


def replay_admissions(path):
    """Rebuild (active, finished, arrived) for every session from scratch.

    This is the controller's own rule set applied to the whole log, with no
    incremental state carried in. It exists to be COMPARED against the live dict.

    Why it is needed: on 2026-09-21 a run stalled for 29 minutes at 894/999 with
    the controller reporting waiting_n=0 while this function, over the same file,
    returned 21 waiting sessions. Restarting the controller resumed the run
    immediately, and the mechanism was never found -- because there was nothing to
    find it with. read_jsonl re-reads the whole file each cycle and applying an
    event is a plain assignment, so by construction the two cannot disagree. They
    did. Without a periodic comparison the next occurrence is equally invisible.
    """
    st = {}
    for ev in read_jsonl(path):
        sid = ev.get("session_id")
        if not sid:
            continue
        s = st.setdefault(sid, [None, False, False])   # arrived, active, finished
        e = ev.get("event")
        if e == "queued":
            if s[0] is None:
                s[0] = ev.get("ts")
        elif e == "admit":
            s[1] = True
        elif e == "resume":
            # The live handler sets active=True here, so the replay must too.
            # Leaving this out was my bug, not the controller's: the first run of
            # the self-check reported mismatches for exactly the sessions that had
            # been resumed. An earlier ad-hoc replay used to diagnose the 29-minute
            # stall had the same omission, so that diagnosis is not trustworthy
            # either and is being redone against the same log.
            s[1] = True
        elif e == "pause":
            s[1] = False
            s[2] = False
        elif e == "release":
            s[1] = False
            s[2] = True
    return st


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


def build_growth_traj(trace_path):
    """{session_id: {round_idx: prompt_len}} from the trace (oracle ablation arm only).

    prompt_len is the whole context the engine must hold at that round
    (prefix_len + input_len in the runner's step records), i.e. the C(r) the
    admission accounting reasons about.
    """
    import csv as _csv
    traj = {}
    for row in _csv.DictReader(open(trace_path)):
        traj.setdefault(row["session_id"], {})[int(row["round_idx"])] = \
            int(row["prefix_len"]) + int(row["input_len"])
    return traj


def oracle_forecast(traj, sid, last_round, horizon_rounds):
    """CLAIRVOYANT arm: G*(t) = max(0, C(t+h) - C(t)), t = last COMPLETED round.

    Anchoring at the completed round is what makes this the exact answer to the
    question the other arms estimate: ctx already covers round t, so
    ctx + G* = C(t+h) for every arm. Not deployable (reads the trace's future).
    """
    rounds = traj.get(sid)
    if not rounds:
        return 0.0
    keys = sorted(rounds)
    a = last_round if last_round >= 0 else 0
    a = max(k for k in keys if k <= a) if a >= keys[0] else keys[0]
    ahead = [k for k in keys if a < k <= a + horizon_rounds]
    if not ahead:
        return 0.0
    return float(max(0, rounds[ahead[-1]] - rounds[a]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--permit-file", required=True)
    ap.add_argument("--admission-log", required=True)
    ap.add_argument("--step-log", required=True)
    ap.add_argument("--decision-log", required=True)
    ap.add_argument("--pool-tokens", type=int, required=True)
    ap.add_argument("--metrics-port", type=int, default=30000)

    # ---- the one knob -------------------------------------------------------
    ap.add_argument("--target-util", type=float, default=0.90,
                    help="RED LINE: stop admitting at this fraction of the KV pool. "
                         "0.75 = the old v3 conservatism, 0.90 = default, 0.95+ = "
                         "deliberately near the edge. This is the aggressiveness knob.")

    # ---- how much of the pessimistic machinery to keep ----------------------
    ap.add_argument("--growth-scale", type=float, default=0.35,
                    help="multiplier on the growth reserve. The reserve is what v3 "
                         "used to hold every resident session against its mean "
                         "round-over-round growth for --horizon-rounds. 0 disables it.")
    ap.add_argument("--margin", type=float, default=1.0,
                    help="padding on the NEWCOMER's arrival context only (v3 used 1.15)")
    ap.add_argument("--horizon-rounds", type=int, default=3)
    ap.add_argument("--ema-alpha", type=float, default=0.4)
    ap.add_argument("--young-blend", type=float, default=0.5)

    # ---- safety net (unchanged from v3) -------------------------------------
    ap.add_argument("--hard-stop-usage", type=float, default=0.93,
                    help="valve: stop admitting outright above this measured usage")
    ap.add_argument("--highwater-decay", type=float, default=0.98,
                    help="fast decay (~70s half-life at a 2s cycle): guards against "
                         "retraction dips faking slack, without holding a peak for "
                         "minutes the way v3's 0.995 did (that cost 29%% of budget)")
    ap.add_argument("--slo-ms", type=float, default=10000.0)
    ap.add_argument("--slo-window", type=int, default=20)
    ap.add_argument("--starve-seconds", type=float, default=240.0)
    ap.add_argument("--starve-cooldown", type=float, default=300.0)
    ap.add_argument("--prefill-tok-s", type=float, default=1500.0,
                    help="measured prefill rate, used to decide when a permitted session "
                         "has actually landed in the engine (see the pending note). "
                         "pois200 measurements: ~2500 tok/s up to 20k, degrading to "
                         "~1700 tok/s at 30k, ~924 tok/s fitted overall.")
    ap.add_argument("--pending-floor-s", type=float, default=6.0,
                    help="never release a pending charge sooner than this")
    ap.add_argument("--pending-ceiling-s", type=float, default=120.0,
                    help="release a pending charge after this even if the estimate said "
                         "longer — a session that never prefilled must not occupy the "
                         "accounting forever")
    ap.add_argument("--pause-confirm-s", type=float, default=90.0,
                    help="keep charging a shed session's capacity until the runner "
                         "ACKNOWLEDGES the pause (it finishes its current round first)")
    ap.add_argument("--candidate-window", type=int, default=8,
                    help="how many waiting sessions to consider for admission, oldest "
                         "first. 1 reproduces the old head-of-line-blocking behaviour.")
    ap.add_argument("--selfcheck-every", type=int, default=300,
                    help="replay the admission log from zero every N cycles and "
                         "compare against the live state; 0 disables")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--max-minutes", type=float, default=300.0)

    ap.add_argument("--disable-highwater", action="store_true")
    ap.add_argument("--disable-single-flight", action="store_true")
    ap.add_argument("--disable-slo-valve", action="store_true")
    ap.add_argument("--disable-starve-guard", action="store_true")
    ap.add_argument("--disable-shedding", action="store_true")
    ap.add_argument("--ttft-freshness-s", type=float, default=600.0)
    ap.add_argument("--predictor", choices=["ema", "zero", "global", "oracle"],
                    default="ema")
    ap.add_argument("--trace", default=None)
    args = ap.parse_args()

    traj = {}
    if args.predictor == "oracle":
        if not args.trace:
            ap.error("--predictor oracle requires --trace (ablation-only arm)")
        traj = build_growth_traj(args.trace)

    red_line = args.pool_tokens * args.target_util
    sess = {}          # sid -> dict(arrived_ts, prompt0, active, finished, ctx, ema, n_obs)
    pending = {}       # sid -> (admit_ts, tokens, clear_at) permitted, not yet in the engine
    pausing = {}       # sid -> (shed_ts, tokens) shed, runner has not acknowledged yet
    highwater = 0.0
    ttfts = deque(maxlen=args.slo_window)
    glob_growth_sum = 0.0
    glob_growth_n = 0
    last_admitted_sid = None
    last_admit_ts = 0.0
    last_forced_ts = 0.0
    deadline = time.time() + args.max_minutes * 60

    def forecast(s):
        """Forecast context growth over the next horizon rounds (tokens)."""
        if args.predictor == "oracle":
            return oracle_forecast(traj, s["sid"], s["last_round"], args.horizon_rounds)
        if args.predictor == "zero":
            return 0.0
        if args.predictor == "global":
            prior = glob_growth_sum / glob_growth_n if glob_growth_n else 0.0
            return prior * args.horizon_rounds
        if s["ema"] is not None:
            est = s["ema"]
            if s["n_obs"] < 3:
                prior = glob_growth_sum / glob_growth_n if glob_growth_n else est
                est = args.young_blend * est + (1 - args.young_blend) * prior
            return est * args.horizon_rounds
        prior = glob_growth_sum / glob_growth_n if glob_growth_n else 0.0
        return prior * args.horizon_rounds

    import re
    import urllib.request
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
        cycle = 0
        while time.time() < deadline:
          try:
            cycle += 1
            now = time.time()

            # 1. arrivals / admission events
            for ev in read_jsonl(args.admission_log):
                sid = ev.get("session_id")
                if not sid:
                    continue
                s = sess.setdefault(sid, dict(sid=sid, arrived_ts=None, prompt0=0,
                                              active=False, finished=False, ctx=0,
                                              last_round=-1, ema=None, n_obs=0))
                etype = ev.get("event")
                if etype == "queued":
                    if s["arrived_ts"] is None:
                        s["arrived_ts"] = ev.get("ts", now)
                    s["prompt0"] = int(ev.get("prompt_tokens") or 0)
                elif etype == "admit":
                    s["active"] = True
                    if ev.get("prompt_tokens"):
                        s["prompt0"] = int(ev["prompt_tokens"])
                    # The engine has not prefilled it yet, so token_usage cannot see
                    # it — carry it explicitly. But only until the engine actually
                    # takes it: prefill starts ~prompt0/prefill_rate seconds after the
                    # permit, at which point the KV is allocated and token_usage
                    # counts it. The previous version held the charge until the first
                    # round COMPLETED, which is prefill PLUS a full decode — so the
                    # session was counted twice for the length of its first round.
                    # That is what pinned rl90's ledger at 100% while the engine sat
                    # at 64%, and it is why the extra concurrency bought nothing.
                    hold = min(max((s["ctx"] or s["prompt0"]) / max(1.0, args.prefill_tok_s),
                                   args.pending_floor_s),
                               args.pending_ceiling_s)
                    pending[sid] = (ev.get("ts", now), s["ctx"] or s["prompt0"],
                                    ev.get("ts", now) + hold)
                    last_admitted_sid = sid
                    last_admit_ts = ev.get("ts", now)
                elif etype == "resume":
                    s["active"] = True
                    hold = min(max((s["ctx"] or s["prompt0"]) / max(1.0, args.prefill_tok_s),
                                   args.pending_floor_s),
                               args.pending_ceiling_s)
                    pending[sid] = (ev.get("ts", now), s["ctx"] or s["prompt0"],
                                    ev.get("ts", now) + hold)
                elif etype == "pause":
                    # a shed pause emits release+pause back-to-back; the release
                    # handler marks finished — undo it, a paused session is NOT done
                    s["active"] = False
                    s["finished"] = False
                    pending.pop(sid, None)
                    pausing.pop(sid, None)   # the runner has now acted on the shed
                elif etype == "release":
                    s["active"] = False
                    s["finished"] = True
                    pending.pop(sid, None)

            # 2. completed rounds: ctx + observed growth + TTFTs
            for rec in read_jsonl(args.step_log):
                sid = rec.get("session_id")
                if not sid or sid not in sess:
                    continue
                s = sess[sid]
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
                    # the engine has now actually materialised this session
                    pending.pop(sid, None)
                ri = rec.get("round_idx")
                if ri is not None:
                    s["last_round"] = max(s["last_round"], ri)
                ft = rec.get("first_token_ms")
                if ft is not None and rec.get("status") == "SUCCESS":
                    ttfts.append((rec.get("complete_timestamp") or now, ft))
            ttfts = deque([(t, v) for (t, v) in ttfts
                           if t > now - args.ttft_freshness_s], maxlen=args.slo_window)

            # 3. the base: engine truth, sharing-aware, dip-guarded
            em = engine_metrics(metrics_url)
            usage = em.get("sglang:token_usage", 0.0)
            highwater = max(usage, highwater * args.highwater_decay)
            floor = usage if args.disable_highwater else max(usage, highwater)
            measured = floor * args.pool_tokens

            # 4. what the engine cannot see yet, and what the residents will add
            for sid in [s for s, v in pending.items() if now >= v[2]]:
                pending.pop(sid, None)
            pending_tokens = sum(v[1] for v in pending.values())
            # A shed session keeps occupying capacity until the runner ACKNOWLEDGES:
            # it runs its current round to completion first. Removing it from `active`
            # the moment we ask lets the controller admit a replacement against memory
            # that is not free yet — planned state and executed state diverge.
            for sid in [s for s, v in pausing.items()
                        if now - v[0] > args.pause_confirm_s]:
                pausing.pop(sid, None)
            # Charged for LOGGING only -- deliberately NOT added to `committed`.
            #
            # Measured on pois200_foyer_rl90fix (2026-09-21), while it was running:
            # measured 97,180 + pausing 15,700 = 112,880 against a pool of 101,432.
            # The engine cannot be holding more non-reclaimable KV than the pool
            # exists, so `measured` -- which is the engine's own token_usage -- already
            # contains the session we asked to pause. It is still running its current
            # round; the runner pauses it only when that round completes. Adding its
            # capacity again charges the same memory twice, and the effect was not
            # subtle: committed sat at 120-132k against a 91,289 red line, so the
            # controller could not admit anything for most cycles.
            #
            # The mechanism this was meant to fix is real -- an earlier version dropped
            # a shed session from `active` immediately and then admitted against memory
            # that was still occupied. But the fix for that is not a second charge on
            # top of telemetry; telemetry already tells the truth here. What must not
            # happen is the opposite: removing it from the GROWTH RESERVE, which is
            # still correct (we should not forecast growth for a session on its way
            # out), and that is handled by `active` excluding it.
            pausing_tokens = sum(v[1] for v in pausing.values())

            active = [sid for sid, s in sess.items() if s["active"]]
            waiting = sorted(
                (sid for sid, s in sess.items()
                 if s["arrived_ts"] is not None and not s["active"] and not s["finished"]),
                key=lambda sid: sess[sid]["arrived_ts"])
            for sid in waiting:
                sess[sid].setdefault("first_seen", now)
            oldest_wait = max((now - sess[sid].get("first_seen", now) for sid in waiting),
                              default=0.0)

            growth_reserve = args.growth_scale * sum(forecast(sess[sid]) for sid in active)
            committed = measured + pending_tokens + growth_reserve

            # 5. admission decision
            valve = usage >= args.hard_stop_usage
            fresh_vals = sorted(v for _, v in ttfts)
            if not args.disable_slo_valve and len(fresh_vals) >= max(5, args.slo_window // 2):
                valve = valve or fresh_vals[len(fresh_vals) // 2] > args.slo_ms

            # 5b. SHEDDING: on valve, pause the YOUNGEST active sessions until the
            # oldest fit inside the red line; paused sessions re-enter via the
            # normal FIFO path once the valve clears and there is room again.
            shed = []
            if valve and active and not args.disable_shedding:
                keep, acc = [], 0.0
                limit = red_line * 0.90
                for sid in sorted(active, key=lambda s: sess[s]["arrived_ts"] or 0):
                    c = sess[sid]["ctx"] or sess[sid]["prompt0"]
                    if not keep or acc + c <= limit:
                        keep.append(sid)
                        acc += c
                shed = [sid for sid in active if sid not in set(keep)]
                if shed:
                    for sid in shed:
                        sess[sid]["active"] = False
                        # keep charging until the pause event comes back
                        pausing[sid] = (now, sess[sid]["ctx"] or sess[sid]["prompt0"])

            # "started" means the ENGINE HAS TAKEN IT, i.e. it is no longer pending.
            # The old test was `last_round >= 0` — a COMPLETED first round, which is
            # prefill plus a full decode, so a fresh admission blocked the next one for
            # tens of seconds while the budget had room. The name was the only thing
            # that said "started".
            prev_started = (last_admitted_sid is None
                            or last_admitted_sid not in pending
                            or now - last_admit_ts > args.pending_ceiling_s)
            candidates = []
            bypassed = 0   # initialised here, not in the branch: the log line below
                           # reads it unconditionally, and scoping it inside the
                           # `if waiting` block made every idle cycle raise
                           # UnboundLocalError, which the per-cycle handler swallowed
                           # into a cycle_error row (caught by the smoke test)
            if waiting and not valve and (prev_started or args.disable_single_flight):
                head = (waiting if args.disable_single_flight
                        else waiting[:max(1, args.candidate_window)])
                for sid in head:
                    s = sess[sid]
                    # a resumed/shed survivor is budgeted at its KNOWN current
                    # context, not its original arrival size
                    base = s["ctx"] or s["prompt0"]
                    n = base * args.margin
                    if committed + n <= red_line:
                        if candidates:
                            bypassed += 1
                        candidates.append(sid)
                        committed += n
                        if not args.disable_single_flight:
                            break
                    else:
                        # Contexts here run from ~19k to ~89k, so a large head that
                        # does not fit used to block every smaller session behind it.
                        # Skipping is bounded by --candidate-window and the rate-limited
                        # starve guard still forces the oldest in eventually.
                        bypassed += 1

            # 6. rate-limited starve guard — gated on the measured base, not the
            # instantaneous value, so a retraction dip cannot force-admit
            forced = False
            if (waiting and not candidates and not args.disable_starve_guard
                    and oldest_wait >= args.starve_seconds
                    and floor < 0.5 and now - last_forced_ts >= args.starve_cooldown):
                candidates = [waiting[0]]
                forced = True
                last_forced_ts = now

            # 7. write the full desired permit state (full-state semantics)
            active = [sid for sid in active if sid not in set(shed)]
            admitted_now = set(active) | set(candidates)
            write_permit(args.permit_file, admitted_now, shed)

            # 8. Q1: the resource decomposition, sampled at THIS instant.
            #
            # Why here and not in monitor.py. The question the paper turns on is
            # whether a session-level logical account and the engine's physical
            # occupancy are the same quantity. Answering it needs five things read
            # at ONE instant over ONE session set: the logical sum, the engine's
            # locked tokens, what is reclaimable, what sits in the host tier, and
            # what is promised but not yet materialised. monitor.py scrapes on its
            # own 5s clock and cannot see the session set at all; the controller
            # already holds both halves and already fetches this endpoint every
            # cycle. `em` carries EVERY gauge the engine exposes -- until now only
            # token_usage was read out of it and the rest were discarded.
            #
            # `ctx_sum` is the sharing-blind logical sum: each resident session
            # charged its own full context, with no credit for shared prefixes.
            # That is deliberately the naive quantity -- it is what a session
            # ledger would compute, and the gap between it and the engine's number
            # is the thing under investigation, not an error to be corrected here.
            # A session that has been admitted but has not run yet has ctx 0, so
            # fall back to its arrival size, matching the admission path.
            #
            # These gauges go STALE WHEN THE ENGINE IS IDLE -- full_token_usage in
            # particular stops updating rather than falling to zero (measured
            # 2026-09-21, ledger section 8). The controller samples continuously,
            # including under load, which is exactly when the readings are valid,
            # so this log is a better source for them than the monitor's.
            resident = [s for s in sess.values() if s["active"]]
            ctx_sum = sum((s["ctx"] or s["prompt0"]) for s in resident)
            res = {
                # fractions of the pool, as the endpoint reports them; multiply by
                # pool_tokens to compare against `measured`, which is already tokens
                "full": em.get("sglang:full_token_usage"),
                "swa": em.get("sglang:swa_token_usage"),
                "pp": em.get("sglang:pending_prealloc_token_usage"),
                "hh": em.get("sglang:hicache_host_used_tokens"),
                "ht": em.get("sglang:hicache_host_total_tokens"),
                "run": em.get("sglang:num_running_reqs"),
                "q": em.get("sglang:num_queue_reqs"),
                "paused": em.get("sglang:num_paused_reqs"),
                "retr": em.get("sglang:num_retracted_reqs"),
                "evict": em.get("sglang:evicted_tokens_total"),
            }

            # Self-check: every N cycles, rebuild the state from the log alone and
            # compare. A mismatch is a real bug and must be visible -- the one on
            # 2026-09-21 was found only because a run happened to stall where a
            # human noticed. Logged, never corrected: silently repairing it would
            # destroy the evidence of how it drifted.
            mismatch = None
            if args.selfcheck_every and cycle % args.selfcheck_every == 0:
                fresh = replay_admissions(args.admission_log)
                bad = []
                for sid, (arr, act, fin) in fresh.items():
                    s_ = sess.get(sid)
                    if s_ is None:
                        bad.append((sid, "absent-from-live"))
                    elif bool(s_["active"]) != act or bool(s_["finished"]) != fin:
                        bad.append((sid, "live a=%s f=%s / replay a=%s f=%s"
                                    % (s_["active"], s_["finished"], act, fin)))
                for sid, s_ in sess.items():
                    if sid not in fresh:
                        bad.append((sid, "absent-from-replay"))
                if bad:
                    mismatch = {"n": len(bad), "sample": bad[:5],
                                "live_waiting": len(waiting),
                                "replay_waiting": sum(
                                    1 for a, ac, f in fresh.values()
                                    if a is not None and not ac and not f)}
                    log.write(json.dumps({"ts": round(now, 3),
                                          "selfcheck_mismatch": mismatch}) + "\n")

            log.write(json.dumps({
                "ts": round(now, 3),
                "active_n": len(active), "waiting_n": len(waiting),
                "usage": round(usage, 3), "highwater": round(highwater, 3),
                "measured": round(measured), "pending": round(pending_tokens),
                "pending_n": len(pending), "growth_reserve": round(growth_reserve),
                "committed": round(committed), "red_line": round(red_line),
                "fill": round(committed / red_line, 3) if red_line else None,
                "candidate": (candidates[0] if candidates else None),
                "bypassed": bypassed, "pausing": round(pausing_tokens),
                "n_admitted": len(candidates), "forced": forced,
                "valve": valve, "shed_n": len(shed),
                "ttft_p50_ms": round(fresh_vals[len(fresh_vals) // 2]) if fresh_vals else None,
                "glob_growth_prior": round(glob_growth_sum / glob_growth_n, 1) if glob_growth_n else None,
                # Q1 (see step 8). ctx_sum is the logical account, measured is the
                # engine's, and `res` is everything else the engine will admit to.
                "ctx_sum": ctx_sum, "resident_n": len(resident),
                "res": {k: (round(v, 6) if isinstance(v, float) else v)
                        for k, v in res.items()},
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
