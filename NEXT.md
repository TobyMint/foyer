# 交接状态（2026-09-25 凌晨更新）

接手先读这一页。**当前在跑什么、下一步做什么、哪些数还不能用，都在这。**

## 〇0、**A100 方向 D 在跑**（2026-09-25 02:47 起，03:2x 更新）

方向 D 之前两页说「跑不了」，**两条理由都是错的**（`docs/a100_toolchain_20260925.md`）：
模型其实在 `/data/xbw/turnstile/models/`（trace md5 与 3090 逐位一致）；
旧窗口判据的 `foreign` 是**全机合计**，GPU2 上有别人的 76G 就永远判不出来。
真正的拦路石是 SGLang 的 JIT kernel 要 C++20 而 A100 上只有 gcc 8/9 ——
conda 装 gcc-12 + `NVCC_PREPEND_FLAGS="-ccbin ..."`（**只设 CUDAHOSTCXX 不够**）。

**池子 983,728 = 3090 的 9.70 倍**，同模型、同 trace、同引擎、同 memfrac，只改卡。

**车道**：GPU0，`a100_cap4 → cap3 → cap5 → cap2`，跑完由 `scripts/a100/chain_a100.sh`
自动接 `a100_cap1`（带窗口检查：GPU0 显存有占用就不启动）。
`gpu_watch` 全程 `n_foreign=0`。

**判据**（看结果前定死，`docs/prereg_a100_addendum_20260925.md`）：
**唯一判决轴 = 兑现率穿过 50% 时的 R̄**；3090 上它是 **1.7344**（cap4 的
60.7432%@R̄1.650488 与 cap5 的 36.3560%@R̄1.840948 之间插值）。
A100 的交叉点 > 1.7344 判支持、≤ 判证伪。判据**已在 `gen_a100.py` 的
`crossing()`/`verdict()` 里实现**（五个分支自测过），判决由脚本打印。
⚠ 初版的两套规则会给出相反判决，已删掉一套；`±10 点` 与 `cap5 ≥65%` 两条阈值
**已撤回**（前者宽度无依据、后者不可复算）。

分析脚本 `scripts/lab/gen_a100.py` → `paper/data/a100.csv`（**不进主表前沿**）。

## 〇a、审查状态（2026-09-25 03:2x）

两路并行，每轮都开。**这一轮两路的分工效果很明显**：codex 查数对不对、能不能追，
子 agent 查论证成不成立 —— 后者抓到两条是**我在回应上一轮审查时新写进去的错**。

- **codex 第 22 轮**：A 段（§VII 重写）一条数字都没挑出来；B、C 两段各三处措辞。
- **子 agent 第 9 轮**：六条 major。最重的两条 ——
  ①「队列是节流造出来的」原来用「18 个在等 + 只跑一个」论证，而那个并列在
  **200 档基线上同样成立**（两档在跑数 1.1369 对 1.1360）；改成引闸门归因与占用投影。
  ② 我加的反证是个**从未暴露于该条件**的对照（那条 run 只有 14.4 分钟在四车道，
  门槛是 60 分钟）。两条通则已进 CLAUDE.md。
- 全部处置，记录在 `docs/finding_review_r22_r9sub_disposition_20260925.md`。
- `check_paper_numbers.py`：**401 项、0 MISS**；编译 **25 页、0 Overfull、无 undefined**。

### 本轮新加的三个数据文件（都是为了补追溯缺口）
`superseded.csv`（新旧并排，让被撤下的 0.6943 可追）、
`tau2_windows.csv`（§repro 的分时段 τ₂ 对照）、
`repeat_spread.csv` 改两位小数。

### 本轮新记进 CLAUDE.md 的一条方法论
**连锁改名要按【数字】清点，不只按【名字】清点** —— §III 末段一个 `bres` 字样都没有，
只有「17 分钟」这个数，名字扫描扫不到。

## 〇、刚刚落地（2026-09-25 00:0x）：`bres` 干净重跑 + realhr 补全扫描

