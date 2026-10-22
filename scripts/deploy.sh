#!/bin/bash
# 把本地 scripts/ 推到实验机 —— 单向，本地是唯一的源。
#
# 为什么需要它：2026-10-12 之前这个项目有三个「事实来源」（本地 scripts/、
# 实验机 scripts/、实验机 TraceLab/replay/scripts/），而且互相同步的方向
# 【每个文件都不一样】——controller_budget3.py 是本地新，run_matrix.py 是
# 实验机新。结果是分析 data31 头条时读了一份从来没跑过的代码，白查一小时。
#
# 从 2026-10-12 起：
#   · 本地  /root/paper/foyer/scripts/         ← 只在这里改代码
#   · 实验机 /data/xbw/turnstile/scripts/       ← 部署目标，不要直接编辑
#   · TraceLab/replay/scripts/{那6个}           ← 符号链接到实验机 scripts/
#
# 用法：
#   bash scripts/deploy.sh            推送并核对
#   bash scripts/deploy.sh --check    只看差异，不推
set -u
# ⚠ `controller_foyer.py` 不在此列，而且**故意不同步**。
# 实验机上留的是 **as-run 版**（md5 43462c27），仓库版（f101f5b5）多一个
# `replay_admissions()` 诊断，**它从没部署过**，而它在主循环里真的被调用（第 570 行）
# —— 推过去就等于改变 `foyer` 路由执行什么，已发表的 `foyfix_hc` 等结果就复现不了。
# 这是**唯一一处有意保留的分歧**，见 docs/CODE_DIVERGENCE.md。新实验走 `budget3`。
HOST=lab-3090
LAB=/data/xbw/turnstile/scripts
SRC=$(cd "$(dirname "$0")" && pwd)
FILES="controller_budget3.py controller_aimd2.py monitor.py run_matrix.py smoke_aimd2_hsignal.py"
CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

fail=0
for f in $FILES; do
    [ -f "$SRC/$f" ] || { echo "  !! 本地缺 $f"; fail=1; continue; }
    a=$(md5sum "$SRC/$f" | cut -c1-12)
    b=$(timeout 25 ssh -o ConnectTimeout=8 "$HOST" "md5sum $LAB/$f 2>/dev/null | cut -c1-12")
    if [ "$a" = "$b" ]; then
        printf "  = %-24s %s\n" "$f" "$a"
    elif [ "$CHECK" = "0" ]; then
        # 走 deploy_to_lab.sh，不裸 scp —— 它做【原子替换】（同目录临时名 + rename）。
        # bash 是增量读脚本的，就地覆盖会把正在跑的脚本撕成两半（2026-09-21 真发生过）。
        LAB_HOST="$HOST" bash "$SRC/deploy_to_lab.sh" "$SRC/$f" \
            && printf "  > %-24s %s -> %s\n" "$f" "$a" "$b"
    else
        printf "  ! %-24s 本地=%s 实验机=%s\n" "$f" "$a" "$b"; fail=1
    fi
done

# TraceLab 那 5 个必须是符号链接、controller_foyer.py 必须是真实文件（唯一例外）
echo "--- 符号链接核对 ---"
timeout 25 ssh -o ConnectTimeout=8 "$HOST" \
  'T=/data/xbw/turnstile/TraceLab/replay/scripts; rc=0
   for f in controller_budget3.py controller_aimd2.py monitor.py run_matrix.py smoke_aimd2_hsignal.py; do
       [ -L "$T/$f" ] || { echo "  !! $f 不是符号链接（被覆盖了？）"; rc=1; }
   done
   [ -L "$T/controller_foyer.py" ] && { echo "  !! controller_foyer.py 变成了符号链接 —— 那会把 as-run 版覆盖掉"; rc=1; }
   [ "$(md5sum "$T/controller_foyer.py" | cut -c1-12)" = "43462c276ec4" ] \
       || { echo "  !! controller_foyer.py 不是 as-run 版（应为 43462c276ec4）"; rc=1; }
   [ $rc = 0 ] && echo "  ✓ 5/6 符号链接 + controller_foyer.py = as-run 版"
   exit $rc' || fail=1

exit $fail
