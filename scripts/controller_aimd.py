#!/usr/bin/env python3
"""Concur-style cache-feedback AIMD admission controller (count-window, re-tuned for 3090).

W starts at --initial-cap. Every interval:
  U < u_low                      -> W += alpha            (additive probing)
  U > u_high and H < h_thresh    -> W = ceil(W * beta)    (multiplicative cut on thrashing)
  otherwise                      -> hold
Writes W to the runner's --cap-file each cycle. U is SGLang token_usage, H is its
cache_hit_rate gauge — the same two feedback signals Concur uses.
"""
import argparse
import json
import math
import os
import time
import urllib.request


def get_metrics(url):
    import re
    vals = {}
    pat = re.compile(r"^(\S+?)(\{.*\})?\s+(\S+)$")
    try:
        text = urllib.request.urlopen(url, timeout=5).read().decode()
    except Exception:
        return vals
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = pat.match(line.strip())
        if not m:
            continue
        name, labelpart, value = m.group(1), m.group(2) or "", m.group(3)
        if "quantile" in labelpart:
            continue
        try:
            vals[name] = float(value)
        except ValueError:
            pass
    return vals


def write_cap(path, cap):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(str(int(cap)))
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-file", required=True)
    ap.add_argument("--metrics-url", default="http://127.0.0.1:30000/metrics")
    ap.add_argument("--decision-log", required=True)
    ap.add_argument("--initial-cap", type=int, default=2)
    ap.add_argument("--u-low", type=float, default=0.35)
    ap.add_argument("--u-high", type=float, default=0.75)
    ap.add_argument("--h-thresh", type=float, default=0.03)
    ap.add_argument("--alpha", type=float, default=2.0)
    ap.add_argument("--beta", type=float, default=0.5)
    ap.add_argument("--max-cap", type=int, default=64)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--max-minutes", type=float, default=300.0)
    args = ap.parse_args()

    write_cap(args.cap_file, args.initial_cap)
    window = float(args.initial_cap)
    deadline = time.time() + args.max_minutes * 60
    with open(args.decision_log, "w") as log:
        while time.time() < deadline:
            m = get_metrics(args.metrics_url)
            usage = m.get("sglang:token_usage", 0.0)
            hit = m.get("sglang:cache_hit_rate", 1.0)
            retracted = m.get("sglang:num_retracted_reqs", 0.0)
            prev = window
            action = "hold"
            # Congestion signal = cache-thrash marker (usage above target AND hit rate
            # collapsed). Classic AIMD: grow whenever the signal is ABSENT and usage is
            # below the hard ceiling; cut multiplicatively when it fires. U == 0 (engine
            # idle, e.g. runner still tokenizing) carries no information: hold.
            congestion = usage > args.u_high and hit < args.h_thresh
            if usage == 0.0:
                action = "hold"
            elif congestion:
                window = max(math.ceil(window * args.beta), 1.0)
                action = "cut"
            elif usage < 0.90:
                window = min(window + args.alpha, float(args.max_cap))
                action = "grow"
            write_cap(args.cap_file, window)
            log.write(json.dumps({
                "ts": round(time.time(), 3), "W": window, "prev": prev,
                "U": usage, "H": hit, "retracted": retracted, "action": action,
                "running": m.get("sglang:num_running_reqs"),
                "queue": m.get("sglang:num_queue_reqs"),
            }) + "\n")
            log.flush()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
