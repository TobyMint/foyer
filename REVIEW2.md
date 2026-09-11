# 审计响应与复审请求（2026-09-11）

> 致独立审计方：本文档逐条回应 `reviews/0909_gpt_foyer_independent_review_zh.md`（对 commit fa0095a 的审计）。
> 请以**当前 HEAD** 重新审计，判定三条致命项的修复是否成立、以及 narrowing 后的主张是否构成可信贡献。
> 所有新数据均为统一 KV 池（101,432 token, memfrac 0.85）+ 清洁 trace（999 行）下的重跑。

## 一、逐条响应

### F1（致命）clairvoyance：读取未来真值 → **已修复**

- `scripts/controller_budget3.py`：**不读任何 trace 文件**。需求估计全部来自运行时可观测量：到达体量（admission log 的 `prompt_tokens` 字段，由 runner 在 queued 事件中记录）、已完成轮次的上下文增量 EMA（冷启动用全局在线先验）、引擎水位高水位判据。
- 原 v0.5（trace 预留版）降级保存为 `controller_budget2.py` = **oracle 上界对照**。
- Runner 侧透明化：`backend.rs` 的 `max_tokens=真实 output_len + ignore_eos` 保留（全策略对称，且这是重放器的固定行为，已在论文 limitation 声明）。
- **实证**：在线版 budget3 在 25 档 hit 66.8% / 200 档 hit 67.3%——在线预测达到甚至超过 oracle 上界（200 档 budget2 52.4%，见"为什么会超过"的 shedding 讨论 §三.3）。

### F2（致命）预测对象 ≠ 获准对象 → **已修复**

- Runner 新增 `--permit-file`：JSON `{"admit": [...], "paused": [...]}`，**只有被点名的 session_id 能进入**；数量上限这个控制变量被彻底移除。
- 新增审计事件链：`queued`（到达+体量）→ `admit`/`resume`（含 prompt_tokens）→ `pause`（轮边界释放）→ `release`。
- 控制器写全量期望状态（full-state semantics），"预测谁就放谁"由构造保证。
- **实证**：`scripts/smoke_permit.py` 端到端冒烟（SMOKE PASS）；生产 run 中 pause/resume 真实触发（如 budget3@200 shed 事件 11 次，admissions.jsonl 可查）。

### F3（致命）Concur 基线失真 → **已修复，且你们的批评被数据证实**

- `scripts/controller_aimd2.py`：逐条复刻论文控制律（**仅 U<U_low 加性增长**；U>U_high∧H<H_thresh 乘性 cut；otherwise hold），观测周期可配（默认 30s 对齐原论文尺度），并用 permit 撤销实现 **step-boundary pause/resume**（正是原论文语义）。
- 失真的旧 `controller_aimd.py` 保留在仓库中仅作方法学对照。
- **实证**：忠实版在 25 档 hit 55.6%（我们失真旧版只有 12.5%——4.4 倍差距，证明你们的 baseline-invalidity 指控完全正确）；200 档 hit 48.4%。
- **预算三仍胜忠实版**：25 档 66.8% vs 55.6%（+11.2pp）；200 档 67.3% vs 48.4%（+18.9pp）。TTFT p50：1.3s vs 4.0s（25 档）、1.9s vs 5.6s（200 档）。
- 附加发现：aimd2 换 2s 观测周期即崩溃（55.6%→16.6%），budget3 在同样 2s 周期下不受影响——阈值律对采样频率敏感、前馈不敏感。`Concur+size-hint` 混合基线与完整参数网格**尚未做**（见开放项）。

### F4（高）池子错配 + oracle 未证明 → **已修复**

- 根因确认：旧矩阵 memfrac 混用（metadata 可查：114,495/76,048/101,432/72,647 四种池子）。**全部作废重跑**，P0 矩阵统一 101,432。
- cap 扫描：25 档 cap1–8 全部完成；200 档 cap3/4/5 完成（cap1/2 待补，见开放项）。悬崖完整：25 档 cap4→5→7 = 55.2→36.3→8.3%。
- 数据清洗：night200 的空请求行（HTTP 400 源头）已剔除（`scripts/clean_trace.py`）。
- 论文草稿中"统一 101,432"的旧表述已随旧矩阵作废。

### F5（高）新颖性边际 → **主张已收缩**

