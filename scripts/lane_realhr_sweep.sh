#!/bin/bash
# Real-arrival sweep: complete the static frontier on the measured arrival trace
# (117 sessions, the busiest hour of 2026-05-29) so the §5.8 comparison is not a
# single cap2 point. Static arms only — the aimd2 controller has been stalling on
# this box (defect A/B) and is not worth a 16h slot here; the working aimd2 rows
# already exist for the flash-crowd and Poisson tables.
set -e
export TURNSTILE_RUN_TIMEOUT_H=8
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_realhr.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane realhr_sweep --gpu 2 --port 30032 \
  --runs 'realhr_cap3:static=3'
$P $S --lane realhr_sweep --gpu 2 --port 30032 \
  --runs 'realhr_cap4:static=4'
$P $S --lane realhr_sweep --gpu 2 --port 30032 \
  --runs 'realhr_cap1:static=1'
bash /data/xbw/turnstile/scripts/lane_done.sh realhr_sweep \
  realhr_cap3 realhr_cap4 realhr_cap1
