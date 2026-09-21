#!/usr/bin/env python3
"""Validate a matched pair, then report the paired difference.

The matched-pair experiment (see lane_pairA_*.sh) exists because the headline
comparison was two runs measured five days apart on a shared box, and a neighbour's
job can move our wall clock 17-25%. The design answers that by running the two arms
CONCURRENTLY on gpu2 and gpu3, then repeating with the GPUs swapped, so the estimator
is the paired difference and not any single run.

But "concurrently" is an assumption about scheduling, not a property of the files.
If one card stalls — a neighbour holding VRAM, a lane that cannot place its KV pool —
the other stream keeps walking its list and the two arms end up sequential. The
metadata would look perfectly normal, the difference would look perfectly plausible,
and the thing the design was built to cancel would be back in the result. Silent.

So this checks the assumption first and refuses to report a difference it cannot
attribute. Then it prints the per-wave differences and the mean of the two waves.

    check_pair.py [--dir DIR] [--pair NAME_A:NAME_B]... [--max-skew-min MIN]
"""
import argparse
import json
import os
import statistics
import sys

DEFAULT_DIR = "/data/xbw/turnstile/results/night"
# Wave A: cap2+HC on gpu2, Foyer+HC on gpu3. Wave B: the same arms, GPUs swapped.
DEFAULT_PAIRS = [
    "pois200_pairA_cap2hc:pois200_pairA_foyerhc",
    "pois200_pairB_cap2hc:pois200_pairB_foyerhc",
]


def load(root, name):
    d = os.path.join(root, name)
    try:
        meta = json.load(open(os.path.join(d, "metadata.json")))
    except (OSError, ValueError):
        return None
    if not os.path.exists(os.path.join(d, "summary.json")):
        return None
    try:
        summ = json.load(open(os.path.join(d, "summary.json")))
    except (OSError, ValueError):
        summ = {}
    rep = summ.get("replay", {}) if isinstance(summ, dict) else {}

    wall_s = meta.get("wall_s")
    if wall_s is None:
        # Same fallback the figures use: the span of completed steps. Never the
        # metrics span, which brackets only the scraping window and disagrees with
        # every table in the paper.
        ts = []
        try:
            with open(os.path.join(d, "steps.jsonl")) as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        t = json.loads(line).get("complete_timestamp")
                        if t:
                            ts.append(t)
        except (OSError, ValueError):
            pass
        if len(ts) < 2:
            return None
        wall_s = max(ts) - min(ts)

    return {
        "name": name,
        "gpu": meta.get("gpu"),
        "started": meta.get("started"),
        "wall_min": wall_s / 60.0,
        "hit": 100.0 * (rep.get("server_prefix_hit_rate") or 0.0),
        "failed": rep.get("failed_steps"),
        "skew_src": "metadata" if meta.get("wall_s") is not None else "step span",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--pair", action="append", default=None,
                    help="A:B run names; repeatable")
    ap.add_argument("--max-skew-min", type=float, default=15.0,
                    help="how far apart the two arms' starts may be and still count "
                         "as concurrent")
    args = ap.parse_args()
    pairs = args.pair or DEFAULT_PAIRS

    rows, usable = [], True
    for spec in pairs:
        a_name, _, b_name = spec.partition(":")
        a, b = load(args.dir, a_name), load(args.dir, b_name)
        if a is None or b is None:
            missing = a_name if a is None else b_name
            print("⚠ %s：%s 还没有可用的结果，本组跳过" % (spec, missing))
            usable = False
            continue
        skew = abs((a["started"] or 0) - (b["started"] or 0)) / 60.0
        rows.append((spec, a, b, skew))

    if not rows:
        print("两组都还没有落地。")
        return 1

    print("=== 配对有效性检查 ===")
    print("%-46s %-8s %-8s %s" % ("组", "并发差(分)", "栅栏", "判定"))
    for spec, a, b, skew in rows:
        ok = skew <= args.max_skew_min
        print("%-46s %8.1f %8.1f %s" % (
            spec, skew, args.max_skew_min,
            "✅ 并发" if ok else "❌ 未并发 —— 这不是配对，差值不可归因"))
        if not ok:
            usable = False
    print()
    for spec, a, b, skew in rows:
        print("  %s" % spec)
        for r in (a, b):
            print("    gpu%s  %-24s wall=%.1f min  hit=%.1f%%  失败=%s  墙钟来源=%s"
                  % (r["gpu"], r["name"], r["wall_min"], r["hit"], r["failed"],
                     r["skew_src"]))

    print("\n=== 每组的配对差（A 减 B）===")
    dw, dh = [], []
    for spec, a, b, skew in rows:
        d_wall = a["wall_min"] - b["wall_min"]
        d_hit = a["hit"] - b["hit"]
        dw.append(d_wall)
        dh.append(d_hit)
        print("  %-46s 墙钟 %+7.1f 分   命中 %+6.1f pp" % (spec, d_wall, d_hit))

    print("\n=== 估计量 ===")
    print("  墙钟配对差  均值 %+.1f 分   两组 %s"
          % (statistics.mean(dw), ["%+.1f" % v for v in dw]))
    print("  命中配对差  均值 %+.1f pp  两组 %s"
          % (statistics.mean(dh), ["%+.1f" % v for v in dh]))
    if len(dw) >= 2:
        print("  墙钟两组极差 %.1f 分（若两组差很大，说明卡或时段效应没被交换抵消干净）"
              % (max(dw) - min(dw)))

    print()
    if not usable:
        print("❌ 上面的差值**不要**写进论文：配对前提不成立（见第一条检查）。")
        return 1
    print("✅ 配对前提成立。差值可归因给控制器与缓存配置，不含跨天/跨卡效应。")
    print("   注意 n=2 组，结论强度有限；要更强需要更多波次。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
