#!/bin/bash
# Lane B (GPU2): aimd repeats + the three budget2 ablations, all at load200.
export TURNSTILE_MEMFRAC=0.88
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane repB --gpu 2 --port 30001 \
  --runs aimd_r2:aimd,aimd_r3:aimd,budget2_nohw:budget2_nohw,budget2_nosf:budget2_nosf,budget2_nosv:budget2_nosv
touch /data/xbw/turnstile/results/night/lane_repB_DONE
