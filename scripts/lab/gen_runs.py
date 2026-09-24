#!/usr/bin/env python3
"""paper/data/runs.csv 的生成器 —— 之前这张表是【手抄 run_summary.py 的打印输出】。

为什么要补这个生成器：runs.csv 是表 I 的行清单、§IV 的 Conc./SD 列、以及
gen_table.py 在缺 runs_precise 时的回退来源。它的四个数值列（wall/conc/slo/sd）
全部由实验机的 run_summary.py 算出来，而这份脚本【不在仓库里跑过】——
「每个数字都能追到脚本」在这张表上是打折扣的。本脚本用与 run_summary.py
逐字相同的定义在本地镜像上复算，让这张表可复现。

定义（抄自 scripts/lab/run_summary.py，改口径必须两边一起改）：
  wall = (最后一个 complete_timestamp − 最早一个 submit_timestamp) / 60
  conc = tw_conc：admissions.jsonl 的 admit/release/resume 事件做时间加权
  slo  = first_token_ms < 10000 的占比（注意是【严格小于】；frontier.py 用 <=）
  sd   = 段 SLO 的总体标准差，段数 nseg = max(2, min(10, 完成步数 // 20))
         —— 999 步是 10 段，125 步是 6 段（不是 10 段）
  steps= 有 complete_timestamp 的步数

用法: python3 gen_runs.py <results_dir> <out.csv>
"""
import csv, json, os, statistics as st, sys

# 表里有哪些 run、各自的 tier 与 family —— 显式列出，缺目录时【报错退出】而不是跳过
# （CLAUDE.md 纪律 3：生成器的 run 列表不全会静默改变下游口径，已栽过三次）
ROWS = """default 200 static
cap1 200 static
cap2 200 static
cap3_fixed 200 static
cap4 200 static
cap5 200 static
pairA_cap2hc 200 static_hc
pairB_cap2hc 200 static_hc
cap4_hc_r2 200 static_hc
cap3_hc_r2 200 static_hc
cap3_hc 200 static_hc
cap4_hc 200 static_hc
foyer_hc 200 foyer
foyer_hz1 200 foyer
foyer_hz1_r2 200 foyer
foyer_hz2 200 foyer
foyer_hz0_r2 200 foyer
foyer_bres_r2 200 foyer
foyer_breshz1 200 foyer
foyer_nogate 200 foyer
foyer_rg4 200 foyer
foyfix_hc 200 foyer
aimd2 200 aimd
aimd2_paper 200 aimd
cap2_25 25 static_hc
cap3_25 25 static_hc
foyer_hc_r2 200 foyer
foyer_sf0_r2 200 foyer""".split("\n")


def tw_conc(d):
    p = os.path.join(d, "admissions.jsonl")
    if not os.path.exists(p):
        return None
    ev = []
    for ln in open(p):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        k = {"admit": 1, "release": -1, "resume": 1}.get(e.get("event"))
        if k and e.get("ts") is not None:
            ev.append((float(e["ts"]), k))
    if len(ev) < 2:
        return None
    ev.sort()
    area, cur = 0.0, 0
    for i, (t, k) in enumerate(ev):
        if i:
            area += cur * (t - ev[i - 1][0])
        cur += k
    sp = ev[-1][0] - ev[0][0]
    return area / sp if sp > 0 else None


def sess_conc(d, rows):
    """没有准入日志时的【会话级】并发 —— 与 tw_conc 同一件事的另一种算法。

    为什么需要：`default`（无准入控制）的 admissions.jsonl 是空的（那个 arm 没有
    控制器，也就没有 admit/release 事件），run_summary.py 的 tw_conc 对它返回 None。
    2026-09-24 发现 runs.csv 里那一格被填成了 **1.69**，而 1.69 是
    metrics.csv 的 sglang:num_running_reqs 全时段均值 —— 也就是表 I 标题里
    明确说「Conc. 不是它」的那个量。同一列在 27 行是一个口径、在 1 行是另一个口径，
    而且是无声的。

    这个估计量 = Σ(每个会话的 first submit → last complete) / 全体跨度，
    与 tw_conc 的定义（面积/跨度）同构。**在四条静态 cap 上与 tw_conc 逐位相符**
    （cap1 0.999 vs 1.00、cap2 1.990 vs 1.99、cap5 4.895 vs 4.89、cap2_25 1.954 vs 1.95），
    在控制器臂上略高（控制器释放 permit 早于会话最后一步，foyer_hc 2.11 vs 2.06），
    所以它是可比但不等价的替代 —— 只在 tw_conc 无值时使用，并在表里注明。
    """
    S = {}
    for r in rows:
        if r.get("submit_timestamp") and r.get("complete_timestamp"):
            k = r["session_id"]; a, b = r["submit_timestamp"], r["complete_timestamp"]
            if k in S:
                S[k][0] = min(S[k][0], a); S[k][1] = max(S[k][1], b)
            else:
                S[k] = [a, b]
    if not S:
        return None
    lo = min(v[0] for v in S.values()); hi = max(v[1] for v in S.values())
    return sum(b - a for a, b in S.values()) / (hi - lo) if hi > lo else None


