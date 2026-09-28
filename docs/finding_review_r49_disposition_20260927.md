# r49 双审查处置记录（2026-09-27）

同一份 brief（`docs/review_brief_r49.md`，19 条）**同时**发给：
- **中立子 agent**（Claude，general-purpose，163 次工具调用；沙箱 `/tmp/rev49/sb`）
- **codex**（`codex exec`，约 249K 字符输出）

处置前基线：**830 项 / 0 MISS / 19 页**。处置后：**834 项 / 0 MISS / 19 页 /
0 Overfull / 0 未定义引用 / 摘要 265 词**。

⚠ 第五节的两条「核不动」**当天都已补做并关闭**（拟合量的生成器、四张机器端表的逐字节复验）——
它们原本是「所有数字可追溯到脚本或日志」这条停止条件上的缺口。

---

## 一、**codex 单独抓到的一条真错**（中立审查没抓到）

### §III 把「干净复跑」说成了「受污的 run」

原文：「**Four of the twenty-eight** host-tier runs---the resident base,
\texttt{horizon}$=0$, \texttt{horizon}$=2$ and the \texttt{horizon}$=1$ no-hw
arm---were measured while three other engine instances shared the host … all four
have since been re-measured alone, and the values above are the clean ones.」

**但那四个 label 指的正是干净复跑**：

| 表 I 的 label | 实际 run | concurrency 判决 |
|---|---|---|
| resident base | `foyer_bres_r2` | **clean** |
| horizon$=$0 | `foyer_hz0_r2` | **clean** |
| horizon$=$2 | `foyer_hz2_r2` | **clean** |
| horizon$=$1, no hw | `foyer_breshz1_r2` | **clean** |

受污的是**被替代的那四条**（`foyer_bres` / `foyer_hz0` / `foyer_hz2` /
`foyer_breshz1`，全 `CONTESTED`），它们**已被替代、根本不在 28 条里**。
所以原句不但把因果说反，还**自相矛盾**（它自己接着说「the values above are the
clean ones」）。

**处置**：改成「Four of the **arms above** … were ***first*** measured while …
shared the host … the values above are the clean ones.」，并补一句
「(The flagged runs themselves are superseded and not in the table; the four labels
above name the arms, whose rows here are the clean re-measurements.)」

⚠ **为什么中立审查没抓到**：它核了「28 条集合」与「两个区间」，但没核**这一句的指代**。
两个审查者的盲区不同 —— 这正是同时开两家的价值。

---

## 二、**中立审查单独抓到、codex 没抓到的**

### §V「**One** point in Fig. 1 is above the line」→ 两个

`scan_r2` 落地后图上有**两个**点越线。而且**守卫反过来锁死了旧说法**：

```python
if "One point in Fig." not in _rs2:      # ← 写死的措辞
    fails.append(("§V 没有讲那个越线的点…"))
```

⇒ 改成「Two points」会**被这条守卫拦住**。守卫写死正文措辞 = 它挡住了**正确的修改**
（与本项目记过的「锚失配 = 沉默」是同一枚硬币的反面）。

**处置**：正文改「Two points … and they are one arm: two rows of Table I,
\texttt{scans the queue} and its repeat, neither of them one of the nine」；
控制周期那句改成两次运行各自的数（**8,030/210** 与 **7,932/203**）；
守卫改成**从 `table1.csv` 现数**越线点数再匹配对应的词。

### `landing_triage.py` 的**错基准**（中立审查 A7 / codex 第 7 条）

第四节用 `table1.csv` 的 `delta_pp` 算各组 Δ 全距 —— 而
`pairA_foyerhc`/`pairB_foyerhc` **不在** `table1.csv` 里 ⇒ base 组只剩两条
⇒ 全距 **0.49**，比 hz2 的 0.51 还小 ⇒ **按升序打印会让人得出「最紧的是 base」**
（与正文相反）。**同一个坑，检查器里我修过、分诊脚本里漏了。**
**处置**：改用 `runs_precise.csv` + `frontier.front_slo()`（与检查器同源）。
实测现在给出 hz2 0.51 / sf0 0.68 / scan 0.86 / base 1.91 / hz1 4.65 ✓。

### 第四节（B16）：**5 处本轮该改没改的派生量，全部无守卫**

| # | 位置 | 原写 | 真值 |
|---|---|---|---|
| (i) | §V | 「**One** point … above the line」 | **Two**（见上） |
| (ii) | §VII | 「Only **seven** configurations have been repeated」 | **nine**（`replicates.csv` 9 组） |
| (iii) | §V | 「**thirty-one** runs where `occupancy.csv` and Table I overlap」 | **thirty-three** |
| (iv) | §V | 「against **31.8%** and 5.9%」 | **32.2%**（见下） |
| (v) | 图 2 图注 | 「computed over all **thirty-six** runs」 | **thirty-seven**（`decomp.csv` 37 行） |

