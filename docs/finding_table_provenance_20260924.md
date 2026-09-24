# 2026-09-24 晚：三张汇总表的出处问题（都不是算错，是「表与数据脱节」）

这一轮没有发现任何一条定性结论被推翻，但发现了**三处数据文件与正文不符**，
全部由「给手抄的表补生成器」这个动作带出来。记下来是因为它们属于同一类：
**生成器存在 ≠ 生成器跑过**。文件在，正文引它，但它是什么时候、用什么集合生成的，
没人知道。

## 1. `runs.csv` —— 一个格子的量纲是错的（量错，不是值错）

`runs.csv` 原来是从实验机 `run_summary.py` 的打印输出**手抄**的。补上
`scripts/lab/gen_runs.py`（定义与 run_summary.py 逐字相同）后逐行对照，
28 行里 25 行逐位相符，3 行不符：

| run | 列 | 文件里 | 复算 | 性质 |
|---|---|---|---|---|
| `default` | conc | **1.69** | **94.91** | **量纲错**：1.69 是 `sglang:num_running_reqs` 的均值，而表 I 的标题写明 Conc.「不是它」 |
| `foyer_breshz1` | sd_pp | 14.2 | 11.19 | 陈旧 |
| `foyer_rg4` | sd_pp | 8.9 | 8.47 | 陈旧 |

`default` 那一格之所以会错，是因为那个 arm **不写准入日志**（它没有控制器），
`tw_conc` 对它返回 `None`，而手工填表时用「在跑请求数」补了位。同一列 27 行一个口径、
1 行另一个口径，而且无声。

**影响**：正文 §V 有一句「the retuned setting ... Three runs are worse
(\texttt{cap4} at 15.8, the all-throttles-off arm at 14.4, and \texttt{breshz1} at 14.2)」
—— breshz1 真值 11.2（比 aimd2 自己的 13.2 低），所以是**两条**更差，不是三条。
已改。表 I 的 no-control 行 Conc. 由 1.69 改为 94.9，并加脚注说明该格用的是
会话跨度估计（与四条静态 cap 上的准入日志口径**逐位相符**：cap1 0.999/1.00、
cap2 1.990/1.99、cap5 4.895/4.89、cap2_25 1.954/1.95）。

## 2. `occupancy.csv` —— 生成器的名单有 23 条，文件里只有 21 行

`gen_occupancy.py` 的 `RUNS` 列了 23 条，文件是 21 行：`cap4_hc_r2` 与 `cap3_hc_r2`
是在这张表生成**之后**才跑完的，于是它们无声地不在表里。这直接让正文那句
「the two columns in `occupancy.csv` rank the twenty arms」既与文件不符、也与事实不符。
重跑后 23 行，秩相关 Spearman rho = 0.95，正文改为「twenty-three arms ... rho=0.95」。
生成器已加「缺 run 直接报错」。

## 3. `gate_attrib.csv` —— 正文引用的两个中位数在文件里查不到

§V 的稳健性声明「over every run in that file they are 27.0% and 5.4%」用的是
**全表**的上中位，而文件里只有 `eight_median`（八条臂）与 `paper_set_median`（十条臂）
两行 —— 全表那一行不存在。补上 `all_rows_median` 行之后发现：**那两个数是旧快照的**。
本地镜像 34 行给 27.0/5.4，实验机 46 行给 **27.4/5.3**。正文已改。

顺带修了 §V 一句解释：文中说八条臂「eight rather than nine because foyfix and the two
AIMD arms ... log no gate state」——但九条里的 `sf=0` 也不在八条里（它被单独用作探针，
正文上一段正是用它的）。原句没解释这一点，而审稿人对着 `gate_attrib.csv` 逐行数就会发现。

## 4. `gen_concurrency.py` 在本地跑会给出错判决（var_cap3）

本地 `results/night/` 是**部分镜像**（116 个目录 vs 实验机 145+），而本脚本的判据是
「同时活着几条车道」——少一个目录就少一条车道。本地跑把 `var_cap3` 从 **CONTESTED
判成 clean**（丢掉的 `_failed_4lane_*` 正在它窗口里）。实验机复跑：与 `paper/data/concurrency.csv`
的 140 条**判决零差异**，`var_cap3` 仍是 CONTESTED（峰值 4 条、158 分钟）。
`§discussion` 里「变负载实验有测量、无结果」的立场因此不变。

已在 `CLAUDE.md` 记下通则：**凡输出随「目录里有哪些 run」变化的生成器，必须在实验机上跑**；
新增 `scripts/lab/data_run_coverage.py` 做镜像体检。

## 复现

- `scripts/lab/gen_runs.py results/night paper/data/runs.csv`（新）
- `scripts/lab/gen_occupancy.py results/night paper/data/occupancy.csv`
- 实验机：`gen_gate_attrib.py <results>/night paper/data/gate_attrib.csv`（有 MIN_ROWS=40 护栏）
- 实验机：`gen_concurrency.py <results>/night paper/data/concurrency.csv`（有 MIN_RUNS=140 护栏）
- 自检：`scripts/lab/check_paper_numbers.py`（204 项，当前 0 MISS）
