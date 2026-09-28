# 第 27 轮审查处置（codex r27 + 中立子 agent 第 12 轮 + 自查）

两条线同时开，按 goal 的要求两边都处置。**每条都自己核过再改**，不采信报告结论。

- codex r27：`docs/codex_review_prompt_r27.md`，日志 `/tmp/codex_r27.log`，
  范围 = 摘要压缩是否丢东西 / 全篇主张 vs 证据 / §IV 的 τ₂ 论证 / 页数判断抽验。
- 子 agent 第 12 轮：摘要压缩的**独立**核对（30 条限定逐条回正文按语义搜）。

**两条线独立命中同一处**：摘要丢了「10 秒阈值」这个限定（codex A1 = 子 agent F1）。
两个互不通信的审查者撞在同一点上，说明这不是措辞偏好，是真缺口。

---

## 一、处置汇总

| # | 来源 | 问题 | 处置 |
|---|---|---|---|
| A1/F1 | codex + 子 agent | 摘要写「none is above」，无条件；§VI 还指着摘要说「条件版写在摘要里」，而摘要里没有 | **改**：阈值限定还回摘要 |
| A2 | codex | 摘要把第二条 trace 也算作 tier 机制的证据，而 §xtrace 明说它**没有 host tier** | **改**：拆成两句，说明它检验的是负结果不是机制 |
| B1 | codex | §III「gives the criterion a mechanism **rather than a correlation**」强于配对证据 | **改**：`a candidate mechanism — a correlation we can name, on a pair that is confounded in the two ways above` |
| B2 | codex | §IV「resolution, not the **existence of the effect**」——该段的 R̄ 只有 1.73→1.75，且 repeat 反转 | **改**：`existence of a cost difference`（论文本来就披露了反转，只是这句概括过头） |
| B3 | codex | §III 图注说 τ₁−τ₂ 的差「not measurement error」，正文却说**不能排除**两个估计器因别的原因不一致 | **改**：图注改为「bounds that share … cannot rule out that part of the gap is the two estimators disagreeing」 |
| B3b | codex | 相关工作把那个差写成**测到的**非 decode 工作 | **改**：`bounds, without identifying` |
| B4 | codex | 引言贡献说 host-tier 重算「stays flat」，而 §III 更新后报 8.6–15.7 M、r=+0.85 | **改**：按 §III 重写 |
| B5 | codex | §V「the resident base from **7.81** to **1.33**，horizon=0 from **13.60** to **7.19**」——**两处各漏两个负号** | **改** + 加检查器（见下） |
| B6 | codex | §a100 说「four static caps」，`a100.csv` 是 cap1–cap5 **五**条（同段上一句还写着 "one of the five runs"） | **改** |
| B7 | codex | §Discussion 局限段说「one 24 GB accelerator … the hardware axis we did not」；后面又说「reproducing on a larger device as the single most important next experiment」 | **改**（两处：硬件轴已测静态扫描；容量控制的前半已由 §a100 回答） |
| B8 | codex | ready-clock 段「nineteen of the twenty-five」，且缺席名单是 6 条 | **改**：20 of 28，缺席 8 条 + 加检查器 |
| B9 | codex | 「the fastest anchor **cap4+HC**」——最快的锚点已是 `cap6+HC`（207.8 min），§V 自己也这么写 | **改** |
| F2 | 子 agent | ε 判据的数值兑现「加 10% 并发买到 4–6% 吞吐」压缩后**全仓库无落点** | **改**：补进 §criterion（3.8% 到 6.1%，= 1.1^(1-ε)）+ 检查器 |
| F3 | 子 agent | NEXT.md 对照表里摘要移出的归因统计写着旧值 6/12、3、3 | **改**：标为过时值并注明"别补回摘要" |
| — | 子 agent | `if _ab:` 找不到 abstract 就**静默跳过**整块（词数 + 8 个锚） | **改**：加 else 分支显式 MISS |
| — | 自查 | `gen_repeat_spread.py` 分组键漏了**池子**，把全池与半池算成「重复对」（71.47%） | **改** + 重生成 + 反向测试（见第三节） |
| — | 自查 | `hc` 轴对 **78/155** 条 run 是瞎的（metadata 无该字段） | **只披露**，不改分组（见第三节） |
| — | 自查 | `num_words` 生成 `twenty-eightth` / `forty-fiveth` 这类不可能命中的候选 | **改** |
| — | 自查 | `cap4_hp` 是引擎 OOM 崩溃，不是「没跑完」 | **记档**，不重跑（见 `finding_pool50_cap4_oom_20260925.md`） |

## 一b、处置后按「改一处 ≠ 改完」做的全文清点

改完每个说法之后，拿它的**同义说法**回全稿 grep 了一遍（本项目栽过：降级一个说法，
正文里还有两处写着旧的）。结果：

| 说法 | 全稿其他出现处 | 结论 |
|---|---|---|
| 「the way the tier predicts」（第二条 trace） | **无** | 只有摘要那一处，已改 |
| 「comes from elsewhere / stays flat」 | **无** | 只有引言那一处，已改 |
| 「measurement error」 | **无** | 只有图注那一处，已改 |
| 「rather than a correlation」 | `sec_criterion.tex:117` 的 `not a transportable causal derivative` | **不改** —— 那句说的是「这个斜率**不是**什么」，方向相反，本来就对 |
| 「four static caps」 | 其余 `static caps` 出现处分别指第二条 trace 的六条、3090 的五条、25 档的三条 | **不改**，都是不同的集合 |
| 「the tier is what separates」（§III:341） | `sec_model.tex:339-343` | **不改** —— 它带着 `in these two runs` 的限定，紧接着就是那段 caveat |
| 「set by the memory tier」（§Discussion 结论） | `sec_discussion.tex:594` | **已改**：caveat 本来就在五句之后，现在**内联**进论点句（`in the sense of an association we see across every configuration we ran rather than of an intervention`） |

