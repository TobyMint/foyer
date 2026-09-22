#!/bin/bash
# 一条命令跑一次快速实验，跑完自动汇总。
#
#   quick.sh <短名> <策略串> [GPU]
#   quick.sh warm2  "budget3:hw=0;target=0.95"       # 用空闲的卡
#   quick.sh warm2  "budget3:hw=0;target=0.95" 3     # 指定 gpu3
#
# 默认跑短 trace（replay_pois200_l04_r2.csv，约 100 分钟；全程要 290 分钟）。
# 要跑全程：QUICK_TRACE=full quick.sh ...
#
# 这个脚本把今天踩过的坑都封进去了：
#   - 端口按 GPU 固定（run_matrix 的清理是按端口的，固定端口才能清掉前一条的残留 server）
#   - 开跑前挪走同名旧目录（run_matrix 用 makedirs(exist_ok=True)，不清目录，
#     追加式日志会把上一次 run 的记录混进来且不报错）
#   - 跑完自动调 run_summary.py 出汇总
set -e
NAME="$1"; POLICY="$2"; GPU="$3"
if [ -z "$NAME" ] || [ -z "$POLICY" ]; then sed -n "2,14p" "$0"; exit 2; fi

B=/data/xbw/turnstile
RUN=pois200_quick_${NAME}

if [ -z "$GPU" ]; then
  for g in 2 3; do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $g)
    [ "$used" -lt 3000 ] && { GPU=$g; break; }
  done
fi
[ -z "$GPU" ] && { echo "两张卡都占着，等一会儿，或者手动给 GPU: quick.sh $NAME '$POLICY' <2|3>"; exit 1; }

if [ "${QUICK_TRACE:-short}" = "full" ]; then
  TRACE=$B/data/replay_pois200_l04.csv;  MINS=~300
else
  TRACE=$B/data/replay_pois200_l04_r2.csv; MINS=~100
fi
PORT=$(( GPU == 2 ? 30052 : 30053 ))

# 同名旧目录挪走
D=$B/results/night/$RUN
if [ -d "$D" ] && [ ! -f "$D/summary.json" ]; then
  mv "$D" "$B/results/night/_stale_$(date +%Y%m%d%H%M)_$RUN"
  echo "挪走同名旧目录 -> _stale_$(date +%Y%m%d%H%M)_$RUN"
fi

echo "=== quick: $RUN ==="
echo "  gpu=$GPU  port=$PORT  trace=$(basename $TRACE)  预计 $MINS 分钟"
echo "  policy=$POLICY"
echo "  日志: $B/scripts/quick_${NAME}.log"
echo

export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=$TRACE
P=$B/envs/main/bin/python

$P $B/TraceLab/replay/scripts/run_matrix.py --lane quick_$NAME --gpu $GPU --port $PORT \
   --runs "${RUN}:${POLICY}" > $B/scripts/quick_${NAME}.log 2>&1 || true

echo
echo "=== 汇总 ==="
$P $B/scripts/run_summary.py $RUN
