#!/bin/bash
# cap2 + HiCache: the one static point that could take the high-SLO claim away.
#
# Why it exists. cap3_hc landed at 242.5 min / SLO 81.1%, taking the 80-85% SLO
# band that used to belong to Foyer alone. cap2_hc is the remaining untested
# static point, and cap2 (310.5 min, SLO 89.5%) sits in exactly the band where
# Foyer still wins. If HiCache gave cap2 the 8-15% it gave cap3 and cap4, it
# would land at 264-286 and beat Foyer+HiCache's 297.6 outright.
#
# The reason to expect it will NOT: HiCache's value scales with concurrency, and
# we now have three pairs showing it, each with concurrency unchanged:
#     cap4   257.6 -> 219.0   15.0%   at concurrency 3.94
#     cap3   264.8 -> 242.5    8.4%   at concurrency 2.93
#     Foyer  299.3 -> 297.6    0.6%   at concurrency 2.06
# cap2 runs at concurrency 1.99, so ~0.6% predicts about 308.6 min.
#
# That is a prediction from three points, not a measurement. This run turns it
# into one either way, and either outcome is worth having: if cap2_hc lands near
# 308 the claim survives as measured fact, and if it lands near 280 then the
# high-SLO story is gone and we need to know that now rather than at submission.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane cap2_hc --gpu 3 --port 30033 \
  --runs 'pois200_cap2_hc:static=2'
bash /data/xbw/turnstile/scripts/lane_done.sh cap2_hc pois200_cap2_hc
