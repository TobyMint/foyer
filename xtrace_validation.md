# 跨 trace 验证：分段弹性判据能不能迁移到第二条工作负载

**日期** 2026-09-23 · **脚本** `scripts/lab/gen_elasticity_x.py` · **数据** `paper/data/elasticity_x.csv`

审稿人（codex）的批评：§IV 的 ε 只在一条 trace 上测过，却用来解释控制器为什么输，
是 "cross-policy association, not a transportable causal derivative"。本文档在第二条
工作负载 `replay_realhr.csv` 上重算同一组量并做判决。

---

## 0. 先说一件必须先纠正的事：主 trace 到底是哪条

任务书里写「主 trace `replay_night200_clean.csv`，cap1–cap5 的 run 名是
`budget200c_cap1`…`budget200c_cap5`」。**核对 metadata 后，这两条都不对**，而且
按名字找 run 恰好是本项目踩过的坑（memo《run 身份与目录卫生》）。

| run | metadata 里的 `trace` | trace_md5 | wall_s | 对得上 decomp.csv 吗 |
|---|---|---|---|---|
| `pois200_cap1` | `replay_pois200_l04.csv` | `df4bdd37e5` | 32013.1 (=533.6 min span) | **是**，cap1 span_min=533.6 |
| `budget200c_cap1` | `replay_night200_clean.csv` | `4570fc5561` | 30939.7 (=515.7 min) | **否**，515.7 ≠ 527.4/533.6 |

`paper/data/decomp.csv` 与 `paper/data/elasticity.csv` 的 cap1–cap5 全部来自
**`pois200_cap1/2/3_fixed/4/5`**，工作负载是 `replay_pois200_l04.csv`（合成泊松 λ=0.04/s，
200 会话 999 步）。`budget200c_*` 是齐射（flash-crowd）档，是另一条 trace，与本次验证无关。

直接验证：对 `budget200c_cap*` 跑同一个 `gen_decomp.py`，得到的是**另一张表**——
`cap1 512.0 min / τ₁ 27.5 ms`、`cap2 298.0 / 27.1`、`cap4 261.9 / 35.0`、`cap5 261.7 / 36.5`，
与 `decomp.csv` 的 `527.4 / 28.8`、`304.2 / 27.4`、`249.9 / 32.4`、`260.9 / 36.7` 逐行都不同。

```bash
python3 scripts/lab/gen_decomp.py results/night /tmp/decomp_b200c.csv \
        budget200c_cap1 budget200c_cap2 budget200c_cap4 budget200c_cap5
# -> budget200c_cap1 512.0/515.6 ... budget200c_cap4 261.9/265.6 ...
```

两者数值很接近（cap2 298.0 vs 304.2、cap4 261.9 vs 249.9），**正因如此按名字取 run
几乎必然出错**——这正是本仓 memo《run 身份与目录卫生》记的那次事故。

**本文档所说的「主 trace」一律指 `replay_pois200_l04.csv`。**

## 1. 数据来源与拉取

```bash
# 主 trace 的 5 个静态 cap（decomp.csv / elasticity.csv 的来源）
for r in pois200_cap1 pois200_cap2 pois200_cap3_fixed pois200_cap4 pois200_cap5; do
  rsync -a --exclude='runner.out' lab-3090:/data/xbw/turnstile/results/night/$r/ \
        results/night/$r/
done
# 第二条 trace 的 run
for r in realhr_cap1 realhr_cap2 realhr_cap3 realhr_cap4 realhr_foyer; do
  rsync -a --exclude='runner.out' lab-3090:/data/xbw/turnstile/results/night/$r/ \
        results/night/$r/
done
# 一致性抽查用（见 §5）
rsync -a --exclude='runner.out' lab-3090:/data/xbw/turnstile/results/night/pois200_foyer_hc/ \
      results/night/pois200_foyer_hc/
```

全部未用 `--delete`，本地已有文件未动。两条 trace 原文本地 `data/` 已有，且与实验机
**逐字节相同**：

```
df4bdd37e5b7241b2433edaeeea3789c  data/replay_pois200_l04.csv   (= metadata trace_md5 df4bdd37e5)
882c29a022b475c4907cde1213156c34  data/replay_realhr.csv        (= metadata trace_md5 882c29a022)
```

## 2. 复现主 trace 的分段弹性（基准）

