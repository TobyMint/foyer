#!/bin/bash
# 从原始日志**重生成** paper/data/ 的全部 CSV，并与交付的那一份逐字节对拍。
#
# ## 为什么要有（Artifact Evaluation 的核心件）
#
# 论文里每个数都来自 paper/data/*.csv，而每张 CSV 都由 scripts/lab/gen_*.py 从
# `"$RESULTS"/` 的**原始逐步日志**算出。这条链此前**没有统一入口** ——
# 48 张表要靠人记得住哪一条先跑、带什么参数。本脚本把那条链写成一条命令。
#
# ## ⚠⚠ 铁律：**绝不写交付树**
#
# 2026-09-27 出过一次事故：一个审计脚本用「无参数」兜底调用触发了生成器的
# **硬编码输出路径**，把四张表写回了仓库。所以本脚本：
#   1. **先把 scripts/ + paper/ + data/ 拷进临时目录**，一切生成在那里发生；
#   2. `results/` **只读**（符号链接，本脚本从不写它）；
#   3. 结束时**只比不写**：diff 沙箱与交付树，然后删沙箱。
# ⇒ 无论本脚本怎么被误用，**交付树都不会变**。
#
# 用法:
#   bash regen_all.sh                 # 用默认 results 目录
#   TURNSTILE_RESULTS=/path/to/night bash regen_all.sh
#   bash regen_all.sh --keep          # 保留沙箱（排查用），会打印路径
set -u

REPO=$(cd "$(dirname "$0")/../.." && pwd)
# ⚠ 脚本自身的**绝对**路径：下面的覆盖面自检要 `grep` 自己，而脚本中途会 `cd` 进沙箱，
# 那时相对的 `$0` 已经解析不到了（第一版就栽在这里，报"文件不存在"⇒ 自检把**全部 45 张**
# 都当成"没被调用"，整条自检退化成永远报错）。
# ⚠ 2026-09-27（r59 中立复核）：`SELF` 现在已经**没有任何引用** ——
# 覆盖面自检从「grep 脚本文本」改成了**记账**（`MANAGED`）。留着这个变量会让
# 下一个人以为 grep 那版还在。**删掉。**（那条「$0 在 cd 后解析不到」的教训
# 已写在下面的自检注释里，不必靠一个没人用的变量记着。）
# SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")   ← 已删
RESULTS=${TURNSTILE_RESULTS:-$REPO/results/night}
P=${PYTHON:-python3}
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

if [ ! -d "$RESULTS" ]; then
    echo "!! 找不到 results 目录：$RESULTS"; exit 2
fi

SB=$(mktemp -d /tmp/regen_all.XXXXXX)
# ⚠⚠ 2026-09-27（r59 中立复核 3）：**两条守卫，都是「一次失败会写坏别处」的形状。**
#  ① `mktemp` 失败时 `$SB` 为空 ⇒ `cp -r … "$SB/"` 展开成 `cp -r … /`（**写根目录**），
#     且 `cd "$SB"` 失败后 cwd 不变 ⇒ 后面的 `rm -f paper/data/…` 打在**调用目录**上。
#     `set -u` 拦不住这个（变量是已定义的空串）。
#  ② `cp -r` **保留符号链接**：若 `paper/data` 是个符号链接，沙箱里的它就直接指向活树
#     ⇒ 下面的 `rm -f paper/data/X.csv` **删的是交付树里的文件**。复核者用硬链接探针
#     实测过：46/48 的目录项会被替换，而脚本照旧打印「交付树全程只读」、`rc=0`
#     （因为此时「沙箱」与「交付树」是同一个目录，成了**自我对拍**）。
#     ⚠ 当前仓库里 `paper/data` 是**真实目录**，所以现状安全 —— 但脚本里**没有一行在保证它**。
[ -n "$SB" ] && [ -d "$SB" ] || { echo "!! mktemp 失败，拒绝继续（\$SB='$SB'）"; exit 3; }
[ -L "$REPO/paper/data" ] && { echo "!! paper/data 是符号链接 —— 拒绝继续（沙箱会直接指向活树）"; exit 3; }
echo "== 沙箱 $SB（交付树 $REPO 全程只读）=="
cp -r "$REPO/scripts" "$SB/"
cp -r "$REPO/paper"   "$SB/"
cp -r "$REPO/data"    "$SB/"
ln -s "$(dirname "$RESULTS")" "$SB/results"   # ⇒ $SB/results/<basename> == $RESULTS
cd "$SB"

