# 半池把 KV 池占满 → SGLang scheduler 抛 OOM → 引擎死掉（cap=3 与 cap=4 各一次）

**状态：半池上【两次独立发生】，且有强对照（全池 ~165 条 run 从未 OOM）。
这是【可行性边界】的观测，不是兑现率读数。**
文件名只写了 cap4（它是最先被发现的），但**本文档同时覆盖 `cap3_hp`** —— 见第〇节。

---

## 〇、2026-09-25 21:4x 追加：`cap3_hp` 也崩了，签名逐字相同

`cap3_hp`（半池 50,716、`static=3`）在**步 757**处死掉：

    RuntimeError: Out of memory. Try to lower your batch size.
    Try to allocate 2048 tokens.
    Available tokens: 1563 (available_size=1563 + evictable_size=0)
    [2026-09-25 20:19:07] SIGQUIT received.

结果 `attempted=807 / 999`，`failed=50`，`runner_rc=0`（**与 cap4_hp 同款的误导性
退出码**）。失败在 5 秒内从 0 跳到 47（`stop_session_on_error` 连锁）。

### ⚠ 这张表原本是错的（2026-09-26 独立复算抓到，已订正）

原文写「`cap2_hp` 的超池请求在步 123 / 673 / 688，**三条全部服务成功**」。
**逐条查 `steps.jsonl` 后两条都不对**：那三步的实际 index 是 **591 / 833 / 843**，
而且它们的 `server_prompt_tokens` **全是 1**、`output_len_actual=1`、`error=None`
—— 是**退化响应**，不是「被服务成功」。

    index=591  input_len=51912  prompt_len=51912  server_prompt_tokens=1  out_actual=1  error=None
    index=833  input_len=63403  prompt_len=63403  server_prompt_tokens=1  out_actual=1  error=None
    index=843  input_len=66571  prompt_len=66571  server_prompt_tokens=1  out_actual=1  error=None

**正确的机制（已做成机械判据）**：**prompt 超过池子的步，一步都不会被执行。**
`cap2_hp` 里 `prompt_len > 50716` 的步共 **104 条，全部** `server_prompt_tokens==1`。
门槛紧到 **4 个 token**（超池的最小 prompt 50,720 对池子 50,716；
被正常服务过的最大 prompt 50,688）。同一判据在 `cap3_p75` 上同样成立
（76,085 被丢、75,445 被服务，池子 76,074），**6 条 run 0 假阳假阴**。

**崩溃是另一回事**：`evictable_size=0`（池子被活请求占满、新的 prefill chunk
无处可放）解释的是 `cap3_hp` 步 757 与 `cap4_hp` 的 OOM **崩溃**，
不是退化响应 —— 两者**可分离**：`cap3_hp` 的退化步从**步 96** 就出现（比崩溃早 661 步），
而 `cap3_p75` **999 步、0 报错、0 崩溃，仍有 14 个退化步**。

### 对照：全池从未 OOM

`results/night/` 全部 `server_*.log` 里带 `Out of memory` 的**只有两个**，
且**都是半池**（`server_30072_pois200_cap3_hp.log`、`server_30073_pois200_cap4_hp.log`）。
全池 101,432 上跑过 concurrency **94.91**（`default`）与 **7.63**（`cap8_hc`，
999/999、0 失败）**都没有 OOM**。所以：**是池子，不是并发。**

### 半池三条的结局

| run | cap | 结局 |
|---|---|---|
| `cap2_hp` | 2 | 999/999、0 失败，**但 104 步的 prompt 超过池子、从未被执行** ✗ |
| `cap3_hp` | 3 | 807/999，50 失败 ✗ OOM |
| `cap4_hp` | 4 | 549/999，116 失败 ✗ OOM |

**推论：在这个 trace 上，半池三个 cap 都拿不到兑现率** —— cap2 有 104 步未被
真正服务，cap3/cap4 直接崩。这是**可行性**证据，不是性能证据，两者不能混着写。

---

## 一、cap4_hp 的原始记录（2026-09-25 晚发现）

发现于做 codex r27 处置时顺手核半池实验的三条 run ——
`cap4_hp` 早就躺在目录里，而我此前只当它是「没跑完的 run」。

---

## 一、事实（可追溯到日志）

`results/night/pois200_cap4_hp/`，lane `pool50_g3`，GPU3，port 30073，
起 13:11:15、止 15:17:59（`/tmp/wait_gpu3_lane_pool50_g3.log` + lane `.out`）。

`server_30073_pois200_cap4_hp.log` 末尾：

    RuntimeError: Out of memory. Try to allocate 2048 tokens.
    Available tokens: 1444 (available_size=1444 + evictable_size=0)
    [2026-09-25 15:17:53] SIGQUIT received. signum=None, frame=None.
                          It usually means one child failed.

调用栈落在 `scheduler.py: get_new_batch_prefill -> prepare_for_extend ->
alloc_for_extend -> alloc_token_slots`。

**`evictable_size=0` 是关键**：池子里每一个 token 都被**活请求**占着，没有可驱逐的。
这不是碎片，是池子被占满。

后果链（每一步都有记录）：

