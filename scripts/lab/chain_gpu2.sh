#!/bin/bash
# gpu2 整夜队列。端口固定 30042：start_server 的清理是按端口做的，
# 固定端口意味着每条 lane 启动时天然清掉前一条留下的 server。
R=/data/xbw/turnstile/results/night
L=/data/xbw/turnstile/scripts/chain_gpu2.log
wait_for () { while [ ! -f "$R/$1/summary.json" ]; do sleep 60; done; sleep 25; }
wait_for pois200_foyfix_hc
for step in foy_r2 foyer_x2 cap3_r3 foyer_hc_r4 foyer_c50 foyer_zero; do
  # stale guard: run_matrix uses makedirs(exist_ok=True) and does NOT clear the
  # run dir. An old dir of the same name would let append-mode logs (admissions,
  # controller) mix records from a previous run into this one, silently.
  for rr in $(grep -o "pois200_[a-z0-9_]*" /data/xbw/turnstile/scripts/lane_$step.sh | sort -u); do
    if [ -d "$R/$rr" ] && [ ! -f "$R/$rr/summary.json" ]; then
      mv "$R/$rr" "$R/_stale_$(date +%Y%m%d%H%M)_$rr"
      echo "$(date '+%m-%d %H:%M')   挪走同名旧目录 $rr" >> $L
    fi
  done
  pre=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 2)
  echo "$(date '+%m-%d %H:%M') -> lane_$step  (开跑前 gpu2 显存 ${pre}MiB)" >> $L
  if bash /data/xbw/turnstile/scripts/lane_$step.sh >> $L 2>&1; then
    echo "$(date '+%m-%d %H:%M')    lane_$step OK" >> $L
  else
    echo "$(date '+%m-%d %H:%M')    lane_$step 失败 rc=$?" >> $L
  fi
done
echo "$(date '+%m-%d %H:%M') gpu2 链完成" >> $L
