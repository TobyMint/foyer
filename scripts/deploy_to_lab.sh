#!/bin/bash
# Deploy one or more files to the lab ATOMICALLY.
#
# Why this exists (2026-09-21): a plain `scp file lab:path` overwrites the
# destination IN PLACE, and bash reads a script incrementally rather than loading
# it. Two queue streams were executing scripts/queue_stream.sh when it was
# overwritten; their read offsets then landed inside the new file's comment block
# and bash executed the fragments as commands ("named: command not found",
# "can: command not found" in watchdog.log). Harmless that time, but the same
# mechanism can silently splice half an old line onto half a new one inside a
# loop body.
#
# Writing to a sibling temp file and renaming within the same directory keeps the
# replacement atomic: mv on one filesystem is rename(2), so a running process
# keeps reading the OLD inode and never sees a torn file. (Copying a temp file
# from /tmp would NOT be safe — that is a cross-device copy, which truncates the
# destination in place and reproduces the original bug.)
#
# The same rule applies to work lists: queue_stream.sh reads them lazily, so
# APPENDING a line is safe while rewriting one is not.
#
# Usage:  deploy_to_lab.sh <local_file>[:<remote_dir>] ...
#         deploy_to_lab.sh scripts/foo.py scripts/bar.sh:TraceLab/replay/scripts
set -euo pipefail
BASE=/data/xbw/turnstile
HOST=${LAB_HOST:-lab-3090}

[ $# -ge 1 ] || { sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

for spec in "$@"; do
  src=${spec%%:*}
  if [ "$spec" = "$src" ]; then
    dir=$BASE/scripts
  else
    dir=$BASE/${spec#*:}
  fi
  [ -f "$src" ] || { echo "缺失: $src" >&2; exit 1; }
  base=$(basename "$src")
  # scp to a SIBLING temp name, then rename inside the destination directory
  scp -q "$src" "$HOST:$dir/.$base.new"
  ssh -o BatchMode=yes "$HOST" "mv -f '$dir/.$base.new' '$dir/$base'"
  printf '  部署 %-24s -> %s\n' "$base" "$dir"
done
