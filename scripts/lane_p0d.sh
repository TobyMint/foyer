#!/bin/bash
# P0 lane D (GPU3, after budget3_r2 finishes): the decisive 200-tier comparisons,
# ordered by importance. budget3 itself is covered by r2 on this same GPU/pool, so
# this lane carries the opponents: oracle (cap4/3/5), default, faithful aimd2, bound.
# Armed on the sustained-free poller — if labmates hold GPU2, GPU3 carries the tier.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night200_clean.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane p0d --gpu 3 --port 30002 \
  --runs budget200c_cap4:static=4,budget200c_default:default,budget200c_aimd2:aimd2,budget200c_cap3:static=3,budget200c_cap5:static=5,budget200c_budget2:budget2
touch /data/xbw/turnstile/results/night/lane_p0d_DONE