FAILED=""
# 每个生成器跑完记一笔（成功/失败），末尾汇总 —— **不许静默跳过**
# ⚠⚠⚠ 2026-09-27（r58 codex 复核 5）：**这个包装器原来有一条假通过通道。**
# 原写法只判「命令退出码为 0」—— 于是**一个成功退出却不写文件的生成器照样印 `ok`**，
# 而沙箱里那份**是拷贝进来的交付版**，对拍自然全过。
# codex 构造实测：把 `gen_slope.py` 改成 rc=0 但不写文件，再把交付副本的斜率改成
# **−999.9** ⇒ 脚本仍报 `ok slope`、**48/48、退出码 0**。
#
# ⇒ 判据改成**两条都要满足**：① 生成器 rc=0；② **目标文件真的被写出来了**
#   （做法：**先删掉沙箱里那一份**，跑完检查它存在且非空）。
#   ⚠ 输出必须**显式给出** —— 我第一版想「从 argv 里猜哪个是输出」，
#     而 `gen_reuse.py ... <out.csv> <concurrency.csv>` 的**最后一个** csv 是**输入**
#     ⇒ 猜错了、把输入删了。**判据不许猜。**
# ⚠ `out` 可以是**逗号分隔的多个文件**（`idle_segments.py` 一次写两张）。
run() {
    local name="$1" outs="$2"; shift 2
    local IFS=','; local missing=""
    for o in $outs; do rm -f "paper/data/$o"; MANAGED="$MANAGED $o"; done   # ← 先删，逼生成器自己写出来
    unset IFS
    if "$@" >/tmp/regen_$name.log 2>&1; then :; else
        printf "  !!   %s（命令失败，见 /tmp/regen_%s.log）\n" "$name" "$name"
        FAILED="$FAILED $name"; return
    fi
    local IFS=','
    for o in $outs; do [ -s "paper/data/$o" ] || missing="$missing $o"; done
    unset IFS
    if [ -n "$missing" ]; then
        printf "  !!   %s（**没有写出**%s，见 /tmp/regen_%s.log）\n" "$name" "$missing" "$name"
        FAILED="$FAILED $name(未写出)"
    else
        printf "  ok   %s\n" "$name"
    fi
}

# 冻结输入：**明列为「不重建」**，因此既不计入重建数、也不掩盖对拍
FROZEN=""
NFROZEN=0
MANAGED=""      # 受 `run` 管理的输出（覆盖面对账用，见末尾自检）
frozen() {
    local name="$1" f="$2"
    cp "$REPO/paper/data/$f" "paper/data/$f"
    printf "  --   %s（**冻结输入，不重建**）\n" "$name"
    FROZEN="$FROZEN $name"; NFROZEN=$((NFROZEN + 1))
    MANAGED="$MANAGED $f"
}


