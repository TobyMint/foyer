#!/bin/bash
# base_mode=resident：投影的底座从 max(resident, ctx_sum) 改成只用 resident（引擎遥测）。
# 这是【单参数】实验，对照组就是 foyer_hc（budget3:hw=0;target=0.95，其余逐字相同）。
#
# 为什么值得跑：论文贡献 2 说"控制变量必须取实测物理占用，不能取会话侧台账"，
# 但控制器自己没遵守——`max` 让 ctx_sum 主导了 57% 的控制周期（实测 8784 个周期：
# ctx_sum 4973、resident 3811）。改成 resident 之后控制器才第一次执行自己那条规则。
#
# 注意这【不显然是修 bug】：ctx_sum 也是"这些会话等会儿要拿回多少"的代理，
# 而引擎的 token_usage 排除 evictable 块，两者会朝两个方向分歧。这个 run 就是判谁对。
#
# 判据：如果 resident 是"去掉了一个虚高"，并发应该涨【并且不掉 SLO】——那就是 Pareto 前沿
#       【上方】的点，论文第一次有反超。如果并发涨、SLO 同比掉，那它只是另一个 horizon，
#       等于把 §二十七 再确认一遍。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane bres --gpu 0 --port 30040 \
  --runs 'pois200_foyer_bres:budget3:hw=0;target=0.95;base=resident'
bash /data/xbw/turnstile/scripts/lane_done.sh bres pois200_foyer_bres
