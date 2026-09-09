#!/bin/bash
# Wait until the given GPU is sustained-free (two consecutive 5-min polls under
# 2 GiB — a single snapshot is not enough, freeloaders land after launch), then
# execute the lane script. Usage: wait_gpu_then_run.sh <gpu> <lane_script>
GPU=$1
SCRIPT=$2
free_hits=0
while true; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$GPU")
  if [ "$used" -lt 2000 ]; then
    free_hits=$((free_hits+1))
    if [ "$free_hits" -ge 2 ]; then break; fi
  else
    free_hits=0
  fi
  sleep 300
done
echo "[$(date +%H:%M:%S)] GPU$GPU sustained-free, starting lane $SCRIPT"
bash "$SCRIPT"
