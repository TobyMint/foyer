#!/bin/bash
# 第三批：先补 25 档的静态前沿（1 小时），再跑引擎侧步时间实验（4 小时）。
# 只工作卡 2/3，不碰卡 0/1。
set -u
L=/data/xbw/turnstile/scripts/batch3.log
g(){ nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$1"; }
echo "$(date '+%m-%d %H:%M') batch3 启动：等卡 2/3 空" >> $L
while pgrep -f "chain_one\.sh" >/dev/null || pgrep -f "/lane_" >/dev/null; do sleep 60; done
for i in $(seq 1 240); do [ "$(g 2)" -lt 200 ] && [ "$(g 3)" -lt 200 ] && break; sleep 60; done
echo "$(date '+%m-%d %H:%M') 卡 2/3 已空，起 25 档 cap 对照" >> $L
setsid bash /data/xbw/turnstile/scripts/chain_one.sh c25_2 2 pois200_cap2_25 >/dev/null 2>&1 </dev/null &
setsid bash /data/xbw/turnstile/scripts/chain_one.sh c25_3 3 pois200_cap3_25 >/dev/null 2>&1 </dev/null &
wait
echo "$(date '+%m-%d %H:%M') cap2/cap3 完成，起 cap4/foyer25" >> $L
setsid bash /data/xbw/turnstile/scripts/chain_one.sh c25_4 2 pois200_cap4_25      >/dev/null 2>&1 </dev/null &
setsid bash /data/xbw/turnstile/scripts/chain_one.sh f25   3 pois200_foyer_push_25 >/dev/null 2>&1 </dev/null &
sleep 2100
echo "$(date '+%m-%d %H:%M') 25 档四条完成，起引擎批" >> $L
setsid bash /data/xbw/turnstile/scripts/chain_one.sh pf64cap 2 pois200_cap4_hc_pf64  >/dev/null 2>&1 </dev/null &
setsid bash /data/xbw/turnstile/scripts/chain_one.sh pf64foy 3 pois200_foyer_hc_pf64 >/dev/null 2>&1 </dev/null &
echo "$(date '+%m-%d %H:%M') 全部已挂" >> $L
