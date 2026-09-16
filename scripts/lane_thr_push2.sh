#!/bin/bash
# Wave 4b — repeat of the best configuration (n=2 for an error bar on the arm we
# would put in the paper).
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane thr_push2 --gpu 3 --port 30026 --runs 'thr25_push_r2:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh thr_push2 thr25_push_r2
