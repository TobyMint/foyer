#!/bin/bash
# 在 lab-A100 上跑：把 3090 上的实验管线搬过来（方向 D 的前置）。
#
# 两台机器在同一网段（3090 = 192.168.1.103，A100 = 192.168.1.104，RTT 0.2ms），
# 所以直连 rsync，不用经本机中转。已在 3090 的 authorized_keys 里加了 A100 的公钥。
#
# 传什么、不传什么：
#   传：TraceLab（去掉 target 里的编译中间产物，只取 release/session_runner 二进制）、
#       data/enwik9（runner 生成正文用的语料）+ 几个 replay csv、cap_* 标记文件
#   不传：results/（历史日志，几十 G，A100 上不需要）、
#         data/syfi_coding_trace.duckdb（153M，主 trace 用不到）
#
# 模型【不在】这里传：3090 上的模型目录只是指向 /data/models/Qwen2.5-Coder-7B-Instruct
# 的符号链接 + 一个改过的 config.json（YaRN factor 3）。A100 上从 hf-mirror 下基座，
# 再把 scripts/a100/qwen25-coder-7b-yarn96k.config.json 覆盖上去即可。
set -e
SRC=192.168.1.103:/data/xbw/turnstile
DST=/data/xbw/turnstile
mkdir -p "$DST"

echo "=== [$(date '+%F %T')] TraceLab（排除 target 整体）==="
rsync -a --partial --exclude='replay/target/*' "$SRC/TraceLab/" "$DST/TraceLab/"

echo "=== [$(date '+%F %T')] runner 二进制 ==="
mkdir -p "$DST/TraceLab/replay/target/release"
rsync -a --partial "$SRC/TraceLab/replay/target/release/session_runner" \
      "$DST/TraceLab/replay/target/release/session_runner"

echo "=== [$(date '+%F %T')] data（enwik9 + replay csv，跳过 duckdb）==="
rsync -a --partial --exclude='syfi_coding_trace.duckdb' "$SRC/data/" "$DST/data/"

echo "=== [$(date '+%F %T')] cap 标记文件 ==="
rsync -a --partial "$SRC/"cap_* "$DST/" 2>/dev/null || true

echo "=== [$(date '+%F %T')] 校验 ==="
ls -la "$DST/TraceLab/replay/target/release/session_runner"
du -sh "$DST/TraceLab" "$DST/data"
md5sum "$DST/data/replay_pois200_l04.csv"
echo "--- 与 3090 对比（应相同）---"
ssh 192.168.1.103 'md5sum /data/xbw/turnstile/data/replay_pois200_l04.csv'
echo "=== [$(date '+%F %T')] 完成 ==="