(iv) 的细节值得记：`gate_attrib.csv` 自己的注释行写的是
`valve_pct=5.9, projection_over_pct=32.2`（**上中位**口径）；50 行时「中间两个取平均」
是 31.75。**我上一轮写的 31.8 是「中位」口径、5.9 是「上中位」口径 —— 同一句话混了两套约定。**
（49 行时两者恰好相等，所以这个分歧是 50 行才出现的。）

### 「the closest is horizon=2」的口径（中立审查）

按「任一读数的最小 |Δ|」算，**`sf0_r3` 的 +0.1310 比 `hz2_r3` 的 +0.2167 更近**；
只有按「九条变体的代表 run」才成立，而正文没写这个口径。三处都没有守卫。
**处置**：改成「**the best**」—— 按 Δ 最大算 `hz2_r3`(+0.2167) 确实是九条里最好的
（`sf0_r3` +0.13 更小），并在 §V 加一句「(Best, not closest: `single-flight off`'s
repeat reads +0.13, nearer the line, but its reported run is −0.55.)」。

### §VI 的 launcher 披露漏了一对（中立审查 B16 尾）

§VI 说「the base's repeat and the scan arm record different hashes of it, as do the
two \texttt{horizon}=2 runs」—— 但 **`sf0` 那一对也跨**：
`foyer_sf0_r2` = `a8605b1e77d5` vs `foyer_sf0_r3` = `cfd46f9b1ea2`。
（`scan` 与 `scan_r2` 则**同** launcher，已一并写明。）
**处置**：补上 sf0 那对，并注明 scan 的重复是同一个哈希。

---

## 三、**两边都提到、我采纳的**

### 「reproducibly」说满了（中立 B13 / codex 第 13 条）

两个审查都指出：`+1.30` 与 `+2.16` 两次都越过是**事实**，但
**「beats the static envelope reproducibly」是在陈述该臂的性质，比两次读数能支撑的强一档**；
而且首跑仅高出带边界 0.30pp，**小于本对自己两次之差 0.8556**。

**处置**：不退回「unresolved」（那才是本项目栽过的「把正说得更负」），
而是**把词收一格**：摘要与 §VI 的 `reproducibly` → **「on both of its runs」**。
判据仍是跑前预注册的 (a) 分支，差别（0.8556 < 1.0）也仍在 §V 里印着。

### 「the only arm here above the line at 5, 10 and 20s」（中立 A5 / codex 第 5 条）

逐臂核过：5s 下只有 **`scan_r2`（+1.2094）** 越线，**`scan` 首跑是 −0.8760（带内）**。
所以「该臂在三个阈值上都越线」**按字面读是假的** —— 是它的**第二次读数**在三个阈值上都越线。

**处置**：「One of its two runs is above the line at all three thresholds---no other
reading here is---and it is the only arm whose repeat confirms it.」

### §VI 说漏了两处、方向都是「把正说得更负」（中立 B14）

1. §VI 只写了 `scan` 的 ready 读数掉到 −0.07，**没写它的重复在 ready 时钟下仍是 +1.51（仍在线上）**；
   §V 写了「mixed」，§VI 没写 ⇒ 单读 §VI 会以为该臂在 ready 下已出带。
2. §VI「the three that cross the ±1.0pp band **all sit at the margin**」—— `scan` 的引擎侧读数是 **+1.30**，**不在边缘**（只有它的 ready 侧在边缘）。

**处置**：(1) 补上「---though its repeat stays above the line at $+1.51$」；
(2) 改成「all **move the same way, toward the negative**」（去掉「sit at the margin」）。

### C17：**第四条「看起来在守」的盲区**（中立审查）

中立审查找到的**第四个**盲区（brief 里问了「有没有第四处」）：

「±1.0pp 打平带只有 `frontier.py` 一处定义」这条不变量的守卫，正则是
`^\s*([A-Za-z_]\w*)\s*=\s*1\.0\s*$` —— **只认赋值式**。而 `gen_table.py`
与 `compare_rerun.py` 当时各自**内联**了 `> 1.0` / `>= -1`：
**正则永远看不到，于是那条不变量是假的而守卫报 0 MISS。**

**处置**：
1. `frontier.py` 加 **`classify_short()`**（**从 `classify` 派生**，
   `_SHORT[classify(delta).split()[0]]` —— 分支只有一处，改边界自动跟着走）；
