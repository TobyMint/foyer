#!/bin/bash
# The repaired controller, at EXACTLY rl90's configuration.
#
# This is the experiment the audit's findings call for: same trace, same pool, same
# red line, same growth scale — the only thing that differs from pois200_foyer_rl90
# is the controller code. So any change in concurrency or wall clock is attributable
# to the four fixes and not to a parameter.
#
# What rl90 did (300.2 min, 57.7% hit, 2.84 concurrency) was limited by defects, not
# by physics: the ledger read 100% while the engine sat at 64%. Each session was
# charged for its whole first round instead of just its prefill, a fresh admission
# blocked the next one until the previous session COMPLETED a round, only the head of
# the wait queue was ever considered, and a shed session's capacity was released
# before the runner had acted on the pause.
#
# The prediction, stated in advance so it can be falsified: concurrency rises well
# above 2.84 and the ledger stops pinning at 100%. Whether the extra concurrency then
# buys wall clock is the question that actually matters — rl90 showed it is possible
# to gain concurrency and lose quality with nothing in return.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane foyer_rl90fix --gpu 3 --port 30033 \
  --runs 'pois200_foyer_rl90fix:foyer:target=0.90;gs=0.35'
bash /data/xbw/turnstile/scripts/lane_done.sh foyer_rl90fix pois200_foyer_rl90fix
