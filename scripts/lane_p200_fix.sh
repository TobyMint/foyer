#!/bin/bash
# 200-session tier (the decisive tier) with the FIXED controller configuration.
# Every existing 200-tier Foyer number was produced with the high-water floor ON
# and target=0.75/0.85 — this is the configuration we would actually ship.
export TURNSTILE_RUN_TIMEOUT_H=14
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p200_fix --gpu 3 --port 30030 --runs 'p200_fix:budget3:hw=0;target=0.95'
touch /data/xbw/turnstile/results/night/lane_p200_fix_DONE