- 不再主张 "agent-level admission" 本身。当前主张：**在线可校准的跨轮会话需求预测 + 以其驱动的容量感知会话级准入，及其与反应式控制（忠实 Concur）和静态 oracle 的系统对比**。
- 与近邻工作的边界已写入论文草稿 §6（Concur=反馈式并发窗口；Past-Future=请求级预测；Continuum/TokenCake/Autellix/InferCept 各有定位）。
- **请复审方判断**：收缩后的主张 + 下述实证，新颖性层级是否从"边际"上调。

### F6（高）TTFT 非用户侧 + "无吞吐代价"不成立 → **承认并重构**

- 已停止"无吞吐代价"叙事。当前框架：**质量-吞吐帕累托**——budget3 站质量角（200 档 TTFT p50 1.9s、SLO 92.2%、hit 67.3%），cap3 站吞吐角（wall 249min vs 我们 669min），两者均如实呈现。
- 用户侧指标（arrival→first-token、JCT）**统计脚本在办**（见开放项）——已知方向性结论：轻载档 budget3 的 JCT 劣于 cap3（这正是不回避的代价）。

### F7（高）单次运行 + SLO 阀非安全阀 → **部分修复**

- 200 档误差棒已出：cap4 3×（49.6/52.7/51.8）、budget2 3×（56.9/51.2/**16.4**）、aimd 3×（10.8/10.7/6.6）。**budget2 的双峰崩溃（r3）成为机制脆弱性的实证**，也催生了 shedding。
- **budget3@200 的 ×3 重复今晚在跑**（明晨出）。
- SLO 阀触发占比属实（~20% 周期）——已重新定位为**负载持续恶化的常态化熔断**而非偶发安全阀，消融数据支持（nosv 拆掉后 SLO 92→63）。
- 你们做的配对 bootstrap（+7.26pp CI[4.03,10.46]）已被引用为方法学基础；×3 后将按 run 为单位重算。

### F8（高）负载嵌套/同时到达/组成混杂 → **未开始（列入路线）**

- 多 seed 分层抽样、自然轮数、Poisson/突发到达、按 agent 类型 OOD 留出——已在路线图，**本复审请勿将其计入"已完成"**。

### 中项

- 空请求清洗 ✅（1000→999）；一键统计脚本 **在办**；schedule-conservativeness × Foyer 因子实验 **未做**（engine-native 基线排队中）。

## 二、当前主数据（全部统一池 101,432，清洁 trace）

**200 会话档（决胜表）**

| 策略 | wall(min) | 失败 | hit% | TTFT p50(s) | SLO% |
|---|---|---|---|---|---|
| budget3（在线版） | 669.2 | 0 | **67.3** | **1.9** | **92.2** |
| cap3（oracle，扫描所得） | 249.4 | 0 | 59.0 | 3.5 | 76.9 |
| cap4 | 265.6 | 0 | 45.1 | 8.4 | 52.8 |
| aimd2（忠实 Concur） | 291.4 | 0 | 48.4 | 5.6 | 65.9 |
| default | 228.1 | **121** | 0.0 | 2155.6 | 0.2 |

**25 会话档**：budget3 66.8%/93.6% vs 忠实 aimd2 55.6%/75.2% vs 最优静态 cap3 63.3%/89.6%；cap 悬崖 cap4→5→7 = 55.2→36.3→8.3。

**消融 @200**：nohw（拆高水位）hit 54.0→**5.8**（承重墙）；nosf 58.5（弱影响）；nosv 51.3（SLO 68.6→63.1）。

**调参悬崖（新增）**：budget3 旋钮扫向激进（target 0.85/0.90 + margin 1.0 + 无单飞）→ hit 0.0/2.1%——默认参数位于安全边缘，机制的质量-吞吐转换是突变型。

## 三、开放项（复审时请勿视为已完成）

1. budget3@200 ×3 重复（**今晚运行，明晨出**）
2. 用户侧指标统计（arrival→first-token、JCT）与一键重建论文表的唯一统计脚本
3. `Concur+size-hint`、conservativeness×Foyer 因子、engine-native max-running 基线
4. F8 全部（多 seed/Poisson/OOD）
5. 第二模型尺寸（3B/14B）
6. aimd2 完整参数网格

## 四、请复审方回答

1. 三条致命项的修复是否达到"可信因果证据"标准？
2. 收缩后的主张（在线可校准需求预测 + 容量感知准入 + 三方对比）新颖性层级？
3. 当前证据距 CCF-B（ICDCS/Middleware/IPDPS 档）/ 二区（FGCS/JSA 档）还差什么？给出**下一批最高杠杆的 3 个实验**。
4. 200 档 wall 2.5× 的代价，在"质量-吞吐帕累托"框架下是否可辩护？
