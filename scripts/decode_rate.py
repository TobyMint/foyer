#!/usr/bin/env python3
"""Per-request decode rate vs concurrency, with the confounds controlled.

Why this replaces the counter-based curve (batching_curve.py). That script derived a
rate from the deltas of `generation_tokens_total` between 5-second scrapes. Two
things were wrong with it:

  1. The engine's counters do not update every scrape. They move in batches about
     every 10 seconds, so a burst lands entirely in whichever scrape happened to
     catch it and the intervening scrapes read zero. Averaging over scrapes then
     understates the rate by roughly 25% at low concurrency, which is exactly where
     the comparison of interest lives. (Measured on pois200_cap2: the same data gives
     33.5 tok/s by scrape-delta and 45.1 tok/s by counter-update period.)

  2. Once corrected, the 1->2 jump was +47%, not the +86% first reported, AND the
     t=2 periods turned out to process proportionally less prefill (prompt/generate
     ratio 39.7 vs 44.5) at a higher cache hit rate (58.7% vs 53.1%). So part of the
     apparent batching gain was really "less recompute per generated token".

This script sidesteps both problems by using steps.jsonl, which records per REQUEST:
submit and complete timestamps, time to first token, output length, and the prefix
hit rate for that request. Decode rate is then

    (output_len - 1) / (total_duration - first_token_ms)

the first token arriving at TTFT, so the remaining tokens are spread over what is
left. Concurrency comes from joining the request's [submit, complete] window against
the num_running_reqs series. Hit rate needs no joining at all — it is on the row.

Steps are filtered to a minimum output length: short rounds are truncated by
finish_reason=length and their "rate" is an artefact of where the cut fell.

    decode_rate.py [--dir DIR] [--runs r1,r2,...]
"""
import argparse
import collections
import csv
import json
import os
import sys

DEFAULT_DIR = "/data/xbw/turnstile/results/night"
DEFAULT_RUNS = ["pois200_cap2", "pois200_foyer", "pois200_foyer_t85",
                "pois200_cap4", "pois200_foyer_rl90", "pois200_foyer_rl99"]
MIN_OUTPUT = 32        # below this, finish_reason=length truncates and rate is noise
MIN_STEPS = 20         # per bucket, or the mean is not worth printing


def load_conc(path):
    ts, running = [], []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            try:
                ts.append(float(row["ts"]))
                running.append(float(row["sglang:num_running_reqs"]))
            except (ValueError, TypeError, KeyError):
                pass
    return ts, running


def mean_conc(ts, running, t0, t1):
    vals = [r for t, r in zip(ts, running) if t0 <= t <= t1]
    return sum(vals) / len(vals) if vals else None


def steps_of(path):
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("status") != "SUCCESS":
                continue
            n_out = r.get("output_len_actual") or 0
            dur = r.get("total_duration_ms")
            ttft = r.get("first_token_ms")
            t0, t1 = r.get("submit_timestamp"), r.get("complete_timestamp")
            if not (t0 and t1) or dur is None or ttft is None:
                continue
            if n_out < MIN_OUTPUT:
                continue
            decode_ms = dur - ttft
            if decode_ms <= 0:
                continue
            out.append({
                "rate": (n_out - 1) / (decode_ms / 1000.0),
                "t0": t0, "t1": t1,
                "hit": r.get("server_prefix_hit_rate"),
                "prompt": r.get("server_uncached_prompt_tokens") or 0,
                "ctx": r.get("prompt_len") or 0,
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--runs", default=",".join(DEFAULT_RUNS))
    args = ap.parse_args()

    print("逐请求解码速率 = (output_len-1) / (total_duration - TTFT)   "
          "只保留 output_len >= %d\n" % MIN_OUTPUT)
    print("%-22s %-4s %8s %10s %9s %9s %9s" %
          ("run", "conc", "n", "tok/s", "命中率", "未缓存prompt", "上下文"))

    bucket = collections.defaultdict(list)
    for name in args.runs.split(","):
        d = os.path.join(args.dir, name)
        mp, sp = os.path.join(d, "metrics.csv"), os.path.join(d, "steps.jsonl")
        if not (os.path.exists(mp) and os.path.exists(sp)):
            print("skip %s (缺文件)" % name)
            continue
        ts, running = load_conc(mp)
        by = collections.defaultdict(list)
        for s in steps_of(sp):
            c = mean_conc(ts, running, s["t0"], s["t1"])
            if c is None:
                continue
            by[int(round(c))].append(s)
        for k in (1, 2, 3, 4):
            v = by.get(k) or []
            if len(v) < MIN_STEPS:
                continue
            n = len(v)
            rate = sum(x["rate"] for x in v) / n
            hits = [x["hit"] for x in v if x["hit"] is not None]
            unc = sum(x["prompt"] for x in v) / n
            ctx = sum(x["ctx"] for x in v) / n
            bucket[k].append((rate, sum(hits) / len(hits) if hits else 0.0, unc, ctx))
            print("%-22s %-4d %8d %10.1f %8.1f%% %9.0f %9.0f" %
                  (name, k, n, rate, 100 * (sum(hits) / len(hits) if hits else 0),
                   unc, ctx))

    print("\n跨 run 汇总")
    print("%-6s %-4s %10s %9s %11s %9s" %
          ("conc", "runs", "tok/s", "命中率", "未缓存prompt", "上下文"))
    for k in sorted(bucket):
        v = bucket[k]
        if not v:
            continue
        m = lambda i: sum(x[i] for x in v) / len(v)
        print("%-6d %-4d %10.1f %8.1f%% %11.0f %9.0f" %
              (k, len(v), m(0), 100 * m(1), m(2), m(3)))

    if 1 in bucket and 2 in bucket:
        a = sum(x[0] for x in bucket[1]) / len(bucket[1])
        b = sum(x[0] for x in bucket[2]) / len(bucket[2])
        print("\n1 -> 2 的速率比：%.2fx" % (b / a))
        print("同期未缓存 prompt 比 %.2fx、命中率差 %+.1fpp —— 若这两项一起来，"
              "说明部分增益来自\"每次生成摊到的重算更少\"，不是纯批处理。"
              % (sum(x[2] for x in bucket[2]) / len(bucket[2]) /
                 (sum(x[2] for x in bucket[1]) / len(bucket[1])),
                 100 * (sum(x[1] for x in bucket[2]) / len(bucket[2]) -
                        sum(x[1] for x in bucket[1]) / len(bucket[1]))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
