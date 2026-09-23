# 发现：判据曲线在控制器臂的实际配置下没有悬崖

日期：2026-09-23
脚本：`scripts/lab/gen_elasticity_hc.py` → `paper/data/elasticity_hc.csv`
起因：codex 审稿意见 #1 —— 「分段弹性来自**无 HiCache 的五个静态 cap**，
而九条控制器臂**全部开着 HiCache**；论文自己承认 HiCache 下相近运行数可对应
明显不同的步成本。」

## 两条曲线（同一个 tau 口径：busy 条件均值，见 gen_arm_running.py）

```
device-only（论文 §IV 现在唯一用的那条）
  cap1         Rbar 1.00  tau 28.8
  cap2         Rbar 1.27  tau 27.4     eps = -0.208
  cap3_fixed   Rbar 1.53  tau 29.7     eps = +0.433
  cap4         Rbar 1.65  tau 32.4     eps = +1.152   <-- 悬崖
  cap5         Rbar 1.84  tau 36.7     eps = +1.143   <-- 悬崖

HiCache（九条控制器臂实际运行的配置）
  pairB_cap2hc Rbar 1.25  tau 27.0
  cap3_hc      Rbar 1.51  tau 28.0     eps = +0.192
  cap4_hc      Rbar 1.73  tau 29.8     eps = +0.458
```

**HiCache 曲线在控制器的整个运行区间（Rbar 1.25–1.73）内 eps 从未达到 1。**
device-only 曲线有 2/4 段 eps>=1，HiCache 曲线 0/2 段。

run 身份已核实：`pois200_pairB_cap2hc` / `pois200_cap3_hc` / `pois200_cap4_hc`，
policy 分别为 static=2/3/4，pool 全部 101432（可比）。控制器车道脚本
（`lane_var_foyer_g2.sh` 等）均设 `TURNSTILE_HICACHE_ARGS`，即控制器确实开 HiCache。

## 后果一：§IV 现在的解释对控制器不成立

论文现写：「Five sit at 1.63 or above, in the eps ≈ 1.15 segment where it
does not pay at all.」—— 这句话把 device-only 的曲线套到 HiCache 的臂上。
按控制器自己的配置，它们所在的段 eps 只有 0.19–0.46，**加并发仍然划算**。

物理上也讲得通：device-only 的悬崖来自**重算**（§III 已测：五条 device-only run
的 device miss 恰好等于重算 token，host 吸收为 0），而 HiCache 把驱逐的 KV 落到
host 再读回，替代了重算，悬崖因此消失。τ 在同 Rbar 下的对比也支持：
Rbar≈1.7 处 device tau=32.4–36.7，HiCache tau=29.8。

## 后果二：19 分钟的那个反例，其实是 idle 不是步成本

论文 sec_results.tex:156 用「hz1 与 cap3_hc 占用相同、Rbar 几乎相同，cap 却快 19 分钟」
论证「低占用不能解释结果」，并把差额归给步成本。拆开 decom：

```
              Rbar_busy  idle_min  busy_min   wall_min
cap3_hc         1.51       24.1      218.4     236.4
foyer_hz1       1.52       36.7      225.2     255.8
差                          +12.6      +6.8     +19.4
```

**65% 的差额（12.6/19.4）是 idle 时间**，不是步成本。两者步成本只差
1.2 ms（29.2 vs 28.0，约 4%）。idle 变多与「控制器攥着 permit 不放」一致：
会话一轮结束去 tool_wait 时，控制器不放进新的，引擎就空转。

## 这对论文意味着什么

现在稿子里有两条互相竞争的解释：
  (a) 步成本悬崖（eps>=1）让加并发不划算
  (b) 控制器高估占用 1.79 倍、只用到 49.2% 池子，不敢放

新数据说 **(a) 在控制器实际配置下不存在**，所以 (b) 才是主因。
这实际上是个**更好**的故事：判据的作用从「解释失败」变成「**排除掉工作负载侧的
解释**，从而把失败定位在控制器自己身上」——这正是一个诊断工具该干的事，
而且它不再需要跨配置外推。

代价：摘要里「that is a property of the workload rather than of the controller」
一句需要重写，§IV 的「operating region」一节需要重写。

## 尚未确定 / 需要补的

- HiCache 曲线只到 Rbar 1.73（没有 cap5_hc），**看不见更高处有没有悬崖**。
  控制器区间（1.35–1.71）落在已测范围内，结论对该区间成立；对更高 Rbar 未知。
- 每条 HiCache 静态 cap 只有一条 run（cap3_hc/cap4_hc 各有一条重复在跑/已有），
  段弹性没有误差棒。
- 控制器是否真的因 idle 而慢，需要在**全部**臂上验证 idle_pct 与 wall 的关系，
  不能只看 hz1/cap3_hc 这一对。

---

# 追加发现（同日）：变负载 trace 上控制器投影饱和

在 `pois200_var_foyer`（控制器主臂 `budget3:hw=0;target=0.95`，跑变负载 trace
`replay_varload_lo2hi.csv`）上观测到准入停滞。核实过程：

```
waiting_n   = 22 ~ 23     有会话在等
resident    = 0           引擎占用的 token 数（设备侧）
usage       = 0.0
valve       = False        SLO 阀门【没有】关
gate_full   = False        round gate 没开（默认 round_gate=0）
candidate   = None
n_admitted  = 0
```

