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

⚠ 就绪时钟的前沿锚点有一处【近似】，必须写明：论文的前沿用四条锚点，其中
cap4_hc_r2 与 cap3_hc_r2 两条重复没有做过就绪时钟重算（见 §讨论），这里用它们的
第一条 run（cap4_hc 52.5、cap3_hc 66.1）代替。这不是论文的判决口径，
只是给「移动了多少」一个可复现的读数；换替代锚点会让每条臂移动 0.4pp 量级
（审稿人用另一组替代得到 AIMD +3.6）。正文已按本文件的读数据写，并写明是替代锚点。
"""
import csv, json, os, statistics, sys

RUNS = ["cap1","cap2","cap3_fixed","cap4","cap5","pairB_cap2hc","cap3_hc","cap4_hc",
        "foyer_hc","foyer_hz1","foyer_hz2","foyer_hz0","foyer_bres_r2","foyer_breshz1",
        "foyer_nogate","foyer_rg4","foyfix_hc","aimd2","aimd2_paper"]
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
    # 前沿：引擎时钟用 frontier.py 的四条全精度锚点（不许另写一遍）；就绪时钟用同一
    # 组墙钟，但把两条没有重算的重复换成它们的第一条 run（见文件头的说明）。
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_fr2", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "frontier.py"))
    _FR = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_FR)
    FR_ENG = [(w, sl) for w, sl, _ in _FR.FRONT]
    RDY = {"cap4_hc_r2": 52.5, "cap3_hc_r2": 66.1, "pairB_cap2hc": 74.5, "cap1": 76.2}

    def front(w, anchors):
        if w < anchors[0][0] or w > anchors[-1][0]:
            return None
        for (w0, s0), (w1, s1) in zip(anchors, anchors[1:]):
            if w0 <= w <= w1:
                return s0 + (s1 - s0) * (w - w0) / (w1 - w0)
        return None

    eng = {r["run"]: r for r in csv.DictReader(
        l for l in open(os.path.join(os.path.dirname(os.path.abspath(out)),
                                     "table1.csv")) if not l.startswith("#"))}
    FR_RDY = [(w, RDY[n]) for w, _, n in _FR.FRONT]
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
        f.write("#   delta_*_pp = 该臂的 SLO − 前沿在同墙钟处的插值；锚点见文件头（就绪时钟\n")
        f.write("#   的 cap4_hc_r2/cap3_hc_r2 用 cap4_hc=52.5 / cap3_hc=66.1 代替）\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
