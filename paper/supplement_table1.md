# 外移材料 —— Table I 被移出的 8 行（完整 36 行照原样）

本文档收集 2026-09-27 为适配 **RTAS 2027 技术正文 11 页硬限**，从
`paper/sec_results.tex` 的 Table I（`\label{tab:runs}`）**移出**的行。
裁决依据：codex 2026-09-27 裁决第 1、3 条 —— 正文只留「支撑三条核心结论的汇总值、
样本数和分母」，**完整 36 行**放 supplement。

**保留 28 行**（下段说明第二次落地后已由 27 变 28）：5 条前沿锚点（`cap1` / `pairB_cap2hc` / `cap3_hc_r2` / `cap4_hc_r2` /
`cap6_hc`）、无控制基线、9 条 `\sys{}` 控制器变体 + 5 条重复、扫队列臂 + 其重复、
全关节流消融、两条 AIMD。
**⚠ 2026-09-27 第二次落地后：保留 28 行、完整 36 行** —— 扫队列臂的**第三次读数**
（`foyer_scan_r3`，Δ=+0.29）进了正文表 I，所以上面那句里的「+ 其重复」现在是「+ 其两次重复」。

**移出 8 行**（全部是静态 cap）：

| 移出行的 label | run（目录名） | Wall (min) | Conc. | SLO (%) | Δ (pp) | 为什么可以移 |
|---|---|---|---|---|---|---|
| cap2 | `pois200_cap2` | 304.2 | 1.99 | 89.5 | −2.23 | 不承载任何判决；同族的 `cap2+HC` 是锚点 |
| cap3 (fixed) | `pois200_cap3_fixed` | 258.7 | 2.89 | 74.4 | −11.77 | 设备侧三点之一；判决由 `cap3+HC` 一对承担 |
| cap3 (paired, dev) | `pois200_cap3_pd` | 246.4 | 2.97 | 79.3 | −5.02 | 配对实验的 device 半边 |
| cap4 | `pois200_cap4` | 249.9 | 3.94 | 55.7 | −29.17 | 设备侧；包络左段由 `cap4+HC (repeat)` 与 `cap6+HC` 两个锚点定 |
| cap5 | `pois200_cap5` | 260.9 | 4.89 | 27.1 | −59.34 | 设备侧最后一点；不在包络的上左段 |
| cap3 (paired, +HC) | `pois200_cap3_ph` | 233.8 | 2.97 | 81.5 | −0.93 | 配对实验的 host 半边，与 `cap3+HC` 同族 |
| cap5+HC | `pois200_cap5_hc` | 227.6 | 4.74 | 47.3 | −32.84 | host 侧中间点；不在包络的上左段 |
| cap8+HC | `pois200_cap8_hc` | 241.8 | 7.63 | 9.5 | −74.10 | 兑现率低端（59.7%）的点；读数在 `reuse.csv` |

**没有移出、但正文句子点过名的两行**（有意保留，因为去掉会让 §V 的两句话失去所指）：

- `cap3+HC`（`pois200_cap3_hc`）—— §V 的「`horizon`=1 与 `cap3`+HiCache 的中位占用率
  相同（都是 57.8%）而 cap 快 19 分钟」这句靠它，`cap3_hc_r2` 的中位占用率是 59.6%，
  换过去这句就不成立了；
- `cap4+HC`（`pois200_cap4_hc`）—— §V 的「`cap4`+HC 的重复把前者挤掉」这句的两个所指之一。

**值现在在哪**：8 行的每一列都逐字留在 `paper/data/table1.csv`（有日志的那部分全精度在
`paper/data/runs_precise.csv`），由 `scripts/lab/gen_table.py` 生成 —— **一个数都没删**，
只是不再印在正文的表里。正文别处点到这些名字的地方（`§III` 的 `cap3_fixed`/`cap3_hc`
占用率对照、`§IV` 的分段弹性链 `cap1→cap2→cap3→cap4→cap5`、`§V` 的 `cap5` 对照臂、
§Related Work 的 `cap4` 兑现率）指的是**这些 run 本身**，不是「表 I 的一行」。

⚠ **两处口径有意【不跟着表缩小】**（这就是 codex 说的「保留样本数和分母」）：