- **`pois200_foyer_bres_r2` 已跑完并全量并入正文**，连锁改动 12 处，逐条记在
  `docs/finding_rerun_bres_20260925.md`。最重要的一条：**Route 1 的结论被改写了** ——
  去掉记账不是「墙钟慢 4.2 分、SLO 掉 6.0 pp、两项相抵」，而是
  **墙钟快 25.4 分、SLO 掉 3.9 pp、相对前沿的距离几乎不变（−1.24 vs −1.33）**，
  即「沿前沿下滑」而不是「越过前沿」。这个版本更强也更负面。
- **realhr 补全扫描全部落地**：cap5/cap6/cap8 把第二条 trace 的 R̄ 推到 1.50（此前只到 1.29），
  另补两个重复对（cap4/cap4_r2 墙钟差 1.7%，**foyer/foyer_r2 只差 0.06%**）。
  结论「方向迁移、水平不迁移」不变（`slope.csv` 的 xtrace 全范围斜率仍是 −40.87）。
- **数据文件全部重生成**，`check_paper_numbers.py` **290 项 0 MISS**；
  论文 **23 页**（上一版 22 页，本轮改动加了一页，页数收紧留到实验全落地后一次做）。

### 本轮新记进 CLAUDE.md 的两条纪律
1. 重跑替代旧测量时，生成器要有**显式的 `SUPERSEDED` 名单**（判据自检否则会误报，
   重复散布表否则会把「污染 vs 干净」当成 run-to-run 噪声）。
2. lab-only 的表会随「实验机上有什么」漂移 —— 论文引这类数**必须同时给出集合规模**。

## 一、论文当前状态

- `paper/` **25 页**（目标 23，**瘦身留到实验全落地后一次做，一条限定都不许丢**），
  0 Overfull，无 undefined，编译干净
- **主线是方向 B**：标题 *When Does Admission Control Pay? The Memory Tier Sets
  the Cost of Concurrency in Agentic LLM Serving*。核心是一条定量律：
  **trace 定复用上界（21.55M / 75.5%），配置定兑现多少**。
  device-only 兑现 **92.5%→36.4%**（R̄ 1.00→1.84）；host tier 的静态点守住
  **90.2–92.4%**，**全部 19 条 host-tier run 落在 72.8–92.5%**（最低那条是关掉
  所有节流的臂）。有一条 host-tier run 被排除（`foyer_hz1_r2`：引擎侧 prompt token
  计数是 trace 计划的 1.41×、零 retraction、零重试，τ₁ 也不成比例）——
  正文写明了排除理由
- **§VI 第二条工作负载**：**方向迁移、水平不迁移**（R̄ 现在覆盖到 1.50）
- 归因表：**12 条中 4 条被归因**（本轮从 3 变 4，`bres` 干净值落到「内存没用满」）
- **数字溯源**：`check_paper_numbers.py` **401 项 0 MISS**

## 一b、还在跑的 / 排队的（2026-09-25 03:25 快照）

**严格 2 条 3090 车道 + 1 条 A100 车道**（A100 是另一台机器）：

- **3090 GPU 2**：`foyer_hz0_r2`（772/999 在跑）→ 链式 waiter 已挂
  `chain_pool50.sh`：跑完自动起**半池因果实验** `cap2_hp/cap3_hp/cap4_hp`
  （带窗口检查：GPU2 有占用就不启动；同名旧目录先挪走）。
- **3090 GPU 3**：`foyer_hz2_r2`（763/999）→ `foyer_breshz1_r2`（同车道排队中）。
- **A100 GPU 0**：`a100_cap4`（348/999）→ cap3 → cap5 → cap2 →（`chain_a100.sh` 自动接）cap1。

⏳ **还没排进车道的**：`cap5/6/8_hc`（三条脚本 `lane_cap_hc_g2/g3/ext.sh` 都在）、
`cap1_r2`（`lane_cap1_r2.sh`）、**同卡背靠背的层级配对** `cap3_pd`/`cap3_ph`
（`docs/prereg_tierpair_20260925.md`；`lane_pair_dev.sh` / `lane_pair_hc.sh` 都在）。
**这些要等 3090 上的车道腾出来**，按优先级：半池 > cap5/6/8_hc > 层级配对 > cap1_r2。

