#!/bin/bash
# Wait until the given GPU is genuinely free — six consecutive 5-min polls under
# FREE_MIB (a single snapshot is not enough: neighbours land after launch) — then run
# the lane.
#
# Threshold calibration. SGLang sizes the KV pool from free VRAM, so ANY neighbour
# residue shifts the pool and the guard aborts the run. The earlier 300 MiB threshold
# rested on the assumption that "a few hundred MiB is display/context residue" — that
# is wrong, and 2026-09-17 falsified it: a neighbour job (another user's
# 48b_collect_layerwise_oracle.py) held 254 MiB on GPUs 2 and 3 for hours, which put
# the pool at 97,398 instead of 101,432, i.e. ~16 tokens lost per MiB held. 254 < 300,
# so the check passed and every attempt died in the pool guard.
# A genuinely idle card reads single-digit MiB; 100 leaves room for that without
# admitting a residue large enough to move the pool.
# Usage: wait_gpu_then_run.sh <gpu> <lane_script>
FREE_MIB=100
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
