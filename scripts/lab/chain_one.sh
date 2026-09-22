#!/bin/bash
# chain_one.sh <step> <gpu> <run>
# 单条 lane 的看门链：等空卡 → 二次确认 → stale 守卫 → 跑 → 失败重试（最多 6 次）。
# 与 chain_gpu{2,3}.sh 同一套门控，只是把 gpu/run 参数化，好在 gpu0/1/2 上各起一条。
#
# 门控是硬门：memory.used < 200 MiB 且 90 秒后仍然 < 200，才允许起 server。
#
# 阈值原先是 2000，2026-09-23 改成 200，因为 2000 有洞：邻居进程占 660 MiB 也会通过。
# 那就等于"算一下剩下的空间够不够"——用户明确禁止这么做（"有别人占用卡的话，就别想跑了，
# 这时候要做的就是 wait"）。空卡实测 15-18 MiB，所以 200 就等于"完全没人用"。
set -u
step=$1; gpu=$2; run=$3
R=/data/xbw/turnstile/results/night
L=/data/xbw/turnstile/scripts/chain_gpu${gpu}.log
for attempt in 1 2 3 4 5 6; do
  while :; do
    pre=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$gpu")
    [ "$pre" -lt 200 ] && break
    echo "$(date '+%m-%d %H:%M')   gpu${gpu} 被占 ${pre}MiB，等空卡" >> $L
    sleep 120
  done
  sleep 90
  pre2=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$gpu")
  if [ "$pre2" -ge 200 ]; then
    echo "$(date '+%m-%d %H:%M')   gpu${gpu} 又被占（${pre2}MiB），继续等" >> $L; continue
  fi
  # stale 守卫：同名旧目录没有 summary.json 就先挪走。
  # run_matrix 用 makedirs(exist_ok=True)，追加式的 admissions/controller 日志会
  # 把上一次 run 的记录混进来且不报错（2026-09-22 踩过，白跑一天）。
  if [ -d "$R/$run" ] && [ ! -f "$R/$run/summary.json" ]; then
    mv "$R/$run" "$R/_stale_$(date +%Y%m%d%H%M)_$run"
    echo "$(date '+%m-%d %H:%M')   挪走 stale 目录 $run" >> $L
  fi
  echo "$(date '+%m-%d %H:%M') -> lane_$step  第${attempt}次 (gpu${gpu} 空 ${pre2}MiB)" >> $L
  if bash /data/xbw/turnstile/scripts/lane_$step.sh >> $L 2>&1; then
    echo "$(date '+%m-%d %H:%M')    lane_$step OK" >> $L; exit 0
  else
    echo "$(date '+%m-%d %H:%M')    lane_$step 失败，重试" >> $L; sleep 60
  fi
done
echo "$(date '+%m-%d %H:%M') lane_$step 六次全失败，放弃" >> $L
exit 1