| 时刻 | 事件 | 证据 |
|---|---|---|
| 15:17:53 | scheduler 抛 OOM，引擎死 | 上面的 server 日志 |
| 15:17:57–59 | 116 个在途步骤失败 | `runner.out` 的 `failed` 从 1 跳到 115；`steps.jsonl` 里 111×`Connection refused`（port 30073）+ 4×`connection closed` + 1×`unexpected EOF` |
| 同时 | 全部会话结束 | `stop_session_on_error` 默认 **true**（`cli.rs:56` 附近）—— 一次失败即终止整条会话 |
| 15:17:59 | runner 退出，**rc=0** | lane 日志 `run pois200_cap4_hp done rc=0`；`metadata.json` `runner_rc=0` |

**runner 的 rc=0 是误导性的**：它只是「所有会话都到了终态」，不代表跑满。
`summary.json`：`attempted_steps=549`（计划 999）、`success_steps=433`、`failed_steps=116`。

## 二、为什么这不是污染、不是被杀

逐条排除（都做过）：

- **不是同机争用**：`gpu_watch.jsonl` 483 个采样（13:15:57→15:17:43）里
  `n_foreign` **全为 0**，`mem_used` 稳在 19,887 MiB。全程只有我们自己的 server。
- **不是被别的车道抢卡**：同一时刻只有 `pool50_g2`（GPU2）和 `pool50_g3`（GPU3）
  两条车道。`cap1_r2` 的等待器 15:18:00 才拿到锁，而它看到的是 `mem=15MiB`
  —— 那时 server 已经死了。
- **不是池子配错**：lane 日志 `server healthy, pool=50716 (attempt 3)`，
  memfrac 求解器试了 3 次才对上 `TURNSTILE_EXPECT_POOL=50716`。
- **不是超时**：`TURNSTILE_RUN_TIMEOUT_H=14`（50400 s），实际只跑了 7318.8 s。

所以：**池子是我们【故意】减半的，这个崩溃是那个变量造成的。**

## 三、退出机制：为什么 runner 会「正常退出」

两处引擎默认值合起来解释了 549/999：

1. `cli.rs` 的 `stop_session_on_error` 默认 **true** —— 一失败就整条会话结束；
2. `session.rs` 的 `status_task` 在 `finished_sessions >= total_sessions` 时 break，
   主流程等所有会话任务到终态才退出。

于是 116 次失败 → 116 条会话连锁终止 → 200 条全会话到终态 → runner 退 rc=0。
**「跑完」和「所有会话都死了」在 rc 上是同一个值**，这正是本项目
「『还没到』和『坏了』长得一样」那条的又一个变体。

## 四、一个必须一起说的混淆

半池 **50,716** 而 trace 的 `max_input_len` 是 **66,571** ——
**池子比最长的单个请求还小**。实测（`cap2_hp/steps.jsonl`，999 步）：

    输入长度超过 50,716 的步骤：3 / 999 = 0.30%（全池 101,432 下为 0.00%）
    分位：p50=3,288  p90=18,615  p99=41,476  max=66,571

所以半池实验**不是纯粹的「复用空间变小」**：另有 3 步单靠长度就不可行。
（**完整 `prompt_len` 超池的是 104 步**，比这 3 步多得多 —— 见第〇节的补充。
两处口径不同：`input_len` 是这一次要处理的量，`prompt_len` 含要复用的前缀。）
这个混淆**写进论文时必须说**，否则「半池 → 兑现率下降」会被读成纯复用效应。

## 五、处置决定（三条，都写明理由）

1. **不重跑。** 半池配 cap=4 是结构性耗尽（`evictable_size=0` 不是偶发），
   重跑只会再崩一次、再吃掉 ~2 小时一条车道，而且**崩掉的 run 给不出兑现率**
   （433 个成功步骤是被截断的有偏样本：活下来的都是短会话）。
2. **不改目录名。** 名字是它在 `concurrency.csv`（争用审计按目录计数）与
   `repeat_spread.csv` 里的身份；改名会动到车道审计。留原名、留证据。
3. **不写进论文的数据表。** 它不进 `reuse.csv` / `a100.csv` / 任何前沿计算。
   可以写的只有下面那句，且要按这个强度写。

## 六、允许写进论文的说法（如果写）

按现有证据，能支撑的最强说法是：

> 半池上 `static=2` 的 runner 记到 999/999 步、0 失败（**但其中 104 步的 prompt
> 从未被处理**）；`static=4` 则把 50,716 个 token 的池子
> 占满（`evictable_size=0`），SGLang 的 scheduler 在 `alloc_for_extend` 抛
> `Out of memory`，引擎退出，余下 450 步未跑。

即：**这是「容量是绑定资源」的一个极端读数（从 60.7% 兑现率到跑不起来），
不是兑现率曲线上的第三个点。** 一条 run、无重复，说的时候要一起说。

预注册判据（`lane_pool50.sh` 头注释）点名的只有 cap2 与 cap3，**不含 cap4**，
所以这条不影响判据的判决。

## 七、给下一个人的提醒

`run_matrix.py:447`：

    if os.path.exists(f"{run_dir}/summary.json"):
        log(f"run {name} already has a summary — skipping")

`cap4_hp` **有** `summary.json`，所以直接重挂 `lane_pool50_g3.sh` 会**静默跳过**
（lane 会正常结束、什么都不跑）。要真重跑必须先 `mv` 走这个目录 ——
这正是 CLAUDE.md「开跑前必须挪走同名旧目录」那条，只是这里的症状从
「静默混跑」变成了「静默不跑」。
