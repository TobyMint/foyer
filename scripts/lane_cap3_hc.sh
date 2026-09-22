#!/bin/bash
# cap3 + HiCache: the baseline point that could invalidate the headline.
#
# We have cap4+HiCache (219.0 min) and cap4 (257.6). We do NOT have cap3+HiCache,
# and cap3_fixed (264.8 min, SLO 74.4%) already beats every Foyer arm without a
# cache tier. If HiCache moves cap3 the way it moved cap4 (15%), cap3+HiCache
# lands near 225 min -- at an SLO the controller arms cannot answer, which would
# leave Foyer with no wall-clock story at all. We need the number, not the worry.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane cap3_hc --gpu 3 --port 30033 \
  --runs 'pois200_cap3_hc:static=3'
bash /data/xbw/turnstile/scripts/lane_done.sh cap3_hc pois200_cap3_hc
