#!/bin/bash
# Client-side hourly wake-up for the Foyer session (WSL cron, not the lab).
# Injects the inspection prompt into the running Codex session via `codex queue`,
# so the check is done by the model reading the state, not by a shell script.
#
# Install:  0 * * * * /root/paper/foyer/scripts/hourly_check.sh
# Remove:   crontab -l | grep -v hourly_check | crontab -
# Dedupe: never queue a second inspection within MIN_GAP seconds (default 45 min), so
# a manual test, a duplicated cron entry, or a burst can't produce back-to-back checks.
MIN_GAP=${MIN_GAP:-2700}
DRY_RUN=${DRY_RUN:-0}
# cron runs with a minimal PATH: resolve codex explicitly instead of relying on nvm shims.
CODEX_BIN="${CODEX_BIN:-$(command -v codex || echo /root/.nvm/versions/node/v24.17.0/bin/codex)}"
export PATH="$(dirname "$CODEX_BIN"):$PATH"
THREAD="${FOYER_THREAD_ID:-01a0b744-164d-7752-b9ec-61bdfdc74257}"
PROMPT_FILE=/root/paper/foyer/scripts/hourly_check_prompt.txt
LOG=/root/paper/foyer/hourly_check.log
STAMP=/root/paper/foyer/.last_hourly_check
{
  if [ -f "$STAMP" ]; then
    age=$(( $(date +%s) - $(stat -c %Y "$STAMP") ))
    if [ "$age" -lt "$MIN_GAP" ]; then
      echo "[$(date '+%m-%d %H:%M')] skip: last inspection ${age}s ago (< ${MIN_GAP}s)"
      [ "$DRY_RUN" = "1" ] || touch "$STAMP"
      exit 0
    fi
  fi
  echo "[$(date '+%m-%d %H:%M')] queueing inspection"
  if [ "$DRY_RUN" = "1" ]; then
    echo "  (dry run: would queue to $THREAD)"
    exit 0
  fi
  touch "$STAMP"
  "$CODEX_BIN" queue --thread "$THREAD" --message "$(cat "$PROMPT_FILE")" 2>&1
} >> "$LOG" 2>&1
