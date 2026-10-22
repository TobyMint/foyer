# 第 25 轮审查处置（2026-09-25 傍晚）

独立子 agent 审「breshz1_r2 落地 + cap5_hc 入表」这一轮，报 **8 条 E 项 + 3 条检查器
问题 + 1 条名单不一致**。这一页记**逐条怎么处置的**，以及**它抓到的三条检查器假通过**。

**这一轮最重要的发现不是某个数字错了，而是：一次数据变动（两条 run 落地）
在正文里留下了 12+ 处过时值，而检查器一处都没报。** 全部是**派生量**
（条数、名次、区间上界、分组计数）。

---

## 一、三条**检查器假通过**（机制各不相同，都值得记）

1. **`ck(20)` 撞上 `20.9 s`。** §III 的回归模型从 18 条变 20 条，正文写的是英文词
   `eighteen`。检查写成 `ck("§III 回归的条数", len(_clean))` —— 而 `20` 作为**子串**
   在 `sec_model.tex` 里出现 15 次（`20.9\,s`、`over-20\,s`…），于是**永远通过**。
2. **`ck("+0.90")` 退化成找 `0.9`。** `has()` 对数字会试 1~4 位小数：
   `"%.1f" % 0.90` = `"0.9"` —— 而正文的 **`"+0.91"` 含有 `"0.9"`**，于是也永远通过。
   同理 `1.6` vs `1.65`。
3. **`ck("90.2")` 撞上表里 `cap4_hc` 那一格。** 静态 host-tier 的兑现下界从 90.2 变
   87.9，但 `90.2` 在 §III 的表里还是 `cap4+HC` 的**正确值**，于是全局搜照样命中。
   **`sec_discussion.tex` 里那处漏改，它一声没吭。**

**三条都改成 `ck_near`（钉在关键词附近）之后，第一次跑就各自报出 MISS。**
其中第 3 条还顺手补上了 `sec_discussion` 那处与 host-tier 条数的守卫。

## 二、处置清单

| 项 | 内容 | 处置 |
|---|---|---|
| E-1 | §III「What is left unexplained」整段失效 | 19→20、τ₁ 上界 **36.2→34.8**（36.2 来自**被污染的旧 breshz1**）、「one being re-measured」删、three→four、eighteen→twenty、r **+0.91→+0.90**、1.6→**1.65 ms**。数字我自己复算过（n=20, r=+0.896, 残差 1.65）|
| E-2 | 「八条干净、一条待重测」的叙事在 **6 处**与表 I 矛盾 | §V 开头整段重写（九条全干净、零条越过、四条修正量 11.2/6.5/6.4/4.5）、表注、§VI 争用段、§III 尾段、摘要 ×2、引言 ×2、图 1 图注、结论，**全部改净**（grep 验证无残留短语）|
| E-3 | 表注清点少一条 | `Eleven further runs`→**Twelve**；`the three arms superseded (bres, hz0, hz2)`→**four（加 breshz1）**|
| E-4 | §VI 争用段 | `three of them are rows of Table I (cap1, F:breshz1, AIMD)`→**two**；`eleven`→**twelve**；`Three further rows … re-measured`→**Four**（加 hz1 no hw）；删掉「The one remaining damaged row is still being re-measured」整句，改为 **No damaged row remains**；volume 那句改用**四条重测臂的 reuse_frac**（0.6811/0.6894/0.6904/0.6952，全在 0.5497–0.6981 内）|
| E-5 | 集合长大了，正文的条数/名次全没跟 | `nineteen`→**twenty**（6 处）、`twenty-three arms`→**twenty-four**（3 处）、Spearman ρ **0.95→0.97**（复算 0.9670）、§V 的 projection **nineteen/1.78→twenty/1.75** |
| E-6 | §IV 同节内相隔 15 行的自相矛盾 | 「three configurations and two segments / stops at 1.73」→**four / three / 1.75**；并**如实加报**第三段在「重复替代」口径下是 **−5.21（符号翻转）**——因为 `cap4_hc_r2` 的 R̄(1.76) 反而高于 `cap5_hc`(1.75)。我自己复算确认 −5.205 |
| E-7 | §V 的 all_rows 区间旧账 | `1.01 to 4.11 with a median of 1.58`→**4.13 / 1.59**（4.11 是 plus 集合的值，两个集合被混了）|
| E-8 | checker 的「图过期」判据用**全部** CSV 的 mtime | 改成从 `make_figs.py` **现推**它 `load()` 了哪些 CSV；推不出来则打一行说明再退回保守判据（不静默）|
| 名单 | `gen_frontier_split.CONTROLLERS` 含 `foyfix_hc` 却**漏了 `foyer_sf0_r2`**（最接近前沿的臂，−0.55），而论文的九条相反 | 把 `NINE` 提到 `gen_arm_running` **模块级**，`CONTROLLERS = NINE + ["foyfix_hc"]`（10 条）。改后**混合前沿下仍是 0 条在线上方**，打平 2→**3** 条 |

