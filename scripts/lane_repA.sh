#!/bin/bash
# Lane A (GPU3): error-bar repeats for the headline load200 tier.
# budget2_r2/r3: mechanism repeats; cap4_r2/r3: oracle-cap repeats.
export TURNSTILE_MEMFRAC=0.88
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane repA --gpu 3 --port 30000 \
  --runs budget2_r2:budget2,budget2_r3:budget2,cap4_r2:static=4,cap4_r3:static=4
touch /data/xbw/turnstile/results/night/lane_repA_DONE
