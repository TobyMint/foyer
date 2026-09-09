#!/usr/bin/env python3
"""Clean replay traces: drop rounds with an empty arrival payload (prefix+input==0)
or zero output target — these are unusable rows (one per known dataset: HTTP 400 under
every policy, so they poison the failure metric with a constant offset). Absolute
prefix_len makes dropping a round chain-safe.
"""
import csv, sys

src, dst = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src)))
keep = [r for r in rows
        if int(r["prefix_len"]) + int(r["input_len"]) > 0 and int(r["output_len"]) > 0]
dropped = len(rows) - len(keep)
with open(dst, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(keep)
print(f"{src}: {len(rows)} -> {len(keep)} rows (dropped {dropped})")
