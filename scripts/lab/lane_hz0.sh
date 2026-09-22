#!/bin/bash
# horizon_rounds=0：增长预留整个关掉，是 horizon 价格曲线（foyer_hc=3、hz2=2、hz1=1、本条=0）的端点。
# 与 hz1 只在 horizon 一个参数上不同，对照组同 foyer_hc。
#
# 机制：forecast() 返回 est * horizon_rounds，horizon=0 时恒为 0，growth_sum 归零。
# §四十九 实测：8784 个控制周期里 7639 个是被这一项挡住的；去掉它 65% 会放行。
# 所以这是"那道闸到底值多少钱"的直接标价，也是 §四十四 里 foyer_rl90fix / foyfix 那条
# "拿 SLO 换并发"标价的同族点——但那条用的是另一个控制器（foyer: 前缀），不能混比。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane hz0 --gpu 1 --port 30041 \
  --runs 'pois200_foyer_hz0:budget3:hw=0;target=0.95;horizon=0'
bash /data/xbw/turnstile/scripts/lane_done.sh hz0 pois200_foyer_hz0
