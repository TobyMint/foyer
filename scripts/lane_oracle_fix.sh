#!/bin/bash
# The corrected oracle arm. The old implementation returned a constant lifetime sum
# (no decay, unbounded window, first-turn input double-counted), which is why the
# "better prediction -> more conservative" reading was retracted from the draft. The
# rewritten predictor is G*(t) = max(0, C(t+h) - C(t)) anchored at the last completed
# round. Two arms: the default skeleton (comparable with the other §5.3 arms) and the
# current fixed config.
set -e
export TURNSTILE_RUN_TIMEOUT_H=6
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane oracle_fix --gpu 2 --port 30032 \
  --runs 'load25c_oracle_fix:budget3:predictor=oracle'
$P $S --lane oracle_fix --gpu 2 --port 30032 \
  --runs 'load25c_oracle_fix_push:budget3:predictor=oracle;hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh oracle_fix \
  load25c_oracle_fix load25c_oracle_fix_push