1. §V 的归因口径改成「每一个静态 cap 里墙钟最接近的那条，**我们跑过的全部 cap**」，
   不是「表 I 里的静态 cap」—— 归因的对照集（`attribution.csv` 的 `nearest_static`，
   用到 `cap5` / `cap3_fixed` / `cap2`）**逐条未变**，因此 13 条臂的归因结果
   （7 归因 / 2 不可比 / 4 残差）与它们的读数**全部未变**；
2. §VI 的就绪时钟分母改成「我们测过的全部三十五个 200-session run」——
   重算过的样本数就是 **35**（`arrival_slo.csv` 的行数），它不因表变短而变小。
   ⚠ **2026-09-27 第二次落地后：37** —— `foyer_scan_r3` 与 `foyer_hc_slru` 各加一行，
   正文那句现在是「all thirty-seven 200-session runs we measured on this trace」。

## 被移出的行所承载的**输入读数**（正文 §III / §IV 的句子靠它们才能复算）

正文里有两处用到这些 run 的**聚合读数**，而表 I 从来不印 $\overline{R}_{\text{busy}}$ 与
$\tau$ —— 所以这里把两处都需要的输入补全（`paper/data/decomp.csv` 的 `running` /
`step_back_ms` / `step_perreq_ms` 三列 + `paper/data/reuse.csv` 的 `realized_frac`，
**没有一个是手抄的**）。

| run | $\overline{R}_{\text{busy}}$ | $\tau_1$ (ms) | $\tau_2$ (ms) | 兑现率 | 在表 I？ |
|---|---|---|---|---|---|
| `cap1` | 1.00 | 28.8 | 20.6 | 92.5% | 是（锚点） |
| `cap2` | 1.27 | 27.4 | 22.8 | 89.7% | **否** |
| `cap3_fixed` | 1.53 | 29.7 | 24.9 | 79.0% | **否** |
| `cap4` | 1.65 | 32.4 | 25.8 | 60.7% | **否** |
| `cap5` | 1.84 | 36.7 | 31.2 | 36.4% | **否** |
| `cap3_pd` | 1.51 | 29.0 | 24.6 | 81.5% | **否** |
| `cap3_ph` | 1.56 | 28.1 | 24.8 | 91.6% | **否** |
| `cap5_hc` | 1.75 | 30.8 | 26.8 | 87.9% | **否** |
| `cap8_hc` | 1.85 | 34.4 | 29.0 | **59.7%** | **否** |
| `pairB_cap2hc` | 1.25 | 27.0 | 22.7 | 92.4% | 是（锚点） |
| `cap3_hc` | 1.51 | 28.0 | 24.5 | 91.3% | 是 |
| `cap4_hc` | 1.73 | 29.8 | 25.7 | 90.2% | 是 |
| `cap6_hc` | 1.87 | 31.8 | 27.6 | 85.4% | 是（锚点） |

**§IV 的分段链就靠这两列**（$\epsilon=\mathrm{d}\ln\tau_1/\mathrm{d}\ln
\overline{R}_{\text{busy}}$，两位小数口径 —— 正文自己声明了这一点）：

- device-only：`cap1→cap2` **−0.208**、`cap2→cap3_fixed` **+0.433**、
  `cap3_fixed→cap4` **+1.152**、`cap4→cap5` **+1.143**（正文印 −0.21 / +0.43 / +1.15 / +1.14；
  逐位可复算，`paper/data/a100_elasticity.csv` 也存了同一条链）；
- HiCache 侧：`pairB_cap2hc→cap3_hc` **+0.19**、`cap3_hc→cap4_hc` **+0.46**、
  `cap4_hc→cap5_hc` **+2.87**（小分母，正文读的是「存在成本差」不是「斜率」）、
  `cap5_hc→cap6_hc` **+0.48**。

**§III 的「平台区不会无限延续」那个读数**（`cap8_hc` 兑现 **59.7%**）
也在这里 —— 那一行的四列（241.8 / 7.63 / 9.5 / −74.10）在下面的移出清单里，
兑现率 59.7% 在本表。

⚠ **2026-09-27（r56 中立复核 4）**：这句原来接着写「**本表最后第二行**」，
而 `cap8_hc` 在本文件的**任何一张表里都不是倒数第二** ——
8 行移出清单里它是**最后一行**、13 行 ε 表里第 **9** 行、36 行完整表里第 **16** 行。
复核者**正确地拒绝猜测**它原本想指哪张表（它可能指的是本文件里已经不存在的一个版本）。
**处置：删掉位置claim，不猜** —— 该行已由 run 名与前四个值唯一确定，
位置信息不增加任何可核内容，而**位置性引用正是本项目反复栽的一类**
（表行号、图行号、页码都会随压缩漂移）。

