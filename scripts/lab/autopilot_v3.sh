#!/bin/bash
# autopilot_v3.sh — 任意空卡自动起实验（最多 2 张卡并发）
#
# 用户 2026-10-23 更新：不再限定卡 2/3；**任何空卡都能用**，**最多同时 2 张**。
# 判据：该卡没有 compute app、显存 <200MiB、温度 <TEMP_MAX（默认 68°C）。
# 每个 slot 占一张卡跑一条 run，跑完（summary.json 出现）释放，再取 worklist 下一条。
#
# v3 修复（v2 的坑）：
#  ① 显存单位 "xx MiB" 解析失败 → 改用 nounits；
#  ② trace 相对路径导致 run_matrix FileNotFoundError → drive_one 已支持补全，
#     且这里启动后回读 pid，没拿到 pid 视为失败、不占 slot、自动重排一次；
#  ③ 进程消失/启动失败自动重试一次（PENDING 队列）。
#
# 用法: bash scripts/lab/autopilot_v3.sh <worklist> [--dry-run]
set -u
WL=${1:-}
[ -z "$WL" ] && { echo "usage: $0 <worklist> [--dry-run]" >&2; exit 2; }
DRY=0; [ "${2:-}" = "--dry-run" ] && DRY=1
HOST=${HOST:-lab-3090}
LAB=/data/xbw/turnstile
TEMP_MAX=${TEMP_MAX:-68}
EXPECT_POOL=${EXPECT_POOL:-101502}
POLL=${POLL:-90}
CANDIDATES=${CANDIDATES:-"1 2 3 0"}
LOGDIR=/root/paper/foyer/logs/autopilot_20261023
mkdir -p "$LOGDIR"
LOG=$LOGDIR/autopilot_v3.log
STATE=$LOGDIR/state_v3.txt
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

