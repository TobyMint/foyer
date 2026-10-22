# 第 30 轮处置（codex r30 全稿重读 + 独立复核子 agent 第 15 轮）

两条线并行。codex 的范围是**全稿重读**（第 29 轮只审了新增的那一段）；
子 agent 的范围限定在**摘要与引言的数字**，逐个独立复算。

**两条线都推翻了东西**：codex 7 条全部成立，子 agent 1 条实质问题 + 2 条口径提示。

---

## 一、codex r30：7 条，全部处置

### 1.1 半池实验被用来支撑它测不出的东西（**已改，两处**）

`sec_model.tex:396` 写容量对照「supports in direction」，`sec_discussion.tex:619`
写「moves realization the way the claim predicts」。**两处都错**：半池实验
**不产生兑现率**（`pool50.csv` 四行全 INFEASIBLE、兑现列留空），它给的是
**服务能力的长度边界**（prompt 超过池子的步根本不被执行）。

已改：§III 改成「that version does **not** confirm in the same terms --- 它只给
长度边界，不给兑现率读数」；§discussion 改成「does not fill that gap: it returns no
realization figure … what it marks is a service boundary rather than a movement in
realization」。

> 这是本项目最贵的一类错：**把「同一个实验」当成支撑两件不同的事**。
> 同一段数据支持「容量会绑住」不等于支持「兑现率会朝预测方向动」。

### 1.2 一次前沿更新被误写成「跨出打平带」（**已改，两处**）

`sec_results.tex` 两处写最佳臂从带内移到「on the losing side of the ±1.0pp band」。
**实测**（用 `runs_precise.csv` 全精度坐标、两套锚点各算一次）：

    foyer_hz2_r2  墙钟 270.976  SLO 87.688
      旧锚点（cap4_hc / cap3_hc 首跑）  前沿 87.2792  Δ = +0.409pp  ON
      新锚点（两条重复）                前沿 87.9838  Δ = −0.296pp  ON

**两次都在带内**，是「跨过线」不是「跨出带」。已改成照实写两个读数，并点明
**锚点选择决定的是我们引用的那个数的符号**（+0.41 还是 −0.30），而我们取了
对我们不利的那一个。这一条尤其值得记：**它错的方向是「把结果说得更负面」**，
比说成正结果更不容易被抓 —— 本项目的审查一直只防「把负说成正」。

### 1.3 `cap3_pd` 已跑完但没进叙述（**已改**）

§III 原写「设备侧只有一次运行」。`cap3_pd` 999/999、0 失败，246.4 分 / SLO 79.3% /
**兑现 81.48%**（`cap3_fixed` 是 79.05%）。已补一句照实报：
取重复则 tier gap 从 **12.2 → 9.8** 点，取首跑仍是 12.2，两个都写；
并说明设备侧因此**不再是单样本**（两条差 2.5pp）。
预注册配对的判决**仍未给**（`cap3_ph` 在跑），正文写了「判据先于两条 run 写下、
落地后报判据给的判决而不是我们届时挑的那个」。

⚠ **数据表的完整并入（14 处）留到 `cap3_ph` 落地一次做**（NEXT.md 有清单）。

### 1.4 「成功且只带一个 token」按字面有反例（**已改**）

`cap2_hp` 第 12 步是 SUCCESS、生成 1 token，但它**正常服务了 27,804-token 的 prompt**
（池 50,716）且有首 token 时间 —— 它不属于退化响应那一类。**全仓库实测**：
干净 run 里**每条都有 57 个**这样的合法单 token 步（64 条 run 有），
退化步只在 4 条小池 run 里出现。判据不是输出 token 数，是**引擎自报的 prompt 计数**。

已把全称量词限定到退化口径（「marked a success while reporting **one prompt token**」），
并明写「This is not the same set as steps that generate one token: the trace contains
those in every run, including the clean ones」。

### 1.5 派生条数留旧值（**已改，两处**）

`sec_results.tex`「Two runs stopped short of 999… so these **four** are not judged」、
`sec_discussion.tex`「including the **four** runs that stopped short」。
表 I 里实际只有 **两条**（`rg4` 998、no-control 997）——
旧的 hz0(995)/hz2(997) 已被 `_r2` 取代，那两条是 999 步。
两处都改成 two/two。

### 1.6 定义唯一性守卫的**实际假通过** + 边界不一致（**已改**）

codex 独立抓到 `gen_frontier_split.py` 仍有独立插值与 `BAND = 1.0`
（**这正是我在同一时段自己抓到的，两条线撞在同一处**）。已改成结构正则守卫
（见 CLAUDE.md 2026-09-26 那条），并连带修掉 `gen_elasticity_x.py`、
`gen_arrival_slo.py` 两处同型重复。

**边界不一致**（新）：`frontier.classify(-1.0)` 返回 `BELOW`，而正文
（`sec_background.tex`）写的是「more than +1.0 算上方、**less than −1.0** 算下方、
之间算 on」—— 恰好 −1.0 应在带内。下界原来是 `delta > -TIE_PP`，已改成 `>=`。
四个边界断言（±1.0、±1.0001）全过；全臂重算判决未变（现有报告点没有恰好落在 −1.0 的）。

