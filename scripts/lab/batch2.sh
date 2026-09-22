#!/bin/bash
# 第二批：round-gate 扫描（政策侧主押注）+ 无闸对照。
# 先等第一批所有进程退出——否则两条 chain 会同时通过门控抢同一张卡。
set -u
L=/data/xbw/turnstile/scripts/batch2.log
echo "$(date '+%m-%d %H:%M') 等第一批结束（round-gate 扫描已就位）" >> $L
while pgrep -f "chain_gpu3\.sh" >/dev/null \
   || pgrep -f "chain_one\.sh" >/dev/null \
   || pgrep -f "/lane_" >/dev/null; do
  sleep 60
done
echo "$(date '+%m-%d %H:%M') 第一批结束，起第二批" >> $L
nohup bash /data/xbw/turnstile/scripts/chain_one.sh rg2    0 pois200_foyer_rg2    >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh rg3    1 pois200_foyer_rg3    >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh rg4    2 pois200_foyer_rg4    >/dev/null 2>&1 &
nohup bash /data/xbw/turnstile/scripts/chain_one.sh nogate 3 pois200_foyer_nogate >/dev/null 2>&1 &
echo "$(date '+%m-%d %H:%M') 第二批已挂: rg2/rg3/rg4/nogate" >> $L
