---
name: citation-check
description: 审计引用是否真的支撑了正文的主张。当用户要求检查引用、核对 refs.bib、查缺引用/过度引用/引错位置、或在投稿前做引用体检时使用。逐句判断哪些主张需要引用、被引文献是否支持该主张；绝不为了补缺口而编造引用。
---

# 引用审计

## 输出格式

逐句过，只报有问题的行。用这三个标记：

```
[CITATION NEEDED]                  该有引用但没有
[SOURCE DOES NOT FULLY SUPPORT CLAIM]  引了，但被引文献支撑不了这句话
[VERIFY REFERENCE]                 元数据可疑 / 核不到 / 键名对不上
```

每条后面跟：文件:行号、原句、为什么有问题、建议怎么改。**没有问题的句子不要列出来。**

## 判断标准

一句话需要引用，当它是：

- 事实性陈述（某系统做了什么、某数字是多少）
- 比较性陈述（比 X 快 N 倍、优于 Y）
- 历史性陈述（首次提出、此前的做法是）
- 性能/规模数字

**关键区分**：被引文献是**讨论了这个话题**，还是**真的支持了这个具体主张**？
只讨论话题不算支持。典型问题：

- 引了一篇综述去支撑一个具体系统的具体数字
- 引了一篇论文的摘要结论，但正文那句话比摘要更强
- 引用挂在错误的句子上（下一句才该引）
- 把「我们测到的」和「文献报的」混在一句里

## 本项目已抓到过的四类错（都是真实发生过的，优先按这几条查）

1. **幻觉标题。** `mori` 条目曾写成 "MORI: State-Preserving Suspension for
   Agentic Serving"——**这篇论文不存在**，真实标题是 "Idleness is Relative:
   Exploiting Tool-Call Idle Windows for Offloading in Agentic Systems with
   MORI"。成因是 LLM 把摘要"回译"成了标题。**凡是读起来特别贴切的标题，
   都要去 arXiv 页面点一下。** 已修。
2. **占位符作者。** 同一时期 `qwen2coder` 的作者栏写的是 `{Qwen Team}`。
   作者栏出现机构名而非人名，基本就是没核过。已修。
3. **把我们自己测的数说成别人论文报的数。** 最隐蔽的一类。曾写
   "matches the source corpus's own **reported** mean tool time of 16.8 s"，
   而 TraceLab 摘要里根本没有任何 tool-wait 数字——16.8 s 是我们自己从 trace
   量的。**引用只允许支撑"文献说了什么"，不允许支撑"我们测到了什么"。**
   已修。
4. **把综述性工作当成对照实验引。** 曾用 KVCache-in-the-Wild 支撑"命中率对
   淘汰策略敏感"，而原文只说 eviction policy design "highly workload-dependent"，
   没有策略间对照。已修。

## 常规核对

- 键一致性：`\cite{}` 的键 ↔ `refs.bib` 的键双向无孤儿；`main.log` 里
  `Citation ... undefined` 必须为 0。
- 引言与背景是最容易缺引用的地方（本项目曾有整篇文献全堆在 Related Work）。

## 硬约束

- **绝不**为了填缺口而编造引用。
- **绝不**推断未经核实的元数据（作者、年份、会议、DOI）。
- 拿不准就标 `[VERIFY REFERENCE]`，并说明核不到的原因。
- 本地有 PDF 或源文件时以本地为准（`docs/`、`reviews/`、`.bib`）；
  需要外部信息时用 `WebSearch` / `WebFetch` / `codex exec`，并注明核实日期。

## 本项目引用红线

- **2608.30830** head-to-head 胜利已被否证，禁引（其 41% goodput 损失可引）。
- **PrefixShield 2608.01657** 已占 "admission responsibility" 术语，避撞。
- **CONCUR 已中 ICML 2026**，不要写成"仅预印本"。
