# 干预记录 —— pois200_aimd2_paper_r2（2026-09-26 14:1x）

## 发生了什么

这条 run 是 `pois200_aimd2_paper` 的干净重跑（那次因墙钟三重污染被标 §）。
**它自己也停摆了**：

- 控制器进程 **1220251 在 13:15:37 退出**（现在 `ps` 显示 `<defunct>` 僵尸，
  父进程 `run_matrix.py` 1219771 从未 reap 它）；`controller.jsonl` 恰好停在
  13:15:37（之前是稳定的 30 秒一行，共 600 行）。
- `ctrl.out` **0 字节** —— 控制器退出时没打任何东西（无 traceback）。
- 最后一条 `admit` 在 13:15:37；最后一条 `release` 在 13:24:39。
- 之后 **54 分钟没有任何准入**，`steps.jsonl` 停在 **989/999**。
- `runner.out` 一直打 `sessions 198/200 | steps 989/999 completed=989 submitted=989
  active=0 failed=0` —— **没有在途请求**。
- `admissions.jsonl` 显示两个会话在 **09:41:23 / 09:41:27 `queued` 之后从未 `admit`**；
  它们正是 trace 里到达最晚的两条（arrival 4,914,286 与 4,918,066 ms）。
  引擎空转，队列里两个会话永远等不到许可。

## 根因（这次有代码证据）

`run_matrix.py` 的 **aimd2 分支没有监督循环**：它直接

    controller = subprocess.Popen([PY, ".../controller_aimd2.py", ...],
                                  stdout=open(f"{run_dir}/ctrl.out", "w"), ...)

而**前面 budget3/foyer 那个分支有**（`while [ ! -f summary.json ]; do <ctrl> ; sleep 20; done`）。
控制器一死，就没有任何东西会把它拉起来，而 `run_matrix.py` 自己阻塞在
`runner.wait(timeout=...)` 上，既不会发现也不会重启。

⚠ 这与本 run 目录里 `pois200_aimd2_paper/INTERVENTION.md` 记的是**同一件事**：
那次写着「aimd2 路由在 run_matrix.py 里没有监督循环（budget3 有），这是缺陷所在」，
并说「补上监督循环（本次运行期间生效）」—— **那个补丁只在那一次运行期间生效，
没有落到 aimd2 分支的代码里**，所以这次原样复现。

## 结论

**墙钟不可用**（含 54 分钟以上的停摆）。这条重跑**没有达成它的目的**
（目的是给 AIMD 那一行一个可用的墙钟），只有 989/999 步。

## 记一件事

`metadata.json` 里的 `controller_aimd2.py` 哈希是 **51602440d103**，
而**第一次尝试用的是 8e995d1f6633**（干预前的版本；那个文件在 2026-09-21 03:58
的干预里被改过）—— 两次**不是同一份控制器代码**，却出现了同一个失效。
⚠ 所以「不是代码版本差异造成的」这个结论**要说得更准**：两次的**启动路径**
都缺监督循环（那一段在 `run_matrix.py` 里，两次都没改过），而控制器代码本身
是有差异的。**同一个失效跨越了两个控制器版本**，指向的是启动路径，不是控制器。
（2026-09-26 更正：原句写「与上次相同」，按字面是错的。）
