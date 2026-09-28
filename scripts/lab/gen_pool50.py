#!/usr/bin/env python3
"""池子对照实验：只动池子大小，兑现率变了多少 —— paper/data/pool50.csv。

**为什么要单独一个脚本**：半池的读数**不能直接和全池比**。池子小 ⇒ `static=N`
塞不下那么多会话 ⇒ **R̄ 自己也降了**（实测：半池 `cap2_hp` 的 R̄ 是 1.08，
全池 `cap2` 是 1.27）。拿 87.1% 比 89.7% 是**拿两个不同的工作点在比** ——
正是 `gen_frontier_split.py` 头注释点名的「跨配置外推」那类错。

正确做法：**在同一个 R̄ 上比**。全池那条「兑现率 ~ R̄」曲线在整数 cap 之间做
分段线性插值，取该 run 的 R̄ 处的参照值，差才是「池子变小的净效应」。

**口径**：R̄ 与兑现都用 `gen_a100.one()` 算（它调 `gen_decomp.busy_stats` 与
`gen_reuse.trace_ceiling`），**不另写一份实现** —— 上界 21,540,371 在
全池 / 半池 / A100 三处一致。

⚠ 2026-09-25 的改写（很重要）：原版用 `os.path.isdir` 判断 run 在不在，
于是**崩溃的 run 也会被当成读数** —— `cap3_hp` / `cap4_hp` 是引擎 OOM 死的
（`attempted_steps` 807 / 549，`failed_steps` 50 / 116），它们的目录**都在**、
还都写了 `summary.json`（`runner_rc=0`，误导性），原版会**静默地**从被删失的
样本里算出一个兑现值来。现在按**是否跑满 999 步且零失败**分类：

    status=OK          跑满 999 步、0 失败 -> 给出 R̄ / 兑现 / 净效应
    status=INFEASIBLE  没跑满（引擎崩了）  -> **R̄ 与兑现一律留空**，
                       只记 attempted/failed 供追溯，绝不从删失样本凑数

用法: python3 gen_pool50.py <results_dir> <out.csv>
"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_a100 as _A          # noqa: E402
import gen_reuse as _R         # noqa: E402

# (被测 run, 它的全池对照, 池子比例)
RUNS = [("cap2_hp", "cap2", "0.50"),
        ("cap3_hp", "cap3_fixed", "0.50"),
        ("cap4_hp", "cap4", "0.50"),
        ("cap3_p75", "cap3_fixed", "0.75")]
# 全池曲线的锚点（device-only 静态点，按 cap 升序）
FULL = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]
PLAN_STEPS = 999


# ⚠ 插值**不在这里实现** —— 调 `envelope.piecewise`（与 frontier.py 的 front_slo
# 同一份）。原来这里自己写了一份 `interp()`，边界容差与重合锚点的处理都不同，
# 而数值碰巧一致所以测试不会响。2026-09-26 codex 第 29 轮抓到（见 CLAUDE.md
# 「抽成共用只做了一半，等于没做」）。
import envelope as _ENV   # noqa: E402


def outcome(d, pool):
    """这个 run 能不能当兑现率读数用。**三条判据，缺一不可**：

    1. 跑满 999 步、0 失败（`summary.json` 的两个计数）——
       **不看目录在不在、不看 `runner_rc`**：崩掉的 run 也写 summary、
       也写 `runner_rc=0`（`stop_session_on_error` 让所有会话到终态，runner 就正常退出）。
    2. **每一步都真的被服务了**：计划 prompt 之和 == 实测 `server_prompt_tokens` 之和。
       2026-09-25 独立复算抓到：半池的 `cap2_hp` 有 **104/999 步**被引擎服务成
       **1-token 退化响应**（`server_prompt_tokens=1`、`first_token_ms=None`、
       `finish_reason=None`、**`error=None`**，runner 记成 SUCCESS），
       计划 prompt 整块没进实测和，被 `prompt - uncached` 算成了「复用」——
       兑现率虚报成 87.12%，而引擎自报命中只有 56.88%。**差 30 pp，一度进了正文。**
       第 1 条判据**够不到**它：runner 的 `failed` 全程是 0。
    3. 池子对齐（由 lane 的守卫保证，不在这里查）。

    返回 (usable, attempted, failed, gap, unserved)。
    """
    import json
    sp = os.path.join(d, "summary.json")
    if not os.path.exists(sp):
        return None, None, None, None, None
    r = json.load(open(sp)).get("replay", {})
    a, f = r.get("attempted_steps"), r.get("failed_steps")
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    plan = sum(s.get("prompt_len") or 0 for s in st)
    meas = sum(s.get("server_prompt_tokens") or 0 for s in st)
    # ⚠ **两种坏法必须分开数**（2026-09-26 独立复算抓到：我原来把两者并成一个
    # `unserved_steps`，于是 `cap2_hp`（0 报错行）两种口径恰好重合，
    # **掩盖了 cap3_hp 的 122 = 72+50、cap4_hp 的 155 = 39+116**）：
    #   degenerate —— 引擎返回 1-token 退化响应而 runner 记成【成功】。
    #                  这是**安静的**：`failed_steps` 全程为 0。
    #   error      —— 引擎报错行（`server_prompt_tokens is None`）。
    #                  这是**响亮的**：`failed_steps` 里数得到。
    # 论文讲的是前者；把它们并起来会自相矛盾（一边说「失败计数为 0」，一边把 50 条报错算进去）。
    # ⚠ **逐步判据，不是比总和**。2026-09-26 codex r29 给了个构造：
    # 在一条干净 run 的两个步上把实测数分别 +1 / −1，逐步已有两处错配，
    # 而**总和不变** —— 只比总和会让它静默通过。
    degenerate = sum(1 for s in st
                     if s.get("prompt_len") is not None
                     and s.get("server_prompt_tokens") is not None
                     and s["prompt_len"] != s["server_prompt_tokens"])
    err = sum(1 for s in st if s.get("server_prompt_tokens") is None)
    # 报错步里【prompt 没超池】的那些 —— §III 用它把「长度门槛」与「OOM 崩溃」
    # 两条链分开：cap3_hp 的 50 个报错步里 49 个的 prompt 是装得下的，
    # 所以门槛解释不了它们。
    err_under = sum(1 for s in st if s.get("server_prompt_tokens") is None
                    and (s.get("prompt_len") or 0) <= pool)
    # 真正的判据：**prompt 超过池子就服务不了**。做成机械的，与退化步数对拍。
    over = sum(1 for s in st if (s.get("prompt_len") or 0) > pool)
    plan_all = plan
    # 判据 2 改成**逐步**：任何一步的 prompt_len 与实测不等就不算跑干净。
    # （原来只比 `plan == meas`，逐步错配会互相抵消。）
    stepwise_clean = degenerate == 0
    ok = (a == PLAN_STEPS and f == 0 and plan == meas and stepwise_clean)
    # 长度门槛的两个端点：超池的最小 prompt、被服务过的最大 prompt。
    # §III 引它们就是为了说明这个门槛是**精确的**（差 4 个 token），所以列在表里。
    over_pl = [s["prompt_len"] for s in st if (s.get("prompt_len") or 0) > pool]
    served = [s["prompt_len"] for s in st
              if s.get("prompt_len") is not None and s.get("server_prompt_tokens") is not None
              and s["prompt_len"] == s["server_prompt_tokens"]]
    # 第二个口径：这些步**本该复用**的 prefix token 之和 —— 与「计划 prompt 之和」
    # 是两个不同的量（prompt > prefix），正文两个都写（2026-09-26 独立复核指出
    # 只写前一个会让读者把两者当成一回事）。
    px = sum(s.get("prefix_len") or 0 for s in st
             if s.get("server_prompt_tokens") == 1 and (s.get("prompt_len") or 0) > 1)
    return (ok, a, f, plan - meas, degenerate, err, over, plan_all,
            min(over_pl) if over_pl else None, max(served) if served else None, err_under, px)


def main():
    # `--pending a,b` 声明哪些 run **还在跑**（而不是缺失）。缺失仍然报错退出 ——
    # 这个区分是必须的：`cap3_p75` 在 0.75× 上跑着，它不在镜像里是正常的；
    # 而 `cap2_hp` 不在镜像里就是镜像不全，那时写出来的表少一条、结论就不同。
    argv = [a for a in sys.argv[1:] if not a.startswith("--pending")]
    pending = set()
    for a in sys.argv[1:]:
        if a.startswith("--pending"):
            pending = set(x.strip() for x in a.split("=", 1)[1].split(",") if x.strip())
    root, out_p = argv[0], argv[1]
    trace_p = os.path.join(HERE, "..", "..", "data", "replay_pois200_l04.csv")
    pre = _R.trace_ceiling(trace_p)["ceiling_tok"]   # 它返回的是字典，不是元组

    # 全池曲线：**缺锚点直接退出**，别写半张表
    full_pts, full_row = [], {}
    for r in FULL:
        d = os.path.join(root, "pois200_" + r)
        if not os.path.isdir(d):
            raise SystemExit("!! 全池的 %s 不在镜像里，别写半张表" % r)
        x = _A.one(d)
        full_row[r] = x
        full_pts.append((float(x["Rbar_busy"]), x["reuse_tok"] / pre * 100))

    rows, absent = [], []
    for hp, fu, frac in RUNS:
        d = os.path.join(root, "pois200_" + hp)
        if not os.path.isdir(d):
            if hp in pending:
                print("  %-9s 还在跑（--pending 声明过），本表不出这一行" % hp)
            else:
                absent.append(hp)
            continue
        m = json.load(open(os.path.join(d, "metadata.json")))
        pool = m.get("pool_tokens") or 0
        (ok, att, fail, gap, degen, err, over, plan_all,
         min_over, max_served, err_under, px) = outcome(d, pool)
        if ok is None:
            absent.append(hp + "（无 summary）")
            continue
        if not ok:
            # **不从删失 / 未被真正服务的样本算兑现值。** 两种坏法：
            #   (a) gap == 0 而步数/失败数不对 -> 引擎崩了（OOM）
            #   (b) gap > 0                     -> 有步骤被服务成退化响应（1 token），
            #       计划 prompt 被算成了复用 —— **它看起来「跑完了」，所以更危险**
            if degen:
                n_step = sum(1 for _ in open(os.path.join(d, "steps.jsonl")))
                why = ("%d/%d 步的 prompt 超过池子（%d tokens）—— 引擎返回 1-token 退化响应"
                       "而 runner 记成成功（`failed_steps` 全程为 0，所以这是【安静】的）；"
                       "计划 prompt 与实测差 %d tokens，`prompt - uncached` 会把缺口算成复用"
                       % (degen, n_step, pool, gap))
                if over != degen:
                    why += "；⚠ 与「prompt_len > 池子」的步数（%d）不符，需人工查" % over
            else:
                why = ("引擎 OOM：池子被活请求占满（evictable_size=0）未跑满 %d/%d 步"
                       % (att, PLAN_STEPS))
            rows.append(dict(run=hp, pool_frac=frac, full=fu, status="INFEASIBLE",
                             attempted_steps=att, failed_steps=fail,
                             degenerate_steps=degen, error_steps=err,
                             error_under_pool=err_under,
                             steps_over_pool=over,
                             min_over_pool_tok=min_over, max_served_tok=max_served,
                             prompt_gap_tok=gap,
                             gap_pct_of_bound="%.1f" % (100.0 * gap / pre),
                             # 这些步本该复用的 prefix token 占同一个上界的比例 ——
                             # **与上面那一列不是同一个量**，正文两个都印。
                             gap_pct_of_prefix="%.1f" % (100.0 * px / pre),
                             gap_pct_of_prompt="%.1f" % (100.0 * gap / plan_all),
                             half_Rbar="", half_real="",
                             full_real_at_same_Rbar="", delta_pp="",
                             note=why + "；见 docs/finding_pool50_cap4_oom_20260925.md"))
            continue
        x = _A.one(d)
        rb = float(x["Rbar_busy"])
        real = x["reuse_tok"] / pre * 100
        ref = _ENV.piecewise(rb, full_pts)   # 全池曲线在同一个 R̄ 上的参照值
        rows.append(dict(run=hp, pool_frac=frac, full=fu, status="OK",
                         attempted_steps=att, failed_steps=fail,
                         degenerate_steps=0, error_steps=0, error_under_pool=0,
                         steps_over_pool=0,
                         min_over_pool_tok="", max_served_tok="",
                         prompt_gap_tok=0, gap_pct_of_bound="0.0",
                         gap_pct_of_prefix="0.0", gap_pct_of_prompt="0.0",
                         half_Rbar="%.4f" % rb,
                         half_real="%.4f" % real,
                         full_real_at_same_Rbar=("" if ref is None else "%.4f" % ref),
                         delta_pp=("" if ref is None else "%+.2f" % (real - ref)),
                         note=("" if ref is None else "同 R̄ 上池子变小的净效应")))
    if absent:
        # **缺了要报，不静默跳过** —— 少一条结论就不同
        raise SystemExit("!! 池子对照还缺这些 run：%s —— 等齐了再写表" % "、".join(absent))

    with open(out_p, "w", newline="") as f:
        f.write("# 池子对照实验：只动池子大小（全池 101432）的净效应 —— gen_pool50.py 生成，勿手改\n")
        f.write("# ⚠ 不能直接拿小池子的兑现去比全池的兑现：**R̄ 自己也降了**。\n")
        f.write("#   本表在**同一 R̄** 上用全池曲线插值取参照（超出锚点范围不给参照，不端点外推）。\n")
        f.write("# 口径：R̄ 与兑现都由 gen_a100.one() 算（共用 gen_decomp / gen_reuse 的定义）。\n")
        f.write("# 上界（trace 的 prefix_len 之和）= %d\n" % pre)
        # 「池子 < trace 最长 prompt」的 run 不止本表这四条 —— §III 的全称量词
        # （every step that comes back as a success carrying a single token has a
        #  prompt larger than the pool）覆盖的是全部六条。另外两条在**另一条 trace**
        # 上，所以不进本表，但数要留在这里供追溯（2026-09-26 实测）：
        f.write("# 另两条（别的 trace，池子也小于各自的最长 prompt）：\n")
        f.write("#   load50_default  池=76018  步=249  退化=7  超池=7\n")
        f.write("#   load25_budget   池=72647  步=125  退化=1  超池=1\n")
        f.write("# 两条崩掉的 run 里「超池」比「退化」多（73 vs 72、41 vs 39）——\n")
        f.write("#   差额是**报错步**（崩溃那条链），所以等式只在【不崩的 run】里成立。\n")
        f.write("# status=INFEASIBLE 的行**没有兑现率**，两种坏法（见 note 列）：\n")
        f.write("#   (a) degenerate_steps > 0 —— 引擎把 1-token 退化响应记为成功，\n")
        f.write("#       `prompt - uncached` 会把没服务的缺口算成复用（安静，failed 为 0）；\n")
        f.write("#   (b) error_steps > 0 —— 引擎崩了/请求失败（响亮，failed_steps 里数得到）。\n")
        f.write("#   两种都不产生可用的兑现率：活下来的都是有偏的样本。\n")
        w = csv.DictWriter(f, fieldnames=["run", "pool_frac", "full", "status",
                                          "attempted_steps", "failed_steps",
                                          "degenerate_steps", "error_steps",
                                          "error_under_pool",
                                          "steps_over_pool", "min_over_pool_tok",
                                          "max_served_tok", "prompt_gap_tok",
                                          "gap_pct_of_bound", "gap_pct_of_prefix",
                                          "gap_pct_of_prompt",
                                          "half_Rbar", "half_real",
                                          "full_real_at_same_Rbar", "delta_pp", "note"])
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out_p, len(rows)))
    for r in rows:
        if r["status"] == "OK":
            print("  %-9s 池=%-5s R̄=%-8s 兑现 %5s%%   同 R̄ 全池参照 %5s%%   净效应 %s pp"
                  % (r["run"], r["pool_frac"], r["half_Rbar"], r["half_real"],
                     r["full_real_at_same_Rbar"], r["delta_pp"]))
        else:
            # 打印**具体**原因，不要一律印「引擎 OOM」—— 两种坏法不一样
            # （崩掉 vs 服务成 1-token 但记成功），混着印会让人以为 cap2_hp 也崩了。
            print("  %-9s 池=%-5s **INFEASIBLE**  退化=%-4s 报错=%-4s 超池=%-4s  缺口占上界 %s%%"
                  % (r["run"], r["pool_frac"], r["degenerate_steps"], r["error_steps"],
                     r["steps_over_pool"], r["gap_pct_of_bound"]))


if __name__ == "__main__":
    main()