# ---------------------------------------------------------------- run 列表复原
# ⚠ 多个生成器的 run 列表是 `sys.argv[3:]`、**脚本内无默认值**（CLAUDE.md:306 记着这件事），
#   所以「不传就对了」是错的 —— 不传会退化成「扫全目录」，产出 170 行而不是 39 行。
#
# **复原办法（2026-09-27 实测有效）**：生成器是**按 argv 顺序**追加行的，
#   所以交付 CSV 的**行序就是当初的 argv 顺序**；而 `run` 列是**目录名去掉
#   `pois200_` 前缀**后的样子。于是：取交付 CSV 的 run 列（保序）、
#   逐个在 results 里找一个存在的目录（原名优先，其次加 `pois200_` 前缀）。
#   实测：`decomp.csv` 用这个列表跑出来**逐字节相同**。
#
# ⚠⚠ **这条复原法有一条循环性，必须写明**（r58 中立复核 5 指出）：
#   既然 run 列表是**从被验的交付 CSV 自己**反推的，那么「逐字节相同」证明的是
#   **「同样的输入 ⇒ 同样的输出」**，它**抓不到**「当初那份 run 列表本身就是错的/不全的」。
#   那一类由**生成器自己的 `_derive` 自检**承担（例如 `gen_eviction.py` 会报
#   「host-tier 集合与判据不一致」）—— 两边合起来才是完整的。
#   **不许把这条对拍当成「run 列表正确」的证明。**
recover_runs() {   # $1 = paper/data 里的 csv 名（不含扩展名）
    $P - "$REPO/paper/data/$1.csv" "$RESULTS" <<'PYEOF'
import csv, os, sys
csv_p, root = sys.argv[1], sys.argv[2]
rows = [l for l in open(csv_p, encoding="utf-8") if not l.startswith("#")]
names = [r["run"] for r in csv.DictReader(rows) if r.get("run")]
seen, out, bad = set(), [], []
for n in names:
    if n in seen:
        continue
    seen.add(n)
    for cand in ("pois200_" + n, n):   # ⚠ `pois200_` **优先**：裸名可能与别的族同名（`cap4` 目录真的存在）
        if os.path.isdir(os.path.join(root, cand)):
            out.append(cand); break
    else:
        bad.append(n)
if bad:
    sys.stderr.write("!! 复原不出这些 run 的目录：%s\n" % bad[:8])
    sys.exit(1)
sys.stdout.write(" ".join(out))
PYEOF
}

# ---------------------------------------------------------------- L0：只吃原始日志
# （生成器内部有各自的 run 名单/筛选；**不传 run 列表** = 用它们自己的默认，
#   这正是当初产出交付版 CSV 的方式）
echo "== L0：原始日志 -> CSV =="
run arm_running arm_running.csv     $P scripts/lab/gen_arm_running.py     "$RESULTS" paper/data/arm_running.csv
run runs runs.csv            $P scripts/lab/gen_runs.py            "$RESULTS" paper/data/runs.csv
run occupancy occupancy.csv       $P scripts/lab/gen_occupancy.py       "$RESULTS" paper/data/occupancy.csv
run eviction eviction.csv        $P scripts/lab/gen_eviction.py        "$RESULTS" paper/data/eviction.csv
# ⚠⚠ **`concurrency.csv` 是【冻结输入】，不重生成**（2026-09-27 实测）。
# 它是「哪些 run 在时间上重叠过」的**共租审计**，判据是**当时那台机器上的目录快照**：
# 换一个快照（本地 199 个目录 vs 实验机 555 个）就会得到**不同的重叠加",
# 于是 `contested` 旗标变化，而 `reuse` / `table1` / `attribution` 全都吃这一列 ——
# 实测：喂回交付版 concurrency.csv，这三张**立刻逐字节复现**（否则各有 9/9/3 个单元格不同）。
# ⇒ 把它当**输入**（与 trace 同级）交付，并在这里显式说明它不参与重生成。
# 这也符合它本身的语义：共租是一次**历史测量**，不是从当前状态能重算出来的量。
frozen concurrency concurrency.csv
# runs -> runs_precise（frontier.py --csv）-> table1（gen_table.py --csv）
echo "== L2：表链 =="
rm -f paper/data/runs_precise.csv
MANAGED="$MANAGED runs_precise.csv"
if env TURNSTILE_RESULTS="$RESULTS" $P scripts/lab/frontier.py --csv > paper/data/runs_precise.csv 2>/tmp/regen_runs_precise.log && [ -s paper/data/runs_precise.csv ]; then
    printf "  ok   %s\n" runs_precise
else
    printf "  !!   %s\n" runs_precise; FAILED="$FAILED runs_precise"
fi
run table1 table1.csv          $P scripts/lab/gen_table.py paper/data/runs.csv --csv paper/data/table1.csv