## 三、本轮新加的检查（421 项、0 MISS）

`§III 回归` 三条改 `ck_near` + τ₁ 上界；projection 三组 ×3；occupancy 条数与 Spearman；
host-tier 条数 ×2；§Discussion ×2。全部**反向测试过**（故意改坏 → 报 MISS → 恢复）。

## 四、检查器自身的两个洞（子 agent 发现，已补）

1. **`num_words` 的个位序数词是错的**：机械 +th 给出 `oneth/twoth/threeth/fiveth/
   eightth/nineth/twelfth`，而正文只会写 `first/second/third/fifth/eighth/ninth/twelfth`。
   本轮用的 45/5/4/7/20 恰好都没踩到（5 是靠基数词 `five` 命中的）。
   **已加不规则表**。
2. **`has(text, [])` 返回 True**：`str([])` 是 `"[]"`，会去字面匹配 LaTeX 的可选参数。
   实测 `has("XX[]YY", []) == True`。目前潜伏（.tex 里字面 `[]` 出现 0 次），
   **已改成收到空列表就 `raise`**。

## 五、我自己在这一轮犯的两个错（记下来）

1. **`gen_decomp.py` / `gen_hitrate.py` 的 run 列表我传小了**（用 `eviction.csv` 的 25 条
   而不是 `default` + `ARMS` + `STATIC` 的 29 条）。见
   `docs/finding_breshz1r2_cap5hc_20260925.md` 第二节。
2. **`ck_near` 的关键词选错**：plus 集合的值在「once the second trace's…」附近，
   我写成了「second trace is the」，得到三条**假 MISS**；另给一个**正文根本不印**的量
   （`all_rows` 的条数）加了检查，也是假 MISS。**假 MISS 和假通过一样消耗信用。**

---

## 六、处置过程中**又冒出来的两处**（子 agent 没报，是它的清单之外的）

### 1. `gen_wall_split.py` 与 `gen_arrival_slo.py` 也有名单问题

按「名单不一致」这个**模式**系统扫了一遍（凡含 `foyfix_hc` 的控制器名单，查它有没有
`foyer_sf0_r2`），又抓到两处：

- `gen_wall_split.py`：`CONTROLLERS` 同样含 `foyfix_hc`、漏 `sf0_r2`；且
  `HC_ANCHORS` 没有 `cap5_hc`。**已统一到 `gen_arm_running.NINE`**，锚点池补上
  `cap5_hc`（实测不影响任何臂的「最近锚点」选择，加它是为了集合完整）。
- `gen_arrival_slo.py`：`RUNS` 缺 `sf0_r2` —— 而它服务的是「**ready 时钟不改变判决**」
  这个稳健性论证，**漏掉最接近前沿的那条臂（−0.55）是不完整的**。
  它有 `controller.jsonl`（7945 行），不是没数据。**已加**。

