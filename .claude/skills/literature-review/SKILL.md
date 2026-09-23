---
name: literature-review
description: 做文献调研与 Related Work。当用户要求找相关工作、比较若干系统、梳理某个方向的方法差异、或撰写/修订 Related Work 章节时使用。按方法学差异组织而非逐篇摘要，先出结构化对比再写散文；绝不编造文献元数据。
---

# 文献综述

## 组织方式

**按方法学差异组织，不按论文逐篇摘要**（除非用户明确要求逐篇）。

先建一张对比表，再写散文。表里每行一篇，列：

```
problem | method | assumptions | workload/dataset | metrics | main finding | limitation | 与我们方法的关系
```

写 Related Work 时讲的是**各组方法的分歧在哪里**、本文落在哪一组、为什么；
不是 "X et al. proposed..., Y et al. proposed..."。

## 本项目的现有材料（先读，别重复劳动）

- `docs/literature_notes_20260921.md`
- `docs/literature_survey_20260911.md`
- `reviews/` 下的两份外部评审（含 GPT 给的定位建议）
- `paper/refs.bib` 现有条目
- `paper/sec_discussion.tex` 的 Related Work 段

## 引用红线（硬约束）

- arXiv **2608.30830** 自报对 MORI/Continuum 的 head-to-head 胜利**已被否证，禁引**。
  它的 41% goodput 损失、~10× 复活差可以引。
- **PrefixShield (2608.01657)** 已占 "admission responsibility" 术语，写作时避撞。
- **CONCUR 已中 ICML 2026**（arXiv:2601.22705 是预印本版）。不要说它是"仅预印本"。

## 不许做的事

- **不许编造**论文、作者、标题、会议、年份、URL、DOI。
- **不许凭记忆写元数据**。每条引用都要有可核实的来源；核不到就明说核不到。
- 拿不到原文时，明说「未能核实」，不要根据摘要或标题推测其方法。

## 区分

每条信息标注来源强度：

- **原文直接支持** —— 给出处（文件路径 / URL / 页码）
- **我们的解读** —— 明确写成解读
- **未能核实** —— 明说

外部检索工具可用时（`WebSearch` / `WebFetch` / `codex exec`）优先用，
并在输出里注明信息是哪来的、什么时候核的。
