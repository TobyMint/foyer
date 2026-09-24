#!/bin/bash
# 把 HiCache 曲线推到更高的 R̄ —— 方向 B 的定量检验。
# 用法: lane_cap_hc_ext.sh <lane名> <gpu> <port> <逗号分隔的 runs> <marker run>
#
# 要检验的预测：复用率的天花板由【容量】定，host 梯队把有效容量变成 device+host。
# 设备池 101432，hicache-ratio 2 => host 再装 2×101432，合计 ~3×。
# 所以 device-only 在 R̄≈1.5 就开始兑现不了天花板（复用 0.596，cap3_fixed），
# 而 HiCache 应该到 ~3 倍的负载才塌。
#
# 现有 HiCache 静态点只到 R̄ 1.729（cap4_hc），刚好卡在控制器运行区间（1.35~1.71）上沿，
# 看不到更高处有没有悬崖 —— docs/finding_hicache_elasticity_20260923.md 把它列为
# 「尚未确定」。cap5/6/8_hc 把区间推到 R̄ ~2.5 以上：
#   概率一：复用守住、eps 仍 <1  -> 容量律成立，且能【测出】悬崖不在此处
#   概率二：复用开始塌           -> 「悬崖位置由容量定」被证伪或需修正
# 两种结果都照实写。这是方向 B 从「观察」变成「可证伪预测」的关键一步。
#
# 与已有 HiCache 静态点逐字同配置（同 trace、memfrac 0.85、同 HiCache 参数、池子 101432）。
set -e
LANE=$1; GPU=$2; PORT=$3; RUNS=$4; MARK=$5
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane "$LANE" --gpu "$GPU" --port "$PORT" --runs "$RUNS"
bash /data/xbw/turnstile/scripts/lane_done.sh "$LANE" "$MARK"
