# 六篇论文的**负载设计**横查（2026-10-10）

> 为什么做：用户 2026-10-10 提出「我们是不是应该改成 Concur 那种一次性全倒的负载」。
> 在改之前，先把这六篇论文**到底怎么发请求、用什么指标、跟谁比**逐篇查清楚。
> **所有引文都是从 PDF 原文抽的**（`pdftotext`，双栏论文用不带 `-layout` 的版本 +
> 按栏裁切核对）；标注为「推断」的地方是原文没写、由旁证得出的，**不许当引文用**。

---

## 一、总表

| 论文 | 请求怎么发 | 主指标 | baseline | 静态并发上限当 baseline？ | 硬件 |
|---|---|---|---|---|---|
| **Concur** (ICML'26) | **一次性全部提交**（明文 "offline batch"） | 端到端延迟（秒）+ speedup | SGLang / SGLang+请求级固定上限 / SGLang+HiCache | **没有**（有请求级 cap，无 agent 级） | 最多 16×H100 |
| **Continuum** (PVLDB) | **泊松到达**，横轴扫 JPS | **average job delay** + P90/P95 | vanilla vLLM / LMCache / Autellix / InferCept | **没有** | A100 / H100 / B200 |
| **PBKV** (arXiv'26-05) | 固定请求池 + 并发上限 72/24/48（**推断**） | E2E latency / per-agent TTFT / 命中率 | LRU(SGLang+HiCache) / KVFlow | **没有**（上限是共享操作点） | 8×A6000 48G |
| **PKAS** (HPDC'26) | 一次性全量 + `max_num_seqs` 512/1024（**推断**） | 吞吐（**排除重算 token**）+ 重算量 | vLLM-FCFS / Learning-to-Rank | **没有**（但 vLLM-FCFS = 贪心填满该上限） | 4×A100 40G |
| **ThunderAgent** (ICML'26) | 固定并行数扫档（自述 "i.e., batch size"） | **throughput (steps/min)**，明确排斥 tail latency | vLLM / Continuum / SGLang Gateway | **没有** | 8×H100 / 64×H100 / 8×A100 |
| **Maestro** (arXiv'26-06) | trace 驱动仿真，扫 λ∈[0.4, 5.0] req/s | **SLO attainment** + interactive queueing delay | FCFS / EDF / Oracle-SRTF | **没有** | 64×A100 |

---

## 二、逐篇要点（带原文）

### Concur
> "we evaluate the end-to-end latency of **offline batch** agentic inference under varying concurrency levels"

- Table 1 是 **batch / TP / #GPU** 三档（Qwen3-32B batch 256；DeepSeek-V3 batch 16/32/40），
  报的是**跑完这批的总秒数**：SGLang 1480s → CONCUR 362s（4.09×）。
- 次要指标是 **KV 命中率**（Table 2）：SGLang 35–80% vs CONCUR 96–97%。
- baseline 里的 "(ii) SGLang with request-level admission control, which limits concurrency
  using a fixed **request-level** cap" —— 是**请求级**上限，不是 agent 级。

### Continuum
> "we evaluate on two collected workloads running GPT-5 and using **poisson distribution for the arrival pattern of agent programs**"

- 主实验横轴是 **Jobs Per Second**，扫描区间随模型/硬件变（A100 上 SWE-Bench 0.02–0.08 JPS）。
- 论文自己承认 JPS 比以前的 serving 论文低得多：
  > "Note that the job per second rates are less than job per second reported in previous LLM serving papers."
- 负载：100 条 mini-swe-agent/SWE-Bench + 100 条 BFCL V4 Web Search（GPT-5 采），
  Table 2：SWE-Bench 每 program **10.9 轮 / 70,126 token**；BFCL **6.3 轮 / 93,256 token**。
- 主指标 **average job delay**；摘要写 "improves the average job completion times by **over 8x**"。
- **`offline` 一词全文只用于 profiling，不是负载模式。**

### PBKV
> "Following prior work [9, 24], we set the number of concurrent workflows to induce memory pressure"

> "**Below 60 workflows, evictions are too rare to differentiate any policy.** At the other extreme, LRU exhausts memory and crashes in 3/10 trials at concurrency 84 and 10/10 at 96. We therefore adopt a concurrency of 72 ... to evaluate all policies under reasonable pressure."

- **这一句是我们「±1pp」的别人的版本**：压力不够时所有策略打平。他们的应对是**把压力调上去**。
- 并发上限 72/24/48 是**所有策略共享的实验操作点**，被击败的对手只有 LRU 和 KVFlow。
- 负载：HoVer+LangChain / SWE-bench+AutoGen / FinanceBench+CrewAI。
- 指标：端到端 workflow latency、per-agent TTFT、KV 命中率。**无 SLO/deadline。**
- 结果：比 LRU 快 1.85×（latency）/ 2.03×（TTFT）。

### PKAS
> "the state-of-the-art **greedy scheduling** strategies optimistically squeeze as many inference requests together in the same batch as long as there is sufficient KV cache capacity ... inevitably leading to an inefficient cycle where the same request is scheduled and preempted repeatedly"

- **它的 baseline（vLLM-FCFS）就是「贪心填满」，与我们的 `default` 臂是同一个东西。**
- 指标：**吞吐（排除重算 token）**、重算 token 总数、queuing/prefill/TTFT/TPOT、KV 利用率。
  > "throughput (i.e., the number of effective tokens processed per second, **excluding recomputed tokens**)"
- 结果：比 vLLM 吞吐高 3.12×（NarrativeQA）/ 7.34×（codeU）。
- **没有做 `max_num_seqs` 的静态上限扫描**，所以它**没有回答**「把静态上限调低到合适值会不会同样有效」。

### ThunderAgent
> "Performance comparison ... as the **parallel workflow number (i.e., batch size)** increases."

> "overall system efficiency is governed by **sustained throughput rather than tail latency**"

- 指标：**steps per minute**。明确排斥 tail latency。
- 扫并发档：24/48/72/96（GLM-4.6）、144/168/192（Qwen3-235B）等。
- 结果：比 vLLM 1.48–3.58×，比 Continuum 1.17–3.31×。
- **它的对比是「program-aware 调度 vs request-aware 调度」，不是「动态准入 vs 静态上限」。**

### Maestro
> "we first **profile isolated executions and use the observed completion-time distribution to set workload-specific deadlines** ... **The same SLO targets are used for all baselines.**"

- **六篇里唯一用 SLO 达标率的**，而且 deadline 是按隔离 profile 定的、所有 baseline 共用。
- 负载：9 个 LLM-MAS 应用模板 + 5 个公开数据集，46,769 jobs / 144,524 stages。
- 扫描：λ 0.4→2.0 req/s（极端到 5.0），batch ratio 0.20→0.80。
- 结果：λ=2.0/batch=0.8 时 EDF 50.0% SLO → Maestro 73.6%；交互排队延迟降 84.8%。
- baseline 是 **FCFS / EDF / Oracle-SRTF**（调度算法），不是并发上限。

---

## 三、横查得到的四条（对我们直接有用）

### ① 「静态并发上限当 baseline」——**六篇里一篇都没有**

这是用户 2026-10-10 的判断，**被完全证实**。最接近的是 PKAS：它的 vLLM-FCFS baseline
就是「贪心填到 `max_num_seqs`」，但那个上限是**所有方法共享的配置**，不是一个被击败的对手；
而且 PKAS **没有做上限本身的扫描**，所以「调低上限会不会一样好」这个问题在文献里是空白。

### ② 到达过程：**只有 Continuum 用泊松**，两篇明文「全倒」，三篇没写

```
明文全倒     Concur（"offline batch"）
明文泊松     Continuum
推断全倒     PBKV（固定请求池 + 并发上限）、PKAS（全量 + max_num_seqs）
推断固定并发 ThunderAgent（自述 "batch size"）
写了 λ 但没说分布  Maestro（"request arrival rate is varied from ..."，全文 0 次 Poisson）
```

⚠ **不得**写成「已有工作都是 offline batch」——ThunderAgent 和 Maestro 原文没声明，
只能引它们的横轴定义。

### ③ 指标：**延迟 / 吞吐 / 排队延迟 / SLO 达标率**，没有一篇用「SLO vs 前沿」

- 用**端到端时间**：Concur（墙钟秒）、Continuum（average job delay）、PBKV（workflow latency）
- 用**吞吐**：PKAS（排除重算的 token/s）、ThunderAgent（steps/min）
- 用**SLO 达标率**：只有 Maestro

**注意 Maestro 的存在**：说明「deadline 达标率」在这批文献里**不是异类**，
而且它的 deadline 是**按隔离跑 profile 定出来的**、所有 baseline 共用——
这正是我们 §II 已经在做的事。

### ④ 报告的倍数范围：**1.12× ~ 8×**

```
ThunderAgent  1.48–3.58× over vLLM (throughput)
PBKV          1.85× latency / 2.03× TTFT over LRU
PKAS          3.12× / 7.34× over vLLM (throughput)
Concur        2.92–4.09× over SGLang (wall clock)
Continuum     1.12–3.66× (delay)，摘要写 "over 8x"
```

**我们的 1.84×（average job delay，200 档）落在这个区间的下缘**——
不是异类，但也不突出。用户的目标 3–4× 落在 Concur / PKAS / Continuum 的上段。

---

## 四、待办 / 悬而未决

- [ ] 我们的 `default`（无控制）与 PKAS 的 vLLM-FCFS 是同一个机制，
      但我们测出来只差 1.03×（整批时间），而他们 3.12×。
      **差别在 regime，不在机制** ⇒ 2026-10-10 已开跑长会话 + 一次性全倒的实验：
      `docs/prereg_atonce_20261010.md`（预期跑前写死）。
- [ ] Concur 的命中率对比（35% → 96%）是我们最该复现的一张表：
      它把「工作量比」直接摆出来了。**我们的对应量已经在算**
      （`atonce_report.py` 打「工作量」与「吞吐」两列，乘积 = 端到端倍数）。

## 五、更换负载的代价（用户已接受）

用户 2026-10-10 明确：「换模型的话，可能很多实验数据都不能用了。不过没事儿，问题不大。」
⇒ **既有的 207 个 run 目录与那篇写到八成的论文，在「新指标 + 新负载」下都不再是主证据**。
它们仍然有用的是：① 机制诊断（realization / ε / 内存层级）；② 反例与边界。
⚠ 但**论文正文的 882 项检查全部锚在旧负载上** —— 换负载之后那套守卫与正文的关系要重新审。
