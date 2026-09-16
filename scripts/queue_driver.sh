#!/bin/bash
# Persistent queue driver: each of our two cards works through its own list of
# pending lanes, waiting for the GPU to be sustained-free before every attempt and
# retrying until the run actually produces a summary. Designed to sit unattended:
# it logs GPU availability as it polls, so we can see when a neighbour's job left.
cd /data/xbw/turnstile || exit 1
N=results/night
LOG=$N/queue_driver.log

log() { echo "[$(date '+%m-%d %H:%M')] $*" >> "$LOG"; }

gpu_snapshot() {
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits |
    tr '\n' ' ' | sed 's/^/    gpu mem(MiB): /' >> "$LOG"
}

# lane list per card: "lane_script run_marker" (marker = the run that must complete)
work_card() {
  local gpu=$1 marker script
  shift
  while [ $# -gt 0 ]; do
    script=$1; marker=$2; shift 2
    if [ -f "$N/$marker/summary.json" ]; then
      log "gpu$gpu: $marker already done, skipping"
      continue
    fi
    for attempt in $(seq 1 24); do
      log "gpu$gpu: waiting for sustained-free GPU -> $script (attempt $attempt)"
      gpu_snapshot
      bash scripts/wait_gpu_then_run.sh "$gpu" "scripts/$script"
      if [ -f "$N/$marker/summary.json" ]; then
        log "gpu$gpu: $marker COMPLETE"
        break
      fi
      log "gpu$gpu: $marker produced no summary (pool guard abort?); retry in 10 min"
      sleep 600
    done
  done
  log "gpu$gpu: queue drained"
}

log "=== queue driver up ==="
gpu_snapshot

work_card 2 lane_fix25.sh load25c_cap3r   lane_pois_cap3r.sh pois200_cap3_r2 &
P2=$!
work_card 3 lane_p200_fixr.sh p200_fix_r2 &
P3=$!
wait $P2 $P3
log "=== queue driver finished all work ==="