run decomp decomp.csv          $P scripts/lab/gen_decomp.py          "$RESULTS" paper/data/decomp.csv $(recover_runs decomp)
run backlog backlog.csv         $P scripts/lab/gen_backlog.py         "$RESULTS" paper/data/backlog.csv $(recover_runs backlog)
run arrival_slo arrival_slo.csv     $P scripts/lab/gen_arrival_slo.py     "$RESULTS" paper/data/arrival_slo.csv
run hitrate hitrate.csv         $P scripts/lab/gen_hitrate.py         "$RESULTS" paper/data/hitrate.csv $(recover_runs hitrate)
run reuse_x reuse_x.csv         $P scripts/lab/gen_reuse_x.py         data/replay_realhr.csv "$RESULTS" paper/data/reuse_x.csv $(recover_runs reuse_x)
# ⚠ `gen_toolwait.py` 的**模块 docstring 是错的**（写的是 `<trace> <results_dir> <out.csv> <run>...`），
#   实现（main 的 docstring + 第 86-91 行）是 `<root> <out.csv> <trace.csv>:<run> ...`。
#   run 列表取自交付的 toolwait.csv 自身（两条 trace 各带自己的 run）。
run toolwait toolwait.csv        $P scripts/lab/gen_toolwait.py        "$RESULTS" paper/data/toolwait.csv \
                        data/replay_pois200_l04.csv:pois200_foyer_hc \
                        data/replay_pois200_l04.csv:pois200_cap1 \
                        data/replay_realhr.csv:realhr_cap2 \
                        data/replay_realhr.csv:realhr_cap4 \
                        data/replay_realhr.csv:realhr_foyer
run stall stall.csv           $P scripts/lab/gen_stall.py           "$RESULTS" paper/data/stall.csv
run superseded superseded.csv      $P scripts/lab/gen_superseded.py      "$RESULTS" paper/data/superseded.csv
run replicates replicates.csv      $P scripts/lab/gen_replicates.py      "$RESULTS" paper/data/replicates.csv
run repeat_spread repeat_spread.csv   $P scripts/lab/gen_repeat_spread.py   "$RESULTS" paper/data/repeat_spread.csv
run budget_sweep budget_sweep.csv    $P scripts/lab/gen_budget_sweep.py    "$RESULTS" paper/data/budget_sweep.csv
run nocontrol nocontrol.csv       $P scripts/lab/gen_nocontrol.py       "$RESULTS" paper/data/nocontrol.csv
run pool50 pool50.csv          $P scripts/lab/gen_pool50.py          "$RESULTS" paper/data/pool50.csv
run tierpair tierpair.csv        $P scripts/lab/gen_tierpair.py        "$RESULTS" paper/data/tierpair.csv
run tau2_windows tau2_windows.csv    $P scripts/lab/gen_tau2_windows.py    "$RESULTS" paper/data/tau2_windows.csv
run slice23 slice23.csv         $P scripts/lab/gen_slice23.py         "$RESULTS" paper/data/slice23.csv
run elasticity_x elasticity_x.csv    $P scripts/lab/gen_elasticity_x.py    "$RESULTS" paper/data/elasticity_x.csv
# ⚠ 2026-09-27（r59 中立复核 9）：**这里原来也有一行 `run projection`**，
# 于是它先被重生成、再被下面的 `frozen` 用交付版覆盖 —— MANAGED 里登记了**两次**。
# 副作用：`gen_projection.py` 一旦失败，一张「明列冻结、声明不重建」的表也会报 `!!`
# 并把 rc 拉成 1。而「不重建」应当是**靠不调用**实现，不是靠覆盖。**已删掉这一行。**
# ⚠ `gen_projection_sat.py` 的输出 `paper/data/projection_sat.csv` **不在交付的 48 张里**
#   （它不是论文引的表）。跑它只为确认它仍能跑通；产物不参与对拍。
run projection_sat projection_sat.csv $P scripts/lab/gen_projection_sat.py "$RESULTS"
run aimd_stall aimd_stall.csv      $P scripts/lab/gen_aimd_stall.py      "$RESULTS" paper/data/aimd_stall.csv
run tier25 tier25.csv          $P scripts/lab/gen_tier25.py          "$RESULTS" paper/data/tier25.csv
run tier25_old tier25_old.csv      $P scripts/lab/gen_tier25_old.py      "$RESULTS" paper/data/tier25_old.csv
# ⚠⚠ 这两张与 `concurrency` **同族**：内容取决于**生成时刻的目录/完成状态**，不是当前状态能重算的量。
#   · `gate_attrib`：代码注释自己写着「**必须在实验机上跑** —— 本表统计【所有】带
#     `controller.jsonl` 的 run，**本地镜像是部分快照**（2026-09-24 实测：本地 34 行 vs 实验机 46 行）」。
#   · `projection`：交付版**只排除 `load25c_budget3_sf0` 一条** —— 因为 `_done()` 筛
#     「**跑完了的** run」，而它是在那之后才跑完的。
#   ⇒ 与 concurrency 一样当**冻结输入**。**不重生成**，但仍在下面参与对拍。
frozen gate_attrib gate_attrib.csv
frozen projection  projection.csv
run a100_baseline a100_baseline.csv   $P scripts/lab/gen_a100_baseline.py   "$RESULTS" paper/data/a100_baseline.csv
run a100 a100.csv,a100_elasticity.csv $P scripts/lab/gen_a100.py            data/replay_pois200_l04.csv "$RESULTS" "$RESULTS" paper/data/a100.csv

