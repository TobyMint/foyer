#!/usr/bin/env python3
"""独立复算论文头条数字 —— 【不 import 任何生成器】，从 trace 与原始日志直接算。

为什么要有：`check_paper_numbers.py` 查的是【正文 ↔ paper/data/*.csv】一致，
而 `paper/data/*.csv` 全部由 `scripts/lab/*.py` 生成。如果某个生成器的定义写错了，
正文与 CSV 会「一致地错」，检查器看不出来。这个脚本把最关键的几个量
**从头再实现一遍**，与生成器的输出对拍：

  1. 复用上界（trace 的 prefix_len 求和）—— 论文的 21,540,371 / 28,526,871 = 75.51%
  2. 每个静态锚点的墙钟与 SLO —— 直接从 steps.jsonl 的时间戳与 first_token_ms 算
  3. 静态上左包络与每条臂的有符号距离 Δ —— 独立写一遍插值

判据：本脚本的输出必须与 `paper/data/runs_precise.csv` / `table1.csv` 逐位相符
（容差 1e-3）。**跑完自己比对，不一致就以本脚本为准去查生成器。**

## 「独立」到什么程度 —— 别把它读强了（2026-09-25 codex 第 21 轮）

它**只独立在实现上**：不 import 任何生成器，插值、包络、墙钟、SLO 都另写一遍。
所以它能抓到的分歧是【实现 bug】与【抄录错误】这两类 —— 那次 `short()` 把
`pois200_` 前缀吃掉、以及手抄汇总表抄错列，都属这一类。

它**独立不了的是假设**，因为它与 `frontier.py` 共用下面这些【输入与定义】：

  - 同一批 `steps.jsonl`（同一份原始日志，谁都没做第二份测量）；
  - 同样的字段口径（墙钟 = max(complete) − min(submit)；SLO = first_token_ms < 10s）；
  - 同一份【预选好的】静态池 STATIC 与候选臂 ARMS —— 这两个列表本身就是判断，
    不是从数据推出来的；
  - 同一套「上左包络 + 分段线性插值」的前沿定义。

也就是说：**如果前沿的定义选错了、或者该进 STATIC 的 run 漏了，本脚本会与生成器
一致地错**，它不会报警。这一层只能靠人来质疑（§II 已经写明前沿是插值线而非实测点）。
上界那一段现在会与 `reuse.csv` 的 `bound_tok` 对拍，不再只是打印。

用法: python3 independent_frontier_check.py <trace.csv> <results_dir>
"""
import csv, json, os, sys

TOL = 1e-3
SLO_MS = 10000.0
STATIC = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5",
          "pairB_cap2hc", "cap3_hc", "cap4_hc", "cap3_hc_r2", "cap4_hc_r2"]
ARMS = ["foyer_sf0_r2", "foyer_hz1", "foyer_hc", "foyer_hz2", "foyer_hz0",
        "foyer_bres_r2", "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyfix_hc"]


def bound(trace_p):
    rows = list(csv.DictReader(open(trace_p)))
    pre = sum(int(r["prefix_len"]) for r in rows)
    tot = sum(int(r["prefix_len"]) + int(r["input_len"]) for r in rows)
    return pre, tot


def wall_slo(root, run):
    """墙钟 = max(complete) − min(submit)（与 run_summary.py:91 逐字同口径）；
    SLO = first_token_ms < 10s 的占比。两个量都只碰客户端日志。"""
    d = os.path.join(root, run)
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [s["submit_timestamp"] for s in st if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in st if s.get("complete_timestamp")]
    tt = [s["first_token_ms"] for s in st if s.get("first_token_ms") is not None]
    return (max(comps) - min(subs)) / 60.0, 100.0 * sum(1 for x in tt if x < SLO_MS) / len(tt)


def main():
    trace_p, root = sys.argv[1], sys.argv[2]
    pre, tot = bound(trace_p)
    print("复用上界 = %d / %d = %.4f  = %.2f%%" % (pre, tot, pre / tot, 100 * pre / tot))

    # 上界也要【对拍】，不能只打印（codex 第 21 轮指出：这一段原来只 print，
    # 于是上界算错了也没人拦）。reuse.csv 的 bound_tok / bound_frac 是正文那个
    # 75.51% 的落盘处 —— 两边必须严格相等。
    _rp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "paper", "data", "reuse.csv")
    if os.path.exists(_rp):
        _rf = [r for r in csv.DictReader(l for l in open(_rp) if not l.startswith("#"))]
        if _rf:
            _bt = int(_rf[0]["bound_tok"])
            _bf = _rf[0]["bound_frac"]
            # bound_frac 是 4 位小数的【字符串】列，比到那一位为止 ——
            # 拿 1e-9 去比 0.7551 与 0.755091 只会得到一次假警报（刚踩过）。
            if _bt != pre or _bf != "%.4f" % (pre / tot):
                raise SystemExit("!! 上界与 reuse.csv 不符：本脚本 %d / %.4f，"
                                 "reuse.csv %d / %s —— 以本脚本为准去查 gen_reuse.py"
                                 % (pre, pre / tot, _bt, _bf))
            print("   与 reuse.csv 的 bound_tok/bound_frac 逐位相符（%d / %s）" % (_bt, _bf))
        else:
            print("   !! reuse.csv 里没有数据行，上界没对拍上")
    else:
        print("   !! 找不到 reuse.csv，上界没对拍上")

    pts = sorted((*wall_slo(root, "pois200_" + r), r) for r in STATIC)
    env, best = [], -1.0
    for w, s, r in pts:
        if s > best:
            env.append((w, s)); best = s
    print("包络锚点（独立重算）:")
    for w, s in env:
        print("   %.4f / %.4f" % (w, s))

    def front(w):
        for (w0, s0), (w1, s1) in zip(env, env[1:]):
            if w0 <= w <= w1:
                return s0 + (w - w0) / (w1 - w0) * (s1 - s0)
        return None

    # 与生成器落盘的值对拍
    ref_p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "paper", "data", "table1.csv")
    ref = {}
    if os.path.exists(ref_p):
        ref = {r["run"]: r for r in csv.DictReader(l for l in open(ref_p) if not l.startswith("#"))}

    bad = 0
    print("\n%-16s %10s %10s %10s %10s" % ("run", "墙钟(算)", "墙钟(csv)", "Δ(算)", "Δ(csv)"))
    for r in ARMS:
        key = "pois200_" + r
        if not os.path.isdir(os.path.join(root, key)):
            print("%-16s （本地没有这条 run）" % r); continue
        w, s = wall_slo(root, key)
        f = front(w)
        d = s - f if f is not None else float("nan")
        rc = ref.get(r)
        dw = float(rc["wall_min"]) if rc else float("nan")
        dd = float(rc["delta_pp"]) if rc else float("nan")
        ok = (abs(w - dw) < TOL) and (abs(d - dd) < TOL)
        if not ok:
            bad += 1
        print("%-16s %10.4f %10.4f %10.4f %10.4f  %s" % (r, w, dw, d, dd, "OK" if ok else "<< 不一致"))
    print("\n结论：%s" % ("全部逐位相符（独立重算与生成器输出一致）" if not bad
                        else "有 %d 处不一致 —— 以本脚本为准去查生成器" % bad))
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
