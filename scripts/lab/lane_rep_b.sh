#!/bin/bash
# 补跑车道 B —— GPU 3，9 条 run（`_02`），配置逐组复刻该组代表 run 的 metadata.json。
# 预注册见 docs/prereg_repeats_20260928.md。**只用卡 2/3，总并发 <= 2 条。**
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane rep_b --gpu 3 --port 30063 \
  --runs "pois200_foyer_hc_rep20260928_02:budget3:hw=0;target=0.95,pois200_foyer_hz1_rep20260928_02:budget3:hw=0;target=0.95;horizon=1,pois200_foyer_scan_rep20260928_02:budget3scan:hw=0;target=0.95,pois200_cap4_hc_rep20260928_02:static=4,pois200_cap2_hc_rep20260928_02:static=2,pois200_cap3_hc_rep20260928_02:static=3,pois200_foyer_hz2_rep20260928_02:budget3:hw=0;target=0.95;horizon=2,pois200_foyer_sf0_rep20260928_02:budget3:hw=0;target=0.95;sf=0"
bash /data/xbw/turnstile/scripts/lane_done.sh rep_b pois200_foyer_sf0_rep20260928_02
