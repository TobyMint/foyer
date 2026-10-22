# 审查范围：**两条新 run 落地 + 头条改写之后**的当前状态（只审这一批）

## 背景（事实，请**独立复核**，不要采信）

2026-09-27，两条实验落地，论文随之改写：

### ① `pois200_foyer_scan_r3` —— 第三次读数**没有复现越线**

| run | 墙钟 | SLO | 前沿 | **Δ** | 判词 |
|---|---|---|---|---|---|
| `pois200_foyer_scan` | 266.3133 | 88.5886 | 87.2842 | **+1.3044** | ABOVE |
| `pois200_foyer_scan_r2` | 262.6125 | 88.8889 | 86.7289 | **+2.1600** | ABOVE |
| **`pois200_foyer_scan_r3`** | **271.7073** | **88.3884** | **88.0936** | **+0.2948** | **ON（带内）** |

**三次全距 1.8651 pp；越线 2/3；首跑与第三次相差 1.0096 pp（> 判带本身）。**

⚠ **这是跑前预注册的分支 (b)**，写在 `scripts/lab/lane_scan_r3.sh` 头部：
「第三条落回带内 ⇒ 2/3，头条必须退回『三次里两次越线，第三次在带内』，并写明是哪一次、读数多少。」

### ② `pois200_foyer_hc_slru` —— 驱逐政策对照，无差

`slru` 的 round-1+ 命中率 **80.5%**，对照 `lru`（`foyer_hc`）**80.6%**，trace 计划 **80.87%**。
预注册分支 (a)：落在 host-tier 已观测带 78.7–80.7% 内 ⇒ 命中率对驱逐策略不敏感。
正文原写「we varied admission policy, **not eviction policy**」，已照实改为测过了。

## 这一批的改动清单（**都要核**）

1. **头条改了 10 处**（摘要、`sec_intro`、`sec_results`、`sec_discussion`、结论）：
   `lands above it twice` → `twice in three runs … the third on the line`
2. **新加一句**：`the arm's own three span 1.87 pp---more than that band, its first and third
   differing by 1.01 pp---so two of three, not a reproducible crossing`
3. 就绪时钟那组：`$-0.56$ and $+0.96$` → `$-0.56$, $+0.96$ and $-1.07$`
4. **§VI 有一句原本是错的、这次被新读数暴露并改对**：
   `it is the one on which nothing crosses` → `on it no run rises above the line`
   （`scan_r3` 在就绪时钟下 +0.29 → −1.07，**确实跨出了带**，只是没往上越线）
5. **重复散布重算**：scan 组自己的全距 0.8556 → **1.8651**；「0.5 to 4.6 pp」那个区间**未变**
   （min = hz2 0.5128、max = hz1 4.6480）；`replicates.csv` 的 `slo_range_pp` **下界 0.3 → 0.5**
6. **表 I 加一行** `scans the queue (3rd run) & 271.7 & 2.29 & 88.4 & +0.29`
7. **一批派生计数变了**：host-tier 26→**thirty**、ready 时钟 35→**三十七**、
   clean runs 15→**十七**、projection 25→**二十七**、表 I 脚注 21→**二十二**、
   stall 15→**十七**、§III 全集 37→**三十九**、§VI 松散端 5→**six**、就绪时钟跨带 6→**seven**
8. **为守住第 11 页压了约 60 词纯连接词**

## 请做的（A：逐条验「这一批改对了没有」）

**逐条独立复核**，给「成立 / 不成立 + 你的复算值」。回 `paper/*.tex`、`paper/data/*.csv` 自己算。

1. **三条 scan 读数的 Δ 与判词**：用 `frontier.front_slo()` 独立复算（**不要用 `table1.csv`**）。
   核 +1.3044 / +2.1600 / +0.2948 与判词 ABOVE/ABOVE/ON。
2. **`scan_r3` 干净吗**：`results/night/pois200_foyer_scan_r3/` 的 `metadata.json`
   （池 101432±20、policy、memfrac、四个代码哈希）与 `scan`/`scan_r2` **逐字段比**；
   `steps.jsonl`（999 步、`failed=0`、`prompt_len` 合计 = 28,526,871）、`gpu_watch.jsonl`（窗内有没有外人）。
3. **`hc_slru` 干净吗**：同上；并核 `metadata` 里**唯一的差别**就是那个 `--radix-eviction-policy slru`
   （policy 串、量、trace 应与 `foyer_hc`/`foyer_hc_r2` 逐字相同）。
4. **头条 10 处逐处核**：有没有**漏改**的（同一主张换词说过的地方）？
   grep 全稿 `lands above`、`two points`、`both runs`、`both of its runs`、`reproducibly`、
   `+1.3 and +2.2`、`crosses the front`。
5. **重复散布重算**：逐组用 `runs_precise.csv` + `frontier.front_slo()` 算 Δ 全距
   （base / hz1 / hz2 / scan / sf0），核「0.5 to 4.6」与「最紧的是 horizon=2」是否仍成立。
6. **一处「原本是错的」**：§VI 那句改对了吗？**在旧读数下它是真错还是碰巧成立**？
7. **表 I 那一行**：逐字对 `gen_table.py` 的输出；`\label{tab:runs}` 还在吗？全稿 `\ref` 有没有悬空？
8. **60 词的连接词压缩有没有压掉限定语**：对比 `git` 无历史，
   **用 `paper/supplement_material*.md` 与正文对拍**，或核 `check_paper_numbers.py` 的 `NORE=1` 输出。

## 请做的（B：反向问 —— **这一批有没有引入新错**）

9. **`gen_repeat_spread.py` 新加的 `ev`（驱逐政策）轴对不对**：
   核 `foyer_hc_slru` 与 `foyer_hc` **确实被分到两组**（它们的 policy 串逐字相同）；
   核**其余 24 组**的成员/政策/trace 有没有被这个改动意外改变。
10. **`check_paper_numbers.py` 的两处来源统一**：host-tier 条数现在读 `eviction.csv`（30 行），
    另一处读 `reuse.csv`（26 行）—— 核**统一之后哪个数是对的**，以及**正文印的是不是它**。
11. **一批派生计数**：上面第 7 条那 9 个数，逐个从数据现算，核正文印的是不是它们。
12. **摘要 265 词（上限 265）**：核它真的 ≤ 265，且**没有被压掉限定语**。
13. **正文是否仍是 11 页**：`pdfinfo` + `pdftotext -f N -l N main.pdf - | grep -c "R EFERENCES"` 逐页判。
    并核 `??` = 0、0 Overfull、0 Float too large。

## 硬约束

- **只读**。扰动在 `/tmp` 沙箱，写入前断言 `os.path.realpath(p)` 以沙箱路径开头。
- **不要用 `git checkout`**（工作区就是最新版本，全未提交）。
- 实验机 `ssh lab-3090` 可用；脚本在 `/data/xbw/turnstile/scripts/`，结果在 `/data/xbw/turnstile/results/night/`。
- 不要重审全稿、不要提篇幅目标、不要编造文献。
- 报告格式：逐条「结论 + 复算值 + 出处」。确证无误的也写一行。
- 最后单列「**我核不动/核不了的**」，写清为什么，不许猜。
