#!/bin/bash
# Poisson main table, Foyer controller with the KV pool as a GUARDRAIL (moderate arm).
#
# target=0.90 / growth-scale=0.35 is the gentlest setting that still differs from
# v3's behaviour: v3 refused whenever max(measured, ctx_sum) + growth-reserve +
# newcomer*1.15 crossed 0.95*pool, which it read as 92% full while the engine held
# 52%. This controller drops the sharing-blind ctx_sum, the 3-round reserve is
# scaled to 35%, and the newcomer carries no margin.
#
# Predicted equilibrium from the measured per-session footprint (23.6k, newcomer
# 20k): concurrency 3, against v3's 2.12. cap3 sits at 3.56.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_foyer_rl90 --gpu 0 --port 30030 \
  --runs 'pois200_foyer_rl90:foyer:target=0.90;gs=0.35'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_foyer_rl90 pois200_foyer_rl90
