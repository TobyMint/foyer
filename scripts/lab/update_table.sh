#!/bin/bash
# 四条被争用臂的重跑落地后，更新表 I 的流水线 —— 一条命令，别手抄。
#
# 用法: bash scripts/lab/update_table.sh
#
# 前提：pois200_foyer_{bres,hz0,hz2,breshz1,cap1}_r2 都已写出 summary.json。
# 顺序有依赖：concurrency（决定 ‡）→ runs_precise（全精度坐标）→ runs.csv → table1.csv。
set -e
cd "$(dirname "$0")/../.."
echo "== 1. 同步 pois200_* 目录 =="
rsync -a --include='pois200_*/' --include='pois200_*/**' --exclude='*' \
      lab-3090:/data/xbw/turnstile/results/night/ results/night/
echo "== 2. concurrency.csv（必须在实验机上跑：判据是同时几条车道）=="
ssh lab-3090 '/data/xbw/turnstile/envs/main/bin/python /data/xbw/turnstile/scripts/gen_concurrency.py \
    /data/xbw/turnstile/results/night /tmp/conc_new.csv' > /dev/null
scp -q lab-3090:/tmp/conc_new.csv paper/data/concurrency.csv
python3 - <<'PY'
import csv
rows=[r for r in csv.DictReader(l for l in open("paper/data/concurrency.csv") if not l.startswith("#"))]
c=[r["run"] for r in rows if r["verdict"]=="CONTESTED"]
print("   CONTESTED %d 条（正文现在说「十四条里两条是 failed」）：" % len(c))
print("   " + " ".join(c))
PY
echo "== 3. runs_precise.csv（frontier.py --csv）=="
TURNSTILE_RESULTS=results/night python3 scripts/lab/frontier.py --csv > paper/data/runs_precise.csv
echo "== 4. runs.csv =="
python3 scripts/lab/gen_runs.py results/night paper/data/runs.csv | tail -3
echo "== 5. table1.csv（表 I 每一列含 Δ）=="
python3 scripts/lab/gen_table.py paper/data/runs.csv --csv paper/data/table1.csv | tail -2
echo "== 6. 重跑对照：判决变不变 =="
python3 scripts/lab/compare_rerun.py results/night \
    pois200_foyer_bres pois200_foyer_bres_r2 \
    pois200_foyer_hz0 pois200_foyer_hz0_r2 \
    pois200_foyer_hz2 pois200_foyer_hz2_r2 \
    pois200_foyer_breshz1 pois200_foyer_breshz1_r2 \
    pois200_cap1 pois200_cap1_r2 || true
echo "== 7. 不放行窗口审计（gen_stall.py 的 RUNS 也要跟着换名，重跑后核对 §V 的四个数）=="
python3 scripts/lab/gen_stall.py results/night paper/data/stall.csv | tail -4
echo "   ⚠ 若上面某条 _r2 的窗口数与正文写的不一样，改 §V 那段（判据在 gen_stall.py 顶部）"
echo "== 8. 自检 =="
python3 scripts/lab/check_paper_numbers.py | head -8