2. `gen_table.py` 与 `compare_rerun.py` 改调它（实测 `table1.csv` **逐字节不变**，改法等价）；
3. 加**正向点名**守卫（`_MUST_CLS`，与既有的 `_MUST_IMPORT` 同风格）。

⚠ **我自己的新守卫第一版又是假通过**：写的是 `"classify_short" not in src`，
而文件里的**注释**就含这个串 ⇒ 反向测试（把内联改回去）**仍报 0 MISS**。
改成匹配**调用式**（`\bclassify_short\s*\(`）后反向测试开火 ✓。
**「反向测试」这条纪律又一次当场抓到了守卫本身的错。**

### C19：铺满性断言的**局限**（codex）

codex 的反向测试：在内存里把 ready 集合的 `foyer_scan_r2` 换成被排除的
`foyer_hc_r2`，**28 / 7 / 1+4+2 全不变，断言照过** ⇒ 它**只守数量、不守成员**。

**处置：不修**，把局限写进注释。理由：修它要引入一份「期望成员」名单，
而那份名单**就是被检查的对象本身**（自证循环）。成员身份由上游保证
（`gen_arrival_slo.py` 的 `RUNS` + `arrival_slo.csv` 的行集合）。

### C18：文档陈旧（中立审查）

`docs/landing_checklist_20260927.md` 里写 `NOT_STATIC`，代码里是 `NOT_SINGLE_CONFIG`。已改准。

---

## 四、**两边都确认无误的**

A1（两条 run 干净：池 101432、999 步 failed=0、`prompt_len` 合计 = 28,526,871、
gpu_watch 窗内 0 外人、本地与实验机 md5 逐字节相同）、A2（Δ 与判词）、
A3（头条三处的数值与余量 0.30/1.16、ready −0.07/+1.51、26.9 分/9.2%）、
A4（§VI 表 33 个格子逐格相符、20s 下恰 5 条越线）、A6（28 条集合与两个区间）、
A8（28 of 35，7 = 1+4+2）、A10（9 组与枚举 0.3…5.1）、A11（图 1：37 点、
「two runs」、无反斜杠、未压点未出轴）、A12（`Conc.` 位数只影响 no-control 一行）、
B15（sf0 两次都没越线，仍是「扫队列不必然赢」的有效反例）。

`NORE=1` 下 **86 条 MISS**（退役清单对拍）；本轮新加的退役仍**诚实**
（`NORE=1` 下两条 `§I 控制器重复 Δ 全距` 都报 ⇒ 数字确实已不在正文里）。

---

## 五、两边「核不动」的条目（照抄，不假装核过）

- ~~**拟合量 `r=0.85 / 残差 1.92ms` 的定义不在任何脚本里**。~~
  ✅ **2026-09-27 08:1x 已关闭**：新增 `scripts/lab/gen_fit.py` → `paper/data/fit.csv`，
  把复核者用的那套口径**固定成代码**（x = `eviction.csv` 的 `uncached_tok` 全精度列、
  y = `decomp.csv` 的 `step_back_ms`、OLS、集合 = hicache ∩ 有 τ₁ 的 **26** 条）。
  实测 **n=26、r=0.852422、max|res|=1.919695**，与复核值逐位相符、与正文印的
  0.85 / 1.92 相符 ✓。并补了**三条守卫**（r / 最大残差 / 点数），
  反向测试开火（把正文的 `+0.85` 改成 `+0.91` → MISS ✓）。
  `swap_superseded.py` 的 `REGEN` 已登记。**这个数现在追得到脚本了。**
- ~~**实验机上那四张必须上机跑的表**：「机器值 = 仓库值」未独立验证。~~
  ✅ **2026-09-27 08:1x 已补做并关闭**：先逐字节确认机器端四个脚本与仓库副本相同，
  再在实验机上重跑，把产物与 `paper/data/` 里那四份**逐字节 diff** ——
  `gen_concurrency` / `gen_gate_attrib` / `gen_projection` / `gen_repeat_spread`
  **全部相同** ✓。顺带：这消除了「机器 48 / 本地 49」那段历史分歧
  （`gen_gate_attrib.py` 的 docstring 已更新）。
- **`fig2` 图注的「thirty-six」是不是有别的意图**：两种解释下端点都对
  （6.3/41.9 由 `cap6_hc` 与 `foyfix_hc` 决定）—— 已按 `decomp.csv` 的 37 行改成
  thirty-seven，但**作者是否另有口径，无法从数据判断**。
- **ready 时钟前沿的两条替代锚点**（`gen_arrival_slo.py` 用 `cap4_hc`/`cap3_hc`
  代替 `_r2`）是文件自陈的近似：核的是「−0.07/+1.51 能由生成器逐字节复现」，
  **没有**构造另一组替代锚点核它在别的口径下会怎么动。
