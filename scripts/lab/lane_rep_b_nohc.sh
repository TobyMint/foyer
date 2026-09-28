#!/bin/bash
# 补跑车道 B-noHC —— GPU 3，1 条 run（`_02`，device-only），配置逐组复刻该组代表 run 的 metadata.json。
# 预注册见 docs/prereg_repeats_20260928.md。**只用卡 2/3，总并发 <= 2 条。**
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
# ⚠ 这一条是 **device-only（无 HiCache）**：不设 TURNSTILE_HICACHE_ARGS。
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane rep_bn --gpu 3 --port 30073 \
  --runs "pois200_cap3_pd_rep20260928_02:static=3"
bash /data/xbw/turnstile/scripts/lane_done.sh rep_bn pois200_cap3_pd_rep20260928_02
