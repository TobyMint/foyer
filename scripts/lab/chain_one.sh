#!/bin/bash
# chain_one.sh <step> <gpu> <run>
# 单条 lane 的看门链：等空卡 → 二次确认 → stale 守卫 → 跑 → 失败重试（最多 6 次）。
# 与 chain_gpu{2,3}.sh 同一套门控，只是把 gpu/run 参数化，好在 gpu0/1/2 上各起一条。
#
# 门控是硬门：memory.used < 2000 MiB 且 90 秒后仍然 < 2000，才允许起 server。
# 不"算一下空间够不够"——别人的租户占一点就会让 KV 池算成 6 万而不是 10 万，
# 那种 run 会被池子守卫拒绝，白跑。
set -u
step=$1; gpu=$2; run=$3
R=/data/xbw/turnstile/results/night
L=/data/xbw/turnstile/scripts/chain_gpu${gpu}.log
for attempt in 1 2 3 4 5 6; do
  while :; do
    pre=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$gpu")
    [ "$pre" -lt 2000 ] && break
    echo "$(date '+%m-%d %H:%M')   gpu${gpu} 被占 ${pre}MiB，等空卡" >> $L
    sleep 120
  done
  sleep 90
  pre2=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$gpu")
  if [ "$pre2" -ge 2000 ]; then
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
