#!/bin/bash
# drive_one.sh <run> <policy> <trace> <port> <hc|nohc> [gpu列表]
#
# **一个任务，一条命令，跑完就退出。** 不挂队列、不串下一条、不 nohup。
# （用户 2026-10-12 定规：服务器上不许再有「脱离的、自己会跑的」东西 ——
#   实证过两个孤儿 watcher 跑 39 小时，往一个 2.15 小时的 run 里灌了 94% 的垃圾。）
#
# 与 drive2.sh 的三点不同：
#   1. GPU【不硬编码】—— 默认按 "2 3 1 0" 的顺序找第一张 <200 MiB 的空卡。
#      drive2.sh 只等 gpu1；若 0 或 3 先空，那条命令会白等。
#   2. 空卡门连查三次（每次隔 90 秒），而不是两次 —— 邻居的任务是移动的。
#   3. 停滞看门狗保留（10 分钟不增长就杀 runner，留 PARTIAL 标记）。
#
# 空卡门是【整卡】判据（<200 MiB），**不算剩余空间够不够** —— 项目规矩。
set -u
# ★ 抗断线：2026-10-19 凌晨本机 WSL 断网，ssh 链路断掉时 sshd 发 SIGHUP，
#   把正在等卡的 drive_one.sh 收走了（最后一条日志 02:25，run 目录都没建）。
#   忽略 HUP 之后 bash 和它派生的 run_matrix / server 都不再随链路消失。
trap '' HUP
RUN=$1; POLICY=$2; TRACE=$3; PORT=$4; HC=${5:-hc}; GPUS=${6:-"2 3 1 0"}
# 2026-10-23：trace 允许相对路径（自动补成 $BASE/data/）。
# 起因：autopilot 传了 "replay_long19.csv"，run_matrix 直接 open() 相对路径 →
# FileNotFoundError，drive_one 在创建 run 目录之前就死了（卡白白空着）。
BASE=/data/xbw/turnstile
case "$TRACE" in
  /*) ;;
  *) TRACE="$BASE/data/$TRACE" ;;
esac
R=/data/xbw/turnstile/results/night
LOG=/data/xbw/turnstile/scripts/drive_atonce.log
say() { echo "$(date '+%m-%d %H:%M')  $*" >> $LOG; }

free_mib() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
temp_c()   { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
clock_mhz(){ nvidia-smi --query-gpu=clocks.sm --format=csv,noheader,nounits -i "$1" 2>/dev/null; }

# 热降频门（2026-10-19 加）。
#
# 为什么需要：那一夜 GPU 2/3 被热降频到 210/240 MHz（上限 2100），满载功耗只有
# 156 W（上限 350 W）—— 不是功耗墙是温度墙。两条 run 因此慢了 10 倍，
# 数据全废，而脚本当时【毫无察觉】，照跑不误。
# 而【空闲】的卡就有 75~77°C ⇒ 这是机箱/机房散热的问题，换卡也没用。
#
# 判据用【空闲温度】，因为开跑前没法测满载时钟：空闲 >TEMP_MAX 的卡，
# 一跑必然冲上 90°C 并降到最低档。TEMP_MAX 可用环境变量覆盖。
TEMP_MAX=${TEMP_MAX:-70}

# ---- 1) 等一张空卡（连续三次确认），并且要凉 ----
GPU=""
while [ -z "$GPU" ]; do
  for g in $GPUS; do
    ok=1; why=""
    for k in 1 2 3; do
      v=$(free_mib "$g"); v=${v:-99999}
      t=$(temp_c "$g");   t=${t:-999}
      [ "$v" -lt 200 ] || { ok=0; why="占着 ${v}MiB"; break; }
      [ "$t" -lt "$TEMP_MAX" ] || { ok=0; why="太热 ${t}°C (上限 ${TEMP_MAX})"; break; }
      [ "$k" -lt 3 ] && sleep 90
    done
    if [ "$ok" = 1 ]; then GPU=$g; break; fi
    [ -n "$why" ] && { say "[$RUN] gpu$g 不能用：$why"; }
  done
  [ -n "$GPU" ] || { say "[$RUN] 没有可用卡（$GPUS），等"; sleep 120; }
done
say "[$RUN] gpu$GPU 空了且 ${TEMP_MAX}°C 以下 —— 开跑"

# ---- 2) 陈旧目录守卫 ----
if [ -d "$R/$RUN" ] && [ ! -f "$R/$RUN/summary.json" ]; then
  mv "$R/$RUN" "$R/_stale_$(date +%Y%m%d%H%M)_$RUN"
  say "[$RUN] 挪走了同名旧目录"
fi

# ---- 3) 环境（与既有 run 逐字同口径） ----
export TURNSTILE_RUN_TIMEOUT_H=8
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_EXPECT_POOL=${TURNSTILE_EXPECT_POOL:-101432}
# HCR 环境变量可以覆盖 host 层倍率（默认 2）。用来做缓存容量的敏感性分析：
# 实测 host 层 0.2M token 在两条臂上都是 100% 满的，而工作集是 19x60K = 1.14M。
HCR=${HCR:-2}
if [ "$HC" = "hc" ]; then
  export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio $HCR --hicache-write-policy write_through"
else
  export TURNSTILE_HICACHE_ARGS=""
fi
export TURNSTILE_TRACE=$TRACE

# ---- 4) 跑（前台，本进程直接持有） ----
P=/data/xbw/turnstile/envs/main/bin/python
say "起 $RUN (policy=$POLICY, hc=$HC, gpu=$GPU, port=$PORT)"
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py \
   --lane atonce --gpu "$GPU" --port "$PORT" --runs "$RUN:$POLICY" >> $LOG 2>&1 &
RM=$!

# ---- 5) 停滞 + 热降频看门狗 ----
# 热降频那一条：开跑前查的是【空闲温度】，挡不住"开跑后才烧起来"。
# 所以跑起来之后再看【实际 SM 时钟】—— 那才是最终事实。
# 判据：时钟 < CLOCK_MIN（默认 800 MHz，上限 2100）连续 3 次（6 分钟）⇒ 杀。
# 用 800 而不是 2100 是留余量：正常跑在 1600~2000，热降频时掉到 200 上下，
# 两者差得很远，阈值不敏感。
CLOCK_MIN=${CLOCK_MIN:-800}
prev=-1; stall=0; slow=0
while kill -0 $RM 2>/dev/null; do
  sleep 120
  n=$(wc -l < "$R/$RUN/steps.jsonl" 2>/dev/null || echo 0)
  if [ "$n" -eq "$prev" ] && [ "$n" -gt 0 ]; then
    stall=$((stall+1))
    if [ "$stall" -ge 5 ]; then
      say "⚠ $RUN 停滞在 $n 步已 10 分钟 —— 杀 runner（记为部分运行）"
      echo "$n" > "$R/$RUN/PARTIAL_$(date +%H%M).txt"
      pkill -f "session_runner.*$RUN" 2>/dev/null
      stall=0
    fi
  else stall=0; fi
  prev=$n
  # 热降频：只在真的在跑（步数在涨）时才判，避免开跑初期误杀
  if [ "$n" -gt 0 ] && [ "$stall" -eq 0 ]; then
    c=$(clock_mhz "$GPU"); c=${c:-9999}
    t=$(temp_c "$GPU");    t=${t:-0}
    if [ "$c" -lt "$CLOCK_MIN" ]; then
      slow=$((slow+1))
      say "[$RUN] ⚠ gpu$GPU 时钟 ${c}MHz < ${CLOCK_MIN}，温度 ${t}°C（第 $slow/3 次）"
      if [ "$slow" -ge 3 ]; then
        say "⚠ $RUN gpu$GPU 热降频到 ${c}MHz —— 数据不可用，杀掉（记为热降频作废）"
        echo "thermal: clock=${c}MHz temp=${t}C steps=$n" > "$R/$RUN/VOID_THERMAL_$(date +%H%M).txt"
        pkill -f "session_runner.*$RUN" 2>/dev/null
        slow=0
      fi
    else slow=0; fi
  fi
done
wait $RM
rc=$?
say "$RUN 结束 rc=$rc"
exit $rc
