#!/usr/bin/env python3
"""独立复算「兑现率」—— 【不 import 生成器】，从 trace 与 steps.jsonl 直接算。

为什么要有：论文的机制主张（标题那句「内存层级决定并发的代价」）落在三个数上 ——
trace 上界 75.5%、host tier 的 87.9--92.4%、device-only 的 92.5% → 36.4%。
它们由 `gen_eviction.py` / `gen_reuse.py` / `gen_a100.py` 三条管线算出来，
而这三条**都从 `server_*_prompt_tokens` 那几个字段出发** —— 本项目在这里栽过最深的一次：

> `pois200_cap2_hp` 有 104/999 步被引擎服务成 **1-token 退化响应**，它们的**计划 prompt
> 整块**没进实测和，于是被算成了「复用」——兑现率虚报成 87.12%，引擎自报只有 56.88%，
> **差 30 个百分点，写进了正文**。

所以这条独立线除了对拍数，还**必须再做一次同源断言**：
`Σ server_prompt_tokens == Σ 计划 prompt`（trace 的 prefix_len + input_len），
两边不等就报错 —— 那正是当年能抓住那个 bug 的判据。

**规则照抄正文**：
  reuse = Σ(server_prompt_tokens − server_uncached_prompt_tokens)
  realized_frac = reuse / Σ(trace 的 prefix_len)        （上界独立于观测，来自 trace）

用法: python3 independent_realization_check.py <trace.csv> <results_dir> <reuse.csv>
"""
import csv, json, os, sys


def trace_totals(p):
    rows = list(csv.DictReader(open(p)))
    return (sum(int(r["prefix_len"]) for r in rows),
            sum(int(r["prefix_len"]) + int(r["input_len"]) for r in rows),
            len(rows))


def run_tokens(d):
    """三个量：计划 prompt（trace 侧）、引擎自报 prompt、引擎自报未命中。

    ⚠ **reuse 的分子必须用【计划】prompt**，与 `gen_eviction.py` 同源：
      reuse = Σ prompt_len(计划) − Σ server_uncached_prompt_tokens
    用 `server_prompt_tokens` 会在有**退化响应**（引擎回 1 个 token）的 run 上偏低
    —— 我第一版就是这么写的，于是在 `rg4` 上报了一条**假「不符」**（差 33,753 tokens）：
    计划量进了分子、引擎自报的没有。这两个量的**差**本身是有用的诊断（见下），
    但它不是 reuse 的口径。
    """
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    plan = sum(int(s.get("prompt_len") or 0) for s in st)
    eng = sum(int(s.get("server_prompt_tokens") or 0) for s in st)
    unc = sum(int(s.get("server_uncached_prompt_tokens") or 0) for s in st)
    return plan, eng, unc, len(st)


