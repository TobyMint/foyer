#!/bin/bash
# lab-A100 第二配置验证 —— 与 3090 主 trace **同模型、同 trace、同 memfrac、同引擎版本**，
# 只有【卡】与【池子大小】不同。这是论文 §III 因果主张的直接检验。
#
# 为什么现在能跑：此前判「不可比」，是因为只在 /data/models 下找模型 ——
# 而模型其实在 /data/xbw/turnstile/models/qwen25-coder-7b-yarn96k（md5 与 3090 侧一致）。
# 2026-09-25 02:40 A100 出现真窗口（三卡 foreign=0MiB、GPU0 空闲 79G、util 0%，持续 10 分钟）。
#
# 预注册预测（看结果前定死）：
#   3090 device-only 的兑现率：cap1 92.5% / cap2 89.7% / cap3 79.0% / cap4 60.7% / cap5 36.4%
#   （R̄ 1.00 → 1.84）。若「兑现率由容量定」，A100 的池子大约是它的 9 倍（memfrac 同 0.85），
#   同一批 cap 在【同一 R̄】上应兑现明显更高（预期 >=85%），塌点被推到更高的 R̄。
#   若 A100 仍在同样的 R̄ 上塌到同样的水平，则「容量定塌点」被证伪。
#   两种结果都照实写。
#
# ⚠ TURNSTILE_EXPECT_POOL=0 是【故意】关掉池子守卫：守卫默认要求 101432±20，
#   而 80G 卡上 memfrac 0.85 的池子本来就该大得多。关掉之后 memfrac 被钉在 0.85，
#   池子由卡自己决定，实际值写进 metadata 的 pool_tokens。
set -e
# ⚠ 主机编译器：A100 上只有 gcc 8/9，而 sglang 的 JIT kernel 要 C++20（需要 gcc>=10）。
# 不指这条，server 会在 CUDA graph capture 阶段因 `fatal error: concepts` 起不来
# （rc=-9）。conda-forge 的 gcc-12 装在 /data/xbw/gcc12，CUDA 12.1 支持到 gcc 12。
# /usr/local/gcc-14.3.0 试过但 CUDA 12.1 不兼容（100 个错误）。
# CUDAHOSTCXX 单独设【不够】：JIT 的 build.ninja 里写死了 nvcc 路径、不带 -ccbin，
# 所以要用 nvcc 自己的 NVCC_PREPEND_FLAGS 把主机编译器注进去（实测有效）。
export NVCC_PREPEND_FLAGS="-ccbin /data/xbw/gcc12/bin/x86_64-conda-linux-gnu-g++"
export CUDAHOSTCXX=/data/xbw/gcc12/bin/x86_64-conda-linux-gnu-g++
export CC=/data/xbw/gcc12/bin/x86_64-conda-linux-gnu-gcc
export CXX=$CUDAHOSTCXX
export PATH=/data/xbw/gcc12/bin:$PATH
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_EXPECT_POOL=0
export TURNSTILE_POOL_TOL=20
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
# 故意不设 TURNSTILE_HICACHE_ARGS —— 与 3090 的 device-only 族逐字同配置
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/sglang-env/bin/python
$P $S --lane a100_dev --gpu 0 --port 30091 \
  --runs "a100_cap4:static=4,a100_cap3:static=3,a100_cap5:static=5,a100_cap2:static=2"
