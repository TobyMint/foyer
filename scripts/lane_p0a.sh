#!/bin/bash
# P0 lane A (GPU3, ports free after lane_repA): tier-25 full matrix at the unified
# KV pool (memfrac 0.85 = 101,432 tokens). Cap sweep 1-8 substantiates the oracle,
# aimd2 is the faithful Concur, budget3 the online-predictor Foyer, budget2 the
# trace-oracle upper bound. Order: decisive runs first.
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p0a --gpu 3 --port 30000 \
  --runs load25c_budget3:budget3,load25c_default:default,load25c_cap4:static=4,load25c_cap6:static=6,load25c_aimd2:aimd2,load25c_aimd2_i2:aimd2:interval=2,load25c_budget2:budget2,load25c_cap1:static=1,load25c_cap2:static=2,load25c_cap3:static=3,load25c_cap5:static=5,load25c_cap7:static=7,load25c_cap8:static=8
touch /data/xbw/turnstile/results/night/lane_p0a_DONE
