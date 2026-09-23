#!/usr/bin/env python3
"""跨 trace 验证：分段弹性判据（Eq. elasticity）能不能迁移到第二条工作负载？

为什么要这个脚本：审稿意见指出，§IV 的 epsilon 只在一条 trace
（pois200_l04，合成泊松到达）上测过，却用来解释控制器为什么输。审稿人的原话是
"cross-policy association, not a transportable causal derivative" —— 判据从未在
第二条工作负载上被检验。本脚本在 replay_realhr.csv（真实 Claude agent 会话，
117 会话 / 390 步，工具等待秒级）上重算同一组量，和主 trace 并排。

口径（与主 trace 逐字一致，不另起一套）：
  - busy/idle 分解、wall、tokens 全部走 gen_decomp.py 的实现（本脚本直接 import
    它，不复制代码——复制出来的第二套实现会漂移）
  - R-bar_busy = 全时段均值 / busy 占比  ← 不是全时段均值。用全时段均值会把
    tau 系统性地低估一个 busy 占比（cap1 会算成 18.5ms 而不是 ~28.8ms）
  - tau1 = busy_min*60*R-bar_busy / tokens * 1000   （模型自洽口径，= decomp 的 step_back_ms）
  - tau2 = 逐请求 decode 间隔中位                     （唯一独立于墙钟的测量）
  - SLO 阈值 10000ms（与 fig_progress.py / frontier.py 一致）

用法: python3 gen_elasticity_x.py <results_dir> <out.csv>
"""
import csv, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_decomp as gd          # 口径的唯一来源，见文件头

SLO_MS = 10000.0
SLO_ALT_MS = 5000.0              # 敏感性用；10s 在 realhr 上饱和到 100%，分辨不出点

# 每个 trace 家族：run 名 -> cap。两族都只用【无 HiCache 的纯静态 cap】，
# 这样前沿是同一种东西。主 trace 的论文前沿用的是 HiCache 点，见文件尾注释。
FAMILIES = [
    ("main", "pois200_l04 (合成泊松, 200 会话)",
     [("cap1", "pois200_cap1"), ("cap2", "pois200_cap2"),
      ("cap3", "pois200_cap3_fixed"), ("cap4", "pois200_cap4"),
      ("cap5", "pois200_cap5")], 5),
    ("realhr", "replay_realhr (真实高峰小时, 117 会话)",
     [("cap2", "realhr_cap2"), ("cap3", "realhr_cap3"),
      ("cap4", "realhr_cap4")], 4),
]
# 控制器臂（每族一条主臂）
ARMS = [("main", "Foyer+HiCache", "pois200_foyer_hc", 200),
        ("realhr", "Foyer", "realhr_foyer", 117)]
# 数据不足以入表的 run，明确列出来而不是删掉
EXCLUDED = [("realhr_cap1", "static=1", "84/390 步（27/117 会话），无 summary.json、"
             "metadata 无 wall_s，run 被截断；R-bar 与 tau 只在残段上算得，且 cap=1 时 "
             "R-bar_busy 恒等于 1，不构成一个信息点")]

# trace 原始文件（本地 data/ 与实验机逐字节相同，md5 见 xtrace_validation.md）
TRACES = {"main": ("data/replay_pois200_l04.csv", "df4bdd37e5"),
          "realhr": ("data/replay_realhr.csv", "882c29a022")}


def trace_stats(path):
    """trace 本身的规模与形状。中位/均值/p90/最大一起报——中位数会骗人。"""
    import csv as _csv
    rows = list(_csv.DictReader(open(path)))
    def q(vals, p):
        v = sorted(vals)
        return v[min(len(v) - 1, int(p * len(v)))]
    # ⚠ 用具名字典而不是元组：本项目已经四次把相邻列的数当成目标列
    # （见 CLAUDE.md 教训 1b）。元组 + 手写标签就是同一个坑。
    f = lambda v: {"med": round(q(v, .5), 1), "mean": round(sum(v) / len(v), 1),
                   "p90": round(q(v, .9), 1), "max": round(max(v), 1)}
    pl = [int(r["prefix_len"]) + int(r["input_len"]) for r in rows]
    ol = [int(r["output_len"]) for r in rows]
    tw = [float(r["tool_wait_after_ms"]) for r in rows if r.get("tool_wait_after_ms")]
    arr = [float(r["arrival_time"]) for r in rows]
    return dict(sessions=len({r["session_id"] for r in rows}), steps=len(rows),
                prompt=f(pl), output=f(ol), tool=f(tw),
                arrival_span_min=round((max(arr) - min(arr)) / 60000.0, 1))


