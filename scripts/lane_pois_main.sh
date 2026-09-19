#!/bin/bash
# Poisson main table (literature-standard arrival setting): the four arms missing
# from the flash-crowd table. Same 200 sessions and same content, arrivals are
# Poisson λ=0.04/s — calibrated to the corpus's measured peak hour (144 sessions/h).
# The Foyer config is NOT retuned for the arrival shape (that is the point).
# Single card on purpose: this is a shared machine and wave 2 already holds gpu2.
set -e
export TURNSTILE_RUN_TIMEOUT_H=14
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
# Concur first (the comparison that matters most), then the motivation row, the
# cliff point, and finally the long cap1 run.
$P $S --lane pois_main --gpu 3 --port 30033 \
  --runs 'pois200_aimd2:aimd2'
$P $S --lane pois_main --gpu 3 --port 30033 \
  --runs 'pois200_default:default'
$P $S --lane pois_main --gpu 3 --port 30033 \
  --runs 'pois200_cap5:static=5'
$P $S --lane pois_main --gpu 3 --port 30033 \
  --runs 'pois200_cap1:static=1'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_main \
  pois200_aimd2 pois200_default pois200_cap5 pois200_cap1
