#!/usr/bin/env python3
"""时间片切换的一次测量 —— paper/data/slice23.csv。

**这是全篇唯一那条承重假设的直接检验。** 论文用「静态点之间的分段线性插值」当判决基线，
理由是「按时间片混合两个 cap 可以逼近线段上任一点」—— 而这句话在第 38 轮之前
**从来没被测量过**，正文一直写着「we do not have the switching policy that would
turn it into a measurement」。

`pois200_slice23_hc` 就是那次测量：主 trace、HiCache、cap 每 60 秒在 3 与 2 之间切
（两个锚点 `cap3_hc_r2` 与 `pairB_cap2hc` 同配置）。

**跑之前写在 lane 脚本头部的预期**（照抄，免得事后挑说法）：
排队系统里吞吐对 cap 是凹的，所以时间片混合一般**落在弦下方** ⇒ 那条线是**上界** ⇒
拿它当基线是**保守**的。若它反而落在线上方，说明前沿的构造有问题、必须重写。

插值**共用 `envelope.piecewise`**（全仓库唯一实现），判决**共用 `frontier.classify`**
（±1.0pp 打平带与判词的唯一实现）。本脚本只把它们用在这一个新点上，不另写一份。

用法: python3 gen_slice23.py <results_dir> <out.csv>
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envelope as ENV      # noqa: E402
import frontier as FR       # noqa: E402


def point(d):
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [x["submit_timestamp"] for x in st if x.get("submit_timestamp")]
    comps = [x["complete_timestamp"] for x in st if x.get("complete_timestamp")]
    wall = (max(comps) - min(subs)) / 60.0
    slo = 100.0 * sum(1 for x in st
                      if x.get("first_token_ms") is not None
                      and x["first_token_ms"] < 10000) / len(st)
    return wall, slo, len(st)


def main():
    root, out = sys.argv[1], sys.argv[2]
    d = os.path.join(root, "pois200_slice23_hc")
    if not os.path.exists(os.path.join(d, "summary.json")):
        raise SystemExit("!! %s 缺 summary.json —— 没跑完的 run 不许进数据文件" % d)
    wall, slo, n = point(d)
    fr = sorted(FR.FRONT)
    line = ENV.piecewise(wall, fr)
    if line is None:
        raise SystemExit("!! 墙钟 %.1f 落在锚点范围外，不给 Δ（端点外推会凭空造数）" % wall)
    delta = slo - line
    # 该段的两个锚点（供正文说明「它落在哪一段」）
    lo = max(p for p in fr if p[0] <= wall)
    hi = min(p for p in fr if p[0] >= wall)
    rows = [
        ("run", "pois200_slice23_hc"),
        ("steps", n),
        ("wall_min", "%.4f" % wall),
        ("slo_pct", "%.4f" % slo),
        ("front_slo_at_wall", "%.4f" % line),
        ("delta_pp", "%+.4f" % delta),
        ("verdict", FR.classify(delta)),
        ("seg_lo", "%s(%s, %s)" % (lo[2], lo[0], lo[1])),
        ("seg_hi", "%s(%s, %s)" % (hi[2], hi[0], hi[1])),
    ]
    hdr = ["# 时间片切换（cap 每 60 s 在 3 与 2 之间切，HiCache，主 trace）—— 由 gen_slice23.py 生成，勿手改",
           "# 它检验的是：论文用「静态点的分段线性插值」当基线，依据是「时间片混合可逼近线段上任意点」。",
           "# 跑【之前】写在 lane 脚本头部的预期：时间片应落在弦**下方**（吞吐对 cap 凹）⇒ 线是上界、判决保守。",
           "# front_slo_at_wall 由 envelope.piecewise 算（全仓库唯一插值实现）；verdict 由 frontier.classify 给。",
           "field,value"]
    body = "\n".join(hdr) + "\n" + "\n".join("%s,%s" % r for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out, "w") as f:
        f.write(body)
    for k, v in rows:
        print("  %-20s %s" % (k, v))
    print("-> %s" % out)


if __name__ == "__main__":
    main()
