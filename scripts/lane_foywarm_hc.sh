#!/bin/bash
# Strategy test: while the SLO valve is on, admit warm sessions instead of nobody.
#
# Why. On pois200_foyfix_hc the valve is on for 49% of cycles (time-weighted)
# while the request-weighted SLO is 89.8%. Both are true at once because almost
# nothing completes while it is on. In those cycles the pool sits at 0.345, so
# capacity is idle, and what the controller cannot afford is specifically a COLD
# prefill. Marginal prefill by round on that same run:
#     round 0 (full context)   median 15,720 tok  ->  17.0 s
#     round 1+ (growth only)   median  1,933 tok  ->   2.1 s
# An 8x difference the valve does not distinguish. So under valve, admit the
# warm ones and hold the fresh ones. No clairvoyance: rounds completed is
# observed state.
#
# Paired against pois200_foyfix_hc, which is the same everything except the
# valve's action. Judge on BOTH concurrency and TTFT -- reaching cap4's
# concurrency by wrecking TTFT is just becoming cap4 the long way round.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane foywarm_hc --gpu 2 --port 30032 \
  --runs 'pois200_foywarm_hc:foyer:target=0.95;hw=0;sf=0;sg=0'
bash /data/xbw/turnstile/scripts/lane_done.sh foywarm_hc pois200_foywarm_hc
