#!/bin/bash
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane e2a --gpu 0 --port 30009 --runs 'load25c_budget3_glob:budget3:predictor=global'
touch /data/xbw/turnstile/results/night/lane_e2a_DONE
