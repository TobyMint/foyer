#!/usr/bin/env python3
"""重算 SLO：把「门外等待」（等 permit）算进去。

为什么需要：现有 SLO 用的是 steps.jsonl 的 first_token_ms，那只从**提交引擎**
算起。但会话在被准入之前要等 permit —— 而**那正是准入控制的代价**。用
submit→first-token 衡量 SLO，等于让控制器不为它造成的排队付账。

⚠ 坑：`arrival_time_ms` 是**会话**的到达时刻，同一会话的每一轮都相同。
拿它去减每一轮的 submit_timestamp 会得到「会话已存活多久」，不是等待 ——
第一版就是这么错的（算出 84 分钟的"等待"）。

正确的每轮「就绪时刻」：
  第 0 轮   = run_start + arrival_time_ms
  第 k 轮   = 上一轮 complete_timestamp + tool_wait_after_ms
门外等待 = submit_timestamp − 就绪时刻（截断到 >= 0）

用法: python3 gen_arrival_slo.py <results_dir> <out.csv> [run ...]

2026-09-24 补：本脚本原来只输出每条臂【自己】的 SLO 变化（delta_pp），而论文
§VIII 引用的「换到就绪时钟后，各臂离前沿的距离移动多少」那组数（foyfix +8.3、
其余 ≤2.7）**不在任何数据文件里**，只能靠人复算 —— 审稿人复算出 AIMD 是 3.6
而不是正文写的 2.8，无法判定谁对。现在把这组数也落成列：
  front_engine/ready_pct, delta_engine/ready_pp, move_pp = Δready − Δengine

⚠ **2026-09-27 更正（废止替代锚点）**：本文件此前用 cap4_hc / cap3_hc 的读数**顶替**
`cap4_hc_r2` / `cap3_hc_r2` 两条重复的就绪时钟值，并把这个近似写进了正文
（§VI 的「the runs we have per-step logs for」）。**那个理由不成立** ——
那两条的 `steps.jsonl` 是完整的 999 步、所需字段一个不缺（与实验机 md5 逐字节相同）。
替代值（52.5 / 66.1）比真值（56.7 / 67.2）**系统性偏低** ⇒ 就绪前沿偏低 ⇒
**每条臂的 Δ 被抬高约 0.5pp**，其中头条那条臂的第二次读数从 +1.51 变成 +0.96
（**从线上掉回带内**）。现在不接受替代：每条 FRONT 锚点都必须自己算得出来。
逐条复算见 `docs/finding_ready_anchor_substitution_20260927.md`。
"""
import csv, json, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envelope as _ENV   # noqa: E402  分段线性插值的唯一实现

# 2026-09-25 加 `foyer_sf0_r2`：它是最接近前沿的控制器臂（Δ −0.55），
# 而「ready 时钟不改变判决」这个稳健性论证**漏掉最接近的那条是不完整的**。
# 它有 controller.jsonl（7945 行），不是没数据。
# ⚠ `cap6_hc` 是 `frontier.FRONT` 的左端锚点，就绪时钟也要它（2026-09-26 补；
# 缺了它，RDY_SRC 的完整性断言会直接退出 —— 这正是想要的行为）。
RUNS = ["cap1","cap2","cap3_fixed","cap3_pd","cap4","cap5","pairB_cap2hc","cap3_hc","cap3_ph","cap4_hc","cap6_hc",
        # ⚠ 2026-09-27 补：这七条此前不在名单里，于是正文写成「我们只有 28 条的逐步日志」——
        # **那个理由不成立**，它们的日志是完整的（实测：999 步、字段齐、与实验机 md5 相同）。
        # 其中 cap4_hc_r2 / cap3_hc_r2 还是 FRONT 的锚点，缺了就得拿别的 run 替代（已废止）。
        "cap3_hc_r2","cap4_hc_r2","cap5_hc","cap8_hc","foyer_hc_r2","foyer_hz1_r2","default",
        "foyer_hc","foyer_hz1","foyer_hz1_r3","foyer_hz2_r2","foyer_hz2_r3","foyer_hz0_r2","foyer_bres_r2","foyer_breshz1_r2",
        "foyer_nogate","foyer_rg4","foyer_scan","foyer_sf0_r2","foyer_scan_r2",
        "foyer_scan_r3","foyer_hc_slru","foyer_sf0_r3",
        "foyfix_hc","aimd2","aimd2_paper_r3"]
THRESH = 10000.0



