# codex 第 32 轮：核第 31 轮那 10 条的修法（不重审全文）

第 31 轮你报了 7 条、独立复核子 agent 报了 3 条，**全部已改**，逐条在
`docs/finding_review_r31_disposition_20260926.md`。这一轮**只核改得对不对**。

## A. 逐条核

- **A1（唯一性守卫扩到斜率形状）**：现在是两个正则（`(a-b)*(c-d)/(e-f)` 与
  `(a-b)/(c-d)`）+ 四条白名单（`envelope.py` / `run_matrix.py` /
  `independent_frontier_check.py` / `decode_rate.py`）。
  **请核**：白名单四条的理由站得住吗？`slo_sensitivity.py` 改成 import 共用实现后
  输出是否真的逐字未变（含它的 36 行打印与 CSV）？**再给一个新的构造** ——
  还有别的写法能让同一插值溜过去吗？
- **A2（`gen_tierpair` 的日志行数守卫）**：现在 summary 与 `steps.jsonl` 两个来源都核。
  **请核**：还有别的「summary 说有、日志里没有」的形态吗（例如 `steps.jsonl`
  有 999 行但其中若干行是别的 run 的）？
- **A3（`2.4pp`）**：`81.4781 − 79.0482 = 2.4299`。**请复算**，并核那一段里
  **每一个** gap 是不是都用未舍入值算的（9.80 / 12.23 / 2.4299）。
- **A4（`same-card` → GPU 3 / GPU 2）**：**请回 `metadata.json` 独立核**这台机器的
  gpu 字段与两条 run 的时间戳，看新写的「removes the card half of the confound
  and leaves the date half, since the two are still three and a half days apart」
  对不对（3.5 天这个数也要核）。
- **A5（`tight to four tokens` 的例子换成半池那一对）**：
  半池 50,688 被服务 / 50,720 被丢 / 池 50,716；四分之三池 76,085 丢 / 75,445 服务 / 池 76,074。
  **请复算这四个边界数与两个池子**，并判「which is why we quote the half-pool pair
  for the bound」这句的因果说不说得通。
- **A6（30.2% 与 23.8% 两个口径）**：`pool50.csv` 新增 `gap_pct_of_prefix` 列。
  **请核**：两列的分子各是什么、与正文的说法是否对得上？另外两行
  （`cap3_hp` 24.8/16.0、`cap4_hp` 21.3/8.5）的差值为什么比 `cap2_hp` 大得多？
  这一列在崩掉的 run 上还有意义吗？
- **A7（§V 三条闸门臂）**：`gate_attrib.csv` 的 `named_arm` 注释行 + 三条现算守卫 +
  正文披露「部分运行」。**请核**：(a) 在实验机上重跑生成器，**数据行**是否真的
  逐字未变（45 条 / 5.4% / 30.6%）？(b) 正文那句披露与 `named_arm` 行是否自洽？
  (c) 检查器那三条守卫是**从 `controller.jsonl` 现算**的，它 import 了
  `gen_gate_attrib.load` —— 这算「共用定义」还是「与被审对象同源」？请判。
- **A8（排版卫兵扩到 `.bib`）**：**请核** `.bbl` 需要单独守吗？
  `refs.bib` 改了、`latexmk` 只重跑 bibtex 而不重跑 pdflatex 的情形会怎样？

## 硬约束

- **只报有证据的问题**，指到 `文件:行号` 或具体数字。不要为了显得严格而编造弱点。
- **不要修改任何文件**（只读）。
- 如果某条修得对，就说对 —— 编造的弱点会浪费一轮。
