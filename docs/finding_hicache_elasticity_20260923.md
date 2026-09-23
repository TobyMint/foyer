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
