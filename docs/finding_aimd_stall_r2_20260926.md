# AIMD 那条臂的第二次停摆 —— 以及 §V 里一句**错了两半**的因果（2026-09-26 14:2x）

## 一、发生了什么

`pois200_aimd2_paper_r2`（为修 AIMD 那一行的墙钟而排的干净重跑）**自己也停摆了**：

| 事实 | 证据 |
|---|---|
| 控制器进程在 **13:15:37 退出**，再没回来 | `controller.jsonl` 停在 13:15:37（此前稳定 30 秒一行，共 600 行）；`ps` 里那个 PID 是 `<defunct>` 僵尸，父进程 `run_matrix.py` 从未 reap |
| 退出时**没有任何输出** | `ctrl.out` **0 字节**（无 traceback） |
| 之后 **56 分钟**无人准入 | 最后一条 `admit` 13:15:37；最后一条 `release` 13:24:39 |
| 停在 **989/999** 步 | `steps.jsonl` 行数 |
| **两个会话一直排队** | `admissions.jsonl`：两条在 09:41:23 / 09:41:27 `queued` 之后**从未 `admit`**——正是 trace 里到达最晚的两条 |
| 引擎空转、无在途请求 | `runner.out` 一直打 `active=0` |

我把它按 PID 停掉了（GPU2 随后被邻居 `cjy` 占满，四个卡都在用）。

## 二、根因：**启动路径缺监督循环**（这是这次真正查出来的）

`run_matrix.py` 里：

- **budget3 / foyer 分支**：控制器包在一个 `while [ ! -f summary.json ]; do <ctrl>; sleep 20; done`
  的监督循环里，控制器死了会被拉起来；
- **aimd2 分支**：直接 `subprocess.Popen([...controller_aimd2.py...])` —— **没有循环**。
  控制器一死，没有任何东西会重启它，而 `run_matrix.py` 自己阻塞在 `runner.wait()` 上，
  既发现不了也不会重启。

⚠ 这与第一次尝试的 `INTERVENTION.md` 记的是**同一件事**：

> 「**aimd2 路由在 run_matrix.py 里没有监督循环**（budget3 有），这是缺陷所在。」
> …「补上监督循环（**本次运行期间生效**）」

**那个补丁只在那一次运行期间生效，没有落进 aimd2 分支的代码里** —— 所以这次原样复现。

## 三、**§V 里那句因果错了两半**

原文（`sec_results.tex`，AIMD 那段）：

> 「The cause is recorded rather than inferred: the host's process reaper had killed
> the controller **and the supervisor loop that would have restarted it**, so the
> permit file froze with 24 sessions queued.」

- **「the supervisor loop that would have restarted it」不存在** —— 代码里那条路由
  从来没有监督循环（第一次的 INTERVENTION 自己写的就是「没有监督循环，这是缺陷所在」）。
  这一半是把**缺失的机制**写成了**被杀的机制**。
- 前半（reaper 杀了控制器）**在记录里**，保留。

已改成：`…had killed the controller, and the launch path that runs this controller has
no supervisor loop---unlike the one our own controller runs under---so nothing
restarted it…`，并**记录重跑复现了同一件事**（控制器退出、两个会话排队、停在 989/999）。

## 四、修了什么、又排了什么

1. 给 `run_matrix.py` 的 **aimd2 分支补上同一个监督循环**；第二次起重启用
   `--resume`（让控制器**采纳**已有的 `admissions.jsonl` 而不是重建空账本 ——
   重建会把已在排队的会话永久锁死；决策日志同时从 "w" 改成追加）。
   `run_matrix.py` 的 md5：`b866b92c6eed…` → `82fecb13ed34…`
   ⚠ **这是启动路径的改动，不是控制器行为的改动**：`controller_aimd2.py` 哈希未变。
   新 run 的 metadata 会记下新哈希，改动可核。
2. 起 `pois200_aimd2_paper_r3`。第一次开火时 **GPU2 已被邻居 `cjy` 占**（池子给到 91,188，
   应为 101,432），按「别人占着卡就等」停掉，改成**等窗口**再开火。
   ⚠ 等待器的阈值第一版写 `< 1000 MiB`，而 3090 的池子守卫是 **±20 token** ——
   邻居占 650 MiB 就足以让池子短 10%。**已收到 <50 MiB**（判据必须与要等的资源同粒度）。

## 五、证据落盘

新增 `paper/data/aimd_stall.csv`（生成器 `scripts/lab/gen_aimd_stall.py`），
两次停摆的可核事实：控制周期数、控制器末条时间、最后一次活动、步数、
排队未准入的会话数。

⚠ **「停摆了多少分钟」故意不印**：那取决于我什么时候手动停掉它，是**写稿时刻的函数**，
不是 run 的属性。这与「句子里锚了写稿当时的词会随时间变假」是同一条。

## 六、状态

**29 页**、0 Float/Overfull、0 悬空引用、**634 项检查 0 MISS**。
