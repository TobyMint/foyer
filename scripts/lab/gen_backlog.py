#!/usr/bin/env python3
"""准入队列长度（等待中的会话数）—— paper/data/backlog.csv。

为什么要有：§VII 引用队列长度，而这些数此前**不在任何 CSV 里** —— 只能从
`controller.jsonl` 的 `waiting_n` 现场算。违反本项目「论文里每个数字都要能追到
CSV / 代码 / 日志」那条（2026-09-25 自查发现）。

为什么这张表是 §VII 的关键：控制器「不赢」的一种辩解是「负载太轻、没有可调的空间」。
等待队列长度是这个辩解的直接读数 —— 200 档几乎每个控制周期都有几十个会话在等，
25 档也有十八个左右。

⚠ **但「两条 run 都只跑着一个请求」这句话本身不能支撑「队列是节流造出来的」** ——
2026-09-25 中立子 agent 第 9 轮实测：200 档基线 foyer_hc 的 running 均值是 **1.137**，
25 档 push_25 是 **1.136**，两档几乎一样。那个并列在基线上同样成立，区分不了任何东西。
正文现在引的是**闸门归因**（`gate_attrib.csv`：blocked 739 个周期里安全阀占 3.7%、
回合闸门占 0.0%）与**占用投影**（`projection.csv`：投影占预算 87.4%、引擎上报 43.6%，
比值 2.00）—— 那才是有测量的机制读数。

⚠ **不要跨档比队列的【绝对长度】**（2026-09-25 中立子 agent 纠正，正文已按此重写）。
   正文仍然把两档并排（归一化份额、三个相位中位），但**不再报两者的比值** —— 那是另一回事：
两档的 trace 不同 —— `replay_night25.csv` **没有 arrival_time 列**，25 个会话全在
t=0 到达，所以它的队列开局就是 24/25，而 200 档的峰值 135 出现在窗口 27% 处。
按本档会话数归一（`pct_of_tier` 列）后大小关系是反的：25 档扣住 72%、200 档扣住 33%。
队列长度在窗口内也不平稳，三个相位中位（`median_p10/mid/p90` 三列）从 21 对 21
变到 89 对 18 再变到 6 对 0。**单一中位描述不了 run 的任何一个时刻。**

口径：读 `controller.jsonl` 每一行的 `waiting_n`（控制器每个 2 s 周期记一次）。
**两个窗口都落盘、不挑一个**：`window=all` 是全部控制周期，`window=run` 只算
[最早提交, 最后完成] 之间（与全篇墙钟同一窗口）。首个请求提交之前那一段队列必然为空，
而它占 25 档 12% 的周期、200 档只占 2% —— 只报一个窗口会让比值差 10%。
两个窗口的分母都在 `samples` 列里。

用法: python3 gen_backlog.py <results_dir> <out.csv> [run ...]
"""
import csv, json, os, statistics, sys

# 论文引用的三条 + 它们的前代对照。前代那几条是为了让 §VII 的
# 「更早一代的 25 档读 9--11」也能追。
# 只列【有 controller.jsonl】的 run —— 静态 cap 不记准入队列，列进来只会刷屏
# 「缺」，把真正的缺失淹掉（2026-09-25 第一次跑就是这样）。
RUNS = ["pois200_foyer_hc", "pois200_foyer_hz1", "pois200_foyer_hz2_r2",
        "pois200_foyer_hz0_r2", "pois200_foyer_bres_r2", "pois200_foyer_breshz1",
        "pois200_foyer_nogate", "pois200_foyer_rg4", "pois200_foyer_sf0_r2",
        "pois200_foyer_push_25",          # §VII 的同代 25 档控制器臂
        # 更早一代的 25 档控制器——正文 §VII 写「read 9--11」。原来只列了 budget3 一条，
        # 于是那句里的「9」在 paper/data/ 里追不到（2026-09-25 中立子 agent 抓）。
        # 把这一代走同一 policy 的几条都列进来，让区间本身可复算。
        "load25c_budget3", "load25c_budget3_t80", "load25c_budget3_sf0",
        "load25c_budget3_zero", "load25c_budget3_hc"]


def cycles(d):
    """返回 [(ts, waiting_n)] —— 控制器每个 2 s 周期记一次。"""
    p = os.path.join(d, "controller.jsonl")
    v = []
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if "waiting_n" in x and x.get("ts") is not None:
            v.append((float(x["ts"]), x["waiting_n"]))
    return v


def run_window(d):
    """(最早提交, 最后完成, 完成的会话数) —— 从 steps.jsonl 取，与其它脚本的墙钟口径一致。

    **会话数是归一化必须的分母**：200 档与 25 档的会话数差 8 倍，不做归一化就比队列长度
    等于拿「8 倍的池子」当「8 倍的负载」。2026-09-25 中立子 agent 指出这个分母原来不在表里，
    读者无法从 CSV 复算「扣住了本档多少比例的会话」。
    """
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [s["submit_timestamp"] for s in st if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in st if s.get("complete_timestamp")]
    if not subs or not comps:
        return None
    return min(subs), max(comps), len({s["session_id"] for s in st if s.get("session_id")})


