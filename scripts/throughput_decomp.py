#!/usr/bin/env python3
"""Aggregate decode throughput per run, decomposed into idling vs busy-time rate.

⚠ Its original purpose is RETRACTED. This script was written to verify "wall clock
versus concurrency is a STEP", by re-deriving the claim from aggregate throughput.
That claim has since been withdrawn (see docs/claim_ledger_20260921.md, R2-R4): the
per-request measurement in decode_rate.py shows per-request rate does not rise with
concurrency, so the aggregate gain is parallelism rather than batching, and the wall
clock is expected to be smooth. **The decomposition below is still computed and still
useful descriptively, but do not cite it as evidence for a step, and do not cite the
"busy-tok/s" half as batching** -- that half came from the same faulty counter
differencing as the retracted curve (ledger R8).

The decomposition matters too. A throughput gain at high concurrency can come from
two very different places:

    throughput = (fraction of time the engine is busy) x (tokens per busy second)

The first is just idling less, which any scheduler tweak can do. The second is
batching, which is a property of the serving engine under load. Reporting them
separately stops "we stopped idling" from being sold as "we batched better".

    python3 scripts/throughput_decomp.py [--dir DIR] [--pattern GLOB] [--min-wall MIN]

Run it on the lab (where the results live), not on the laptop.
"""
import argparse
import csv
import glob
import json
import os

DEFAULT_DIR = "/data/xbw/turnstile/results/night"


def read_metrics(path):
    """Return (span_minutes, total_generation_tokens, busy_fraction, mean_running).

    Two bugs fixed here on 2026-09-21, both flagged by an external review and both
    mine:

    1. The samples were collected by appending ts, gen and running to three separate
       lists inside ONE try block. A row missing any single column therefore left the
       first lists one element longer than the last, and every later `zip` paired a
       timestamp with the wrong scrape -- silently, with no error. (I hit this exact
       failure in a throwaway script earlier the same day, fixed it there by
       collecting tuples, and did not notice the durable script still had it.)
       Now a row is parsed into a tuple and appended only if ALL fields parse.

    2. The counter total used max(gen), reasoning that generation_tokens_total returns
       to 0 on restart. max is wrong for that: it returns the largest SINGLE epoch, so
       a run with two restart epochs is undercounted by everything before the last
       reset. It is now summed per monotonic epoch.
    """
    rec = []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            try:
                rec.append((float(row["ts"]),
                            float(row["sglang:generation_tokens_total"]),
                            float(row["sglang:num_running_reqs"])))
            except (ValueError, TypeError, KeyError):
                # A scrape that straddles a server restart can drop columns; the
                # gauges are advisory anyway, so skip the sample rather than the run.
                pass
    if not rec:
        return None
    span = (rec[-1][0] - rec[0][0]) / 60.0
    # Sum each monotonic epoch: the counter resets to 0 on a server restart, so a
    # drop means "new epoch began", not "tokens were un-generated".
    total, prev = 0.0, rec[0][1]
    for _, g, _ in rec[1:]:
        if g >= prev:
            total += g - prev
        else:
            total += g          # new epoch: everything since the reset
        prev = g
    running = [r for _, _, r in rec]
    return span, total, sum(1 for v in running if v > 0) / len(running), \
        sum(running) / len(running)


def collect(root, pattern, min_wall):
    """Complete runs only.

    `summary.json` is written at the very end, so its presence is what separates a
    finished run from one that is still going or was killed. That check is not
    cosmetic: a partial run's metrics.csv has a correct-looking throughput and a
    wall clock of a few minutes, and averaging one of those into a group silently
    moves the group mean. (It happened: cap4_hc at 13 minutes and two abandoned
    *_fixed directories were in the first version of this table.)
    """
    out = []
    for d in sorted(glob.glob(os.path.join(root, pattern))):
        if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "summary.json")):
            continue
        f = os.path.join(d, "metrics.csv")
        if not os.path.exists(f):
            continue
        got = read_metrics(f)
        if got is None:
            continue
        span, gen, busy, conc = got
        if span < min_wall:
            continue
        out.append({
            "name": os.path.basename(d), "wall": span, "gen": gen,
            "tok_s": gen / (span * 60), "busy": busy,
            "tok_s_busy": gen / (span * 60) / busy if busy > 0 else 0.0,
            "conc": conc,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--pattern", default="pois200_*")
    ap.add_argument("--min-wall", type=float, default=60.0,
                    help="drop runs shorter than this many minutes (partials)")
    args = ap.parse_args()

    rows = collect(args.dir, args.pattern, args.min_wall)
    if not rows:
        print("no complete runs matched %s in %s" % (args.pattern, args.dir))
        return 1
    rows.sort(key=lambda r: r["conc"])

    print("%-24s %8s %8s %8s %8s %10s" %
          ("run", "wall_m", "engconc", "tok/s", "busy%", "tok/s@busy"))
    for r in rows:
        print("%-24s %8.1f %8.2f %8.1f %7.1f%% %10.1f" %
              (r["name"], r["wall"], r["conc"], r["tok_s"],
               100 * r["busy"], r["tok_s_busy"]))

    # Load check: every run replays the same trace, so the total work must be equal.
    # If it is not, `tok/s` is comparing different amounts of work and every ratio
    # below is meaningless. Do this BEFORE any interpretation.
    gens = [r["gen"] for r in rows]
    spread = (max(gens) - min(gens)) / (sum(gens) / len(gens))
    print("\ntotal generation tokens: %.0f .. %.0f  (spread %.2f%%)" %
          (min(gens), max(gens), 100 * spread))
    if spread > 0.05:
        print("  !! spread > 5%% — tok/s is NOT comparable across these runs; "
              "the traces or the session counts differ. Stop and check.")
        return 1

    print("\ndecomposition (throughput = busy_fraction x tokens_per_busy_second)")
    for lbl, sel in (("all", lambda r: True),
                     ("without cap1 (a conc-0.64 outlier)", lambda r: "cap1" not in r["name"])):
        sub = [r for r in rows if sel(r)]
        lo = [r for r in sub if r["conc"] < 1.40]
        hi = [r for r in sub if r["conc"] >= 1.40]
        if not lo or not hi:
            continue
        m = lambda g, k: sum(r[k] for r in g) / len(g)
        tl, th = m(lo, "tok_s"), m(hi, "tok_s")
        bl, bh = m(lo, "busy"), m(hi, "busy")
        jl, jh = m(lo, "tok_s_busy"), m(hi, "tok_s_busy")
        print("\n  [%s]" % lbl)
        print("    eng conc <  1.40  n=%d  %.1f tok/s  busy %.1f%%  busy-tok/s %.1f"
              % (len(lo), tl, 100 * bl, jl))
        print("    eng conc >= 1.40  n=%d  %.1f tok/s  busy %.1f%%  busy-tok/s %.1f"
              % (len(hi), th, 100 * bh, jh))
        print("    ratio tok/s %.2fx  =  busy %.2fx  x  busy-tok/s %.2fx"
              % (th / tl, bh / bl, jh / jl))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