```bash
python3 scripts/lab/gen_decomp.py results/night /tmp/decomp_repro.csv \
        pois200_cap1 pois200_cap2 pois200_cap3_fixed pois200_cap4 pois200_cap5
python3 scripts/lab/gen_elasticity.py /tmp/decomp_repro.csv /tmp/elasticity_repro.csv
```

`/tmp/elasticity_repro.csv` 与 `paper/data/elasticity.csv` **`diff` 报 IDENTICAL**。
四个分段值逐位复现：

| 段 | R̄busy | τ₁ ms | ε | 论文值 | 对上？ |
|---|---|---|---|---|---|
| cap1→cap2 | 1.00 → 1.27 | 28.8 → 27.4 | **−0.21** | −0.21 | ✓ |
| cap2→cap3 | 1.27 → 1.53 | 27.4 → 29.7 | **+0.43** | +0.43 | ✓ |
| cap3→cap4 | 1.53 → 1.65 | 29.7 → 32.4 | **+1.15** | +1.15 | ✓ |
| cap4→cap5 | 1.65 → 1.84 | 32.4 → 36.7 | **+1.14** | +1.14 | ✓ |

decomp 的 `running`（busy 条件均值）与 `step_perreq_ms` 也与 `paper/data/decomp.csv`
逐行相同。**基准没有问题。**

> 口径提醒（写在脚本注释里，防止下一个人再踩）：ε 是两个对数之比，分母
> ln(R̄₁/R̄₀) 在 R̄≈1.5 时只有 0.076。R̄ 只留 2 位小数就能把它挪 3%，于是
> cap3→cap4 从 1.15 变成 **1.20**（用未取整 R̄）。新脚本主列 `eps_tau1` 严格复刻
> `gen_elasticity.py` 的输入精度（τ₁ 1 位、R̄ 2 位），`eps_tau1_full` 才是未取整的。

## 3. 第二条 trace：realhr

`replay_realhr.csv`，真实 Claude agent 会话（`claude:df7977ee-…`），117 会话 390 步。
`summary.json` 里 `server_prefix_hit_rate` 与 `docs/parked_scenarios.md` §3 的表对得上
（cap2 64.5%）。

### 3.1 两条 trace 是不是同一族（中位/均值/p90/最大 一起报）

| | main `pois200_l04` | realhr |
|---|---|---|
| 会话 / 步 | 200 / 999 | 117 / 390 |
| 到达跨度 | 79.6 min | 59.8 min |
| prompt tokens 中位/均值/p90/最大 | 23187 / 28555 / 51064 / 89436 | 18809 / 18586 / 21834 / 29597 |
| 输出 tokens 中位/均值/p90/最大 | 275 / 707 / 1861 / 13223 | 241 / 310 / 785 / 1366 |
| tool_wait ms 中位/均值/p90/最大 | 73 / 12655 / 18991 / 300000 | 10556 / 29115 / 65918 / 538180 |
| tool_wait 零值 / >1 s / >10 s | 34% / 37% / 14% | 29% / 71% / 50% |

两条 trace 的请求形状（prompt/输出规模）比预想的接近；真正的差别在**会话间的思考停顿**：
主 trace 一半以上的步几乎不等（中位 73 ms），realhr 一半的步等 10 s 以上。
按均值算两者只差 2.3 倍（12.7 s vs 29.1 s）——只报中位会把这个差别说成 145 倍。

### 3.2 R̄busy / τ / 分段弹性（**一律用 busy 条件均值**）

`running_busy = 全时段均值 / busy 占比`，`τ₁ = busy_min × 60 × R̄busy / tokens × 1000`。
与 `gen_decomp.py` 逐字一致（新脚本直接 `import gen_decomp`，不复制实现）。

| run | 步 | 墙钟 min | busy min | idle% | R̄busy | tokens | τ₁ ms | τ₂ ms | SLO@10s | 命中% |
|---|---|---|---|---|---|---|---|---|---|---|
| `realhr_cap2` | 390 | 128.4 | 83.3 | 36.8 | **1.077** | 121020 | 44.5 | 20.3 | 100.0 | 64.5 |
| `realhr_cap3` | 390 | 87.0 | 65.1 | 28.4 | **1.161** | 121020 | 37.5 | 20.9 | 99.7 | 62.2 |
| `realhr_cap4` | 390 | 66.9 | 57.1 | 19.1 | **1.287** | 121020 | 36.4 | 22.0 | 99.5 | 58.2 |
| `realhr_foyer` | 390 | 75.6 | 62.0 | 21.8 | **1.223** | 121020 | 37.6 | 21.6 | 100.0 | 59.8 |