## Table I 的完整 36 行（`gen_table.py --full` 的现状，逐字原文）

⚠ **2026-09-27 第二次落地后更新**：`foyer_scan_r3`（扫队列臂的**第三次读数**，Δ=+0.29）
进入表 I，正文表 I 由 27 行变 **28 行**，本表由 35 行变 **36 行**。
下面那张 LaTeX 表因此**不是「改前」的快照**，而是**当前**的完整表 ——
它是 `gen_table.py <runs.csv> --full` 的逐字输出（只有 8 条静态 cap 的移出是历史事实）。
⚠ 本节的守卫（`check_paper_numbers.py` 的「表 I 的完整表里有既不在正文也不在 supplement 的行」）
要求 `--full` 的**每一行**都印在正文表 I 或本表里，所以这一行必须补在这里。

```latex
\begin{table}[tb]
  \caption{The runs we compare. \emph{Conc.} is the time-weighted mean
  number of \emph{live} sessions, not the running-request count $\overline{R}$
  of \S\ref{sec:model}: a live session is parked in a tool wait most of the time,
  so \texttt{cap5} shows 4.89 live against 1.84 running. $^\ast$The no-control
  arm writes no admission log, so its \emph{Conc.} is estimated from the
  per-step log's session spans; on the five static caps the two estimators agree
  to two decimals. $\Delta$ is the signed distance from the static envelope at
  that wall clock; \S\ref{sec:bg} defines the $\pm1.0$\,pp band.}
  \label{tab:runs}
  \centering
  \small
  \setlength{\tabcolsep}{3pt}%
  \begin{tabular}{lrrrr}
    \toprule
    Policy & Wall (min) & Conc. & SLO (\%) & $\Delta$ (pp) \\
    \midrule
    \multicolumn{5}{l}{\emph{Static caps}}\\
    no control        & 288.6 & 94.9 & 3.0 & $-$87.62 \\
    cap1$^\ddagger$   & 527.4 & 1.00 & 94.8 & \emph{anchor} \\
    cap2              & 304.2 & 1.99 & 89.5 & $-$2.23 \\
    cap3 (fixed)      & 258.7 & 2.89 & 74.4 & $-$11.77 \\
    cap3 (paired, dev) & 246.4 & 2.97 & 79.3 & $-$5.02 \\
    cap4              & 249.9 & 3.94 & 55.7 & $-$29.17 \\
    cap5              & 260.9 & 4.89 & 27.1 & $-$59.34 \\
    \midrule
    \multicolumn{5}{l}{\emph{Static caps + HiCache}}\\
    cap2+HC           & 295.0 & 1.99 & 91.6 & \emph{anchor} \\
    cap3+HC           & 236.4 & 2.93 & 81.1 & $-$1.72 \\
    cap3 (paired, +HC) & 233.8 & 2.97 & 81.5 & $-$0.93 \\
    cap3+HC (repeat)  & 230.3 & 2.97 & 81.9 & \emph{anchor} \\
    cap4+HC           & 213.0 & 3.93 & 63.4 & $-$7.55 \\
    cap4+HC (repeat)  & 209.1 & 3.87 & 68.5 & \emph{anchor} \\
    cap5+HC           & 227.6 & 4.74 & 47.3 & $-$32.84 \\
    cap6+HC           & 207.8 & 5.85 & 28.9 & \emph{anchor} \\
    cap8+HC           & 241.8 & 7.63 & 9.5 & $-$74.10 \\
    \midrule
    \multicolumn{5}{l}{\emph{\sys{} controller variants}}\\
    scans the queue (2nd run) & 262.6 & 2.41 & 88.9 & $+$2.16 \\
    scans the queue   & 266.3 & 2.34 & 88.6 & $+$1.30 \\
    scans the queue (3rd run) & 271.7 & 2.29 & 88.4 & $+$0.29 \\
    horizon$=$2 (2nd run) & 274.2 & 2.22 & 88.7 & $+$0.22 \\
    single-flight off (2nd run) & 263.5 & 2.44 & 87.0 & $+$0.13 \\
    horizon$=$2       & 271.0 & 2.28 & 87.7 & $-$0.30 \\
    single-flight off & 263.3 & 2.43 & 86.3 & $-$0.55 \\
    horizon$=$1       & 255.8 & 2.58 & 84.8 & $-$0.93 \\
    horizon$=$3 (base) & 291.3 & 2.06 & 89.8 & $-$1.24 \\
    resident base     & 265.9 & 2.41 & 85.9 & $-$1.33 \\
    horizon$=$3 (2nd run) & 293.2 & 2.07 & 89.6 & $-$1.73 \\
    horizon$=$1 (3rd run) & 274.4 & 2.37 & 85.3 & $-$3.22 \\
    horizon$=$1 (repeat) & 260.8 & 2.69 & 80.9 & $-$5.58 \\
    horizon$=$0       & 264.2 & 2.64 & 79.8 & $-$7.19 \\
    horizon$=$1, no hw & 257.0 & 2.92 & 77.6 & $-$8.31 \\
    no gate, no resv. & 272.3 & 3.25 & 66.6 & $-$21.62 \\
    running gate$=$4  & 282.3 & 3.03 & 64.3 & $-$25.39 \\
    all throttles off & 415.0 & 2.58 & 46.1 & $-$47.10 \\
    \midrule
    \multicolumn{5}{l}{\emph{Independent adaptive controller (\S\ref{sec:results:aimd})}}\\
    AIMD, paper params & 326.8 & 2.17 & 79.4 & $-$12.65 \\
    AIMD, retuned     & 264.6 & 3.87 & 52.8 & $-$34.28 \\
    \bottomrule
  \end{tabular}
\end{table}
```

