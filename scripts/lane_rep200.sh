#!/bin/bash
# 200-tier fixed-config repeat: error bars for the headline config (currently n=1).
set -e
export TURNSTILE_RUN_TIMEOUT_H=14
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane rep200 --gpu 3 --port 30033 \
  --runs 'p200_fix_r3:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh rep200 p200_fix_r3
