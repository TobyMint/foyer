#!/bin/bash
# Fast variant of wait_gpu_then_run.sh: poll every INTERVAL seconds and start as
# soon as POLLS consecutive samples are under FREE_MIB (default 2 x 30s = ~1 min,
# instead of the old 6 x 5min = 25 min).
#
# Why this is safe now: the slow version dates from before run_matrix's pool guard
# existed. Back then a neighbour's VRAM residue at server start silently shrank the
# KV pool, so the only defence was to wait for a long stretch of genuine idleness.
# The guard now solves mem_fraction_static to reach the aligned pool and absorbs
# ~1,150 MiB of residue; beyond that the run aborts BEFORE anything is recorded and
# the driver retries. Racing a neighbour who is about to launch therefore costs one
# aborted attempt, not a corrupted run.
#
# Usage: wait_gpu_then_run_fast.sh <gpu> <lane_script>
FREE_MIB=${FREE_MIB:-1000}
POLLS=${FREE_POLLS:-2}
INTERVAL=${FREE_INTERVAL:-30}
GPU=$1
SCRIPT=$2
free_hits=0
while true; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$GPU")
  if [ "$used" -lt "$FREE_MIB" ]; then
    free_hits=$((free_hits+1))
    if [ "$free_hits" -ge "$POLLS" ]; then break; fi
  else
    free_hits=0
  fi
  sleep "$INTERVAL"
done
echo "[$(date +%H:%M:%S)] GPU$GPU free (${POLLS} consecutive samples), starting lane $SCRIPT"
bash "$SCRIPT"
