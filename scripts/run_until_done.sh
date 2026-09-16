#!/bin/bash
# run_until_done.sh <gpu> <lane_script> <first_run_name> [max_attempts]
# Keep retrying a lane until its first run actually produced a summary. Each attempt
# first waits for the GPU to be sustained-free; the pool guard inside run_matrix
# aborts (rather than records) any attempt that starts while a neighbour holds VRAM.
GPU=$1
SCRIPT=$2
RUN=$3
MAX=${4:-20}
N=/data/xbw/turnstile/results/night
cd /data/xbw/turnstile || exit 1

for i in $(seq 1 "$MAX"); do
  bash scripts/wait_gpu_then_run.sh "$GPU" "$SCRIPT"
  if [ -f "$N/$RUN/summary.json" ]; then
    echo "[$(date '+%H:%M:%S')] $RUN produced a summary — done (attempt $i)"
    exit 0
  fi
  echo "[$(date '+%H:%M:%S')] attempt $i: $RUN has no summary (pool guard abort or crash); retrying in 10 min"
  sleep 600
done
echo "[$(date '+%H:%M:%S')] giving up on $RUN after $MAX attempts"
exit 1
