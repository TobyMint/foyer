# 落地清单：`pois200_foyer_scan_r2` 与 `pois200_foyer_sf0_r3`

写于 2026-09-27 06:40，两条 run 落地**之前**。目的是让落地那一刻不用重新推导
「哪些生成器名单要加 run」——**名单漏一个是本项目栽过三次的错**（生成器静默改口径）。

两条 run 的**跑前预期**分别写在实验机上：
`/data/xbw/turnstile/scripts/lane_scan_r2.sh` 与 `lane_sf0_r3.sh` 的头部
（三种结果各自的处置，**照抄，不许事后挑说法**；本地无副本）。

---

## 〇、先确认「真的跑完了」

```bash
timeout 90 ssh lab-3090 'for n in pois200_foyer_scan_r2 pois200_foyer_sf0_r3; do
  printf "%-26s summary=%s steps=%s\n" "$n" \
    "$( [ -f /data/xbw/turnstile/results/night/$n/summary.json ] && echo YES || echo no )" \
    "$( wc -l < /data/xbw/turnstile/results/night/$n/steps.jsonl )"; done'
```

**两条都必须 `summary=YES` 才能往下走。** 判据是 `summary.json` 存在 ——
这是全项目统一的「跑完」定义（`frontier.py:145`、`gen_concurrency.py`、
`gen_repeat_spread.py:108` 都用它）。在跑时 `steps.jsonl` 也会在长，
按行数判断会误判成跑完。

### ⚠ 回本地镜像时只拷跑完的

```bash
rsync -a --include='*/' --include='summary.json' --include='steps.jsonl' \
      --include='controller.jsonl' --include='admissions.jsonl' --include='metadata.json' \
      --include='*.csv' --exclude='*' lab-3090:/data/xbw/turnstile/results/night/ results/night/
```

**本地镜像里此刻没有这两条**（72 个目录 / 64 有 summary）。若把在跑的目录拷进来，
本地那些**没有 `summary.json` 护栏**的生成器（`gen_decomp.py` 走显式名单，
但 `gen_replicates.py` 读时间戳就能算出「部分窗口」）会把它算成一个**会自己变化的事实**。

---

## 一、必须加进「run 名单」的地方（缺一个就静默改口径）

> ✅ **这一节已经做成了脚本：`python3 scripts/lab/apply_landing_edits.py`**
> （先干跑，确认 8 处都不失败，再加 `--apply`）。
> 脚本在沙箱里实测过：8 处锚点**全部唯一**、改完语法有效、**幂等**（重复跑会 `跳过`）、
> 八处名单都确实含两条。**不用手改** —— 手改八处就是八次机会。
> ⚠ 下面这张表仍然保留，用来**核对**脚本的覆盖面（脚本的 `EDITS` 列表要与它一致）。

> ⚠⚠ **本节第一版是错的，2026-09-27 06:36 重写。** 第一版只列了 4 处
> （`gen_runs` / `gen_table` / `gen_arm_running` / `gen_stall`）——
> 而**清单本身就是「名单漏一个」那一族**。用探针法重扫才补全：
> 拿**最近加入的那条臂**（`foyer_hz2_r3`）去 `grep`，
> **它出现过的每一处，就是新臂也要加的地方**。
> 规矩记在 CLAUDE.md：**列「要改哪些名单」时，不许靠回忆，要用一条已知的新 run 当探针扫全仓。**

