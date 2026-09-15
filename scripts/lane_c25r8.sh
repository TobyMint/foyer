#!/bin/bash
# cap8@25 aligned-pool rerun (old run was on 97,367 pool; target 101,432)
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane c25r8 --gpu 2 --port 30015 --runs 'load25c_cap8r:static=8'
touch /data/xbw/turnstile/results/night/lane_c25r8_DONE
