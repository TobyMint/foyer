#!/bin/bash
# 短 trace 的另一半：cap2 + HiCache，同一条 r2 trace。
# 两条一起才构成"短 trace 是否复现全程排序"的检验。
set -e
export TURNSTILE_RUN_TIMEOUT_H=6
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04_r2.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane cap2_r2 --gpu 3 --port 30043 \
  --runs 'pois200_cap2_r2:static=2'
bash /data/xbw/turnstile/scripts/lane_done.sh cap2_r2 pois200_cap2_r2