| 文件 | 名单 / 位置 | 加什么 |
|---|---|---|
| `scripts/lab/gen_runs.py` | `ROWS`（第 22 行起） | `foyer_scan_r2 200 foyer`、`foyer_sf0_r3 200 foyer` |
| `scripts/lab/gen_table.py` | `LABEL`（第 26 行起） | `"foyer_scan_r2": "scans the queue (2nd run)"`、`"foyer_sf0_r3": "single-flight off (2nd run)"` |
| `scripts/lab/gen_arm_running.py` | `ARMS`（第 28 行起） | 两条都加（**不进 `NINE`** —— NINE 是「九条变体」的定义） |
| `scripts/lab/gen_stall.py` | `RUNS`（第 41 行起） | `"pois200_foyer_scan_r2"`、`"pois200_foyer_sf0_r3"` |
| `scripts/lab/gen_eviction.py` | `RUNS`（第 101 行起） | ⚠⚠ **不只是"加两条"** —— 见下面的专条 |
| `scripts/lab/slo_sensitivity.py` | `RUNS`（第 13 行起） | 两条都加 —— 否则 §VI 阈值表里这两条臂**没有 5s/20s 列** |
| `scripts/lab/gen_arrival_slo.py` | `RUNS`（第 42 行起） | 两条都加。注释里写着 `sf0_r2` 入表就是因为「**漏掉最接近的那条，稳健性论证不完整**」—— 重复同属此列 |
| `scripts/lab/gen_occupancy.py` | `RUNS`（第 19 行起） | 两条都加 |
| `scripts/lab/check_paper_numbers.py` | 第 1165 行附近的 `_C11` | **不用改** —— 它是 `sorted(k for k in arrival_slo.csv ...)`，从数据现算。但它**上游是 `gen_arrival_slo.py` 的 `RUNS`**，那一处不加，这里就永远看不到新臂 |

### ⚠⚠ `gen_eviction.py`：落地后集合会从 26 变 28，正文六处要改

2026-09-27 06:44 修掉了一个**判据太粗**的错：`pois200_slice23_hc`（时间片切换实验）
满足机械判据但不是静态配置，导致判据在实验机上给 **27** 而 `RUNS` 是 26，
生成器**在实验机上直接报错退出**。已加 `NOT_SINGLE_CONFIG` 类别修好（⚠ 文档此处一度写 `NOT_STATIC`，与代码不符，已改）（机器上实测
`判据重算：host-tier 26 条`、`rc=0`）。

**但同一段输出里还有一行**：

```
未达 995 步被排除 9 条 … foyer_scan_r2(876) foyer_sf0_r3(866) …
```

⇒ 这两条**是主 trace、是 HiCache**，落地后就会**进入判据集合** ⇒
判据变成 **28**、`RUNS` 若不加就再次报错。

**所以落地时这一处要做三件事**（不是一件）：

1. `RUNS` 加 `foyer_scan_r2`、`foyer_sf0_r3`（否则判据自检直接退出）；
2. 正文**六处**的「twenty-six host-tier runs」要变成 **twenty-eight**
   （`sec_model.tex:152/192/274/279/281`、`sec_discussion.tex:329` —— 行号会漂，按 `grep -n "twenty-six"` 找）；
3. **重算那两个拟合量**：`sec_model.tex:281` 的 `$r=+0.85$ with a largest
   residual of 1.92\,ms` —— 它是这 26 条拟合出来的，集合一变数就变
   （中立复核按 27 条算过：r=0.8546、max|res|=1.9432 ⇒ 会印成 **1.94**；
   28 条要重跑脚本）。⚠ 这条**目前没有守卫**，要手动核。

**这些生成器缺目录会 `raise SystemExit`（不静默跳过）**，所以只能在落地后加。

**不要**加进 `gen_attribution.py` 的 `ARMS` —— 那张表是「一配置一代表」，
重复 run 不进去（`gen_attribution.py:26` 的注释明写了 `foyer_hz2_r3` 不加）。

`gen_decomp.py` / `gen_hitrate.py` 的 run 列表在**命令行上**，照 `swap_superseded.py`
的 `REGEN` 那几行的写法加即可。

⚠ **加完要问一遍**：这些集合里有没有哪一个是正文引了**条数**的？
（「twenty-six host-tier runs」「thirty-one runs」「fifteen controller arms」…）
条数变了就得回去改正文，而那些条数**大多有守卫**（`ck_near` + `num_words`），
检查器会报 —— 但**先知道要找什么，比等它报要快**。

---

## 二、会**自动**变的派生量（我不动手，生成器算）

