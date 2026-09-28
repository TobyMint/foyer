#!/bin/bash
# `horizon=2` 的**第三次测量** —— 全篇头条所依赖的那条臂的重复。
#
# 为什么跑：论文写着「the closest arm is horizon=2 at 0.30pp below the line」，
# 而这条臂**只有一次 run**（§VI 也明写「horizon=2 has one run, so its +1.0pp at 20s is a
# single measurement with no repeat to check it against」）。0.30pp 比我们实测到的复跑散布
# （最宽 5.1pp）小一个数量级，所以「它到底在不在线下方」目前是一个单次读数。
#
# **跑之前写在头部的预期**（照抄，免得事后挑说法）：
#   (a) 若新 run 的 Δ 仍在 ±1.0pp 带内（不管偏上偏下）→ 头条「九条臂无一越线」不变，
#       而且这条臂从「单次读数」变成「两次读数」；
#   (b) 若它落到 **+1.0pp 以上** → 论文的头条被推翻，必须照实改写（负结果不成立的那一面）；
#   (c) 若两次读数差得比 1.0pp 还多 → 说明这条臂的不可分辨性比论文写的更大，也要照实说。
# 三种都要写进 §V/§VI，**不许只报对自己有利的那种**。
#
# 配置与 `pois200_foyer_hz2_r2` 逐字相同（policy 串是唯一判据）：
#   budget3:hw=0;target=0.95;horizon=2
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane hz2r3 --gpu 3 --port 30085 \
  --runs 'pois200_foyer_hz2_r3:budget3:hw=0;target=0.95;horizon=2'
bash /data/xbw/turnstile/scripts/lane_done.sh hz2r3 pois200_foyer_hz2_r3
