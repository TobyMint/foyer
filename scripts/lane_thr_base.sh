#!/bin/bash
# Throttle A/B wave 1 — fresh baseline (current controller code; the 09-10 baseline
# predates the TTFT-freshness fix and is not comparable).
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane thr_base --gpu 2 --port 30020 --runs 'thr25_base:budget3'
touch /data/xbw/turnstile/results/night/lane_thr_base_DONE
