#!/bin/bash
# P0 lane G (GPU0): the decisive opponents at 200 tier, in importance order.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p0g --gpu 0 --port 30004 \
  --runs budget200c_cap4:static=4,budget200c_default:default,budget200c_aimd2:aimd2
touch /data/xbw/turnstile/results/night/lane_p0g_DONE
