#!/bin/bash
# 足迹上限 80k token（安全带边缘，§五十二 预测的最优点）
# 纯足迹控制器：projection = resident + 候选，无增长预留(horizon=0)，无会话数上限。
# target 就是【并发总足迹上限】占池比例。对照 foyer_hc = budget3:hw=0;target=0.95 (291.3/2.06/89.8)
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane fp80 --gpu 1 --port 30041 \
  --runs 'pois200_foyer_fp80:budget3:hw=0;target=0.79;horizon=0;base=resident'
bash /data/xbw/turnstile/scripts/lane_done.sh fp80 pois200_foyer_fp80
