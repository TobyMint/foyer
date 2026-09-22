#!/bin/bash
# 【策略取舍实验，不是修 bug】
# 把增长预留归零（predictor=zero），在 pois200 这个负载上量出这笔买卖的价格。
# 别的 trace 上量过：budget200c +50% 并发 / −4pp SLO；load25c +27% 并发 / −0.8pp SLO。
# 但 pois200 上没量过，而那是我们全部主张所在的负载。
# 判据：并发从 2.06 涨到多少、SLO 从 89.8 掉到多少。用户决定要不要换。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane foyer_zero --gpu 2 --port 30042 \
  --runs 'pois200_foyer_zero:budget3:hw=0;target=0.95;predictor=zero'
bash /data/xbw/turnstile/scripts/lane_done.sh foyer_zero pois200_foyer_zero
