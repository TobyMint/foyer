#!/bin/bash
# lane_done.sh <lane> <run1> [run2 ...]
# Mark a lane complete ONLY if every run produced a summary. A lane that aborted
# (e.g. the pool guard refusing a shrunken KV pool) must NOT look finished, or the
# chain drivers will skip the retry.
N=/data/xbw/turnstile/results/night
lane=$1
shift
for r in "$@"; do
  if [ ! -f "$N/$r/summary.json" ]; then
    echo "[$(date '+%H:%M:%S')] lane $lane INCOMPLETE: run $r has no summary — not marking done"
    exit 1
  fi
done
touch "$N/lane_${lane}_DONE"
echo "[$(date '+%H:%M:%S')] lane $lane complete"
