#!/bin/bash
# 步时间杠杆（Foyer）：对照 foyer_hc 291.3/89.8
# 引擎侧批次：改的是【上界本身】，不依赖政策维度。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through --max-prefill-tokens 65536"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane pf64foy --gpu 1 --port 30041 \
  --runs 'pois200_foyer_hc_pf64:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh pf64foy pois200_foyer_hc_pf64
