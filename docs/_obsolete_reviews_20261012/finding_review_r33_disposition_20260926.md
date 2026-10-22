# 第 17 轮独立复核处置（「没出处的因果与条件词」专项扫描）

这一轮的任务不是通读全稿，而是**把一个新暴露的失败模式扫一遍**：
第 16 轮抓到「co-tenancy terminated rg2/rg3」是**我编的原因**（数字对，因果编的），
于是让复核者专门去找「关于**实验条件或因果**的词，在仓库里哪份记录都找不到出处」的句子。

**报了 5 条，全部处置。** 这一轮的价值密度是迄今最高的一轮 ——
其中两条直接推翻了论文正文里的因果陈述。

---

## 一、**「切换器」那条 15 分钟：切换器一次都没切**（最严重）

正文（`sec_discussion.tex` 的 Limitations）说变负载实验里
「**the switcher** finishing 15 minutes ahead of the best static cap at an SLO
inside the tie band, which would be the first evidence in this paper that
adaptivity pays」。

复核者查了三条「切换器」run 的全部记录：

| 判据 | 结果 |
|---|---|
| 三条 `admissions.jsonl`（各 400 事件）的 `cap` 字段 | **全部是 3**，没有一条在 cap=2 下跑过 |
| 三条 `switcher.jsonl` | 各 1~2 行，**每行都是 `cap=3`**（该脚本「cap 变了才写记录」） |
| `docs/finding_hicache_elasticity_20260923.md:170` | 「第一次的 `pois200_var_switch` 实际等价于一条静态 cap3 run」——**根因也记了**：static=N 下 runner 立即放行、没有 `queued` 事件，于是 `rate` 恒为 0、**全程一次没切** |
| `paper/data/repeat_spread.csv:19` | 把 `var_cap3 / var_switch / var_switch2 / var_switch2b` **归成同一组** `static=3+HC`，散布 5.68% |

我逐条复核确认。**那 15 分钟（265.79 − 250.92 = 14.87）就是同一配置的
run-to-run 散布**，项目自己的表就是这么归组的 —— 与「切换」没有任何关系。

已改写整段（`sec_discussion.tex` 的 Limitations）：
- 明写 **The switcher never fired**，并给出机制（static 模式下没有 queue 事件）；
- 那三条因此是**变负载 trace 上的静态 cap3 run**，14.9 分钟的领先是
  同一配置的重复散布（4 条，5.7%，`repeat_spread.csv`），**不是「适应性有效」的证据**；
- 补上**事后修好信号并离线重放**的记录（从每次准入自己的 `waited_ms` 反推到达时刻，
  重放切换在 128.0 分钟、设计值 124.5），并明写**没有重跑**；
- 删掉「Clean re-runs of that family are in flight」（**第 2 条**：镜像里没有任何
  `var_*_r2`，队列里也没有），改成「变负载这一格是**测过但不可用**，
  而**切换版本**是**没测**」。

## 二、**AIMD「原参数」那一行：墙钟不合格，因果也写错了**（第 3 条）

`pois200_aimd2_paper` 自己的 `INTERVENTION.md` 写着：

> **墙钟不可用**，且此 run 的墙钟有**三重污染**…**这个 367 分钟不能进主表**…
> **质量指标（命中 60.5% / SLO 81.4% / TTFT）有效**，按步统计、不受上述影响。
> **若这一行要进主表，墙钟需在干净环境重跑。**

而表 I 的 `AIMD, paper params` 那一行（364.3 / Δ −11.16）正是从它算的。
**同一个记录还推翻了我写的一句因果**：正文说停摆是「**the controller pinned its
window at one session**, admitted nothing, and left the engine idle for **over an
hour**」；记录说是**本机 process-reaper 杀掉了控制器与它的监督循环**、时长 **32 分钟**，
而实测该 run 最长连续空转 **27.7 分钟**（67.1 分钟那条是**另一条** 09-18 的 run）。

已做三件：
1. 正文那句改成照记录写，并明写**不把它读成控制律把窗口钉住**（两种说法不同，
   只有前者在记录里）；
2. 表 I 那一行加 **§** 标记，表注写明「墙钟不可用、SLO 与逐步量不受影响、
   干净重跑在跑、该行的墙钟与 Δ 是暂定值」；
3. **排了一次干净重跑**：`pois200_aimd2_paper_r2`（GPU2，08:15 起，
   配置逐字照抄 `lane_pois_aimd2_paper.sh`）。

## 三、**「fourteen … two of which are failed runs」**（第 4 条）

正文先说「flagged：fourteen of ours are, **two of which are failed runs we do not
report**」，而同节后文自己给的是另一个拆法（「two of them are rows of Table I…
twelve are arms we do not report here」）。复核者按 `min_at_ge3 >= 60` 复算：
主 trace 上是 **14 条**（与新表一致），其中**没有**失败的 run；
三条 `_failed_4lane_*` 是**另外三条**，不在那 14 条里。
已改成：主 trace 14 条、变负载 trace 3 条、死在窗口里的 3 条我们不报告。

## 四、**F:t85 的「理由」两个分句都不成立**（第 5 条）

原文：「five of the twelve show no aggregate inflation at all, **because their
overlap was short relative to the run or did not touch their decode interval**」。
复核者查 `concurrency.csv`：t85 的争用窗口 **165.3 / 333.9 分钟（约一半）**，
「短」不成立；而 `tau2_windows.csv` 显示它在争用期的半小时桶是 28.9--29.8 ms、
离开后 22.3--22.6 ms —— 「没碰到 decode 间隔」也不成立
（**同节 15 行之后的正文自己就引了这组数**）。

已改成可复算的理由：**这五条里被 flag 的窗口都是整条 run 的少数**
（31%--50%），所以**逐 run 的中位由未被污染的那部分定**；
并加一条脚注点明 F:t85 是「中段一半被污染」的平均，其半小时序列正是我们
在下面当作对照引的那一组。**聚合中位不动不等于没发生事**。

---

## 五、复核者另外列出的「查过但有出处」的 6 条

A100 的四条（池子 971,456 / 基线最后 24 分钟被占 / 同模型同引擎同 memfrac /
完成分位）· 预注册配对的「still running」· `cap1_r2` 的 511.7 与 3.0% ·
「两个 harness 代」· 半池的「same card, same trace, only the pool changed」·
`var_cap3` 的 158/266 与 `var_cap2` 的 watch —— 都有出处，**下一轮不必重查**。

---

## 六、状态

**28 页**、**0 Float too large**、0 Overfull、**592 项检查 0 MISS**。
本轮 **报 5 条、处置 5 条**。

> **这一轮的教训**：前 16 轮的所有审查（我自己的、codex 的、子 agent 的）都在核
> **数字**，而这一轮专门核**因果词与条件词**，一次就推翻两处正文陈述 ——
> 其中「切换器」那条还是论文**自己文档里早就记着是坏的**。
> **一个说得通的因果，不等于有出处的因果**；而「说得通」恰恰是我们写它时的理由。
