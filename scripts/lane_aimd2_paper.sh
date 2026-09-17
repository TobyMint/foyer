#!/bin/bash
# Concur at its PAPER parameters, plus an H-signal ablation.
#
# Why: our existing aimd2 arm runs u_low=0.35 / u_high=0.75 / h_thresh=0.03 with H read
# straight off the sglang:cache_hit_rate gauge, which is zeroed on a shorter timer than
# our 30s control interval — so 98% of ticks read H=0, `H < h_thresh` is true for every
# h_thresh, and the gate silently disappears (h_thresh had no effect at all; cuts fired
# on `usage > u_high` alone). Concur's paper (§5.1) states Ulow=0.2, Uhigh=0.5,
# Hthresh=0.2, and its Appendix A.1 measures Uhigh=0.8 as "severely degrade[d] ...
# 4-5x" and Ulow>=0.3 as "2-3x", so the retuned values sit inside its own degraded
# region. These three runs separate the two defects.
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
$P $S --lane aimd2_paper --gpu 2 --port 30032 \
  --runs 'aimd2_paper:aimd2:u_low=0.2;u_high=0.5;h_thresh=0.2'
$P $S --lane aimd2_paper --gpu 2 --port 30032 \
  --runs 'aimd2_uh06:aimd2:u_low=0.2;u_high=0.6;h_thresh=0.2'
$P $S --lane aimd2_paper --gpu 2 --port 30032 \
  --runs 'aimd2_paper_rawH:aimd2:u_low=0.2;u_high=0.5;h_thresh=0.2;h_mode=raw'
bash /data/xbw/turnstile/scripts/lane_done.sh aimd2_paper aimd2_paper aimd2_uh06 aimd2_paper_rawH
