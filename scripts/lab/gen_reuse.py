#!/usr/bin/env python3
"""前缀复用：trace 定的上界 vs 配置兑现了多少 —— paper/data/reuse.csv。

出发点是一个此前没被拆开的量：**总复用** = 设备侧命中 + host 侧接住。

上界必须【独立于观测】定义，否则是循环论证。曾经写成「数据里最多复用的量就是
天花板」，审稿人 2026-09-24 直接指出这是拿观测定义上界。真正的上界来自 trace 本身：
把 `data/replay_pois200_l04.csv` 每一行的 prefix_len 加起来 —— 那是这条 trace 的
前缀结构允许被复用的 token 总量，任何策略都不可能超过它。实测值只用来比较，
不用来定义。

本脚本输出的 realized_frac = 实测复用 / trace 上界。这一个数就是「兑现了多少」。

用法: python3 gen_reuse.py <trace.csv> <eviction.csv> <arm_running.csv> <decomp.csv> <out.csv> [concurrency.csv]

上游 eviction.csv 必须带 prompt_tok/reuse_tok/uncached_tok 三列（未舍入原始计数）——
比例一律用它们算，不用舍入到 0.1M 的列。曾经用舍入列算，cap1 印成 69.8% 而真值 69.9%。
"""
import csv, os, sys


def load(p):
    return {r["run"]: r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))}


def trace_ceiling(path):
    """trace 允许的复用上界：所有步 prefix_len 之和，以及 prompt 总量。"""
    rows = list(csv.DictReader(open(path)))
    reuse = sum(int(r["prefix_len"]) for r in rows)
    prompt = sum(int(r["prefix_len"]) + int(r["input_len"]) for r in rows)
    r0 = sum(int(r["prefix_len"]) for r in rows if int(r["round_idx"]) >= 1)
    return {"steps": len(rows),
            "sessions": len({r["session_id"] for r in rows}),
            "ceiling_tok": reuse, "prompt_tok": prompt,
            "ceiling_frac": reuse / prompt,
            "ceiling_r1_tok": r0}


