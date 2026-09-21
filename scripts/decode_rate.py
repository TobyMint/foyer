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
SESS_PAIRS = []
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
            # Decode window, computed from ONE origin.
            #
            # `total_duration_ms` is `elapsed_ms(start)` where `start` is taken BEFORE
            # the payload is built; `first_token_ms` is `elapsed_ms(send_instant)` where
            # send_instant is taken AFTER. Subtracting them therefore folds the payload
            # construction time into the decode window -- and that time scales with
            # prompt length, so the bias is not uniform across requests. (Both are also
            # SystemTime rather than Instant, so an NTP step mid-run makes them wrong;
            # `unwrap_or_default()` turns a negative into 0.)
            #
            # submit/post/complete_timestamp are absolute readings of the same wall
            # clock, so post->complete minus TTFT is a window with consistent ends:
            # post_timestamp is taken just before send_instant. The residual is the
            # sub-millisecond gap between those two, which is below anything this
            # measurement can resolve.
            if r.get("post_timestamp") and r.get("complete_timestamp"):
                span_ms = (r["complete_timestamp"] - r["post_timestamp"]) * 1000.0
            else:
                span_ms = dur
            decode_ms = span_ms - ttft
            if decode_ms <= 0:
                continue
            out.append({
                "session_id": r.get("session_id"),
                "rate": (n_out - 1) / (decode_ms / 1000.0),
                "t0": t0, "t1": t1,
                "hit": r.get("server_prefix_hit_rate"),
                "prompt": r.get("server_uncached_prompt_tokens") or 0,
                "ctx": r.get("prompt_len") or 0,
            })
    return out


def figure(bucket, path):
    """Per-request rate vs concurrency, with the session-internal control beside it.

    Two panels because the left one is the result and the right one is the reason to
    believe it: the cross-sectional means are what a reader wants, and the
    session-internal ratios are what rules out the selection effect that the
    cross-sectional view invites (higher-concurrency buckets show higher hit rates
    and smaller contexts, which is backwards and suspicious).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.6, 4.4))

    ks = sorted(bucket)
    for name, col in (("rate", "#1f77b4"),):
        pass
    xs = ks
    ys = [sum(x[0] for x in bucket[k]) / len(bucket[k]) for k in ks]
    ns = [len(bucket[k]) for k in ks]
    a.plot(xs, ys, "o-", color="#1f77b4", lw=2, ms=8)
    for x, y, nn in zip(xs, ys, ns):
        a.annotate("%.1f\n(%d run)" % (y, nn), (x, y), textcoords="offset points",
                   xytext=(0, 11), ha="center", fontsize=8.5, color="#1f77b4")
    a.set_xlabel("引擎并发  mean(num_running_reqs)")
    a.set_ylabel("逐请求解码速率 (tok/s)")
    a.set_title("每请求速率不随并发上升", fontsize=11.5)
    a.set_ylim(min(ys) - 4, max(ys) + 5)
    a.grid(True, color="#e8e6e0", lw=0.7)
    a.set_axisbelow(True)
    for sp in ("top", "right"):
        a.spines[sp].set_visible(False)

    # Right panel: the session-internal control.
    if SESS_PAIRS:
        ratios = [c2 / c1 for c1, c2 in SESS_PAIRS if c1 > 0]
        ratios.sort()
        med = ratios[len(ratios) // 2]
        lo = ratios[len(ratios) // 4]
        hi = ratios[3 * len(ratios) // 4]
        b.axhline(1.0, color="#999", lw=1, ls="--")
        b.boxplot([ratios], vert=True, widths=0.35, showfliers=False,
                  patch_artist=True,
                  boxprops=dict(facecolor="#cde2fb", edgecolor="#2a78d6"),
                  medianprops=dict(color="#d62728", lw=2),
                  whiskerprops=dict(color="#2a78d6"),
                  capprops=dict(color="#2a78d6"))
        b.set_xticks([1]); b.set_xticklabels(["%d 对会话内配对" % len(ratios)])
        b.set_ylabel("并发 2 / 并发 1 的速率比")
        b.set_title("会话内配对：同一会话自己比自己\n"
                    "中位 %.3f（四分位 %.3f–%.3f）｜均值 %.3f 不稳定"
                    % (med, lo, hi, sum(ratios) / len(ratios)), fontsize=10.4)
        b.grid(True, axis="y", color="#e8e6e0", lw=0.7)
        b.set_axisbelow(True)
        for sp in ("top", "right"):
            b.spines[sp].set_visible(False)

    fig.suptitle("并发买到的是并行度，不是效率——且结论经得起会话内配对的控制",
                 fontsize=12.2, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(path)
    print("\nwrote %s" % path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--runs", default=",".join(DEFAULT_RUNS))
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    print("逐请求解码速率 = (output_len-1) / (total_duration - TTFT)   "
          "只保留 output_len >= %d\n" % MIN_OUTPUT)
    print("%-22s %-4s %8s %10s %9s %9s %9s" %
          ("run", "conc", "n", "tok/s", "命中率", "未缓存prompt", "上下文"))

    bucket = collections.defaultdict(list)
    global SESS_PAIRS
    SESS_PAIRS = []
    for name in args.runs.split(","):
        d = os.path.join(args.dir, name)
        mp, sp = os.path.join(d, "metrics.csv"), os.path.join(d, "steps.jsonl")
        if not (os.path.exists(mp) and os.path.exists(sp)):
            print("skip %s (缺文件)" % name)
            continue
        ts, running = load_conc(mp)
        bysess = collections.defaultdict(lambda: collections.defaultdict(list))
        by = collections.defaultdict(list)
        for r0 in steps_of(sp):
            s = r0
            c = mean_conc(ts, running, s["t0"], s["t1"])
            if c is None:
                continue
            by[int(round(c))].append(s)
            bysess[r0["session_id"]][int(round(c))].append(s["rate"])
        for sid, sb in bysess.items():
            if 1 in sb and 2 in sb and len(sb[1]) >= 2 and len(sb[2]) >= 2:
                SESS_PAIRS.append((sum(sb[1]) / len(sb[1]), sum(sb[2]) / len(sb[2])))
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
    if SESS_PAIRS:
        r = sorted(c2 / c1 for c1, c2 in SESS_PAIRS if c1 > 0)
        # MEDIAN is the headline, not the mean. The per-session ratios have a long
        # right tail, and the mean moved from 0.976 (4 runs) to 1.017 (6 runs) while
        # the median stayed at 0.95-0.97. Quoting the mean would make the finding
        # flip direction depending on which runs happen to be included.
        print("\n会话内配对：%d 对" % len(r))
        print("  中位 %.3f（四分位 %.3f–%.3f）  <- 以此为准"
              % (r[len(r)//2], r[len(r)//4], r[3*len(r)//4]))
        print("  均值 %.3f  <- 不稳定，勿单独引用（长右尾）" % (sum(r)/len(r)))
    if args.out:
        figure(bucket, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
