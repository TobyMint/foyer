#!/bin/bash
# chain_rep.sh <lane_script> <gpu> <run1> [run2 ...]
#
# 补跑用的看门链。与 `chain_one.sh` 的三处不同（都是 r66 codex 点出的缺陷）：
#   ① **绝不搬走、绝不覆盖既有目录** —— 目标目录存在就**拒跑并退出**（旧脚本会 `mv` 走
#      同名未完成目录再用同名重试，那与「绝不覆盖既有目录」相悖）。
#   ② **核对 lane 里写的 `--gpu` 与这里检查的那张卡是同一张**（旧脚本只查传入的编号，
#      而真正跑在哪个卡写在 lane 里，二者可以不一致）。
#   ③ **只跑一次**：失败不自动重试 —— 重试要用**新目录名**，由人来决定并记进预注册，
#      免得「同一个名字下面混了两次尝试」（本项目 2026-09-22 白跑一天的形状）。
set -u
lane=$1; gpu=$2; shift 2
RUNS=("$@")
R=/data/xbw/turnstile/results/night
L=/data/xbw/turnstile/scripts/chain_rep.log
say() { echo "$(date '+%m-%d %H:%M:%S')  $*" >> $L; echo "$(date '+%m-%d %H:%M:%S')  $*"; }

[ -f "$lane" ] || { say "!! lane 脚本不存在：$lane"; exit 2; }

# ② lane 里的 --gpu 必须与参数一致
if ! grep -qE -- "--gpu[[:space:]]+${gpu}([[:space:]]|\\\\)" "$lane"; then
  say "!! lane 里的 --gpu 与要检查的卡（$gpu）不一致 —— 拒绝启动"
  grep -n -- "--gpu" "$lane" >> $L
  exit 3
fi

# ① 目标目录一个都不许存在
for r in "${RUNS[@]}"; do
  if [ -e "$R/$r" ]; then
    say "!! 目标目录已存在：$R/$r —— 拒绝启动（绝不覆盖/搬走既有目录）"
    exit 4
  fi
done

# 等空卡：连续两次探测（间隔 90 s）都 < 200 MiB 才开火
while :; do
  pre=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$gpu")
  [ "$pre" -lt 200 ] && break
  say "gpu${gpu} 被占 ${pre}MiB，等空卡"
  sleep 120
done
sleep 90
pre2=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$gpu")
if [ "$pre2" -ge 200 ]; then say "gpu${gpu} 又被占（${pre2}MiB），继续等"; exec "$0" "$lane" "$gpu" "${RUNS[@]}"; fi

say "开火：$(basename "$lane") on gpu${gpu}（空 ${pre2}MiB），${#RUNS[@]} 条 run"
if bash "$lane" >> $L 2>&1; then
  say "lane OK"
  exit 0
else
  rc=$?
  say "lane 失败 rc=$rc —— **不自动重试**：重试要用新目录名并把这次尝试记进预注册"
  exit 1
fi
