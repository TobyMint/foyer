# 2026-10 实验证据归档（atonce / 长会话线）

**归档时间**：2026-10-22（DSH 会话）
**来源**：本机 `/tmp/an/`。这些文件是 2026-10-17 ～ 2026-10-19 分析期间从实验机
`lab-3090:/data/xbw/turnstile/`（具体路径未记录）拷到本机的工作副本，
`cp -a` 保留了原始 mtime。实验机自 2026-10-19 起失联，这批文件是**本机唯一副本**；
`/tmp` 会被系统清理，因此移入仓库。

**为什么重要**：这批 run 是 2026-10-10 换线（一次性全倒 + 长会话）之后的全部原始数据，
`docs/finding_atonce_20261011.md`、`docs/DECISION_BRIEF.md`、
`docs/design_mechanism_20261016.md` §16–§25 的所有读数都来自这里。

## 目录对照（名称是分析时的短名，不一定等于实验机上的正式 run 名）

| 目录 / 文件 | 内容（据文档记载） |
|---|---|
| `long19_foyer/` | 长会话 19 会话 trace，我们的控制器（`budget3:hw=0;target=0.95;base=resident`），HiCache 开 |
| `long19_default/` | 同 trace，无控制（default），HiCache 开 |
| `big27d/` | big27（27 会话 / 957 步）无控制臂（**未核实**） |
| `big27f/` | big27 我们的控制器臂（**未核实**） |
| `l19rv/` | long19 的 revoke 判据修复后重跑（**未核实**），带 controller/admissions |
| `hc8/`、`f8/`、`vnp/`、`n1/`、`n2/` | long19 上不同配置/候选机制的裸 steps/metrics（分析中间产物，**未核实**） |
| `srv/*.log` | SGLang 服务器日志（`long19_default[_hc8]`、`long19_foyer[_hc8]`），§18/§21 的引擎侧分解出自这里 |
| `replay_big27.csv` | big27 重放 trace |
| `*.py` | 当时的一次性分析脚本（`batch.py` `decomp.py` `fair.py` `fair2.py` `gaps.py` `rate.py`） |

## ⚠ 使用纪律

1. 这些是**工作副本**，不是实验机上的正式产物目录；`metadata.json` 多数缺失，
   缺 `summary.json` 的目录不能当作“跑完”。
2. 文档已记载：10-17～10-18 的多数 run 受 **revoke 判据 bug**、**permit 文件共享 bug**、
   **热降频/重启** 影响；哪些能用、哪些作废以 `DECISION_BRIEF.md` / design doc §23–§25 为准。
3. 原始数据的正式来源、池子、trace 哈希、代码哈希在实验机的 `metadata.json` 里；
   机器恢复后应优先把这些 run 的 `summary.json`/`metadata.json`/`gpu_watch.jsonl` 补回来。
