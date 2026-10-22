# codex 第 43 轮：只审【r42 之后这一批改动】

## 范围

第 42 轮之后新改了这些（都在 `paper/` 与 `scripts/lab/` 下）。**只看这些**，不要重审全稿。

1. **`paper/sec_discussion.tex` 开头新增的单变量分解句**（25 档、旧 harness）：
   数据在 `paper/data/tier25_old.csv`（`scripts/lab/gen_tier25_old.py` 生成，读 `results/night/thr25_*`）。
   核三件事：(a) 五条臂**是否同一代 harness**（`metadata.json` 的 `started`/`code`）；
   (b) 「each of the two knobs carries about a third on its own, and moving both is
   sub-additive」在数据上是否成立；(c) 正文有没有把旧 harness 的读数说得比它该有的强。

2. **四条独立复算线**：`scripts/lab/independent_{frontier,elasticity,attribution,realization}_check.py`。
   判据：是否真的不 import 生成器、**输入集合**是否与生成器一致、容差是否按被比表的精度、
   结论是否真的支持「逐位相符」。请**直接跑**（参数见各自 docstring；frontier 那条需要
   `data/replay_pois200_l04.csv results/night`，realization 那条需要
   `data/replay_pois200_l04.csv results/night paper/data/reuse.csv`）。

3. **摘要压到 262 词**（`main.tex`）：八条锚是否都在、有没有哪句被压得比证据强。

4. **§VII 相关工作的引用修正**：`mori` 从「recomputation dominates」去掉、τ 区间改成与 §III
   同口径（3.3--8.8 / 20.6--39.2）、§V 补 `\cite{concur}`、SGLang 可配置性挂 `\cite{zheng2024sglang}`。

5. **tier25 表注**新增的 harness 判据句；**表 I 脚注**新增的「两条短 run 各丢了一个请求」。

6. **`scripts/lab/check_paper_numbers.py` 今晚新增的守卫**：
   独立复算覆盖面、分段 ε 第二实现、短 run 丢请求数、v25 表注哈希、摘要按排版口径计数。
   判据：这些守卫**是不是自证的**（关键词/阈值里带不带它要查的那个数）、**会不会静默不执行**。

## 输出

`## Major issues` / `## Minor issues` / `## Questions requiring clarification`，
每条给：**文件:行号 + 现在的原句 + 为什么 + 你在哪份产物里核的**。

**不要报**：前 42 轮已处置的老问题、错别字、排版、参考文献格式。
**不要为了显得严格而编造**；核不到就写「核不到，因为……」。