def main():
    trace_p, root, ref_p = sys.argv[1], sys.argv[2], sys.argv[3]
    bound, planned, nsteps = trace_totals(trace_p)
    print("trace: %d 步，上界 Σprefix_len = %d，计划 prompt = %d，上界占比 = %.4f (%.2f%%)"
          % (nsteps, bound, planned, bound / planned, 100 * bound / planned))
    ref = {r["run"]: r for r in csv.DictReader(l for l in open(ref_p) if not l.startswith("#"))}
    # 上界也要对拍（这一半是「独立于观测」的那个量）
    _bf = {r.get("bound_frac") for r in ref.values() if r.get("bound_frac")}
    if _bf and abs(float(sorted(_bf)[0]) - bound / planned) > 5e-5:
        print("!! 上界与参考表的 bound_frac 不符：本脚本 %.4f，表 %s"
              % (bound / planned, sorted(_bf)[0]))
        return 1

    bad = 0
    print("\n%-12s %12s %12s %10s %10s  %s" %
          ("run", "reuse(算)", "reuse(表)", "兑现(算)", "兑现(表)", "计划-引擎差"))
    for name in sorted(ref):
        # ⚠ 目录名：主 trace 是 `pois200_<name>`，**第二条 trace 是裸 `<name>`**
        # （`realhr_cap2` 等）。只认前者会让本脚本对 `reuse_x.csv` 静默什么都不查
        # —— 那是「生成器静默丢 run」的镜像。两个都试，找不到就报出来。
        d = os.path.join(root, "pois200_" + name)
        if not os.path.exists(os.path.join(d, "steps.jsonl")):
            d = os.path.join(root, name)
        if not os.path.exists(os.path.join(d, "steps.jsonl")):
            print("%-12s 找不到 run 目录（两种命名都试过）" % name)
            bad += 1
            continue
        plan, eng, unc, n = run_tokens(d)
        reuse = plan - unc
        frac = reuse / bound
        r_reuse = int(ref[name]["reuse_tok"])
        r_frac = float(ref[name]["realized_frac"])
        # 同源断言：引擎自报的 prompt 总量必须等于 trace 计划的总量。
        # ⚠ 例外：**没跑满 999 步**的 run（部分运行、退化响应、崩溃）不参与这条断言 ——
        # 它们的计划量本来就少一块。这一条要**明写**，不能静默跳过。
        # 同源诊断：**计划 prompt 与引擎自报 prompt 的差**。跑满 999 步的健康 run
        # 两者相等；不等有三种已知来源，都是**症状**而不是本脚本要判的错，只报不计：
        #   ① 退化响应（引擎回 1 token，半池那两条有 104 / 14 步）；
        #   ② 请求失败（`error` 非空 —— `foyer_rg4` 差 33,753 就是**一个** connection
        #      error 的整块计划量）。⚠ 本脚本只遍历 `reuse.csv` 的行，而 `reuse.csv`
        #      **不含** `default`/no-control（它没有复用口径），所以「baseline 的 600 s
        #      idle timeout」这类例子在本输入下**打不出来** —— 要查它得跑
        #      `check_paper_numbers.py` 里那条「短 run 丢请求数」守卫。
        #   ③ 部分运行（步数不足）。
        # ⚠ 正文原来只写「两条短 run ... and both finished」，把 ② 掩盖了 ——
        # 已改成「each lost one request（各是什么原因）」。
        gap = plan - eng
        diag = "相等" if gap == 0 else ("差 %d（占 %.3f%%）" % (gap, 100.0 * gap / plan))
        # ⚠ 2026-09-26（codex r43）：这段原来**只打印不断言** —— 于是一条跑满 999 步、
        # 却有差值的臂照样能让脚本报「全部相符」。现在真断言，并且**明列豁免名单**：
        # 半池那三条的退化响应（引擎回 1 token）是正文披露过的已知现象（104 / 14 / … 步），
        # 不在豁免名单里的**跑满 999 步**的 run 一旦有差值就计入 bad。
        DEGENERATE = {"cap2_hp", "cap3_hp", "cap4_hp"}
        if gap != 0 and n == nsteps and name not in DEGENERATE:
            bad += 1
            diag += " !! 未豁免的同源差" 
        ok_reuse = abs(reuse - r_reuse) <= 1
        # ⚠ 容差按**被比表的精度**：`reuse.csv` 的 `realized_frac` 存 4 位小数
        # ⇒ 半个末位是 5e-5。原来写 5e-4（松 10 倍），被中立复核指出。
        ok_frac = abs(frac - r_frac) <= 5e-5 + 1e-12
        flag = "" if (ok_reuse and ok_frac) else "   <<<"
        if flag:
            bad += 1
        print("%-12s %12d %12d %10.4f %10.4f  %s%s"
              % (name, reuse, r_reuse, frac, r_frac, diag, flag))

    print()
    if bad:
        print("!! %d 条不符 —— 以本脚本为准去查 gen_eviction/gen_reuse" % bad)
    else:
        print("结论：全部相符（独立重算与 reuse.csv 一致）")
        print("       「计划-引擎差」不为零的 run 是退化响应/部分运行的症状，正文已就它披露过")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
