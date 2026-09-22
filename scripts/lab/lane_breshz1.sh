#!/bin/bash
# base=resident + horizon=1：两个旋钮的交互点。
# 若 bres 是"去掉虚高"（并发涨、SLO 不掉），那这一条就是论文的头号配置——
# 两个改良叠在一起。若 base=resident 只是"另一个 horizon"，这一条就把
# 两个旋钮的可加性测出来（bres 的效应在 horizon=3 和 horizon=1 上是否同号同量）。
# 对照组仍是 foyer_hc，单参数差在 base 与 horizon 两处，所以它只作交互解释、不作因果解释。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane breshz1 --gpu 2 --port 30042 \
  --runs 'pois200_foyer_breshz1:budget3:hw=0;target=0.95;horizon=1;base=resident'
bash /data/xbw/turnstile/scripts/lane_done.sh breshz1 pois200_foyer_breshz1
