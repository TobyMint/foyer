#!/bin/bash
# Hourly status snapshot for the Foyer queue. Appends one compact block to
# results/night/status_snapshots.log so there is an independent record of whether the
# queue was actually running — independent of any agent being awake.
#
# Install:  0 * * * * /data/xbw/turnstile/scripts/status_snapshot.sh >/dev/null 2>&1
N=/data/xbw/turnstile/results/night
LOG=$N/status_snapshots.log

stream() {  # alive?
  if pgrep -f "queue_stream.sh $1 " > /dev/null; then echo -n "alive"; else echo -n "DEAD"; fi
}

{
  echo "=== $(date '+%m-%d %H:%M') ==="
  echo "streams: gpu2=$(stream 2) gpu3=$(stream 3)"
  echo -n "gpu: "
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits \
    | tr '\n' ' ' | sed 's/  */ /g'
  echo
  # the two runs being written most recently = what is running now
  for f in $(ls -t $N/*/steps.jsonl 2>/dev/null | head -2); do
    d=$(dirname "$f"); r=$(basename "$d")
    if [ -f "$d/summary.json" ]; then
      echo "  $r: DONE"
    else
      echo "  $r: $(tail -1 "$d/runner.out" 2>/dev/null | cut -c1-90)"
    fi
  done
  echo -n "  completed runs: "; ls $N/*/summary.json 2>/dev/null | wc -l
  # last few watchdog/queue events, so restarts are visible in the record
  tail -2 $N/watchdog.log 2>/dev/null | sed 's/^/  wd: /'
} >> "$LOG"
