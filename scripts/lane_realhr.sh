#!/bin/bash
# Real-arrival study — the measured peak-hour burst from the TraceLab corpus
# (117 sessions, real sub-minute arrival structure). Same two arms as the Poisson
# study so the three arrival shapes are directly comparable.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_realhr.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane realhr --gpu 2 --port 30031 --runs 'realhr_foyer:budget3:hw=0;target=0.95,realhr_cap2:static=2'
bash /data/xbw/turnstile/scripts/lane_done.sh realhr realhr_foyer realhr_cap2