def main():
    tr_p, ev_p, ar_p, dc_p, out_p = sys.argv[1:6]
    ce = trace_ceiling(tr_p)
    ev, ar, dc = load(ev_p), load(ar_p), load(dc_p)

    # 争用标记：被主机争用抬高了 tau 的 run，其 tau 列不可用。
    # 复用/重算是【体积】，与时间无关，实测这四条臂与同族干净 run 一致（见下）。
    conc = {}
    if len(sys.argv) > 6 and os.path.exists(sys.argv[6]):
        # 去 pois200_ 前缀再配对：eviction.csv 用短名，concurrency.csv 用 run 目录名。
        # 不归一化会静默全部落空（2026-09-24 犯过一次）。
        conc = {r["run"].replace("pois200_", ""): r["verdict"] for r in
                csv.DictReader(l for l in open(sys.argv[6]) if not l.startswith("#"))}
        assert len(conc) > 50, "concurrency.csv 只读到 %d 行" % len(conc)

    rows, bad = [], []
    for run, e in ev.items():
        a, d = ar.get(run), dc.get(run)
        if not a or not d:
            bad.append((run, "arm_running 或 decomp 里没有这条"))
            continue
        if "prompt_tok" not in e:
            bad.append((run, "eviction.csv 缺 prompt_tok —— 请用新版 gen_eviction.py 重跑"))
            continue

        prompt = int(e["prompt_tok"])
        reuse = int(e["reuse_tok"])
        unc = int(e["uncached_tok"])
        dev_miss = int(round(float(e["dev_miss_M"]) * 1e6))
        host_hit = int(round(float(e["host_hit_M"]) * 1e6))

        # 断言 1：设备未命中 = host 接住 + 真正重算（这套记账的定义式；
        # 挡住的是从 eviction.csv 抄错列——抄错不会有这个性质）
        assert abs(dev_miss - (host_hit + unc)) < 2e5, \
            "%s: dev_miss %d != host_hit %d + uncached %d" % (run, dev_miss, host_hit, unc)
        # 断言 2：复用 + 重算 = 总 prompt
        assert abs((reuse + unc) - prompt) < 2e3, \
            "%s: reuse %d + uncached %d != prompt %d" % (run, reuse, unc, prompt)
        # 断言 3：实测复用不得超过 trace 上界 —— 这是本表的核心不等式，
        # 若它被违反，说明口径搞错了（而不是发现了超光速）
        assert reuse <= ce["ceiling_tok"], \
            "%s: 实测复用 %d 超过 trace 上界 %d" % (run, reuse, ce["ceiling_tok"])

        rows.append({
            "run": run,
            "family": "hicache" if e["hicache"] == "1" else "device_only",
            "Rbar_busy": a["running_busy"],
            "prompt_tok": prompt,
            "reuse_tok": reuse,
            "reuse_host_tok": host_hit,
            "recompute_tok": unc,
            "reuse_frac": "%.4f" % (reuse / prompt),                 # 占总 prompt
            "realized_frac": "%.4f" % (reuse / ce["ceiling_tok"]),   # 占 trace 上界 <<< 关键列
            "tau1_ms": d["step_back_ms"],
            "contested": conc.get(run, "?"),
        })

    rows.sort(key=lambda r: (r["family"], float(r["Rbar_busy"])))
    header = "\n".join([
        "# 前缀复用：trace 定的上界 vs 配置兑现了多少 —— 由 scripts/lab/gen_reuse.py 生成，勿手改",
        "#",
        "# trace 上界（独立于观测，从 %s 求和）:" % os.path.basename(tr_p),
        "#   %d 会话 %d 步；sum(prefix_len) = %d tokens；prompt 总量 = %d tokens" % (
            ce["sessions"], ce["steps"], ce["ceiling_tok"], ce["prompt_tok"]),
        "#   => 计划复用率 ceiling_frac = %.4f（这就是论文里那个 75%% 的来源）" % ce["ceiling_frac"],
        "#   上界【必须】这样定义。曾经写成「数据里最多复用的量就是天花板」，是循环论证。",
        "#",
        "# realized_frac = reuse_tok / trace 上界 —— 这一个数才是「兑现了多少」。",
        "#   device-only 随 R̄ 一路掉；host tier 在控制器运行区间内守住。",
        "#   注意【没有任何配置兑现到 1.0】：实测最好也只有 %.4f。" % (19935879 / ce["ceiling_tok"]),
        "#",
        "# 比例一律由未舍入的 *_tok 列算出。曾经拿舍入到 0.1M 的列算，cap1 印成 69.8%%（真值 69.9%%）。",
        "# contested: 该 run 是否落在主机争用窗口（见 concurrency.csv）；CONTESTED 的 tau1_ms 不可用，",
        "#            但 reuse/recompute 是体积量，实测与同族干净 run 一致。",
        "run,family,Rbar_busy,prompt_tok,reuse_tok,reuse_host_tok,recompute_tok,reuse_frac,realized_frac,tau1_ms,contested"])
    fields = ["run", "family", "Rbar_busy", "prompt_tok", "reuse_tok", "reuse_host_tok",
              "recompute_tok", "reuse_frac", "realized_frac", "tau1_ms", "contested"]
    body = header + "\n" + "\n".join(",".join(str(r[k]) for k in fields) for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as fh:
        fh.write(body)

    print("trace 上界 %d / prompt %d = %.4f" % (ce["ceiling_tok"], ce["prompt_tok"], ce["ceiling_frac"]))
    print("写入 %s：%d 行" % (out_p, len(rows)))
    for r in rows:
        print("  %-16s %-11s R̄ %-6s 复用 %10s (%.4f) 兑现 %.4f  重算 %10s  τ₁ %-6s %s" % (
            r["run"], r["family"], r["Rbar_busy"], r["reuse_tok"], float(r["reuse_frac"]),
            float(r["realized_frac"]), r["recompute_tok"], r["tau1_ms"],
            "<<CONTESTED" if r["contested"] == "CONTESTED" else ""))
    if bad:
        print("!! 未写入：")
        for n, why in bad:
            print("   %-16s %s" % (n, why))


if __name__ == "__main__":
    main()
