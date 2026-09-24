#!/bin/bash
# lab-A100 上的第二配置实验（方向 D）。用法: lane_a100.sh <lane> <gpu> <port> <runs> <marker> <expect_pool>
#
# 要回答的问题：论文的主线主张是「容量决定复用悬崖在哪」。3090 上池子 101,432 token
# （只装得下约四个中位会话），所以「池子是绑定资源」这个前提在那边是当然成立的。
# A100 80GB 上同一个模型能开大约 8~10 倍的池子 —— 如果复用天花板在这个配置下
# 一直到高得多的运行数都不塌，那条主张就在【第二个配置】上得到支持；如果照样在
# 低运行数就塌，说明我们量到的不是容量。
#
# 与 3090 逐项对齐（可比性的前提，任一不同就变成"换配置+换别的东西"）：
#   模型  qwen25-coder-7b-yarn96k（基座从 3090 传过来，config.json md5 两边一致）
#   trace replay_pois200_l04.csv（md5 两边一致）
#   引擎 sglang 0.5.10.post1 / torch 2.9.1+cu128 / python 3.11.16
#   上下文 98304；不开 HiCache（本实验只动容量）
#
# ⚠ 池子守卫：这台卡有别的租户，mem-fraction-static 是按【总显存】算的，
# 别人占着的时候开不高。所以 EXPECT_POOL 由调用方按当时可用的显存给，
# 实际值记在 metadata.json 里，事后必须核对而不是假定。
# ⚠ 本机同样会跑采样器记录同卡进程；A100 常年 90%+ 利用率，跑之前先看
#   是否真有窗口，测完必须查 gpu_watch 再决定这批数据能不能用。
set -e
LANE=$1; GPU=$2; PORT=$3; RUNS=$4; MARK=$5; POOL=${6:-811456}
export TURNSTILE_RUN_TIMEOUT_H=14
export TURNSTILE_MEMFRAC=0.70          # 下界，求解器会往上找
export TURNSTILE_EXPECT_POOL=$POOL
export TURNSTILE_POOL_TOL=$((POOL / 20))
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/sglang-env/bin/python
$P $S --lane "$LANE" --gpu "$GPU" --port "$PORT" --runs "$RUNS"
bash /data/xbw/turnstile/scripts/lane_done.sh "$LANE" "$MARK" 2>/dev/null || true
