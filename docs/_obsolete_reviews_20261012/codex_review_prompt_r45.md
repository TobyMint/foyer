# codex 第 45 轮：只审【r44 报告之后这一批改动】

## 范围

第 44 轮之后又改了这些。**只看这些**，不要重审全稿。

### 一、正文（四处，仍然**一个数字都没改**）

| # | 文件 | 改动 | 起因 |
|---|---|---|---|
| 1 | `sec_model.tex` | 「The pair is **a harness generation apart, its two runs three and a half days and two GPUs apart**, and it is not a paired experiment; ...」→「The pair **is not a paired experiment: its two runs are the same harness generation, about a day and two GPUs apart.** The repeat landed on the card the host-tier run used, so **pairing the repeat with the host-tier run** removes the card half of the confound and leaves the date half---**those two are three and a half days and a generation apart**」 | §IV 写这个混杂配对「a day apart on different cards」，与 §III 的「three and a half days / a harness generation apart」**互相矛盾**。实测（`metadata.json` + `steps.jsonl` 首末时间戳）：`cap3_fixed`(GPU2, 09-21 14:28)↔`cap3_hc`(GPU3, 09-22 09:56) = **19.5 小时**、**harness 哈希完全相同**（`run_matrix 90958758c26b` / 控制器 `2b573829083c`）；而 `cap3_pd`(GPU3, 09-26 00:04)↔`cap3_hc` = **3.59 天**、**不同代**。⇒ 3.5 天那个数属于**另一个比较**，原句把两个比较并进了一句 |
| 2 | `sec_model.tex` | 「with the pool **halved**」→「with the pool **cut to half or three quarters**」 | r44 指出：`cap3_p75` 是 **76,074 = 75%**，不是一半 |
| 3 | `sec_model.tex` | 「The controlled experiment **varies the pool alone, on one card** and one trace, and shows that capacity matters」→「**reduces the pool on the same trace, by lowering the memory fraction**, and shows that capacity matters」 | r44 指出同段漏网；且 `TURNSTILE_MEMFRAC` 也变了（0.85 → 0.73 / 0.78），卡也不是一张（3 张在卡 2、`cap4_hp` 在卡 3） |
| 4 | `sec_xtrace.tex` | 「same trace and the same engine version」→「**replaying the main trace** with the same engine version」 | r44 指出「same trace」紧接「a second replay」，读者会以为是第二负载（真值：A100 十条 run 的 trace 都是**主 trace**） |
| 5 | `sec_discussion.tex` | 「with **the only change** being who else was on the machine」→「**the change in $\tau_2$ tracks** who else was on the machine」；「**two** within-run controls ... **Both** are the same run」→「two within-run controls---**neighbours arriving and neighbours leaving**---... **Each** is the same run」 | r44 指出前者的「only change」比记录强（同 run 两个窗口之间时间也在走）；后者**说两个、列三个**（cap1 / t85 / rl99） |

### 二、检查器（`scripts/lab/check_paper_numbers.py`，六处新守卫 / 补强）

1. **层对照配对**（新增）：从 `metadata.json` 现算「混杂配对是否同代 / 相距几天 / 是否同卡」与「repeat↔host 是否同卡 / 3~4 天 / 不同代」，逐条对正文；外加负面守卫（`harness generation apart, its two runs` 再出现就 MISS）。
2. **容量对照** 补「满池对照必须仍是 101,432」（r44 的构造：把 `cap4` 改成 90,000 原来能过）。
3. **派生计数** 补「六条退化 run 的**名字**名单」（原来只核条数与池子种数）。
4. **A100** 补「按名字去重后必须十条」（原来漏一条仍通过）。
5. **两日守卫** 从「找正文里的短语」改成**读七条 `thr25_*` 的 `steps.jsonl` 首末时间戳现算天数**。
6. **§II 的重复散布区间**（新增）：§II 引 `replicates.csv` 的 min/max（0.5--5.1pp），此前只有 §IV 的逐组枚举有守卫；某一组变成新的 min/max 时 §II 会静默过期。

## 请你做的

**A. 独立复核上表五处正文改动的事实依据**（不要信我写的，自己去 `results/night/*/metadata.json` 与 `steps.jsonl` 核）。特别是第 1 处：**新句对两个配对的说法是否各自成立**？有没有哪个条件词仍然错？

**B. 反过来问**：这五处改完，有没有哪一处**比证据弱**（本项目记过：「审查一直防把负说成正，所以把正说得更负没人防」）？例如第 5 处把 "the only change" 改成 "tracks"，是不是把原本**成立**的对照削弱了？

**C. 六处守卫**：逐条读代码并**自己设计反向测试**（不要用我上面写的构造）。特别问：
- 判据方向对不对？有没有**自证**（锚里自带要查的数）？
- **集合完整性**：名单/条数漏一个会不会仍报 OK？
- 第 5 处现在读 `steps.jsonl` —— **镜像不全**（某条 `thr25_*` 不在本地）时它报什么？是报警还是静默给个数？
- 第 6 处用 `ck_near` 锚 `SLO spread of configurations` —— 这个锚在 `sec_background.tex` 里唯一吗？

扰动数据文件前必须 `cp` 备份、测完 `md5sum -c` 还原。**不要用 `git checkout`**。
（上一轮你的沙箱里 matplotlib 缓存不可写，于是图 2 的标签检查没执行、你报的 736/1 MISS 是这个原因 —— 本轮可以忽略那一条，或只报「因沙箱无法执行」。）

**D. 继续扫这一族**：还有没有「关于实验条件的词」说得比记录强、或与记录不符？把**出处**（文件+行号）一并给出。

## 不要做的事

- 不要重审全稿、不要提篇幅（作者已决定）。
- 不要提已被撤回的主张（见 `CLAUDE.md`「撤回记录」）。
- 不要编造文献。