⚠ **`concurrency.csv` 的 CONTESTED 计数会随新 run 落地而变** —— 正文写了这个数，
定稿前必须重跑一次 `gen_concurrency.py` 并对齐。

⚠ **摘要 1045 词**（接手时 892），多数 venue 远短于此。瘦身留到实验全落地后做，
**挪位置可以，一条限定都不许丢**。

⚠ **页数 25，目标 23** —— 同一批一起收。

## 二、审查基线（下一轮拿这个对比）

- codex 第 8 轮：**5–15%**（7 条 major，全成立）
- 中立子 agent 第 1 轮（全稿）：M1–M5
- 中立子 agent 第 2 轮（新 §VI + 归因表）：8 条 major，全成立
- codex 第 9 轮：**10–25%**（4 条 major，全成立）
- codex 第 11 轮：**20–35%**
- **codex 第 12 轮：30–45%**（五项机械核对全 MATCH，只剩两处措辞/出处）
- 子 agent 第 4 轮（第 12 轮审查）：9 条 major，**5 条是「集合没说清/数字无出处」**，全部处置
- **codex 第 13 轮：15–30%**（它读的是修改中途的版本；核到的 host-tier 端点、表 I 并发列、
  sf=0 探针四个数全部 MATCH）
- **子 agent 第 5 轮（复核「上一轮 25 处修改」）**：7 条 major —— 最重要的一条是
  **host-tier 集合的定义不成立**（摘要的全称句被自己的数据反驳：`cap2_hc` 70.7%、
  `foyer_rg2` 67.1% 在区间外，变量负载族六条不在集合里）。全部处置，
  见 `docs/finding_review_r13_disposition_20260924.md`
- **codex 第 14 轮：20–35%**（三条 MATCH、两处要改：`14.27%`→`14.26%`、
  「turns expensive」→「turns positive」；另两条集合/表述问题）。处置见
  `docs/finding_review_r14_disposition_20260924.md`
- **子 agent 第 6 轮：第一版卡死**（跑了 56 分钟没写一行输出，已停掉重开一个收紧范围的）。
  教训：给子 agent 派活要写「最多核这几条、不要穷尽全稿」，否则它会去做全量复算
- **下一轮**（四条重跑 + 半池落地后）：codex 第 15 轮 + 子 agent 第 7 轮
- 分数在升，理由**从「结构性上限」换成了「可当场修的账目错误」**
- **每一轮修正都引入过被下一轮抓到的新错误** —— 所以每批改动后必须再开审查，
  这一步不能省（本会话已因此循环了五轮）

## 三、⚠ 哪些数现在不能用

**同机争用**：14 条 run 落在「同机 ≥4 条引擎 ≥60 分钟」的窗口里，其中 **6 条在表 I**。

- **实测被损害的 4 条**（τ₂ 30.9–33.3 ms，同族干净值 23.8–25.7）：`bres`、`hz0`、`hz2`、
  `breshz1`。它们的墙钟/SLO/Δ **不可用**，正在重跑
- **只被窗口标记、未被实测损害的 2 条**：`cap1`（τ₂ 20.6，全场最低）与 `aimd2_paper`（24.4）。
  数保留，但表里带 ‡；cap1 已排重跑
- 审计：`scripts/lab/gen_concurrency.py` → `paper/data/concurrency.csv`
- 纪律：**判据是窗口（风险标记），不是损害测量**，两者必须分开说

## 四、实验队列（7 条等待器，自动串行，**严格 2 车道**）

```
GPU2: var_switch2 → bres_r2,hz0_r2 → cap5_hc,cap6_hc → cap2_hp,cap3_hp
GPU3: realhr补全(cap5→cap6→cap8→cap4_r2→foyer_r2) → hz2_r2,breshz1_r2 → cap8_hc → cap4_hp → cap1_r2
```

