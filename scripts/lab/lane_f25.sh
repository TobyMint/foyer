#!/bin/bash
# 25 档 Foyer（节流全关那档，thr25_push 的同代重跑）
# 25 档：125 步一条，约 30 分钟。目的是补【静态前沿对照】——原来那批七条全是 budget3 变体。
set -e
export TURNSTILE_RUN_TIMEOUT_H=3
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane f25 --gpu 3 --port 30043 \
  --runs 'pois200_foyer_push_25:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh f25 pois200_foyer_push_25
