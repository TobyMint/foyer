# r48 双审查处置记录（2026-09-27）

同一份 brief（`docs/review_brief_r48.md`，19 条）**同时**发给两个审查者：
- **中立子 agent**（Claude，general-purpose，172 次工具调用；沙箱 `/tmp/r48/sb`）
- **codex**（`codex exec`，258,996 tokens）

两边**独立**核了同一批事实，结论有交集也有分歧。下面逐条处置；
**分歧处两边都记，并写明我采纳哪一边、为什么。**

处置前基线：**808 项检查 / 0 MISS / 18 页**。
处置后：**817 项检查 / 0 MISS / 18 页 / 0 Overfull / 0 未定义引用**。

---

## 一、两边一致、我已改的（按严重度）

### 1. ★ `gen_eviction.py` 的判据太粗 —— 它在实验机上**自己报错退出**

**中立审查（第 5 条）报的，codex 因 ssh 被拒没查到。**

- 正文六处写 host-tier 集合 **26**；生成器硬编码名单也是 26；
  但脚本**自己的判据** `_derive()` 在实验机上算出 **27** —— 多的是 `pois200_slice23_hc`。
- 后果：在实验机上跑生成器，**它直接 `raise SystemExit`**
  （`!! host-tier 集合与判据不一致 … ['slice23_hc']`），即这条管线在机器上是坏的。
- 我核过：`slice23_hc` 主 trace、HiCache、999 步、有 `summary.json` —— **满足那三条机械判据**。
  它是**时间片切换实验**（`gen_slice23.py`：cap 每 60 秒在 3 与 2 之间切），
  **不是静态 cap 配置**，本来就不属于「静态配置兑现了多少」这个集合。
  ⇒ **正文的 26 是对的，错的是判据。**

**处置**：加 `NOT_STATIC` 类别（与 `EXCLUDED`/`SUPERSEDED` **分开**记录 —— 那两类
数的是正文那句「Five runs … one … and four superseded」，塞进去会让 5 变成 6）。
实验机实测：`判据重算：host-tier 26 条`、`rc=0` ✓

⚠ **连带发现，已写进落地清单**：同一次输出里 `foyer_scan_r2`/`foyer_sf0_r3` 被列为
「未达 995 步」—— 它们**是**主 trace + HiCache，落地后进入判据集合 ⇒ **集合变 28**，
正文六处的 26 要改，且 `sec_model.tex` 的 `r=+0.85 / 残差 1.92ms` 要**重算**（该处无守卫）。

### 2. ★ §I 的集合限定语漏了「controller」

**中立审查（第 2 条）；codex 未提。**

§I 写「the 0.5 to 4.6 pp between our own repeats of a **fixed** configuration」，
而按那个集合（**全部七组**重复）真值是 **0.49 to 7.55**（`cap4+HC` 一组就 7.55）。
§V 的措辞是对的（「a single **controller** configuration」）。
⇒ 典型「区间必须写出是哪个集合」。

**处置**：§I 加 `\emph{controller}`；并把这条量的守卫从 2 处（§V/§VI）扩到 **3 处**
（含 §I），锚短语里**必须**含 `controller`（漏了就匹配不到 ⇒ MISS）。

### 3. ★ codex：§VII 声称「对 arrival 作了控制」，而那张 trace 没有 arrival 列

**codex 第 18/19 条（同一条的两面）；中立审查未提。**

§VII 原写「queue depth does not order the two tiers **once arrivals and phase are
accounted for**」。实测 `data/replay_night25.csv` 的表头是
`session_id,round_idx,prefix_len,input_len,output_len,tool_wait_after_ms`
—— **没有 `arrival_time`**，所以「已对 arrival 作控制」**做不到**。
而且这是**压缩时静默删掉限定语**的现场：旧版有「25-session trace carries no arrival times」，
被换成了这句意思相反的话。

**处置**：改回事实（「the 25-session trace carries no arrival times, so arrival phase
is not controlled either」），并**新增一类守卫**：**限定语在场检查**
（`check_paper_numbers.py` 的 `_Q` 列表）—— 这类守卫只能钉「某句话还在不在」，
钉不了「有没有说出别的错话」，是**下限**，但比零覆盖强。

### 4. codex：§III「zero retractions」与日志冲突

`pois200_foyer_hz1_r2` 的 `sglang:num_retracted_reqs` 共 **3,190** 个采样，
**其中 1 个非零**（值 1）。所以「with zero retractions」不准确。
**处置**：改成「with no client-side retries and a retraction counter zero in all but
one sample---neither accounts for the excess---」。