- `paper/data/replicates.csv`：**已预先登记**两个新组（`gen_replicates.py` 的 `GROUPS`）：
  - `"scans the queue": ["foyer_scan", "foyer_scan_r2"]`
  - `"single-flight off": ["foyer_sf0_r2", "foyer_sf0_r3"]`
  落地前每组只有 1 条有效 run ⇒ 自动跳过。落地后自动生效。
- 图 1 的标注条数 `_n_rep`（`paper/figs/make_figs.py:216`，从 `table1.csv` 现数）。

---

## 三、**必须手改**的正文（检查器盯着的三处，落地后一定过期）

| 位置 | 现在写的 | 为什么必须改 |
|---|---|---|
| `paper/sec_results.tex:39` | `and this arm has been run once` | scan 臂变成两次读数 |
| `paper/sec_discussion.tex:194` | `and which has been run once` | 同上 |
| `paper/sec_discussion.tex:199` | `Every crossing in this table that no repeat checks is that one arm's.` | 重复落地后这句不再成立 |

### ⚠⚠ 有两个「26」，是**两个不同的集合** —— 别一起改

| 处 | 集合 | 现在 | 落地后 |
|---|---|---|---|
| `sec_model.tex` ×5 + `sec_discussion.tex:330` | **host-tier 集合**（主 trace + HiCache + ≥995 步） | 26 → **28** | 见上面的 `gen_eviction.py` 专条 |
| `sec_discussion.tex:209` | **ready 时钟子集**（`arrival_slo.csv` ∩ 表 I） | 「26 of the **33**」→ **「28 of the 35」** | 分母是**表 I 在 LaTeX 里印的行数** |

⚠⚠ **第二个的「分母」不是 `table1.csv` 的行数。** `table1.csv` 是**超集**：
`pairA_cap2hc` 与 `aimd2_paper` 在 CSV 里但**不印在表 I 里**。
2026-09-27 我按 CSV（35 行）算，得出「分母应 35、分解应 5+3」，
**差点把一句本来正确的话改错** —— 拦下我的是那条**我 grep 不到**的守卫
（它把期望值现算成 `"%s of the %s"`，源码里没有字面串）
报出「twenty-six of the thirty-three」。原文「33 / 1+4+2」**逐条正确**。

**落地后这句怎么变**（用守卫现算验证，别手推）：
- 分母 33 → **35**（两条新臂进表 I）；
- 分子 26 → **28**（两条也进 `arrival_slo.csv`，因为清单第一节会把它们加进
  `gen_arrival_slo.py` 的 `RUNS`）；
- 分解**不变**（`four` host-tier + `two` controller repeats）——
  新来的两条是**在**子集里的，不进排除名单。

⇒ 正确的落地结果：**「twenty-eight of the thirty-five」**，分解仍为 four/two。
跑完检查器应当 **0 MISS**；`§VI ready 子集排除的 host-tier 条数` 与
`控制器重复条数` 两条守卫（2026-09-27 新加，口径是 `_tex` 不是 CSV）会验它。

### ⚠ 还有两处**检查器不一定抓得到**的（要自己算）

1. `paper/sec_results.tex:36-39` 与 `paper/sec_discussion.tex:193`：
   「the `$0.5$ to $4.6$\,pp` that separates repeats of a single configuration」/
   「the tightest of **the three groups** at `$0.5$\,pp`」。
   新组进来就是**第四、第五组**，而且 `scan`/`scan_r2` 这一对的 Δ 全距
   **极可能把上界推得比 4.6 更高**（scan 是 +1.30）。三处数字（下界、上界、组数）
   都要按新的 `replicates.csv` 重算。
2. 摘要（`paper/main.tex` 的 `abstract`，**词数上限 265**）里的
   「nine controller variants … none above … A tenth arm … on one run … so unresolved」
   —— 若重复**复现**了越线，这句要升级；若**没复现**，要写明「一次读数曾越过、
   重复反驳了它」。改摘要**必须重新数词**。

---

## 四、落地后按顺序跑（`swap_superseded.py` 的 `REGEN` 是权威顺序）

