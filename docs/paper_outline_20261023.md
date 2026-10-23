# 论文骨架与"故事"清单（2026-10-23 起草）

> 目标：把论文从「实验报告」改成「一个机制 + 一套论证 + 实验验证」。
> 本文件只列结构与主张；每个 claim 必须能对应到一个实验或一个推导。
> 数字只写已验证过的（来源：`docs/plan_positive_paper_20261023.md` §0.5 的盘点）。

## 一、标题候选

1. *Capacity-Accounted Admission for Long Agentic LLM Sessions*
2. *Price the Tier: Admission Control for Agentic Serving under KV Pressure*
3. *When Sessions Do Not Fit: Capacity Accounting and State-Preserving Admission*

（倾向 1 或 2：主题词 = capacity accounting + tier，不出现"评测"。）

## 二、摘要骨架（数字只用已验证的）

```
长会话 agentic 负载在显存受限单卡上装不下工作集：没有会话级准入时，
每次会话回来都整段重算（实测 3.39× 工作量差、约 10× 冗余 prefill、会话被打死）。
我们提出容量核算准入：控制器按 KV token 记账、写下确切会话集合（计划即执行），
在轮边界做状态保留挂起（复活是搬运不是重算），并按 KV 所在层级定价。
在 19 会话 / 602 步的长会话回放上，整批时间 1.43×、单会话端到端中位 1.30×、
deadline miss 由 99.4% 降到 2.3%；在 host 缓存更大的配置下收益反转，
我们用 tier 计价模型解释并预测这个边界。
```

## 三、章节结构与每节要回答的问题

| 节 | 要回答的问题 | 理论/机制 | 证据 |
|---|---|---|---|
| 1 Intro | 为什么"请求级/agent 级调度"不够？我们的三个处理分别解决什么？ | 三段论 | 动机数字（3.39×/10×/会话被打死） |
| 2 Background & Measurement | 会话长什么样：轮数、增长、工具等待、工作集 vs 池 | 分布与结构（中位/均值/p90 一起报） | 现有 trace 统计 + 无控制崩溃 |
| 3 Model | KV 容量、层级、复活 vs 重算、增长过程的假设 | A1–A4 的形式化 | 定义 + 假设清单 |
| 4 Design | 五个机制分别怎么实现、为什么这样设计、额外处理了什么 | M1–M5 | 伪代码 + 实现细节 |
| 5 Analysis | 什么时候能赢？边界在哪？ | A1 上界、A3 breakeven、A4 有效容量、A6 周期 | 推导 + 用实测参数对拍 |
| 6 Implementation | 在 SGLang/runner 上改了什么 | permit/named admission、pause/resume、tier signal | 代码/接口描述 |
| 7 Evaluation | vs B1/B2/Ours；消融；边界 | — | §4 矩阵 |
| 8 Related work | 与 Concur/Continuum/Maestro/PKAS/ThunderAgent 的边界 | — | 6 篇横查 |
| 9 Discussion | 适用范围与未解问题 | — | 诚实清单 |

## 四、Claims → Evidence 矩阵（2026-10-23 收缩后）

评测只有 **long19** 一套数据集；HiCache 默认开、ratio=2；每个方案**只跑一次**。

| 主张 | 证据 | 状态 |
|---|---|---|
| 无控制（request 级）造成大量重复 prefill、会打死会话 | A 臂 `l19_default_r2` | 待跑（等空卡） |
| 我们（C）比 request 级（A）快、工作量少、deadline miss 低 | A vs C | C 在跑；A 待跑 |
| 我们（C）比 agent 级（Concur 式，B）也更好 | B 臂 `l19_aimd2` | 待跑 |
| 机制解释：容量核算 + 状态保留的收益 | 三条 run 的逐步/逐会话分解、device/host 命中 | 待算（不额外跑实验） |
| 复活代价/层级定价的论证 | 引擎 metrics 的 device/host 命中 + 搬运/重算代价推算 | 分析，不做 hc 变化实验 |
| n=1 的不确定性 | 逐会话 / 逐步配对 + 完整分布；论文不写"显著" | 写作约束 |

## 五、写作 pattern（待抽，读 6 篇后填）

- Concur：问题 → 观察（缓存抖动）→ 控制律（AIMD）→ 分析 → 实验。
- Continuum：program 级调度 → 队列模型 → 实验。
- Maestro/ThunderAgent/PKAS/PBKV：待补。
- 共通点（假设）：先把"为什么现有做法不行"写成机制性论证，再给方法；
  实验是验证不是主体。

## 六、必须避免的写法（来自 RTAS 模拟审稿）

1. 把"点估计落在某个带内"写成"没有改善"/"更好"——要有 CI 与等价性/显著性口径。
2. 用插值/合成基线代替实测基线。
3. 只报对自己有利的时钟口径（engine vs ready 双钟都报）。
4. 结论不带范围限定（单卡/单 trace/单 SLO）。
5. 不解释引擎空转/利用率（十月线已有把柄：foyer 空转 56.7 min vs 无控制 26.1 min）。