### 2. 加 `sf0_r2` 之后，正文的**分组计数**是错的（而且我改错了两次）

加进去后 12 条：`sf0_r2` 的 ready 时钟是 **−0.55 → −0.89**（移动 0.34），**仍在
±1.0 band 内** —— 所以判决不变 ✓ 这是**好事**（论证更完整）。

但同一句里的分组计数「of the eleven controller arms, **nine** move by no more than
2.5 pp. **Two** move more」要重新算。真值：

    12 条中 <=2.5pp 的 9 条；>2.5pp 的 3 条
    （breshz1_r2 −3.16、foyfix_hc +8.22、aimd2 +3.22）

**注意 `breshz1_r2` 是第三条** —— 旧的 `breshz1` 不超 2.5，重跑后超了。
所以**这又是一处落地残留**（子 agent 的清单里没有，因为它要算 2.5pp 这个统计才看得见）。

**我自己在这一步连错两次**：先手算成「10 条 <=2.5」，改错了正文；补检查时才发现真值
是 9，再改回来，并把「Two」改成「Three」。**已加两条检查**（`<=2.5pp` 的条数与
`>2.5pp` 的条数），并做了反向测试（故意写回 `ten` → 报 MISS → 恢复 → 0 MISS）。

### 3. 这一轮我引入/犯的错误合计四处

1. `gen_decomp`/`gen_hitrate` 的 run 列表传小了（25 而非 29）；
2. `ck_near` 关键词选错，得到三条**假 MISS**；
3. 给一个**正文根本不印**的量加了检查（假 MISS）；
4. 上面第 2 条的「10 条」——**手算挤掉了脚本**，而本项目的规矩是「手算的表一定会错」。

第 4 条尤其值得记：**我明明就在改一个「该由脚本算的分组计数」，却先手算了一遍。**
# 第 25 轮审查处置（2026-09-25 傍晚）

独立子 agent 审「breshz1_r2 落地 + cap5_hc 入表」这一轮，报 **8 条 E 项 + 3 条检查器
问题 + 1 条名单不一致**。这一页记**逐条怎么处置的**，以及**它抓到的三条检查器假通过**。

**这一轮最重要的发现不是某个数字错了，而是：一次数据变动（两条 run 落地）
在正文里留下了 12+ 处过时值，而检查器一处都没报。** 全部是**派生量**
（条数、名次、区间上界、分组计数）。

---

## 一、三条**检查器假通过**（机制各不相同，都值得记）

1. **`ck(20)` 撞上 `20.9 s`。** §III 的回归模型从 18 条变 20 条，正文写的是英文词
   `eighteen`。检查写成 `ck("§III 回归的条数", len(_clean))` —— 而 `20` 作为**子串**
   在 `sec_model.tex` 里出现 15 次（`20.9\,s`、`over-20\,s`…），于是**永远通过**。
2. **`ck("+0.90")` 退化成找 `0.9`。** `has()` 对数字会试 1~4 位小数：
   `"%.1f" % 0.90` = `"0.9"` —— 而正文的 **`"+0.91"` 含有 `"0.9"`**，于是也永远通过。
   同理 `1.6` vs `1.65`。
3. **`ck("90.2")` 撞上表里 `cap4_hc` 那一格。** 静态 host-tier 的兑现下界从 90.2 变
   87.9，但 `90.2` 在 §III 的表里还是 `cap4+HC` 的**正确值**，于是全局搜照样命中。
   **`sec_discussion.tex` 里那处漏改，它一声没吭。**

**三条都改成 `ck_near`（钉在关键词附近）之后，第一次跑就各自报出 MISS。**
其中第 3 条还顺手补上了 `sec_discussion` 那处与 host-tier 条数的守卫。

## 二、处置清单

