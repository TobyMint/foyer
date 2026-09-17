#!/bin/bash
# One-factor-at-a-time decomposition of our retuning away from Concur's paper config.
# With lane_aimd2_paper this gives paper(0.2,0.5,0.2) + the two single-factor moves we
# made (u_low 0.2->0.35, u_high 0.5->0.75) + the paper's own safe-region top (0.6),
# so the gap can be attributed to a specific threshold instead of "AIMD is bad here".
# Abort the lane on the first failure: a run aborted by the pool guard must
# stop the lane, not silently roll on to the next arm and burn GPU time.
# run_matrix.py skips runs that already have a summary, so the driver's
# wholesale retry only redoes the arms that did not finish.
set -e
export TURNSTILE_RUN_TIMEOUT_H=16
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane aimd2_grid --gpu 3 --port 30033 \
  --runs 'aimd2_ul35:aimd2:u_low=0.35;u_high=0.5;h_thresh=0.2'
$P $S --lane aimd2_grid --gpu 3 --port 30033 \
  --runs 'aimd2_uh75:aimd2:u_low=0.2;u_high=0.75;h_thresh=0.2'
bash /data/xbw/turnstile/scripts/lane_done.sh aimd2_grid aimd2_ul35 aimd2_uh75