### 5. codex：§VI 那句**说得比证据更负**

原句「A margin that appears at one threshold and at a size we cannot resolve
**is not evidence that** adaptive admission works」。
`+1.3044` 是一次**有利读数**，说它「不是证据」比证据更强（往负的方向）。
**这是本项目「没人防」的那一类**（审查 brief 第 18 条点名要查）。
**处置**：`is not evidence that` → `does not establish that`（准确：不足以确立）。

### 6. 两条**死守卫**（值对、守卫不工作）

| 守卫 | 毛病 | 处置 |
|---|---|---|
| `§V τ 高行数` | `"%s\\nhave a $\\tau$"` 里的 `\\n` 是**字面反斜杠+n**，正文里是换行 ⇒ **从未匹配过**；又因 `tier="S"` **从不进 MISS** | 改成 `ck_near` + 锚短语，**P 档**（次要项 75→74 就是它挪档） |
| `idle all_runs median_s` | 退役条目**是孤儿**（全仓库无同名检查），且**理由不实** —— 正文至今印着 `5.0\,s`（`sec_model.tex:23-24`） | 删孤儿条目，**加活守卫** |

> 第 6 条第一行来自中立审查（7b），第二行来自中立审查（12/3）。
> 两条都是「**退役/守卫看起来合理，而事实相反**」那一族。

### 7. 「0.21 to 0.64 across the thirty-one runs」**全无守卫**且**丢了出处**

**中立审查（第 9 条）。** 按「量」搜 `0.21 to 0.64` / `thirty-one runs` 全仓库零命中，
且这一批把旧版的出处括注（哪两列）删掉了。
**处置**：正文改回点名两列（`\texttt{occupancy.csv}` 与 Table I 的交集），**并补守卫**。

### 8. 三处措辞精度（**都朝对自己有利的方向**，中立审查 16/17/18）

| 处 | 原文 | 真值 | 处置 |
|---|---|---|---|
| §VII | 「the red-line knob at **several times** the SLO cost」 | 5.6 vs 2.4 pp = **2.33×**（"several" 通常 ≥3） | → 「**more than twice**」 |
| §VII | 「above **the nearest static point we actually ran**」 | 「最近」**取决于选哪个点**（左锚 `cap3_hc_r2` 给 +5.8；右邻 `cap2` 给 **−1.8**；按墙钟最近是 `cap5`，+60.6） | → 「the nearest static **anchor below them in wall clock**」（与 §II 同一点名） |
| §V/§VI | 「the controller source … **and nothing else**」/「The controller source and the recorded parameters and build **do match**」 | 两份源码差**一个表达式 + 一个注释块**（中立审查真的 diff 了：1 个 hunk）。§VI 那句读起来像「两份源码相同」 | §V → 「that one expression, **plus a comment block**」；§VI → 「The recorded parameters and build do match; the controller source **differs by the one expression named in §V, plus a comment block**」 |

### 9. 在跑的 run 漏进了 `paper/data/concurrency.csv`

**中立审查的额外发现（不在 brief 里）。** 两行 `pois200_foyer_scan_r2` / `pois200_foyer_sf0_r3`
的 τ₂（20.77 / 20.65）是**部分日志**算的，比整个干净控制器族的下界（23.7）还低 3 ms。
根因：实验机上的 `gen_concurrency.py` **是旧版**，缺「在跑的 run 不写自己那行」的过滤，
而仓库那份有 —— **仓库与机器静默分叉**。
**处置**：推仓库版过去；扫描确认**喂正文的目录扫描器里只有它缺护栏**
（`frontier.py` / `gen_projection.py` / `gen_gate_attrib.py` / `gen_repeat_spread.py` 都有）。
**对当前正文零影响**（那两条不在任何表里，且消费者都是逐行取值），已记入 CLAUDE.md。

---

## 二、**两个审查意见相反**的一处，以及我采纳哪边

**§I「we call it an unresolved observation rather than a crossing」**

- **codex（第 15 条）**：若 "crossing" 指**本次读数**，它**已经发生**；
  这句话把观测本身也否定了。建议只否定稳定/因果结论。
- **中立审查（第 15 条）**：明确写了「**站得住，没找到混回去的地方**」，并引了 §V 的分离句。

**处置：采纳 codex 的方向，但用最小改动满足两边。**
改成「so we report it and do not call it a crossing」——
「report it」保住了观测（中立审查关心的），「do not call it a crossing」只否定那个**词**
（codex 关心的）。§V 的「we report the observation and the inference separately」**未动**。

