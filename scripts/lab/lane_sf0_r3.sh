#!/bin/bash
# `single-flight off` 的第二次测量（`pois200_foyer_sf0_r3`）—— 第二近那条臂的第一次重复。
#
# 为什么跑：论文写着「the closest arm is `horizon`=2 at 0.30pp below the line」，
# 而**第二近的**就是这条（Δ = −0.55，在 ±1.0pp 带内）。它**只有一次读数**，
# 而「九条控制器臂无一越线」这条头条主张**也依赖它**（它离带的上沿只差 1.55pp）。
# 它还是 §V 里唯一一个「同一个控制器、只关掉单飞这一根旋钮」的两百档臂。
#
# **跑之前写在头部的预期**（照抄，免得事后挑说法）：
#   (a) 仍落在 ±1.0pp 带内（不管偏上偏下）→ 头条不变，该臂从一次读数变成两次；
#   (b) 落到 **+1.0pp 以上** → **有控制器越线，头条被推翻，照实改写，不许只报有利的那种**；
#   (c) 两次相差 >1.0pp → 连第二近的臂都不可分辨，照实说（这会让 §V 的「最近」叙事更弱）。
#
# 配置与 `pois200_foyer_sf0_r2` 逐字相同（policy 串是唯一判据）：
#   budget3:hw=0;target=0.95;sf=0
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane sf0r3 --gpu 3 --port 30087 \
  --runs 'pois200_foyer_sf0_r3:budget3:hw=0;target=0.95;sf=0'
bash /data/xbw/turnstile/scripts/lane_done.sh sf0r3 pois200_foyer_sf0_r3