### 1.7 配对判据的占用率口径与预注册不同 + 缺完整性守卫（**已改**）

- 预注册举的旧配对（55.8/55.5）用的是**均值**（`occupancy.csv` 第 3 列），
  而 `gen_tierpair` 判前提用的是 `one()` 的 `occ_p50_pct`（**中位**）。
  已抽 `gen_a100.occ_stats()` 出中位与均值**两个**，两者都要 <10% 才判前提成立，
  判决串里两个都印（实测：中位差 0.50%、均值差 1.93%，都在阈内）。
- 只查 `summary.json` 存在**不等于跑完**（`stop_session_on_error` 让崩溃的 run 也写
  summary 且 `runner_rc=0`）。已加 999 步 / 0 失败的硬守卫，**并做了两个反向测试**：
  用还在跑的 `foyer_hz1_r3` 当替身 → 拒判；造一条「有 summary 但 807/50」的假 run → 拒判。

### 1.8 顺带抓到的一条（不在 codex 报告里）：**在跑的 run 漏进了 `runs_precise.csv`**

`foyer_hz1_r3` 以 **31/999 步**的残缺行进了 `runs_precise.csv`（做 1.2 的复算时才看到）。
根因：`frontier.py --csv` 的「不过滤步数」本意是收【跑完但不足 999 步】的 run，
却把【在跑的】也收了。已加判据「必须有 `summary.json`」并重生成：
64 → 58 行，剔掉的 6 条全是崩溃/中止/在跑的（`cap2_hc` 763、`cap4_fixed` 22、
`foyer_hz1_r3` 31、`foyer_rg2` 770、`foyer_rg3` 169、`v4_r2` 134）。
**`table1.csv` 重生成后逐字相同** —— 那 6 行本来就没被用。

---

## 二、独立复核子 agent 第 15 轮：摘要与引言逐个复算

**11 个数/口径全部与 `paper/data` 一致**，没有编造或抄错列。一条实质问题、两条口径提示：

### 2.1 摘要把「跨五条策略的关联」写成了无条件因果（**已改**）

`main.tex` 原来写「and what it tracks is the memory tier rather than the controller」，
而正文两处都带限定（§III「consistent rather than demonstrated」、§model「we did not
hold concurrency fixed and vary eviction」）。**摘要丢了限定 = 强于证据**，且 `it`
指代不清（字面像在说「弹性本身 tracks 内存层级」）。
已改成「what that elasticity tracks is … --- an association across five policies,
which we call consistent rather than demonstrated」。

### 2.2 摘要的 range 写错（**已改**）

「across the range our controllers occupy」—— 九条臂的 R̄ 区间是 **1.35–1.69**，
而 87.9% 那个点（`cap5_hc`）在 **1.746**，**区间外**。引言写的是明确区间
「over 1.25 to 1.75」（那是四个 host-tier 静态点自己的区间，1.253–1.746）。
摘要已改成同一个明确区间。

### 2.3 摘要缺打平带限定（**已改**）

「the closest misses by 0.30pp」按论文自己的 ±1.0pp 带是 **TIE**；引言写明了
「inside the ±1.0pp band we call a tie, but on the below side of it」，摘要没带。
已补「inside the band we call a tie」。

### 2.4 ε 的两个值**贴边**（**已披露**）

子 agent 复算：两位小数口径给 **0.3768 / 0.6079**，六位小数口径给
**0.3738 / 0.6047** —— 后者印出来是 **0.37 / 0.60**。也就是说「正文写 0.38」
依赖 **R̄ 取两位小数**这个约定，而那个约定原先只声明覆盖【分段】弹性。
我自己独立复算确认了四个数。已把约定扩到「fitted or segmented」，并**在正文里
明写六位小数口径读作 0.37 和 0.60**；检查器里那两个数改成**现算**（不硬编码），
另加两条守卫钉住 0.37/0.60 的披露句。

**摘要 291 → 309 词**（上限 320）；三条新限定各加了一条检查（反向测试：删掉限定 → MISS）。

---

## 三、状态

**27 页**、**0 Overfull**、0 undefined、**555 项检查 0 MISS**。

两条线合计：**已处置 12 条，明确不处置 0 条**。

### 本轮新加的守卫（都做过反向测试）

| 守卫 | 反向测试 |
|---|---|
| 唯一性：插值**正则**（不是字面量）+ 白名单 | 换变量名抄一份进 `gen_pool50` / `gen_arrival_slo` → 各报 MISS |
| 唯一性：`TIE/BAND = 1.0`（行尾注释也算） | 抄进 `gen_a100_delta` → MISS |
| 排版：0 Overfull / 页数下界 / 源文件 md5 与上次编译一致 | 假造 Overfull / 改页数 / 改 .tex 不重编译 → 各报 MISS；**只 touch 不改内容不报**（对 mtime 判据的改进） |
| §criterion 的 ε 现算 + 六位小数披露句 | `0.61`→`0.62` → MISS |
| 摘要三条限定 | 删掉「consistent rather than demonstrated」 → MISS |
| `gen_tierpair`：999 步守卫 / 占用两口径 | 在跑的替身、造 807/50 的假 run → 各拒判 |

### 未处置（写明理由）

**无。** 本轮两条线提的每一条都改了或补了披露。
