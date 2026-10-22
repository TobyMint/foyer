#!/bin/bash
# long19 头条队列（2026-10-12）—— 长会话数据集的「我们 vs 完全不管」那一对。
#
# 数据集：data/replay_long19.csv（19 会话 / 602 步 / 理论倍 12.7）
#         建法：scripts/build_replay_trace.py --long --mod 80
# 预注册：docs/prereg_atonce_20261010.md 的「2026-10-12」那一节（预测跑前写死）
#
# ⚠ 这一对是 2026-10-12 修好控制器【之后】的第一对 —— 此前所有 run 都带着
#    队首阻塞（head = waiting[:1]），实测造成 1387 分钟的门口等待。
#    所以这一对同时也在测那个修复，**不能直接与旧 run 比倍数**。
#
# 臂的顺序：先 foyer。无控制的用时大致可从上一条推（数据量大 ~1.4 倍），
# 而 foyer 那条是未知数，先拿到它。
D=/data/xbw/turnstile/scripts
T=/data/xbw/turnstile/data/replay_long19.csv
LOG=$D/drive_atonce.log
echo "$(date '+%m-%d %H:%M')  === long19 头条队列开始 ===" >> $LOG
bash $D/drive2.sh long19_foyer   "budget3:hw=0;target=0.95;base=resident" $T 30111 hc
bash $D/drive2.sh long19_default "default"                                $T 30112 hc
echo "$(date '+%m-%d %H:%M')  === long19 头条队列结束 ===" >> $LOG
