#!/bin/bash
# 半上下文 trace：每个请求占的显存减半，于是安全并发数应该翻倍。
# 静态 cap 只会数数，看不见"每个请求变轻了"，所以它会继续卡在 2 —— 把容量白白空着。
# Foyer 看的是池子利用率，应该自动放开。
# 判据：若 Foyer 在 c50 上没有明显快过 cap2，则"自适应"这条贡献不成立。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04_c50.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane cap2_c50 --gpu 2 --port 30042 \
  --runs 'pois200_cap2_c50:static=2'
bash /data/xbw/turnstile/scripts/lane_done.sh cap2_c50 pois200_cap2_c50
