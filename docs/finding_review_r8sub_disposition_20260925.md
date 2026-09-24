# 中立子 agent 第 8 轮（全稿）处置记录（2026-09-25）

它只做三件事：找**强于证据**的句子、找**自相矛盾**、判断「负结果可不可信」。
九条「强于证据」+ 八处矛盾，**全部成立**，全部处置。它与 codex 第 19 轮几乎不重叠
（codex 查数值与逻辑，它查主张强度），说明两条线都要跑。

## 一、它自己挑的「最该改的一条」：摘要说的「前沿」是哪一个

**问题**：摘要写 "none is above the static Pareto front"。**「static Pareto front」
会被读成「实测静态点的非支配集」**，而在那个读法下，最好的那条臂（`sf0_r2`，
263.3 min / 86.3%）**是非支配的** —— 比它快的静态点 SLO 都比它低，SLO 比它高的都比它慢——
而且对最近的离散锚点还高 **+4.4 pp**。审稿人一查表就会认为摘要在放大。

**改法**：摘要点名用的是哪条前沿，并**同时给出两种读法的数**：
「misses the \emph{interpolated envelope} ... by 0.55 pp, and against the discrete
static points it is \emph{not dominated} by any we measured (4.4 pp above the
nearest). We use the envelope because it is the stricter reading」。§II 早就写全了
这两个数，只是没搬进摘要。

## 二、摘要里三处与正文打架

| 摘要原句 | 正文怎么说 | 改法 |
|---|---|---|
| "so the engine **had room they did not take**" | §V 明确拒绝这一步：「it cannot say *why* the arm fails to beat the front」「a description of what they did, **not a demonstration that doing otherwise would have won**」 | 改成「the ceiling we measure on device-only caps **is not what stopped them** ... That rules an explanation out; **it does not show they could have taken the room**」 |
| "their own headroom estimate is **1.79× the truth**" | §V 说这个差里 28% 是**设计上就要留的** growth reserve，而 parked session 的前缀「reserves capacity that really will be needed back」 | 改成「1.79× **the occupancy the engine reports** ... of which the growth reserve alone is 28% of the budget」 |
| "what **sets** it is the memory tier" | §IV 把同一件事写成「a cross-policy association, not a transportable causal derivative」 | 改成「in our data what it **tracks** is the memory tier」 |

## 三、其余六条「强于证据」

1. §I「whether recomputation happens is **decided** by the memory tier rather than
   by the policy」→ 改成「in our data ... **tracks** ... an association across five
   policies, which §III calls consistent rather than demonstrated」。
2. §V「The result is **unambiguous**」→「consistent across every arm we can compare」。
3. §V「The direction of the correction is **known** and it runs our way」→
   改成「**The one re-measurement we have** moved our way ... but that is one data
   point, and co-tenancy could in principle also reorder completions, which need
   not push the same way」。（这是我自己上一轮加的，subagent 是对的。）
4. §III「the τ₁ spread **does not sit unexplained at all** ... **which is the
   mechanism**」→「does not look like a residual ... a cross-policy association
   like every other fit in this section, not an intervention」。
5. 贡献列表与结论的「+51% / −42%」缺跨代限定（限定只活在 §VI）→ 两处都补上
   「a comparison that spans two harness generations (§VII)」。
6. §I「+0.9 pp ... **inside the noise**」与 §VI「about a replicate wide ... we quote
   the tightest pair because it is the **least favourable to us**」方向相反 →
   统一为「about a replicate wide at the tightest spread and inside it at the
   widest---so we report it as **not worse**, not as a win」。

## 四、八处矛盾

**A. §VI 把第二条 trace 的局限写反了方向（最严重的一处）。** 原文说它「failed here
on the configuration where §III says added concurrency is **expensive**」——
而那条 trace 在控制器工作点的 ε 是 **−0.28**（负），正是「加并发还是便宜的」。
真正让它检验不了层级机制的是**它没有 host tier**。已改。

**B. 表 I 脚注的 ‡ 算术自己算不平**（**我上一轮改出来的**）：写「四行带旗、三行受损…
第四行…**剩下两行**」，按枚举是六行。数据侧现在带旗的是 **五行**（`cap1`、`hz2`、
`hz0`、`breshz1`、AIMD），加上已重测干净的 `bres` 是**六行曾带旗**。已改成
「Six rows of this table carried the flag; five still do」。

**C. 「九条控制器变体」的成员定不下来。** §II 把 `foyfix_hc` 算进九条，§V 的归因表
又把 `sf0` 当成「第九条」、把 `foyfix` 排除。已统一：**九条 = 走 `budget3` 那条
policy 的九个配置**；`foyfix_hc` 跑的是另一个控制器（`foyer:target=0.95;hw=0;sf=0;sg=0`），
所以 §II 那句改成「Table I 控制器段里三行比 295 分钟慢——**九条变体里的两条，
加上跑另一个控制器的 all-throttles-off 臂**」。

**D. host-tier 集合的算术。** 原文写「判据本身选出**二十**，再点名四条不是要抓的」，
但 20 − 4 ≠ 19，而且那「四条」里有两条是被 ≥995 步**条件本身**排除的，不是被点名排除的。
已改成不报中间数、只写**判据 + 两条具名排除**（那条 1.41× 的异常 run，和那条被重测替代的旧测量），
并单说步数条件自己排除了哪两条（763/770 步）。这样计数对读者是可复算的，
而且不受「重跑陆续落地」影响。检查器加了「集合条数 = 19 且不含 hz1_r2」。

**E. tool_wait 的保真度证据挂在错的那条 run 上。** §II 说「harness 忠实：实测 16.85 s
对要求 15.82 s」——16.85 是**控制器那条** run 的（含等 permit），而 `toolwait.csv`
显示无控制器的 `cap1` 是 **15.82 对 15.82，比值 1.0001**。用控制器那条证明 harness 忠实，
等于把控制器的开销算进 harness 的账。已改成用 `cap1` 证保真、再把 16.85 作为控制器的
增量引出。顺带修了中位：**要求的中位是 0.34 s**（正文两处写成 0.35，那是 `foyer_hc` 的实测中位）。

**F. 同一个 +0.9 pp 在两处取用方向相反** —— 见三.6。

**G. §VI 那段「5 s 越线」的收回写成了循环论证**（「后面那句把它收回了」）→
改成先说「does not survive its repeat」，再给 +0.86 的数。

**H. 同一条臂三个名字**（`bres` / `resident base` / "the charge-free base"）→
在 Route 1 开头绑定：「The arm that tests this is `bres` in the data files and
*resident base* in Table I; we use both names below」。

（另一处措辞：「moves our best arm from *on* the line to *on the line, below it*」
字面自相矛盾——「on the line」按定义是带内。改成「from *inside the tie band* to
*just below the line*」。）

## 五、它的「设计注定测不出」反驳

它给的最有力一条正是第一节那条（判据是未实测的插值线）。论文能回应一部分
（§II 同时报两种读法的数、§VII 用了非支配读法、§II 承认时间片本身不免费），
**回应不了的是**：那条线从没被实测过、「更严所以更容易得负」是论文自己写的、
而判带宽度对某些配置「far too narrow」。第二节的改法把这条反驳的可攻击面缩小了：
现在摘要把两种读法的数都摆出来了。

## 六、自检

`check_paper_numbers.py`：**361 项、0 MISS**；编译 **24 页、0 Overfull、无 undefined**。
摘要 1071 词（这几轮为回应两轮审查加了约 180），NEXT.md 里仍记着「定稿前瘦身、
一条限定都不许丢」。
