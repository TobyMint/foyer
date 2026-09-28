# codex 第 26 轮处置（2026-09-25 深夜）

codex 审「`cap6_hc`/`cap8_hc` 并入」这一批，**结论是「有实据的漏改与论断问题」** —— 它对。

## 一、**一条硬伤**：`$+2.87$` 不在 `$+0.46$` 和 `$+0.48$` 之间

我写的是：

> 「$+2.87$ **sits between** $+0.46$ and $+0.48$ and is an artifact of the small
> denominator」

**2.87 远大于 0.46 与 0.48 —— 它不「在两者之间」。** 我的本意是「在**序列**上被
这两个段夹着」（前一段 +0.46、后一段 +0.48），但措辞把它写成了**数值区间**。

已改成：

> 「the spike is \emph{flanked} in the sequence by $+0.46$ and $+0.48$, so the
> segments on either side of it are ordinary and the $+2.87$ is a property of
> its own denominator rather than a change of regime」

**这是这一轮最该记的一条**：一个**比喻**（「夹在中间」）被写成了**数值断言**，
而数值上它是假的。检查器当时守的是「那三个数在不在」，**守不住「它们的关系对不对」**。

## 二、**一条前沿定义不一致**：`cap6_hc` 该是最左锚点

`fig_frontier()` 的包络是**从 `runs.csv` 现算**的（`if s > best`），所以它的左端点
必然是**最快的静态点** —— 现在是 `cap6_hc`（207.8470）。
而 `frontier.py` 的 `FRONT` 是**硬编码**的四点、`gen_table.py` 的 `ENV_KEYS`
也没它，于是**表 I 把 207.8 分钟的 `cap6_hc` 报成「left of front」**。

**已加**（`FRONT` 与 `ENV_KEYS` 各一处），**核实过不移动任何已报告的 Δ**：
现有控制器臂都比 209.137 慢，插值区间不变；`foyer_rg2`（203.1 分）更快但它是
**控制器臂**、本来就不进静态包络。

**顺带修了一个格式 bug**：`d == 0` 时 `$-$%.2f % -d` 印成 `$-$-0.00`。
现在 `|d| < 5e-5` 直接标 `\emph{anchor}`（落在这条上的点就是锚点本身）。

## 三、**14 处派生量漏改**（全是区间端点）

| 处 | 旧 | 新 |
|---|---|---|
| §III host 命中 | 9.5--19.3 M | **3.1--19.3 M**（新下界 `cap8_hc`）|
| §III host-tier 的设备 miss | 21.6--27.9 M | **16.5--27.9 M**（新下界 `cap6_hc`）|
| §III 驱逐与重算之差 | 1.3--8.6 M | **1.3--15.2 M**（新上界 `cap6_hc`）|
| §Discussion `reuse_frac` | 0.5497--0.6981（20 条）| **0.4511--0.6981**（22 条）|
| §Discussion round-1+ 命中 | 「every cap we ran: 80.7/79.6/78.7」| 加 **77.3 / 74.3 / 53.1**，并把「every cap」限定为「as long as the cap stays inside what the pool can hold」|
| §III idle 端点 | 7.3% / 7.6% | **6.3% / 6.5%**（最快 run 变成 `cap6_hc`）|
| §III「28 runs」 | 28 | **30** |

**四处措辞也要改**（不只是数）：§III 的「最低点是全关节流臂」→ **`cap8_hc`**；
§I 的「the decline disappears」与「recomputation is flat」都要**限定在控制器区间**。

## 四、**新增 9 条检查**（区间端点这一类此前**零覆盖**）

host 命中区间、host-tier 的设备 miss 区间、驱逐差区间、`reuse_frac` 区间、
idle 的两端、hitrate 的 cap5/6/8 三个读数。

**反向测试**：两处一起改 → 报 MISS ✓；改 `77.3` → 报 MISS ✓。

## 五、这一轮我犯的错（合计）

1. **`between` 写成了数值断言**（见第一节）—— 比喻与断言的混淆；
2. **`cap6_hc` 的前沿身份**在 `FRONT`/`ENV_KEYS`/图 1 三处不一致
   （图 1 是现算的、那两处是硬编码的，硬编码的漏了）；
3. `d == 0` 的格式 bug（`$-$-0.00`）；
4. 前一轮的：一批替换里一个没匹配 ⇒ **整批没写盘**，而打印显示「10 处成功」。

**共同的形状**：**「某个东西在几处各写了一份」**（前沿锚点、检查串、替换批次），
一份更新了、另一份没有。这与 `cap5_hc` 那次的「生成器与手写表分叉」是同一个形状。
