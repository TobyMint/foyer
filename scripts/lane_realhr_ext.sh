#!/bin/bash
# realhr 静态扫描的补全（2026-09-24 假期窗口）。
#
# 为什么补：xtrace_validation.md §6.1 记的缺口是「判据的核心区间在 realhr 上未采样」——
# 已有的三个静态点 R̄busy = 1.076 / 1.160 / 1.287（cap2/3/4，均已验证 cap 是绑定的，
# peak == cap），一个都没到 1.5，而主 trace 的悬崖在 R̄≈1.53。所以跨 trace 检验只覆盖了
# 曲线的便宜一半，贵段那一半是【未测】而不是【被证实不存在】。
#
# 这个补充同时是方向 B 的关键检验：realhr 的静态点全部是 device-only（无 HiCache），
# 与主 trace 的 device-only 族同配置。若 cap5/6/8 把 R̄busy 推过 1.5 之后 ε 同样过 1
# （即命中率塌、τ 跳），则「悬崖是【配置】属性而非 trace 属性」得到第二个 trace 的支持；
# 若 ε 不过 1，则方向 B 的主线主张在第二条 trace 上不成立 —— 两种结果都照实写。
#
# 另外补两个重复：realhr 这一族此前【一个重复都没有】，而 realhr_foyer 的 +0.40pp
# 判决和 cap4 的锚点位置都建立在单次 run 上。
#
# 判据（看结果前定死）：判决口径同 frontier.py（对静态点上左包络的分段线性插值，
# 10 s 阈值，±1.0 pp 打平）。cap5/6/8 只作为包络候选点，不预设它们越过谁。
#
# ⚠ 与现有 realhr 点必须逐字同配置：无 HiCache、memfrac 0.85、同一条 realhr.csv
#   (md5 882c29a022)、池子 101432。池子对不上该 run 作废（run_matrix 自带守卫）。
set -e
export TURNSTILE_RUN_TIMEOUT_H=8
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_realhr.csv
# 故意不设 TURNSTILE_HICACHE_ARGS —— 与已有 realhr 静态点保持一致（device-only）
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane realhr_ext --gpu 3 --port 30033 \
  --runs 'realhr_cap5:static=5,realhr_cap6:static=6,realhr_cap8:static=8,realhr_cap4_r2:static=4,realhr_foyer_r2:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh realhr_ext realhr_foyer_r2