四条 run 的 tokens 完全相同（121020，`summary.json` 的 `output_token_delta: 0`），
所以横向比的是"同样的活干了多久"，不是"干了多少活"。

> ⚠ **墙钟有两个口径，别抄错列。** 上表的墙钟是 `run_summary.py` / `gen_decomp.py` /
> `frontier.py` 三处共用的那一个：**最后一个完成 − 最早一个提交**，从 steps.jsonl 算。
> `docs/runs_registry.md` 和 `docs/parked_scenarios.md` §3 用的是另一个：metadata 的
> `wall_s`（引擎自报，含起停）。同一个 `realhr_cap2`，前者 128.4 min、后者 7916.7 s = 131.9 min。
> 本次验证与论文 Table（`paper/data/runs.csv`）同口径，都是前者。

分段弹性：

| 段 | R̄busy | τ₁ ms | **ε(τ₁)** | ε_full | ε(τ₂) | τ₁ ±5% / ±10% 噪声带 |
|---|---|---|---|---|---|---|
| cap2→cap3 | 1.08 → 1.16 | 44.5 → 37.5 | **−2.40** | −2.28 | +0.41 | [−3.80, −0.99] / [−5.20, +0.41] |
| cap3→cap4 | 1.16 → 1.29 | 37.5 → 36.4 | **−0.28** | −0.27 | +0.48 | [−1.22, +0.66] / [−2.17, +1.61] |

**两条 trace 的弹性曲线不一样，而且差得不是一点。** 主 trace 在 R̄ 1.27 之后 ε 转正、
1.53 之后过 1（贵段）；realhr 在 1.08→1.29 全程 ε<0，即加并发不但不亏，反而是赚的
（cap2→cap4 只多了 19% 的并发，墙钟少了 48%）。

两个口径在 realhr 上**符号相反**：模型自洽的 τ₁ 说 ε<0（−2.40 / −0.28），唯一独立于墙钟的
τ₂（逐请求 decode 间隔中位）说 ε>0（+0.41 / +0.48）。τ₂ 在两条 trace 上其实很一致
（主 trace 前三段 +0.42/+0.47/+0.47，realhr +0.41/+0.48），但 τ₂ 只测 decode，
不能代进含 prefill 的吞吐式（论文已声明），而且 τ₂ 说悬崖在 cap4 之后而不是 cap3 之后。
**这条分歧必须照实报：realhr 的结论取决于你用哪个 τ。**

## 4. realhr 的静态前沿与 realhr_foyer 的 Δ

静态点只有 **3 个**（cap2/cap3/cap4），全部无 HiCache——与控制器臂是同一种运行配置，
所以这一族内部可比。三个点都落在上左包络上，谁也没支配谁。
按 `frontier.py` 内部逻辑（分段线性插值、±1.0 pp 判带、范围外不外推）算：
（代码代不一致的问题见 §6.3，这里不能声称三点完全同源。）

| 锚点 | 墙钟 min | SLO@10s | SLO@5s | 命中% |
|---|---|---|---|---|
| `realhr_cap4` | 66.9 | 99.5 | 92.3 | 58.2 |
| `realhr_cap3` | 87.0 | 99.7 | 97.4 | 62.2 |
| `realhr_cap2` | 128.4 | 100.0 | 99.0 | 64.5 |

`realhr_foyer`（75.6 min，SLO@10s 100.0%，命中 59.8%）：

- **SLO@10s 轴（论文口径）：Δ = +0.40 pp → ON（在线上，不算赢）**
- SLO@5s 轴（敏感性）：Δ = +1.87 pp → ABOVE
- 命中率轴：Δ = −0.14 pp → ON
- 相对最快的纯静态 cap：**75.6 vs 66.9 min，慢 13.2%**

> ⚠ **SLO@10s 在 realhr 上退化**：四个点的 SLO 是 99.5~100.0，阈值 10 s 分辨不出任何东西，
> 所以"+0.40 pp 落在线上"这条判决**几乎没有信息量**——它只说明没人违反 10 s。
> 真正有分辨力的轴是墙钟（foyer 慢 cap4 13.2%）和命中率（foyer 排在 cap4 与 cap3 之间，
> 仍然没越过包络）。SLO@5s 那一列不是论文登记的阈值，是我为了让轴恢复分辨力加的，
> **不能拿它当判决**，列在这里只是为了说明判决对阈值敏感。

