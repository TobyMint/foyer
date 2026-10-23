#!/bin/bash
# autopilot_v2.sh — 任意空卡自动起实验（最多 2 张卡并发）
#
# 用户 2026-10-23 更新：不再限定卡 2/3；**任何空卡都能用**，**最多同时 2 张**。
# 判据：该卡没有 compute app、显存 <200MiB、温度 <TEMP_MAX（默认 68°C）。
# 每个 slot 占一张卡跑一条 run，跑完（summary.json 出现）释放，再取 worklist 下一条。
#
# 用法:
#   bash scripts/lab/autopilot_v2.sh <worklist> [--dry-run]
set -u
WL=${1:-}
[ -z "$WL" ] && { echo "usage: $0 <worklist> [--dry-run]" >&2; exit 2; }
DRY=0; [ "${2:-}" = "--dry-run" ] && DRY=1
HOST=${HOST:-lab-3090}
LAB=/data/xbw/turnstile
TEMP_MAX=${TEMP_MAX:-68}
POLL=${POLL:-90}
CANDIDATES=${CANDIDATES:-"1 2 3 0"}
LOGDIR=/root/paper/foyer/logs/autopilot_20261023
mkdir -p "$LOGDIR"
LOG=$LOGDIR/autopilot_v2.log
STATE=$LOGDIR/state_v2.txt
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

mapfile -t ITEMS < <(grep -v '^#' "$WL" | grep -vE '^[[:space:]]*$')
N=${#ITEMS[@]}
NEXT=0
declare -a S_RUN=("" "") S_CARD=("" "") S_MISS=(0 0)

log "v2 start: items=$N slots=2 candidates='$CANDIDATES' temp_max=$TEMP_MAX poll=${POLL}s dry=$DRY"

remote_status() {
  timeout 45 ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" bash -s -- "${S_RUN[0]:-none}" "${S_RUN[1]:-none}" <<'REMOTE' 2>&1
echo "@@GPU"
nvidia-smi --query-gpu=index,temperature.gpu,memory.used,utilization.gpu --format=csv,noheader,nounits 2>/dev/null
echo "@@APPS"
for g in 0 1 2 3; do
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

launch_item() {  # $1=item line  $2=card
  local item=$1 card=$2 run policy trace port hc hcr cmd res
  IFS='|' read -r run policy trace port hc hcr <<< "$item"
  cmd="cd $LAB && HCR=$hcr TEMP_MAX=$TEMP_MAX setsid nohup bash $LAB/scripts/drive_one.sh '$run' '$policy' $trace $port $hc '$card' >> $LAB/scripts/autopilot_launch.log 2>&1 < /dev/null & echo pid=\$!"
  if [ "$DRY" = 1 ]; then log "DRY launch card$card: $run ($policy, $trace, port=$port, $hc, hcr=$hcr)"; return 0; fi
  res=$(timeout 45 ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" "$cmd" 2>&1)
  log "launch card$card: $run -> ${res:-<no output>}"
}

while :; do
  OUT=$(remote_status) || true
  if ! echo "$OUT" | grep -q '@@GPU'; then
    log "ssh/status failed: $(echo "$OUT" | head -1)"; sleep "$POLL"; continue
  fi
  declare -A GT GM GA 2>/dev/null || true
  GT=(); GM=(); GA=()
  while IFS=',' read -r idx t m u; do
    idx=${idx// /}; t=${t// /}; m=${m// /}
    [ -n "$idx" ] && GT[$idx]=$t && GM[$idx]=$m
  done < <(echo "$OUT" | sed -n '/@@GPU/,/@@APPS/p' | grep -E '^[0-9]')
  while read -r tag g n; do
    [ "$tag" = APPS ] && GA[$g]=$n
  done < <(echo "$OUT" | sed -n '/@@APPS/,/@@PROCS/p' | grep '^APPS')
  DONE_LIST=$(echo "$OUT" | sed -n '/@@DONE/,$p' | tail -n +2)
  PROCS=$(echo "$OUT" | sed -n '/@@PROCS/,/@@DONE/p' | sed '1d;$d')
  gsum=""
  for c in 0 1 2 3; do gsum="$gsum gpu$c=${GT[$c]:-?}C/${GM[$c]:-?}MiB/${GA[$c]:-?}app"; done
  log "poll $gsum | slot0=${S_RUN[0]:-none}@${S_CARD[0]:-?} slot1=${S_RUN[1]:-none}@${S_CARD[1]:-?} next=$NEXT/$N"

  # 1) 结算 slot
  for i in 0 1; do
    [ -z "${S_RUN[$i]}" ] && continue
    if echo "$DONE_LIST" | grep -qx "DONE ${S_RUN[$i]}"; then
      log "slot$i done: ${S_RUN[$i]} (card${S_CARD[$i]})"
      S_RUN[$i]=""; S_CARD[$i]=""; S_MISS[$i]=0
    elif echo "$PROCS" | grep -q -- "${S_RUN[$i]}"; then
      S_MISS[$i]=0
    else
      S_MISS[$i]=$((S_MISS[$i]+1))
      if [ "${S_MISS[$i]}" -ge 2 ]; then
        log "⚠ slot$i 丢失：${S_RUN[$i]} 无进程且无 summary，放弃（card${S_CARD[$i]}）"
        S_RUN[$i]=""; S_CARD[$i]=""; S_MISS[$i]=0
      fi
    fi
  done

  # 2) 填充空 slot
  for i in 0 1; do
    [ -n "${S_RUN[$i]}" ] && continue
    [ "$NEXT" -ge "$N" ] && break
    item="${ITEMS[$NEXT]}"
    IFS='|' read -r run policy trace port hc hcr <<< "$item"
    picked=""
    for c in $CANDIDATES; do
      [ "${S_CARD[0]:-}" = "$c" ] && continue
      [ "${S_CARD[1]:-}" = "$c" ] && continue
      [ "${GA[$c]:-1}" -eq 0 ] || continue
      [ "${GM[$c]:-99999}" -lt 200 ] || continue
      [ "${GT[$c]:-999}" -lt "$TEMP_MAX" ] || continue
      picked=$c; break
    done
    if [ -z "$picked" ]; then
      log "slot$i 待启动 $run：暂无空卡（排除已被另一 slot 占的卡）"
      continue
    fi
    launch_item "$item" "$picked"
    if [ "$DRY" = 1 ]; then
      S_RUN[$i]=$run; S_CARD[$i]=$picked; NEXT=$((NEXT+1))
    else
      S_RUN[$i]=$run; S_CARD[$i]=$picked; S_MISS[$i]=0; NEXT=$((NEXT+1))
    fi
  done

  {
    echo "updated $(date '+%F %T')"
    echo "slot0: run=${S_RUN[0]:-none} card=${S_CARD[0]:-?}"
    echo "slot1: run=${S_RUN[1]:-none} card=${S_CARD[1]:-?}"
    echo "next: $NEXT/$N"
  } > "$STATE"

  if [ "$DRY" = 1 ]; then log "dry-run: 退出"; exit 0; fi
  if [ "$NEXT" -ge "$N" ] && [ -z "${S_RUN[0]}" ] && [ -z "${S_RUN[1]}" ]; then
    log "worklist 完成"; exit 0
  fi
  sleep "$POLL"
done
