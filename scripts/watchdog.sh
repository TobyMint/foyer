#!/bin/bash
# Cron entry point (every 5 minutes). This box has a periodic process-reaper: on
# 09-19 it killed both queue drivers and the whole queue stopped silently, because
# nothing restarted them. The watchdog only starts a stream that is not running, so
# it is safe to run as often as you like.
#
# Install:  */5 * * * * /data/xbw/turnstile/scripts/watchdog.sh >/dev/null 2>&1
BASE=/data/xbw/turnstile
N=$BASE/results/night
LOCK=$N/.watchdog.lock
exec 9>"$LOCK" || exit 1
flock -n 9 || exit 0
cd "$BASE" || exit 1
for pair in "2:worklist_gpu2.txt" "3:worklist_gpu3.txt"; do
  gpu=${pair%%:*}
  list=${pair#*:}
  if pgrep -f "queue_stream.sh $gpu " > /dev/null; then
    continue
  fi
  echo "[$(date '+%m-%d %H:%M')] watchdog: stream gpu$gpu not running — starting $list" >> "$N/watchdog.log"
  setsid nohup bash "$BASE/scripts/queue_stream.sh" "$gpu" "$BASE/scripts/$list" \
    >> "$N/watchdog.log" 2>&1 < /dev/null &
  sleep 2
done
