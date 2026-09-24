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
1b. **从错的列抄数 —— 已经犯过四次。** 手抄汇总表时把相邻一列的数当成目标列：
   `pairB_cap2hc` 的 busy/idle 来自另一条 run、`foyer_hz2`/`foyer_hz0` 的 running
   抄错、表 I 的 rg4/foyfix 两行 Δ 用了中途读数、相关工作的「round-1+ 命中率
   89.8%」其实是 foyer_hc 的 **SLO**（真值 80.9%）。
   **凡是从表里抄一个数，抄完回头看一眼它在原表里是哪一列。**

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
- **不要同时占满四张卡。** 卡 0/1 可用时，总并发仍应 <= 2 条车道。
  2026-09-21 学到过一次（记在 `scripts/watchdog.sh` 注释里）：把四张卡全占满，
  长跑进程会被共享机器上其它租户的 reaper 杀掉。**2026-09-24 又犯了一次**：
  四条车道一起开，卡 0/1 的两条 run 在 02:36:46 / 02:37:00（相隔 14 秒，
  同一绝对时刻）双双被 SIGTERM，只跑到 679 和 624 步就终止，两条都作废。
  症状：`steps.jsonl` 里 `connection closed before message completed` 在某个时刻
  突然成簇出现，`status=FAILED`；server 日志里 `Subprocess scheduler_0 crashed
  with exit code -15`。**这个 SIGTERM 是结果不是原因，别去查谁发的。**
- **2026-09-24 追加：四条车道就算没被杀，数据也已经废了。** 审计（`scripts/lab/gen_concurrency.py`
  → `paper/data/concurrency.csv`）查明：同机同时 ≥4 条 run 且持续 ≥60 分钟，
  会把**逐请求 decode 间隔中位 τ₂ 抬高 25~40%**（30.9~33.3 ms vs 同族干净值 23.8~25.7）。
  2~3 条不抬（pairB_foyerhc 3 条跑 277 分钟，τ₂=23.8，正常）。
  **危险之处：引擎侧所有指标都看不出异常** —— `num_running_reqs`、占用率、驱逐量、
  重算量在这四条臂上与干净 run 不可区分，只有客户端实测的 τ₂ 露馅。
  四条控制器臂（bres/hz0/hz2/breshz1）因此作废并重跑（新名加 `_r2`）。
  详见 `docs/finding_concurrency_contamination_20260924.md`。
  **判据要按时长不按峰值**：`foyer_hz1` 峰值到过 4 条但只有 14 分钟，τ₂ 正常。
- **跑实验时必须挂 `gpu_watch.py`**（2026-09-24 用户提出，已接入 `run_matrix.py`）：
  池子守卫只管【启动那一刻】，跑到一半别人往同一张卡上挂进程会静默污染这一段的
  tau / SLO / 墙钟，而数据看上去完全正常。watcher 每 15 秒记一次该卡的显存、
  利用率、全部计算进程及其属主，输出到 `<run_dir>/gpu_watch.jsonl`；属主不是自己的
  标成 foreign。汇总用 `gpu_watch_summary.py <rundir>`，有它就可以写"这次测量期间
  该卡独占"。**这是低概率情况的便宜保险，不是对已有结果的质疑**：起跑时的池子守卫
  已保证池子严格对齐，且多次重复之间墙钟 CV 只有 0.9~1.8% —— 真被偷算力不会这么稳。
  所以早期 run 照常可信，不因缺这个记录而作废。
- KV pool 必须落在 `101,432 ± 20`，否则该 run 作废，不记录——SGLang 按启动时的空闲显存
  定池子，池子小了数字就不可比。

## 改文件

- **`open(path,"w")` 会在 write 之前就截断文件。** 2026-09-24 犯过：`s.replace(...)`
  后面多打一个逗号使返回值成了元组，write 抛 TypeError，但文件已经被清空
  （`sec_discussion.tex` 整篇丢失，页数从 15 掉到 12 是这个信号）。
  规矩：写完先断言 `isinstance(s, str)`，或者先写临时文件再 `os.replace`。
  征兆是**页数突然变少** —— 编译后页数掉了，先怀疑有文件被清空。
- 长文档改完后 `git diff --stat` 看一眼增删行数，与预期差太多就停下查。

## 语言

- 对用户回复一律用**中文**。代码、路径、报错原文可保留英文。
- TUI 里不要写 LaTeX 公式，用纯文本或中文名。

## git

commit message 里含反引号时**不要用 `-m`**，走 `-F 文件`——已因此静默丢词三次。
