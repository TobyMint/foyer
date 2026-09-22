#!/bin/bash
# 第二批：足迹上限扫描（政策侧，主押注）+ 一个引擎侧对照。
# 先等第一批所有进程退出——否则两条 chain 会同时通过门控抢同一张卡。
set -u
L=/data/xbw/turnstile/scripts/batch2.log
echo "$(date '+%m-%d %H:%M') 等第一批结束（足迹扫描已就位）" >> $L
while pgrep -f "chain_gpu3\.sh" >/dev/null \
   || pgrep -f "chain_one\.sh" >/dev/null \
   || pgrep -f "/lane_" >/dev/null; do
  sleep 60
done
echo "$(date '+%m-%d %H:%M') 第一批结束，起第二批" >> $L
nohup bash /data/xbw/turnstile/scripts/chain_one.sh fp70    0 pois200_foyer_fp70     >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh fp80    1 pois200_foyer_fp80     >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh fp90    2 pois200_foyer_fp90     >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh cap4pf  3 pois200_cap4_hc_pf64   >/dev/null 2>&1 &
echo "$(date '+%m-%d %H:%M') 第二批已挂: fp70/fp80/fp90 + cap4pf" >> $L
