# codex 第 41 轮：**只审【这一轮新改的十二处】**

## 为什么要限定范围

第 40 轮之后我按它和一份中立复核的意见改了十几处，其中一处**动到了论文的贡献陈述**。
这一轮只看**这些改动本身**，不要重审全稿（前 40 轮已覆盖）。

## 请逐处核这十二处（都在 `paper/` 下）

1. **「One switch, two regimes」的四处改写**（`sec_discussion.tex` 开篇、末段、图 5 图注、
   `sec_intro.tex` 的贡献条）。**这是最重要的一处。** 判据：
   - 两档的 `policy` 串到底差什么？（`results/night/<run>/metadata.json`；
     25 档是 `thr25_base` / `thr25_push`，200 档是 `pois200_foyer_hc` / `pois200_foyfix_hc`）
   - `--target-util` 的默认值是多少？（`controller_budget3.py`）
   - 改后的正文有没有把差异**说准**？有没有**新的**过头或过弱？
   - 图 5 的图注与正文是否一致？
2. **§IV 的「device misses more」**（`sec_model.tex`）：原句「at every point」被证明为假
   （`cap5_hc` 19.0M < device-only `cap5` 20.7M，见 `paper/data/eviction.csv`），
   现改成**成对比较 + 明写 cap5 上反向**。核：改后的每一句是否都被 `eviction.csv` 支持？
3. **§IV 的 host 命中率集合**：现在写「三个点在 80.7--78.7、加 cap5 到 77.3、全家最低 53.1」
   （`hitrate.csv` 的 `observed_round1_pct`）。核这三个集合与三个数。
4. **§VII 的 host-tier 限定**：现在写「四个静态 host-tier 点在 87.9--92.4%，
   但 24 条 host-tier run 最低到 59.7%（那是 cap8，问的会话比池子还多）」。
   核「四个静态点」是哪些、87.9/92.4/59.7 对不对。
5. **§VII 的共租用两对照**（cap1 的 20.3--20.9 → 21.3/27.1/21.1；t85 的 29.8 → 22.3--22.6；
   rl99 的 32.4 → 25.2/25.1）：核 `paper/data/tau2_windows.csv`。
6. **§II 的锚点敏感性** `+6.6`（对 `cap3+HC` 的**首跑** 81.1%/236.4 分钟，而 `+5.8` 对重复
   81.9%/230.3）：核 `runs_precise.csv` 与表 I。
7. **§IV 的半池自我限定**：`49 of the first run's 50 and 114 of the second's 116`
   （`pool50.csv` 的 `error_under_pool` 与 `failed_steps`）。
8. **三处 `0.93\%` 改成「占其采样跨度」**：核 `stall.csv` 的 `pct_span` 口径
   （分母是 `metrics.csv` 的采样跨度，不是 `run_summary` 的墙钟）。
9. **四次「同配置重复」**现在写着「跨了一个控制器版本与两张卡」：核那四条的 `metadata.json`。
10. **§I 与 §VI 对 A100 的口径**：现在都写成「**not overturning**，不是 full strength」。
    核 §VI 的 `sec_xtrace.tex` 与 §I 是否**一致**，有没有第三处还按「复现」写。
11. **`sec_xtrace.tex` 的「not a property of one trace family or one card」**：现在删掉了
    「or one card」。核删得对不对（第二张卡支持的是 tier 机制，不是控制器判决）。
12. **检查器的退役名单**（`scripts/lab/check_paper_numbers.py` 的 `RETIRED`）：
    我按一份全量复核的结论删掉了 2 条、加了 5 条。核**新加的那 5 条**
    （`第二条 trace 重复对的兑现散布` / `realhr foyer 重复对墙钟散布` /
    `replicates 墙钟散布上界` / `idle all_runs median_s` / `§III cap4_hc 的空转%`）
    是否成立 —— 判据：把描述里的数拿去全稿 `grep`（用 `{,}` 与 `\\,` 归一化后），
    **值不在正文、且它支撑的论断也随之收窄或删除 → 退役成立**。

## 输出

`## Major issues` / `## Minor issues` / `## Questions requiring clarification`。
每条给：**文件:行号 + 现在的原句 + 为什么 + 你在哪份产物里核的**。

**不要报**：前 40 轮已处置的老问题、错别字、排版、参考文献格式。
**不要为了显得严格而编造**；核不到就写「核不到，因为……」。
