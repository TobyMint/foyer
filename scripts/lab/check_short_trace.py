#!/usr/bin/env python3
"""短 trace 到底能不能替代全程？——用真跑出来的短 run 判，不靠离线截断分析。

§三十八 已经用【截断已有的全程 run】证明过：墙钟排序在每一个截断长度上都稳定
（foyer_hc 从第 150 步到 999 步一直领先 cap2_hc），但截断会系统性夸大领先量 2-3 倍，
因为 T(N) 是累积量，早期抢到的领先会被一直背到终点。

那是一次离线分析。这个脚本判的是另一件事：短 trace 作为一条独立的 trace 文件，
跑出来的排序是否和全程一致。差别在于——只有 round 0/1 的 run 会提前结束，
尾部没有"驻留会话堆满池子"那一段，所以它未必等价于全程的前 40%。

    check_short_trace.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_summary import summary

PAIRS = [
    ("pois200_foyer_r2", ["pois200_pairA_foyerhc", "pois200_pairB_foyerhc"]),
    ("pois200_cap2_r2",  ["pois200_pairA_cap2hc", "pois200_pairB_cap2hc"]),
]


def main():
    short_rows, full_rows, missing = [], [], []
    for short, fulls in PAIRS:
        d, err = summary(short)
        if d is None:
            missing.append((short, err))
            continue
        short_rows.append((short, d))
        for f in fulls:
            fd, _ = summary(f)
            if fd:
                full_rows.append((f, fd))
    if missing:
        print("还没落地：")
        for n, e in missing:
            print("  %-20s %s" % (n, e))
    if not short_rows:
        print("\n两条短 run 都还没跑，等它们。")
        return 0

    print("\n短 trace 的 run（只有 round 0/1）：")
    for n, d in sorted(short_rows, key=lambda kv: kv[1]["wall"]):
        print("  %-20s 步数=%3d 墙钟=%6.1f 并发=%.2f SLO=%5.1f 段SD=%4.1f" % (
            n, d["steps"], d["wall"], d["conc"] or 0, d["slo"], d["sd"]))
    print("\n全程的对应项：")
    for n, d in sorted(full_rows, key=lambda kv: kv[1]["wall"]):
        print("  %-20s 步数=%3d 墙钟=%6.1f 并发=%.2f SLO=%5.1f 段SD=%4.1f" % (
            n, d["steps"], d["wall"], d["conc"] or 0, d["slo"], d["sd"]))

    if len(short_rows) == 2:
        s = sorted(short_rows, key=lambda kv: kv[1]["wall"])
        fw = [d["wall"] for n, d in full_rows if "foyer" in n]
        cw = [d["wall"] for n, d in full_rows if "cap2hc" in n]
        print("\n--- 判定 ---")
        print("  短 trace 上更快的是: %s（%.1f vs %.1f min）" % (
            s[0][0], s[0][1]["wall"], s[1][1]["wall"]))
        if fw and cw:
            fs, cs = sum(fw)/len(fw), sum(cw)/len(cw)
            print("  全程上（均值）:     foyer_hc %.1f  vs  cap2_hc %.1f" % (fs, cs))
            ok = ("foyer" in s[0][0]) == (fs < cs)
            print("  → %s" % ("OK 排序一致，短 trace 可用于排序"
                              if ok else "不一致 —— 短 trace 只能筛 bug，不能排序"))
        print("\n  SLO 排序（§三十八 说它会翻号，所以只作参考）：")
        for n, d in sorted(short_rows, key=lambda kv: -kv[1]["slo"]):
            print("    %-20s SLO=%5.1f" % (n, d["slo"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