def main():
    root, out = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    rows = []
    print("%-14s %7s %7s %7s %8s %8s %8s" % (
        "run", "SLO内%", "SLO外%", "差pp", "等p50", "等p90", "等max(秒)"))
    for r in runs:
        p = os.path.join(root, "pois200_" + r, "steps.jsonl")
        if not os.path.exists(p):
            continue
        st = [json.loads(l) for l in open(p) if l.strip()]
        by = {}
        for s in st:
            by.setdefault(s["session_id"], []).append(s)
        # run_start：用第 0 轮的 submit 减 arrival 的最小值对齐（最早提交的那个会话）
        cands = [s["submit_timestamp"] - s["arrival_time_ms"] / 1000.0
                 for s in st if s["round_idx"] == 0 and s.get("submit_timestamp")]
        if not cands:
            continue
        base = min(cands)

        inside, outside, waits = [], [], []
        for sid, ss in by.items():
            ss.sort(key=lambda s: s["round_idx"])
            ready = None
            for i, s in enumerate(ss):
                ft, sub = s.get("first_token_ms"), s.get("submit_timestamp")
                if ft is None or sub is None:
                    continue
                if i == 0:
                    ready = base + s["arrival_time_ms"] / 1000.0
                else:
                    prev = ss[i - 1]
                    pc, tw = prev.get("complete_timestamp"), prev.get("tool_wait_after_ms") or 0
                    if pc is None:
                        ready = None
                    else:
                        ready = pc + tw / 1000.0
                if ready is None:
                    continue
                q = max(0.0, sub - ready) * 1000.0
                inside.append(ft)
                outside.append(ft + q)
                waits.append(q)
                # 下一轮的 ready 用本轮的 complete + tool_wait
        if not inside:
            continue
        si = 100 * sum(1 for x in inside if x < THRESH) / len(inside)
        so = 100 * sum(1 for x in outside if x < THRESH) / len(outside)
        print("%-14s %7.1f %7.1f %7.1f %8.0f %8.0f %8.0f" % (
            r, si, so, so - si, statistics.median(waits),
            sorted(waits)[int(.9 * len(waits))], max(waits) / 1000))
        rows.append({"run": r, "slo_engine_pct": round(si, 1),
                     "slo_ready_pct": round(so, 1), "delta_pp": round(so - si, 1),
                     "wait_p50_ms": round(statistics.median(waits)),
                     "wait_p90_ms": round(sorted(waits)[int(.9 * len(waits))]),
                     "wait_max_s": round(max(waits) / 1000)})
    # 前沿：**两条时钟都用 frontier.py 的同一组锚点**（不许另写一遍）。
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_fr2", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "frontier.py"))
    _FR = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_FR)
    FR_ENG = [(w, sl) for w, sl, _ in _FR.FRONT]
    # ⚠⚠ 2026-09-27：**替代锚点已废止，这是一处真错的更正。**
    # 原来是 `RDY_SRC = {"cap4_hc_r2": "cap4_hc", "cap3_hc_r2": "cap3_hc", ...}` ——
    # 用两条**第一条** run 的就绪读数去顶替那两条 `_r2` 重复，理由写在文件头
    # （「那两条没有做过就绪时钟重算」）并进了正文（「the runs we have per-step logs for」）。
    # **实测那个理由不成立**：cap4_hc_r2 / cap3_hc_r2 的 `steps.jsonl` 是完整的 999 步、
    # 所需字段一个不缺（本地镜像与实验机 md5 逐字节相同），就绪时钟完全算得出来 ——
    # cap4_hc_r2 = 56.7、cap3_hc_r2 = 67.2，而替代用的 cap4_hc / cap3_hc 是 52.5 / 66.1。
    # 替代值**系统性偏低** ⇒ 就绪时钟的前沿偏低 ⇒ **每条臂的 Δ 被抬高约 0.5pp**。
    # 现在不接受替代：**每条 FRONT 锚点都必须在算出来的行里**，缺一条直接退出。
    _rdy = {r["run"]: r["slo_ready_pct"] for r in rows}
    _names = [n for _, _, n in _FR.FRONT]
    _miss_run = sorted(set(_names) - set(_rdy))
    if _miss_run:
        raise SystemExit("!! 这些 FRONT 锚点算不出就绪时钟 SLO（不在 RUNS 里？）：%s\n"
                         "   不许用别的 run 替代 —— 那会让两条时钟的前沿不是同一组锚点"
                         "（2026-09-27 更正过一处）。把缺的 run 加进 RUNS。" % _miss_run)
    FR_RDY = [(w, _rdy[n]) for w, _, n in _FR.FRONT]

    # ⚠ 这里原来又写了一份分段线性插值（2026-09-26 codex 第 30 轮抓到，同型第三处）。
    # 一律调 `envelope.piecewise` —— 判据是「全仓库只剩一份实现」。
    def front(w, anchors):
        return _ENV.piecewise(w, anchors)

    eng = {r["run"]: r for r in csv.DictReader(
        l for l in open(os.path.join(os.path.dirname(os.path.abspath(out)),
                                     "table1.csv")) if not l.startswith("#"))}
    for r in rows:
        t = eng.get(r["run"])
        if not t:
            r.update(front_engine_pct="", front_ready_pct="",
                     delta_engine_pp="", delta_ready_pp="", move_pp="")
            continue
        w = float(t["wall_min"])
        fe, fr = front(w, FR_ENG), front(w, FR_RDY)
        de = None if fe is None else float(t["slo_pct"]) - fe
        dr = None if fr is None else r["slo_ready_pct"] - fr
        r.update(front_engine_pct="" if fe is None else round(fe, 1),
                 front_ready_pct="" if fr is None else round(fr, 1),
                 delta_engine_pp="" if de is None else round(de, 2),
                 delta_ready_pp="" if dr is None else round(dr, 2),
                 move_pp="" if (de is None or dr is None) else round(dr - de, 2))

    if not rows:
        print("没有可用数据"); return
    with open(out, "w", newline="") as f:
        f.write("# SLO 两种口径 —— 由 scripts/lab/gen_arrival_slo.py 生成\n")
        f.write("# slo_engine: TTFT<10s，从【提交引擎】算起（论文现用口径）\n")
        f.write("# slo_ready:  TTFT<10s，从【该轮就绪】算起（含等 permit 的门外时间）\n")
        f.write("# delta_pp = slo_ready - slo_engine，即准入控制造成的门外等待的代价\n")
        f.write("# move_pp  = delta_ready_pp - delta_engine_pp（换口径后离前沿的距离移动了多少）\n")
        f.write("#   delta_*_pp = 该臂的 SLO − 前沿在同墙钟处的插值；两条时钟用【同一组】\n")
        f.write("#   FRONT 锚点（2026-09-27 起：每条锚点都用它自己的就绪读数，\n")
        f.write("#   不再用别的 run 替代 —— 替代会让前沿系统性偏低）\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
