# codex 第 29 轮：审【池子—未服务步梯度】这条新主张，及它的生成器与守卫

范围**限定在 2026-09-26 凌晨这一阶段的改动**，不重审全文。

## 背景：上一轮撤掉了一个错的头条数字，换成了这一条

第 28 轮你（codex）与一个独立复算子 agent **各自独立**发现：半池的兑现率
`87.1241%` 是虚报的 —— `cap2_hp` 有 **104/999 步**被引擎服务成 **1-token 退化响应**
（`server_prompt_tokens=1`、`first_token_ms=None`、**`error=None`**，runner 记成 SUCCESS），
它们的计划 prompt 整块没进实测和，被 `gen_a100.one()` 的
`reuse_tok = 计划 prompt − 实测 uncached` 算成了「复用」。
据此写进 §III/§I 的「净效应 **−4.6 pp**」已撤。

**换上来的是这条**（现在写在 `paper/sec_model.tex` 的「capacity-controlled version」段，
与 `sec_intro.tex` 两处）：

> 同一个 cap（3）、同一张卡、同一条 trace，**只改池子**：
> 1.00× 池子（101,432）**0/999** 步未被服务；
> 0.75×（76,074）**14/999**（缺口占 trace 上界 **5.3%**）；
> 0.50×（50,716）**72/807**（**24.8%**）**并且引擎崩了**。
> 对照组：全池的 cap2 / cap4 / cap3+HC 各 999 步、**0 未服务**；
> `paper/data/pool50.csv` 四条全判 INFEASIBLE、兑现率一律留空。

**请核**：

- **A1. 「no configuration we ran at the full pool has a single such step」这句站得住吗？**
  我的依据是「扫了全部 136 条 run，池子在 101432±2 的没有任何一条带 1-token 步」。
  请自己扫一遍（`results/night/*/metadata.json` 的 `pool_tokens` 与
  `steps.jsonl` 的 `server_prompt_tokens`）**验伪**：有没有漏掉的、或我扫错的地方？
- **A2. 梯度真的是池子造成的吗？** 有没有别的解释：
  引擎版本、某些会话的形态、lane/端口、memfrac 的求解路径、SGLang 对某个长度的处理？
  **关键**：0.75× 那条是 `static=3`，0.50× 的三条是 cap2/3/4 —— 同 cap 的对比只有 cap3 那一列。
  这个对比够不够支撑「池子 → 未服务步」的因果？
- **A3. 「引擎返回 1 token 但记成成功」这个机制描述准确吗？**
  证据是 `steps.jsonl` 里那些步的字段（`server_prompt_tokens=1`、`output_len_actual=1`、
  `finish_reason=None`、`first_token_ms=None`、`error=None`）。有没有更准确的描述？
  这到底是**引擎**的行为还是 **runner** 的行为？
- **A4. §III/§I 里有没有把「还没跑完」的写成已跑？** 在途的：`cap1_r2`（998/999）、
  `foyer_hz1_r3`、`cap3_pd`/`cap3_ph`、A100 的 `cap8`/`cap16`/`a100_default_r2`。

## 上一轮那几条我改完了，请核**改得对不对**

- **B1.** `gen_a100.one()` 加了硬断言（计划 prompt != 实测 prompt 就 `SystemExit`）。
  请核：**会不会误伤**？有没有哪条**合法**的 run 会被它拒掉（例如正常失败步的 run）？
  它现在还会被谁调用（`gen_a100.py` / `gen_pool50.py` / `gen_a100_delta.py`）？
- **B2.** `gen_pool50.py` 的 OK 判据从两条扩到三条。请核它**会不会假通过**：
  有没有第三种「服务不完整」的形态是这三条判据都够不到的？
- **B3.** 检查器（531 项）。这一阶段新改的守卫里有：
  **逐 run 指认关键词**（`_SPEC`，不再共用窗口）、池子四条 run 的数值、
  §A100 的准入等待与安全阀读数、`--contested` 那一行。
  请找**假通过**（值与关键词都在同一段里、但换了位置也能过）与**假 MISS**。
  上一轮你给过三个构造（对调两臂的值 / 倒写分子分母 / 对调两条 run 的数），
  我已经用它们验过；这一轮请给**新的**构造。
- **B4.** `frontier.py` 的 `TIE_PP` / `classify()` 现在与 `gen_a100_delta.py` 共用。
  `gen_pool50.py` 的 `interp()` 与 `envelope.front_slo()` 是不是**又各写了一份**？

## 硬约束

- **只报有证据的问题**，指到 `文件:行号` 或具体数字。不要为了显得严格而编造弱点。
- **不要修改任何文件**（只读）。
- 结论正负都照实说。
