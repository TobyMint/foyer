#!/bin/bash
# P0 lane B (GPU2, after lane_repB): tier-200 core at the unified pool, decisive
# runs first (budget3 = headline; cap4/3/5 = oracle neighborhood; aimd2 = faithful
# Concur; budget2 = trace-oracle bound). Cleaned trace (999 rows, empty round dropped).
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p0b --gpu 2 --port 30001 \
  --runs budget200c_budget3:budget3,budget200c_cap4:static=4,budget200c_default:default,budget200c_cap3:static=3,budget200c_cap5:static=5,budget200c_aimd2:aimd2,budget200c_budget2:budget2
touch /data/xbw/turnstile/results/night/lane_p0b_DONE