# ---------------------------------------------------------------- L0b：四条无参数的
# ⚠ 这四个**不接受参数**、输出路径硬编码在源码里（`out = os.path.join(ROOT,...)`）——
#   就是 2026-09-27 那次事故里被误写的四个。本脚本在**沙箱**里跑它们，所以安全。
echo "== L0b：无参数生成器（输出路径硬编码，故必须在沙箱里跑）=="
run elasticity_hc elasticity_hc.csv   $P scripts/lab/gen_elasticity_hc.py
run frontier_split frontier_split.csv  $P scripts/lab/gen_frontier_split.py
run prefill_share prefill_share.csv   $P scripts/lab/gen_prefill_share.py
run wall_split wall_split.csv      $P scripts/lab/gen_wall_split.py

# ⚠⚠ 2026-09-27（r58 中立复核 5，**哨兵法证明**）：`idle_seg.csv` / `idle_seg_raw.csv` /
# `slo_sensitivity.csv` **此前从头到尾没被调用过** —— 而它们被计进了「逐字节相同」。
# 哨兵（在沙箱副本末行写 `313131`）在跑完后**原样存活**。这正是本项目
# 「检查数掉了没人发现」的同族：**一项检查/一个步骤没跑，计数上却看不出来**。
# ⇒ 补上这两个生成器（`idle_segments.py` **一次写两张**）。
run idle_segments idle_seg.csv,idle_seg_raw.csv $P scripts/lab/idle_segments.py "$RESULTS" paper/data/idle_seg.csv
run slo_sensitivity slo_sensitivity.csv $P scripts/lab/slo_sensitivity.py "$RESULTS" paper/data/slo_sensitivity.csv

# ---------------------------------------------------------------- L1：吃别的 CSV
echo "== L1：CSV -> CSV =="
run elasticity elasticity.csv      $P scripts/lab/gen_elasticity.py      paper/data/decomp.csv paper/data/elasticity.csv
run attribution attribution.csv     $P scripts/lab/gen_attribution.py     paper/data/runs.csv paper/data/occupancy.csv paper/data/decomp.csv paper/data/attribution.csv
run reuse reuse.csv           $P scripts/lab/gen_reuse.py           data/replay_pois200_l04.csv paper/data/eviction.csv paper/data/arm_running.csv paper/data/decomp.csv paper/data/reuse.csv paper/data/concurrency.csv
run fit fit.csv             $P scripts/lab/gen_fit.py             paper/data paper/data/fit.csv
run slope slope.csv           $P scripts/lab/gen_slope.py           paper/data/reuse.csv paper/data/reuse_x.csv paper/data/slope.csv
run idle_pooled idle_pooled.csv     $P scripts/lab/gen_idle_pooled.py     paper/data/idle_seg_raw.csv paper/data/concurrency.csv paper/data/idle_pooled.csv
# ⚠ `gen_a100_delta.py` 的输出必须用 `--csv <out>` 显式给（它默认只印到终端），
#   且 `--contested` **必须显式声明**（脚本自己说「不许在这里猜」：gpu_watch.jsonl
#   不在本地镜像里）。run 列表取自交付的 a100_delta.csv 自身。
run a100_delta a100_delta.csv $P scripts/lab/gen_a100_delta.py paper/data/a100.csv "$RESULTS" \
    --csv paper/data/a100_delta.csv --contested a100_default \
    a100_foyer_hz2 a100_default

