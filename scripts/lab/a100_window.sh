#!/bin/bash
# lab-A100 的【真】空窗检测 —— 2026-09-25 加。
#
# 为什么旧的 a100_watch2.sh 不够：它每 30 分钟采一次瞬时利用率，
# 而 2026-09-25 00:14 那次采样读到 gpu0 util=0%、于是写下
# 「*** BIG WINDOW ***」——但同一分钟按进程查，机器上有三个租户在跑活跃训练
# （`yz` 的 CE3_baselines 三个进程，其中一个 elapsed 只有 3 分 23 秒，
# 也就是刚起的；`qcrs` 的 vllm 跑了 1 天 13 小时；`linchen` 的 GNN 跑了 14 小时）。
# 瞬时利用率在「一个 kernel 刚结束、下一个还没提交」的瞬间就是 0。
#
# 这正是本项目在 3090 上栽过的那类错误的翻版：**用错的口径判可用性**，
# 结果是把 run 跑进一个共享的机器上，而引擎侧指标事后看不出来。
#
# 严判据（三条同时满足，且要【持续】满足）：
#   1. 每 20 秒采一次，取窗口内 **util 的最大值**（不是瞬时值）；
#   2. 空闲显存 > 60GB；
#   3. 该卡上【别人的】计算进程占用的显存合计 < 1GB（有人挂着 4GB 就是有人在用）；
#   4. 以上状态连续保持 >= 10 分钟才判定为窗口。
#
# 判定的窗口写成标记文件，供人工/监控读取 —— **本脚本不自动起实验**：
# 起一个多小时的长跑是不可逆动作，必须由人看过再决定。
LOG=/data/xbw/a100_window.log
MARK=/data/xbw/a100_window_open
SAMPLE_S=20
WINDOW_MIN=10
SAMPLE_PER_MIN=$((60 / SAMPLE_S))
NEED=$((WINDOW_MIN * SAMPLE_PER_MIN))
: > "$LOG"
ok_streak=0
while true; do
  ts=$(date '+%m-%d %H:%M:%S')
  # 【按卡】统计：窗口只需要某一张卡空闲，所以“别人占用多少”必须逐卡算，
  # 不能全机合计（2026-09-25 第一版就写成了全机合计，于是 GPU2 被占 80GB
  # 会把 GPU0 的窗口也算掉）。
  foreign_by_gpu=$(nvidia-smi --query-compute-apps=gpu_uuid,used_memory \
                     --format=csv,noheader,nounits 2>/dev/null \
                   | awk -F, '{gsub(/ /,"",$1); gsub(/ /,"",$2); s[$1]+=$2} END{for (k in s) print k","s[k]}')
  best_free=0; best_util=100; best_foreign=0
  while IFS=, read -r idx uuid mem tot utl; do
    idx=$(echo "$idx"|tr -d ' '); uuid=$(echo "$uuid"|tr -d ' ')
    mem=$(echo "$mem"|tr -d ' '); tot=$(echo "$tot"|tr -d ' '); utl=$(echo "$utl"|tr -d ' ')
    [ -z "$idx" ] && continue
    freeg=$(( (tot - mem) / 1024 ))
    fo=$(echo "$foreign_by_gpu" | awk -F, -v u="$uuid" '$1==u{print $2+0}')
    fo=${fo:-0}
    if [ "$freeg" -gt "$best_free" ]; then best_free=$freeg; best_util=$utl; best_foreign=$fo; fi
  done <<< "$(nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu \
                --format=csv,noheader,nounits 2>/dev/null)"
  foreign=$best_foreign
  if [ "$best_free" -gt 60 ] && [ "$best_util" -lt 20 ] && [ "$foreign" -lt 1024 ]; then
    ok_streak=$((ok_streak + 1))
  else
    ok_streak=0
  fi
  echo "$ts free=${best_free}G util=${best_util}% foreign=${foreign}MiB streak=${ok_streak}/${NEED}" >> "$LOG"
  if [ "$ok_streak" -ge "$NEED" ]; then
    if [ ! -f "$MARK" ]; then
      {
        echo "$ts 真窗口：最大空闲 ${best_free}G、最大 util ${best_util}%、"
        echo "别人占用 ${foreign}MiB，且已连续 ${WINDOW_MIN} 分钟满足判据。"
        echo "→ 起跑前仍需人工确认（本脚本不自动起实验）。"
      } > "$MARK"
      echo "$ts *** REAL WINDOW ***" >> "$LOG"
    fi
  elif [ -f "$MARK" ]; then
    mv "$MARK" "$MARK.closed_$(date +%m%d_%H%M)" 2>/dev/null
    echo "$ts 窗口关闭（连续判据不再满足）" >> "$LOG"
  fi
  tail -3000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
  sleep "$SAMPLE_S"
done
