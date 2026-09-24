# 停止条件对照（2026-09-25 00:2x 状态）

目标是「持续完成 paper，推到实在没法再推进为止」。停止条件是三条同时满足。
这一页把每条对应到可核对的东西上。**上一版在 `docs/stopping_conditions_20260924.md`。**

## 一、论文自洽、无已知错误，所有数字可追溯到脚本或日志

**现状：满足，且这一条有机械护栏。**

- `check_paper_numbers.py`：**351 项检查、0 MISS**（56 项是「论文只印聚合值」的次要档，
  逐条列出供扫一眼）。查的是【正文 ↔ 数据文件】的逐项一致。
  **2026-09-25 共新增 69 项**：归因表 12 行三列连查（此前**完全没有**检查）、
  §III 的三个例证、重复对散布、`replicates.csv` 区间、`superseded.csv`、
  `tau2_windows.csv`。
- 编译：**23 页、0 Overfull、无 undefined 引用**；禁用文献（2608.30830 / 2608.01657）不在库里。
- 所有生成器都有「缺 run 就报错」护栏（`gen_concurrency` 140、`gen_gate_attrib` 40、
  `gen_projection` 45、`gen_reuse_x` 退非零、`gen_occupancy`/`gen_eviction` 直接退出）。
- **2026-09-25 新增两条**：`gen_gate_attrib` 只算跑完的 run（在跑的 run 日志长度任意，
  实测把 all-rows 中位数从 30.6 拖到 27.3）；`gen_eviction` / `gen_repeat_spread`
  各有一份 `SUPERSEDED` 名单，把「被重跑替代的旧测量」排除在判据之外。

**2026-09-25 新增一层独立复算**：`check_paper_numbers.py` 查的是【正文 ↔ `paper/data/*.csv`】，
而所有 CSV 都由 `scripts/lab/*.py` 生成 —— 若某个生成器的**定义**写错了，正文与 CSV 会
「一致地错」，检查器看不出来。新增 `scripts/lab/independent_frontier_check.py`：
**不 import 任何生成器**，从 trace 与 `steps.jsonl` 从头再实现一遍复用上界、
每个静态锚点的墙钟/SLO、以及静态上左包络与每条臂的 Δ，再与 `table1.csv` 对拍。
当前结果：**复用上界 21540371/28526871 = 75.51%、四个包络锚点、十条臂的 Δ
全部逐位相符**。

**已知的、无法消除的边界**：本机镜像不等于实验机全集；凡「对 run 集合计数」的生成器
必须在实验机上跑。论文引这类数必须同时给出集合规模（已写进 CLAUDE.md）。

## 二、每一轮审查提的问题都已处置，或明确说明为何不处置

**现状：满足到第 19 轮（全稿），全部处置。**

| 轮次 | 记录 | 结果 |
|---|---|---|
| codex r8–r11 | `reviews/codex_r*`、`docs/finding_*.md` | 逐条处置 |
| 第 12 轮（codex + 子 agent） | `docs/finding_review_r12_disposition_20260924.md` | 25 处改动，全部处置 |
| 第 13 轮（子 agent 复核 + codex） | `docs/finding_review_r13_disposition_20260924.md` | 7 条 major + 9 条 minor 全部处置；未处置项写明理由 |
| 第 14 轮（codex） | `docs/finding_review_r14_disposition_20260924.md` | 3 项 MATCH、2 处改、2 处表述 |
| 第 15 轮（codex + 子 agent 第 7 轮） | `docs/finding_review_r15_disposition_20260925.md` | 四条 major + 六条 minor 全部处置；codex 给 5–15%，主要驱动是 §III 一段残留 |
| 第 16/17/18 轮（codex 复读） | `reviews/codex_r1[678]_20260925.md` | 逐轮核「九条判决」的限定是否到位；最后一轮 6 处里 5 处 RESOLVED、1 处 PARTIALLY，已再改 |
| **第 19 轮（codex 全稿）** | `docs/finding_review_r19_disposition_20260925.md` | 5 条 major + 5 条 minor 全部处置；**其中两条 major 是我自己在这一轮引入的** |

**本轮（bres_r2 落地）的处置**记在 `docs/finding_rerun_bres_20260925.md`，12 条连锁改动。

## 三、该跑的实验都跑完，或明确说明为何跑不了

**现状：第一条重跑 + realhr 补全已落地；队列排满，两条车道。**

- **2026-09-25 已落地**：
  - `pois200_foyer_bres_r2`（第一条争用臂的干净重跑，**改写了一条结论的推理**）；
  - realhr 补全扫描 `cap5`/`cap6`/`cap8`（把第二条 trace 的 R̄ 从 1.29 推到 1.50）
    + 两个重复对 `cap4_r2`/`foyer_r2`；
- **在跑**：`foyer_hz0_r2`（GPU 2）、`foyer_hz2_r2` + `foyer_breshz1_r2`（GPU 3）；
- **排队**（`wait_and_launch.sh` 链式，严格 2 车道）：`cap5_hc`/`cap6_hc`/`cap8_hc`（HiCache
  推到高 R̄）→ 半池因果实验 `cap2_hp`/`cap3_hp`/`cap4_hp` → `cap1_r2` →
  **同卡背靠背的层级配对** `cap3_pd`/`cap3_ph`（2026-09-25 新排，预注册在
  `docs/prereg_tierpair_20260925.md`：论文的匹配对跨 19.5 小时、跨卡，
  而**梯队**正是标题主张的那个变量，这一对把它控制住）；
- **跑不了的**：lab-A100 的方向 D（第二配置复现）。**理由已换成具体的三条**
  （见 `docs/a100_window_assessment_20260925.md`）：① 旧判据（瞬时 util<20%）
  是**假阳性** —— 它连续六次报「BIG WINDOW」，而同机有三个租户在跑活跃训练
  （`yz` 三分钟前刚起一个新 job、`qcrs` 跑了 1 天 13 小时、`linchen` 14 小时）；
  ② A100 上没有 coder + YaRN 模型，换过去会同时动四条轴；
  ③ 论文因果主张最缺的那条对照（同卡、只改池子）在 3090 上，已预注册。
  新看门狗 `a100_window.sh`（按卡统计 + 持续 10 分钟判据）已挂上，窗口出现会写标记文件，
  **不自动起实验**。**宁可交白卷也不产出不可比的数据。**

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
