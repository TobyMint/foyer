#!/usr/bin/env python3
"""AIMD「原参数」那条臂两次停摆的**可核事实** —— §\ref{sec:results:aimd} 引的数都出自这里。

为什么单独一张表：正文说「重跑也没修好：控制器进程中途退出、再没回来、两个会话一直排队、
停在 989/999 步」，以及第一次的「32 分钟不发许可、24 个会话排队」。这些数此前只在
那两个 run 目录的 `INTERVENTION.md`（散文）与终端里 —— 按证据纪律要落到 `paper/data/*.csv`。

⚠ **「停摆了多少分钟」不能只印一个数**。两次尝试的形态不同：

  - 第 1 次：控制器被 process-reaper 杀掉，**中间断了 31.4 分钟**，然后被手工恢复了
    （所以它的控制日志里有一段长间隔，而日志本身一直写到 08:58）。
  - 第 2 次：控制器进程**退出后再没回来**，日志就在 13:15:37 结束，之后引擎空转
    直到我手动停掉它（所以它的「最长日志间隔」只有 0.5 分钟，**完全不代表停摆时长**）。

因此这里给**两个机械可复算的起点**，各对应正文一处：

  - `queued_at_log_gap`    控制日志**最长中断**的起点 → 第 1 次 = 24（正文引的）
  - `queued_at_last_cycle` 控制日志**最后一行**处 → 第 2 次 = 2（正文引的）

用法: python3 gen_aimd_stall.py <results_dir> <out.csv>
"""
import collections, csv, datetime as dt, json, os, sys

RUNS = [("pois200_aimd2_paper", 1), ("pois200_aimd2_paper_r2", 2)]