## 随缩行改掉的正文句子（逐条，原值 → 新值）

| 处 | 改前 | 改后 | 依据 |
|---|---|---|---|
| Table I 的 `\caption` | 「`cap5` shows 4.89 live against 1.84 running」 | 「`cap6`+HC shows 5.85 live against 1.87 running」 | 例子的行必须在表里；`cap6`+HC 的 Conc. 5.85 取自 `table1.csv`，1.87 取自 `arm_running.csv` 的 `running_busy` = 1.865188 |
| Table I 的 `\caption` 首句 | 「The runs we compare.」 | 「The runs the results below turn on.」 | 表已是子集，不再是全部对照 run |
| Notes to Table I | （无指针） | 增一句「The supplement carries our full run table, including the eight static caps this one omits.」 | 移出的 8 行要有去处 |
| §V idle-memory 的例子 | 「`cap5` and `cap4`+HC run 1.62 and 1.60 and finish 48 minutes apart」 | 「`cap3`+HC and `horizon`=1, no hw carry the same mean running count to two decimals and finish 21 minutes apart」 | 两条旧行都移出了；新例子两条都在表里，`occupancy.csv` 的 `running_mean` 都是 1.36（`arm_running.csv` 全精度 1.359434 / 1.362595），墙钟 236.4 与 257.0 相减 20.6 → 21 |
| §V 归因口径 | 「the static cap of Table I closest to it in wall clock」 | 「the static cap closest to it in wall clock, out of every cap we ran」 | 对照集没变（仍含 `cap5`/`cap3_fixed`/`cap2`），**归因结果逐条未变** |
| §V 点名 `cap5` | 「matched against `cap5`, whose SLO is 27.1%」 | 「matched against `cap5` of the full run table, whose SLO is 27.1%」 | 同上：值没变，只是指到全表 |
| §VI 就绪时钟 | 「all thirty-five 200-session runs **in Table I**」 | 「all thirty-five 200-session runs **we measured on this trace**」 | 重算过的样本数是 35（`arrival_slo.csv` 行数），分母不跟着表缩小 |

**未改动、仍然成立的派生计数**（逐条核过，表缩了但它们指的不是「印出来的行」）：

- §V「Four of the **nine** carried the co-tenancy flag of Table I」—— 九条变体全部保留；
- §V「Two points in Fig. 1 are above the line … **two of its three rows** of Table I」——
  ⚠ **2026-09-27 第二次落地后改的**：扫队列臂现有**三次读数**，两次在线上方、
  第三次在带内（+0.29）；那句的旧措辞「two rows」已随之作废；
- §V Notes「**Two** rows of this table stopped short of 999（`rg4` 998 / no control 997）」—— 两行都保留；
- §V Notes「**One** row now carries it, `cap1`, and **five** more did in earlier versions」—— 带旗判据走 `table1.csv`，与表无关；
- §V「Of the **thirteen** arms, **seven** are attributed …」—— 归因集合未变。
