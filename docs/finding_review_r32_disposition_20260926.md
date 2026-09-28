# 第 32 轮处置（codex r32 核 r31 的修法 + 独立复核子 agent 第 16 轮）

两条线的范围：**核第 31 轮那批改动本身**。

**r31 的数字修正全部成立**（两条线各自独立复算：9.8/12.2/2.4、四个边界数、
两个比例、三个闸门百分比、摘要的数 —— **没有一个是错的**）。
但两条线又各抓到东西 —— 合计 **9 条**，全部处置。

---

## 一、codex r32

| 项 | 结论 |
|---|---|
| A1 白名单四条 | **理由成立**；`slo_sensitivity` 改前改后 **36 行打印 + 17 行 CSV 逐字相同** ✓ |
| A2 行数守卫 | codex 的**新构造**（用 `cap3_fixed` 的日志冒充 `cap3_pd`）**当轮已修**（见 2.1） |
| A3 `2.4` | 复算 9.801493 / 12.231475 / **2.429981** ✓ |
| A4 GPU 与日期 | GPU3/GPU2/GPU3 ✓；「三天半」实测 **3.59 天** ✓ |
| A5 四个边界数 | 50,688 / 50,720 / 池 50,716；75,445 / 76,085 / 池 76,074 ✓ |
| A6 两个比例 | 分子分别是 6,515,669（prompt）与 5,135,394（prefix）✓ |
| A7 三条闸门百分比 | 逐条复算相符；**但发现一个实错**（见 2.2） |
| A8 `.bbl` | **需要单独守**（见 2.3） |

### 2.1 唯一性守卫：codex 的第**三**个构造（**已处理，但换了办法**）

构造：`dy=y1-y0; dx=x1-x0; y=y0+(x-x0)*dy/dx` —— 两条形状正则都抓不到。

**我没有再加正则**：要抓它就得匹配 `\* 名 / 名`，而那在全仓库有 **16 处误报**
（`100 * x / n` 这种最常见不过的写法）。加了等于把守卫变成一张 16 行的白名单。

**改成加一条【正向】不变量**：凡算前沿/包络的 7 个文件**必须 import `envelope`**
（`frontier` / `gen_a100_delta` / `gen_pool50` / `gen_frontier_split` /
`gen_elasticity_x` / `gen_arrival_slo` / `slo_sensitivity`）。
反向测试：删掉任一个的 import → MISS ✓。
⚠ 名单里**不能放 `envelope.py` 自己**（第一版写进去了，干净状态就报假 MISS）。

> **判据的形状匹配有极限，到极限之后要换成【正向点名】。**
> 这与「值在不在正文里」换成「集合完不完整」是同一种换法。

### 2.2 `rg4` 被标成「跑完」是错的（**已改**）

生成器原来凭「`summary.json` 在不在」写 `finished=Y`，而 **`rg4` 是
998 attempted / 1 failed**（codex 抓到）。判据已统一成 **999 步、0 失败**，
并把 `attempted`/`failed` 一起落进 `named_arm` 行。
实验机重跑：`finished_999_0=N`（三条都是），**数据行逐字未变**。

### 2.3 `.bbl` 要单独守（**已改**）

改了 `refs.bib` 之后**只跑 bibtex**：fdb 里 `.bib` 的哈希更新、旧守卫通过，
而 `main.bbl` 已变、PDF 仍是旧的。已把 `.bbl` 加进比对的文件集，
反向测试（往 `main.bbl` 追加一行）→ MISS ✓。

---

## 二、独立复核子 agent 第 16 轮

**它抓到一条我自己编的东西**（3.1），这是本轮最重要的一条。

### 3.1 「co-tenancy terminated rg2/rg3」——**我编的**（**已改**）

正文写「co-tenancy terminated `rg2` at 770 of 999 steps and `rg3` at 169」。
**仓库里唯一的终止记录**（`docs/claim_register_20260921.md:4349`「五十八·附」）写的是
**「用户要求释放卡 0 / 卡 1（第二天早上，别人可能要用）」**；
而项目自己的争用审计 `concurrency.csv` 给的是 **rg2 = watch、rg3 = clean**
（都不是 CONTESTED）。**两条证据都不支持「同机争用把它掐停」这个说法。**

已改成照记录写：**卡要还给别的用户**，并明写「**不是因为它被损坏**——
我们自己的争用审计也没标记这两条」。

