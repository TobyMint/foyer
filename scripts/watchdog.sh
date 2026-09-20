#!/bin/bash
# Cron entry point (every 5 minutes). This box has a periodic process-reaper: on
# 09-19 it killed both queue drivers and the whole queue stopped silently, because
# nothing restarted them. The watchdog only starts a stream that is not running, so
# it is safe to run as often as you like.
#
# Install:  */5 * * * * /data/xbw/turnstile/scripts/watchdog.sh >/dev/null 2>&1
BASE=/data/xbw/turnstile
N=$BASE/results/night
LOCK=$N/.watchdog.lock
exec 9>"$LOCK" || exit 1
flock -n 9 || exit 0
cd "$BASE" || exit 1
# gpu0/gpu1 joined on 2026-09-21 for the Foyer guardrail arms: they had been idle
# (15-18 MiB, no compute processes) for over an hour, and the box's other tenants
# only ever touch cards 2 and 3. A stream is only started when one is NOT already
# running, so listing a card here costs nothing while it is busy.
for pair in "0:worklist_gpu0.txt" "1:worklist_gpu1.txt" "2:worklist_gpu2.txt" "3:worklist_gpu3.txt"; do
  gpu=${pair%%:*}
  list=${pair#*:}
  marker="$N/.drained.$list"
  if [ -f "$marker" ] && [ "$(cat "$marker" 2>/dev/null)" = "$(wc -l < "$BASE/scripts/$list" 2>/dev/null)" ]; then
    continue
  fi
  # ANCHOR the pattern, and match BOTH spellings (relative and absolute path). An unanchored `pgrep -f "queue_stream.sh $gpu "` also
  # matches any stale `bash -c` wrapper whose command line merely MENTIONS that
  # string — and this box is full of them, because whoever launched a stream did
  # it through a compound shell command that stays in the process table. With the
  # unanchored pattern the watchdog concluded "stream already running" every time
  # and never restarted anything: watchdog.log was empty for the project's entire
  # history, so the self-healing was imaginary.
  if pgrep -f "^bash [^ ]*queue_stream\.sh ${gpu} " > /dev/null; then
    continue
  fi
  echo "[$(date '+%m-%d %H:%M')] watchdog: stream gpu$gpu not running — starting $list" >> "$N/watchdog.log"
  # 9>&- is load-bearing: without it the child INHERITS the flock fd, keeps it open
  # for its whole life (and passes it to every descendant — run_matrix, the server,
  # the runner), and the lock is never released. The watchdog then fails `flock -n 9`
  # on every subsequent invocation and exits silently: it can start each stream
  # exactly once and is disabled from then on. Observed 2026-09-21 — the lock was
  # held by a queue_stream.sh that had been started six hours earlier.
  setsid nohup bash "$BASE/scripts/queue_stream.sh" "$gpu" "$BASE/scripts/$list" \
    >> "$N/watchdog.log" 2>&1 < /dev/null 9>&- &
  sleep 2
done
