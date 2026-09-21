#!/bin/bash
# Re-run static cap3 with the FIXED runner.
#
# The original cap3 (pois200_cap3_r2) is invalid: the runner's count-cap gate used a
# non-atomic load-then-store, so 88 of its 200 admissions happened while already at
# or above cap and the peak in-flight was 5 against a cap of 3. cap4 and cap5 were
# unaffected (zero counter drift), which is why only cap3 is being redone.
#
# Nothing else changes: same trace, same pool, same mem fraction. The metadata will
# record a different session_runner hash, which is exactly the provenance needed to
# tell the two apart.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane cap3_fixed --gpu 0 --port 30030 \
  --runs 'pois200_cap3_fixed:static=3'
bash /data/xbw/turnstile/scripts/lane_done.sh cap3_fixed pois200_cap3_fixed
