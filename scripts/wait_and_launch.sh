#!/bin/bash
# wait_and_launch.sh <gpu> <lane_script> <marker_run> [max_my_servers]
#
# 等【前一条车道的最后一个 run 写完 summary】再启动下一条车道，启动前再核一遍
# 目标卡是空的、且全局并发不超标。
#
# 为什么用 marker run 而不是"显存空"判定：run_matrix 在一条车道的两条 run 之间会
# 卸载 server，那一刻显存是空的但车道并没结束。只看显存会让新车道抢进同一张卡。
#
# 为什么启动前要数自己的 server：2026-09-24 查明，同机 >=3 台 SGLang server 会把
# τ₂（逐请求 decode 间隔）抬高 25~40%，该段数据作废（见 lane_foyer_r2_batch1.sh）。
# 所以并发必须硬卡在 2 条车道。
set -u
GPU=$1; LANE=$2; MARKER=$3; MAXMINE=${4:-1}
N=/data/xbw/turnstile/results/night
LOG=/tmp/wait_gpu${GPU}_$(basename "$LANE" .sh).log
echo "[$(date '+%F %T')] 等待 marker: $N/$MARKER/summary.json" >> "$LOG"
for i in $(seq 1 1440); do
  if [ -f "$N/$MARKER/summary.json" ]; then
    MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$GPU" 2>/dev/null || echo 99999)
    # 数的是 launch_server 主进程，不是 'sglang::scheduler'：
    #   (a) pgrep -f 'sglang::scheduler' 会把"命令行里含这串"的别的进程一起数进来
    #       （2026-09-24 实测：ssh 过去那条命令自己被算了，计数虚高 1）；
    #   (b) 加 ^...$ 锚点又匹配不上——setproctitle 会在进程名后补空格。
    # 'sglang\.launch_server' 是 server 主进程的 argv，且不会出现在本脚本命令行里。
    MINE=$(pgrep -u "$(id -u)" -f 'sglang\.launch_server' 2>/dev/null | wc -l)
    if [ "$MEM" -lt 2000 ] && [ "$MINE" -le "$MAXMINE" ]; then
      echo "[$(date '+%F %T')] marker 就绪；gpu$GPU mem=${MEM}MiB 我的server=${MINE} -> 启动 $LANE" >> "$LOG"
      nohup bash "$LANE" >> "${LOG%.log}.out" 2>&1 &
      echo "[$(date '+%F %T')] 已启动 pid=$!" >> "$LOG"
      exit 0
    fi
    [ $((i % 5)) -eq 0 ] && echo "[$(date '+%F %T')] marker 已就绪，仍在等卡：gpu$GPU mem=${MEM}MiB 我的server=${MINE}" >> "$LOG"
  else
    [ $((i % 15)) -eq 0 ] && echo "[$(date '+%F %T')] 等 marker 中（第 ${i} 次）" >> "$LOG"
  fi
  sleep 60
done
echo "[$(date '+%F %T')] 超时未启动" >> "$LOG"
exit 1
