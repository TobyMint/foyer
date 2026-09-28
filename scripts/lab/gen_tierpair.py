#!/usr/bin/env python3
"""同卡背靠背的层级配对 `cap3_pd` / `cap3_ph` 的**预注册判决** —— paper/data/tierpair.csv。

预注册在 `docs/prereg_tierpair_20260925.md`（2026-09-25 00:2x，任何数据落地之前写下）。
**本脚本是那条判据唯一的机械实现**（CLAUDE.md 纪律 4：判据写在正文里，代码里也必须实现）
—— 判决由脚本打印，不由人读表得出。这一条尤其重要，因为这一对是**可能推翻论文自己的
§III 匹配对段落**的实验：判据若留在人脑里，结果不合意时最容易悄悄挪动它。

## 预注册判据（逐字照抄，不许在结果出来之后改）

| 结果 | 结论 |
|---|---|
| 占用率与在跑数各差 <10%，且 `cap3_ph` 的兑现率比 `cap3_pd` **高 >=10 个点** | 与现有那一对一致；匹配对主张得到**同卡**支持 |
| 差 **<5 个点**，或方向相反 | §III 的匹配对段落**必须改写**，把这一对作为反例写进去 |
| 中间（5–10 个点） | 照实报出差距，并说明它比现有那一对弱多少 |

兑现率 `realization = (prompt − dev_miss + host_hit) / 上界`，同 `gen_reuse.py`。

## 口径：全部走 `gen_a100.one()`，一句都不另写

`one()` 内部已经调了 `gen_reuse.trace_ceiling`（上界）与 `gen_decomp.busy_stats`
（busy 占比 / R̄ / τ₁），并且带**同源断言**（计划 prompt 必须等于实测 `server_prompt_tokens`，
否则拒算）。本脚本再写一份就会分叉 —— 本项目已经栽过三次（见 CLAUDE.md 纪律 2）。
代数上 `prompt − uncached` 恒等于 `prompt − dev_miss + host_hit`，所以 `one()` 的
`reuse_tok` 与预注册写的那个分子是同一个量。

用法: python3 gen_tierpair.py <results_dir> <out.csv>
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_a100 as _A   # noqa: E402  口径共用（上界 / R̄ / 兑现率）

# ⚠ 2026-09-26：这两条的目录**原本没有 `pois200_` 前缀**，而下游生成器（含
# `frontier.py --csv` 的 `startswith("pois200_")`）一律按前缀拼路径 ——
# 独立复核子 agent 第 16 轮抓到：不解决这一点，并入后它们拿不到全精度坐标、
# 表 I 的 Δ 会静默回落到 1 位小数。**已在实验机上把目录改名**为带前缀的形式，
# 这里跟着改。`runner_argv` 里记的仍是旧路径，那是**当时实际跑的命令**，不改。
PAIR = ("cap3_pd", "cap3_ph")        # (设备侧, host 侧)；load() 用 prefixed=True 拼 pois200_
# 论文 §III 现有的那一对（**有混淆**：相隔 19.5 小时、不同 GPU）。本脚本把它一起算出来
# 作对照，好让读者看出同卡这一对是更强还是更弱。
OLD = ("cap3_fixed", "cap3_hc")
SUPPORT_PP = 10.0    # 判据第 1 行
WEAK_PP = 5.0        # 判据第 2 行的下界
COND_PCT = 10.0      # 前提：占用率与在跑数各差 <10%
PLAN_STEPS = 999     # 主 trace 的步数；跑不满就不许进判决


def load(root, name, prefixed):
    """读一条 run；**只接受跑完的**。

    ⚠ `summary.json` 存在**不等于跑完**：`stop_session_on_error` 会让崩溃的 run
    也写出 summary（`runner_rc=0`，误导性）。`gen_a100.one()` 对一条【在跑的】
    日志同样能返回一组数（它的同源断言只看已落地的步）。判决表因此可能被判据
    之外的东西污染，所以这里逐条要求 999 步、0 失败（2026-09-26 codex 第 30 轮抓到）。
    """
    d = os.path.join(root, ("pois200_" if prefixed else "") + name)
    sp = os.path.join(d, "summary.json")
    if not os.path.exists(sp):
        return None, d
    r = json.load(open(sp)).get("replay", {})
    if r.get("attempted_steps") != PLAN_STEPS or r.get("failed_steps") != 0:
        raise SystemExit(
            "!! %s 没跑完（attempted=%s failed=%s，要求 %d/0）—— 不许拿它算配对判决"
            % (name, r.get("attempted_steps"), r.get("failed_steps"), PLAN_STEPS))
    x = _A.one(d)          # 缺 steps.jsonl / 没被真正服务 -> 这里会抛（不许静默凑数）
    # ⚠ **summary 说 999 不等于日志真有 999 行**（codex 第 31 轮的构造：summary 里
    # 保留 999/0、把 steps.jsonl 截成 998 行 —— `one()` 照样返回一组数、
    # `load()` 照样放行）。两个来源都要核。
    if x["steps"] != PLAN_STEPS:
        raise SystemExit("!! %s 的 steps.jsonl 只有 %d 行（summary 说 %d）—— 两个来源"
                         "不一致，不许拿它算配对判决"
                         % (name, x["steps"], PLAN_STEPS))
    # ⚠ **行数相同不代表是同一批行**（codex 第 32 轮的构造：把 `cap3_fixed` 的
    # steps.jsonl 冒充 `cap3_pd` 的 —— 两条都是 999 行，长度守卫放行）。
    # 判据用**这条 run 自己的**量：summary 的 `total_duration_ms_sum` 必须等于
    # 日志里 `total_duration_ms` 的和。它是逐 run 不同的（31.27M / 32.20M / 28.33M），
    # 而 `target_output_tokens` 是 trace 的性质（四条 run 全是 706,010），
    # **不能**拿它当身份判据。
    _st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    _tot = sum(x.get("total_duration_ms") or 0 for x in _st)
    _sd = r.get("total_duration_ms_sum")
    if _sd is None or abs(_sd - _tot) > 1.0:
        raise SystemExit("!! %s 的 summary 与日志不是同一条 run（summary 时长和 %.1f，"
                         "日志 %.1f）—— 拒判" % (name, _sd or -1, _tot))
    return x, d


def rel_pct(a, b):
    """两个读数的相对差（%），以两者的均值为分母。"""
    a, b = float(a), float(b)
    return abs(a - b) / ((a + b) / 2) * 100 if (a + b) else 0.0


def decide(g_new, g_old, cond_occ, cond_run, cond_occ_mean=None):
    """预注册那三行判据的**唯一实现**，抽成纯函数是为了能逐分支做单元测试
    （三行判据 + 「前提不成立」那一支，共四种输入形态）。

    返回 (判决串, 前提是否成立)。**判据一个字都不许在这里放宽** ——
    这一对可能推翻论文自己的 §III 匹配对段落，所以它必须能被人拿两个数复核。
    """
    # 占用率**两个统计量都要过**：预注册举的旧配对例子（55.8/55.5）用的是均值，
    # 而 `one()` 报的是中位。只判一个的话，前提的成立与否会随选哪个统计量而变
    # （2026-09-26 codex 第 30 轮抓到）。
    _oc = [cond_occ] if cond_occ_mean is None else [cond_occ, cond_occ_mean]
    controlled = max(_oc) < COND_PCT and cond_run < COND_PCT
    if g_new < 0:
        return ("反向：host 侧比设备侧低 %.2f 个点 —— 判据第 2 行，"
                "§III 的匹配对段落必须改写，把这一对作为反例写进去" % -g_new), controlled
    if g_new < WEAK_PP:
        return ("差 %.2f 个点（<5）—— 判据第 2 行，§III 的匹配对段落必须改写，"
                "把这一对作为反例写进去" % g_new), controlled
    if g_new < SUPPORT_PP:
        return ("差 %.2f 个点（5--10，中间档）—— 照实报出差距，并说明它比现有那一对"
                "（%.2f 个点）弱多少" % (g_new, g_old)), controlled
    if controlled:
        return ("差 %.2f 个点（>=10）且前提成立（占用差 %.1f%%（中位）/ %.1f%%（均值）、"
                "R̄ 差 %.1f%%，均 <10%%）"
                "—— 判据第 1 行：与现有那一对一致，匹配对主张得到同卡支持"
                % (g_new, cond_occ, cond_occ_mean or 0.0, cond_run)), controlled
    # 判据第 1 行带前提，前提不成立时它**不适用** —— 不许把判据放宽，
    # 也不许因此宣布支持。照实报，并说明前提哪一条不成立。
    return ("差 %.2f 个点（>=10）但**前提不成立**（占用差 %.1f%%（中位）/ %.1f%%（均值）、"
            "R̄ 差 %.1f%%，要求各 <10%%）—— 判据第 1 行不适用；这一对不是受控对照，"
            "§III 必须写明实际差在哪里，不许当作同卡支持"
            % (g_new, cond_occ, cond_occ_mean or 0.0, cond_run)), controlled


def main():
    root, out_p = sys.argv[1], sys.argv[2]
    trace_p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "..", "data", "replay_pois200_l04.csv")
    bound = _A.bound(trace_p)[0]      # 与 reuse.csv 同一个函数

    got = {}
    missing = []
    for prefixed, names in ((True, PAIR), (True, OLD)):
        for n in names:
            x, d = load(root, n, prefixed)
            if x is None:
                missing.append(os.path.basename(d))
            else:
                got[n] = x
    # ⚠ **先查齐、再写文件**。2026-09-26 在 gen_a100.py 上栽过一次：守卫写在
    # `open(out,"w")` 之后，于是它照样把表写残（CLAUDE.md：`open(w)` 在 write 之前
    # 就截断文件）。凡是「缺输入就拒写」的守卫，**必须在打开输出文件之前**。
    if missing:
        raise SystemExit("!! 缺 summary.json，拒写表（这几条没跑完就别判）：\n   "
                         + "\n   ".join(missing))

    rows = []
    for role, names in (("paired", PAIR), ("pre-existing (confounded)", OLD)):
        for side, n in zip(("device-only", "host-tier"), names):
            x = got[n]
            rows.append(dict(run=n, pair=role, side=side,
                             steps=x["steps"], wall_min=x["wall_min"],
                             pool_tokens=x["pool_tokens"],
                             Rbar_busy=x["Rbar_busy"], occ_p50_pct=x["occ_p50_pct"],
                             occ_mean_pct=x["occ_mean_pct"],
                             tau1_ms=x["tau1_ms"], tau2_ms=x["tau2_ms"],
                             slo_pct=x["slo_pct"],
                             reuse_tok=x["reuse_tok"],
                             realized_frac="%.6f" % (x["reuse_tok"] / bound),
                             realized_pct="%.2f" % (100.0 * x["reuse_tok"] / bound)))

    def gap(names):
        a, b = (float(got[n]["reuse_tok"]) / bound * 100 for n in names)
        return b - a, a, b          # (host − device) 的百分点差

    g_new, d_new, h_new = gap(PAIR)
    g_old, d_old, h_old = gap(OLD)
    # ⚠ **占用率用未舍入值算**：`one()` 返回的是格式化到 1 位的字符串
    # （"56.3" / "56.7"），拿它们算相对差会得到 0.71%，而原始 `token_usage` 算出来
    # 是 **0.78%**（中位 0.60%）—— 而这正是本项目在 `reuse.csv` 表头明令禁止的
    # 「拿舍入后的列算比例」（2026-09-26 独立复核子 agent 第 18 轮抓到）。
    # 直接调共用的 `occ_stats()` 取未舍入值。
    _oc = {k: _A.occ_stats(os.path.join(root, ("pois200_" if prefixed else "") + n))
           for k, n, prefixed in ((PAIR[0], PAIR[0], True), (PAIR[1], PAIR[1], True))}
    cond_occ = rel_pct(_oc[PAIR[0]][0], _oc[PAIR[1]][0])
    cond_occ_m = rel_pct(_oc[PAIR[0]][1], _oc[PAIR[1]][1])
    cond_run = rel_pct(got[PAIR[0]]["Rbar_busy"], got[PAIR[1]]["Rbar_busy"])
    controlled = decide(g_new, g_old, cond_occ, cond_run, cond_occ_m)[1]

    verdict = decide(g_new, g_old, cond_occ, cond_run, cond_occ_m)[0]

    body = []
    body.append("# 同卡背靠背的层级配对 cap3_pd / cap3_ph —— gen_tierpair.py 生成，勿手改")
    body.append("# 预注册：docs/prereg_tierpair_20260925.md（2026-09-25 00:2x，数据落地前写下）")
    # ⚠ 本行**没有** % 格式化，所以百分号写单个 —— 写成 `%%` 会原样印进文件
    # （2026-09-26 第一版就是这么写的，跑出来表头里是 `<10%%`）。
    body.append("# 判据：占用率与在跑数各差 <10% 且 host 侧兑现高 >=10 个点 -> 支持；")
    body.append("#       <5 个点或反向 -> §III 匹配对段落必须改写；5–10 -> 照实报差距。")
    body.append("# 口径：全部走 gen_a100.one()（上界 gen_reuse.trace_ceiling = %d，" % bound)
    body.append("#       R̄ 与 τ₁ 走 gen_decomp.busy_stats），**不另写一份实现**。")
    body.append("# realized = reuse_tok / 上界；代数上等于预注册写的 (prompt − dev_miss + host_hit)/上界。")
    body.append("# 同卡这一对：host 侧 − 设备侧 = %+.2f 个点" % g_new)
    body.append("# 现有那一对（cap3_fixed / cap3_hc，相隔 19.5 小时、不同 GPU，论文自陈有混淆）：")
    body.append("#   host 侧 − 设备侧 = %+.2f 个点 —— 同卡这一对是 %s 的"
                % (g_old, "更强" if g_new >= g_old else "更弱"))
    body.append("# 前提检查：占用率差 %.2f%%（中位）/ %.2f%%（均值）、在跑数差 %.2f%%"
                "（阈值各 %.0f%%，两个占用统计量都要过）-> %s"
                % (cond_occ, cond_occ_m, cond_run, COND_PCT,
                   "成立" if controlled else "不成立"))
    body.append("# 判决：%s" % verdict)
    fields = list(rows[0].keys())
    body.append(",".join(fields))
    for r in rows:
        body.append(",".join(str(r[k]) for k in fields))
    out = "\n".join(body) + "\n"
    assert isinstance(out, str)          # CLAUDE.md：open(w) 先截断，写完先断言是 str
    with open(out_p, "w") as f:
        f.write(out)

    print("配对（同卡背靠背）")
    for r in rows[:2]:
        print("  %-9s %-11s 墙钟 %7s 分  R̄ %-9s 占用 %5s%%  τ₂ %5s  兑现 %6s%%"
              % (r["run"], r["side"], r["wall_min"], r["Rbar_busy"],
                 r["occ_p50_pct"], r["tau2_ms"], r["realized_pct"]))
    print("对照（现有那一对，有混淆）")
    for r in rows[2:]:
        print("  %-11s %-11s 墙钟 %7s 分  R̄ %-9s 占用 %5s%%  τ₂ %5s  兑现 %6s%%"
              % (r["run"], r["side"], r["wall_min"], r["Rbar_busy"],
                 r["occ_p50_pct"], r["tau2_ms"], r["realized_pct"]))
    print()
    print("  同卡这一对：%+.2f 个点（设备侧 %.2f%% -> host 侧 %.2f%%）" % (g_new, d_new, h_new))
    print("  现有那一对：%+.2f 个点（%.2f%% -> %.2f%%）" % (g_old, d_old, h_old))
    print("  前提：占用率差 %.2f%%（中位）/ %.2f%%（均值）、在跑数差 %.2f%% -> %s"
          % (cond_occ, cond_occ_m, cond_run, "成立" if controlled else "**不成立**"))
    print("  判决：%s" % verdict)
    print("-> %s" % out_p)


if __name__ == "__main__":
    main()
