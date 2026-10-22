# codex 第 33 轮：核第 32 轮那 9 条的修法（不重审全文）

第 32 轮你报了 8 条、独立复核子 agent 报了 3 条实质 + 3 条次要，**全部已改**，
逐条在 `docs/finding_review_r32_disposition_20260926.md`。**只核改得对不对。**

## A. 逐条核

- **A1（唯一性守卫：没有再正则，改成【正向】不变量）**：现在断言 7 个算前沿的文件
  必须 `import envelope`（`frontier.py` / `gen_a100_delta.py` / `gen_pool50.py` /
  `gen_frontier_split.py` / `gen_elasticity_x.py` / `gen_arrival_slo.py` /
  `slo_sensitivity.py`）。你上一轮那个构造（`dy=y1-y0; dx=x1-x0; y=y0+(x-x0)*dy/dx`）
  **我决定不追**：要抓它得匹配 `\* 名 / 名`，全仓库误报 16 处。
  **请判这个决定对不对**：(a) 那 16 处误报我数得对吗？(b) 有没有**误报更少**、
  又能抓住那个构造的判据？(c) 正向名单**少了谁**（还有哪个文件算前沿/包络却没在里面）？
- **A2（`gen_tierpair` 的 run 身份守卫）**：现在核 `summary.total_duration_ms_sum`
  必须等于日志里 `total_duration_ms` 的和。**请核**：这个量真的逐 run 不同吗？
  还有别的「999 行但属于别的 run」的形态能溜过去吗（例如同一个 run 的两次运行、
  或者把日志**重排**）？
- **A3（`rg4` 的 `finished` 判据）**：改成 999 步 / 0 失败，并把 attempted/failed
  落进 `named_arm` 行。**请核**：实验机上重跑后数据行是否仍未变（45 条 / 5.4% / 30.6%）？
  `finished_999_0` 的三行对不对？
- **A4（`.bbl` 守卫）**：**请核**这个路径现在堵住了吗？还有别的构建产物漏在外面吗
  （`.aux`、`.out`、`main.fls`）？
- **A5（§V 的终止原因）**：正文从「co-tenancy terminated」改成
  「`rg2` and `rg3` were stopped at 770 and 169 of the 999 steps because the
  shared cards they were on had to be returned to other users, not because they
  were damaged---and our own co-tenancy audit flags neither」。
  **请核**：这与 `docs/claim_register_20260921.md` 的「五十八·附」逐条相符吗？
  `concurrency.csv` 给这两条的标记是什么？「flags neither」这个说法准不准
  （rg2 是 watch、rg3 是 clean —— 「不被 flag」还是「不是 contested」）？
- **A6（摘要的四条路线）**：改成「nine controller variants on three routes, plus two
  arms on a fourth」。**请核**：九条臂（`gen_arm_running.py` 的 `NINE`）实际覆盖
  哪几条路线？Route 3 的两条臂（`foyer_t85`/`foyer_t90`）在不在那九条里？
  §I:31 与 §VI 结论的同步改法对不对？
- **A7（摘要的 both / §III 的 occupancy）**：摘要改成
  「reproduces the direction of both the accounting and the criterion but not their
  level」；§III 的「the same occupancy (57.4\%)」改成
  「within two points of the same mean device occupancy (57.4\% against 55.5\%)」。
  **请核**这两个数与它们各自的 CSV 列。
- **A8（§V `rg4` 的 0.6\%）**：改成「stays at 0.6\% of blocked cycles, against 0.0\%
  on every arm that leaves the gate off」。**请核**：45 行里有几行不是 0.0？

## 硬约束

- **只报有证据的问题**，指到 `文件:行号` 或具体数字。
- **不要修改任何文件**（只读）。
- 如果某条修得对，就说对 —— 编造的弱点会浪费一轮。
- ⚠ 你若需要读实验机（`ssh lab-3090`）而在沙箱里被挡，**照实说读不到**，
  不要用本地镜像的结果去代替（本地镜像对几条 run 是短的）。
