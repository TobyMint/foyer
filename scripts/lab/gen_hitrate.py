#!/usr/bin/env python3
"""round-1+ 命中率序列 —— paper/data/hitrate.csv。

为什么要有：§related 引用「无 HiCache 时 80.8/78.5/70.6/56.0/32.8%，有 HiCache 时
80.7/79.6/78.7%，控制器 80.6%」以及「计划值 80.9%」。这一串数是从 steps.jsonl 的
server_prefix_hit_rate 逐步算的，此前不在任何 CSV 里（审计报了 8 处"找不到源头"）。

⚠ 口径（正文必须与表头一致，混了会被审稿人抓）：
  这是【观测】的 server 命中率，round>=1 的【逐步非加权均值】。
  它与 gen_reuse.py 的 reuse_frac 是同一现象的不同归一化：
    - 本表：只取 round>=1，逐步非加权
    - reuse_frac：全部步，按 prompt token 加权
  两者不可互相换算，也不能混引。计划的 round-1+ 值恒为 80.9%，不随 cap 变。

用法: python3 gen_hitrate.py <results_dir> <out.csv> <run> [<run> ...]
"""
import csv, json, os, statistics, sys


def round1_mean(path):
    st = [json.loads(l) for l in open(path) if l.strip()]
    r1 = [s for s in st if s.get("round_idx", 0) >= 1]
    if not r1:
        return None, None, 0
    obs = statistics.mean(s.get("server_prefix_hit_rate") or 0 for s in r1)
    plan = statistics.mean(s.get("planned_prefix_hit_rate") or 0 for s in r1)
    return obs, plan, len(r1)


def main():
    root, out_p = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:]
    rows = []
    for r in runs:
        p = os.path.join(root, r, "steps.jsonl")
        if not os.path.exists(p):
            print("!! 缺 %s" % p); continue
        obs, plan, n = round1_mean(p)
        if obs is None:
            print("!! %s 没有 round>=1 的步" % r); continue
        rows.append({"run": r, "n_round1_steps": n,
                     "observed_round1_pct": "%.1f" % (obs * 100),
                     "planned_round1_pct": "%.2f" % (plan * 100)})
    header = "\n".join([
        "# round-1+ 命中率 —— 由 scripts/lab/gen_hitrate.py 生成，勿手改",
        "# 口径：观测的 server_prefix_hit_rate，round>=1，逐步【非加权均值】",
        "# ⚠ 与 reuse.csv 的 reuse_frac 不是一回事（那个是全部步、按 token 加权），",
        "#   两者不可换算、不可混引。planned_round1_pct 是 trace 常量，不随 cap 变。",
        "run,n_round1_steps,observed_round1_pct,planned_round1_pct"])
    fields = ["run", "n_round1_steps", "observed_round1_pct", "planned_round1_pct"]
    body = header + "\n" + "\n".join(",".join(str(x[k]) for k in fields) for x in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as fh:
        fh.write(body)
    print("写入 %s：%d 行" % (out_p, len(rows)))
    for x in rows:
        print("  %-20s round>=1 n=%3d  观测 %5s%%  计划 %s%%" % (
            x["run"], x["n_round1_steps"], x["observed_round1_pct"], x["planned_round1_pct"]))


if __name__ == "__main__":
    main()