| 项 | 内容 | 处置 |
|---|---|---|
| E-1 | §III「What is left unexplained」整段失效 | 19→20、τ₁ 上界 **36.2→34.8**（36.2 来自**被污染的旧 breshz1**）、「one being re-measured」删、three→four、eighteen→twenty、r **+0.91→+0.90**、1.6→**1.65 ms**。数字我自己复算过（n=20, r=+0.896, 残差 1.65）|
| E-2 | 「八条干净、一条待重测」的叙事在 **6 处**与表 I 矛盾 | §V 开头整段重写（九条全干净、零条越过、四条修正量 11.2/6.5/6.4/4.5）、表注、§VI 争用段、§III 尾段、摘要 ×2、引言 ×2、图 1 图注、结论，**全部改净**（grep 验证无残留短语）|
| E-3 | 表注清点少一条 | `Eleven further runs`→**Twelve**；`the three arms superseded (bres, hz0, hz2)`→**four（加 breshz1）**|
| E-4 | §VI 争用段 | `three of them are rows of Table I (cap1, F:breshz1, AIMD)`→**two**；`eleven`→**twelve**；`Three further rows … re-measured`→**Four**（加 hz1 no hw）；删掉「The one remaining damaged row is still being re-measured」整句，改为 **No damaged row remains**；volume 那句改用**四条重测臂的 reuse_frac**（0.6811/0.6894/0.6904/0.6952，全在 0.5497–0.6981 内）|
| E-5 | 集合长大了，正文的条数/名次全没跟 | `nineteen`→**twenty**（6 处）、`twenty-three arms`→**twenty-four**（3 处）、Spearman ρ **0.95→0.97**（复算 0.9670）、§V 的 projection **nineteen/1.78→twenty/1.75** |
| E-6 | §IV 同节内相隔 15 行的自相矛盾 | 「three configurations and two segments / stops at 1.73」→**four / three / 1.75**；并**如实加报**第三段在「重复替代」口径下是 **−5.21（符号翻转）**——因为 `cap4_hc_r2` 的 R̄(1.76) 反而高于 `cap5_hc`(1.75)。我自己复算确认 −5.205 |
| E-7 | §V 的 all_rows 区间旧账 | `1.01 to 4.11 with a median of 1.58`→**4.13 / 1.59**（4.11 是 plus 集合的值，两个集合被混了）|
| E-8 | checker 的「图过期」判据用**全部** CSV 的 mtime | 改成从 `make_figs.py` **现推**它 `load()` 了哪些 CSV；推不出来则打一行说明再退回保守判据（不静默）|
| 名单 | `gen_frontier_split.CONTROLLERS` 含 `foyfix_hc` 却**漏了 `foyer_sf0_r2`**（最接近前沿的臂，−0.55），而论文的九条相反 | 把 `NINE` 提到 `gen_arm_running` **模块级**，`CONTROLLERS = NINE + ["foyfix_hc"]`（10 条）。改后**混合前沿下仍是 0 条在线上方**，打平 2→**3** 条 |

## 三、本轮新加的检查（421 项、0 MISS）

`§III 回归` 三条改 `ck_near` + τ₁ 上界；projection 三组 ×3；occupancy 条数与 Spearman；
host-tier 条数 ×2；§Discussion ×2。全部**反向测试过**（故意改坏 → 报 MISS → 恢复）。

## 四、检查器自身的两个洞（子 agent 发现，已补）

1. **`num_words` 的个位序数词是错的**：机械 +th 给出 `oneth/twoth/threeth/fiveth/
   eightth/nineth/twelfth`，而正文只会写 `first/second/third/fifth/eighth/ninth/twelfth`。
   本轮用的 45/5/4/7/20 恰好都没踩到（5 是靠基数词 `five` 命中的）。
   **已加不规则表**。
