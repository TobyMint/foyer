# 第 35 轮处置（codex r35 + 我自己顺着「queued」一词的 grep）

范围：2026-09-26 08:30 之后那一批（图注条数 / A100 基线重跑失败 / 图 1-2-3 共用争用集合）。
独立复核子 agent 那一线**还在跑**，落地后另开一节。

**这一轮最重要的不是 codex 报的那 6 条，而是它报了 1 条之后我顺着同一个词
grep 全稿、又抓到 2 条 —— 而且这 2 条比它报的那条更严重。**

---

## 一、**「已经跑完的实验还写着『在排队』」**（codex 1 条 + 我自己 2 条）

CLAUDE.md 纪律 1 记的是「**不要把还没跑的实验写成已跑**」。**这次是它的镜像**：

| 位置 | 旧句 | 实情 |
|---|---|---|
| `sec_discussion.tex:381`（codex 报） | A100 无控制基线的「Its re-run is still queued」 | 重跑**已经跑了**，且**失败**（§A100 已整段重写） |
| `sec_discussion.tex:641`（我 grep 到） | 同卡层级配对「is queued rather than done」 | 那一对**已经跑完**，§III 报的就是它的判决（+10.1 点） |
| `sec_criterion.tex:115`（我 grep 到） | 同一件事「a same-card pairing *of those two* is queued」 | 同上 |

第 2、3 条比第 1 条严重：它们说的是**论文的标题主张**（梯队决定并发代价）所依赖
的那个配对。§III 早在 09-25 就写了「has since finished」，而 §VI 与 §V 两处
还停在排队 —— **同一件事在同一篇稿子里有两个互相矛盾的状态**，而检查器一个都没报。

**规矩：「还在排队 / 还没跑 / in flight」与「已经跑了」是同一枚硬币的两面，
要一起扫。** 已加守卫：每处含 `queued` 的句子都打印出来供人逐句确认，
并对**已经作废的具体说法**（`still queued` / `queued rather than done` /
`a re-run is queued` / `clean re-runs … in flight`）点名禁止。
反向测试：把 `still queued` 塞回 §VI → 报 MISS ✓。

## 二、codex 的其余 5 条

### 2.1 §A100「池子变小是因为定池时卡已被占」——**断言了没有证据的那一刻**

watcher 的第一条采样在**定池之后**，它证明的是运行期间有外人，**证不到定池那一刻**。
已改成陈述事实 + 已披露的机制，并**明写 watcher 的时间边界**：
「SGLang 从启动时的空闲显存定池子，所以池子短说明启动时卡不是空的；
watcher 的第一条采样在那之后，所以它界定的是**运行期间**的争用、不是定池那一刻。」

⚠ 这与同段「不断言池子小与争用哪个造成 148 分钟」是**同一条克制**，
codex 说我后半段守住了、前半段没有 —— 它说得对。

### 2.2 「last **23.7** minutes」把两个不同的量混了

- `dirty_span_min` = 首末两条脏采样之间 = **23.7215**
- `dirty_before_end_min` = 首条脏采样 → run 结束 = **23.8470**

正文说的是「最后 N 分钟共卡」，N 是后者 ⇒ **23.8**。已改，并把守卫换成后者。

### 2.3 §VI「the negative result itself is still measured on one card」范围不明

与 §A100「控制器在第二张卡上是打平、不是越过」并读会矛盾。已限定为
「**across the nine \sys{} variants**」。

### 2.4 图注守卫的两个构造（都真的漏过去了，都已堵上）

| 构造 | 原判据为什么会放过 |
|---|---|
| `\caption[short]{Three bars are hatched.}`（合法写法） | `rfind("\\caption{", 0, k)` 匹配不上带可选参数的 caption，**取到上一张图的 caption** |
| `\mbox{thirty-}two bars are hatched`（排出来是 thirty-two） | 正则只看到 `two bars` → 返回 **2**，错的条数通过 |

已改成：**限定在同一个 `figure` 环境内**（`\begin{figure`…`\end{figure`，
前缀同时盖住 `figure*`）+ `\caption\s*(\[...\])?\s*\{`；`_cap_n` 匹配前
**剥掉 `\mbox{}` 之类的排版命令与花括号**。两个构造各自反向测试 → 都报 MISS ✓。

### 2.5 `tau2_of()` 抽取与「ten times / seven static runs」——codex 复核确认**对**

## 三、我自己在修的过程中犯的两个

