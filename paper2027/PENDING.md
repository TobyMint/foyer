# PENDING — 论文里所有还没落地的数字

> 规矩：`\pend{...}` 是红色方括号占位，**投稿前 `grep -c '\\pend{' *.tex` 必须是 0**。
> 每个 `\pend` 在这里有一条对应记录：它等哪条 run / 哪个脚本 / 哪个测量。

## A. 三臂结果（等实验）

| 占位 | 位置 | 等什么 |
|---|---|---|
| `ms-A/B/C`、`e2e-*`、`r50-*`、`r90-*`、`miss-*`、`gp-*`、`work-*`、`hit-*` | `sec_eval.tex` 表 II | 三条 run 跑完 → `scripts/lab/slo_goodput.py --csv` + `atonce_report.py` |
| `busy-*`、`idle-*`、`pr-*`、`ca-*`、`unc-*`、`dec-*`、`hit2-*`、`rr-*` | `sec_eval.tex` 表 III | 三条 run → `scripts/lab/gen_work_decomp.py --csv`（**已写好**） |
| `one-sentence result ...`（Intro / Conclusion / Abstract） | `sec_intro.tex`、`sec_conclusion.tex`、`main.tex` | 上面两张表齐了之后写 |
| `headline number`（Abstract） | `main.tex` | 同上 |
| 分解段落、时间线段落、反事实段落、负结果段落 | `sec_eval.tex` 四个 `\pend` 段 | 表齐 + `fig_timeline` + 反事实脚本 |

**三条 run**：C `l19_foyer_r3`（在跑）、A `l19_default_r2`、B `l19_aimd2`（等空卡）。
跑完的标志是 `summary.json` 存在（`steps.jsonl` 存在不算）。

## B. 部署常数（可以在空卡上量，或从 run 日志反解）

| 占位 | 位置 | 怎么填 |
|---|---|---|
| `cold prefill time` | `sec_background.tex`、`sec_model.tex` | 从 C/A 的冷启动步（`uncached ≈ prompt`）的 `first_token_ms` 取分位 |
| `KB/token`（κ） | `sec_analysis.tex` | 模型配置算：28 层 × 2(KV) × 4 KV heads × 128 dim × 2 B = 57,344 B/token |
| `tok/s`（R） | `sec_analysis.tex` | 冷启动步：`prompt_tokens / first_token_ms` 的中位 |
| `GB/s`（B） | `sec_analysis.tex` | 需要一次微基准（torch H2D 拷贝 2.5GB）；或从 HiCache 命中步的 TTFT 反解 |
| `ratio`（T_rev/T_rec） | `sec_analysis.tex` | 上面三个数代进公式 (4) |
| `host-tokens`、`hw-ratio`、`host-slots` | `sec_analysis.tex` | host = 2× device = 203,004；working set/host = 6.45；host/69.0K = 2.94 |
| `t-star` | `sec_design.tex`、`sec_analysis.tex` | 控制器 `--revoke-after` 的实测标定值（long19 记录为 2.6 s），要从 run 的 policy 串/日志确认 |
| `delta` | 已删（改用覆盖率实测 99.5%） | — |
| `loc` | `sec_impl.tex` | `wc -l controller_budget3.py`（540）+ runner 侧 |

## C. 分析脚本状态

| 脚本 | 状态 | 产出 |
|---|---|---|
| `gen_trace_facts.py` | ✅ | `data/trace_facts.csv`（§2/§3 全部 workload 事实） |
| `slo_goodput.py` | ✅ | `data/slo_goodput.csv`（表 II） |
| `gen_work_decomp.py` | ✅ | `data/work_decomp.csv`（表 III） |
| `gen_engine_constants.py` | ✅（已量 C 的 426 步） | `data/engine_constants.csv`（R、冷 prefill） |
| 反事实脚本 | ❌ 待写 | 离线比较「只限并发」vs「可挂起」 |
| `fig_timeline` | ❌ 待写 | 会话 admit/suspend/resume 时间线 |
| 敏感性（ρ、h） | ❌ 待写 | 日志上的离线扫描 |

⚠ **引擎的 device/host 命中分解拿不到**：SGLang v0.5.10 的
`sglang:cached_tokens_total{cache_source=...}` 在 metrics.csv 里是**空列**（与 itl/e2e/ttft 同病）。
表 III 因此只报聚合命中率 + 重读税；正文里不要写"device 命中 X%、host 命中 Y%"。
若一定要这个拆分，得去 SGLang 的 server 日志里捞（未验证有没有）。

## D. 引用

- `refs.bib` 里 `kvflow` 的标题/作者**未核**（本机无外网）。投稿前逐条核。
- EfficientAgent (2609.33762)、ConServe (2606.01839)、kvlive (2609.16215)、
  KV Residency (2610.22863) 已在正文点名但**没有 cite key**，`sec_related.tex` 里有
  `TODO(cite)` 注释。核过标题/作者后加进 `refs.bib` 再补 `\cite`。

## E. 排版/纪律

- 编译后检查：页数、0 Overfull、0 undefined、无控制字符（沿用旧稿的 `check_paper_numbers.py` 思路）。
- 双盲：作者栏保持 `Anonymous Submission`；致谢里不能出现基金号/姓名。
- GenAI 披露：RTAS 2027 要求，提交时按 CFP 填。
