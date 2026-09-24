#!/usr/bin/env python3
"""跨 trace 的复用兑现表 —— paper/data/reuse_x.csv（论文 §VI 的数字来源）。

为什么单独一个表：gen_reuse.py 只覆盖主 trace 的 13 条 run（它读的 eviction.csv
是 poisons200 专用）。§VI 引用了第二条 trace 的兑现率（74.8%、67.5%），那两个数
一度只存在于正文里、不在任何 CSV —— 违反本项目「每个数字都要能追到」的纪律。
这个脚本让它们有出处。

定义与 gen_reuse.py 逐字一致：
  上界 = sum(prefix_len) / sum(prefix_len + input_len)，从 trace 文件直接求和，
         独立于任何观测（runner 的 summary.json 也报同一个数，本脚本断言二者相符）
  实测复用 = prompt - uncached（steps.jsonl 的 server_uncached_prompt_tokens 累加）
  兑现率 = 实测复用 / 上界 —— 「兑现了多少」这个数

用法: python3 gen_reuse_x.py <trace.csv> <results_dir> <out.csv> <run> [<run> ...]
"""
import csv, json, os, statistics, sys


def trace_bound(path):
    rows = list(csv.DictReader(open(path)))
    pre = sum(int(r["prefix_len"]) for r in rows)
    tot = sum(int(r["prefix_len"]) + int(r["input_len"]) for r in rows)
    return pre, tot, pre / tot, len({r["session_id"] for r in rows}), len(rows)


def main():
    trace, root, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
    runs = sys.argv[4:]
    pre, tot, bound, nsess, nsteps = trace_bound(trace)

    rows, bad = [], []
    for r in runs:
        d = os.path.join(root, r)
        sp, mp, sj = (os.path.join(d, f) for f in ("steps.jsonl", "metrics.csv", "summary.json"))
        if not (os.path.exists(sp) and os.path.exists(sj)):
            bad.append((r, "缺 steps.jsonl 或 summary.json"))
            continue
        steps = [json.loads(l) for l in open(sp) if l.strip()]
        prompt = sum(s.get("prompt_len") or 0 for s in steps)
        unc = sum(s.get("server_uncached_prompt_tokens") or 0 for s in steps)
        reuse = prompt - unc

        # 断言 1：本脚本从 trace 求和得到的上界，必须等于 runner 自己报的
        # planned_prefix_hit_rate —— 两个独立来源，对不上说明口径搞错了
        sj_d = json.load(open(sj)).get("replay", {})
        if "planned_prefix_hit_rate" in sj_d:
            assert abs(sj_d["planned_prefix_hit_rate"] - bound) < 1e-4, \
                "%s: 本脚本算的上界 %.4f != runner 报的 %.4f" % (r, bound, sj_d["planned_prefix_hit_rate"])
        # 断言 2：实测复用不得超过上界
        assert reuse <= pre, "%s: 复用 %d 超过上界 %d" % (r, reuse, pre)

        rn = [float(x["sglang:num_running_reqs"]) for x in csv.DictReader(open(mp))
              if x.get("sglang:num_running_reqs")]
        occ = [float(x["sglang:token_usage"]) for x in csv.DictReader(open(mp))
               if x.get("sglang:token_usage")]
        busy = [v for v in rn if v > 0]
        rows.append({
            "run": r,
            "sessions": nsess, "steps": len(steps),
            "Rbar_busy": "%.6f" % (statistics.mean(busy) if busy else 0),
            "occ_p50_pct": "%.1f" % (statistics.median(occ) * 100 if occ else 0),
            "prompt_tok": prompt,
            "reuse_tok": reuse,
            "recompute_tok": unc,
            "reuse_frac": "%.4f" % (reuse / prompt) if prompt else "",
            "bound_frac": "%.4f" % bound,
            "realized_frac": "%.6f" % (reuse / pre),
        })

    rows.sort(key=lambda x: float(x["Rbar_busy"]))
    header = "\n".join([
        "# 跨 trace 的复用兑现 —— 由 scripts/lab/gen_reuse_x.py 生成，勿手改",
        "# trace: %s（%d 会话 %d 步）" % (os.path.basename(trace), nsess, nsteps),
        "# 上界 = %d / %d = %.4f，从 trace 的 prefix_len 求和，独立于观测；" % (pre, tot, bound),
        "#   与 runner summary.json 的 planned_prefix_hit_rate 断言相符。",
        "# 实测复用 = prompt - uncached（steps.jsonl），兑现率 = 实测 / 上界。",
        "# 用途：§VI 在第二条 trace 上重算同一组量。",
        "#   主 trace 的同一组量在 paper/data/reuse.csv（gen_reuse.py 生成）；两张表",
        "#   用同一套定义，合起来才是 §VI 那张跨 trace 对照。",
        "# 注意【兑现率跨 trace 不可用占用率概括】：",
        "#   这条 trace 在占用 15.8% 时兑现 0.7478，而主 trace 在占用 22.4% 时兑现 0.9255。",
        "run,sessions,steps,Rbar_busy,occ_p50_pct,prompt_tok,reuse_tok,recompute_tok,reuse_frac,bound_frac,realized_frac"])
    fields = ["run", "sessions", "steps", "Rbar_busy", "occ_p50_pct", "prompt_tok",
              "reuse_tok", "recompute_tok", "reuse_frac", "bound_frac", "realized_frac"]
    body = header + "\n" + "\n".join(",".join(str(r[k]) for k in fields) for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as fh:
        fh.write(body)

    print("trace 上界 %.4f；写入 %s：%d 行" % (bound, out_p, len(rows)))
    for r in rows:
        print("  %-16s R̄ %-6s 占用 %5s%%  兑现 %s" % (
            r["run"], r["Rbar_busy"], r["occ_p50_pct"], r["realized_frac"]))
    if bad:
        print("!! 未写入：")
        for n, why in bad:
            print("   %-16s %s" % (n, why))


if __name__ == "__main__":
    main()
