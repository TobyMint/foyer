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

1. ~~**`concur` 的 ICML 2026 录用**~~ **✅ 2026-09-26 已独立复核**。
   条目里写 `Poster, Seoul, July 2026; OpenReview id U7c6glPdDW`。
   2026-09-25 那一次 `openreview.net` 与 `api2.openreview.net` 都挡在浏览器挑战页后面
   （HTTP 403 ChallengeRequiredError），核不到。**换了来源之后核到了**：
   ICML 2026 官方虚拟站点有该论文的 poster 页
   （`icml.cc/virtual/2026/poster/63743`，标题与十位作者与 `refs.bib` **逐位相符**），
   与该论文的 arXiv 条目（`2601.22705`）并存。
   **结论不变**（红线本来就说「不要写成仅预印本」），但现在它是**核过的**而不是继承的。
   ⚠ 仍未核：`U7c6glPdDW` 这个 OpenReview id 本身，以及「Poster」以外的录用形式。
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


---

## 四、第二轮核实（2026-09-25 05:xx，独立子 agent 审查后复验）

独立子 agent 审了全部 23 个 `\cite` 点 / 20 个唯一键。**它的每条 finding 我都自己抓原文复验了一遍**，
结果如下 —— 包括**推翻它的一条**。

### A. 已确证并**改了正文**的三条

1. **`sec_background.tex:33` —— 被引文献直接反证正文（最严重的一条）。**
   原句写 TraceLab「…but **gives no numeric mean**」。我抓 `arxiv.org/html/2606.30560v1` §6.2
   原文：**「Overall, average tool-call latency is 16.8s, but latency depends heavily on tool type.」**
   Table 7 还有完整分位（Tool execution: Avg 16.8s / P50 0.1s / P90 10.0s / P99 3.2m）。
   **它有均值，而且 16.8 s 与我们测的 15.82 s 很接近** —— 原句把一条**交叉印证**
   说成了「对方没数据」。已改成并列陈述（16.8 s 是它的，15.82 s 是我们对释放 trace 的测量）。
   这条是子 agent 报的，我独立抓原文确认后采纳。
2. **`sec_discussion.tex:142` —— `continuum` 挂在 «admission» 上，但它不做准入。**
   抓 `arxiv.org/html/2511.02230v7`：「admission」与「admit」全文 **0 次**（唯一的 "admit" 是
   "Admittedly"）。它的机制是 **TTL 钉住 + 优先级调度**（`pin_request(request, τ*)`、
   「Continnum selectively pins the KV cache in GPU memory with a time-to-live value」），
   而 CPU/DRAM offload 它当作**既有能力**（"with fast asynchronous CPU offloading provided by
   engines like LMCache"）。已拆开：`talaria` 挂 admission，`continuum` 挂 TTL 保留 + CPU offload。
3. **`refs.bib` 的 `qwen2coder` 作者表 19/24。** 抓 `arxiv.org/abs/2409.12186` 得完整 24 人，
   缺的正是第 **12/13/17/18/20** 位（`Yang Fan`、`Yichang Zhang`、`Bo Zheng`、`Yibo Miao`、
   `Yunlong Feng`）—— 是**中间跳行**不是末尾截断。已按 arXiv 顺序补齐。
   **补法**：这 5 位一律用 `{Yang Fan}` 这种 **braces 原样保留 arXiv 显示名**，
   **不对中文名做名/姓拆分猜测**（`Yang Fan` 是姓杨还是姓 Fan，arXiv 页看不出，不许猜）。

### B. **推翻子 agent 的一条**：`mooncake` 的「版本对不上」是误报

子 agent 报「bib 声称 ToS 22(4):1--38，但它核到 FAST'25 版标题与作者都不同」。
**复验结论：bib 是对的，子 agent 核错了版本。** 两条独立证据：

