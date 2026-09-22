#!/usr/bin/env python3
"""How much of each run overlapped a host-contention window.

Why this is a script and not a column in runs_registry.md: that file is
auto-generated, so a hand-added column disappears on the next rebuild. The
inputs here -- load.log and each run's metadata.json -- both persist, so the
annotation can be regenerated at any time, including by whatever rebuilds the
tables.

It reports an OVERLAP FRACTION and deliberately NOT a correction. The size of
the effect is not known: the 17-25% figure that used to be quoted here was
measured with step rate, which turns out to track prompt length rather than CPU
contention, and on 2026-09-21 a 46-core window of the same kind produced the
opposite sign on the same instrument (ledger section 11). So a run at 20%
overlap is not "20% of the way to being 17-25% wrong"; it is a run that spent
20% of its wall clock under a condition we cannot currently quantify.

    load_overlap.py [--log PATH] [--results DIR] [--threshold CORES]

Run on the lab, where results/night and load.log live.
"""
import argparse
import glob
import json
import os
import time

DEFAULT_LOG = "/data/xbw/turnstile/results/night/load.log"
DEFAULT_RESULTS = "/data/xbw/turnstile/results/night"


def read_windows(path, threshold):
    """Contiguous stretches where other-user cores stayed above `threshold`.

    Samples are ~2 min apart (one per watcher poll). A window opens on the first
    sample at or above the threshold and closes on the first sample strictly
    below it -- the closing sample is when we OBSERVED it end, so the true end is
    somewhere in the preceding interval. Windows shorter than one sample interval
    are kept: a single 40-core reading is a real event even if we only caught one.
    """
    pts = []
    with open(path) as fh:
        for line in fh:
            f = line.split()
            if len(f) >= 3:
                try:
                    pts.append((float(f[0]), float(f[1]), float(f[2])))
                except ValueError:
                    pass
    pts.sort()
    out = []
    start = peak = None
    for ts, other, _us in pts:
        if other >= threshold:
            if start is None:
                start, peak = ts, other
            peak = max(peak, other)
        elif start is not None:
            out.append((start, ts, peak))
            start = peak = None
    if start is not None:                       # still open at the last sample
        out.append((start, pts[-1][0], peak))
    return out


def step_count(d):
    p = os.path.join(d, "steps.jsonl")
    if not os.path.exists(p):
        return 0
    n = 0
    with open(p) as fh:
        for _ in fh:
            n += 1
    return n


def run_span(d):
    """(start_epoch, end_epoch) for a run, from metadata.json and its artifacts.

    metadata.json carries `started` and `wall_s`, but wall_s is None for a run
    that was killed before it could be written -- and killed runs are exactly the
    ones we most want to place. Fall back to the first and last timestamp in the
    decision log / step log, which exist as soon as the run starts.
    """
    meta = os.path.join(d, "metadata.json")
    if not os.path.exists(meta):
        return None
    try:
        with open(meta) as fh:
            m = json.load(fh)
    except ValueError:
        return None
    t0 = m.get("started")
    if t0 is None:
        return None
    if m.get("wall_s"):
        return t0, t0 + m["wall_s"]
    # Killed run: the last event we have is the best available end.
    last = t0
    for name in ("steps.jsonl", "controller.jsonl", "metrics.csv"):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            continue
        try:
            if name.endswith(".csv"):
                with open(p) as fh:
                    rows = fh.read().strip().splitlines()
                v = float(rows[-1].split(",")[0]) if len(rows) > 1 else None
            else:
                with open(p) as fh:
                    tail = fh.readlines()[-1]
                j = json.loads(tail)
                v = j.get("complete_timestamp") or j.get("ts")
            if v:
                last = max(last, float(v))
        except Exception:
            pass
    return t0, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--results", default=DEFAULT_RESULTS)
    ap.add_argument("--threshold", type=float, default=20.0,
                    help="other-user cores at or above this opens a window")
    ap.add_argument("--min-steps", type=int, default=100,
                    help="a run without summary.json needs at least this many steps "
                         "to be considered real rather than an abandoned directory")
    args = ap.parse_args()

    if not os.path.exists(args.log):
        print("no %s -- the watcher writes it; nothing to annotate" % args.log)
        return 0

    wins = read_windows(args.log, args.threshold)
    if not wins:
        print("no window at or above %.0f other-user cores in %s"
              % (args.threshold, args.log))
        return 0

    print("host-contention windows (>= %.0f cores held by other users):" % args.threshold)
    total = 0.0
    for t0, t1, peak in wins:
        dur = (t1 - t0) / 60.0
        total += dur
        print("  %s -> %s  (%.0f min, peak %.1f cores)"
              % (time.strftime("%m-%d %H:%M", time.localtime(t0)),
                 time.strftime("%H:%M", time.localtime(t1)), dur, peak))
    print("  total %.0f min\n" % total)

    print("%-24s %-16s %9s %9s  %s" %
          ("run", "started", "wall(min)", "overlap", "note"))
    rows = []
    for d in sorted(glob.glob(os.path.join(args.results, "*"))):
        if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "metadata.json")):
            continue
        # Abandoned directories otherwise get annotated with a bogus span: they
        # hold a metadata.json with a `started`, so run_span falls back to their
        # last artifact, which never advanced past the first few steps. Two of
        # them (cap3_fixed, cap4_fixed at 21-22 steps) were reported at 13% overlap
        # before this guard existed. A real run of this trace commits 999.
        if not os.path.exists(os.path.join(d, "summary.json")) and \
                step_count(d) < args.min_steps:
            continue
        span = run_span(d)
        if span is None:
            continue
        t0, t1 = span
        wall = (t1 - t0) / 60.0
        if wall <= 0:
            continue
        ov = sum(max(0.0, min(t1, w1) - max(t0, w0)) for w0, w1, _ in wins) / 60.0
        frac = ov / wall
        rows.append((frac, os.path.basename(d), t0, wall, ov))
    rows.sort(reverse=True)
    for frac, name, t0, wall, ov in rows:
        if ov <= 0:
            continue
        note = ""
        if frac >= 0.25:
            note = "** 墙钟须标注，勿跨天比"
        elif frac >= 0.05:
            note = "有重叠"
        print("%-24s %-16s %9.1f %8.1f%%  %s" %
              (name, time.strftime("%m-%d %H:%M", time.localtime(t0)),
               wall, 100 * frac, note))
    print("\n(overlap is a fraction of wall clock, NOT a correction -- the effect"
          " size is unmeasured; see docs/claim_register_20260921.md section 11)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