def stats(v):
    v_sorted = sorted(v)
    return dict(samples=len(v), waiting_p50=statistics.median(v),
                waiting_p90=v_sorted[int(0.9 * (len(v_sorted) - 1))],
                waiting_max=max(v),
                pct_nonzero="%.1f" % (100.0 * sum(1 for x in v if x > 0) / len(v)))


def main():
    root, out = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    rows, missing = [], []
    for r in runs:
        # 25 档那批目录带 `pois200_` 前缀，主 trace 那批不带 —— 两种都试。
        # （2026-09-25 第一次跑时只试了不带前缀的，于是把 25 档整批报成「缺」，
        #   而那正是 §VII 要引的那三条。run 目录命名不统一是这个项目的老毛病，
        #   凡按名字找目录的脚本都要两种都试。）
        d = None
        for cand in (os.path.join(root, r), os.path.join(root, "pois200_" + r)):
            if os.path.exists(os.path.join(cand, "controller.jsonl")):
                d = cand
                break
        if d is None:
            missing.append(r)
            continue
        cy = cycles(d)
        if not cy:
            missing.append(r + "（日志里没有 waiting_n）")
            continue
        # 【两个窗口都报】。codex 第 21 轮指出：只报「全部控制周期」会把
        # 首个请求提交之前的空队列周期算进来（200 档 188/8784、25 档 112/931），
        # 而那一段里队列必然为 0 —— 它拉低的是 25 档的中位（16 → 18）。
        # 正文要比的是【运行期间】的队列长度，所以 run 窗口那一行才是主张的直接读数；
        # 全周期那一行保留，是因为「这一次 run 从头到尾的队列有多长」本身也有人在问。
        # 两个窗口 + 分母一起给，读者自己就能复算，不必猜我们挑了哪个。
        win = run_window(d)
        variants = [("all", [w for _, w in cy])]
        if win:
            variants.append(("run", [w for t, w in cy if win[0] <= t <= win[1]]))
        # 相位中位：队列长度在窗口内不是平稳的（200 档前 10% 是 21、中段 89、后 10% 是 6），
        # 只报一个中位会让「跨档比队列长度」看着比实际稳。三个相位都落盘。
        ph = {}
        if win:
            W = win[1] - win[0]
            for tag, lo, hi in (("p10", 0.0, 0.1), ("mid", 0.25, 0.75), ("p90", 0.9, 1.0)):
                vv = [w for t, w in cy if win[0] <= t <= win[1] and lo <= (t - win[0]) / W < hi]
                ph["median_%s" % tag] = "%.1f" % statistics.median(vv) if vv else ""
        for tag, v in variants:
            if not v:
                continue
            rows.append(dict(run=os.path.basename(d), window=tag,
                             n_sessions=win[2] if win else "",
                             pct_of_tier="%.1f" % (100.0 * statistics.median(v) / win[2])
                             if win and win[2] else "",
                             **ph, **stats(v)))
    with open(out, "w", newline="") as f:
        f.write("# 准入队列长度（每个 2 s 控制周期记一次的 waiting_n）—— gen_backlog.py 生成，勿手改\n")
        f.write("# 用途：§VII 的队列长度。正文**不报两档的绝对长度之比**（两档 trace 不同、\n")
        f.write("#   25 档没有 arrival_time，归一化后方向是反的，见生成器 docstring）。\n")
        f.write("#   正文引的是：两档非零周期占比、pct_of_tier（扣住本档多少会话）、\n")
        f.write("#   三个相位中位、以及「更早一代的 25 档读 11--13」（window=run；\n")
        f.write("#   注意 9--11 是 window=all 那一列，两列别混）。\n")
        f.write("#   取舍：中位、p90、最大一起报（中位会骗人）。\n")
        f.write("# 口径：两个窗口都报，不挑一个 ——\n")
        f.write("#   window=all  全部控制周期（含首个请求提交之前的空队列段）\n")
        f.write("#   window=run  只算 [最早提交, 最后完成] 之间的周期（与全篇墙钟同一窗口）\n")
        f.write("# 两个窗口的分母都在 samples 列里，读者可复算。\n")
        w = csv.DictWriter(f, fieldnames=["run", "window", "n_sessions", "samples",
                                          "waiting_p50", "pct_of_tier", "median_p10",
                                          "median_mid", "median_p90", "waiting_p90",
                                          "waiting_max", "pct_nonzero"])
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out, len(rows)))
    for r in rows:
        print("  %-20s %-5s 采样 %-6s 中位 %-5s p90 %-5s 最大 %-5s（非零 %s%%）" % (
            r["run"], r["window"], r["samples"], r["waiting_p50"], r["waiting_p90"],
            r["waiting_max"], r["pct_nonzero"]))
    if missing:
        print("!! 没写进去（本地镜像没有，或日志里没这个字段）：")
        for m in missing:
            print("   " + m)


if __name__ == "__main__":
    main()
