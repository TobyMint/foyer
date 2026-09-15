#!/bin/bash
# Wave driver: waits for the current lanes to finish, then launches the next wave
# automatically. Runs on the lab (nohup), so the pipeline keeps moving without
# anyone watching. One wave per invocation; the caller logs what it launched.
cd /data/xbw/turnstile || exit 1
N=results/night
LOG=$N/wave_driver.log

echo "[$(date '+%m-%d %H:%M')] driver up: waiting for pois_cap2 + pois_foyer" >> "$LOG"
while [ ! -f "$N/lane_pois_cap2_DONE" ] || [ ! -f "$N/lane_pois_foyer_DONE" ]; do
  sleep 60
done
echo "[$(date '+%m-%d %H:%M')] wave A done -> launching wave B (pois cap3+cap4 | p200 fixed config)" >> "$LOG"

nohup bash scripts/lane_pois_cap34.sh > "$N/lane_pois_cap34.log" 2>&1 &
echo "  launched pois_cap34 (gpu 2) pid $!" >> "$LOG"
nohup bash scripts/lane_p200_fix.sh > "$N/lane_p200_fix.log" 2>&1 &
echo "  launched p200_fix (gpu 3) pid $!" >> "$LOG"

echo "[$(date '+%m-%d %H:%M')] driver exiting (wave B is supervised by its own lanes)" >> "$LOG"