def one(d):
    c = [json.loads(l) for l in open(os.path.join(d, "controller.jsonl")) if l.strip()]
    a = [json.loads(l) for l in open(os.path.join(d, "admissions.jsonl")) if l.strip()]
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]

    ev = collections.defaultdict(set)
    for x in a:
        ev[x["session_id"]].add(x["event"])
    never = [k for k, v in ev.items() if "queued" in v and "admit" not in v]
    admits = [x["ts"] for x in a if x["event"] == "admit"]
    acts = [x["ts"] for x in a] + [x["complete_timestamp"] for x in st
                                   if x.get("complete_timestamp")]

    # 控制日志里最长的一段中断及其起点
    ts = [x["ts"] for x in c]
    gap, gi = 0.0, 0
    for i in range(len(ts) - 1):
        if ts[i + 1] - ts[i] > gap:
            gap, gi = ts[i + 1] - ts[i], i

    def q_at(t):
        """t 时刻「已 queued 且还没 admit」的会话数。

        同一控制周期里自己的 admit 算**已准入**（决策行与准入事件相差毫秒）——
        不留这点余量的话第 2 次会多数出一个（那一个是该周期刚放行的）。
        """
        n = 0
        for k, v in ev.items():
            if "queued" not in v:
                continue
            q = min(x["ts"] for x in a if x["session_id"] == k and x["event"] == "queued")
            ad = [x["ts"] for x in a if x["session_id"] == k and x["event"] == "admit"
                  and x["ts"] <= t + 1.0]
            if q <= t and not ad:
                n += 1
        return n

    # 正文 §V 的「32 minutes」是**两次发许可之间**的间隔（03:26:26 -> 03:58:18
    # = 31.87），与控制日志的中断（31.4）不是同一个量 —— 两个都印，别让复算的人
    # 拿 31.4 去对正文的 32（独立复核子 agent 第 20 轮指出）。
    border = sorted(admits) + [max(acts)]
    agap = max(border[i + 1] - border[i] for i in range(len(border) - 1))

    # 那个 32 分钟的许可间隔里，引擎**真正空闲**了多久（`num_running_reqs == 0`）。
    # 为什么要有这一列：正文说「the engine sat idle for 28 of them」，
    # 而这张表此前**没有**任何一列能追到这个 28 —— 生成器的 docstring 却写着
    # 「§V 这一节引的数都出自这里」。是独立复核子 agent 第 39 轮指出来的：
    # **「日志里有」是必要条件不是充分条件**，日志会被 rsync 覆盖、会被清理，
    # 而数据文件是版本化的。
    import csv as _csv
    _idle = 0.0
    _M = []
    _mp = os.path.join(d, "metrics.csv")
    if os.path.exists(_mp):
        for _x in _csv.DictReader(open(_mp)):
            try:
                _M.append((float(_x["ts"]), float(_x["sglang:num_running_reqs"] or 0)))
            except (ValueError, TypeError):
                pass
    _M.sort()
    _b = sorted(admits)
    if len(_b) >= 2:
        # 找最长许可间隔的起止，在其区间内积分「引擎空闲」的时长
        _i = max(range(len(_b) - 1), key=lambda k: _b[k + 1] - _b[k])
        _t0, _t1 = _b[_i], _b[_i + 1]
        for (_x0, _r0), (_x1, _r1) in zip(_M, _M[1:]):
            _lo, _hi = max(_x0, _t0), min(_x1, _t1)
            if _hi > _lo and _r0 == 0:
                _idle += _hi - _lo

    return dict(admit_gap_min="%.1f" % (agap / 60.0),
                idle_in_gap_min="%.1f" % (_idle / 60.0),
                ctrl_cycles=len(c), ctrl_last="%.0f" % c[-1]["ts"],
                last_activity="%.0f" % max(acts), steps=len(st),
                queued_never_admitted=len(never),
                queued_at_log_gap=q_at(ts[gi]), queued_at_last_cycle=q_at(ts[-1]),
                stall_gap_min="%.1f" % (gap / 60.0),
                admit_first="%.0f" % min(admits) if admits else "",
                admit_last="%.0f" % max(admits) if admits else "",
                ctrl_gap_min="%.1f" % ((max(acts) - c[-1]["ts"]) / 60.0))


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = []
    for r, k in RUNS:
        d = os.path.join(root, r)
        if not os.path.exists(os.path.join(d, "controller.jsonl")):
            raise SystemExit("!! %s 不在镜像里 —— 缺 run 不能静默少一行" % d)
        x = one(d)
        x["run"], x["attempt"] = r, k
        rows.append(x)
        f = lambda t: dt.datetime.fromtimestamp(float(t)).strftime("%m-%d %H:%M:%S")
        print("%-22s 第 %d 次  控制周期 %d  末条 %s  最后活动 %s  步 %d  "
              "日志中断 %.1f 分  中断处排队 %d  末行处排队 %d"
              % (r, k, x["ctrl_cycles"], f(x["ctrl_last"]), f(x["last_activity"]),
                 x["steps"], float(x["stall_gap_min"]), x["queued_at_log_gap"],
                 x["queued_at_last_cycle"]))
    with open(out, "w", newline="") as fh:
        fh.write("# AIMD 原参数那条臂的两次停摆 —— gen_aimd_stall.py 生成\n")
        fh.write("# 时间戳是 unix 秒。两次的停摆**形态不同**，所以给两个起点，各对应正文一处：\n")
        fh.write("#   queued_at_log_gap    控制日志最长中断的起点 -> 第 1 次 = 24"
                 "（正文 §V 引的「24 sessions queued」）\n")
        fh.write("# admit_gap_min = 两次「发许可」之间最长的间隔（第 1 次 31.9 -> 正文的"
                 "「32 minutes」）；\n")
        fh.write("#   它与 stall_gap_min（控制日志的中断，31.4）**不是同一个量**，别混用。\n")
        fh.write("# idle_in_gap_min = 那个最长许可间隔【之内】，引擎 num_running_reqs==0\n")
        fh.write("#   的时长（第 1 次 28.0 -> 正文 §V 的「the engine sat idle for 28 of them」；\n")
        fh.write("#   第 2 次 7.9）。这一列是 2026-09-26 补的：正文那个 28 此前在任何数据\n")
        fh.write("#   文件里都追不到，而本脚本的 docstring 却写着「这一节引的数都出自这里」\n")
        fh.write("#   （独立复核子 agent 第 39 轮指出）。\n")
        fh.write("#   queued_at_last_cycle 控制日志最后一行处     -> 第 2 次 = 2"
                 "（正文引的「two sessions stayed queued」）\n")
        fh.write("# ⚠ stall_gap_min 只对第 1 次有意义（31.4 分钟，控制器被杀后重来）；\n")
        fh.write("#   第 2 次是「末条之后再没写过」，它的 0.5 分钟只是内部一次常规顿挫，\n")
        fh.write("#   **不代表停摆时长** —— 正文因此不引任何「停摆 N 分钟」。\n")
        fh.write("# queued_never_admitted = 整个 run 上从未被准入过的会话数"
                 "（第 1 次是 0：干预后它们最终都放行了）。\n")
        fh.write("# ctrl_gap_min 两行量的不是同一件事，且可以是负的"
                 "（第 1 次：干预后重启的控制器跑满默认 --max-minutes 300，\n")
        fh.write("#   比 runner 结束还晚；那个 run 的停摆发生在干预【之前】）。\n")
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