1. **`median occupancy of` 跨了换行** —— 我改措辞时把短语断在两行，`ck_near`
   立刻报 MISS（**假 MISS**，正文是对的）。这就是 CLAUDE.md 那条
   「关键词一律挑【同一行内】的字串」。已把换行挪开。
2. **新写的「最后 23.8 分钟」把守卫也带翻了** —— 守卫原来读 `dirty_span_min`。
   两条一起改才一致（**改了正文就要看守卫盯的是不是同一个量**）。

## 三·补、顺着「会随时间变假」这条线又扫了一次

`queued` 那一族让我把**同类词**一起扫了一遍（`in flight` / `pending` /
`not yet run` / `still running` / `today` / `at the time of writing`）：

- 七处 `in flight` 里六处是技术义（「请求在途」），一处（§V，AIMD 那行说
  「a clean re-run of the arm is in flight」）**当前确实还在跑**（140/999），
  属于待办清单上的那句，落地时一起改。
- **抓到一处新的**：`sec_results.tex` 写着「one of them reads 1.95 **today**」——
  那个 run 早就跑完了，而 **1.95 在现在的 `projection.csv` 里根本不存在**
  （main_trace 的 max 是 1.96）。不是数错，是**这句话的有效期过了**。
  已改成不带时点的说法（「他们的中位还没定稿」）。

**已加守卫**：正文里出现 `today` / `at the time of writing` / `as of this
writing` / `for now` / `at present` / `currently reads` 一律报 MISS。
反向测试：塞回 `today` → 报 MISS ✓。

**现在 28 页、0 Float/Overfull、608 项检查 0 MISS。**

## 三·补二、**独立复核子 agent 第 19 轮**（与 codex 同一批，两条线独立）

报 **2 条 major + 9 条 minor**，逐条复核后：

### Major（两条都是真的，都已改）

**M1｜§VI 的 flag 计数按 trace 拆错了。** 原句「Fourteen of our **main-trace**
runs are; three more are on the moving-load trace」，而 `concurrency.csv` 逐条数：
**主 trace 12 + 变负载 2 = 14**。同一段的下一句自己写的又是
「Fourteen of our runs … two are Table I rows and twelve are arms we do not report」
——**两句互相矛盾**，检查器一处没报（它从来没按 trace 拆过这个集合）。
已改成「twelve on the main trace and two on the moving-load」并加守卫
（按 `metadata.json` 的 trace 字段现算 + 反向测试三条都报 MISS）。
「三条死在窗口里」也改成正确的 **四条**（`_failed_4lane_*` 目录实测 4 个）。

**M2｜§VI「the one affected arm still carrying the flag in Table I」读 33.3 ms —— 已不成立。**
表 I 现在带 ‡ 的只有 `cap1`（20.6 ms）与 AIMD 行（24.4 ms）；33.3075 是**旧的**
`foyer_breshz1`，而它的行已被干净的 `breshz1_r2`（25.5 ms）替换。
已改成「reached 33.3 ms on the worst-affected arm in its flagged reading —
`horizon`=1 no hw, since re-measured at 25.5 ms」并加守卫。

### Minor（逐条处置）

| # | 问题 | 处置 |
|---|---|---|
| m1 | 图 2 图注的 6.3 / 36.3 / 11.4 无守卫（改了不报） | 已加 5 条守卫（含两个名次），反向测试报 MISS ✓ |
| m2 | §III **正文**里的「thirty-four runs」无守卫（只有图注那处有） | 已加；反向测试两处同时报 ✓ |
| m3 | §A100 的 90.1 / 88.3(against) / 8.8 / 999 of 999 无守卫 | 已加 6 条 ✓ |
| m4 | 本文件自称「9 条 §A100 守卫」，实测 **10 条** | 本文件已改 |
| m5 | `make_figs.py` docstring 仍写「空转 7.4%–36.3%」 | 已改成 6.3%–41.9% |
| m6 | `gen_a100_baseline.py` 把墙钟/SLO 各写了一遍 | 已抽成 `gen_a100.wall_slo_of`，`one()` 与 baseline 都 import；`a100.csv` 重生成**逐位未变** ✓ |
| m7 | §A100「tracking it at every completion quantile」**太强** | **实测**：baseline 在 501/999 个分位更快，p90/95/99 慢 33.8/25.1/45.4 s，最大落后 83.5 s。已改成「前七个十分位内相差 4 s 以内、只在尾部拉开」并加守卫 |
| m8 | §IV「Four of the nine **carry** the flag … have since been re-measured」时态 | 改成 `carried` |
| m9 | 「A third attempt is queued」只能靠 `NEXT.md` 作证 | 无本地脚本可核（那条 lane 只存在于实验机）—— **如实保留**，它确实是当前状态 |

