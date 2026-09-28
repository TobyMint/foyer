# codex 第 42 轮：只审【今晚这一轮的改动】

## 为什么要限定范围

第 41 轮之后，今晚做了一次**篇幅手术**（21 页 -> 18 页）与一次**臂替换的串联收尾**。
这一轮只看这些改动本身，不要重审全稿（前 41 轮已覆盖）。

## 请逐处核（都在 `paper/` 与 `scripts/lab/` 下）

1. **`aimd2_paper` -> `aimd2_paper_r3` 的连锁**。表 I 那一行与所有派生表现在都指第三次尝试
   （`326.8 / 2.17 / 79.4 / -12.65`，去掉 ‡ 与 § 标记）。核：
   - `paper/data/table1.csv`、`attribution.csv`、`occupancy.csv`、`decomp.csv`、
     `arrival_slo.csv`、`slo_sensitivity.csv`、`runs.csv`、`runs_precise.csv` 里那条臂的
     读数是否**描述同一次运行**；
   - `paper/data/aimd_stall.csv` **故意**保留两次失败的尝试（不要报它「不一致」）；
   - `metadata.json` 里 `pois200_aimd2_paper_r3` 的 `policy` 与 `r2` 是否逐字相同。

2. **`arrival_slo.csv` 的三行新增**（`cap3_pd`/`cap3_ph`/`foyer_hz1_r3`）带来的派生量变化。
   核 §VI 三处：
   - 「twenty-four of the thirty-one」与紧随其后的缺席名单
     （「no-control baseline, four host-tier runs and two controller repeats」）是否
     **恰好**对上数据（表 I 列了 31 行、`arrival_slo.csv` 有 24 行）；
   - SLO 损失区间 `2.9--19.5`；
   - 阈值敏感性表新增的 `horizon=1` 第三次运行那一行与改过的 AIMD 行。

3. **删掉五张图之后的一致性**（fig3 步时间 / fig4 idle 段 / fig5 负载层级 / fig6 horizon /
   fig8 转移；fig8 本来就没进过论文）。核：正文里有没有**指代不存在的图**的句子；
   被删图的图注里承重的读数（例如 fig6 的「其余两个设置各跑一次」）有没有落进正文。

4. **压缩有没有把限定语删掉**（这是最危险的失效模式：删数→句子更顺→主张更强）。
   重点核 §V「The frontier」附近、§V 归因小节、§III 的 `What tracks reuse is the tier`、
   §VI。判据：**逐个结论句往回找它的数**，并检查 `we do not / cannot / rather than /
   not an intervention / consistent, not demonstrated` 这类限定是否在压缩中丢失。
   ⚠ LaTeX 是硬换行的，检索多词短语前先把空白归一化，否则会报**假「不存在」**。

5. **检查器的退役名单**（`RETIRED`，今晚新加 15 条）。判据是「**值现在在哪**」：
   把描述里的数拿去全稿找；凡「值不在正文、且它支撑的那句话还在」→ 那是**恢复**
   （把数加回正文），不是退役。另外：今晚发现一条旧守卫（`§VII 更早一代 25 档的下界`，
   值 `11`）**一直是靠代码哈希 `d692ab11f396` 里的 `ab11f` 假通过**的 —— 请看看还有没有
   同类（短数字靠子串/哈希命中）的守卫。

6. **`gen_concurrency.py` 新增的「还在跑的 run 不进表」**（判据：没有 `summary.json`
   **且** `steps.jsonl` 30 分钟内还在写）。核这个合取判据有没有反例：
   一条已经跑完、但从没写过 `summary.json` 的 run，会不会被误判成「还在跑」而**整行消失**。

## 输出

`## Major issues` / `## Minor issues` / `## Questions requiring clarification`。
每条给：**文件:行号 + 现在的原句 + 为什么 + 你在哪份产物里核的**。

**不要报**：前 41 轮已处置的老问题、错别字、排版、参考文献格式。
**不要为了显得严格而编造**；核不到就写「核不到，因为……」。
