#!/bin/bash
# 第三批：先补 25 档的静态前沿（每条约 30 分钟），再跑引擎侧步时间实验（约 4 小时）。
# 只工作卡 2/3，不碰卡 0/1。
#
# 时序用【显式轮询】而不是 wait：setsid 会 fork，wait 追踪不到那些子进程会立刻返回，
# 导致四条同时挂上抢同一张卡。轮询判据是"目标 run 的 summary.json 出现"。
set -u
L=/data/xbw/turnstile/scripts/batch3.log
N=/data/xbw/turnstile/results/night
g(){ nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$1"; }
done_run(){ [ -f "$N/pois200_$1/summary.json" ]; }
launch(){ setsid bash /data/xbw/turnstile/scripts/chain_one.sh "$1" "$2" "$3" >/dev/null 2>&1 </dev/null & }

echo "$(date '+%m-%d %H:%M') batch3 启动：等卡 2/3 空" >> $L
while pgrep -f "chain_one\.sh" >/dev/null || pgrep -f "/lane_" >/dev/null; do sleep 60; done
for i in $(seq 1 240); do [ "$(g 2)" -lt 200 ] && [ "$(g 3)" -lt 200 ] && break; sleep 60; done

echo "$(date '+%m-%d %H:%M') 起 25 档 cap2/cap3" >> $L
launch c25_2 2 pois200_cap2_25
launch c25_3 3 pois200_cap3_25
for i in $(seq 1 120); do { done_run cap2_25 && done_run cap3_25; } && break; sleep 60; done

echo "$(date '+%m-%d %H:%M') cap2/cap3 完成，起 cap4/foyer25" >> $L
launch c25_4 2 pois200_cap4_25
launch f25   3 pois200_foyer_push_25
for i in $(seq 1 120); do { done_run cap4_25 && done_run foyer_push_25; } && break; sleep 60; done

echo "$(date '+%m-%d %H:%M') 25 档四条完成，起引擎批" >> $L
launch pf64cap 2 pois200_cap4_hc_pf64
launch pf64foy 3 pois200_foyer_hc_pf64
echo "$(date '+%m-%d %H:%M') 全部已挂" >> $L