### 子 agent 独立复算并确认【对】的

图注三个「2」与 `.counts.json` 的 32/2、34/2、34/2；`a100_baseline.csv` 13 列
全部逐位；§A100 每个数的出处（含 222.6867/21.3546 = 10.4 → 「ten times」）；
「哪个造成 148 分钟」守住了；第一次尝试「尾部 τ₂ 抬高」有 within-run 证据
（含外人起点前 16.73 ms → 之后 38.66 ms）；§III 的 8.4–39.7 / 3.3–8.8 / 20.6–39.2
三个区间；§VI 的「31% 到 50%」与「十二个干净 run 23.7–27.5」。

## 三·补三、**绝对词专项扫描**（本批第三次扫词，2026-09-26 09:5x）

前两轮扫过**因果词**（r33）与**排队词**（本轮），这次扫**绝对词**：
`the only` / `never` / `always` / `the first` / `the largest` / `none of` / `all of`。
报 2 条：

1. **§V 同一件事写了两个数**：第 609 行「in **4** of the 11 \sys{} runs a scan finds
   windows」、第 630 行「the signature is present in **three** of our eleven」
   —— 同一个判据、同一个集合。`stall.csv` 实测 **4 条**（单窗口 3 条 + 全关那条 9 个窗口）。
   已改 + 加 4 条守卫。**检查器查不出这个**：它只问「值在不在」，
   **不问「同一个量出现了几次、是不是同一个数」**。
2. **§II「cap1 is the only anchor there that runs without HiCache」—— 复核后确认【对】。**
   ⚠ 但我第一遍**读反了**：`TURNSTILE_HICACHE_ARGS` 关掉时的字面值是
   字符串 **`"unset"`**，`bool("unset")` 是 `True`。**差点去改一句本来是对的正文。**
   已加守卫（从 `frontier.FRONT` 现算右段里没有 HiCache 的锚点，与正文点名的臂逐字比；
   判据写成**从短语里取名字**，不是「cap1 在不在这附近」——那句话里
   `\texttt{cap1}` 出现两次，反向测试实测只查值不会报）。

顺带复核并确认**对**的：§II「minus flagged 就是 minus cap1」（19 条池子里只有 cap1 被 flag）、
§V「the configuration that produced our best result never showed one」（`foyer_hz2_r2` 窗口数 0）、
§VI「twenty-four host-tier runs … never below 59.7%」（`reuse.csv` 的 hicache 族恰好 24 条，
区间 59.7--92.5，低端是 `cap8_hc`）。

## 三·补四、**守卫自己的一个假 MISS**：`has()` 的「数字↔英文词」是单向的

上面第 1 条的守卫第一版写成 `ck_near(..., num_words(4), ..., "a scan finds windows")`
→ **假 MISS**，而正文是对的（它写的是阿拉伯数字 `4`）。
`has()` 只做了**传数字时也试英文词**这个方向；**传英文词不会去找阿拉伯数字**。
已改成 `num_words(k) + [k]`。

**现在 28 页、0 Float/Overfull、631 项检查 0 MISS（rc=0）。**

## 三·补五、一条「**说出来像测过、其实是构造性成立**」的说法

§V 原句：「the signature is present in four of our eleven \sys{} runs and
**absent from all of our static caps**, which have no admission decision to get
stuck in」。

实测：静态 cap **根本没有 `controller.jsonl`**（只有 `admissions.jsonl`，里面没有
`valve` / `n_admitted` / `waiting_n` 任何一个字段）—— 判据**在它们身上无法求值**。
所以「absent」不是测出来的，是**构造上不可能**。

已改成「**cannot arise in** our static caps, which have no admission decision to get
stuck in **and write no control-cycle log to scan**」。
（这类「像测量、实为推理」的说法与「一个说得通的因果不等于有出处的因果」同族，
只是这次推理是对的、措辞把推理说成了测量。）

## 四、状态

**28 页**、**0 Float too large**、0 Overfull、**607 项检查 0 MISS**。

> **这一轮的教训**：codex 报 1 条，顺着同一个词 grep 出 3 条 ——
> **报告里的一条只是采样，不是全集**。上一轮「切换器」那条也是这么发现的。
> 而「已经跑了却写着在排队」这个方向，34 轮里从来没人扫过：
> 所有审查都在防「把没跑的说成跑了」。
