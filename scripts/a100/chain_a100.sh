#!/bin/bash
# 等当前 A100 车道跑完，若窗口仍然干净就接着跑 a100_cap1。
# 为什么补这一条：预注册判据里列了五个 cap（cap1 92.5% / cap2 89.7% / cap3 79.0% /
# cap4 60.7% / cap5 36.4%），而车道只排了 cap2~cap5 —— 表里会有一行 3090 的 cap1
# 没有 A100 对应点。是审查（中立子 agent）指出来的。
set -u
CUR=3710875
LOG=/data/xbw/a100_chain.log
echo "[$(date +%H:%M:%S)] 等当前车道 (pid $CUR) 结束" >> $LOG
while kill -0 $CUR 2>/dev/null; do sleep 60; done
echo "[$(date +%H:%M:%S)] 当前车道已结束" >> $LOG

# 窗口检查：GPU0 上除了自己人不许有别的进程，且必须有足够空闲显存
FOREIGN=$(nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader 2>/dev/null | wc -l)
FREE=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$1==0{print $2}')
echo "[$(date +%H:%M:%S)] 收尾检查：GPU0 上显存 ${FREE} MiB，计算进程数 ${FOREIGN}" >> $LOG
if [ "${FREE:-99999}" -gt 2000 ]; then
  echo "[$(date +%H:%M:%S)] ⚠ GPU0 上还有 ${FREE} MiB 被占，不启动 —— 人工决定" >> $LOG
  exit 0
fi
if [ -d /data/xbw/turnstile/results/night/a100_cap1 ]; then
  mv /data/xbw/turnstile/results/night/a100_cap1 /data/xbw/turnstile/results/night/a100_cap1.old_$(date +%H%M)
fi
echo "[$(date +%H:%M:%S)] 启动 a100_cap1 车道" >> $LOG
cd /data/xbw/turnstile/scripts && setsid nohup bash ./lane_a100_cap1.sh >> $LOG 2>&1 < /dev/null &
echo "[$(date +%H:%M:%S)] 已启动" >> $LOG
