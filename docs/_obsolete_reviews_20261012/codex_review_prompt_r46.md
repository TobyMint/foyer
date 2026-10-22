# codex 第 46 轮：只审【r45 报告之后这一批改动】

## 范围（只看这些，不要重审全稿）

### 一、正文六处（仍然**一个数字都没改**）

| # | 文件 | 改动 | 起因 |
|---|---|---|---|
| 1 | `sec_model.tex` | 「leaves the date half」→「those two are still three and a half days **and a generation** apart」 | r45 说：同句自己写了 `a generation apart`，只提日期自相矛盾 |
| 2 | `sec_discussion.tex` | 「**pin the cause** to co-tenancy」→「**implicate** co-tenancy rather than the configuration」 | r45 建议（非随机时间对照） |
| 3 | `sec_model.tex` | 「**The controlled experiment**」→「**The capacity control**」 | r45：对照来自更早批次、`cap4_hp` 与 `cap4` 不同卡 |
| 4 | `sec_xtrace.tex` | 「the pool is 983{,}728」→「the **nominal** pool is 983{,}728」 | r45：七条静态 run 里三条不是满池 |
| 5 | `sec_background.tex` + `sec_model.tex` | 「SGLang v0.5.10」→「v0.5.10**.post1**」 | 实验机实测 `sglang.__version__ == "0.5.10.post1"`（pip 元数据同） |
| 6 | `sec_results.tex` | 带旗那段：原来「One row … cap1, and **five** more … Four of those five … **The remaining one, cap1** …; **the fifth** is …」数下来是 **6**（cap1 不在那五条里）。已把 cap1 摘出来挪到句尾 | 我通读时发现 |

### 二、检查器 +8 条守卫（`scripts/lab/check_paper_numbers.py`）

G1a 配对·两边 `code` 都缺失时不许当「同代」；G1b/c 配对·时间差改成**有符号**并断言 `cap3_pd` 在后；
G2 容量·两边都记了 `MEMFRAC` 时缩的那条必须更小；G3 退化名单·**逐名**核池子值；
G4 A100·按名字去重后的**集合**必须等于十条的预期集合；G5 §II 散布·下界必须出现在上界**之前**；
G6 §V 带旗计数（新，此前无守卫）；G7 `gate_attrib` 的「forty-six of them」（新）。

## 请你做的

**A.** 独立复核六处正文的**事实依据**（`results/night/*/metadata.json`、`steps.jsonl`、
`paper/data/*.csv`、以及你能读到的实验记录）。**特别是第 6 处**：请自己从
`paper/data/table1.csv` + `paper/data/concurrency.csv` 数一遍，判断新句
「One row … cap1 … five more … Four of those five were damaged … The fifth is the
superseded first attempt at the AIMD arm … cap1 itself …」**是否每一句都成立**。

**B. 反过来问**：六处改完，有没有哪一处**比证据弱**（本项目记过：审查一直防「把负说成正」，
所以「把正说得更负」没人防）？例如第 2 处把 `pin` 改成 `implicate`、第 3 处把
`controlled experiment` 改成 `capacity control`，是不是把**成立**的说法削弱了？

**C.** 八条守卫逐条读代码并**自己设计反向测试**。重点问：判据方向对不对、有没有**自证**
（锚里自带要查的数）、名单/集合漏一项会不会仍报 OK、以及**边界值**（±1、空集、缺键）。

**D.** 还有没有「关于实验条件的词」说得比记录强？（继续上一轮的线程。）

## 硬约束

- **反向测试必须在沙箱里做**，而且写入前要断言 **`os.path.realpath(p)` 在沙箱内**——
  只查「文件本身不是符号链接」**挡不住父目录是符号链接**（2026-09-26 我就是这么把两个
  活数据文件写坏的）。推荐：把 `paper/` 复制、`results/night/*` 逐条符号链接，
  **再把你打算扰动的每个 run 目录换成真副本**；写完用
  `rsync -a lab-3090:/data/xbw/turnstile/results/night/<run>/ <本地>/` 就能取回原件。
- **不要用 `git checkout`**（本仓库工作区就是最新版本）。
- 不要重审全稿、不要提篇幅、不要提撤回记录里的主张、不要编造文献。