## 5. 核心检验：判据的预测 vs 实测

| | 内容 |
|---|---|
| **判据的输入** | `realhr_foyer` 的 R̄busy = **1.223** |
| **落在哪一段** | realhr 的 **cap3→cap4 段**，ε(τ₁) = **−0.28**（R̄ 1.16~1.29，τ₁ 37.5→36.4 ms） |
| **判据的预测** | ε 远小于 1，这一段加并发**几乎免费甚至倒赚**；判据**没有**给出控制器应当失败的理由。按判据，foyer 只要往右挪到 cap4 的运行点就该拿到吞吐。 |
| **实测** | 墙钟 75.6 min，**比最快的静态 cap（cap4, 66.9 min）慢 13.2%**；SLO@10s 轴 Δ=+0.40 pp（ON，不算赢），命中率轴 Δ=−0.14 pp（ON），都没越过前沿。 |

> ⚠ 这 13.2% 本身**在运行间抖动之内**（同配置重复对的墙钟极差可到 22.4%，见 §6.2），
> 所以"Foyer 比 cap4 慢"**不是一个被确立的结论**。被确立的只有反面那句：
> **Foyer 没有越过 realhr 的静态前沿**——它在论文口径下 ON、在命中率轴上 ON（还略低），
> 而论文要求的是 ABOVE。**"判据预测它该赢" vs "实测它没赢"，这一对是稳的；
> "实测它输了"不是。**

**三个点按 R̄busy 排出来是一条干净的单调线（两条 trace 都是）：**

```
realhr :  R̄busy 1.08 → 128.4 min   R̄busy 1.16 → 87.0 min
          R̄busy 1.22 →  75.6 min (Foyer)   R̄busy 1.29 → 66.9 min
main   :  R̄busy 1.00 → 527.4 min   R̄busy 1.27 → 304.2 min   R̄busy 1.35 → 291.3 min
          R̄busy 1.53 → 258.7 min   R̄busy 1.65 → 249.9 min   R̄busy 1.84 → 260.9 min
```

R̄busy 来自 metrics 采样器，墙钟来自 steps.jsonl，两个独立来源，所以这条排序不是循环论证。
**Foyer 的墙钟恰好就是它运行点该有的墙钟——它没有输给判据，它是跑在了 cap4 的左边。**

### 判决：这次验证**削弱**了「弹性判据可以跨 trace 迁移」

分四条讲清楚，不粉饰：

1. **判据的机制在 realhr 上不存在。** 论文的解释是「九条臂跑在 R̄busy 1.35~1.69，
   五条落在 ε≈1.15 的贵段，所以加并发不划算」。realhr_foyer 的 R̄busy=1.22，
   **比九条主 trace 臂里的任何一条都低**，落在最便宜的一段，仍然没赢过最好的静态 cap。
   也就是说：在第二条工作负载上，控制器失败**不是因为**它卡在贵段。
   判据给出的那个因果机制不迁移。

2. **判据的操作区间在 realhr 上根本够不着。** 论文的判据全部内容在
   「R̄≈1.5 以上 ε 过 1」这个悬崖上。realhr 的最大 R̄busy 是 **1.29**，三个静态点
   一个都没到 1.5。所以跨 trace 检验只覆盖了曲线的**便宜一半**，
   贵段那一半在第二条 trace 上是**未测**而不是**被证实**。

3. **在两条 trace 重叠的区间（R̄≈1.0–1.3）里，判据的符号是对的。**
   主 trace cap1→cap2 是 −0.21，realhr cap3→cap4 是 −0.28，差 0.07。
   两边的墙钟都在这一段随 R̄busy 单调下降，且都在某个点之后反转（realhr 没跑到反转点）。
   这是**弱支持**：判据的定性方向在第二条负载上成立。但它是判据最没有争议的那一半。

4. **判据的定量部分连在自己家里都不稳。** 把 τ₁ 各自 ±10%（本仓同 policy 同 trace
   的重复对实测墙钟极差是 1.2%~22.4%，见 §6）重算：主 trace cap3→cap4 的
   ε=1.15 变成 **[−1.51, +3.81]**，realhr cap3→cap4 的 −0.28 变成 **[−2.17, +1.61]**。
   **两条 trace 的噪声带都跨过了 1。** 论文「五条落在 ε≈1.15 的贵段」这句话，
   在 ±10% 的运行间抖动下不成立——这不是跨 trace 才有的问题，是判据本身的问题。

