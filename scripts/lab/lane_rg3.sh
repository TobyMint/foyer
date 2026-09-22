#!/bin/bash
# round-gate=3：在跑的最多 3 个（预测最优点）
# 纯足迹记账 + round-gate：base=resident 让停放会话不再被重复收费（活着的会话变多），
# rgate 把【在跑】的数量钉住（TTFT 有界）。对照 = 同样记账但不加闸（nogate）。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane rg3 --gpu 1 --port 30041 \
  --runs 'pois200_foyer_rg3:budget3:hw=0;target=0.95;horizon=0;base=resident;rgate=3'
bash /data/xbw/turnstile/scripts/lane_done.sh rg3 pois200_foyer_rg3
