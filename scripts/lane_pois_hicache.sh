#!/bin/bash
# Poisson main table + HiCache: mechanism ② (state-preserving suspension) measured in
# the main evaluation setting, same controller parameters as pois200_foyer.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_hc --gpu 2 --port 30032 \
  --runs 'pois200_foyer_hc:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_hc pois200_foyer_hc