> 这是本项目红线（「不许编造」）的一个新变体：**数字全对，原因是编的。**
> 复核者交叉查了两份记录才发现 —— 与「`no hw` 不是 no HiCache」是同一类：
> **一个说得通的因果，不等于有出处的因果。**

### 3.2 `cap3_pd` 的目录**没有 `pois200_` 前缀**（**已改：写进 NEXT.md**）

下游全部按 `"pois200_" + name` 拼路径，而 **`frontier.py --csv` 是
`if not nm.startswith("pois200_"): continue` —— 静默跳过**。
后果：即使照清单把 `cap3_pd` 写进各列表，它也**拿不到全精度坐标**，
表 I 的 Δ 会静默回落到 1 位小数。已把「先定用 `mv` 改名还是加例外清单」写进并入清单。

### 3.3 摘要「nine controller variants spanning four routes」（**已改**）

九条（Table I）覆盖的是 **Route 1/2/4**；**Route 3 的两条臂是
`foyer_t85`/`foyer_t90`，不在那九条里**（`budget_sweep.csv` 表头自己写着
「这两条不在表 I 里」）。§VI 的「nine variants, four routes tested」是准的，
摘要那句不是。已改成 **three routes + 两条第四路线的臂**；
§I:31 与 §VI 结论同步。

### 3.4 摘要「reproduces both measurements in direction but not in level」（**已改**）

「both」指代不清（第二条 trace 的三段限定其实各不相同：复用是 in direction not in
level、弹性判据是 in sign not in place、控制器判决是 transfers weakly）。
已写明是 **the accounting and the criterion**。

### 3.5 「the same occupancy (57.4%)」不成立（**已改**）

`cap3_hc_r2` 的占用均值 57.4%，而它要重复的 `cap3_hc` 是 55.5%、
`cap3_fixed` 是 55.8% —— 差 1.9pp，不是 "the same"。
已照实改成「**within two points of the same mean device occupancy
(57.4% against 55.5%)**」，count 那句（1.53 vs 1.51）保持不变。

### 3.6 「stays at 0.6% like every arm that leaves it off」（**已改**）

`gate_attrib.csv` 的 45 条里 44 条是 **0.0**，只有 rg4 是 0.6 ——
「like」在 0.6 vs 0.0 上不字面成立。已改成「**stays at 0.6% of blocked cycles,
against 0.0% on every arm that leaves the gate off**」。
⚠ 改第一版时我把 0.6 删掉了，检查器立刻报 MISS —— **检查器挡住了「为了让措辞干净
而丢掉一个数」**，这是它少见的正面作用，值得记。

### 3.7 复核确认但**不处置**的两条

- **`87.9--92.4` 的上界依赖「每个 cap 取一条代表」**：`pairA_cap2hc`（92.45%）
  落在同一区间内。§III 的表确实一行一个 cap，摘要读者拿不到那个约定。
  复核者认为「可接受」；我也**不为摘要多花 4 个词而压别的限定**（见 r31 处置 2.9）。
- **9.8 的取法有第三个读数**（host 侧改取 `cap3_hc_r2` 得 9.6）：
  正文选 `cap3_hc` 有理由（同卡论证只能用 GPU3 那条），且下一句已说
  「we quote both rather than the one that suits the argument」。
  **不逐条列出第三个读数** —— 那会把一句话撑成一段。

---

## 三、本轮我自己另外抓到的（不在两条审查的清单里）

### 4.1 **表 I 比一页还高，底部三行被裁掉**（**已修**）

翻编译日志时看到 `Float too large for page by 124.85pt`。渲染确认：
**表 I 的最后三行（两条 AIMD）不在页面上**。根因是那张表的 caption **471 词**
（整段论证写在 caption 里）。

**为什么没人发现**：`Overfull \hbox` 与 `Float too large` 是两回事，
而我只守着前者 —— **比一页高的浮动体不产生 Overfull，它安静地切掉底部内容。**

修法：caption 收到 153 词（只留列定义），其余 351 词挪到表后的
`\paragraph{Notes to Table~I.}`，**一个字没删**；表从第 27 页移到第 13 页、完整可见。
检查器已加 `Float too large` 守卫（⚠ 第一版写成 `startswith`，
而日志前缀是 `LaTeX Warning: ` —— 永远查不到；**确定性反向测试当场戳穿**）。

## 四、状态

**27 页**、**0 Overfull**、0 undefined、**566 项检查 0 MISS**。
两条线合计 **已处置 9 条，明确不处置 2 条**（理由见 3.7），
外加我自己抓到并修掉的 1 条排版缺陷（4.1）。
