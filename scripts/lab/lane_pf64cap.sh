#!/bin/bash
# 步时间杠杆·静态对照：Cap4+HiCache，prefill 批预算 16384->65536。对照 cap4_hc 213.0/3.93/63.4
# 引擎侧：只改起服参数，不改代码。依据 §五十五 的模型 wall = 产出 × 步时间 / 在跑均值。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through --max-prefill-tokens 65536"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane pf64cap --gpu 2 --port 30042 \
  --runs 'pois200_cap4_hc_pf64:static=4'
bash /data/xbw/turnstile/scripts/lane_done.sh pf64cap pois200_cap4_hc_pf64
