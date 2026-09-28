# codex 第 36 轮：核**这一批**（图注条数/A100 基线/两处 stale「在排队」/AIMD 停摆的因果改正）

**范围**：2026-09-26 08:30 之后的全部改动（r35 那一批 + 我刚做的 AIMD 修正）。
之前的状态你审过（r35）。逐条记在：
- `docs/finding_review_r35_disposition_20260926.md`（你上一轮报的 6 条 + 独立复核子 agent 的 2 major + 9 minor）
- `docs/finding_aimd_stall_r2_20260926.md`（**新的，最要紧**）

## A. AIMD 停摆那一段（**这一批的核心，请重点核**）

`pois200_aimd2_paper_r2`（干净重跑）**自己停摆了**：控制器进程 13:15:37 退出（僵尸），
之后 56 分钟无人准入，停在 **989/999**，两个会话一直排队。

我从代码里查的根因：`run_matrix.py` 的 **aimd2 分支没有监督循环**，
而 budget3/foyer 分支有（`while [ ! -f summary.json ]; do <ctrl>; sleep 20; done`）。
第一次尝试的 `INTERVENTION.md` 自己就写着「aimd2 路由没有监督循环，这是缺陷所在」。

于是 §V 原句「the reaper had killed the controller **and the supervisor loop that
would have restarted it**」的**第二半是错的**（那个循环不存在）。已改成照记录写。

**请核**：
1. 上面这个根因判断对不对？`run_matrix.py` 里 aimd2 分支**真的**没有监督循环吗？
   两个分支的差异我描述得准确吗？（`scripts/` 下的 `run_matrix.py` 是本仓库的副本；
   实验机上的是权威版本，但你读不到就说读不到。）
2. §V 的新句子（`sec_results.tex` 的 AIMD 段）有没有**新引入**的过度断言？
   我刻意只说「控制器进程退出、两个会话排队、停在 989/999」这三件日志里能重算的事，
   并把「停摆多少分钟」拿掉了（那取决于我何时手动停掉）。
3. 新表 `paper/data/aimd_stall.csv`（生成器 `scripts/lab/gen_aimd_stall.py`）
   里的数能复算吗？`ctrl_gap_min` 对第一次尝试是**负的**（−260.3），
   我在表头注释里解释了，这个解释站得住吗？
4. 我写「with the supervisor loop added to that path, **is queued**」——
   这是个**当前状态**。检查器里有一条「queued 逐句列出 + 作废说法点名禁止」的守卫，
   **请找它的假通过/假 MISS**。

## B. r35 那一批（应已处置，抽核即可）

5. §VI 的 flag 计数改成「twelve on the main trace and two on the moving-load」，
   并说「四车道那件事杀掉四条」。**请从 `concurrency.csv` + `metadata.json` 复算**。
6. §VI 的「33.3 ms on the worst-affected arm」——**请核**它现在是「被 flag 的臂里 τ₂ 最大的那条」。
7. §A100「前七个十分位内相差 4 s 以内」——请从两条 run 的 `steps.jsonl` 复算
   （注意 `complete_timestamp` 是 **epoch 秒的浮点**，不是毫秒）。
8. §V 的「不放行窗口」四个数（11 / 4 / 3 / 4）**请从 `stall.csv` 复算**。

## C. 新加的守卫（请找新的假通过）

9. 这一批新加了：悬空 `\ref`/`\cite` 守卫、`today/at the time of writing` 守卫、
   `has()` 数字↔英文词双向、图注条数守卫的 `figure` 环境限定与 `\mbox{}` 剥壳、
   以及 §A100/§II/§V/§VI 的一批 `ck_near`。**请给新的构造**（不要重复你之前给过的）。

## 硬约束

- **只报有证据的问题**，指到 `文件:行号` 或具体数字。
- **不要修改任何文件**（只读）。
- 某条改得对就说对。**编造的弱点会浪费一轮。**
- ⚠ 需要读实验机（`lab-3090` / `lab-A100`）而在沙箱里被挡时**照实说读不到**。
