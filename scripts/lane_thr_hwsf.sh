#!/bin/bash
# Wave 4a — floor off AND single-flight off: with the occupancy accounting fixed,
# does the admission-rate limiter still bind?
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane thr_hwsf --gpu 2 --port 30025 --runs 'thr25_hwsf:budget3:hw=0;sf=0'
touch /data/xbw/turnstile/results/night/lane_thr_hwsf_DONE