- DOI `10.1145/3773772` 有**多个独立来源**（另一篇 arXiv 论文的参考文献表、ACM 的
  FAST 2025 special section 导言）指向标题
  **「Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving」**、
  作者含 **Heyi Tang / Teng Ma / Shangming Cai / Yineng Zhang**（与 bib 的 13 人一致）、
  **ToS 卷 22、页 1--38**（与 bib 的 `22(4):1--38` 卷/页对上，**期号未能独立确认**）。
- FAST'25 那篇叫 **「Mooncake: Trading More Storage for Less Computation — A KVCache-centric
  Architecture for Serving LLM Chatbot」**，**9 位作者**（Ruoyu Qin 等），是**另一篇**，
  获 Erik Riedel Best Paper；ToS 版是它的**扩展版**。
  **同一个系统的会议版与期刊版标题/作者不同是常态**，不是 bib 的错。

**这一条值得记**：子 agent 抓到的是「一篇真实存在、标题对不上的论文」，
于是合理地怀疑 bib；但**怀疑的方向错了**。复验时要问的是「bib 指的是哪一版」，
而不是「我抓到的这一版和 bib 对不上」。**照单全收会把一条正确的期刊引用改成会议版。**

### C. 照实说：仍未核到的（**不要当成已核**）

| 条目 | 核什么 | 为什么核不到 |
|---|---|---|
| ~~`concur`~~ | **✅ 2026-09-26 核到**：ICML 2026 虚拟站点的 poster 页标题与十位作者逐位相符（仍未核 OpenReview id 与录用形式） | 原判据：comments 栏为空；OpenReview 挡在挑战页后。**另**：同一 v1 的 abs 页 `citation_title` 与 HTML 全文页 `<title>` 给出**两个不同标题**（…via Congestion-Based Concurrency Control / Concur: Proactive Agent-Level Admission Control…），无法判定哪个是投稿版。**按红线不改写成「仅预印本」**；投稿前人工确认。正文用法（49.1%）已抓原句核实 ✓ |
| `wang2026xperf` | 日期矛盾 | abs 页说 v1 提交 **2026-06-19**，而 ID 前缀 `2608` 是 8 月。**两次独立抓取都是 6 月 19 日**。标题与 6 位作者逐位相符 ✓。矛盾解释不了，照实标出。不影响正文用法（只引它做过 agentic 基准评测） |
| `kwon2023pagedattention` | 整条元数据 | SOSP'23，ACM 403、DBLP 取不到（HTTP 000）。**整条未核**。正文两处用它支撑「KV 池是瓶颈」「KV 是分页的」，从标题与领域共识看没问题，但**元数据我没核过** |
| `zheng2024sglang` 页码、`wu2026fastserve` 页码 | NeurIPS'24 / NSDI'26 卷期页 | 同上，ACM/DBLP 不可达 |
| 12 条非 arXiv 会议论文 | 会议名/年份/页码 | 子 agent **顺带核到了大部分起始页**（`sarathi` 117–134、`distserve` 193–210、`yu2022orca` 521、`sun2024llumnix` 173、`lin2024parrot` 929、`gao2024cachedattention` 111、`wang2025kvcachewild` 465、`yu2025pensieve` EuroSys'25 144–158 均 ✓），但**不是逐条独立复核**，仍按「弱核实」对待 |

### D. 本轮的另一处改动（非引用问题，但是同一段）

`sec_discussion.tex:181` 的 Related Work 段首原写「The prefix cache is **often proposed** as the
signal an admission policy should use.」—— 这是一句**对文献的归属性陈述却无出处**。
我搜到该方向**确实存在**（Kthena Session Boost 明确以最大化 prefix cache 命中为目标的准入控制；
KVLearn 形式化 KV 块的联合准入与驱逐），**但这两条的元数据我没核过，不写进 `refs.bib`**。
改动方式：把这个 foil **归给本文自己的早期版本**（「looks like the signal … and an earlier
draft of this paper treated it as one」）—— 与紧接的下一句「an earlier draft of this paper
conflated the two」语义连贯，且**零引用风险**。
