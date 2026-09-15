#!/bin/bash
# Second-stage driver: once the Poisson static sweep (cap3+cap4) is done, run the
# real-arrival trace on the freed card. Chain: pois sweep -> real-hour study.
cd /data/xbw/turnstile || exit 1
N=results/night
LOG=$N/wave_driver.log

echo "[$(date '+%m-%d %H:%M')] driver2 up: waiting for pois_cap34" >> "$LOG"
while [ ! -f "$N/lane_pois_cap34_DONE" ]; do
  sleep 60
done
echo "[$(date '+%m-%d %H:%M')] pois sweep done -> launching real-hour study (gpu 2)" >> "$LOG"
nohup bash scripts/lane_realhr.sh > "$N/lane_realhr.log" 2>&1 &
echo "  launched realhr (gpu 2) pid $!" >> "$LOG"
echo "[$(date '+%m-%d %H:%M')] driver2 exiting" >> "$LOG"
