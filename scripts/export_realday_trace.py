#!/usr/bin/env python3
"""Export a replay trace from ONE real calendar day of the TraceLab corpus, keeping
the real session arrival offsets — the arrival shape is measured, not synthesised.

Same content fields as the night traces (prefix/input/output/tool_wait), same size
filter (peak input+output <= 96K tokens), rounds capped at MAX_ROUNDS to match the
night traces' shape. `arrival_time` = ms from the day's first session start.

Usage: export_realday_trace.py DAY OUT_CSV      (DAY = YYYY-MM-DD)
"""
import csv
import sys

import duckdb

DAY = sys.argv[1] if len(sys.argv) > 1 else "2026-05-29"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/data/xbw/turnstile/data/replay_realday.csv"
MAXPEAK, MAX_ROUNDS = 98304, 5

con = duckdb.connect("/data/xbw/turnstile/data/syfi_coding_trace.duckdb", read_only=True)
con.execute("""CREATE TEMP TABLE ev AS
  SELECT round_pk, MIN(timestamp) AS t0, MAX(timestamp) AS t1
  FROM timing_events GROUP BY round_pk""")
con.execute("""CREATE TEMP TABLE sess AS
  SELECT r.session_id, MIN(e.t0) AS s0, MAX(r.input_tokens_total + r.output_tokens) AS peak,
         COUNT(*) AS n_rounds
  FROM rounds r JOIN ev e ON r.round_pk = e.round_pk
  GROUP BY r.session_id""")
con.execute(f"""CREATE TEMP TABLE keep AS
  SELECT session_id, s0 FROM sess
  WHERE CAST(s0 AS DATE) = DATE '{DAY}' AND peak <= {MAXPEAK} AND n_rounds >= 2""")
n_sess = con.execute("SELECT count(*) FROM keep").fetchone()[0]
t0 = con.execute("SELECT min(s0) FROM keep").fetchone()[0]

rows = con.execute(f"""WITH r AS (
    SELECT r.session_id, r.round_index AS round_idx, r.prefix_tokens, r.newly_append_tokens,
           r.output_tokens, e.t0, e.t1,
           ROW_NUMBER() OVER (PARTITION BY r.session_id ORDER BY r.round_index) AS rn
    FROM rounds r JOIN ev e ON r.round_pk = e.round_pk
    JOIN keep k ON k.session_id = r.session_id),
  w AS (
    SELECT session_id, round_idx, prefix_tokens, newly_append_tokens, output_tokens, rn,
           GREATEST(COALESCE(date_diff('milliseconds', t1,
              LEAD(t0) OVER (PARTITION BY session_id ORDER BY round_idx)), 0), 0) AS tool_wait
    FROM r)
  SELECT w.session_id, w.round_idx, w.prefix_tokens, w.newly_append_tokens, w.output_tokens,
         w.tool_wait, date_diff('milliseconds', DATE '{DAY}', k.s0) AS arrival_ms
  FROM w JOIN keep k USING (session_id)
  WHERE w.rn <= {MAX_ROUNDS}
  ORDER BY w.session_id, w.round_idx""").fetchall()

# --- crop to the densest WINDOW_MIN-minute window (a day-long literal replay is
# --- impractical and spends most of its time idle; the peak window keeps the
# --- measured burst structure and makes runs comparable in length).
WINDOW_MIN = 60
starts = sorted({r[6] for r in rows})                     # distinct session arrivals (ms)
best, best_n = starts[0], 0
for s in starts:
    n = sum(1 for x in starts if s <= x < s + WINDOW_MIN * 60000)
    if n > best_n:
        best, best_n = s, n
kept_ids = {r[0] for r in rows if best <= r[6] < best + WINDOW_MIN * 60000}
kept = [r for r in rows if r[0] in kept_ids]

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["session_id", "round_idx", "prefix_len", "input_len", "output_len",
                "tool_wait_after_ms", "arrival_time"])
    for sid, ri, pre, inp, out, tw, arr in kept:
        w.writerow([sid, ri, pre, inp, out, int(tw or 0), int(arr - best)])

span = (max(r[6] for r in kept) - best) / 60000.0
arr = sorted({r[6] for r in kept})
gaps = sorted((arr[i + 1] - arr[i]) / 60000 for i in range(len(arr) - 1))
print(f"{DAY}: {n_sess} sessions on the day; peak {WINDOW_MIN}-min window holds "
      f"{len(kept_ids)} sessions / {len(kept)} rounds -> {OUT}")
print(f"   window starts at {best/60000:.0f} min into the day, session arrivals span "
      f"{span:.1f} min; inter-arrival p50={gaps[len(gaps)//2]:.2f} min" if gaps else "")
