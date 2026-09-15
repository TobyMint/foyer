#!/bin/bash
# Wave 3a — push both knobs: floor off AND budget to 0.95. Where does the next
# constraint appear once the ledger no longer over-counts occupancy?
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane thr_push --gpu 2 --port 30024 --runs 'thr25_push:budget3:hw=0;target=0.95'
touch /data/xbw/turnstile/results/night/lane_thr_push_DONE
