#!/bin/bash
# Wave 3: complete the Poisson main table on gpu3 ONLY.
# Shared machine: wave 2 already holds gpu2, so this driver deliberately touches
# one card. Same wait/retry discipline as wave 2: sustained-free GPU before each
# attempt, per-run skip inside run_matrix, retry until the lane's last run has a
# summary.
cd /data/xbw/turnstile || exit 1
N=results/night
LOG=$N/queue_driver.log

log() { echo "[$(date '+%m-%d %H:%M')] $*" >> "$LOG"; }

log "=== wave 3 (Poisson main table, gpu3 only) queued ==="
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits |
  tr '\n' ' ' | sed 's/^/    gpu mem(MiB): /' >> "$LOG"

for attempt in $(seq 1 24); do
  if [ -f "$N/pois200_cap1/summary.json" ]; then
    log "gpu3: lane_pois_main already complete, skipping"
    break
  fi
  log "gpu3: waiting for sustained-free GPU -> lane_pois_main.sh (attempt $attempt)"
  bash scripts/wait_gpu_then_run_fast.sh 3 scripts/lane_pois_main.sh \
    >> "$N/lane_lane_pois_main_attempt${attempt}.log" 2>&1
  if [ -f "$N/pois200_cap1/summary.json" ]; then
    log "gpu3: lane_pois_main COMPLETE"
    break
  fi
  log "gpu3: lane_pois_main produced no summary (pool guard abort?); retry in 10 min"
  sleep 600
done
log "gpu3: wave 3 queue drained"
