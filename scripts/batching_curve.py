#!/usr/bin/env python3
"""Instantaneous decode rate as a function of instantaneous concurrency, WITHIN a run.

Why this is the strong version of the argument. The between-run comparison in
throughput_decomp.py splits 14 policies into two groups by mean engine concurrency
and compares group means — which is confounded, because the two groups are also
different policies (the high group is mostly static caps, the low group is mostly
Foyer). It cannot separate "more concurrent sequences decode faster" from "static
caps are different in some other way".

This does separate them. Each 5-second scrape gives an interval; pair the tokens
generated during that interval with the concurrency observed at its start. Both
numbers come from the SAME run, the SAME policy, the SAME server. If the rate rises
with concurrency here, batching is demonstrated rather than inferred.

It also gives the mechanism for the aggregate gap: the per-concurrency rate curve
turns out to be essentially policy-independent, so a run's aggregate throughput is
just its concurrency DISTRIBUTION convolved with that one shared curve.

    batching_curve.py [--dir DIR] [--runs r1,r2,...] [--out PNG]
"""
import argparse
import collections
import csv
import os
import sys

DEFAULT_DIR = "/data/xbw/turnstile/results/night"
DEFAULT_RUNS = ["pois200_cap2", "pois200_foyer", "pois200_foyer_t85",
                "pois200_cap4", "pois200_foyer_rl90", "pois200_foyer_rl99"]
# n=0 is dropped: with nothing running the engine still emits a token or two when a
# request finishes, which reads as ~1 tok/s and would drag the axis to zero.
MIN_SAMPLES = 20
MAX_CONC = 6


def curve(path):
    ts, gen, run = [], [], []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            try:
                ts.append(float(row["ts"]))
                gen.append(float(row["sglang:generation_tokens_total"]))
                run.append(float(row["sglang:num_running_reqs"]))
            except (ValueError, TypeError, KeyError):
                pass
    acc = collections.defaultdict(list)
    for i in range(len(ts) - 1):
        dt = ts[i + 1] - ts[i]
        if dt <= 0 or dt > 30:
            continue
        dg = gen[i + 1] - gen[i]
        if dg < 0:                      # counter reset (server restart)
            continue
        acc[int(round(run[i]))].append(dg / dt)
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--runs", default=",".join(DEFAULT_RUNS))
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    curves = {}
    for name in args.runs.split(","):
        p = os.path.join(args.dir, name, "metrics.csv")
        if not os.path.exists(p):
            print("skip %s (no metrics.csv)" % name)
            continue
        c = curve(p)
        if c:
            curves[name] = c

    print("瞬时解码速率 (tok/s) vs 瞬时引擎并发 —— 每个 run 内部配对\n")
    header = "%-24s" % "run"
    for k in range(1, MAX_CONC + 1):
        header += " %10s" % ("n=%d" % k)
    print(header)
    for name, acc in curves.items():
        line = "%-24s" % name
        for k in range(1, MAX_CONC + 1):
            v = acc.get(k) or []
            line += " %10s" % ("%.1f" % (sum(v) / len(v)) if len(v) >= MIN_SAMPLES else "-")
        print(line)

    # How the curve is shared: at each concurrency, the spread across policies.
    print("\n跨策略一致性（同一并发下各 run 的速率）")
    for k in range(1, MAX_CONC + 1):
        vals = [(sum(acc[k]) / len(acc[k]), n) for n, acc in curves.items()
                if acc.get(k) and len(acc[k]) >= MIN_SAMPLES]
        if len(vals) < 2:
            continue
        lo, hi = min(vals), max(vals)
        mean = sum(v for v, _ in vals) / len(vals)
        print("  n=%d  %d runs  mean %.1f  range %.1f (%s) .. %.1f (%s)  spread %.0f%%"
              % (k, len(vals), mean, lo[0], lo[1], hi[0], hi[1],
                 100 * (hi[0] - lo[0]) / mean))

    print("\n并发分布（各 run 花在 n 上的采样占比）")
    for name, acc in curves.items():
        tot = sum(len(v) for k, v in acc.items() if 0 < k <= MAX_CONC)
        if not tot:
            continue
        parts = []
        for k in range(1, MAX_CONC + 1):
            v = acc.get(k) or []
            if len(v) >= MIN_SAMPLES:
                parts.append("n=%d %4.0f%%" % (k, 100.0 * len(v) / tot))
        print("  %-24s %s" % (name, "  ".join(parts)))

    if not args.out:
        return 0
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(no matplotlib: table only)")
        return 0

    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    colours = ["#1f77b4", "#2ca02c", "#8c564b", "#d62728", "#9467bd", "#ff7f0e"]
    for (name, acc), col in zip(curves.items(), colours):
        xs = [k for k in range(1, MAX_CONC + 1)
              if acc.get(k) and len(acc[k]) >= MIN_SAMPLES]
        ys = [sum(acc[k]) / len(acc[k]) for k in xs]
        ax.plot(xs, ys, "o-", color=col, label=name, lw=1.8, ms=6)
    ax.set_xlabel("瞬时引擎并发  num_running_reqs")
    ax.set_ylabel("瞬时解码速率 (tok/s)")
    ax.set_title("批处理：更并发的序列在同一时刻解码更快\n（同一 run 内配对，无跨策略混淆）",
                 fontsize=11)
    ax.grid(True, color="#e8e6e0", lw=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(args.out)
    print("\nwrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
