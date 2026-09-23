# Foyer — 项目约定

内存受限 GPU 上 agentic LLM serving 的准入控制研究。论文在 `paper/`（IEEEtran + LaTeX），
实验在共享的 2×RTX 3090 上跑，原始日志在实验机 `lab-3090:/data/xbw/turnstile/results/`。

## 证据纪律（所有工作都适用）

- **不许编造**引用、实验数字、数据集、结果。数字对不上就报对不上，不要顺手改圆。
- **论文里出现的每个数字都要能追到**代码、日志或 `paper/data/*.csv`。追不到的就标出来，
  不要留在正文里。
- **改 LaTeX 不许改科学含义**。措辞归措辞，结论归结论，两者分开说。
- 下结论前先看文件。涉及实验的陈述必须来自 `results/`、`paper/data/` 或实验机日志。

## 这个项目的三条血的教训

1. **手算的表一定会错。** `paper/data/decomp.csv` 曾有一行 busy/idle 来自另一条 run、
   wall 却是对的，两个数自相矛盾，图 2 因此画错，几个月没人发现。任何汇总表都应由
   `scripts/lab/*.py` 生成并带断言（见 `gen_decomp.py`：busy+idle 必须精确等于采样跨度，
   残差非零直接退出）。
2. **中位数会骗人。** `tool_wait` 中位 0.35 s 让整个项目以为会话不离开引擎；均值是 16.85 s。
   报分布的时候，中位、均值、p90、最大值一起报。
3. **"还没到" 和 "坏了" 长得一样。** 曾三次把「trace 的第一个会话还没到」误判成「实验卡住」。
   判断一个 run 是否正常，先看 `runner.out` 和它已跑时长，别只看 steps=0。

## 撤回记录

已经撤回的主张不许复活，除非有新证据：`tool_wait` 0.1s→16.85s、oracle 单调性、
记账重复计费、驱逐→重算推高步时间（被 `num_retracted_reqs≈0` 与
`prompt_tokens_total == 计划 prefill` 反驳）、空转率随并发单调下降。
详见 `paper/claims_audit.md` 与 `docs/claim_register_20260921.md`。

## 引用红线

- arXiv **2608.30830** 自报对 MORI/Continuum 的 head-to-head 胜利**已被否证，禁引**；
  它的 41% goodput 损失与 ~10× 复活差可以引。
- **PrefixShield (2608.01657)** 已占 "admission responsibility" 术语，需避撞。
- 任何引用的标题、作者、年份都必须核实过才能进 `refs.bib`。**不要凭记忆写文献。**

## 硬件与运维

- 平时只用**卡 2 和卡 3**。卡 0/1 仅限 00:00–08:00 且确认空闲（`memory.used < 200 MiB`）。
- **别人占着卡就等，不要算剩余空间够不够。只在完整的卡上跑。**
- KV pool 必须落在 `101,432 ± 20`，否则该 run 作废，不记录——SGLang 按启动时的空闲显存
  定池子，池子小了数字就不可比。

## 语言

- 对用户回复一律用**中文**。代码、路径、报错原文可保留英文。
- TUI 里不要写 LaTeX 公式，用纯文本或中文名。

## git

commit message 里含反引号时**不要用 `-m`**，走 `-F 文件`——已因此静默丢词三次。