2. **`has(text, [])` 返回 True**：`str([])` 是 `"[]"`，会去字面匹配 LaTeX 的可选参数。
   实测 `has("XX[]YY", []) == True`。目前潜伏（.tex 里字面 `[]` 出现 0 次），
   **已改成收到空列表就 `raise`**。

## 五、我自己在这一轮犯的两个错（记下来）

1. **`gen_decomp.py` / `gen_hitrate.py` 的 run 列表我传小了**（用 `eviction.csv` 的 25 条
   而不是 `default` + `ARMS` + `STATIC` 的 29 条）。见
   `docs/finding_breshz1r2_cap5hc_20260925.md` 第二节。
2. **`ck_near` 的关键词选错**：plus 集合的值在「once the second trace's…」附近，
   我写成了「second trace is the」，得到三条**假 MISS**；另给一个**正文根本不印**的量
   （`all_rows` 的条数）加了检查，也是假 MISS。**假 MISS 和假通过一样消耗信用。**

---

## 六、处置过程中**又冒出来的两处**（子 agent 没报，是它的清单之外的）

### 1. `gen_wall_split.py` 与 `gen_arrival_slo.py` 也有名单问题

按「名单不一致」这个**模式**系统扫了一遍（凡含 `foyfix_hc` 的控制器名单，查它有没有
`foyer_sf0_r2`），又抓到两处：

- `gen_wall_split.py`：`CONTROLLERS` 同样含 `foyfix_hc`、漏 `sf0_r2`；且
  `HC_ANCHORS` 没有 `cap5_hc`。**已统一到 `gen_arm_running.NINE`**，锚点池补上
  `cap5_hc`（实测不影响任何臂的「最近锚点」选择，加它是为了集合完整）。
- `gen_arrival_slo.py`：`RUNS` 缺 `sf0_r2` —— 而它服务的是「**ready 时钟不改变判决**」
  这个稳健性论证，**漏掉最接近前沿的那条臂（−0.55）是不完整的**。
  它有 `controller.jsonl`（7945 行），不是没数据。**已加**。

### 2. 加 `sf0_r2` 之后，正文的**分组计数**是错的（而且我改错了两次）

加进去后 12 条：`sf0_r2` 的 ready 时钟是 **−0.55 → −0.89**（移动 0.34），**仍在
±1.0 band 内** —— 所以判决不变 ✓ 这是**好事**（论证更完整）。

但同一句里的分组计数「of the eleven controller arms, **nine** move by no more than
2.5 pp. **Two** move more」要重新算。真值：

    12 条中 <=2.5pp 的 9 条；>2.5pp 的 3 条
    （breshz1_r2 −3.16、foyfix_hc +8.22、aimd2 +3.22）

**注意 `breshz1_r2` 是第三条** —— 旧的 `breshz1` 不超 2.5，重跑后超了。
所以**这又是一处落地残留**（子 agent 的清单里没有，因为它要算 2.5pp 这个统计才看得见）。

**我自己在这一步连错两次**：先手算成「10 条 <=2.5」，改错了正文；补检查时才发现真值
是 9，再改回来，并把「Two」改成「Three」。**已加两条检查**（`<=2.5pp` 的条数与
`>2.5pp` 的条数），并做了反向测试（故意写回 `ten` → 报 MISS → 恢复 → 0 MISS）。

### 3. 这一轮我引入/犯的错误合计四处

1. `gen_decomp`/`gen_hitrate` 的 run 列表传小了（25 而非 29）；
2. `ck_near` 关键词选错，得到三条**假 MISS**；
3. 给一个**正文根本不印**的量加了检查（假 MISS）；
4. 上面第 2 条的「10 条」——**手算挤掉了脚本**，而本项目的规矩是「手算的表一定会错」。

第 4 条尤其值得记：**我明明就在改一个「该由脚本算的分组计数」，却先手算了一遍。**


---

# 七、codex 第 25 轮的处置（它比子 agent 又找出 5 处）

