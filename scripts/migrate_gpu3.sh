#!/bin/bash
# One-shot switch, run from cron every 5 min: the gpu3 stream has the OLD work list
# buffered in memory, so once its current lane (Poisson completion) is finished, stop
# the stream and let watchdog.sh restart it with the Poisson-only list.
N=/data/xbw/turnstile/results/night
[ -f "$N/.gpu3_migrated" ] && exit 0
[ -f "$N/pois200_cap1/summary.json" ] || exit 0
touch "$N/.gpu3_migrated"
echo "[$(date '+%m-%d %H:%M')] migrate: Poisson lane complete — restarting gpu3 stream with the Poisson-only list" >> "$N/watchdog.log"
pkill -f "queue_stream.sh 3 "
