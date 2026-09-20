#!/bin/bash
# Wave 4 (gpu2): real-arrival sweep. Same wait/retry discipline as waves 2-3.
# This box has a periodic process-reaper that has killed our drivers before, so
# the retry loop is what keeps a lane alive across reaps.
cd /data/xbw/turnstile || exit 1
N=results/night
LOG=$N/queue_driver.log

log() { echo "[$(date '+%m-%d %H:%M')] $*" >> "$LOG"; }

log "=== wave 4 (real-arrival sweep, gpu2) queued ==="
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits |
  tr '\n' ' ' | sed 's/^/    gpu mem(MiB): /' >> "$LOG"

for attempt in $(seq 1 24); do
  if [ -f "$N/realhr_cap1/summary.json" ]; then
    log "gpu2: lane_realhr_sweep already complete, skipping"
    break
  fi
  log "gpu2: waiting for sustained-free GPU -> lane_realhr_sweep.sh (attempt $attempt)"
  bash scripts/wait_gpu_then_run_fast.sh 2 scripts/lane_realhr_sweep.sh \
    >> "$N/lane_lane_realhr_sweep_attempt${attempt}.log" 2>&1
  if [ -f "$N/realhr_cap1/summary.json" ]; then
    log "gpu2: lane_realhr_sweep COMPLETE"
    break
  fi
  log "gpu2: lane_realhr_sweep produced no summary; retry in 10 min"
  sleep 600
done
log "gpu2: wave 4 queue drained"
