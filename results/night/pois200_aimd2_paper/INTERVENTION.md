# 人工干预记录 — 2026-09-21 03:58

## 发生了什么

03:26:55 控制器停止写决策日志，03:30 runner 停止推进
（卡在 880/999 步、176/200 会话、active=0）。

根因：本机周期性 process-reaper 杀掉了 `controller_aimd2.py` **和它的监督 bash 循环**。
`ctrl.out` 为空说明监督循环自己也被杀了，所以那句"controller exited, relaunching"
从未打印，run_matrix 也不会察觉（它只等 runner）。

后果：permit 文件停在最后一次写入的状态，runner 有 24 个排队会话却拿不到许可，
永久等待。**aimd2 路由在 run_matrix.py 里没有监督循环**（budget3 有），这是缺陷所在。

## 恢复了什么

1. `--resume` 开关（新增，默认关）：让陈旧日志守卫采用已有 admissions.jsonl 而不是忽略它。
   守卫无法区分"上一次尝试的日志"和"本次自己的日志"，所以被杀的控制器重启后会重建
   一个空账本、把 runner 永久锁死。
2. `--resume` 时决策日志改为追加（原本是 "w"，会截断）。
3. 修掉第二层死锁：`if usage == 0.0: hold` 改为 `if usage == 0.0 and active: hold`。
   引擎空转 + 队列非空时，零读数不代表"没有信息"，恰恰是该增长窗口的时候。
4. 补上监督循环（本次运行期间生效）。

## ⚠ 溯源影响

本次运行的 `metadata.json` 记录的是**修改前**的 controller_aimd2.py 哈希。
干预后运行的是**修改后**的版本（多两处改动）。这个 run 因此不是纯粹的单版本产物：
- 03:26:55 之前：原始版本
- 03:58 之后：打补丁版本

改动只影响两处边界情形（控制器重启、engine 空转时的零读数），
不影响 03:26:55 之前已完成的 880 步的采集方式。
干预前的决策历史保留在 `controller.jsonl.pre_resume`。

## 补记 04:45 — 墙钟不可用，且此 run 的墙钟有三重污染

run_matrix 本身也被 reaper 杀掉了，因此 metadata 从未收尾：
`wall_s=None, finished=None, runner_rc=None`。`summary.json` 存在（runner 写的），
所以 lane 的完成标志有效、队列正常推进到 t85。

`compare_arms.py` 现在会降级读取 `runner.out` 的 `elapsed=22019.7s` 并**标注来源**，
不静默替换。但**这个 367 分钟不能进主表**，它同时包含：

  1. 23:16–02:24 邻居 24 核任务的 CPU 污染（同期 cap1/aimd2 步速掉 17–25%）
  2. 03:26:55–03:58 控制器停摆期间的 32 分钟空转
  3. runner 启动开销（runner.out 的 elapsed 与 run_matrix 的 wall_s 口径不同）

**质量指标（命中 60.5% / SLO 81.4% / TTFT）有效**，按步统计、不受上述影响。
若这一行要进主表，墙钟需在干净环境重跑。