# ---------------------------------------------------------------- L2：表链
# ⚠⚠ 2026-09-28：`runs_precise` 与 `table1` 的生成**已上移到 `frozen concurrency`
# 之后** —— 因为 `arrival_slo`（上面）**读 table1.csv**，而它原来排在第 252 行才重建
# ⇒ 真重生成时它读到的是**上一版** table1（codex r66 第 3 条；AE 场景下无害，
# 因为交付版 table1 本来就对，所以 48/48 照样逐字节相同）。
run horizon horizon.csv         $P scripts/lab/gen_horizon.py         paper/data/table1.csv paper/data/horizon.csv
run loadtier loadtier.csv        $P scripts/lab/gen_loadtier.py        "$RESULTS" paper/data/table1.csv paper/data/loadtier.csv

# ---------------------------------------------------------------- 对拍
echo
echo "===================== 逐字节对拍（沙箱 vs 交付树）====================="
cd "$SB/paper/data"
same=0; diffn=0; only_sb=0; only_del=0; commentonly=0; DIFFS=""
for f in *.csv; do
    # ⚠⚠ 2026-09-27（r59 codex 复核 2）：**这里原来是无条件跳过。**
    # `projection_sat.csv` 不在交付的 48 张里，所以对拍要跳过它 —— 但**无条件跳过**
    # 意味着：**如果它哪天出现在交付树里（哪怕内容是错的），比对照样跳过**，
    # 而覆盖面自检又把它算作「受管理」⇒ 一路 48/48、退出 0。
    # codex 构造：交付一份 31 字节的 `projection_sat.csv`（生成版是 2473 字节）⇒ **仍报 48/48**。
    # ⇒ 判据改成：**只有当交付树里没有它时才跳过**；有就照常比。
    # ⚠⚠ 2026-09-27（r60 codex 构造）：**判据不能只用 `-f`。**
    # `-f` **会跟随符号链接** ⇒ 交付树里一个**悬空**的 `projection_sat.csv`
    # （指向不存在的目标）对它来说「不是文件」⇒ **又跳过了**，脚本照报 48/48、rc=0。
    # ⇒ 必须同时看 `-e`（跟随）与 `-L`（不跟随）：**链接存在也算「交付树里有」**。
    if [ "$f" = "projection_sat.csv" ] && [ ! -e "$REPO/paper/data/$f" ] \
       && [ ! -L "$REPO/paper/data/$f" ]; then continue; fi
    d="$REPO/paper/data/$f"
    if [ ! -f "$d" ]; then
        printf "  只有沙箱有  %s\n" "$f"; only_sb=$((only_sb+1)); DIFFS="$DIFFS $f(仅沙箱)"
    elif cmp -s "$f" "$d"; then
        same=$((same+1))
    elif diff -q <(grep -v '^#' "$f") <(grep -v '^#' "$d") >/dev/null; then
        printf "  仅注释不同  %s（内容是逐字节相同的）\n" "$f"; commentonly=$((commentonly+1))
    else
        n=$(diff <(grep -v '^#' "$f") <(grep -v '^#' "$d") | grep -c '^[<>]')
        printf "  不一致      %s（%s 行不同）\n" "$f" "$n"
        diffn=$((diffn+1)); DIFFS="$DIFFS $f"
    fi
done
for f in "$REPO"/paper/data/*.csv; do
    b="${f##*/}"
    [ -f "$b" ] || { printf "  只有交付树有  %s\n" "$b"; only_del=$((only_del+1)); }