HEADER = ["kind", "trace", "name", "cap", "sessions", "steps",
          "wall_min", "span_min", "busy_min", "idle_min", "idle_pct", "busy_frac",
          "running_all", "running_busy", "tokens", "tau1_ms", "tau2_ms",
          "slo10_pct", "slo5_pct", "hit_pct",
          "from", "to", "r0", "r1", "tau1_a", "tau1_b", "eps_tau1", "eps_tau1_full",
          "eps_tau2", "eps_lo5", "eps_hi5", "eps_lo10", "eps_hi10",
          "frontier_kind", "front_slo10", "delta10_pp", "front_slo5",
          "delta5_pp", "front_hit", "delta_hit_pp", "verdict",
          "prompt_tok_med", "prompt_tok_mean", "prompt_tok_p90", "prompt_tok_max",
          "tool_wait_med_ms", "tool_wait_mean_ms", "tool_wait_p90_ms", "tool_wait_max_ms",
          "arrival_span_min"]


def run_stats(root, run):
    """一条 run 的全部量。分解口径来自 gen_decomp（有 busy+idle==span 的断言）。"""
    d = os.path.join(root, run)
    rows_m = gd.read_metrics(os.path.join(d, "metrics.csv"))
    span_min, busy_min, idle_min, idle_pct = gd.decompose(rows_m)
    steps = gd.read_steps(os.path.join(d, "steps.jsonl"))
    tokens = sum(s.get("output_len_actual") or 0 for s in steps)
    subs = [s["submit_timestamp"] for s in steps if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in steps if s.get("complete_timestamp")]
    wall_min = (max(comps) - min(subs)) / 60.0
    running_all = sum(v for _, v in rows_m if v is not None) / len(rows_m)
    busy_frac = busy_min / span_min
    running_busy = running_all / busy_frac
    tau1 = busy_min * 60 * running_busy / tokens * 1000 if tokens else None
    tau2 = gd.step_perreq_ms(steps)
    ttft = [s["first_token_ms"] for s in steps if s.get("first_token_ms") is not None]
    slo10 = 100.0 * sum(1 for x in ttft if x <= SLO_MS) / len(ttft) if ttft else None
    slo5 = 100.0 * sum(1 for x in ttft if x <= SLO_ALT_MS) / len(ttft) if ttft else None
    hit = None
    sj = os.path.join(d, "summary.json")
    if os.path.exists(sj):
        import json
        try:
            hit = 100.0 * json.load(open(sj))["replay"]["server_prefix_hit_rate"]
        except Exception:
            hit = None
    return dict(run=run, wall_min=wall_min, span_min=span_min, busy_min=busy_min,
                idle_min=idle_min, idle_pct=idle_pct, busy_frac=busy_frac,
                running_all=running_all, running_busy=running_busy, tokens=tokens,
                tau1=tau1, tau2=tau2, slo10=slo10, slo5=slo5, hit=hit,
                steps=len(steps), sessions=len({s.get("session_id") for s in steps}))


def envelope(points):
    """上左包络：按墙钟升序，只保留 SLO 严格递增的点（被支配的点踢掉）。"""
    pts = sorted(points, key=lambda p: p[0])
    out = []
    for p in pts:
        if not out or p[1] > out[-1][1]:
            out.append(p)
    return out


