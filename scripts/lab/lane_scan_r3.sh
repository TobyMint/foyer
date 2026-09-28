#!/bin/bash
# `foyer_scan` 的**第三次**读数 —— 全篇头条那条臂的第三条重复。
#
# ## 为什么跑第三条（这一条要写清，因为它是【改了计划】）
#
# 今早 `scan_r2` 落地后，我们按跑前预注册走的是 (a) 分支：两次读数都越线
# （+1.3044 / +2.1600），头条据此从「一次读数、unresolved」升级为「两次读数都越线」。
# 那份预注册的决策表在 (a) 档写的是「**不必**再排，两次独立读数已是真结果」。
#
# **现在跑第三条，是因为那条判断的依据变了，不是因为结果不合意：**
# r49 双审查（中立子 agent + codex）把这一处列为**全篇最可能被审稿人攻击的一点** ——
# 两次读数相差 **0.8556 pp**，而同配置重复的 Δ 全距是 **0.5--4.6 pp**，0.86 落在
# 那个散布**之内**。也就是说「两次都越线」是事实，但它只靠两个样本，
# 而这两样本之间的差**并不小于**我们自己的重复散布。
#
# ## 预注册的【报告规则】（比三条预期更重要）
#
# **三条读数全部照实报，无论结果。** 不许只报有利的那条，不许跑第四条来「补到好看为止」。
# 若第三条落回带内，头条必须从「都越线」改成「三条里两条越线」，§V/§VI/§VII/摘要
# 一起收 —— 这是跑之前就答应的，不是事后商量的。
#
# ## 三条预期（跑之前写在这里，照抄）
#
#   (a) 第三条仍 **> +1.0pp** ⇒ 3/3 越线。头条升级为「三次读数都越线」，
#       **但必须同时写明** 0.86 的两次之差落在重复散布内 —— 两件事都要说。
#   (b) 第三条落回 **±1.0pp 带内或线下方** ⇒ 2/3。头条**必须退回**
#       「三次里两次越线，第三次在带内」，并写明是哪一次、读数多少。
#   (c) 三条两两相差 > 1.0pp ⇒ 这条臂的噪声比正文写的更大，
#       「0.5 to 4.6pp」那个区间要按三条重算（scan 组自己的全距也会变）。
#
# 三种都要写进 §V/§VI/§VII 与摘要，**不许只报对自己有利的那种**。
#
# ## 配置：与 `pois200_foyer_scan` / `_scan_r2` **逐字相同**
#
# 判据是 metadata 逐字段比（两条已有的读数在这几轴上完全相同）：
#   gpu=2 / policy=budget3scan:hw=0;target=0.95 / pool=101432 / memfrac=0.85 /
#   trace=df4bdd37e5 (replay_pois200_l04.csv) / run_matrix=cfd46f9b1ea2 /
#   controller_budget3_scan.py=068b0b7a0bcc
#
# ⚠ **共现条件也复现**：`scan` 与 `hz2_r3` 并行、`scan_r2` 与 `sf0_r3` 并行 ——
#   两条都是在 **2 车道**下测的。所以这一条也配一条伙伴跑在卡 3，
#   而不是让它独占一台机器（那会变成第三个变量）。
#
# ⚠ run_matrix.py 的默认值逐条核过：EXPECT_POOL 默认正好是 101432 ✓、POOL_TOL 20 ✓；
#   但 MEMFRAC 默认 0.88、TRACE 默认 replay_night200.csv、RUN_TIMEOUT_H 默认 6 ——
#   这三条**必须显式设**才能与已有两条逐字相同（本项目在 A100 上栽过「默认值是别人的机器」）。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane scanr3 --gpu 2 --port 30090 \
  --runs "pois200_foyer_scan_r3:budget3scan:hw=0;target=0.95"
bash /data/xbw/turnstile/scripts/lane_done.sh scanr3 pois200_foyer_scan_r3
