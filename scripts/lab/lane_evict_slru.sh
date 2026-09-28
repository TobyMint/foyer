#!/bin/bash
# 驱逐政策对照：同一配置换成 `slru` —— 测 C9 的边界，而 C9 的边界**就是主线主张的边界**。
#
# ## 为什么跑
#
# 论文（sec_model.tex:213）写：
#   「the round-1-and-later prefix hit rate falls from 80.8% to 32.8% across the
#     device-only caps and holds at 80.7% to 78.7% across the three host-tier caps
#     of the controller's range」
# 也就是说：**命中率的崩塌只发生在 device-only 一侧，host-tier 一侧稳得住** ——
# 这是「host tier 决定准入控制有没有空间」这条主线的一根柱子。
#
# `paper/claims_audit.md` 的 C9 记着它的边界：
#   「**只测过准入政策，没测过驱逐政策**（SGLang 的 radix-eviction-policy 有 lru/lfu/slru）。
#     如果 slru 能超过计划值，这条就破。**未做的对照必须写明。**」
#
# 本次就是把那条对照补上。**它跑不跑得成不影响交付**（Limitations 已如实写了这个轴未测），
# 但如果 slru 动了命中率，那句话就得加限定。
#
# ## 配置：与 `pois200_foyer_hc`/`_hc_r2` 的差别**不止那个 flag**
#
# ⚠⚠ **2026-09-27（r51 双审查 D 组）改正**：本节原来写着「与 `pois200_foyer_hc`/`_hc_r2`
#    逐字相同」「已核两条已有 run 的 metadata 逐字段相同」「本次唯一的差别是 server
#    命令行多一个 `--radix-eviction-policy slru`」——**那是错的**。逐字段核
#    `metadata.json` 的实情：
#
#      | 字段 | foyer_hc | foyer_hc_r2 | **hc_slru** |
#      |---|---|---|---|
#      | run_matrix.py         | 9c7545548a5f | a8605b1e77d5 | **cfd46f9b1ea2** |
#      | controller_budget3.py | 2b573829083c | f825bc768188 | f825bc768188 |
#      | gpu                   | 2 | 2 | **3** |
#      | gpu_watch.jsonl       | **没有** | 有（晚起 283 分、**覆盖本次测量窗 5.8%**） | 有（全程 1166 条、0 外来） |
#
#    ⚠ **2026-09-27（r52 复核）改正**：`foyer_hc_r2` 那格原来写「覆盖 **2.4%**」，
#      **标签错**。2.34% = 本地镜像那份 `gpu_watch.jsonl` 里 2,900 条采样有 68 条
#      落在 run 窗内 —— 那是**文件的构成**，不是**监控的覆盖率**；watcher 实际覆盖
#      本次测量 1016.8 s ÷ 293.2 min（首 submit → 末 complete）= **5.8%**。
#      "晚起 283 分"（对 `metadata.json` 的 `started`）未动。
#
#    ⇒ **harness 代、控制器代、卡三项都不同**（相对 `foyer_hc`）；相对 `foyer_hc_r2`
#    也差 harness 代与卡两项。逐字相同的只有 policy 串 / 池 101432 / memfrac 0.85 /
#    trace / timeout 这几项 —— **这一半成立，整句不成立**。
#
#    ⇒ **这不是单变量对照。** 所以正文（`sec_discussion.tex` 的 realized-reuse 段）与
#    `paper/claims_audit.md` 的 C9 都按「**一次 `slru` 运行、读数与两次默认策略运行
#    相差 0.1pp；该比较跨卡、跨 launcher 版本**」改写 —— **提示性对照，不是
#    「命中率对驱逐策略不敏感」**。**照实披露，不许为了让对照看起来干净而含糊过去。**
#
# ⚠ **那个开关是走 `TURNSTILE_HICACHE_ARGS` 透传进去的，这是有意的**（这一条不变）：
#   `run_matrix.py` 只有这一个「原样追加到 server 命令行」的入口（第 353 行）。
#   ⚠ 但本文件原来接着写的是「没那么做是因为那会改 `run_matrix.py` 的哈希，于是本 run
#   与 `foyer_hc_r2`（harness cfd46f9b1ea2）就跨 harness 修订」——**哈希认错了**：
#   `foyer_hc_r2` 是 **a8605b1e77d5**，而 cfd46f9b1ea2 是**当时磁盘上最新的那一版**
#   （scan 三条 + 本 run 都用它）。本 run 事实上**就是**跨了 harness 修订，
#   「不让 harness 变」**没有兑现** —— 处置因此是**披露**，不是声称单变量。
#   读 metadata 的人请注意 `TURNSTILE_HICACHE_ARGS` 这一格里**多带了一个不是
#   HiCache 的 flag**。
#
# ## 三条预期（跑之前写在这里，照抄，不许事后挑说法）
#
# 主读数 = `hitrate.csv` 口径的 **round-1+ prefix hit rate**（逐步非加权均值），
# 已有的两条 lru 读数都是 **80.6%**，计划上限（trace 常量）是 **80.87%**。
#
#   (a) slru 落在 host-tier 已观测带 **78.7--80.7%** 之内（且 ≤ 80.87）
#       ⇒ **未在这一条 trace 的这一次运行上观察到大幅变化**。⚠ **不写成
#         「命中率对驱逐策略不敏感」** —— 800 个 round-1+ 步属于**同一次运行**、
#         不是 800 次独立重复，而且这一次跨了卡与 launcher 版本（见上）。
#         C9 的边界因此从「没测」变成「**测了一次、无大差、但对照不干净**」。
#   (b) slru **高于 80.87%**（即超过 trace 的计划上限）
#       ⇒ ⚠ **上限不是上限** ⇒ §III 的「appears here only as the bound」
#         与 C9 一起被推翻，必须**显著地**改写，不能塞进 Limitations 了事。
#   (c) slru **低于 78.7%** ⇒ 驱逐政策**确实能推动命中率**（向下）
#       ⇒ 「hit rate holds across the three host-tier caps」必须加限定：
#         那句话是在 lru 下测的，换 slru 会掉到 N%。
#
# 三种都要写，**不许只报对自己有利的那种**。Δ（SLO vs 前沿）作为次要观测一并记录，
# 但它**不是**本次的判据 —— 本次判据只有命中率。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
# ⚠ 末尾那一个 flag 不是 HiCache 参数（见上面的说明），它就是要测的那根旋钮。
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through --radix-eviction-policy slru"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane evictslru --gpu 3 --port 30091 \
  --runs "pois200_foyer_hc_slru:budget3:hw=0;target=0.95"
bash /data/xbw/turnstile/scripts/lane_done.sh evictslru pois200_foyer_hc_slru
