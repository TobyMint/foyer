# 第 15 轮 codex + 子 agent 第 7 轮：处置记录（2026-09-25）

两条线同时审的是 `foyer_bres_r2` 落地后的改动。**两边各自独立命中了同一处最严重的问题**
（§III 末段还留着被重跑推翻的 `bres` 解释），而那一处是我改漏的 —— 说明「改一条臂要清点
它出现过的所有地方」这件事，靠人肉清单不够。

codex 给 **5–15%**（上一轮 20–35%），子 agent 给了三条结论 + 三条 major。

---

## 一、两边都命中：§III 末段的 `bres` 段落（已改，本轮最重要）

**问题**：`sec_model.tex` 最后一段仍写着「`bres` 追回约 17 分钟空转，但它整体更慢，
因为保活的会话把步成本推高的幅度超过追回的空转」。干净重跑的实际值是
**空转 −9.5 分、忙时 −15.5 分、墙钟 −25.4 分**（`decomp.csv`），
即**两个分量同向下降、整条 run 更快**。这不是舍入问题，是结论反向。

**为什么漏掉**：我做连锁改动时按「`bres` 出现在哪些地方」列了 12 条清单，
但这一段里没有出现 `bres` 字样以外的线索（它写的是「追回 17 分钟」这个数），
所以按名字扫没扫到。**教训：清点应按【数字】扫，不只按【名字】扫。**
（`check_paper_numbers.py` 当时也没覆盖这段 —— 现在加了。）

**改法**：整段重写为「这个补救**有效**、但**不产生收益**」：`bres` 把空转砍掉 9.5 分、
忙时也降 15.5 分，于是快 25.4 分；但 SLO 掉 3.9 pp、相对前沿的距离不变（§V）。
并**明写这是修订**，说明早先那一版的形状来自一条后来查明受污染的测量。

## 二、子 agent 的三条

### M1（最重要）：Route 1 的「距离相同」精度主张

**问题**：我写的对照是「0.09 pp 的差 vs 同配置 repeat 的 0.5 pp 散布」。
子 agent 复算指出两处都不成立：(i) 0.5 pp 是**四条** base run 的 **SLO** 跨度，
不是两条 run 的 **Δ** 跨度；同样这四条 run 的 **Δ** 跨度是 **1.91 pp**
（+0.18 / −1.49 / −1.24 / −1.73，我用 `frontier.py` 独立复算，逐位相符）；
(ii) 只与其中一条比，换一条**符号会翻**（对 `foyer_hc_r2` 比是**好** 0.40 pp，
对 `pairA_foyerhc` 比是**差** 1.51 pp）。

**改法**：删掉 0.5 pp 那句，把论证的重心移到**斜率检验**上 ——
SLO 掉 3.90 pp，而前沿在这 25.4 分钟里自己掉 3.81 pp，残差 0.09 pp；
并**明说 0.09 pp 不是分辨率主张**，把四条 base run 的 Δ 跨度 1.9 pp 摆出来，
承认「与其中任何一条单独比都不可分辨」。可证伪的那句改成：
**要越过前沿，这条臂最多只能让掉 2.6 pp SLO，而它让了 3.9 pp。**
（这句是 89.7898 − 87.2171 = 2.5727，可直接复算。）

### M2：论文引的「干净族 τ₂ 23.8–25.7」被干净 run 打破

**问题**：`foyfix_hc` 判 clean 但 τ₂ = 27.5 ms、`foyer_rg4`（watch）27.0 ms，
下界也被 `pairA/pairB_foyerhc` 的 23.7 突破。于是「抬高 25–40%」的分母是错的，
实际是 **24–41%**。

**改法**：把区间改成**按判据可复算的集合** —— 「同一控制器族（policy 前缀
`budget3:hw=0;target=0.95`、开 HiCache）的七条干净 run，23.7–25.0 ms」，
比值改为 **24–41%**（30.9/25.0 与 33.3/23.7）。四处同步（§V、§repro、§III、图 1 图注）。
**并说明 §III 新换的两个例证为什么不在这个族里**：无控制臂根本不是控制器，
`foyfix_hc` 跑的是另一个控制器 —— 它们的步成本不参与那个区间。

