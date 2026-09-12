#!/bin/bash
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane e2b --gpu 1 --port 30010 --runs 'load25c_budget3_oracle:budget3:predictor=oracle'
touch /data/xbw/turnstile/results/night/lane_e2b_DONE
