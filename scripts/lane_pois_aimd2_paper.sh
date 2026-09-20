#!/bin/bash
# Concur at its PAPER parameters on the Poisson main trace — the decisive baseline run.
#
# Why this exists: the earlier "paper parameters deadlock" observation was an artefact
# of defect B (stale admission-log state inherited from a previous attempt in the same
# run dir), not of the parameters. The controller now ignores events written before it
# started (and handles `admit`), so this run gives Concur's published configuration a
# fair test in a run dir that has never been used before.
set -e
export TURNSTILE_RUN_TIMEOUT_H=8
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_aimd2_paper --gpu 2 --port 30032 \
  --runs 'pois200_aimd2_paper:aimd2:u_low=0.2;u_high=0.5;h_thresh=0.2'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_aimd2_paper pois200_aimd2_paper
