#!/usr/bin/env python3
"""生成 paper/data/eviction.csv —— 论文 §3.3 里「驱逐 → 重算」那条因果链的数据。

为什么要有这个脚本：这条链子曾经被错误地"反驳"过，用的两个检验都是恒等式：

  1. "total prefilled tokens == planned prefill, ratio 1.00"
     `sglang:prompt_tokens_total` 计的是**完整提交的 prompt 长度，含 cached 部分**，
     所以它恒等于 sum(prompt_len)，不管重算多少都不会变。这是个恒等式。
     能测出重算的是 `server_uncached_prompt_tokens`，本脚本报的就是它。

  2. "SGLang reports zero retractions"
     radix cache 驱逐记在 `sglang:evicted_tokens_total`；retraction 指的是
     抢占**正在跑**的请求，是另一件事、另一个计数器。拿后者反驳前者是范畴错误。

正确的读法（本脚本的输出）：
  - 设备侧未命中 = 设备没接住的量（prompt − cached_tokens_total）
  - 重算量 = steps 里的 server_uncached_prompt_tokens（真正重新 prefill 的）
  - 两者之差 = host 梯队接住的量
  - 无 HiCache 的五条：host 接住【精确为 0】，设备未命中 == 重算量，1:1
  - 有 HiCache 的八条：host 接住 13~19M
  - 但 HiCache 那一族的 τ 仍然散开（重算恒定 8.7M，τ 22.5~30.6ms）→ 未解释

用法: python3 gen_eviction.py <results_dir> <out.csv> [run ...]
"""
import csv, json, os, statistics, sys, glob

HEADER = ["run", "hicache", "prompt_M", "dev_miss_M", "host_hit_M", "uncached_M",
          "evicted_M", "running", "step_back_ms", "step_perreq_ms"]
SAMPLE_S = 5.0

RUNS = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5", "pairB_cap2hc", "cap3_hc",
        "cap4_hc", "foyer_hc", "foyer_hz1", "foyer_hz2", "foyer_hz0", "foyer_bres"]


def last_value(path, name):
    """取某一列最后一个有效值（这些是累计计数器）。"""
    hdr = open(path).readline().strip().split(",")
    if name not in hdr:
        return None
    i = hdr.index(name)
    v = None
    for line in open(path).readlines()[1:]:
        c = line.rstrip("\n").split(",")
        if len(c) <= i:
            continue
        try:
            v = float(c[i])
        except ValueError:
            pass
    return v


def col(path, name):
    hdr = open(path).readline().strip().split(",")
    if name not in hdr:
        return []
    i = hdr.index(name)
    out = []
    for line in open(path).readlines()[1:]:
        c = line.rstrip("\n").split(",")
        if len(c) <= i:
            continue
        try:
            out.append(float(c[i]))
        except ValueError:
            pass
    return out


def main():
    root, out_path = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    rows, bad = [], []
    for r in runs:
        d = os.path.join(root, "pois200_" + r)
        mp = os.path.join(d, "metrics.csv")
        sp = os.path.join(d, "steps.jsonl")
        if not (os.path.exists(mp) and os.path.exists(sp)):
            bad.append((r, "缺 metrics.csv 或 steps.jsonl"))
            continue
        try:
            prompt = last_value(mp, "sglang:prompt_tokens_total")
            cached = last_value(mp, "sglang:cached_tokens_total")
            evicted = last_value(mp, "sglang:evicted_tokens_total")
            steps = [json.loads(l) for l in open(sp) if l.strip()]
            uncached = sum(s.get("server_uncached_prompt_tokens") or 0 for s in steps)
            plan = sum(s.get("prompt_len") or 0 for s in steps)

            # 断言 1：prompt_tokens_total 必须等于计划 prefill —— 这是恒等式，
            # 挡住的是列读错（读错列不会有这个性质）
            assert prompt and abs(prompt - plan) / plan < 0.01, \
                "prompt_tokens_total %.1fM 与计划 %.1fM 不符，列可能读错了" % (
                    (prompt or 0) / 1e6, plan / 1e6)

            # 断言 2：cached 必须是 prompt 的一部分（不是独立的量）
            assert cached is not None and 0 <= cached <= prompt * 1.01, \
                "cached_tokens_total 不在 [0, prompt] 内"
            # 注意：prompt − cached == steps 的未命中数，这条【只在无 HiCache 时成立】。
            # 有 HiCache 时两者差很多（cap4_hc: 22.4M vs 9.1M），因为
            # sglang:cached_tokens_total 只计【设备侧】radix cache 的命中，
            # host 梯队接住的那部分不进这个计数器，但逐请求 usage 里算作 cached。
            # 所以本表以 steps 的未命中数为准（那才是真正重新 prefill 的量），
            # 并把设备侧命中单列出来，两者的差就是 host 梯队的贡献。
            dev_miss = prompt - cached   # 设备侧未命中

            rn = col(mp, "sglang:num_running_reqs")
            # metadata.json 里没有 hicache_enabled 这个键（核过），所以按已知
            # 配置判定：HiCache 只在这些 run 上开。这比猜 metadata 的键名可靠。
            HC = {"pairB_cap2hc", "cap3_hc", "cap4_hc", "foyer_hc",
                  "foyer_hz1", "foyer_hz2", "foyer_hz0", "foyer_bres"}
            rows.append({
                "run": r,
                "hicache": "1" if r in HC else "0",
                "prompt_M": round(prompt / 1e6, 1),

                "uncached_M": round(uncached / 1e6, 1),
                "evicted_M": round((evicted or 0) / 1e6, 1),
                "dev_miss_M": round(dev_miss / 1e6, 1),
                "host_hit_M": round((dev_miss - uncached) / 1e6, 1),   # 设备没接住、但也没重算的
                "running": round(statistics.mean(rn), 2) if rn else "",
                "step_back_ms": "", "step_perreq_ms": "",
            })
        except Exception as e:
            bad.append((r, str(e)))

    if bad:
        print("!! 未通过校验：")
        for r, why in bad:
            print("   %-14s %s" % (r, why))

    with open(out_path, "w", newline="") as f:
        f.write("# 驱逐 vs 重算 —— 由 scripts/lab/gen_eviction.py 生成，勿手改\n")
        f.write("# dev_miss_M: prompt - cached_tokens_total —— 【设备侧】没接住的部分\n")
        f.write("# host_hit_M: dev_miss - uncached —— 设备没接住、但也没重算的那部分 = host 梯队接住的。\n#             无 HiCache 时精确为 0（五条全是），有 HiCache 时 13~19M\n")
        f.write("# uncached_M: steps.jsonl 的 server_uncached_prompt_tokens 累加（真正重新 prefill 的量）\n")
        f.write("# evicted_M: metrics.csv 的 sglang:evicted_tokens_total 末值\n")
        f.write("# host_hit_M 是最关键的一列：无 HiCache 的五条精确为 0.0，有 HiCache 的八条 13~19M。\n")
        f.write("# evicted_M 单列出来只作参照——驱逐量本身不决定重算量，dev_miss 才决定。\n")
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out_path, len(rows)))
    for r in rows:
        print("  %-13s hc=%s 设备未命中 %5.1fM host命中 %5.1fM 重算 %5.1fM 驱逐 %5.1fM" % (
            r["run"], r["hicache"], r["dev_miss_M"], r["host_hit_M"],
            r["uncached_M"], r["evicted_M"]))


if __name__ == "__main__":
    main()
