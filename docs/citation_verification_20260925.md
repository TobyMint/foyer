# 引用元数据核实（2026-09-25）

项目红线：「任何引用的标题、作者、年份都必须核实过才能进 `refs.bib`。
**不要凭记忆写文献。**」这一页记这次核了什么、怎么核的、**哪些核不了**。

核法：对每个带 `eprint` 的条目，直接抓 `arxiv.org/abs/<id>`，比对**标题与完整作者列表**。

## 一、核过的（标题 + 作者逐位相符）

| 键 | arXiv | 标题 | 作者 | 结果 |
|---|---|---|---|---|
| `zhu2026tracelab` | 2606.30560 | TraceLab: Characterizing Coding Agent Workloads for LLM Serving | 7 人（Kan Zhu 等） | ✅ **本论文的 trace 来源，这条最要紧** |
| `mori` | 2606.00866 | Idleness is Relative: … with MORI | 8 人（Tian Xia … Ion Stoica） | ✅ |
| `talaria` | 2607.17181 | Talaria: Session-Aware Serverless Serving of … | 5 人（Utopia Meng 等） | ✅ 见下 |
| `concur` | 2601.22705 | CONCUR: High-Throughput Agentic Batch Inference … | 10 人（Qiaoling Chen 等） | ✅ |
| `thunderagent` | 2602.13692 | ThunderAgent: A Simple, Fast and Program-Aware … | 10 人（Hao Kang 等） | ✅ |
| `wang2026xperf` | 2608.20370 | Benchmarking LLM Serving Systems for Agentic AI … | 6 人（Michael Wang 等） | ✅ |
| `continuum` | 2511.02230 | Continuum: Efficient and Robust Multi-Turn LLM … | 11 人（Hanchen Li 等） | ✅ |

**`talaria` 是一条「看着像编的、其实是真的」**：它的作者名是
Utopia Meng / Unicornt Zhao / Derek Li / Goalen Gao / Frank Du ——
`Utopia`、`Unicornt`、`Goalen` 都不像常见的英文名，而原来的 `note` 还写着
「author names as listed on arXiv」（说明写的时候也拿不准）。
**抓下来核完确认属实**。这一条值得记：**「名字奇怪」不是判据，核了才算。**

## 二、核不了的（照实说，不猜）

1. **`concur` 的 ICML 2026 录用**。条目里写 `Poster, Seoul, July 2026;
   OpenReview id U7c6glPdDW`。arXiv 页面的 comments 栏没提录用
   （但这不构成反证 —— 录用后不回填 arXiv 是常态）。
   `openreview.net/forum?id=U7c6glPdDW` 与 `api2.openreview.net` **都挡在
   浏览器挑战页后面**（HTTP 403 ChallengeRequiredError），核不到。
   项目 `CLAUDE.md` 的红线里记着「CONCUR 已中 ICML 2026」（那是更早建立的结论），
   本次**未能独立复核**。**不要**因为核不到就把它降级成「仅预印本」——
   红线的方向是「不要写成预印本」。
2. **`wang2026xperf` 的投稿日期看着对不上**：抓下来的页面摘要说
   「v1 submitted Fri, 19 Jun 2026」，而 ID 前缀 `2608` 是 8 月。
   ID 与标题、作者都对得上，**我倾向于是抓取工具把日期读错了**，
   但没能二次确认。不影响论文里的用法（只引它做过基准评测）。
3. **`qwen2coder`（2409.12186）与 12 条非 arXiv 条目**
   （`sarathi` / `distserve` / `mooncake` / `zheng2024sglang` /
   `kwon2023pagedattention` / `yu2022orca` / `yu2025pensieve` /
   `gao2024cachedattention` / `sun2024llumnix` / `wu2026fastserve` /
   `lin2024parrot` / `wang2025kvcachewild`）**本轮没核**。
   前一条是众所周知的论文；后 12 条是会议论文，元数据（会议名/年份）
   需要另找 DBLP 之类去核，不是抓 arXiv 能解决的。**列在这里，别当成已核。**

## 三、这一页的意义

「不许编造引用」这条红线的**可执行版本**就是这一页：
把「核过的 / 核不了的」分开写清楚，而不是笼统说「都核过了」。
下次动 `refs.bib` 时，先看这一页 —— 上面没有的条目，就是还没核过的。
