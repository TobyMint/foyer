# 请审查这个仓库（Foyer 项目）

## 任务

下面这个公开仓库是一个研究项目的全部工作记录。**请通读我指定的文件，然后从方案、代码、
证据链、以及"接下来该做什么"四个角度，给出整体意见。**

仓库：**https://github.com/TobyMint/foyer**（公开，可直接读）

请**按顺序**读这几个文件（都是纯文本，raw 链接可直接打开）：

```
1. docs/STATUS_20260922.md
   https://raw.githubusercontent.com/TobyMint/foyer/2e4d61d17c5c67aa12a854ab6fcb4b216a395864/docs/STATUS_20260922.md
   —— 169 行的当前状态快照。★ 从这里开始

2. docs/claim_register_20260921.md
   https://raw.githubusercontent.com/TobyMint/foyer/2e4d61d17c5c67aa12a854ab6fcb4b216a395864/docs/claim_register_20260921.md
   —— 3201 行、47 节的主产物，**唯一的真相来源**。太长可先读 §二十七 与 §三十七–§四十七
      （用文件内搜索定位；§二十七 在全文约 45% 处，§三十七 之后是今天新增的）

3. scripts/controller_budget3.py
   https://raw.githubusercontent.com/TobyMint/foyer/2e4d61d17c5c67aa12a854ab6fcb4b216a395864/scripts/controller_budget3.py
   —— 395 行的准入控制器。今天刚改过（见下）

4. paper/draft-v1.zh.md
   https://raw.githubusercontent.com/TobyMint/foyer/2e4d61d17c5c67aa12a854ab6fcb4b216a395864/paper/draft-v1.zh.md
   —— 936 行的论文草稿
```


> **URL 用的是提交号（`2e4d61d17c5c`）而不是 `main` 分支。** 两个原因：
> ① `raw.githubusercontent.com` 的 `main` 分支 URL 有 CDN 缓存，实测推送后十几分钟
> 仍返回旧内容——用它会导致你读到的是改动【之前】的代码；
> ② 审查本来就该针对一个固定快照。
> 想确认自己读到的是最新的，比对文件行数即可（见每个文件后面标注的行数）。

需要别的文件（`runner/src/*.rs`、`docs/three_paths_20260921.md`、
`docs/literature_notes_20260921.md`、其他 `controller_*.py`）**请直接说要哪一个**，
不要猜内容。

---

## 项目是什么

一篇论文（代号 **Foyer**），主题：**显存受限单卡上 agentic LLM serving 的准入控制**。
目标 CCF-B / 中科院二区，投稿窗口 2026 年 10–11 月。

```
硬件    单张 RTX 3090 24GB（共享机器，有别的租户）
模型    Qwen2.5-Coder-7B-Instruct + YaRN×3（96K 上下文）
引擎    SGLang v0.5.10，KV 池 101,432 token
负载    200 个真实 coding-agent 会话的轨迹重放，泊松到达 λ=0.04/s，共 999 步
度量    端到端墙钟、前缀缓存命中率、TTFT 的 SLO（<10s）达标率、实测并发
```

**Foyer 的方案**：一个准入控制器，读引擎遥测（池占用、TTFT）自己决定放几个会话进来，
用命名许可而不是标量 cap。基线是静态 cap（`cap1`…`cap5`，即"最多同时放 N 个"）。

---

## 今天（2026-09-22）发生了什么——三件事，两件是坏消息

### 1. 「调参 / 关掉节流」这条路被**四重否证**

```
§二十七  结构论证：只用池子占用做准入的控制器，其可达点【不会超过】静态前沿——
         因为对任意一个"放 N 个"的结果都有一个 cap-N 在同一位置，静态扫描已穷举前沿。
         用一个看不见缓存的信号去控制一个由缓存决定的结果，只能靠碰巧。
§三十九  实测：把静态 cap 扫描连成（墙钟 × SLO）曲线后，Foyer 的三个点落在
         静态+HiCache 插值线的【下方】0.67pp。不是"更好"，只是"更细"。
§四十三  实测：Foyer 实测并发 2.06，cap2 是 1.99，悬崖在 2.9。
         Foyer 离悬崖还有 30%——它不是"找到了安全操作点"，而是几乎停在 cap2 的位置。
§四十六  实测：把三个安全节流全部关掉，并发只从 2.06 抬到 2.62（+27%），
         代价是 SLO 从 89.8 掉到 46.1（−43.7pp），墙钟慢 42%。全表最差。
```

### 2. 「Foyer 更快」的幅度**和噪声同阶**

```
同代 Foyer+HC      279.6   289.4   (n=2)
同代 cap2+HC       294.8   304.3   (n=2)
                   ↑ 最差的 Foyer 仍比最好的 cap2 快 5.4 分钟
```

而且**门槛一换结论就反过来**：SLO ≥ 85% 时 Foyer 最快；SLO ≥ 90% 时
Foyer 三条全部够不到，只剩 cap2+HC。

### 3. 换策略第一步**今天已部署**

见下面第四节。

---

## 今天改的代码：`--charge-mode delta`

### 动机

准入块里原来这一行：

```python
base = s["ctx"] or s["prompt0"]
n = (base + forecast(s)) * args.margin
if projection + n <= budget: ...
```

`ctx` 是会话**这一轮的整轮 prompt 长度**（约 20k token）。但一个**热会话**
（跑过至少一轮又回来）的前缀**已经在引擎里**，而 `projection` 的第一项
`resident`（引擎实测占用）**已经算了它**：

