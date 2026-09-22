#!/bin/bash
# 安全点：cap3 + prefill 批预算放大。对照 cap3_hc 236.4/2.93/81.1
# 单变量相对照组；引擎参数走 TURNSTILE_HICACHE_ARGS 通道（run_matrix.py:348 是通用附加参数）。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through --max-prefill-tokens 65536"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane cap3pf --gpu 1 --port 30041 \
  --runs 'pois200_cap3_hc_pf64:static=3'
bash /data/xbw/turnstile/scripts/lane_done.sh cap3pf pois200_cap3_hc_pf64
