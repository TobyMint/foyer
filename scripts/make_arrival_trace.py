#!/usr/bin/env python3
"""Add an `arrival_time` column (ms since run start) to a replay trace.

The runner already honours this column (runner/src/trace.rs: `arrival_time`,
default 0; session starts are held until that offset). Content is untouched, so
a Poisson trace is a clean single-variable variant of the flash-crowd one.

  mode=poisson  session arrivals are a Poisson process at `lam` sessions/second
  mode=flash    every session at t=0 (explicit; equivalent to omitting the column)

Usage: make_arrival_trace.py SRC DST poisson LAM SEED
"""
import csv
import random
import sys

src, dst, mode = sys.argv[1], sys.argv[2], sys.argv[3]
lam = float(sys.argv[4]) if len(sys.argv) > 4 else 0.04
seed = int(sys.argv[5]) if len(sys.argv) > 5 else 20260915

rows = list(csv.DictReader(open(src)))
order, seen = [], set()
for r in rows:
    if r["session_id"] not in seen:
        seen.add(r["session_id"])
        order.append(r["session_id"])

rng = random.Random(seed)
shuffled = order[:]
rng.shuffle(shuffled)          # arrival order independent of session id ordering

arrival, t = {}, 0.0
for sid in shuffled:
    if mode == "poisson":
        t += rng.expovariate(lam)   # exponential inter-arrivals => Poisson process
    arrival[sid] = t * 1000.0

fields = list(rows[0].keys())
if "arrival_time" not in fields:
    fields = fields + ["arrival_time"]
with open(dst, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        r["arrival_time"] = f"{arrival[r['session_id']]:.1f}"
        w.writerow(r)

span = max(arrival.values()) / 1000.0
gap = f"{1/lam:.1f}s" if lam > 0 else "n/a"
print(f"{src} -> {dst}: {len(order)} sessions, mode={mode}, lam={lam}/s, "
      f"last arrival {span/60:.1f} min, mean inter-arrival {gap}")
