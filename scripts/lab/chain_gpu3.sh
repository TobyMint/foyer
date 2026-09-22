#!/bin/bash
# gpu3 整夜队列。端口固定 30043（理由同 chain_gpu2）。
R=/data/xbw/turnstile/results/night
L=/data/xbw/turnstile/scripts/chain_gpu3.log
wait_for () { while [ ! -f "$R/$1/summary.json" ]; do sleep 60; done; sleep 25; }
wait_for pois200_cap2_hc
for step in cap2_r2 cap2_x2 cap2_x05 foyer_x05 cap2_c50; do
  # stale guard: run_matrix uses makedirs(exist_ok=True) and does NOT clear the
  # run dir. An old dir of the same name would let append-mode logs (admissions,
  # controller) mix records from a previous run into this one, silently.
  for rr in $(grep -o "pois200_[a-z0-9_]*" /data/xbw/turnstile/scripts/lane_$step.sh | sort -u); do
    if [ -d "$R/$rr" ] && [ ! -f "$R/$rr/summary.json" ]; then
      mv "$R/$rr" "$R/_stale_$(date +%Y%m%d%H%M)_$rr"
      echo "$(date '+%m-%d %H:%M')   挪走同名旧目录 $rr" >> $L
    fi
  done
  pre=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 3)
  echo "$(date '+%m-%d %H:%M') -> lane_$step  (开跑前 gpu3 显存 ${pre}MiB)" >> $L
  if bash /data/xbw/turnstile/scripts/lane_$step.sh >> $L 2>&1; then
    echo "$(date '+%m-%d %H:%M')    lane_$step OK" >> $L
  else
    echo "$(date '+%m-%d %H:%M')    lane_$step 失败 rc=$?" >> $L
  fi
done
echo "$(date '+%m-%d %H:%M') gpu3 链完成" >> $L
