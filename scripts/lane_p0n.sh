#!/bin/bash
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p0n --gpu 2 --port 30006 \
  --runs 'load25c_budget3_sf0:budget3:margin=1.0;sf=0,load25c_budget3_t80:budget3:target=0.80'
touch /data/xbw/turnstile/results/night/lane_p0n_DONE