codex 审同一批改动，**结论是「处置尚未完整」** —— 它对。它找到的与子 agent **不重叠**的有：

## A 正文（5 处，我漏的）

| 处 | 旧 | 新 |
|---|---|---|
| `sec_model.tex:12` | twenty-eight runs | **twenty-nine** |
| `sec_model.tex:124` | over the 27 runs | **28** |
| `sec_model.tex:242` | Across the nineteen host-tier runs | **twenty**（所问六处里我漏的那一处）|
| 图 4 图注 | 65.8--70.2%、20.8 s | **66.0--70.2%、20.9 s** |
| 引言 | mean 20.8 s | **20.9 s** |

**外加一处图文不一致**：`make_figs.py:143` 把 `best Foyer` 标在 **`sf0_r2`**（−0.55）上，
而 `hz2_r2` 干净重跑后是 **−0.30**、才是最近的那条（摘要也用 −0.30）。
**这是上一轮 hz2_r2 落地时就遗留的**，不是这一轮引入的。已改锚点。

**codex 还澄清了两处「不该改」**：`sec_discussion.tex:300/337` 的 `nineteen` 指的是
**ready-clock 可重算子集**（十九 of 二十五），不是 host-tier 总数 —— 我差点一并改错。

## B 检查器（4 类假通过，全部实测复现）

1. **`has()` 丢符号**：`float("+0.90")` 再格式化得 `"0.9"`，于是正文写 `+0.91`
   甚至 `-0.90` 都通过。**符号在这里是语义**（正负是相反的结论）。
   修好后全量重跑**立刻暴露 3 条**——而那三处正文其实是对的（写的是 LaTeX 的
   `$-2.3$`），所以又补上「认 LaTeX 正负号」。
2. **整数词子串**：`"twenty"` 被 `twenty-three` 命中。加了**不对称**边界：
   右侧排除连字符（挡住 `twenty-three`），左侧**不**排除（否则 `---forty-five`
   这种 LaTeX 破折号后会全成假 MISS）。
3. **projection 邻组串撞车**：`main_trace` 与 `main_plus` 的 `upper_median`
   **都是 1.75**、两处关键词相距约 60 字符，默认 260 的窗口互相覆盖。
   已按组重选**该组独有**的关键词并收窄窗口。
4. **§IV 弹性检查取了 `abs`**：把正文 `+2.87` 写成 `-2.87` 也能过。已去 `abs`。
5. **图过期判据两头都错**：漏抓图 1 直接 `open()` 读的 `concurrency.csv`（假通过）；
   又拿全部 CSV 的最新 mtime 与**每一张**图比（只更新图 8 的 `reuse_x.csv`
   会把其余七张判旧，假 MISS）。现在 `make_figs.py` 会写 `.deps.json`
   （**逐图**记录它读过哪些文件）做精确判定。
6. **`if _m4:` 静默跳过**：projection.csv 表头少一组就等于那组数字没人守。已改成报错。

## C §IV

codex 复算 **−5.20465**，确认正文的 **−5.2 正确**（不是 −5.21）。

**但它指出我加的那句是「辩解式的过度解释」**：既然分母近零、替代后**符号都翻转**，
就不能同时说第三段「locates a turn」。**它对** —— 这是自相矛盾，已删掉三处
「locates/locating a turn」，改成如实的弱断言：*平坦区间不会无限延续，但五个点
说不出它在哪里结束*。

**图 7 也漏了 `cap5_hc`**（正文讨论四段，图只画三点），已补并同步图注。

## 我自己在这一轮**又**犯的错

修 `.deps.json` 时，`fails.append` 里引用了只在新分支定义的 `newest_data` →
**`NameError` 让 checker 崩掉**。而我的反向测试 grep 的正是 `"MISS|共 "`，
**把 traceback 一起过滤掉了** ——「崩了」看起来像「通过了」。
已记进 CLAUDE.md：**反向测试没报时，先看退出码和完整输出**。