一句话：**realhr 没有复现主 trace 的弹性曲线，只复现了它在低并发段的方向（符号）。
判据作为"这个策略运行在曲线哪一段"的诊断在第二条负载上仍然可算、且算得出与实测一致的
排序；但作为"控制器为什么输"的解释，它给出的那个机制（卡在 ε≥1 的贵段）在 realhr 上
不成立——那里的控制器压根没进过贵段。**

## 6. 数据局限性（这些都必须写进论文的 Limitations）

1. **静态点只有 3 个，且没有一个到 R̄busy 1.5。** 判据的核心区间在 realhr 上未采样。
   `realhr_cap1` 本可以补第 4 个点，但**不可用**：只有 84/390 步（27/117 会话），
   无 `summary.json`、metadata 无 `wall_s`，run 被截断；而且 cap=1 时 R̄busy 恒等于 1，
   本来就不构成一个信息点。已明确排除，未用任何东西替代。
2. **每个配置只有一次 run，没有重复。** 本仓「同 policy + 同 trace、落地 ≥2 条」的重复对
   实测墙钟极差 **1.2%~22.4%**（唯一的例外是 `budget3` 在 night200 上的 85.9%，
   那是一组不稳定的控制器配置，不是静态 cap）。realhr 的 ε 是两个单次测量之比，
   **只能信符号，不能信量级**——§5 第 4 条的 ±10% 噪声带就是按这个量级取的。
3. **代码代混淆。** realhr 的 cap2 与 foyer 跑在 09-16（metadata 无 `code` 块，老 schema），
   cap3/cap4 跑在 09-20（`session_runner=34e5cea815f5`）。**同一份 ε 曲线的两端来自不同代码代。**
   主 trace 的基准同样如此（cap2/cap4 老代码，cap1/cap5 `34e5cea8`，cap3_fixed `5d40964a`）。
   跨代码代的重复对极差是 **3.5%~11.5%**（`static=2/3/4` night25 等 6 组），
   同代码代的重复对极差是 **1.2%~22.4%**——两者**重叠**，所以
   **代码代效应没有被分离出来**，是个未消除的混淆，不是可以忽略的项。
4. **哪些结论稳、哪些不稳**：cap2 比 cap4 慢 92%，远超重复对极差上限 22.4%，
   所以"cap2 ≫ cap4"这个排序是稳的；realhr_foyer 比 cap4 只慢 13.2%，
   **落在抖动范围内，"Foyer 输了"不成立**，成立的只是"Foyer 没赢"。
   ε=−2.40 这个量级不稳（见 §5 第 4 条）。
5. **SLO@10s 轴在 realhr 上退化**（四点在 99.5~100.0），论文的 ±1.0 pp 判决带在这里
   没有分辨力。realhr 的有效判决轴是墙钟和命中率。
6. **规模/形状差异**：390 步 vs 999 步、117 vs 200 会话、tool_wait 中位 10.6 s vs 73 ms。
   两条 trace 的请求规模接近，差在会话间停顿。
7. **realhr 上静态 cap 几乎不 binding**：`num_running_reqs >= cap` 的采样占比
   cap2 4.8% / cap3 1.2% / cap4 0.2%，排队深度均值 0.003~0.020、最大 2
   （对比主 trace 的 cap4：排队 >0 的采样 **61.6%**、排队均值 1.18）。
   也就是说 realhr 上并发由到达+工具等待决定，不由准入决定——
   这既解释了为什么判据测不动，也说明"准入控制在 realhr 上本来就是个小问题"。

## 7. 一致性抽查（防止第二套实现漂移）

- `gen_elasticity_x.py` 直接 `import gen_decomp`，decompose/read_metrics/step_perreq_ms
  都是同一份代码；`busy+idle==span` 的断言在 realhr 五条 run 上都通过。
- `pois200_foyer_hc` 本脚本算出的 `running_busy = 1.353`，与 `paper/data/arm_running.csv`
  里 `foyer_hc` 那行的 `running_busy = 1.353` 相同（那是由 `gen_arm_running.py` 独立算的）。