三组实验各自要回答什么：

- **`*_r2`**（重跑）—— 那四条被争用损害的臂。**判决可能变**：估算 bres 的 Δ 可能从 −7.8
  变成约 −0.6（进打平带）
- **`*_hc`**（HiCache 推到高 R̄）—— B 的**可证伪预测**：host tier 把有效容量变 3×，
  悬崖应推到约 3 倍运行数。复用守住 → 容量律成立；塌 → 证伪
- **`*_hp`**（**半池**，101,432 → 50,716）—— B 的**因果**检验。同一张卡、同一条 trace、
  同一个模型，**只动池子**。这是唯一能把「容量」单独拎出来的实验；跨 trace 做不到

纪律：`wait_and_launch.sh` 等前一条车道的**最后一个 run 写出 summary** 才启动（不是「显存空」
—— run_matrix 在一条车道的两条 run 之间会卸载 server）。启动前数一遍自己的 server 数（≤1），
并用 `/tmp/turnstile_launch.lock` 防两个等待器同时启动凑成 3 条。

## 五、lab-A100（方向 D）：**在跑**（这一节以前写的是「跑不了」，已作废）

工具链与判据见 `## 〇0` 与 `docs/prereg_a100_addendum_20260925.md`。
两条留给下一次的提醒：

- **JIT kernel 编译要靠 `NVCC_PREPEND_FLAGS`**（`-ccbin` 指到 `/data/xbw/gcc12/bin`）——
  只设 `CUDAHOSTCXX` 不够，ninja 里写死了 nvcc 路径。
- **池子守卫故意关掉**（`TURNSTILE_EXPECT_POOL=0`）：80G 卡上池子本来就该大得多，
  关掉后 memfrac 钉在 0.85，池子由卡自己决定，实际值 983,728 写进 metadata。

## 六、实验跑完后要做的（按顺序）

0. ~~realhr 扫描~~ **已做**（cap8 落地，§VI/§criterion 已按六条 cap 重写，
   见 `docs/update_xtrace_cap8_20260924.md`）。cap4_r2 / foyer_r2（重复对）落地后
   再跑一次 `bash scripts/lab/update_xtrace.sh` 即可，它们只影响重复散布。
1. 四条 `*_r2` 落地 → **`bash scripts/lab/update_table.sh`**（一条命令：concurrency →
   runs_precise → runs.csv → table1.csv → `compare_rerun.py` 看判决变不变 → 自检）。
   然后改正文的表 I 行、去掉 ‡、改图注的六条空心圈、把 §repro 的「正在重测」改成过去时。
2. `cap*_hc`（HiCache 推到高 R̄）落地 → 扩 `elasticity_hc.csv` 与 `reuse.csv`
   → §III 那条可证伪预测（host tier 把悬崖推到约 3 倍运行数）写成实测。
3. `cap*_hp`（**半池因果实验**）落地 → 判据**已经先写好了**（`docs/prereg_halfpool_20260924.md`），
   照它逐条回答 → §IV 的因果段。
4. 全部落地后：codex 第 14 轮 + 子 agent 第 6 轮 → 处置 → 最后收紧页数（22 → 21 需省约 30 行）。

## 七、这个项目的硬规矩（详见 CLAUDE.md，这里只列最容易犯的）

- **不要把没跑的实验写成已跑** —— 一天内犯了**三次**，三方审查各自独立命中
- **生成器的 run 列表不全会静默丢数据 / 改口径** —— 犯了**三次**（hz1、aimd2_paper、sf0 口径）
- **判据写在正文里、代码里也必须实现** —— 归因表因此多算五条
- **两条管线算同一个量必须共用定义** —— 表 I 与 §V 曾给 −0.55 / −0.57
- 先找有没有生成脚本再动手改数；从表里抄数后回头确认是哪一列
- `open(p,"w")` 先截断后报错 —— 写完先断言是 str
- commit message 有反引号走 `-F` 文件，别用 `-m`
