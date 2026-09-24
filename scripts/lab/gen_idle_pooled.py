#!/usr/bin/env python3
"""空转段的合并统计（全部 vs 排除受争用影响的 run）—— paper/data/idle_pooled.csv。

为什么要有：论文 §III 引用「1849 段，中位 5.6 s，均值 20.6 s，idle 时间中 69.6%
在 >20 s 的段里」。但那 1849 段里含四条被同机争用影响的 run（争用抬高 τ，
busy 变长、idle 变短，所以段时长【可能】被影响）。本脚本回答：排除它们之后
这些数会变吗？

答案是不会（中位 5.60→5.00 s，均值 20.65→21.02 s，>20 s 占比 69.6%→70.6%）。
这是因为段时长由【工具等待】决定，是工作负载属性，不是步成本的函数 ——
所以这个检查反过来支持了论文「空转是结构性的」这一主张。

用法: python3 gen_idle_pooled.py paper/data/idle_seg_raw.csv paper/data/concurrency.csv <out.csv>
"""
import csv, statistics, sys

BAD = None


def load(p):
    return [r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))]


def main():
    raw_p, conc_p, out_p = sys.argv[1:4]
    bad = {r["run"].replace("pois200_", "") for r in load(conc_p)
           if r["verdict"] == "CONTESTED"}
    rows = load(raw_p)
    assert len(rows) > 1000, "原始段只有 %d 条，路径或格式不对" % len(rows)

    # 四个变体都出：合并在位/均值对【并哪些 run】的敏感性本身就是要报的东西。
    # 实测：中位被 cap1 一条主导（它占 22% 的段，自身中位 5.0 s），去掉它中位
    # 从 5.60 跳到 10.00；而均值（18.3~21.0）与 >20s 占比（64.8~70.6%）稳定。
    # 实测被争用损害的【重跑前】那几条。foyer_bres 已由 foyer_bres_r2 替代、
    # 不再进入正文，所以它从这一组里拿掉（2026-09-25）。
    # 【从数据推导，不硬编码】—— 2026-09-25 教训：这一行原来是
    #     damaged = {"foyer_hz2", "foyer_hz0", "foyer_breshz1"}
    # 一个硬编码的集合。两条被干净重跑替代后它**匹配不到任何东西**，
    # `minus_damaged3` 于是退化成与 `all_runs` 一模一样的重复行，
    # 而正文还写着「四个 pooling」——实际上只剩三个不同的。
    # 新定义：**仍带旗且 τ₂ 确实被抬高的**（≥30ms）。重跑前恰好就是那三条，
    # 重跑后只剩 breshz1 —— 集合随数据走，不再随记忆走。
    _tau = {r["run"].replace("pois200_", ""): r.get("tau2_ms") for r in load(conc_p)}
    damaged = {k for k in bad
               if (lambda v: v is not None and v >= 30.0)(
                   (lambda t: float(t) if t not in (None, "", "None") else None)(_tau.get(k)))}
    # ⚠ 这条提示原来判的是 `damaged == (bad ∩ rows)` —— **判错了对**，
    # 实际会退化的是另外两对（`damaged ∩ rows` 为空、`bad ∩ rows` 只剩 cap1），
    # 所以它永不触发（2026-09-25 中立子 agent 第 11 轮实测：跑生成器无任何提示，
    # 而表里四行两两相同）。改成直接按**输出**判重：哪两行逐列相同就说出来。
    # ⚠ 要比的是【与池内 run 求交之后】的排除集，不是排除集本身 ——
    # `minus_damaged` 排除的是 {foyer_breshz1}，而它根本不在这个池里，
    # 所以它的**有效池**与 all_runs 相同。只比集合本身会漏掉这一对。
    _inpool = {r["run"] for r in rows}
    _seen = {}
    for _n, _e in (("all_runs", set()), ("minus_cap1", {"cap1"}),
                   ("minus_damaged", damaged),
                   ("minus_contested4", bad & _inpool)):
        _seen.setdefault(frozenset(_e & _inpool), []).append(_n)
    for _k, _v in _seen.items():
        if len(_v) > 1:
            print("  注：这些变体的【有效池】相同（排除集与池内 run 求交后一样）：%s" % "、".join(_v))
    out = []
    for name, excl in (("all_runs", set()),
                       ("minus_cap1", {"cap1"}),
                       ("minus_damaged", damaged),
                       ("minus_contested4", bad & {r["run"] for r in rows})):
        sel = [r for r in rows if r["run"] not in excl]
        v = [float(r["duration_s"]) for r in sel]
        tot = sum(v)
        out.append({
            "set": name, "n_segments": len(v), "n_runs": len({r["run"] for r in sel}),
            "median_s": "%.2f" % statistics.median(v),
            "mean_s": "%.2f" % statistics.mean(v),
            "p90_s": "%.2f" % sorted(v)[int(0.9 * len(v))],
            "max_s": "%.1f" % max(v),
            "pct_idle_time_in_gt20s": "%.1f" % (100 * sum(x for x in v if x > 20) / tot),
            "pct_segments_gt20s": "%.1f" % (100 * sum(1 for x in v if x > 20) / len(v)),
        })

    header = "\n".join([
        "# 空转段的合并统计 —— 由 scripts/lab/gen_idle_pooled.py 生成，勿手改",
        "# clean_only = 排除 concurrency.csv 里判 CONTESTED 的 run（它们的 τ 被同机争用抬高）",
        "# 四个变体：中位与 p90 被 cap1 主导（它占 22% 的段），均值与 >20s 占比稳定。",
        "# 论文引用的「中位 5.6 s」必须写成区间；「均值 ~20 s」与「>20s 占 idle 时间 ~2/3」稳健。",
        "set,n_segments,n_runs,median_s,mean_s,p90_s,max_s,pct_idle_time_in_gt20s,pct_segments_gt20s"])
    fields = ["set", "n_segments", "n_runs", "median_s", "mean_s", "p90_s", "max_s",
              "pct_idle_time_in_gt20s", "pct_segments_gt20s"]
    body = header + "\n" + "\n".join(",".join(str(r[k]) for k in fields) for r in out) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as fh:
        fh.write(body)
    print("写入 %s" % out_p)
    for r in out:
        print("  %-11s n=%4d(%2d run) 中位 %5s 均值 %5s  p90 %6s  >20s 占 idle 时间 %5s%%"
              % (r["set"], r["n_segments"], r["n_runs"], r["median_s"], r["mean_s"],
                 r["p90_s"], r["pct_idle_time_in_gt20s"]))


if __name__ == "__main__":
    main()
