# 停止条件对照（2026-09-25 00:2x 状态）

目标是「持续完成 paper，推到实在没法再推进为止」。停止条件是三条同时满足。
这一页把每条对应到可核对的东西上。**上一版在 `docs/stopping_conditions_20260924.md`。**

## 一、论文自洽、无已知错误，所有数字可追溯到脚本或日志

**现状：满足，且这一条有机械护栏。**

- `check_paper_numbers.py`：**317 项检查、0 MISS**（55 项是「论文只印聚合值」的次要档，
  逐条列出供扫一眼）。查的是【正文 ↔ 数据文件】的逐项一致。
  **2026-09-25 新增 55 项**：归因表（此前完全没有检查）、§III 的两个例证、
  重复对散布、`replicates.csv` 的区间。
- 编译：**23 页、0 Overfull、无 undefined 引用**；禁用文献（2608.30830 / 2608.01657）不在库里。
- 所有生成器都有「缺 run 就报错」护栏（`gen_concurrency` 140、`gen_gate_attrib` 40、
  `gen_projection` 45、`gen_reuse_x` 退非零、`gen_occupancy`/`gen_eviction` 直接退出）。
- **2026-09-25 新增两条**：`gen_gate_attrib` 只算跑完的 run（在跑的 run 日志长度任意，
  实测把 all-rows 中位数从 30.6 拖到 27.3）；`gen_eviction` / `gen_repeat_spread`
  各有一份 `SUPERSEDED` 名单，把「被重跑替代的旧测量」排除在判据之外。

**已知的、无法消除的边界**：本机镜像不等于实验机全集；凡「对 run 集合计数」的生成器
必须在实验机上跑。论文引这类数必须同时给出集合规模（已写进 CLAUDE.md）。

## 二、每一轮审查提的问题都已处置，或明确说明为何不处置

**现状：满足到第 15 轮，第 15 轮在跑。**

| 轮次 | 记录 | 结果 |
|---|---|---|
| codex r8–r11 | `reviews/codex_r*`、`docs/finding_*.md` | 逐条处置 |
| 第 12 轮（codex + 子 agent） | `docs/finding_review_r12_disposition_20260924.md` | 25 处改动，全部处置 |
| 第 13 轮（子 agent 复核 + codex） | `docs/finding_review_r13_disposition_20260924.md` | 7 条 major + 9 条 minor 全部处置；未处置项写明理由 |
| 第 14 轮（codex） | `docs/finding_review_r14_disposition_20260924.md` | 3 项 MATCH、2 处改、2 处表述 |
| 第 15 轮（codex） | `reviews/codex_r15_20260925.md` | 针对 bres_r2 落地的改动 |
| 子 agent 第 7 轮 | 进行中 | 范围收紧到三件事（Route 1 改写、§III 换例证、新增句子的强度） |

**本轮（bres_r2 落地）的处置**记在 `docs/finding_rerun_bres_20260925.md`，12 条连锁改动。

## 三、该跑的实验都跑完，或明确说明为何跑不了

**现状：第一条重跑 + realhr 补全已落地；队列排满，两条车道。**

- **2026-09-25 已落地**：
  - `pois200_foyer_bres_r2`（第一条争用臂的干净重跑，**改写了一条结论的推理**）；
  - realhr 补全扫描 `cap5`/`cap6`/`cap8`（把第二条 trace 的 R̄ 从 1.29 推到 1.50）
    + 两个重复对 `cap4_r2`/`foyer_r2`；
- **在跑**：`foyer_hz0_r2`（GPU 2）、`foyer_hz2_r2` + `foyer_breshz1_r2`（GPU 3）；
- **排队**（`wait_and_launch.sh` 链式，严格 2 车道）：`cap5_hc`/`cap6_hc`/`cap8_hc`（HiCache
  推到高 R̄）→ 半池因果实验 `cap2_hp`/`cap3_hp`/`cap4_hp` → `cap1_r2`（队尾，确认性质）；
- **跑不了的**：lab-A100 的方向 D（第二配置复现）。判据是「空闲 >60GB 且 util <20%」，
  实测该机 GPU0/1/2 的 util 长期 49–100%，waiter 挂着但整夜没出现窗口。
  **宁可交白卷也不产出被同机争用污染的数据** —— 已写进论文 Limitations。

## 四、如果要继续推，还差什么

1. 三条争用臂重跑落地 → `python3 scripts/lab/swap_superseded.py <old> <new> --apply`
   （新增脚本，一次改完 20 处引用并打印重生成命令）→ 按 `docs/finding_rerun_bres_20260925.md`
   的清单改正文 → `check_paper_numbers.py` 到 0 MISS；
2. `cap5_hc`/`cap6_hc`/`cap8_hc` 落地 → host-tier 集结延伸到高 R̄，检验「host tier 守住兑现率」
   是否在 R̄ > 1.8 仍成立（这是主线主张的直接检验）；
3. 半池实验落地 → §IV 的因果段从「已排队」改成实测（判据已预注册在
   `docs/prereg_halfpool_20260924.md`）；
4. **定稿前必须重跑一次 `gen_concurrency.py`**：正文写了「十四条 CONTESTED」，
   而这个计数会随新 run 落地而变；
5. 全部落地后：codex + 子 agent 各一轮，然后收紧页数（23 页，没有硬性上限，
   但 §V 与 §III 有几段可以压）。
