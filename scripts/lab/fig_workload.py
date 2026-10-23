#!/usr/bin/env python3
"""论文图 1：工作集 vs 池子 + 工具等待的双峰分布。只读 trace，不依赖任何 run。

用法：python3 fig_workload.py data/replay_long19.csv --pool 101502 --out fig.pdf

左panel：每个会话的上下文随轮次增长（19 条线），水平虚线是 KV 池（101.5K tokens）。
         要点：几乎每个会话在生命周期的后半段都**单独超过整个池子**。
右panel：工具等待的 CCDF（log x）。要点：中位 0.18 s，但 13% 的间隔 >10 s，
         且这 13% 吃掉 93% 的停放时间 —— 双峰，所以"停多久"不能用一个阈值猜。
"""
import argparse
import csv
import sys
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--pool", type=int, default=101502)
    ap.add_argument("--out", default="fig_workload.pdf")
    a = ap.parse_args()

    by = defaultdict(list)
    for r in csv.DictReader(open(a.trace)):
        ctx = int(r["prefix_len"]) + int(r["input_len"])
        by[r["session_id"]].append((int(r["round_idx"]), ctx, float(r["tool_wait_after_ms"])))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(3.5, 1.55))

    # --- (a) 全部会话同时驻留需要多少 KV（聚合工作集） ---
    # 每轮 i 的聚合工作集 = 所有"活到第 i 轮"的会话在该轮的 ctx 之和。
    # 这才是"全部驻留"的定义量：单条会话的 ctx 从不超过池子，但 19 条加起来是池子的十几倍。
    max_round = max(x[0] for v in by.values() for x in v)
    agg_x, agg_y = [], []
    for i in range(max_round + 1):
        tot = sum(v[i][1] for v in by.values() if len(v) > i)
        if tot:
            agg_x.append(i)
            agg_y.append(tot / 1000.0)
    for sid, v in by.items():   # 背景：单会话
        v.sort()
        ax1.plot([x[0] for x in v], [x[1] / 1000.0 for x in v], lw=0.5, alpha=0.45,
                 color="0.6")
    ax1.plot(agg_x, agg_y, lw=1.0, color="0.1")
    ax1.axhline(a.pool / 1000.0, ls="--", lw=0.8, color="#c0392b")
    ax1.text(1, a.pool / 1000.0 * 1.25, "KV pool", fontsize=5, color="#c0392b")
    ax1.set_xlabel("round", fontsize=5.5)
    ax1.set_ylabel("tokens (K)", fontsize=5.5)
    ax1.set_xlim(0, 85)
    ax1.set_ylim(0, max(agg_y) * 1.12)
    ax1.tick_params(labelsize=5)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # --- (b) 工具等待 CCDF ---
    tw = sorted(x[2] / 1000.0 for v in by.values() for x in v if x[2] > 0)
    n = len(tw)
    xs = sorted(set(tw))
    ys = [(n - sum(1 for t in tw if t < x)) / n for x in xs]
    ax2.loglog(xs, ys, lw=0.9, color="#2471a3")
    ax2.axvline(10.0, ls=":", lw=0.8, color="0.4")
    ax2.text(11, 0.5, "10 s", fontsize=5, color="0.4")
    ax2.set_xlabel("tool wait (s)", fontsize=5.5)
    ax2.set_ylabel("P(wait > x)", fontsize=5.5)
    ax2.tick_params(labelsize=5)
    ax2.set_ylim(0.008, 1.0)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.tight_layout(pad=0.2, w_pad=0.6)
    fig.savefig(a.out, bbox_inches="tight")
    print("写 %s（%d 会话，%d 个工具等待）" % (a.out, len(by), n))


if __name__ == "__main__":
    main()
