#!/usr/bin/env python3
"""并发争用探针 —— 在【实验机】上跑（需要 results/night/<run>/steps.jsonl）。

回答一个问题：同一台机器上同时跑几条 run 时，每条 run 的
τ₂（逐请求 decode 间隔中位，客户端实测，不经采样器）会不会被抬高。

用法: python3 probe_concurrency.py <results_dir> <run> [run ...]
"""
import json, statistics, datetime, sys, os


def tau2_bins(root, run, nb=16):
    steps = [json.loads(l) for l in open(os.path.join(root, run, "steps.jsonl")) if l.strip()]
    ok = [s for s in steps
          if (s.get("output_len_actual") or 0) >= 32 and s.get("status") == "SUCCESS"]
    t0 = min(s["submit_timestamp"] for s in steps)
    t1 = max(s["complete_timestamp"] for s in steps)
    B = [[] for _ in range(nb)]
    for s in ok:
        u = (s["submit_timestamp"] - t0) / (t1 - t0)
        B[min(nb - 1, int(u * nb))].append(
            (s["total_duration_ms"] - s["first_token_ms"]) / max(1, (s["output_len_actual"] - 1)))
    med = [(statistics.median(b) if b else float("nan")) for b in B]
    return t0, t1, med, len(ok)


def fmt(t):
    return datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M")


def main():
    root = sys.argv[1]
    for run in sys.argv[2:]:
        t0, t1, med, n = tau2_bins(root, run)
        vals = [m for m in med if m == m]
        print("=== %-28s %s -> %s   n=%d  全程中位 %.1f  binned min %.1f max %.1f  (max/min %.2f)"
              % (run, fmt(t0), fmt(t1), n, statistics.median(vals),
                 min(vals), max(vals), max(vals) / min(vals)))
        for i, v in enumerate(med):
            tb = t0 + (t1 - t0) * (i + 0.5) / len(med)
            bar = "#" * int(max(0, (v - 18)) * 2) if v == v else ""
            print("    %s  %5.1f  %s" % (fmt(tb), v, bar))
        print()


if __name__ == "__main__":
    main()
