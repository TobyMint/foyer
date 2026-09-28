# codex 第 44 轮：只审【r43 之后这一批改动】

## 范围

第 43 轮之后只改了这些文件。**只看这些**，不要重审全稿。

- `paper/sec_model.tex`（1 句）
- `paper/sec_xtrace.tex`（1 句）
- `paper/sec_discussion.tex`（1 句）
- `scripts/lab/check_paper_numbers.py`（+7 项守卫，4 个新块）
- `CLAUDE.md` / `NEXT.md`（记录）

**一个数字都没有改。** 这一批只动「关于实验条件的词」。

## 一、三处措辞改动的**依据**是否成立（这是本轮的重点）

改动的起因：§III 原来写容量对照实验「A capacity-controlled version---**same card**,
same trace, one policy, only the pool size changed」，而逐条核 `metadata.json` 后发现
四条容量对照 run 里 `cap4_hp` 在**卡 3**、它的满池对照 `cap4` 在**卡 2**（另三条同卡）。
于是把这一族「并列的实验条件词」全扫了一遍，又改了两处：

| # | 文件 | 旧 | 新 | 依据 |
|---|---|---|---|---|
| 1 | `sec_model.tex` | `same card, same trace, one policy, only the pool size changed` | `the same trace and policy, with the pool halved` | 上面那张卡号表 |
| 2 | `sec_xtrace.tex` | `same trace and engine build (identical checksum)` | `same trace and the same engine version` | 仓库里**只有 trace 的 md5**（十条 A100 run 全 = `df4bdd37e5`）；引擎的出处是 `docs/a100_toolchain_20260925.md:11` 的「sglang 版本一致（0.5.10.post1）」——**没有 checksum** |
| 3 | `sec_discussion.tex` | `an earlier harness batch---same day, same trace and pool` | `over two consecutive days, the same trace and pool` | 七条 `thr25_*` 里五条 **09-14**、两条 **09-15**（`thr25_push_r2` 与 `thr25_hwsf`；而 `push_r2` 正是那句点名的 repeat） |

**请你独立复核这三条依据**（`results/night/*/metadata.json` 的 `gpu` / `trace_md5` /
`pool_tokens` / `policy`，以及 `steps.jsonl` 首末时间戳）：

1. 改动 1 的新措辞「the same trace and policy, with the pool halved」对**四条**
   容量对照 run 是否都成立？（`cap2_hp` / `cap3_hp` / `cap4_hp` / `cap3_p75`
   各自与 `gen_pool50.py` 的 `RUNS` 里那个满池对照比。）
2. 改动 2：`sec_xtrace.tex` 里那句「same trace」指的是**主 trace**（A100 跑的是
   `replay_pois200_l04.csv`，不是第二负载）—— 这个读法在**句子的上下文里**是否清楚？
   有没有更含糊或更该写明的说法？
3. 改动 3：「over two consecutive days」对**整批**七条 thr25 是否成立？
   如果正文真正引用的是其中五条（09-14 那批），这个改法会不会把范围说得**比实际更宽**？
   （这是本轮我最没把握的一处。）
4. **反过来问**：这三处改完，有没有哪一处的**新措辞**比证据强、
   或者把一句本来有的限定改没了？

## 二、新加的 7 项守卫是否真的在检查它声称的东西

在 `check_paper_numbers.py` 里搜「容量对照」「six runs at four pool sizes」
「identical checksum」「A100 与 3090 同 trace」「25 档批次」。逐条问：

- 判据的**方向**对不对（正/负面哪一边会响）？
- 是不是**自证**（锚里自带要查的那个数 / 判据和扰动共用同一个常量）？
- **集合完整性**：会不会因为名单漏一个 run 而算错却仍报 OK？
- 派生计数那条（退化步 run 数 == 6、池子种类 == 4）扫的是
  `results/{night,a100_night}/*/steps.jsonl`：**镜像不全时它会怎么表现**？
  这是「报警让人去看」还是「静默给一个像样的数」？

请**直接跑** `python3 scripts/lab/check_paper_numbers.py`（应当 737 项 0 MISS），
并**自己设计反向测试**（不要用我文档里写的那几个构造 —— 用你自己的）。
注意：扰动**数据文件前先 `cp` 备份、测完 `md5sum -c` 还原**；
`paper/*.tex` 同样。**不要用 `git checkout`**（本仓库工作区就是最新版本，会把未提交的改动退掉）。

## 三、这一族还有没有漏网的

我扫过的措辞：`same card` / `same trace` / `one policy` / `only the pool size changed` /
`same day` / `identical checksum` / `back-to-back` / `on one card` / `same configuration` /
`held everything but` / `all else equal` / `controlled for` / `single-variable`。

**请再想一遍「关于实验条件的说法」还有哪些词类我没扫到**（例如：同时/先后、
独占/共享、同一次会话、同一批、首次/重跑、预热、冷启动……），
并**实际 grep 一遍**，把「说得通但仓库里找不到出处」的句子列出来。
「说得通」恰恰是写它时的理由，不是出处。

## 四、不要做的事

- 不要重审全稿、不要提篇幅问题（那是作者已决定的）。
- 不要提已被撤回的主张（见 `CLAUDE.md` 的「撤回记录」）。
- 不要编造文献。
