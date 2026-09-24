# 停止条件对照（2026-09-24 21:05 状态）

目标是「持续完成 paper，推到实在没法再推进为止」。停止条件是三条同时满足。
这一页把每条对应到可核对的东西上，方便判断还差什么。

## 一、论文自洽、无已知错误，所有数字可追溯到脚本或日志

**现状：基本满足，且这一条现在有机械护栏。**

- `check_paper_numbers.py`：**262 项检查、0 MISS**（49 项是「论文只印聚合值」的次要档，
  逐条列出供扫一眼）。它查的是【正文 ↔ 数据文件】的逐项一致。
- `audit_numbers.py`（正文数字 ↔ 任何文件）：残留 18 处，全部属于允许来源 ——
  配置常量（101,432）、两条数据相减/相除得到的差（43.7、3.5、2.44、93.3、13.89、13.15、6.3）、
  配置阈值（6.7，在 `gate_attrib.csv` 的注释行里）、以及来自 trace 文件与原始日志的量
  （87,821、29.1 s、70.7/67.1）。
- `data_run_coverage.py`：本地镜像比实验机少 58 个 run 目录，**全部**属于
  「在实验机上生成的那几张表」（concurrency / gate_attrib / projection）——不是缺数据。
- 编译：**22 页、0 Overfull、无 undefined 引用**；`\cite` 键与 `refs.bib` 20 对 20 全对上；
  禁引的 2608.30830 / 2608.01657 不在库里。
- 所有生成器都有「缺 run 就报错」的护栏（`gen_concurrency` 140、`gen_gate_attrib` 40、
  `gen_projection` 45、`gen_reuse_x` 退非零、`gen_occupancy`/`gen_eviction` 直接退出）。

**已知的、无法消除的边界**：本机镜像不等于实验机全集。凡「对 run 集合计数」的生成器
必须在实验机上跑 —— 这条写在 CLAUDE.md 与 `scripts/lab/README.md` 里，三个生成器带护栏。

## 二、每一轮审查提的问题都已处置，或明确说明为何不处置

**现状：满足。** 六轮审查（codex r8–r13 与子 agent 五轮）的处置记录：

| 轮次 | 记录 | 结果 |
|---|---|---|
| codex r8–r11 | `docs/finding_*.md`、`reviews/codex_r*` | 逐条处置 |
| 第 12 轮（codex + 子 agent） | `docs/finding_review_r12_disposition_20260924.md` | 25 处改动，全部处置 |
| 第 13 轮（子 agent 复核 + codex） | `docs/finding_review_r13_disposition_20260924.md` | 7 条 major + 9 条 minor 全部处置；**未处置项写明理由**（realhr 扫描未完成前不重算弹性、页数留到最终收紧） |

**未处置的只剩两类**：① 依赖还在跑的实验（§VI 的形状段、表 I 的 ‡）；
② 页数（21→22），留到所有实验落地后一次收紧。

## 三、该跑的实验都跑完，或明确说明为何跑不了

**现状：在跑，队列排满，两条车道。**

- **已落地**：`realhr_cap8`（第二条 trace 的扫描完成，§VI/§criterion 已按它重写 ——
  判据的「贵」分支在第二条 trace 上也被触及，见 `docs/update_xtrace_cap8_20260924.md`）；
- 在跑：重跑的 `bres_r2`（约 23:30）、realhr 的 `cap4_r2`/`foyer_r2`（重复对）；
- 排队（自动串行，`wait_and_launch.sh`，严格 2 车道）：
  四条被争用臂的重跑（hz0_r2/hz2_r2/breshz1_r2/cap1_r2）、
  HiCache 推到高 R̄ 的 `cap5_hc`/`cap6_hc`/`cap8_hc`、
  **半池因果实验** `cap2_hp`/`cap3_hp`/`cap4_hp`（同一张卡、同一条 trace，只改池子）；
- **跑不了的**：lab-A100 的方向 D（第二配置复现）。判据是「空闲 >60GB 且 util <20%」，
  实测该机 GPU0/1/2 的 util 长期 49–100%，waiter 挂着但整晚没出现窗口。
  **宁可交白卷也不产出被同机争用污染的数据** —— 这条已写进论文的 Limitations。

## 四、如果要继续推，还差什么

1. 等 realhr 扫描落地 → `bash scripts/lab/update_xtrace.sh` → 改 §VI 形状段与 §criterion 的弹性段；
2. 等四条重跑落地 → 更新表 I、去掉 ‡、图注的六个空心圈 → 看判决变不变（`compare_rerun.py`）；
3. 等半池实验落地 → §IV 的因果段从「已排队」改成实测；
4. 全部落地后：codex 第 14 轮 + 子 agent 第 6 轮，然后收紧页数。