```python
projection = max(resident, ctx_sum) + growth_sum
                    ↑ 引擎实测占用，已含热会话的驻留前缀
```

**再按 `ctx` 收一次，同一批 token 计费两次。** 实测支撑：

```
round 0   未命中中位 15,720 token   ← 真的要从头 prefill
round 1+  未命中中位  1,933 token   ← 前缀基本都在
会话间隔（tool_wait）中位 0.1 秒     ← 所以前缀几乎必然还在
```

### 改法（`scripts/controller_budget3.py` 里搜 `charge_mode`）

```python
ap.add_argument("--charge-mode", choices=["full", "delta"], default="full")

unc = rec.get("server_uncached_prompt_tokens")   # 引擎自己量的边际代价
if unc is not None:
    s["uncached"] = float(unc)

base = s["ctx"] or s["prompt0"]
if (args.charge_mode == "delta" and s["last_round"] >= 0
        and s.get("uncached") is not None):
    base = s["uncached"]
n = (base + forecast(s)) * args.margin
```

**实验是严格单变量的**：

```
对照   budget3:hw=0;target=0.95
处理   budget3:hw=0;target=0.95;charge=delta     ← 只多这一个参数
```

**部署安全性**：控制器有一个重启循环（一退出就从磁盘重新拉起），所以改这个文件
有"中途换控制器"的风险。**这次的边界是"新参数默认值 = 旧行为"**——运行中的进程
不重读源文件；万一半夜重启，新进程拿到默认 `full`，与旧版逐字相同。

**现在正在跑这条实验**（短 trace 上，2026-09-22 17:40 起）。

---

## 请你回答的五个问题

### A.（最重要）`charge=delta` 的逻辑对吗？

我的论证是"热会话的前缀已经在 `resident` 里，再按 `ctx` 收就是重复计费"。

**但 `projection = max(resident, ctx_sum) + growth_sum` 里的 `max` 意味着
`ctx_sum` 有 57% 的周期压过 `resident`**（实测 8784 个控制周期：
`ctx_sum` 主导 4973 次，`resident` 主导 3811 次）。

**如果 `ctx_sum` 主导，那 `resident` 根本没被计入，我的"重复计费"就不成立。**

请判断：**在这个 `max` 结构下，"重复计费"的说法还站得住吗？**
如果站不住，`charge=delta` 是不是就变成了"单纯把账放松"——那会掉 SLO，而不是修 bug？

### B. 出路（前缀身份准入）的论证有漏洞吗？

§二十七 说"用看不见缓存的信号去控制由缓存决定的结果，只能靠碰巧"。

**但**：如果池占用与缓存状态其实足够相关（池占用高 → 驱逐多 → 命中率低），
那"看不见缓存"是不是就没那么致命？我们实测到 `resident` 中位 49.2% 时
`ctx_sum` 中位 56.9%，**两者差距不大——这支持还是削弱那个前提？**

而且我们验过一条候选信号是**弱信号**：同会话相邻两轮的命中率相关性 Pearson r=0.382。

### C. 如果这条也失败，论文还剩什么？

三条候选：

```
1. 窄的      在 SLO ≥ 85% 档里最快（领先 cap2+HC 1.2–4.5%，对 2.2–4.1% 的重复极差）
2. 螺旋测量  静态 cap 越过悬崖会掉进"驱逐螺旋"，run 内部可见：
             cap3_r2 命中率 63→27 单调下滑、单步耗时 22s→66s，同配置的 cap3_fixed 稳定
3. 澄清性的  并发买不到效率（逐请求解码速率随并发不升反降）
```

**哪一条最值得做主线？还是都不够，应该换场景（更长上下文 / 更大模型 / 多租户）？**

### D. 代码里还有别的 bug 吗？

重点看 `scripts/controller_budget3.py`：

1. `projection` 的构造（`max(resident, ctx_sum) + growth_sum`）有没有量纲或语义错误？
2. `shed`（熔断时撤销最年轻的活跃会话）与 `forecast` 的交互
3. 用"上一轮的实测未命中量"作为**这一轮**的边际成本估计——这个外推在什么情况下会错得离谱？

### E. 还有什么在过度声称？

请通读 `docs/STATUS_20260922.md` 与登记表的 §三十七–§四十七，找出**我仍然说过头的地方**
——包括数字、因果方向、"实测"与"推论"的混淆。

---

## 已知的、我们自己没有答案的洞

- **控制器为什么停在 2.06 而硬件能撑到 2.9**：只答了一半，没有完整解释
- **`ctx_sum` 是否高估驻留**：引擎报 50% 占用，`ctx_sum` 报 56.9%，两者对不上
- **谁杀过 controller**（一次 29 分钟停摆）：撤回了一个解释，机制至今未知
- **同代 Foyer 只有 n=2**，是弱的一侧
- **共享机器**：别的租户占 2.8GB 就会让 KV 池算成 6 万而不是 10 万（被我们的池子守卫拒绝），
  所以**不允许在非空卡上跑**，只能等

---

## 输出要求

- **直接指出错误**，不要先肯定再转折。
- 对每个问题给**可执行的具体建议**（补哪个实验、改哪句话、删哪段代码）。
- 如果某条你已经认为站得住，**明确说站得住**——我需要知道哪些不用再改。
- **如果你认为这个项目应该换题，请直说，并说明理由。**
- 中文回答。

---

> **注**：这个仓库更早的两轮 GPT 审查在 `reviews/` 下（0909、0911）。
> 其中 0911 那一轮已经结束，结论被数据取代——**不要再重复那批问题**。
