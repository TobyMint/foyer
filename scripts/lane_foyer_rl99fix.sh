#!/bin/bash
# The repaired controller at rl99's configuration — the second half of the pair.
#
# rl90fix answers "does fixing the accounting raise concurrency at a fixed config".
# This one asks it at the aggressive config, where the answer matters more: rl99
# reached 3.30 concurrency but was 60 minutes SLOWER than cap3 and dominated by it,
# because its own hard valve fired on 45% of decision cycles and the engine idled 28%
# of the time. Two of the four fixes bear directly on that (the shed capacity that
# was released before the runner acted, and the head-of-line block), so if the
# diagnosis is right this arm should idle less than rl99 did.
#
# Same parameters as pois200_foyer_rl99 (target=0.99, gs=0.05, hs=0.98) so the only
# difference is the controller code. Reference point: 362.0 min, 46.3% hit, conc 3.30.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane foyer_rl99fix --gpu 3 --port 30033 \
  --runs 'pois200_foyer_rl99fix:foyer:target=0.99;gs=0.05;hs=0.98'
bash /data/xbw/turnstile/scripts/lane_done.sh foyer_rl99fix pois200_foyer_rl99fix
