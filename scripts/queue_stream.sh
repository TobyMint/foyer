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
# Read the work list on fd 3, NOT on stdin.
#
# With `done < "$LIST"` the loop body inherits the work list as its stdin, and the
# body launches long-running subprocesses (wait_gpu_then_run_fast.sh and everything
# it spawns). Any of them that reads stdin consumes work-list bytes — and because
# bash's `read` buffers ahead, the file offset already sits PAST the line just
# parsed, so the next `read` resumes in the middle of a line.
#
# Not theoretical. On 2026-09-21 the gpu3 stream finished lane_pois_main and then
# logged "gpu3 waiting -> can" — a word from the comment "...two streams can never
# race...". It spent the next five hours retrying a lane named `can` that does not
# exist, while t90 sat unstarted at the end of the list.
exec 3< "$LIST"
while read -r lane marker _rest <&3; do
  case "${lane:-}" in ""|\#*) continue ;; esac
  if [ -f "$N/$marker/summary.json" ]; then
    log "$lane already done ($marker) — skip"
    continue
  fi
  for attempt in $(seq 1 30); do
    if [ -f "$N/$marker/summary.json" ]; then break; fi
    log "gpu$GPU waiting -> $lane (attempt $attempt)"
    bash "$BASE/scripts/wait_gpu_then_run_fast.sh" "$GPU" "scripts/$lane" \
      < /dev/null >> "$N/stream_gpu${GPU}_${lane%.sh}_attempt${attempt}.log" 2>&1
    if [ -f "$N/$marker/summary.json" ]; then
      log "$lane COMPLETE"
      break
    fi
    log "$lane produced no summary; retry in 10 min"
    sleep 600
  done
done
exec 3<&-
log "work list $LIST drained (gpu$GPU)"
