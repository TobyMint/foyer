# paper2027 — RTAS 2027 投稿（唯一在写的论文）

`../paper/` 是 **2026-09-28 冻结的负结果旧稿**，不投，只作素材（LaTeX 外壳、`refs.bib`、
背景测量）。**这一篇是新的。**

## 故事

> **Admission is a feasibility test, not a threshold.**
> 会话可挂起之后，准入不再是"预测未来 + 调阈值"，而是"容量核算 + 复活定价"。

单一事实源：`../docs/story_synthesis_20261023.md`。

## 编译

```bash
cd paper2027
latexmk -pdf main.tex        # 需要 IEEEtran
```

## 数字纪律

- 正文里每个数都要能追到 `data/*.csv` 或 `scripts/lab/*.py` 的产物。
- 没落地的数写成 `\pend{...}`（红色方括号），并在 `PENDING.md` 里登记。
- **投稿前 `grep -c '\\pend{' *.tex` 必须是 0。**

## 数据来源

| 文件 | 生成器 | 说明 |
|---|---|---|
| `data/trace_facts.csv` | `scripts/lab/gen_trace_facts.py` | §2/§3 的全部 workload 事实（12.9×、13×、14×、0.18s/15.9s、储备覆盖率…） |
| `data/slo_goodput.csv` | `scripts/lab/slo_goodput.py` | 三臂的 makespan / 端到端 / round latency / deadline miss / goodput |

trace 本体：`../data/replay_long19.csv`（md5 `c753fa4f10`，602 轮，与实验机
`/data/xbw/turnstile/data/replay_long19.csv` 一致）。

## 当前状态（2026-10-23）

- 骨架完成：10 节 + 摘要 + 2 张结果表 + 2 张图占位，全部论点已写成正文。
- 三臂实验：C 在跑（`l19_foyer_r3`），A/B 等空卡。表 II/III 全是 `\pend`。
- 待办见 `PENDING.md`。
