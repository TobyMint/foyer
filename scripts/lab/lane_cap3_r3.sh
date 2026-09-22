#!/bin/bash
# static=3 的第三次重复（当前 harness、全程 trace、无 HiCache）。
# 为什么这条最关键：cap3_r2 与 cap3_fixed 是同配置，墙钟只差 2.2%，
# 但 SLO 差了 12.2pp（62.2 vs 74.4）。cap3_r2 是旧 harness 跑的，没有记录 trace 字段，
# 所以这 12.2pp 有两种解释：(a) 悬崖附近 SLO 本身不稳，(b) harness 口径差异。
# 这一条用当前 harness 再跑一次，直接分开这两种解释。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane cap3_r3 --gpu 2 --port 30042 \
  --runs 'pois200_cap3_r3:static=3'
bash /data/xbw/turnstile/scripts/lane_done.sh cap3_r3 pois200_cap3_r3
