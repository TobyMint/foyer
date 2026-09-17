#!/bin/bash
# Second-wave queue: the Concur-parameter reruns. It must NOT run concurrently with
# queue_driver.sh (both would fight for the same two cards), so it waits for the
# first driver's "finished all work" line *appearing after we start* — matching on
# the file directly would immediately re-match the previous wave's line.
cd /data/xbw/turnstile || exit 1
N=results/night
LOG=$N/queue_driver.log

log() { echo "[$(date '+%m-%d %H:%M')] $*" >> "$LOG"; }

gpu_snapshot() {
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits |
    tr '\n' ' ' | sed 's/^/    gpu mem(MiB): /' >> "$LOG"
}

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
      bash scripts/wait_gpu_then_run.sh "$gpu" "scripts/$script" \
        >> "$N/lane_${script%.sh}_attempt${attempt}.log" 2>&1
      grep -h "POOL MISMATCH\|pool=" "$N/lane_${script%.sh}_attempt${attempt}.log" 2>/dev/null \
        | tail -2 | sed 's/^/    /' >> "$LOG"
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

# Wait for wave 1 by PROCESS, not by its log line. The line-based version had to
# ignore everything already in the log (or it re-matched the previous wave's line),
# which meant that once wave 1 had finished before this driver started, it waited
# forever for an occurrence that would never come. The bracket keeps the pattern
# from matching this script's own command line.
log "=== wave 2 (Concur paper params) queued ==="
while pgrep -f 'scripts/queue_drive[r]\.sh' > /dev/null; do
  sleep 300
done
log "=== wave 1 not running, wave 2 starting ==="
gpu_snapshot

work_card 2 lane_aimd2_paper.sh aimd2_paper &
P2=$!
work_card 3 lane_aimd2_grid.sh aimd2_ul35 &
P3=$!
wait $P2 $P3
log "=== wave 2 finished all work ==="
