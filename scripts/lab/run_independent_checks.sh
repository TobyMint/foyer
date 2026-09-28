#!/bin/bash
# 五条独立复算线一次跑完 —— 定稿前必跑，任何一条非零退出就整体失败。
#
# 为什么要有这个脚本：这四条线**只有被跑才有价值**，而四条各有各的参数，
# 手打容易漏（本项目「跑之前先挂脚本、别手打」那一条）。
# 它们的共同判据是：**不 import 生成器**、从 trace / steps.jsonl 从头算，
# 与 paper/data/*.csv 逐位对拍。抓的是【实现 bug】【抄录错误】【用错列】三类。
set -u
cd "$(dirname "$0")/../.."
P=python3
fail=0
run() {
  echo "===== $* ====="
  if ! $P "$@"; then echo "!! 失败：$*"; fail=1; fi
  echo
}
run scripts/lab/independent_frontier_check.py   data/replay_pois200_l04.csv results/night
run scripts/lab/independent_realization_check.py data/replay_pois200_l04.csv results/night paper/data/reuse.csv
# 第二条 trace 的同一组量（§VI 的跨 trace 对照；目录名是裸 `realhr_*`，不带 pois200_ 前缀）
run scripts/lab/independent_realization_check.py data/replay_realhr.csv results/night paper/data/reuse_x.csv
run scripts/lab/independent_decomp_check.py      results/night paper/data/decomp.csv
run scripts/lab/independent_elasticity_check.py  paper/data/decomp.csv
run scripts/lab/independent_attribution_check.py paper/data
echo "==================================================="
if [ "$fail" = 0 ]; then echo "五条独立线全部通过"; else echo "有独立线失败 —— 以它为准去查生成器"; fi
exit $fail