引擎侧同时是空的：metrics.csv 里 `num_running_reqs=0`、`num_used_tokens=0`、
`num_queue_reqs=0`，`generation_tokens_total` 冻结在 136501。

## 根因

`controller_budget3.py:321-326`：

```
ctx_sum    = 72100     # 【在跑的 2 个会话】的上下文之和，各约 36000 token
growth_sum = 26737
base       = max(resident, ctx_sum) = 72100
projection = base + growth_sum = 98837
budget     = 96360
```

判定是 `if projection + n <= budget`（:406）。**projection 本身已经超过 budget，
所以对任何候选者都不成立**，`candidates` 恒为空 → 一个都不放行。

`ctx_sum` 中位 47164、最大 123312；`base` 最大 103469，均可达/超过 budget 96360。

唯一在推进的是 starve guard（:413-419），它 bypass 预算直接强推 `waiting[0]`，
但有 `--starve-cooldown`（默认 300 秒）限速。实测 admit 间隔中位 87 秒，
最后几次 199 / 278 / 343 / 302 秒 —— 就是 cooldown 的节拍。70 分钟里放了 35 个。

## 为什么这不是 bug，而是论文机制的极端形态

投影把**停在 tool_wait 里的会话按完整上下文计费**，而它们的 KV 是可驱逐的、
并不在引擎的 resident 计数里。这正是 §V「控制器认为快满了，其实空着一半」
（投影 1.79 倍于真值）描述的同一个量，只是在这条 trace 上被推到了极端：
**只要有两个大上下文会话同时停在 tool wait，控制器就完全停止接纳，而引擎空转。**

论文 §V 的 Route 1 已经测过：把这个 double charge 去掉（`base=resident`）反而
更差（慢 4.2 分钟、SLO −6.0pp）。所以控制器是按设计行事。

## 对变负载实验的影响（待定，取决于最终能否跑完）

- 按当前速率，200 个会话约需 6.7 小时，可能落在 12h 超时内。
- 若跑完：这是一个**可用但极端**的数据点 —— 控制器在变负载下不是"输一点"，
  而是退化成每 5 分钟放一个。
- 若跑不完：按项目规矩记为部分 run，不与 999 步的臂同表比较。
- **需要在论文里如实报告这个机制**，否则审稿人会把它当成隐藏的 bug。

---

# 追加发现（09-24 凌晨）：变负载切换基线第一次跑无效，根因是仪表坏了

## 现象

`pois200_var_switch` 跑完（999 步、250.9 分钟、rc=0），但 `switcher.jsonl` 只有
**1 条**记录（t=0，cap=3），而 `--interval 2` 下 250 分钟本该写约 7500 条。

## 排除

`cap_switcher.py` 的日志是**条件写入**的：

```python
if nxt != cap or wrote is None:   # 只在 cap 变化时记
```

所以「只有 1 条」不等于「死了」，而是**一直在跑但从未切换**。

## 根因

```python
EVENTS = ("queued",)     # 只数 queued 事件当到达
```

但 `static=N` 模式下 runner 立即放行、没有东西压着会话，
`admissions.jsonl` 里 **400 条全是 admit 和 release，一个 queued 都没有**。
于是 `n_recent` 恒为 0、`rate` 恒为 0、`hi_streak` 永远到不了 2，**全程一次没切**。

**所以第一次的 `pois200_var_switch` 实际等价于一条静态 cap3 run**（cap 文件被写成
3 后再没动过），仍可当 cap3 的数据点用，不必浪费。

## 修法（改仪表，不改判据）

第一次尝试改成数 `admit` 事件 —— **错了**，离线模拟显示它在 82 分钟就切、89 分钟
又切回来，之后再不切。原因是 `admit` 衡量的是**放行速率**，被 cap=3 限住了，那是
容量节流不是到达。

最终改法：用 `admit` 事件的 `waited_ms` **反推真实到达时刻**
（`arrival = ts - waited_ms/1000`）。这是可部署的量（一个会话等了多久），
不是偷看 trace。验证：

```
反推到达的速率： 0-125 分 0.009~0.019/s  ← 低载相
              125-175 分 0.030~0.037/s  ← 高载相
切点 125 分，与 trace 设计的 124.5 分吻合。
```

离线重放（拿第一次 run 的 admissions.jsonl 走修好的逻辑）：**t=128.0 分切到 cap2**，
滞后 3.5 分钟；之后保持 cap2。

**切换规则本身（hi 0.025 / lo 0.020 / 窗 600s / 连续两个采样）一个字未改。**

## 顺带纠正一处我对规则的误读

`hi_streak >= 2` 数的是**连续两个 2 秒采样**（4 秒去抖），不是「两个 10 分钟窗」；
600 秒窗只提供平滑。所以 codex 担心的「要 20 分钟才降档」，实测滞后 3.5 分钟。

## 另一个观察：cap 在变负载 trace 上并不顶满引擎

`pois200_var_switch`（cap=3）全程 `sglang:num_running_reqs` 中位 1~2、
`sglang:num_queue_reqs` 中位 0（最大 2）—— **cap 从未被在跑数顶满**。
cap 限的是**活跃会话数**（含停在 tool_wait 的），不是在跑数，
所以引擎空着而会话在排队（积压最高 67 个）。这与子 agent 在 realhr 上的发现一致。
