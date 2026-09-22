#!/bin/bash
# Foyer 能否吃到引擎红利。对照 foyer_hc 291.3/2.06/89.8
# 单变量相对照组；引擎参数走 TURNSTILE_HICACHE_ARGS 通道（run_matrix.py:348 是通用附加参数）。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through --max-prefill-tokens 65536"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane foyerpf --gpu 2 --port 30042 \
  --runs 'pois200_foyer_hc_pf64:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh foyerpf pois200_foyer_hc_pf64
