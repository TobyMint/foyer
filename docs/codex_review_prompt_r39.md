# codex 第 39 轮：**审「关于代码与实验条件的每一句话」**

## 为什么是这一轮

第 38 轮之后，我在准备「队首阻塞修复后前沿会不会移动」这个实验时，
顺手核了「每条臂跑的到底是哪个控制器」，**一天之内连抓两条 major**：

1. **`gen_stall.py` 的判据 (b) 极性是反的。** 注释写「阀门开着（不是阀门挡的）」，
   实现是 `bool(e["valve"])`，而 `valve` 为真 = 阀门**正在挡**。
   于是「不放行窗口」审计选出来的是**阀门在工作**的周期，而正文写成
   「阀门开着、控制器却不放人」。**34 轮、codex 三十多轮、七章逐项复算，一次都没碰到。**
2. **§VI 的「That is the code every run in this paper executed」过头**：
   表 I 的 `all throttles off` 行跑的是**另一个控制器**（`policy` 前缀是 `foyer:` 而不是
   `budget3:`），它有扫队列那段代码、单飞还是关的；而 §I 与 §V 都写着「它跑的是另一个控制器」。

**共同形状**：这两条都不是数字错，而是**关于代码 / 判据 / 实验条件的陈述与产物不符**。
项目的守卫体系全部盯着**数值**，对「这句话说的是哪份代码、哪个谓词、哪条臂」是瞎的。

## 这一轮请专门扫这一类

判据是：**这句话里的每个关于代码或实验条件的词，能不能在某份产物里找到出处？**
出处可以是：`metadata.json`（`policy` / `build` / `code`）、
`results/` 里的日志字段、`scripts/lab/*.py` 的实现、
或 `docs/` 里当时的记录。**「说得通」不算出处。**

### 请逐个核这几类词（在 `paper/sec_*.tex` 里 grep）

- **控制器身份**：`our controller` / `this controller` / `the same controller` /
  `a different controller` / `every run` / `all of our runs`
  —— 每条臂的身份是 `metadata.json` 的 **`policy` 前缀**（`budget3:` vs `foyer:`），
  **run 名字不是**（`pois200_foyer_*` 里两种都有）。
- **代码内容**：`scans the queue` / `only the head` / `single-flight` /
  `the break that enforces` / `the fix in our repository` / `the artifact that produced`
  —— 每一句都要问：**跑出这批数据的，是今天磁盘上那一份吗？**
  （已发现：这些 run 的日志里 `base_mode`/`base` 是 `None`，
  而今天的 `controller_budget3.py` 有 `--base-mode` —— **不是同一版**。）
- **谓词方向**：任何 `when X was open/closed/triggered`、`the valve`、`the gate`、
  `blocked`、`admitted` 的句子 —— 方向能不能从**日志自身的联合分布**里量出来？
  （已用这招抓到第 1 条：`valve` 为真时放行率 0.5%，为假时 9.8%。）
- **版本与修订**：`revision` / `copy` / `hash` / `re-measured` / `predates`
  —— 说的那个版本，与 `metadata.json` 里记的对得上吗？
- **配置等同性**：`identical` / `same configuration` / `back-to-back` / `paired`
  —— 两侧的 `policy`、池子、HiCache、卡、代码哈希逐项一样吗？

## 也请复核我这一轮的改法本身

`sec_results.tex` 的 §V「An independent adaptive controller」段与我新加的
`docs/finding_stall_predicate_inverted_20260926.md`：

- 我从「九条单飞开着的臂乱序放行 0/200、两个考虑整队列的臂 40%/58%」
  推出「只看队首」。**这个推论有没有跳步？**
  （我承认它**不是证明**：扫描 + 队首恰好总是放得下时也会是 0 乱序。正文有没有说过头？）
- 我写「that path does not explain the window above」，依据是
  「池子空 + 队首 15,981 token + 红线 96,360」。**这个否定够不够硬？**
- 我把 §V 的窗口从「4 条臂」改成「1 条臂」，并加了第七条撤回项。
  **有没有哪一处还残留旧口径？**

## 输出

`## Major issues` / `## Minor issues` / `## Questions requiring clarification`，
每条给：**文件:行号 + 原句 + 为什么 + 你在哪份产物里核的**。
**不要报**：守卫的假通过、TeX 构造、`has()` 的边界 —— 已处置到收益递减。
**不要为了显得严格而编造**；核不到就写「核不到，因为……」。
