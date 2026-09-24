#!/bin/bash
# 半池对照 —— 方向 B 的【因果】检验。
# 用法: lane_pool50.sh <lane名> <gpu> <port> <runs> <marker run>
#
# 为什么这个实验比换卡更有价值：
# 现在的证据是「device-only 会塌、加了 host 梯队不塌」，这两者同时变了三样东西
# （容量、是否有第二级、驱逐后的去向）。所以「容量决定悬崖」目前只是相关，不是因果。
# 把池子减半、其余全不动（同一张卡、同一条 trace、同一个模型、同一份代码），
# 只改容量这一个变量，才把这个主张变成可证伪的因果陈述。
#
# 预测（看结果前定死）：复用天花板塌掉的运行数应随池子同比例下移。
#   全池 101432：cap2 (R̄ 1.27) 兑现 0.677、cap3_fixed (R̄ 1.53) 兑现 0.596
#   半池  50716：cap2 的上下文总和已经接近半个池子，预期 cap2、cap3 都明显跌破各自全池的值
# 判据：复用率 = (prompt - dev_miss + host_hit) / prompt，同 gen_reuse.py。
#   若半池的 cap2/cap3 复用率与全池【无显著差别】，则「容量决定悬崖」被证伪。
#
# 池子大小：101432 -> 50716（正好一半）。run_matrix 的 solve_memfrac 会自己找
# mem-fraction。MEMFRAC 设 0.73 是给求解器的下界（源码里是 max(MEMFRAC, solve(...))），
# 按 57 KB/token 反推半池需 memfrac 0.737（全池 0.850003 对应 101432），下界取 0.73：
# 低了下界会让探针 OOM，高了下界会把求解器顶住导致池子对不上，两者都会显式失败、不会静默出错。
#
# ⚠ 池子守卫：这里的 EXPECT_POOL 必须是 50716，不是默认的 101432 —— 本项目
# 「池子必须 101432±20」那条规矩是为了和主表可比，本实验是【故意】改池子，
# 所以显式覆盖，并把新值记进 metadata（run_matrix 会把这几个 env 写进 metadata）。
set -e
LANE=$1; GPU=$2; PORT=$3; RUNS=$4; MARK=$5
export TURNSTILE_RUN_TIMEOUT_H=14
export TURNSTILE_MEMFRAC=0.73
export TURNSTILE_EXPECT_POOL=50716
export TURNSTILE_POOL_TOL=20
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
# 故意不设 HiCache —— 本实验只动容量，不动梯队级数
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane "$LANE" --gpu "$GPU" --port "$PORT" --runs "$RUNS"
bash /data/xbw/turnstile/scripts/lane_done.sh "$LANE" "$MARK"