---

## 三、**不改**的，及理由

### 3.1 `gate_attrib` 的 49 / 30.6%（中立审查第 6 条，codex 第 6 条）

两边都报了，两边也都说清了事实：
- **实验机**跑：**48 行 / 上中位 31.3%**
- **本地镜像**跑：**49 行 / 30.6%** —— 与发布的 `paper/data/gate_attrib.csv` **逐字相同**
- 差的一行是 `load25c_budget3_sf0`（25 档、池 101432、`budget3:margin=1.0;sf=0`），
  **它的目录在实验机上被清理了，本地镜像还留着**。

**决定：保留 49 / 30.6%。** 理由：正文那句点名了范围 ——
「over every completed run **in that file**」—— 那个 "file" 就是发布出去的那份 CSV，
而本地镜像**能逐字复现它**（判据链完整）。脚本选 run 的判据是
`glob(*/controller.jsonl)` + 池子匹配，**不区分档位**，25 档那条本来就该在。

⚠ **但这不是「没问题」**：在实验机上按 docstring 跑会得到 48。
**要消灭分歧，该动的是镜像或明确声明删除，不是改正文的数。**
已把这个分叉写进 `gen_gate_attrib.py` 的 docstring 顶部（标题级）。

### 3.2 中立审查「我核不动」清单（5 条）—— 我同样核不动，不假装核过

`foyer_hz1_r2` 的「no client-side retries」需要 runner 侧日志语义（无机械判据）；
`run_matrix.cpython-38.pyc` 对应哪个哈希（pyc 只存 mtime+size，无 md5）；
「旧版被就地覆盖」的过程；`slice23_hc` 的**作者意图**（已按事实改为「不是静态配置」，
未替作者声明「当初就是故意排除的」）。**五条都保持未核状态。**

---

## 四、这一轮**新增的守卫汇总**（803 → 817，净增 **14 条**，含 1 条新类别）

| 守卫 | 条数 | 出处 |
|---|---|---|
| §I / §V / §VI 三处「控制器重复 Δ 全距」上下界 | **6** | 中立审查 2（§V/§VI 原有 4 条，**§I 那处是补的**） |
| §V「the tightest of the N groups」的**组数** | 1 | 同上 |
| §II `horizon=1` 三次运行的 Δ **逐个列出** | **3** | 逆向扫描（该处此前零覆盖） |
| §VII / §III 的 SLO 代价 43.6 | **2** | 逆向扫描（同上） |
| §V τ 高行数（**复活**：原守卫是死的） | 1 | 中立审查 7b |
| §III 全体池的中位（**复活**：原退役是孤儿且理由不实） | 1 | 中立审查 12 |
| 限定语在场：§VII「no arrival times」（**新类别**） | 1 | codex 19 |
| **合计** | **15** | 其中 2 条是「复活」，故净增 **14**（803 → 817） |

⚠ 另修：`landing_triage.py` 里我写的 `TIE = 1.0` 被**既有的唯一性守卫当场抓到**
（改成转调 `frontier.classify`）—— 记在 CLAUDE.md 里当「守卫起作用的正面例子」。

---

## 五、这一轮**独立于两个审查**、由逆向扫描抓到的真错

**`43.7` 应为 `43.6`**（§VII 与 §III 各一处）。

§VII/§III 写「全关节流那条臂 …… 43.7 pp of SLO」。真值：
`table1.csv` 全精度 `foyer_hc 89.7898 − foyfix_hc 46.1461 = 43.6437 ⇒ 43.6`。
**43.7 只有拿两个已印出的舍入列相减（89.8 − 46.1）才拿得到**；
换任何一条基准 run（`_r2` 89.5896、两次均值 89.6897）分别是 43.4 / 43.5。
同段另外三个差值（13.8 / 11.1 / 2.7）**都是全精度算完再舍入**，
§III 另一处的 `12.2` 也验证是全精度（12.2314）—— **所以这是那一处抄错，不是两套口径**。

发现路径：逆向扫描「出现在 ≥2 个 `.tex`、又不在任何 `paper/data/*.csv` 里」的数
（两遍：第二遍把 CSV 值按 1/2/3 位小数**舍入后**再比对）。
第一遍 108 个候选全是噪声（守卫里的值多半是 `"%.1f" % x` 现算的）；
第二遍只剩 3 个，其中 1 个是真错。**方法记在 CLAUDE.md；也记了它的盲区** ——
`5.58` 当时没露头（§II 印 2 位小数、CSV 是全精度），是人工核候选时才发现的。
