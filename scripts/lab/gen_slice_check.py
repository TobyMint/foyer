#!/usr/bin/env python3
"""时间片切换 run 落在线段的哪里 —— 那条**插值前沿**的直接检验。

为什么要有这个：全篇的判决是「没有控制器越过那条插值前沿」，而那条线的依据是
「按时间片混合两个 cap 可以逼近线段上任一点」。**这句话在 2026-09-26 之前从未被测量过**
（第 38 轮两条独立审查线都点名为「最该补、也最便宜」的那一个实验）。

`pois200_slice23_hc` 就是那次测量：主 trace、HiCache、cap 每 60 秒在 3 与 2 之间切。
本脚本把它得到的（墙钟, SLO）点放到 `frontier.FRONT` 的同一套判据下，
算出它相对那条线的 Δ，并把该段的两个锚点与弦中点一并印出来做对照。

⚠ **预期写在 lane 脚本头部**（跑之前就写了）：排队系统里吞吐对 cap 是凹的，
所以时间片混合一般**落在弦下方** ⇒ 那条线是**上界** ⇒ 拿它当基线是**保守**的。
本脚本**不判断哪个结果更好**，只报数。

用法: python3 gen_slice_check.py <results_dir> [run 名，默认 pois200_slice23_hc]
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envelope as ENV      # noqa: E402 插值的唯一实现
import frontier as FR       # noqa: E402  锚点与打平带的唯一实现


def point(d):
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [x["submit_timestamp"] for x in st if x.get("submit_timestamp")]
    comps = [x["complete_timestamp"] for x in st if x.get("complete_timestamp")]
    if not subs or not comps:
        raise SystemExit("!! 没有时间戳 —— 这个 run 还没开始跑")
    wall = (max(comps) - min(subs)) / 60.0
    slo = 100.0 * sum(1 for x in st
                      if x.get("first_token_ms") is not None
                      and x["first_token_ms"] < 10000) / len(st)
    return wall, slo, len(st)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "results/night"
    run = sys.argv[2] if len(sys.argv) > 2 else "pois200_slice23_hc"
    d = os.path.join(root, run)
    if not os.path.exists(os.path.join(d, "summary.json")):
        raise SystemExit("!! %s 还没落地（没有 summary.json）—— 跑完再看" % d)

    wall, slo, n = point(d)
    fr = sorted(FR.FRONT)
    ref = ENV.piecewise(wall, fr)
    print("时间片 run: %s" % run)
    print("  步数 %d  墙钟 %.4f 分  SLO %.4f%%" % (n, wall, slo))
    print("  前沿锚点: %s" % " -> ".join("%s(%.1f, %.1f)" % (nm, w, s) for w, s, nm in fr))
    if ref is None:
        print("  ⚠ 墙钟 %.1f 落在那条线的锚点范围之外，**不给 Δ**（端点外推会凭空造数）" % wall)
        return
    print("  线在 %.4f 分处的 SLO = %.4f%%" % (wall, ref))
    print("  **Δ = %+.4f pp**（> +1.0 在线上方 / 带内打平 / < -1.0 在线下方）"
          % (slo - ref))
    print("  判词: %s" % FR.classify(slo - ref))
    # 该段的两个锚点与弦中点，供对照
    lo = max((p for p in fr if p[0] <= wall), default=None)
    hi = min((p for p in fr if p[0] >= wall), default=None)
    if lo and hi and lo[0] != hi[0]:
        mid_w = (lo[0] + hi[0]) / 2.0
        mid_s = (lo[1] + hi[1]) / 2.0
        print("  同段锚点: %s(%.1f, %.1f) 与 %s(%.1f, %.1f)"
              % (lo[2], lo[0], lo[1], hi[2], hi[0], hi[1]))
        print("  弦中点: (%.1f, %.1f) —— 时间片若落在它下方，那条线就是**上界**"
              % (mid_w, mid_s))
    print()
    print("⚠ 本脚本只报数。结论（这条线是上界还是高估了静态侧）看 Δ 的符号与大小。")


if __name__ == "__main__":
    main()