def front_slo(env, wall):
    """包络在给定墙钟处的 SLO 上界。范围外返回 None，不做端点外推。"""
    if not env or wall < env[0][0] or wall > env[-1][0]:
        return None
    for (w0, s0), (w1, s1) in zip(env, env[1:]):
        if w0 <= wall <= w1:
            return s0 + (s1 - s0) * (wall - w0) / (w1 - w0)
    return None


def verdict_of(delta, wall, env):
    if delta is None:
        return ("LEFT-OF-FRONT (无静态点在更左, 平凡获胜)" if env and wall < env[0][0]
                else "OUT-OF-RANGE (超出现有静态点范围)")
    if delta > 1.0:
        return "ABOVE (越过前沿)"
    if delta > -1.0:
        return "ON (在线上, 不算赢)"
    return "BELOW (在线下)"


def seg_lookup(sigma, tau_a, tau_b):
    """相邻两个静态 cap 之间的分段弹性。tau_a/tau_b 给出 τ₁ 与 τ₂ 两种口径。

    ⚠ 取整不是无关紧要的，而这不是小事：gen_elasticity.py 读的是 decomp.csv，
    那里的 running 只留 2 位、step_back_ms 只留 1 位。ε 是两个对数之比，分母
    ln(R̄1/R̄0) 在 R̄≈1.5 时只有 ~0.076，2 位取整能把它挪动 3%，于是 cap3→cap4
    从 1.15 变成 1.20。所以本函数算【三个】口径，并且主列 eps1 严格复刻
    gen_elasticity.py 的输入精度（τ₁ 1 位、R̄ 2 位），这样主 trace 那一列能和
    论文 §IV 的四个数逐位对上；eps1f 是未取整的，eps2 用独立的 τ₂。
    """
    out = []
    for i in range(len(sigma) - 1):
        r0, r1 = sigma[i][1], sigma[i + 1][1]
        r0r, r1r = round(r0, 2), round(r1, 2)          # 与 decomp.csv 同精度
        a, b = tau_a[i], tau_a[i + 1]
        c, d = tau_b[i], tau_b[i + 1]
        ar, br, cr, dr = round(a, 1), round(b, 1), round(c, 1), round(d, 1)
        e1 = math.log(br / ar) / math.log(r1r / r0r) if a and b else None
        e1f = math.log(b / a) / math.log(r1 / r0) if a and b else None
        e2 = math.log(dr / cr) / math.log(r1r / r0r) if c and d else None
        # 噪声带：ε 是两个对数之比，分母 ln(R̄1/R̄0) 在 R̄≈1.2 时只有 ~0.07，
        # 所以 τ 的百分之几就能把分子放倒。这里把 τ₁a、τ₁b 各自 ±p 独立扰动，
        # 给出 ε 的范围。p 取 5% / 10%，参照本仓 repeat 实测的墙钟极差
        # （同 policy 同 trace 的重复对：1.2% ~ 22.4%，见 xtrace_validation.md）。
        lo5 = hi5 = lo10 = hi10 = None
        if a and b:
            for p, lo_ref, hi_ref in ((0.05, "lo5", "hi5"), (0.10, "lo10", "hi10")):
                d_ = math.log(r1r / r0r)
                lo = math.log((1 - p) * br / ((1 + p) * ar)) / d_
                hi = math.log((1 + p) * br / ((1 - p) * ar)) / d_
                if lo_ref == "lo5":
                    lo5, hi5 = lo, hi
                else:
                    lo10, hi10 = lo, hi
        out.append(dict(from_=sigma[i][0], to=sigma[i + 1][0], r0=r0, r1=r1,
                        tau1_a=ar, tau1_b=br, eps1=e1, eps1f=e1f, eps2=e2,
                        lo5=lo5, hi5=hi5, lo10=lo10, hi10=hi10))
    return out


