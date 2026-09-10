#!/bin/bash
# P0 lane E (GPU2, sustained-free poller): the budget3@200 rerun — the headline
# number. First attempt hit the 6h timeout (archived as *_timedout_591steps); the
# relaunch collided with labmates colonizing the card. 12h run timeout now.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p0e --gpu 2 --port 30001 --runs budget200c_budget3:budget3
touch /data/xbw/turnstile/results/night/lane_p0e_DONE
