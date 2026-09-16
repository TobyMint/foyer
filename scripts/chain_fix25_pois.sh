#!/bin/bash
# Chain: after the short 25-tier alignment lane finishes, queue the Poisson cap3
# re-run behind a fresh GPU-availability waiter (card 2).
cd /data/xbw/turnstile || exit 1
N=results/night
while [ ! -f "$N/lane_fix25_DONE" ]; do sleep 60; done
echo "[$(date '+%m-%d %H:%M')] fix25 done -> queueing pois cap3 re-run on gpu 2" >> "$N/wave_driver.log"
nohup bash scripts/wait_gpu_then_run.sh 2 scripts/lane_pois_cap3r.sh > "$N/waiter_gpu2.log" 2>&1 &
echo "  queued pois_cap3r pid $!" >> "$N/wave_driver.log"
