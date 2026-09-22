#!/bin/bash
# rg3 专用：等 GPU1 真正空出来。
# 为什么不用 chain_one.sh 的门控：那里阈值是 2000 MiB，而邻居占 660 MiB 也会通过——
# 那就等于"算一下剩下的空间够不够"，用户明确禁止这么做。这里阈值 200 MiB，
# 空卡实测 15-18 MiB，所以 200 就等于"完全没人用"。
L=/data/xbw/turnstile/scripts/chain_gpu1.log
echo "$(date '+%m-%d %H:%M') rg3 等 GPU1 真空（阈值 200MiB；有邻居就不跑，不凑合）" >> $L
while :; do
  pre=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 1)
  [ "$pre" -lt 200 ] && break
  echo "$(date '+%m-%d %H:%M')   GPU1 被占 ${pre}MiB（可能是别人的进程），继续等" >> $L
  sleep 120
done
echo "$(date '+%m-%d %H:%M')   GPU1 已空，起 rg3" >> $L
exec bash /data/xbw/turnstile/scripts/chain_one.sh rg3 1 pois200_foyer_rg3
