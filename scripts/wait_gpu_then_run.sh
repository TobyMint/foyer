#!/bin/bash
# Wait until the given GPU is genuinely free — six consecutive 5-min polls under
# FREE_MIB (a single snapshot is not enough: neighbours land after launch) — then run
# the lane.
#
# Threshold calibration. SGLang sizes the KV pool from free VRAM, so a neighbour's
# residue shifts the pool: a job holding 254 MiB on this card put it at 97,398
# instead of 101,432 (~16 tokens lost per MiB held).
#
# That is no longer fatal. run_matrix's pool guard now SOLVES for the memory
# fraction that reaches the aligned pool instead of aborting, and it can absorb a
# shortfall of (MAX_MEMFRAC - nominal) * tokens-per-fraction ~= 1,150 MiB before the
# solve runs out of headroom. So the wait only needs to reject residues beyond what
# the solve can compensate for — waiting for a perfectly clean card would block a
# lane indefinitely for a residue that costs nothing.
#
# Usage: wait_gpu_then_run.sh <gpu> <lane_script>
FREE_MIB=1000
GPU=$1
SCRIPT=$2
free_hits=0
while true; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$GPU")
  if [ "$used" -lt "$FREE_MIB" ]; then
    free_hits=$((free_hits+1))
    if [ "$free_hits" -ge 6 ]; then break; fi
  else
    free_hits=0
  fi
  sleep 300
done
echo "[$(date +%H:%M:%S)] GPU$GPU sustained-free, starting lane $SCRIPT"
bash "$SCRIPT"
