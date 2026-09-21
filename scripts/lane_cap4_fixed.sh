#!/bin/bash
# Re-run static cap4 with the FIXED runner — as a CONTROL.
#
# cap4 showed zero counter drift in the original sweep, so its result should be
# unchanged. Running it again is what makes that a check rather than an assumption:
# if the fixed binary moves cap4's numbers materially, the fix itself changed
# behaviour and the whole cap-n sweep needs redoing; if it reproduces, the fix is
# confined to the broken case and cap4/cap5 keep their original results.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane cap4_fixed --gpu 1 --port 30031 \
  --runs 'pois200_cap4_fixed:static=4'
bash /data/xbw/turnstile/scripts/lane_done.sh cap4_fixed pois200_cap4_fixed
