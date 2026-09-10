#!/bin/bash
# P0 lane F (GPU1): the headline rerun — budget3@200, aligned pool, 12h timeout.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p0f --gpu 1 --port 30003 --runs budget200c_budget3:budget3
touch /data/xbw/turnstile/results/night/lane_p0f_DONE