### M3：表 I 脚注的「四行」列表含一条已经不是那个值的行

**问题**：脚注写「四条带旗行是 hz2 / hz0 / breshz1 / resident base，τ₂ 30.9–33.3」，
而 resident base 在同一张表里印的是 24.8 ms。

**改法**：改成「**四行曾带旗，其中三行受损**（30.9–33.3 ms），正在重测；
第四行（resident base）已重测干净，表中那一行就是新值」。

### 子 agent 的第三件事：三句新增话

- 「The three are being re-measured...」**属实**（子 agent 核了在跑的 run）；
  风险是时效 —— 三条落地后要改成完成态。**已记进 `docs/stopping_conditions_20260925.md` 第 4 条。**
- 「carry no signature of the contamination **at all**」→ 已在审阅期间改软为
  「that we can detect---one arm is one comparison」。子 agent 指出**剩下的真问题是追溯**：
  被撤下的 0.6943 当时不在任何 CSV 里。**已修**（见下）。
- 「the cancellation was a property of the contamination」的**前提句引错了**：
  原文的「两项相抵」指的是 **R̄ 与 τ₂**，不是墙钟与 SLO。**已改回 R̄/τ₂ 口径**，
  并且换成可复算的数：污染时 R̄ +9.5% 而 τ₂ +31.5%（净吞吐 −17%），
  干净时 R̄ +9.5%、τ₂ +4.2%（净 **+5.1%**）—— 根本不抵消。

## 三、codex 的三条（子 agent 未覆盖）

### Major 2：否定判决仍含三条不可比测量

**问题**：表 I 脚注与 §repro 自己声明 `hz0`/`hz2`/`breshz1` 的墙钟、SLO、Δ 不可用，
而摘要与 §V 开头的「九条无一越过」覆盖了全部九条。

**改法**：§V 开头**明写边界**，而且不放在脚注里：「三条带旗、判决**暂定**；
修正方向对我们有利（争用抬高步成本 → 把臂往下压），所以它们的距离**高估**了；
第四条（已重测）从 −7.81 收到 −1.33；**若有一条真落在线上方，标题会弱化成
『九条中六条干净、一条胜出』，本文会照写**。」

### Major 3：「梯队决定」写成了因果结论

codex 指出最接近的匹配对（`cap3_fixed` / `cap3_hc`）虽然占用率与在跑数都接近，
却跑在不同日期、不同 GPU，而同卡容量控制还排在队里。

**处置：不改标题与主张，但已核实在三处都写明了这个混淆。**
摘要：「that pair is two runs on two days, so we also have a capacity control in
the queue that changes the pool size alone on one card; we report it when it lands」；
§III：「The caveat is that this pair is two runs on two different days and two
different GPUs, not a paired experiment」。**§IV 当时其实没有这句**（我先前写"§IV：同句"
是错的，codex 第 16 轮指出）——§IV 只有更强的「cross-policy association, not a
transportable causal derivative」，没点名日期/卡。已补一句点名，
并注明同卡配对已排队（`docs/prereg_tierpair_20260925.md`）。**不做进一步弱化的理由**：
分层对照（device-only 族 vs host-tier 族，同 trace、同引擎、同模型、同池子大小）
不依赖那一对；`cap3_fixed`/`cap3_hc` 只是最干净的单点说明。预注册的容量控制
（`docs/prereg_halfpool_20260924.md`）落地后会直接检验它。

### Major 4：「低于插值线」≠「被某条静态策略支配」

codex 说 §II 自己承认没跑时间片混合策略，摘要与结论应保留这个限定。
**已核实保留**：摘要写的是「none is above the static Pareto front」，
图 1 图注写的是「a policy below or on it has not beaten a static cap, because
time-slicing two caps approximates any point on the segment between them」——
两处都是插值口径，没有声称被某条实测策略支配。**无需改动。**