mapfile -t ITEMS < <(grep -v '^#' "$WL" | grep -vE '^[[:space:]]*$')
N=${#ITEMS[@]}
NEXT=0
declare -a S_RUN=("" "") S_CARD=("" "") S_LINE=("" "") S_MISS=(0 0) PENDING=()
declare -A PREV_READY=()   # 上一轮该卡是否 ready（双确认，减少"刚看空就被抢"的竞争）
LAUNCHED_THIS_POLL=0
declare -A RETRIED=()

log "v3 start: items=$N slots=2 candidates='$CANDIDATES' temp_max=$TEMP_MAX poll=${POLL}s dry=$DRY"

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

launch_item() {  # $1=item line  $2=card ; echoes ok/fail
  local item=$1 card=$2 run policy trace port hc hcr cmd res
  IFS='|' read -r run policy trace port hc hcr <<< "$item"
  cmd="cd $LAB && TURNSTILE_EXPECT_POOL=$EXPECT_POOL HCR=$hcr TEMP_MAX=$TEMP_MAX setsid nohup bash $LAB/scripts/drive_one.sh '$run' '$policy' $trace $port $hc '$card' >> $LAB/scripts/autopilot_launch.log 2>&1 < /dev/null & echo pid=\$!"
  if [ "$DRY" = 1 ]; then log "DRY launch card$card: $run ($policy, $trace, port=$port, $hc, hcr=$hcr)"; echo ok; return; fi
  res=$(timeout 45 ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" "$cmd" 2>&1)
  log "launch card$card: $run -> ${res:-<no output>}"
  if echo "$res" | grep -q 'pid='; then echo ok; else echo fail; fi
}

take_item() {
  ITEM=""
  if [ "${#PENDING[@]}" -gt 0 ]; then
    ITEM="${PENDING[0]}"; PENDING=("${PENDING[@]:1}")
  elif [ "$NEXT" -lt "$N" ]; then
    ITEM="${ITEMS[$NEXT]}"; NEXT=$((NEXT+1))
  fi
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
  LAUNCHED_THIS_POLL=0
  gsum=""
  for c in 0 1 2 3; do gsum="$gsum gpu$c=${GT[$c]:-?}C/${GM[$c]:-?}MiB/${GA[$c]:-?}app"; done
  log "poll $gsum | s0=${S_RUN[0]:-none}@${S_CARD[0]:-?} s1=${S_RUN[1]:-none}@${S_CARD[1]:-?} next=$NEXT/$N pending=${#PENDING[@]}"

  for i in 0 1; do
    [ -z "${S_RUN[$i]}" ] && continue
    if echo "$DONE_LIST" | grep -qx "DONE ${S_RUN[$i]}"; then
      log "slot$i done: ${S_RUN[$i]} (card${S_CARD[$i]})"
      S_RUN[$i]=""; S_CARD[$i]=""; S_LINE[$i]=""; S_MISS[$i]=0
    elif echo "$PROCS" | grep -q -- "${S_RUN[$i]}"; then
      S_MISS[$i]=0
    else
      S_MISS[$i]=$((S_MISS[$i]+1))
      if [ "${S_MISS[$i]}" -ge 2 ]; then
        lr="${S_RUN[$i]}"
        if [ -z "${RETRIED[$lr]:-}" ]; then
          RETRIED[$lr]=1; PENDING+=("${S_LINE[$i]}")
          log "⚠ slot$i 丢失：$lr（无进程/无 summary），排队重试一次"
        else
          log "⚠ slot$i 丢失：$lr，重试过仍失败，跳过"
        fi
        S_RUN[$i]=""; S_CARD[$i]=""; S_LINE[$i]=""; S_MISS[$i]=0
      fi
    fi
  done

  for i in 0 1; do
    [ -n "${S_RUN[$i]}" ] && continue
    if [ "$NEXT" -ge "$N" ] && [ "${#PENDING[@]}" -eq 0 ]; then break; fi
    take_item
    [ -z "${ITEM:-}" ] && break
    IFS='|' read -r run policy trace port hc hcr <<< "$ITEM"
    picked=""
    for c in $CANDIDATES; do
      [ "${S_CARD[0]:-}" = "$c" ] && continue
      [ "${S_CARD[1]:-}" = "$c" ] && continue
      [ "${GA[$c]:-1}" -eq 0 ] || continue
      [ "${GM[$c]:-99999}" -lt 200 ] || continue
      [ "${GT[$c]:-999}" -lt "$TEMP_MAX" ] || continue
      [ "${PREV_READY[$c]:-0}" = "1" ] || continue   # 双确认：上一轮也空
      picked=$c; break
    done
    if [ -z "$picked" ]; then
      PENDING=("$ITEM" "${PENDING[@]}"); log "slot$i 待启动 $run：暂无空卡（或空卡未双确认）"; break
    fi
    if [ "$LAUNCHED_THIS_POLL" -ge 1 ]; then
      PENDING=("$ITEM" "${PENDING[@]}"); log "slot$i 待启动 $run：本轮已启动过一条，下一轮再起"; break
    fi
    if [ "$(launch_item "$ITEM" "$picked")" = "ok" ]; then
      S_RUN[$i]=$run; S_CARD[$i]=$picked; S_LINE[$i]="$ITEM"; S_MISS[$i]=0; LAUNCHED_THIS_POLL=1
    else
      if [ -z "${RETRIED[$run]:-}" ]; then RETRIED[$run]=1; PENDING+=("$ITEM"); log "launch 失败，排队重试：$run"; else log "launch 失败且已重试过，跳过：$run"; fi
    fi
  done

  # 记录本轮各卡 ready，供下一轮双确认
  for c in 0 1 2 3; do
    if [ "${GA[$c]:-1}" -eq 0 ] && [ "${GM[$c]:-99999}" -lt 200 ] && [ "${GT[$c]:-999}" -lt "$TEMP_MAX" ]; then
      PREV_READY[$c]=1
    else
      PREV_READY[$c]=0
    fi
  done

  {
    echo "updated $(date '+%F %T')"
    echo "slot0: run=${S_RUN[0]:-none} card=${S_CARD[0]:-?}"
    echo "slot1: run=${S_RUN[1]:-none} card=${S_CARD[1]:-?}"
    echo "next: $NEXT/$N pending=${#PENDING[@]}"
  } > "$STATE"

  if [ "$DRY" = 1 ]; then log "dry-run: 退出"; exit 0; fi
  if [ "$NEXT" -ge "$N" ] && [ "${#PENDING[@]}" -eq 0 ] && [ -z "${S_RUN[0]}" ] && [ -z "${S_RUN[1]}" ]; then
    log "worklist 完成"; exit 0
  fi
  sleep "$POLL"
done
