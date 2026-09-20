#!/bin/bash
# Poisson main table, Foyer controller with the KV pool as a GUARDRAIL (aggressive arm).
#
# target=0.99 / growth-scale=0.05 deliberately runs near the edge. The arithmetic
# says why it has to: a session costs ~23.6k of pool and a newcomer needs ~20k, so
# four concurrent sessions (~117k) do not fit in 101,432 tokens at all. cap3 and
# cap4 reach 3.56/3.94 concurrency only by over-subscribing the pool and letting
# SGLang evict to make room — which is exactly why their hit rate is 46-50%.
# This arm asks whether admission that knows what it is doing can run at cap-4
# concurrency and keep more of its cache than a blind cap-4 does.
#
# --hard-stop-usage is raised to 0.98 because the natural operating point of a
# 4-session equilibrium IS ~93% of the pool: leaving the valve at its 0.93 default
# would trip it continuously and shed the sessions we just admitted.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_foyer_rl99 --gpu 1 --port 30031 \
  --runs 'pois200_foyer_rl99:foyer:target=0.99;gs=0.05;hs=0.98'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_foyer_rl99 pois200_foyer_rl99