## 四、其余 minor（全部已改）

| 项 | 处置 |
|---|---|
| 图 3 图注「六行带 ‡」 | 改「五行」；并在检查器里加了带旗行数的核对 |
| 图 2 图注说五条带旗柱「忙时被抬高」 | 改为「其中三条实测抬高、两条只是标了窗口」 |
| §III 把 `horizon=1` 重复 run 的「数字不可用」说得过宽 | 限定到「引擎 token 计数及其导出量」；说明它的墙钟与 SLO 照用 |
| §VI 的 1.7% / 0.06% 在 `repeat_spread.csv` 里查不到 | **表改成两位小数**（1.59% / 0.02%），正文改引 0.02–6.08%（十组） |
| `cap1` 分时段 τ₂ 跳变只在 `docs/` 手抄序列里 | **新增 `gen_tau2_windows.py` → `tau2_windows.csv`**，按半小时桶重算；正文改引桶中位（20.3–20.9 / 21.3, 27.1, 21.1；t85 29.8→22.3–22.6；rl99 32.4→25.2, 25.1），**并说明为什么不用更细的桶**（更细的桶噪声大、支撑不起分钟级主张，所以不做那个主张） |
| 被撤下的 0.6943 追不到 CSV | **新增 `gen_superseded.py` → `superseded.csv`**（新旧并排，逐列） |

## 五、自检

`check_paper_numbers.py`：**331 项、0 MISS**（本轮从 317 加到 331：
归因表 12 行三列连查、superseded.csv 四项、tau2_windows 七项、§III 三个例证九项）。
编译 **23 页、0 Overfull、无 undefined**。

## 六、本轮暴露的一条方法论问题

**连锁改名要按【数字】清点，不只按【名字】清点。** §III 末段没有任何 `bres` 字样，
只有「17 分钟」这个数，名字扫描扫不到；两条独立审查线都抓到了它，说明这类残留
只能靠「把每个数当线索回去找它属于谁」。已加进 CLAUDE.md。


---

## 七、自查发现的两处（不是审查提的，是自己扫出来的）

### 7.1 论文唯一那条「越线」经不起它自己的重复

补 `slo_sensitivity.py` 的臂列表时（原来缺 `hz1_r2` 与 `sf0_r2`），发现：

**`horizon=1` 在 20 s 阈值下读 +1.5 pp（论文唯一一处「有控制器越线」），
它自己的重复读 −2.3 pp** —— 不只是落回带内，而是落到线**下方**、在带外。
两条同配置 run 在这条轴上差 3.8 pp（SLO 94.4% vs 91.1%），判决的符号随之翻转。

这改了三处：
- 摘要：「at a loose latency threshold one variant appears above the front in a
  single measurement, and that variant's own repeat lands 2.3 points below it,
  so the crossing does not reproduce」；
- §VI 阈值表：加了一行 `horizon=1 (repeat)`，−6.8 / −5.6 / −2.3；
- §VI 段：把「越线」的论证从「裕度不可分辨」升级为「**越线不复现**」，
  两条理由并列（旧的那条保留，因为它是锚点散布的问题，与这条不同）。

**这是加强而不是削弱**：论文的立场本来就是「零条越过」，现在连那条唯一的例外
都有了自己重复的反证。

### 7.2 `slo_sensitivity.py` 自己重建了一遍前沿

同一个 Δ 在它和表 I 里差一位小数：**它写死舍入到 0.1 分的墙钟、又自己从
`stat` 字典重建包络**，而表 I / §V 用的是 `frontier.py` 的 `FRONT`。改成
**import `frontier.py` 的 `FRONT`、墙钟从 `table1.csv` 读全精度**之后，
两条臂的 10 s 距离变了（base −1.3→−1.2、bres −1.4→−1.3），已同步正文。

这又是 CLAUDE.md 纪律 2 那一条（两条管线算同一个量必须共用定义），
**这次是自查扫出来的，不是审查抓的** —— 说明那条纪律要主动去查，不能等。
