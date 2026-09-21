#!/bin/bash
# Matched pair, wave A, arm 1/2: static cap 2 WITH HiCache, on the Poisson trace.
#
# Why this run exists. The main table compares Foyer+HiCache (297.6, 09-20) against
# cap2 (310.5, 09-15) and the difference is 4.2%. Two problems with that:
#
#   1. The two were measured FIVE DAYS apart on a shared box. We have measured a
#      neighbour's 24-core job inflating our wall clock by 17-25% while GPU decode
#      moves only 2%. A 4.2% difference between runs five days apart is not
#      attributable to anything.
#   2. The arms are not matched on mechanism: Foyer+HC has HiCache on, this cap2
#      has it off, so the comparison bundles the controller together with the
#      cache tier. The paired baseline for Foyer+HC is cap2+HC — which does not
#      exist on this trace (budget200c_cap2_hc is on night200_clean).
#
# So: same trace, same pool, same HiCache flags, and — critically — running
# CONCURRENTLY with its partner on the other GPU, so both arms see the same box
# conditions. Wave B swaps the GPUs so a card-specific neighbour cannot masquerade
# as a treatment effect. The paired difference across waves is the estimator; no
# single run is interpreted on its own.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pairA_cap2hc --gpu 2 --port 30032 \
  --runs 'pois200_pairA_cap2hc:static=2'
bash /data/xbw/turnstile/scripts/lane_done.sh pairA_cap2hc pois200_pairA_cap2hc
