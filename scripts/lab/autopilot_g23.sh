#!/bin/bash
# autopilot_g23.sh — 等 lab-3090 的 GPU2/3 空且凉，按 worklist 逐卡串行启动 drive_one.sh
#
# 用户 2026-10-23 定规：卡 2/3 空了就直接起实验。本脚本是那条指令的执行器：
# 每 90s 查一次远端状态；某张卡「没有 compute app + 显存 <200MiB + 温度 <TEMP_MAX」
# 且该卡上一条 run 已经写出 summary.json，就启动 worklist 里该卡的下一条。
#
# 安全边界（本项目血泪）：
#   · 只碰卡 2/3；不 kill 任何别人的进程；不用 pkill -f 自匹配。
#   · 单条 run 用 setsid nohup 挂在实验机上，本地断线不影响它（drive_one.sh 自带 trap HUP）。
#   · 每条命令都写在日志里；状态落盘，重启本脚本不会重复起同一条。
#
# 用法:
#   bash scripts/lab/autopilot_g23.sh scripts/lab/autopilot_worklist_20261023.txt
#   bash scripts/lab/autopilot_g23.sh <worklist> --dry-run    # 只看状态，不启动
set -u
WL=${1:-}
[ -z "$WL" ] && { echo "usage: $0 <worklist> [--dry-run]" >&2; exit 2; }
DRY=0; [ "${2:-}" = "--dry-run" ] && DRY=1
HOST=lab-3090
LAB=/data/xbw/turnstile
TEMP_MAX=${TEMP_MAX:-68}
POLL=${POLL:-90}
LOGDIR=/root/paper/foyer/logs/autopilot_20261023
mkdir -p "$LOGDIR"
LOG=$LOGDIR/autopilot.log
STATE=$LOGDIR/state.txt
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