**两条判定为「不改」并写明理由**：

1. **摘要的 `what it tracks is the memory tier rather than the controller` 不加 hedge**
   —— 子 agent 说它比 §I 的「in our measurements」宽。但该句的**主句**是
   `On a memory-bound agentic replay we measure ...`，作用域已经由它限定了；
   再塞一个 `in our data` 是给一个句法上已经受限的从句加冗余限定，而摘要已经
   291 词（见下面未处置第 1 条）。
2. **§III:339-343 的 `the tier is what separates ...`** —— 同上，它自带
   `in these two runs`，且下一句就是 `The caveat is that this pair is two runs on
   two different days and two different GPUs, not a paired experiment`。
   删或弱化反而会让读者以为这一节没意识到混淆。

## 二、未处置（写明理由）

1. **摘要词数 273→291，仍可能超出 venue 的 250 上限。** 检查器的上限是 320。
   **理由**：投稿目标未定，不按猜的数字压。而这次补回的是**一条限定**——为了
   一个假想的 250 把限定切掉，正是「不许为了让结果好看而调整口径」的镜像。
   与页数 26 的处置同一个理由（见 `NEXT.md` 〇-2）。
2. **codex D 段的三处「可合并」**（§V 复测讨论里锚点移动讲了两遍、§IV 限定段
   重复陈述、§Discussion 代码版本段的细节）—— **理由**：都是压缩动作，
   与页数绑定，等 venue 定了和页数一起做。codex 自己也确认那三处的**核心论证
   不可删**，可删的是重复叙述。

## 三、自查发现的两条（不在两份报告里）

### 3.1 `gen_repeat_spread.py` 的分组键漏了池子 —— 论文引的上限被顶到 71.47%

**病**：分组键是 `(policy, trace, HiCache)`。全池 `pois200_cap4` 与半池
`pois200_cap4_hp` 同 policy、同 trace、同无 HiCache → 归成一组，算出
**71.47%** 的「run-to-run 散布」。表头自己写着「论文 §VI 引的上限就是本表的 max」，
而论文引的是 **22.0%**。

**同一个病犯过第二次**：该脚本 docstring 记着第一版只用 `(policy, trace)`，
把 device-only 与 +HC 混成一组算出 58.2%，当时的修法是加 `hc` ——
**但没推广到「还有什么属于配置」**。池子是第三条轴。

**修法**：`cluster_by_pool()` 按 ±20（与「KV pool 必须落在 101,432 ± 20」同源）
把每组再聚类，并加自检断言「组内池子跨度 ≤ 容差」。新增 `pool` 列。

**实测影响**：坏组不止那一个 —— 被污染的共 **5 组**（pois200 的 `static=2`/`static=4`，
以及 `load25_*` 与 `load25c_*` 两代实验混在一组的 night25 三条）。
修完后全表 **20 组、max 21.96%**，两条 trace **10 组、0.02–6.08%、22 条 run、
一组 4 条其余各 2 条** —— 与正文那句「ten repeat groups … four runs in one of
them, two in each of the rest」**逐字对上**。所以正文是对的，被改坏的是 CSV。

**反向测试**：第一次做错了 —— 我把 `POOL_TOL` 自己撑大来"破坏聚类"，
而断言的阈值就是 `POOL_TOL`，于是断言恒真、测试**假通过**。
**用同一个常量既做判据又做扰动，等于没测。** 改成只破坏 `cluster_by_pool`
的返回值（不动常量），报错、rc=1 ✓。

### 3.2 `hc` 轴对一半的 run 是瞎的 —— 只披露，不猜

`hicache_enabled` 字段在 **78/155** 条 run 的 metadata 里**根本不存在**
（含正文引用的 `pois200_cap2`、`pois200_cap4`、`cap4`、`realhr_cap2`），
而代码是 `bool(m.get("build", {}).get("hicache_enabled"))` —— 缺失与 False 同值。
于是 `load25c_cap6` 与 `load25c_cap6_hc`（名字带 `_hc`）被归进同一组。

**不改分组，两个理由**：
1. 按**名字里的 `_hc`** 去补，是把命名约定当科学事实 —— 本项目栽过（`no hw`
   不是 no HiCache，是 high-water）；
2. 按 None/False 拆组，会把「一条记了字段、一条没记」的**合法重复对拆散**，
   比现在更坏。

**改法**：加 `hc_src` 列（`meta` / `unknown` / `mixed`）+ 表头写明
「unknown 的组可能混了 +HC 与 device-only」。实测分布 9 / 9 / 2。
论文引的三个数（22.0%、0.02–6.08%、十组）都不落在这些组上，不受影响。

## 四、检查器净变化

495 → **511 项**，0 MISS。本轮新增 16 条，全部做过反向测试（改坏 → 报 MISS → rc=1）：

- §criterion 的 1.1^(1-ε) 两个端点，**与摘要那两个 ε 共用常量**（改 ε 会两边一起动）；
- §V 四条复测臂的旧值/新值 ×2 各一对，外加「位移 = 新 − 旧」的**派生量**检查；
- §VI ready-clock 的分子与分母（分母从**表 I 的 LaTeX 现解析**，不用 `table1.csv`
  —— 后者多一条 `pairA_cap2hc`，表 I 不列它）；
- `if _ab:` 的 else 分支（把「静默不跑」变成显式 MISS）；
- `num_words` 的复合序数修正。

## 五、状态

26 页、0 Overfull、0 undefined、511 项检查 0 MISS、摘要 291 词。
两道审查的全部条目：已处置 20 条（含一b 的两条），明确不处置 2 条（理由见第二节）。
