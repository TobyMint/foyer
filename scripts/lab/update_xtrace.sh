#!/bin/bash
# 第二条 trace（realhr）扫描落地后的更新流水线 —— 一条命令跑完，别手抄。
#
# 用法: bash scripts/lab/update_xtrace.sh
#
# 前提：realhr_cap8 / realhr_cap4_r2 / realhr_foyer_r2 都已写出 summary.json。
# 本脚本会先把 realhr_* 目录 rsync 下来，再按依赖顺序重生成三张数据文件。
set -e
cd "$(dirname "$0")/../.."
echo "== 1. 同步 realhr_* 目录 =="
rsync -a --include='realhr_*/' --include='realhr_*/**' --exclude='*' \
      lab-3090:/data/xbw/turnstile/results/night/ results/night/
echo "== 2. reuse_x.csv（gen_reuse_x.py 的 RUNS 是显式的，缺 run 会报出来）=="
python3 scripts/lab/gen_reuse_x.py data/replay_realhr.csv results/night paper/data/reuse_x.csv
echo "== 3. elasticity_x.csv（FAMILIES 已含 cap2..cap8）=="
python3 scripts/lab/gen_elasticity_x.py results/night paper/data/elasticity_x.csv
echo "== 4. slope.csv（两条 trace 的逐段与全范围斜率）=="
python3 scripts/lab/gen_slope.py paper/data/reuse.csv paper/data/reuse_x.csv paper/data/slope.csv
echo "== 4b. 第二条 trace 的重复对（cap4/cap4_r2 与 foyer/foyer_r2）=="
python3 - <<'PY2'
import csv, importlib.util
spec=importlib.util.spec_from_file_location("_fr", "scripts/lab/frontier.py")
FR=importlib.util.module_from_spec(spec); spec.loader.exec_module(FR); FR.RESULTS="results/night"
rx={r["run"]: r for r in csv.DictReader(l for l in open("paper/data/reuse_x.csv") if not l.startswith("#"))}
for a,b in (("realhr_cap4","realhr_cap4_r2"),("realhr_foyer","realhr_foyer_r2")):
    if a in rx and b in rx:
        da=abs(float(rx[a]["realized_frac"])-float(rx[b]["realized_frac"]))*100
        wa=FR.summarise(a); wb=FR.summarise(b)
        print("   %-28s 兑现差 %.2f 点  墙钟差 %.2f%%" % (a+" vs "+b, da,
              100*abs(wa["wall"]-wb["wall"])/wa["wall"] if wa and wb else float("nan")))
    else:
        print("   %s vs %s 还缺一条" % (a,b))
print("   ⚠ §VI 的「八倍散布」用的是 cap4 那对的 1.7%；若控制器那对的散布大得多，要改那句话")
PY2
echo "== 5. 自检 =="
python3 scripts/lab/check_paper_numbers.py | head -6
