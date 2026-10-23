#!/usr/bin/env python3
"""从一条 run 的 steps.jsonl 反解引擎常数：冷 prefill 速率 R、冷 prefill 时延、暖步 TTFT。

用法：python3 gen_engine_constants.py <run_dir> [--csv out.csv]

## 为什么要单独一个脚本

论文 §III/§V 的 T_rev/T_rec 公式里要用 R（tok/s）和冷 prefill 时延。这两个数
**必须是测出来的**，不能从别处抄，也不能用卡的理论算力估。它们只能从"冷启动步"里反解：

    冷步判据   server_uncached_prompt_tokens / server_prompt_tokens > 0.9
    R         = prompt_tokens / (first_token_ms/1000)      （每步一个样本，取中位）
    冷时延    = first_token_ms

暖步（uncached 占比 < 0.2）的 TTFT 另外报，因为它里面**混着排队**（被别的长 prefill
挡住），不能当 prefill 时间用。

⚠ 这些数随负载变化：同一条 run 前后段的 R 不同。CSV 里带 run 名与样本数，
正文引用时必须说明是在哪条 run、多少个样本上测的。
"""
import json
import os
import statistics as st
import sys


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    d, csv_out = argv[0], None
    i = 1
    while i < len(argv):
        if argv[i] == "--csv":
            i += 1
            csv_out = argv[i]
        i += 1

    rows = []
    for line in open(os.path.join(d, "steps.jsonl")):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("status") != "SUCCESS" or not r.get("first_token_ms"):
            continue
        if not r.get("server_prompt_tokens"):
            continue
        rows.append(r)

    cold = [r for r in rows
            if r["server_uncached_prompt_tokens"] / r["server_prompt_tokens"] > 0.9]
    warm = [r for r in rows
            if r["server_uncached_prompt_tokens"] / r["server_prompt_tokens"] < 0.2]

    def q(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(len(xs) * p))]

    R = [r["server_prompt_tokens"] / (r["first_token_ms"] / 1000.0) for r in cold]
    out = [
        ("run", os.path.basename(d.rstrip("/")), "", "run 目录名"),
        ("n_steps", len(rows), "steps", "SUCCESS 且 first_token_ms 非空"),
        ("n_cold", len(cold), "steps", "uncached/prompt > 0.9"),
        ("n_warm", len(warm), "steps", "uncached/prompt < 0.2"),
        ("cold_prefill_p50_s", round(q([r["first_token_ms"] / 1000 for r in cold], .5), 1), "s", ""),
        ("cold_prefill_p90_s", round(q([r["first_token_ms"] / 1000 for r in cold], .9), 1), "s", ""),
        ("prefill_rate_p50_tok_s", round(q(R, .5)), "tok/s", "prompt/(ttft) 的中位（冷步）"),
        ("prefill_rate_p90_tok_s", round(q(R, .9)), "tok/s", ""),
        ("warm_ttft_p50_s", round(q([r["first_token_ms"] / 1000 for r in warm], .5), 2), "s",
         "暖步 TTFT（含排队，不是纯 prefill）"),
        ("warm_ttft_p90_s", round(q([r["first_token_ms"] / 1000 for r in warm], .9), 2), "s", ""),
    ]
    for k, v, u, note in out:
        print("%-24s %12s %-8s %s" % (k, v, u, note))

    if csv_out:
        import csv as _csv
        os.makedirs(os.path.dirname(os.path.abspath(csv_out)), exist_ok=True)
        with open(csv_out, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["key", "value", "unit", "note", "source"])
            for k, v, u, note in out:
                w.writerow([k, v, u, note, d])
        print("\n写 %s（%d 行）" % (csv_out, len(out)))


if __name__ == "__main__":
    main(sys.argv[1:])
