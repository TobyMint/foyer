#!/bin/bash
# Throttle A/B wave 2 — raise the admission budget to 0.95 of the pool (from the
# default 0.75). Single variable vs the fresh baseline: is the ledger ceiling the
# binding constraint on concurrency?
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane thr_t95 --gpu 3 --port 30023 --runs 'thr25_t95:budget3:target=0.95'
touch /data/xbw/turnstile/results/night/lane_thr_t95_DONE
