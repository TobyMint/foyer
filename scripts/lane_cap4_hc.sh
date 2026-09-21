#!/bin/bash
# Poisson, static cap4 WITH HiCache — the fair baseline GPT's audit asked for.
#
# Why this specific point: cap4 is the fastest static policy (257.6 min, 45.9% hit),
# and it is the point most likely to move the Pareto picture. Our own cap6 experiment
# on the 25-tier trace showed HiCache turning 27.9 min / 31.7% into 22.8 min / 64.1%
# — faster AND better at once. If something similar happens at cap4 on the main
# trace, the entire comparison changes, because the baseline we have been measuring
# ourselves against was never given the same mechanism.
#
# Pairs with pois200_cap4_fixed, which is running on gpu1 with the repaired runner:
# same trace, same pool, same binary, only the HiCache flag differs.
#
# This is also the first data point of the capacity question: HiCache bought +4.1pp
# at Foyer's concurrency (~2, almost no eviction pressure) and +32pp at cap6 on the
# 25-tier trace. A benefit that swings 8x with the operating point is what puts
# MORI's "adapting to any hardware capacity ratio" claim under test.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane cap4_hc --gpu 2 --port 30032 \
  --runs 'pois200_cap4_hc:static=4'
bash /data/xbw/turnstile/scripts/lane_done.sh cap4_hc pois200_cap4_hc
