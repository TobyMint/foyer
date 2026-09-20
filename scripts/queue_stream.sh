#!/bin/bash
# One work stream per GPU. Walks a work list of "<lane_script> <marker_run>" lines:
# skip lanes whose marker run already has a summary, otherwise wait for the GPU and
# run the lane, retrying until the marker lands. Idempotent by design — a stream that
# gets killed by the box's periodic process-reaper is simply restarted by watchdog.sh
# and resumes at the first unfinished line.
#
# Usage: queue_stream.sh <gpu> <worklist_file>
set -u
GPU=$1
LIST=$2
BASE=/data/xbw/turnstile
N=$BASE/results/night
LOG=$N/queue_driver.log
log() { echo "[$(date '+%m-%d %H:%M')] stream$GPU: $*" >> "$LOG"; }

cd "$BASE" || exit 1
log "work list $LIST starting (gpu$GPU)"
while read -r lane marker _rest; do
  case "${lane:-}" in ""|\#*) continue ;; esac
  if [ -f "$N/$marker/summary.json" ]; then
    log "$lane already done ($marker) — skip"
    continue
  fi
  for attempt in $(seq 1 30); do
    if [ -f "$N/$marker/summary.json" ]; then break; fi
    log "gpu$GPU waiting -> $lane (attempt $attempt)"
    bash "$BASE/scripts/wait_gpu_then_run_fast.sh" "$GPU" "scripts/$lane" \
      >> "$N/stream_gpu${GPU}_${lane%.sh}_attempt${attempt}.log" 2>&1
    if [ -f "$N/$marker/summary.json" ]; then
      log "$lane COMPLETE"
      break
    fi
    log "$lane produced no summary; retry in 10 min"
    sleep 600
  done
done < "$LIST"
log "work list $LIST drained (gpu$GPU)"
