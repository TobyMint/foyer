#!/bin/bash
# THE CEILING TEST for the wall-clock question.
#
# Why this run exists. On 2026-09-22 the controller arms were found to sit at
# time-average session concurrency ~2.06 while cap4+HiCache sits at 3.93 on the
# same trace, with the pool ~50% idle and 26-93 sessions queued outside. 87% of
# the controller's cycles are "stuck": someone waiting, nobody admitted, and the
# SLO valve not firing. Three legacy throttles are candidates, and the repairs for
# them were applied to controller_foyer.py but never to the run that was actually
# being quoted:
#
#   single-flight        one admission at a time, gated on the previous one starting
#   head-of-line window  budget3 uses waiting[:1]; foyer uses candidate-window=8
#   starve guard         gated on floor < 0.5, and the floor sits at 0.49
#
# So: foyer's controller (which has the window repair), every legacy throttle off,
# the aggressive red line, and HiCache on -- the combination that has never run.
#
# This is a feasibility ceiling, deliberately four variables at once. If it cannot
# reach cap4+HiCache (219.0 min / avg concurrency 3.93), the approach cannot win on
# wall clock and the paper's claim has to change. If it can, the next run bisects.
#
# Judge it on ACHIEVED CONCURRENCY, not wall clock: a controller that admits more
# and lands 20 minutes slower is a different finding from one that still sits at 2.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane foyfix_hc --gpu 2 --port 30032 \
  --runs 'pois200_foyfix_hc:foyer:target=0.95;hw=0;sf=0;sg=0'
bash /data/xbw/turnstile/scripts/lane_done.sh foyfix_hc pois200_foyfix_hc
