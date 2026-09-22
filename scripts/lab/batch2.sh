#!/bin/bash
# 第二批（引擎侧）的串行器。
#
# 为什么需要它：chain_one.sh 是"等空卡→跑一条"，如果第一批的 chain 还在
# （特别是它失败后进入 sleep 60 重试的窗口），第二批的 chain 会同时通过门控，
# 两条 run_matrix 抢同一张卡同一个端口。所以这里先等第一批【所有】进程退出。
#
# 第一批：gpu0=bres gpu1=hz0 gpu2=breshz1（chain_one）gpu3=hz2（chain_gpu3.sh）
set -u
L=/data/xbw/turnstile/scripts/batch2.log
echo "$(date '+%m-%d %H:%M') 等第一批结束" >> $L
while pgrep -f "chain_gpu3\.sh" >/dev/null \
   || pgrep -f "chain_one\.sh" >/dev/null \
   || pgrep -f "/lane_" >/dev/null; do
  sleep 60
done
echo "$(date '+%m-%d %H:%M') 第一批结束，起第二批" >> $L
nohup bash /data/xbw/turnstile/scripts/chain_one.sh cap4pf   0 pois200_cap4_hc_pf64  >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh cap3pf   1 pois200_cap3_hc_pf64  >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh foyerpf  2 pois200_foyer_hc_pf64 >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh cap4slru 3 pois200_cap4_hc_slru  >/dev/null 2>&1 &
echo "$(date '+%m-%d %H:%M') 第二批已挂" >> $L