- `realhr_foyer` 的 τ₁=37.6 ms、`realhr_cap2` 的 44.5 ms 与 `gen_decomp.py` 单独跑出来的
  `step_back_ms` 逐位相同。
- 主 trace 五个 cap 的 wall/busy/running/τ₁ 与 `paper/data/decomp.csv` 逐行相同。

## 8. 完整命令与原始输出

```bash
python3 scripts/lab/gen_elasticity_x.py results/night paper/data/elasticity_x.csv
```

```
==============================================================================
### 两条 trace 是不是同一族（中位/均值/p90/最大 一起报）
  main    pois200_l04 (合成泊松, 200 会话)  md5=df4bdd37e5…  会话 200, 步 999, 到达跨度 79.6 min
           prompt tokens 中位=  23187.0 均值=  28555.4 p90=  51064.0 最大=  89436.0
           输出 tokens     中位=    275.0 均值=    706.7 p90=   1861.0 最大=  13223.0
           tool_wait ms  中位=     73.0 均值=  12654.7 p90=  18991.0 最大= 300000.0
  realhr  replay_realhr (真实高峰小时, 117 会话)  md5=882c29a022…  会话 117, 步 390, 到达跨度 59.8 min
           prompt tokens 中位=  18809.0 均值=  18586.2 p90=  21834.0 最大=  29597.0
           输出 tokens     中位=    241.0 均值=    310.3 p90=    785.0 最大=   1366.0
           tool_wait ms  中位=  10556.0 均值=  29115.3 p90=  65918.0 最大= 538180.0
==============================================================================
### main — pois200_l04 (合成泊松, 200 会话)
cap              步    墙钟min    busy%   R̄busy    tokens    τ₁ ms    τ₂ ms  SLO@10s%      命中%
cap1           999    527.4     63.7     1.00    706010     28.8     20.6      94.8     69.9
cap2           999    304.2     81.6     1.27    706010     27.4     22.8      89.5     67.7
cap3           999    258.7     86.0     1.53    706010     29.7     24.9      74.4     59.7
cap4           999    249.9     89.6     1.65    706010     32.4     25.8      55.7     45.9
cap5           999    260.9     87.9     1.84    706010     36.7     31.2      27.1     27.5

  分段弹性（ε(τ₁) 用 2 位小数的 R̄，与论文 §IV 同算法；ε_full 用未取整 R̄）
  from      -> to           R̄0    R̄1     τ₁0     τ₁1    ε(τ₁)   ε_full    ε(τ₂)   τ₁ ±5% / ±10% 噪声带
  cap1      -> cap2        1.00   1.27    28.8    27.4    -0.21    -0.21    +0.42   [-0.63,+0.21] / [-1.05,+0.63]
  cap2      -> cap3        1.27   1.53    27.4    29.7    +0.43    +0.43    +0.47   [-0.10,+0.97] / [-0.64,+1.51]
  cap3      -> cap4        1.53   1.65    29.7    32.4    +1.15    +1.20    +0.47   [-0.17,+2.48] / [-1.51,+3.81]
  cap4      -> cap5        1.65   1.84    32.4    36.7    +1.14    +1.14    +1.74   [+0.23,+2.06] / [-0.70,+2.98]

  控制器臂 Foyer+HiCache (pois200_foyer_hc): 墙钟 291.3 min, R̄busy 1.35, SLO@10s 89.8%, 命中 69.7%
    → 落在 ε(τ₁)=+0.43 段（R̄ 1.27~1.53，τ₁ 27.4→29.7 ms，ε(τ₂)=+0.47）
    → Δ = +4.60 pp（SLO@10s，论文口径）/ +4.12 pp（SLO@ 5s）/ +4.28 pp（命中率轴）
      ※ 这条包络用的是主 trace 的【纯静态 cap】，与论文 Table 的前沿（带 HiCache 锚点）
        不是同一条，两族的 Δ 不可直接比，列在这里只是为了让两族走同一套代码路径。

### realhr — replay_realhr (真实高峰小时, 117 会话)
cap              步    墙钟min    busy%   R̄busy    tokens    τ₁ ms    τ₂ ms  SLO@10s%      命中%
cap2           390    128.4     63.2     1.08    121020     44.5     20.3     100.0     64.5
cap3           390     87.0     71.6     1.16    121020     37.5     20.9      99.7     62.2
cap4           390     66.9     80.9     1.29    121020     36.4     22.0      99.5     58.2

  from      -> to           R̄0    R̄1     τ₁0     τ₁1    ε(τ₁)   ε_full    ε(τ₂)   τ₁ ±5% / ±10% 噪声带
  cap2      -> cap3        1.08   1.16    44.5    37.5    -2.40    -2.28    +0.41   [-3.80,-0.99] / [-5.20,+0.41]
  cap3      -> cap4        1.16   1.29    37.5    36.4    -0.28    -0.27    +0.48   [-1.22,+0.66] / [-2.17,+1.61]

  静态前沿（锚点）：
    wall=   66.9  SLO@10s= 99.5     wall=   87.0  SLO@10s= 99.7     wall=  128.4  SLO@10s=100.0
    wall=   66.9  SLO@ 5s= 92.3     wall=   87.0  SLO@ 5s= 97.4     wall=  128.4  SLO@ 5s= 99.0

  控制器臂 Foyer (realhr_foyer): 墙钟 75.6 min, R̄busy 1.22, SLO@10s 100.0%, 命中 59.8%
    → 落在 ε(τ₁)=-0.28 段（R̄ 1.16~1.29，τ₁ 37.5→36.4 ms，ε(τ₂)=+0.48）
    → Δ = +0.40 pp（SLO@10s，论文口径）/ +1.87 pp（SLO@ 5s）/ -0.14 pp（命中率轴）
      SLO@10s 判决：ON (在线上, 不算赢)；命中率轴判决：ON (在线上, 不算赢)
    → 相对最快的纯静态 cap: 75.6 vs 66.9 min（+13.2%）
    → 按 R̄busy 升序（n=4 个点）：
       R̄busy= 1.08  墙钟= 128.4 min   cap2
       R̄busy= 1.16  墙钟=  87.0 min   cap3
       R̄busy= 1.22  墙钟=  75.6 min   Foyer
       R̄busy= 1.29  墙钟=  66.9 min   cap4

!! 数据不足以入表：
   realhr_cap1    [static=1] 84/390 步（27/117 会话），无 summary.json、metadata 无 wall_s，
                  run 被截断；R̄ 与 τ 只在残段上算得，且 cap=1 时 R̄busy 恒等于 1，不构成一个信息点
==============================================================================
-> paper/data/elasticity_x.csv（18 行）
```