def main():
    root, out_path = sys.argv[1], sys.argv[2]
    rows = []
    stats = {}
    print("=" * 78)
    print("### 两条 trace 是不是同一族（中位/均值/p90/最大 一起报）")
    for fam, label, _, _ in FAMILIES:
        t = trace_stats(TRACES[fam][0])
        print("  %-7s %s  md5=%s…  会话 %d, 步 %d, 到达跨度 %.1f min" %
              (fam, label, TRACES[fam][1], t["sessions"], t["steps"], t["arrival_span_min"]))
        for nm, key in (("prompt tokens", "prompt"), ("输出 tokens", "output"),
                        ("tool_wait ms", "tool")):
            d = t[key]
            print("           %-13s 中位=%9.1f 均值=%9.1f p90=%9.1f 最大=%9.1f" %
                  (nm, d["med"], d["mean"], d["p90"], d["max"]))
        rows.append(dict(kind="trace", trace=fam, name=os.path.basename(TRACES[fam][0]),
                         sessions=t["sessions"], steps=t["steps"],
                         prompt_tok_med=t["prompt"]["med"], prompt_tok_mean=t["prompt"]["mean"],
                         prompt_tok_p90=t["prompt"]["p90"], prompt_tok_max=t["prompt"]["max"],
                         tool_wait_med_ms=t["tool"]["med"], tool_wait_mean_ms=t["tool"]["mean"],
                         tool_wait_p90_ms=t["tool"]["p90"], tool_wait_max_ms=t["tool"]["max"],
                         arrival_span_min=t["arrival_span_min"]))
    print("=" * 78)
    for fam, label, caps, _ in FAMILIES:
        print("### %s — %s" % (fam, label))
        print("%-13s %4s %8s %8s %8s %9s %8s %8s %9s %8s" %
              ("cap", "步", "墙钟min", "busy%", "R̄busy", "tokens", "τ₁ ms", "τ₂ ms",
               "SLO@10s%", "命中%"))
        for capname, run in caps:
            st = run_stats(root, run)
            stats[run] = st
            print("%-13s %4d %8.1f %8.1f %8.2f %9d %8.1f %8.1f %9.1f %8.1f" %
                  (capname, st["steps"], st["wall_min"], 100 - st["idle_pct"],
                   st["running_busy"], st["tokens"], st["tau1"], st["tau2"],
                   st["slo10"], st["hit"] if st["hit"] is not None else float("nan")))
            rows.append(dict(kind="run", trace=fam, name=run, cap=capname,
                             sessions=st["sessions"], steps=st["steps"],
                             wall_min=round(st["wall_min"], 1), span_min=round(st["span_min"], 1),
                             busy_min=round(st["busy_min"], 1), idle_min=round(st["idle_min"], 1),
                             idle_pct=round(st["idle_pct"], 1), busy_frac=round(st["busy_frac"], 3),
                             running_all=round(st["running_all"], 3),
                             running_busy=round(st["running_busy"], 3), tokens=st["tokens"],
                             tau1_ms=round(st["tau1"], 1), tau2_ms=round(st["tau2"], 1),
                             slo10_pct=round(st["slo10"], 1), slo5_pct=round(st["slo5"], 1),
                             hit_pct=(round(st["hit"], 1) if st["hit"] is not None else "")))
        sigma = [(c, stats[r]["running_busy"]) for c, r in caps]
        tau1s = [stats[r]["tau1"] for _, r in caps]
        tau2s = [stats[r]["tau2"] for _, r in caps]
        print()
        print("  分段弹性（ε(τ₁) 用 2 位小数的 R̄，与论文 §IV 同算法；ε_full 用未取整 R̄）")
        print("  %-9s -> %-9s %6s %6s %7s %7s %8s %8s %8s   %s" %
              ("from", "to", "R̄0", "R̄1", "τ₁0", "τ₁1", "ε(τ₁)", "ε_full", "ε(τ₂)",
               "τ₁ ±5% / ±10% 噪声带"))
        for sg in seg_lookup(sigma, tau1s, tau2s):
            print("  %-9s -> %-9s %6.2f %6.2f %7.1f %7.1f %+8.2f %+8.2f %+8.2f   [%+.2f,%+.2f] / [%+.2f,%+.2f]" %
                  (sg["from_"], sg["to"], sg["r0"], sg["r1"], sg["tau1_a"], sg["tau1_b"],
                   sg["eps1"], sg["eps1f"], sg["eps2"],
                   sg["lo5"], sg["hi5"], sg["lo10"], sg["hi10"]))
            rows.append(dict(kind="segment", trace=fam, name="%s->%s" % (sg["from_"], sg["to"]),
                             from_=sg["from_"], to=sg["to"], r0=round(sg["r0"], 2),
                             r1=round(sg["r1"], 2), tau1_a=round(sg["tau1_a"], 1),
                             tau1_b=round(sg["tau1_b"], 1),
                             eps_tau1=round(sg["eps1"], 2), eps_tau1_full=round(sg["eps1f"], 2),
                             eps_tau2=round(sg["eps2"], 2),
                             eps_lo5=round(sg["lo5"], 2), eps_hi5=round(sg["hi5"], 2),
                             eps_lo10=round(sg["lo10"], 2), eps_hi10=round(sg["hi10"], 2)))
        segs = seg_lookup(sigma, tau1s, tau2s)
        # 前沿：只用纯静态 cap（与控制器臂同一代码代、同一 pool）
        env10 = envelope([(stats[r]["wall_min"], stats[r]["slo10"]) for _, r in caps])
        env5 = envelope([(stats[r]["wall_min"], stats[r]["slo5"]) for _, r in caps])
        print()
        print("  静态前沿（锚点）：")
        for w, s in env10:
            print("    wall=%7.1f  SLO@10s=%5.1f" % (w, s))
        print("    (SLO@10s 在 realhr 上饱和到 99.5~100 —— 阈值 10s 分辨不出这些点)")
        for w, s in env5:
            print("    wall=%7.1f  SLO@ 5s=%5.1f" % (w, s))
        # 前缀命中率轴 —— SLO@10s 在本档退化，这一轴才分辨得出点。
        # 命中率是引擎报的 server_prefix_hit_rate，和墙钟无关，不是自洽量。
        envhit = envelope([(stats[r]["wall_min"], stats[r]["hit"]) for _, r in caps
                           if stats[r]["hit"] is not None])
        # 控制器臂
        for afam, alabel, arun, asess in ARMS:
            if afam != fam:
                continue
            st = run_stats(root, arun)
            stats[arun] = st
            f10, f5 = front_slo(env10, st["wall_min"]), front_slo(env5, st["wall_min"])
            d10 = (st["slo10"] - f10) if f10 is not None else None
            d5 = (st["slo5"] - f5) if f5 is not None else None
            fhit = front_slo(envhit, st["wall_min"])
            dhit = (st["hit"] - fhit) if (fhit is not None and st["hit"] is not None) else None
            seg_hit = [s for s in segs if s["r0"] <= st["running_busy"] <= s["r1"]]
            fkind = ("realhr 纯静态 cap 上左包络（cap2/cap3/cap4，3 个锚点）" if fam == "realhr"
                     else "主 trace 纯静态 cap 上左包络（cap1..cap5）——⚠ 与论文 Table 的前沿"
                          "不是同一条（论文的前沿锚点带 HiCache），两族的 Δ 不可直接比")
            order = sorted([(stats[r]["running_busy"], stats[r]["wall_min"], c)
                            for c, r in caps] + [(st["running_busy"], st["wall_min"], alabel)])
            print()
            print("  控制器臂 %s (%s): 墙钟 %.1f min, R̄busy %.2f, SLO@10s %.1f%%, 命中 %.1f%%" %
                  (alabel, arun, st["wall_min"], st["running_busy"], st["slo10"], st["hit"]))
            for s in seg_hit:
                print("    → 落在 ε(τ₁)=%+.2f 段（R̄ %.2f~%.2f，τ₁ %.1f→%.1f ms，"
                      "ε(τ₂)=%+.2f）" % (s["eps1"], s["r0"], s["r1"], s["tau1_a"],
                                         s["tau1_b"], s["eps2"]))
            print("    → 前沿：%s" % fkind)
            print("    → Δ = %s pp（SLO@10s，论文口径）/ %s pp（SLO@ 5s）/ %s pp（命中率轴）" %
                  ("%+.2f" % d10 if d10 is not None else "n/a",
                   "%+.2f" % d5 if d5 is not None else "n/a",
                   "%+.2f" % dhit if dhit is not None else "n/a"))
            print("      SLO@10s 判决：%s；命中率轴判决：%s" %
                  (verdict_of(d10, st["wall_min"], env10),
                   verdict_of(dhit, st["wall_min"], envhit)))
            print("    → 相对最快的纯静态 cap: %.1f vs %.1f min（%+.1f%%）" %
                  (st["wall_min"], min(stats[r]["wall_min"] for _, r in caps),
                   100 * (st["wall_min"] / min(stats[r]["wall_min"] for _, r in caps) - 1)))
            print("    → 按 R̄busy 升序（n=%d 个点）：" % len(order))
            for rb, w, nm in order:
                print("       R̄busy=%5.2f  墙钟=%6.1f min   %s" % (rb, w, nm))
            rows.append(dict(kind="arm", trace=fam, name=arun, sessions=asess,
                             steps=st["steps"], wall_min=round(st["wall_min"], 1),
                             span_min=round(st["span_min"], 1), busy_min=round(st["busy_min"], 1),
                             idle_min=round(st["idle_min"], 1), idle_pct=round(st["idle_pct"], 1),
                             busy_frac=round(st["busy_frac"], 3),
                             running_all=round(st["running_all"], 3),
                             running_busy=round(st["running_busy"], 3), tokens=st["tokens"],
                             tau1_ms=round(st["tau1"], 1), tau2_ms=round(st["tau2"], 1),
                             slo10_pct=round(st["slo10"], 1), slo5_pct=round(st["slo5"], 1),
                             hit_pct=(round(st["hit"], 1) if st["hit"] is not None else ""),
                             frontier_kind=fkind,
                             front_slo10=(round(f10, 1) if f10 is not None else ""),
                             delta10_pp=(round(d10, 2) if d10 is not None else ""),
                             front_slo5=(round(f5, 1) if f5 is not None else ""),
                             delta5_pp=(round(d5, 2) if d5 is not None else ""),
                             front_hit=(round(fhit, 1) if fhit is not None else ""),
                             delta_hit_pp=(round(dhit, 2) if dhit is not None else ""),
                             verdict=verdict_of(d10, st["wall_min"], env10)))
        print()

    print("!! 数据不足以入表：")
    for r, pol, why in EXCLUDED:
        print("   %-14s [%s] %s" % (r, pol, why))
    print("=" * 78)

    with open(out_path, "w", newline="") as f:
        f.write("# 跨 trace 弹性验证 —— 由 scripts/lab/gen_elasticity_x.py 生成，勿手改\n")
        f.write("# 口径与 gen_decomp.py 逐字一致（本脚本 import 它，不复制实现）\n")
        f.write("# running_busy = 全时段均值 / busy占比（busy 条件均值，不是全时段均值）\n")
        f.write("# tau1_ms = busy_min*60*R̄busy/tokens*1000 = decomp 的 step_back_ms（模型自洽）\n")
        f.write("# tau2_ms = 逐请求 decode 间隔中位（唯一独立于墙钟的测量）\n")
        f.write("# eps_tau1/eps_tau2 = dln(tau)/dln(R̄busy) 在相邻两个纯静态 cap 之间\n")
        f.write("# SLO 阈值 10000ms（论文口径）；slo5_pct 是 5s 敏感性 —— 10s 在 realhr 上饱和\n")
        f.write("# 前沿只用【无 HiCache 的纯静态 cap】建，两族同一种东西\n")
        w = csv.DictWriter(f, fieldnames=HEADER, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("-> %s（%d 行）" % (out_path, len(rows)))


if __name__ == "__main__":
    main()