mapfile -t L2 < <(awk -F'|' '$1==2' "$WL")
mapfile -t L3 < <(awk -F'|' '$1==3' "$WL")
N2=${#L2[@]}; N3=${#L3[@]}
IDX2=0; IDX3=0; CUR2=""; CUR3=""; MISS2=0; MISS3=0
log "autopilot start: card2=$N2 runs card3=$N3 runs poll=${POLL}s temp_max=${TEMP_MAX} dry=$DRY"

remote_status() {
  timeout 45 ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" bash -s -- "${CUR2:-none}" "${CUR3:-none}" <<'REMOTE' 2>&1
echo "@@GPU"
nvidia-smi -i 2,3 --query-gpu=index,temperature.gpu,memory.used,utilization.gpu --format=csv,noheader 2>/dev/null
echo "@@APPS"
for g in 2 3; do
  n=$(nvidia-smi -i "$g" --query-compute-apps=pid --format=csv,noheader 2>/dev/null | wc -l)
  echo "APPS $g $n"
done
echo "@@PROCS"
ps -eo pid,args --no-headers | grep -E "replay/target/release/session_runner|run_matrix\.py|drive_one\.sh" \
  | grep -v "bash -c" | grep -v grep | head -12
echo "@@DONE"
for r in "$1" "$2"; do
  [ "$r" = none ] && continue
  [ -f /data/xbw/turnstile/results/night/$r/summary.json ] && echo "DONE $r"
done
REMOTE
}

launch_item() {  # $1 = worklist line
  local line=$1 card run policy trace port hc hcr cmd res
  IFS='|' read -r card run policy trace port hc hcr <<< "$line"
  cmd="cd $LAB && HCR=$hcr TEMP_MAX=$TEMP_MAX setsid nohup bash $LAB/scripts/drive_one.sh '$run' '$policy' $trace $port $hc '$card' >> $LAB/scripts/autopilot_launch.log 2>&1 < /dev/null & echo pid=\$!"
  if [ "$DRY" = 1 ]; then log "DRY launch card$card: $run ($policy, $trace, port=$port, $hc, hcr=$hcr)"; return 0; fi
  res=$(timeout 45 ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" "$cmd" 2>&1)
  log "launch card$card: $run -> ${res:-<no output>}"
}

card_ready() {  # $1 = temp $2 = mem $3 = apps
  [ "${3:-1}" -eq 0 ] && [ "${1:-999}" -lt "$TEMP_MAX" ] && [ "${2:-99999}" -lt 200 ]
}

while :; do
  OUT=$(remote_status) || true
  if ! echo "$OUT" | grep -q '@@GPU'; then
    log "ssh/status failed (retry): $(echo "$OUT" | head -2 | tr '\n' ' ')"
    sleep "$POLL"; continue
  fi
  T2=$(echo "$OUT" | awk -F', *' '/^2,/{print $2}'); M2=$(echo "$OUT" | awk -F', *' '/^2,/{print $3}')
  T3=$(echo "$OUT" | awk -F', *' '/^3,/{print $2}'); M3=$(echo "$OUT" | awk -F', *' '/^3,/{print $3}')
  A2=$(echo "$OUT" | awk '/^APPS 2/{print $3}');      A3=$(echo "$OUT" | awk '/^APPS 3/{print $3}')
  DONE_LIST=$(echo "$OUT" | sed -n '/@@DONE/,$p' | tail -n +2)
  PROCS=$(echo "$OUT" | sed -n '/@@PROCS/,/@@DONE/p' | sed '1d;$d')
  log "poll gpu2 temp=${T2:-?} mem=${M2:-?} apps=${A2:-?} | gpu3 temp=${T3:-?} mem=${M3:-?} apps=${A3:-?} | cur2=${CUR2:-none} cur3=${CUR3:-none}"

  # ---- 卡 2 ----
  if [ -n "$CUR2" ]; then
    if echo "$DONE_LIST" | grep -q "^DONE $CUR2$"; then
      log "done card2: $CUR2"; CUR2=""; MISS2=0
    elif ! echo "$PROCS" | grep -q -- "$CUR2"; then
      MISS2=$((MISS2+1)); [ "$MISS2" -ge 2 ] && { log "⚠ card2 run $CUR2 无进程且无 summary，放弃"; CUR2=""; MISS2=0; }
    else
      MISS2=0
    fi
  fi
  if [ -z "$CUR2" ] && [ "$IDX2" -lt "$N2" ] && card_ready "${T2:-999}" "${M2:-99999}" "${A2:-1}"; then
    if [ -n "$PROCS" ]; then
      log "card2 空闲但远端仍有我们的进程，先不动：$(echo "$PROCS" | head -1)"
    else
      launch_item "${L2[$IDX2]}"
      IFS='|' read -r _ CUR2 _ _ _ _ _ <<< "${L2[$IDX2]}"
      IDX2=$((IDX2+1)); MISS2=0
    fi
  fi

  # ---- 卡 3 ----
  if [ -n "$CUR3" ]; then
    if echo "$DONE_LIST" | grep -q "^DONE $CUR3$"; then
      log "done card3: $CUR3"; CUR3=""; MISS3=0
    elif ! echo "$PROCS" | grep -q -- "$CUR3"; then
      MISS3=$((MISS3+1)); [ "$MISS3" -ge 2 ] && { log "⚠ card3 run $CUR3 无进程且无 summary，放弃"; CUR3=""; MISS3=0; }
    else
      MISS3=0
    fi
  fi
  if [ -z "$CUR3" ] && [ "$IDX3" -lt "$N3" ] && card_ready "${T3:-999}" "${M3:-99999}" "${A3:-1}"; then
    if [ -n "$PROCS" ]; then
      log "card3 空闲但远端仍有我们的进程，先不动：$(echo "$PROCS" | head -1)"
    else
      launch_item "${L3[$IDX3]}"
      IFS='|' read -r _ CUR3 _ _ _ _ _ <<< "${L3[$IDX3]}"
      IDX3=$((IDX3+1)); MISS3=0
    fi
  fi

  { echo "updated $(date '+%F %T')"; echo "card2: cur=${CUR2:-none} next=$IDX2/$N2"; echo "card3: cur=${CUR3:-none} next=$IDX3/$N3"; } > "$STATE"

  if [ "$DRY" = 1 ]; then log "dry-run: 退出"; exit 0; fi
  if [ "$IDX2" -ge "$N2" ] && [ "$IDX3" -ge "$N3" ] && [ -z "$CUR2" ] && [ -z "$CUR3" ]; then
    log "worklist 完成（所有条目已启动且已结束/放弃）"; exit 0
  fi
  sleep "$POLL"
done
