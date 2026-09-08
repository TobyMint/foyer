#!/usr/bin/env python3
"""Sample SGLang /metrics every N seconds into a CSV. Runs alongside a replay."""
import argparse
import csv
import time
import urllib.request

GAUGES = [
    "sglang:token_usage",
    "sglang:full_token_usage",
    "sglang:cache_hit_rate",
    "sglang:num_running_reqs",
    "sglang:num_queue_reqs",
    "sglang:num_retracted_reqs",
    "sglang:max_total_num_tokens",
    "sglang:num_used_tokens",
    "sglang:new_token_ratio",
]
COUNTERS = [
    "sglang:generation_tokens_total",
    "sglang:cached_tokens_total",
    "sglang:evicted_tokens_total",
    "sglang:prompt_tokens_total",
]
HISTOGRAMS = {
    "ttft": "sglang:time_to_first_token_seconds",
    "e2e": "sglang:e2e_request_latency_seconds",
    "itl": "sglang:inter_token_latency_seconds",
}


def fetch(url):
    """Parse Prometheus exposition into {plain_name: value} + {hist_name: {quantile: v}}.

    Metric lines carry labels (e.g. sglang:token_usage{engine_type=...,tp_rank="0"} 0.69),
    so name = text before '{' and value = last token after '}'.
    """
    import re
    out = {}
    hists = {}
    pat = re.compile(r"^(\S+?)(\{.*\})?\s+(\S+)$")
    lab = re.compile(r'(\w+)="([^"]*)"')
    try:
        text = urllib.request.urlopen(url, timeout=5).read().decode()
    except Exception:
        return out
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = pat.match(line.strip())
        if not m:
            continue
        name, labelpart, value = m.group(1), m.group(2) or "", m.group(3)
        try:
            v = float(value)
        except ValueError:
            continue
        labels = dict(lab.findall(labelpart))
        out[name] = v
        if "quantile" in labels:
            hists.setdefault(name, {})[labels["quantile"]] = v
    for base, qs in hists.items():
        for q, v in qs.items():
            out[f"{base}{{quantile=\"{q}\"}}"] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:30000/metrics")
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=5.0)
    args = ap.parse_args()

    fields = ["ts"] + GAUGES + COUNTERS
    for tag in HISTOGRAMS:
        fields += [f"{tag}_p50", f"{tag}_p90", f"{tag}_p99"]
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        while True:
            row = {"ts": round(time.time(), 3)}
            m = fetch(args.url)
            for name in GAUGES + COUNTERS:
                row[name] = m.get(name, "")
            for tag, base in HISTOGRAMS.items():
                for q, label in [("0.5", "p50"), ("0.9", "p90"), ("0.99", "p99")]:
                    row[f"{tag}_{label}"] = m.get(f'{base}{{quantile="{q}"}}', "")
            w.writerow(row)
            f.flush()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