def one(root, name):
    d = os.path.join(root, "pois200_" + name)
    sp = os.path.join(d, "steps.jsonl")
    if not os.path.exists(sp):
        raise SystemExit("!! %s 没有 steps.jsonl（目录 %s）—— 缺 run 时不静默跳过" % (name, d))
    rows = []
    for ln in open(sp):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("complete_timestamp"):
            rows.append(r)
    rows.sort(key=lambda r: r["complete_timestamp"])
    tt = [r["first_token_ms"] for r in rows if r.get("first_token_ms") is not None]
    nseg = max(2, min(10, len(rows) // 20))
    seg = []
    for k in range(nseg):
        g = rows[k * len(rows) // nseg:(k + 1) * len(rows) // nseg]
        h = [y["first_token_ms"] for y in g if y.get("first_token_ms") is not None]
        if h:
            seg.append(100 * sum(1 for t in h if t < 10000) / len(h))
    c, src = tw_conc(d), "admission log"
    if c is None:
        # 只在没有准入日志时才退回会话级估计，并记录来源（见 sess_conc 的注释）
        c, src = sess_conc(d, rows), "session spans (no admission log)"
    return dict(
        run=name, steps=len(rows),
        wall=(max(r["complete_timestamp"] for r in rows)
              - min(r["submit_timestamp"] for r in rows if r.get("submit_timestamp"))) / 60.0,
        conc=c, conc_src=src,
        slo=100 * sum(1 for t in tt if t < 10000) / len(tt),
        sd=st.pstdev(seg) if len(seg) > 1 else 0.0,
        nseg=nseg)


def main():
    root, out = sys.argv[1], sys.argv[2]
    recs = []
    print("%-16s %6s %9s %7s %7s %6s %5s" % ("run", "步数", "墙钟min", "Concurrency", "SLO%", "SDpp", "段数"))
    for line in ROWS:
        name, tier, fam = line.split()
        r = one(root, name)
        r["tier"], r["family"] = int(tier), fam
        recs.append(r)
        print("%-16s %6d %9.4f %7.4f %7.4f %6.4f %5d  %s" % (
            name, r["steps"], r["wall"], r["conc"], r["slo"], r["sd"], r["nseg"],
            "" if r["conc_src"] == "admission log" else "<- " + r["conc_src"]))
    hdr = [
        "# Foyer 全部 run 的实测值 —— 由 scripts/lab/gen_runs.py 生成，勿手改",
        "# 生成器用的定义与实验机的 scripts/lab/run_summary.py 逐字相同（wall/tw_conc/slo/sd）。",
        "# 这张表原来是从 run_summary.py 的打印输出【手抄】的，2026-09-24 补上生成器。",
        "# 列: run, tier, steps, wall_min, conc, slo_pct, sd_pp, family",
        "#   tier   200 = 200 会话档（泊松 λ=0.04/s，999 步）；25 = 25 会话档（125 步）",
        "#   family static / static_hc（带 HiCache）/ foyer / aimd",
        "#   sd_pp  段 SLO 的总体标准差；段数 = max(2, min(10, 完成步数//20))，",
        "#          999 步 10 段、125 步 6 段 —— 段数不同不可直接比",
        "#   显示为 1 位小数；全精度值在 paper/data/runs_precise.csv（wall/slo）与本脚本的 stdout",
        "# conc 一律是【会话级活着的条数】（准入日志的 admit/release 时间加权）。",
        "#   唯一的例外是 default：那个 arm 没有控制器、不写准入日志，用会话跨度估计",
        "#   （与静态 cap 上的 tw_conc 逐位相符；见表 I 标题的脚注）。曾经那一格被填成",
        "#   1.69 —— 那是 num_running_reqs 的均值，也就是 Conc. 明确【不是】的那个量。",
        "run,tier,steps,wall_min,conc,slo_pct,sd_pp,family"]
    body = "\n".join(hdr) + "\n" + "\n".join(
        "%s,%d,%d,%.1f,%.2f,%.1f,%.1f,%s" % (r["run"], r["tier"], r["steps"],
                                             r["wall"], r["conc"], r["slo"], r["sd"], r["family"])
        for r in recs) + "\n"
    assert isinstance(body, str)
    with open(out, "w") as f:
        f.write(body)
    print("-> %s（%d 行）" % (out, len(recs)))


if __name__ == "__main__":
    main()
