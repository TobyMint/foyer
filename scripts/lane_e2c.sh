#!/bin/bash
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane e2c --gpu 2 --port 30011 --runs 'load25c_budget3_sg0:budget3:sg=0'
touch /data/xbw/turnstile/results/night/lane_e2c_DONE
