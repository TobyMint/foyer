#!/bin/bash
# Client-side hourly wake-up for the Foyer session (WSL cron, not the lab).
# Injects the inspection prompt into the running Codex session via `codex queue`,
# so the check is done by the model reading the state, not by a shell script.
#
# Install:  0 * * * * /root/paper/foyer/scripts/hourly_check.sh
# Remove:   crontab -l | grep -v hourly_check | crontab -
THREAD="${FOYER_THREAD_ID:-01a0b744-164d-7752-b9ec-61bdfdc74257}"
PROMPT_FILE=/root/paper/foyer/scripts/hourly_check_prompt.txt
LOG=/root/paper/foyer/hourly_check.log
{
  echo "[$(date '+%m-%d %H:%M')] queueing inspection"
  codex queue --thread "$THREAD" --message "$(cat "$PROMPT_FILE")" 2>&1
} >> "$LOG" 2>&1