产出：`paper/data/elasticity_x.csv`（18 行：2 trace + 9 run + 6 segment + 2 arm，
三种 `kind`；列含 `eps_tau1 / eps_tau1_full / eps_tau2 / eps_lo5 / eps_hi5 / eps_lo10 / eps_hi10`）。

### 8.1 §6.7「cap 几乎不 binding」的来源

```bash
cd /root/paper/foyer && python3 - <<'EOF'
import csv
for r,cap in [("realhr_cap2",2),("realhr_cap3",3),("realhr_cap4",4),("realhr_foyer",None),
              ("pois200_cap2",2),("pois200_cap4",4)]:
    rd=list(csv.DictReader(open("results/night/%s/metrics.csv"%r)))
    rn=[float(x["sglang:num_running_reqs"]) for x in rd if x["sglang:num_running_reqs"]]
    qq=[float(x["sglang:num_queue_reqs"]) for x in rd if x["sglang:num_queue_reqs"]]
    n=len(rn)
    print("%-14s n=%4d  在跑>=cap 的采样 %4.1f%%  在跑 max=%d  排队>0 的采样 %5.1f%%  排队 max=%d 排队均值=%.3f" %
          (r,n,(100*sum(1 for x in rn if cap is not None and x>=cap)/n) if cap else -1,
           int(max(rn)), 100*sum(1 for x in qq if x>0)/n, int(max(qq)), sum(qq)/n))
EOF
```

```
realhr_cap2    n=1577  在跑>=cap 的采样  4.8%  在跑 max=2  排队>0 的采样   0.3%  排队 max=1 排队均值=0.003
realhr_cap3    n=1087  在跑>=cap 的采样  1.2%  在跑 max=3  排队>0 的采样   0.7%  排队 max=2 排队均值=0.008
realhr_cap4    n= 844  在跑>=cap 的采样  0.2%  在跑 max=4  排队>0 的采样   1.9%  排队 max=2 排队均值=0.020
realhr_foyer   n= 948  在跑>=cap 的采样 -1.0%  在跑 max=4  排队>0 的采样   0.3%  排队 max=1 排队均值=0.003
pois200_cap2   n=3711  在跑>=cap 的采样 22.2%  在跑 max=2  排队>0 的采样  14.6%  排队 max=1 排队均值=0.146
pois200_cap4   n=3080  在跑>=cap 的采样  0.7%  在跑 max=4  排队>0 的采样  61.6%  排队 max=3 排队均值=1.178
```

