#!/bin/bash
# Pool-drift experiment (25-tier): the same sessions, but the KV pool shrunk ~25%
# (101,432 -> ~76,000 tokens). The pool guard solves mem_fraction_static to reach the
# target, so the pool stays the invariant and the dial moves.
#
# Question this answers: does the optimal static cap move when the pool changes, and
# does the UNCHANGED Foyer config still land on the new frontier? That is the direct
# evidence for "n is not portable" — currently only inferred from one pool size.
set -e
export TURNSTILE_RUN_TIMEOUT_H=8
export TURNSTILE_MEMFRAC=0.79
export TURNSTILE_EXPECT_POOL=76000
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane drift25 --gpu 3 --port 30033 --runs 'drift25_cap2:static=2'
$P $S --lane drift25 --gpu 3 --port 30033 --runs 'drift25_cap1:static=1'
$P $S --lane drift25 --gpu 3 --port 30033 --runs 'drift25_cap3:static=3'
$P $S --lane drift25 --gpu 3 --port 30033 --runs 'drift25_cap4:static=4'
$P $S --lane drift25 --gpu 3 --port 30033 --runs 'drift25_foyer:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh drift25 \
  drift25_cap2 drift25_cap1 drift25_cap3 drift25_cap4 drift25_foyer
