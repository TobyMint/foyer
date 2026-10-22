# codex 第 21 轮：只审【2026-09-25 新写的生成器】与它们支撑的正文数字

范围限定，不要重审全文。上一轮（r20）刚查过数值与逻辑，这轮换一个面：
**新脚本本身算得对不对，以及正文引的数能不能追到它们。**

## 要审的文件

生成器（`scripts/lab/`）：

1. `gen_backlog.py` → `paper/data/backlog.csv`（新）
2. `gen_superseded.py` → `paper/data/superseded.csv`（新）
3. `gen_tau2_windows.py` → `paper/data/tau2_windows.csv`（新）
4. `gen_a100.py` → `paper/data/a100.csv`（新，**尚未有数据**，只审口径）
5. `independent_frontier_check.py`（新，自称「不 import 任何生成器」地独立复算前沿）
6. `swap_superseded.py`（新，改名工具；上轮它曾误改定义文件，已加三分类）

## 请回答这五个问题

1. **`gen_backlog.py` 的 `waiting_n` 口径**：它取 `controller.jsonl` 全部控制周期的
   `waiting_n`（中位 / p90 / 最大）。正文 §VII 引「中位 66 对 16，最大 135 对 25」。
   **这两个数在 CSV 里查得到吗？对得上吗？** 另外：取全部周期（不筛）是否真的是
   这个论点需要的读数，还是说某个筛选才更诚实？脚本注释声称「筛选会改变这个数，
   而它正是论点本身」—— 这个理由站得住吗？

2. **`gen_superseded.py` 的旧/新对照**：`paper/data/superseded.csv` 里
   `foyer_bres`（旧）对 `foyer_bres_r2`（新）的四个数（bres / τ₂ / 步成本 / SLO）
   是不是分别来自正确的列？**本项目已四次从错的列抄数**，请逐列核。
   `docs/finding_rerun_bres_20260925.md` 里有同样的四个数，两边是否逐位一致？

3. **`independent_frontier_check.py` 的「独立」是不是真的独立**：它声称不 import
   任何生成器、自己重算上界/锚点/Δ。**请找出它实际上与 `frontier.py` 共享的假设**
   （哪怕是隐式的：同一个 wall 来源、同一个池子判据、同一个集合定义）。
   如果它其实只是把 `frontier.py` 的算法抄了一遍，那它没有增加任何保证 ——
   这一点要明说。

4. **`gen_tau2_windows.py`**：它按半小时分桶算 τ₂。**分桶边界是否会把跨越边界的
   请求切坏？** 桶内的样本数够不够支撑正文对它的引用？

5. **`gen_a100.py` 的口径**：它注定要与 `gen_reuse.py` / `gen_decomp.py` 比
   「兑现率」。**请逐行核这三个脚本的兑现率定义是否真的逐字一致**
   （上界来源、分子、分母、R̄ 是 `busy` 还是全时段）。CLAUDE.md 纪律 2 说
   「两条管线算同一个量，必须共用定义」—— 这里是不是又犯了一次？

## 硬约束

- 只报**有证据的问题**，指到文件:行号或具体数字。不要为了显得严格而编造弱点。
- **不要生成审稿分数或接受概率**。
- 不许为了让结论好看而调口径 —— 正负都照实说。
- 最后给一个 0-100 的**中稿概率判断**（明确这是判断不是预测），并列出最该修的前三条。