```
gen_runs → frontier --csv → gen_table → gen_occupancy → gen_decomp → gen_arm_running
→ gen_hitrate → gen_eviction → gen_reuse → gen_attribution → idle_segments
→ gen_idle_pooled → gen_stall → slo_sensitivity → gen_replicates → gen_repeat_spread
```

**机器端四条**（`gen_concurrency` / `gen_gate_attrib` / `gen_projection` /
`gen_repeat_spread`）必须在 `lab-3090` 上跑 —— `gen_concurrency.py` 有
`MIN_RUNS=140` 的镜像完整性断言，本地镜像只有 72 个目录，会直接拒绝跑。

⚠ `gen_concurrency.py` 的实验机副本**此前是旧版**（没有「在跑的 run 不写自己那行」
的过滤），2026-09-27 06:33 已把仓库版推过去。**推之前先 diff**，别再出现两边不一致。

跑完：
```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex
cd .. && python3 scripts/lab/check_paper_numbers.py     # 必须 0 MISS
NORE=1 python3 scripts/lab/check_paper_numbers.py       # 退役清单对拍
```

图若变了要重渲并 **cp 到 Windows 目录**（`/mnt/c/Users/X2406/Downloads/Foyer_images`，沿用原名覆盖）。

---

## 四之二、落地**也是**一个阶段完成 ⇒ 要开新一轮审查

目标里的工作方式是「每完成一个阶段，开一个中立子 agent 审查，**同时**启动一次 codex
审查，把两边意见都处置掉」。落地（改数字 + 改正文 + 重生成管线）就是一个阶段，
而且**这一批改动正是上一轮审查没能覆盖的**（它们依赖新数据）。

所以落地收尾时**必须**：

1. 写一份新 brief 到 `docs/review_brief_r49.md`，范围**只限这一批**（照 r48 那份的写法：
   A 部分「我声称改了 X，逐条独立复核」、B 部分「有没有引入新错 / 两个方向都查」、
   C 部分「陈旧说法扫描」；末尾单列「我核不动/核不了的条目」）；
2. **同时**发两家：中立子 agent（`paper-reviewer` skill + 沙箱）与 `codex exec`
   （输出到 `/tmp/codex_r49.out`，PID 落 `/tmp/codex_r49.pid`）；
3. 两边回来后**逐条处置**，写 `docs/finding_review_r49_disposition_20260927.md`。

⚠ 等待器用 **PID** 不要用 `pgrep -f`（本项目为此白等过几个小时，CLAUDE.md 有专条）。

⚠ brief 里要**点名**这一批最可能出错的四处：
   - `gen_eviction.py` 的集合从 26 变 **28**（正文六处 + `r=+0.85 / 残差 1.92ms` 要重算）；
   - 「0.5 to 4.6pp」与「the three groups」（新重复组进来后**两端都可能动**，
     现在有 6 条守卫盯着 —— 让审查者去验守卫**算的是不是对的量**，不只是绿没绿）；
   - 图 1 的 `_n_rep` 自动变（会不会变错）；
   - 摘要（若头条升级，**词数上限 265** 要重新数）。

## 五、本轮新修的一个真错（落地前记在这里，免得忘）

`gen_concurrency.py` 的实验机副本是**旧版**：对 `finished`/`wall_s` 都缺的 run
回退到 `steps.jsonl` 末时间戳 —— 对**在跑**的 run 等于「拿当前最后一步当收尾」，
造出一个假窗口。后果是 `paper/data/concurrency.csv` 里曾出现两行在跑的 run
（`pois200_foyer_scan_r2`、`pois200_foyer_sf0_r3`）。

**对当前正文零影响**（那两条不在任何表里，且 `gen_table.py` 是按名单查的）。
仓库版脚本有 `_done` 过滤，实验机副本没有 —— 已同步。落地后重跑一次即可清掉那两行。

同一次扫描确认：**喂正文的目录扫描器里只有它缺护栏**；
`frontier.py`（判决唯一产地）、`gen_projection.py`、`gen_gate_attrib.py`、
`gen_repeat_spread.py` 都有 `summary.json` 护栏。