done
echo "---------------------------------------------------------------------"
echo "  逐字节相同 $same ｜ 仅注释不同 $commentonly ｜ 内容不一致 $diffn ｜ 仅沙箱 $only_sb ｜ 仅交付树 $only_del"
# ⚠⚠⚠ **覆盖面自检**（r58 中立复核 5 用哨兵法抓到的那一类）。
# 判据：**交付的每一张 CSV，都必须是被 `run` 管理过的输出、或被明列为冻结**。
# 为什么必须有：一张表如果**根本没被任何 `run` 调用到**，它在沙箱里就一直是
# **拷贝进来的交付版** ⇒ 对拍必然「逐字节相同」⇒ 被计进重建数。
# 2026-09-27 哨兵法实测：`idle_seg.csv` / `idle_seg_raw.csv` / `slo_sensitivity.csv`
# 三张**从未被调用**，哨兵原样存活，而计数把它们算成了「重建成功」。
#
# ⚠ 判据**用记账、不 grep 脚本文本**：第一版是 `grep -q "paper/data/$f" "$SELF"`，
#   (a) 脚本中途 `cd` 进沙箱后相对的 `$0` 解析不到（退化成永远报错），
#   (b) 无参数生成器的调用行里没有 `paper/data/` 前缀 ⇒ 4 张**假报**。
#   **记账不受脚本措辞影响。**
# ⚠⚠⚠ 2026-09-28（r65 codex 复核 8）：**这一段原来靠 `ls`** ——
# `for f in $(cd … && ls *.csv)`。在**缺 `ls` 的最小 PATH** 下，命令替换取到**空**，
# 循环体一次都不跑 ⇒ `COVER` 永远为空 ⇒ **「既没重建也没冻结」的那张表不被发现**，
# 脚本照报 49/49、**退出 0**（codex 实测；补回 `ls` 后同一构造报错退出 1）。
# ⇒ 判据：**用纯 bash 展开**（不依赖 `ls`/`basename`/`wc`），并**断言枚举非空** ——
#    「什么都没枚举到」必须报，不能算通过。
COVER=""; NDEL=0
for f in "$REPO"/paper/data/*.csv; do
    [ -e "$f" ] || continue
    f="${f##*/}"
    NDEL=$((NDEL+1))
    case " $MANAGED " in *" $f "*) ;; *) COVER="$COVER $f";; esac
done
if [ "$NDEL" -eq 0 ]; then
    echo "  !! 交付树的 CSV **一张都没枚举到**（$REPO/paper/data）—— 覆盖面判据空转，拒绝通过"
    FAILED="$FAILED 覆盖面空转"
fi
if [ -n "$COVER" ]; then
    echo "  !! 这些交付的 CSV **既没有被重建、也没有被明列为冻结**：$COVER"
    FAILED="$FAILED 覆盖面"
fi
echo "  ⚠ 口径：$same 张是【沙箱重建后逐字节相同】，其中含冻结输入（$FROZEN ）——"
echo "     冻结的那些是【拷进来的交付版】，不证明能从当前日志重建。真实的【重建】张数 = $((same - NFROZEN))。"
if [ -n "$FAILED" ]; then echo "  ⚠ 生成失败的生成器：$FAILED"; fi
if [ -n "$DIFFS" ]; then echo "  ⚠ 对不上的表：$DIFFS"; fi

# ---------------------------------------------------------------- 沙箱
if [ "$KEEP" = 1 ]; then echo "  沙箱保留在 $SB"; else rm -rf "$SB"; fi
# ⚠⚠ 2026-09-27（r58 codex 复核 5）：退出条件原来**漏了 `commentonly`** ——
# codex 构造：只改交付 `elasticity.csv` 的一行注释，脚本报 47 同 / 1「仅注释不同」、
# **仍然退出 0**。而「逐字节相同」这个声称包含注释 ⇒ 注释不同也是**没复现**。
# ⇒ `commentonly` 计入失败。（对拍那段仍把它单列，是为了**看得见**差在哪。）
[ -z "$FAILED" ] && [ "$diffn" = 0 ] && [ "$commentonly" = 0 ] && [ "$only_sb" = 0 ] && [ "$only_del" = 0 ]