（`realhr_foyer` 一行 `-1.0%` 是因为它是控制器 arm、没有静态 cap，不是测量值。）

### 8.2 §6.2/§6.3 重复对极差与代码代的来源

```bash
ssh lab-3090 'python3 - <<"PY"
import json,glob,os,collections
rows=[]
for p in glob.glob("/data/xbw/turnstile/results/night/*/metadata.json"):
    try: m=json.load(open(p))
    except Exception: continue
    r=os.path.basename(os.path.dirname(p)); code=m.get("code") or {}
    rows.append((m.get("policy","?"), os.path.basename(str(m.get("trace",""))),
                 r, code.get("session_runner","(old)"), m.get("wall_s")))
g=collections.defaultdict(list)
for pol,tr,r,sr,w in rows: g[(pol,tr)].append((sr,w,r))
for k,v in sorted(g.items()):
    if len(v)<2: continue
    ws=[x[1] for x in v if x[1]]
    if len(ws)!=len(v): continue
    srs=sorted({x[0] for x in v})
    print("  %-36s %-18s walls_min=%s  极差%.1f%%  sr=%s%s" % (
        k[0][:36], k[1][:18], str([round(x/60,1) for x in sorted(ws)]),
        100*(max(ws)-min(ws))/min(ws), "/".join(s[:6] for s in srs),
        "  <== session_runner 不同（跨代码代）" if len(srs)>1 else ""))
PY'
```

```
  aimd                                 replay_night200.cs walls_min=[267.1, 272.1, 277.3]  极差3.8%  sr=(old)
  budget2                              replay_night200.cs walls_min=[227.1, 231.4, 263.6]  极差16.1%  sr=(old)
  budget2                              replay_night25.csv walls_min=[27.9, 31.1]  极差11.6%  sr=(old)
  budget3                              replay_night200_cl walls_min=[360.0, 540.1, 555.3, 669.2]  极差85.9%  sr=(old)
  budget3                              replay_night25.csv walls_min=[54.8, 59.0, 62.1]  极差13.2%  sr=(old)
  budget3:hw=0;target=0.95             replay_night25.csv walls_min=[31.4, 33.0, 33.9]  极差8.2%  sr=(old)/5d4096  <== 跨代码代
  budget3:hw=0;target=0.95;horizon=1   replay_pois200_l04 walls_min=[262.0, 267.0]  极差1.9%  sr=5d4096
  default                              replay_night25.csv walls_min=[31.5, 32.2]  极差2.1%  sr=(old)
  foyer:target=0.90;gs=0.35            replay_pois200_l04 walls_min=[300.2, 319.1]  极差6.3%  sr=34e5ce/5d4096  <== 跨代码代
  foyer:target=0.99;gs=0.05;hs=0.98    replay_pois200_l04 walls_min=[362.0, 377.6]  极差4.3%  sr=34e5ce/5d4096  <== 跨代码代
  static=2                             replay_night200_cl walls_min=[298.2, 301.7]  极差1.2%  sr=(old)
  static=2                             replay_night25.csv walls_min=[36.1, 37.4]  极差3.5%  sr=(old)/5d4096  <== 跨代码代
  static=3                             replay_night25.csv walls_min=[28.0, 30.4]  极差8.7%  sr=(old)/5d4096  <== 跨代码代
  static=4                             replay_night200.cs walls_min=[223.4, 224.3, 233.8]  极差4.7%  sr=(old)
  static=4                             replay_night25.csv walls_min=[27.2, 30.4]  极差11.5%  sr=(old)/5d4096  <== 跨代码代
  static=6                             replay_night25.csv walls_min=[22.8, 27.0, 27.9]  极差22.4%  sr=(old)
```

> 注意：跨代码代的 6 组极差是 3.5%~11.5%，同代码代的组是 1.2%~22.4%（`budget3` night200
> 的 85.9% 除外，那是一组不稳定的控制器配置）。两者**重叠**，所以代码代效应
> **没有被分离出来**，不能说它无关紧要，也不能说它必然有害。
