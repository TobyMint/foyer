#!/bin/bash
# 200-tier fixed config WITH HiCache. Mechanism ② so far only has a 25-tier host-tier
# measurement in the current config lineage; this gives the 200-tier on/off pair against
# p200_fix_r2 (no HiCache), same sessions, same controller parameters.
set -e
export TURNSTILE_RUN_TIMEOUT_H=14
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane hc200 --gpu 3 --port 30033 \
  --runs 'p200_fix_hc:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh hc200 p200_fix_hc
