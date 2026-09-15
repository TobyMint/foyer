#!/bin/bash
# Throttle A/B wave 1 — single-flight admission OFF (hypothesis: the 1-per-cycle +
# wait-for-first-round/60s gate is what pins concurrency at ~1.1 of an allowed ~2.2).
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane thr_nosf --gpu 3 --port 30021 --runs 'thr25_nosf:budget3:sf=0'
touch /data/xbw/turnstile/results/night/lane_thr_nosf_DONE
