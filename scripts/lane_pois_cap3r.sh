#!/bin/bash
# Re-run of the Poisson cap3 arm: the first attempt ran on a 84,528-token pool
# (a neighbour held VRAM at server start), so it is not comparable. The pool guard
# in run_matrix now aborts instead of recording such a run.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_cap3r --gpu 2 --port 30032 --runs 'pois200_cap3_r2:static=3'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_cap3r pois200_cap3_r2
