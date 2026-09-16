#!/bin/bash
# Wait until the given GPU is genuinely free — three consecutive 5-min polls under
# 300 MiB (a single snapshot is not enough: neighbours land after launch) — then run
# the lane. Threshold history: 2 GiB was too lax. SGLang sizes the KV pool from free
# VRAM, and a neighbour holding even ~1.6 GiB pushed the pool under the aligned
# 101,432, so every attempt was aborted by the pool guard (2026-09-16). A few hundred
# MiB is display/context residue; GB-scale residues make runs un-comparable.
# Usage: wait_gpu_then_run.sh <gpu> <lane_script>
GPU=$1
SCRIPT=$2
free_hits=0
while true; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$GPU")
  if [ "$used" -lt 300 ]; then
    free_hits=$((free_hits+1))
    if [ "$free_hits" -ge 6 ]; then break; fi
  else
    free_hits=0
  fi
  sleep 300
done
echo "[$(date +%H:%M:%S)] GPU$GPU sustained-free, starting lane $SCRIPT"
bash "$SCRIPT"
