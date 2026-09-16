#!/bin/bash
# Re-run of the 200-tier fixed-config arm: the first attempt ran on a 48,234-token
# pool (half size — a neighbour held VRAM at server start), which faked a quality
# regression. Pool guard now enforces 101,432 or aborts.
export TURNSTILE_RUN_TIMEOUT_H=16
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p200_fixr --gpu 3 --port 30033 --runs 'p200_fix_r2:budget3:hw=0;target=0.95'
touch /data/xbw/turnstile/results/night/lane_p200_fixr_DONE
