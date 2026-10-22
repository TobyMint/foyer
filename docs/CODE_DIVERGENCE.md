# 代码不一致清单（2026-09-22 17:45）

**仓库里的代码 ≠ 实际跑过的代码。** 这是个可复现性问题，记在这里。

发现方式：推送前验证 raw URL 能不能读到新内容，顺手比对 md5，才发现。

## 三处不一致

| 文件 | 仓库 | 实验机（实际跑的） | 差异 |
|---|---|---|---|
| `scripts/controller_budget3.py` | ~~`2b573829083c`~~ → 已同步 | `e1dd5ae78019` | 23 行 |
| `scripts/controller_foyer.py` | `f101f5b5bc8c` | `43462c276ec4` | 108 行 |
| `run_matrix.py` | 仓库有一份 | 实验机版 | 111 行 |

### `controller_budget3.py` —— 已处理（仓库 → 实验机版）

差的是 2026-09-22 加的 `--charge-mode`。**已在发现当天同步**，
现在仓库里是实际跑过的版本。

**根因**：我在实验机上直接改，只把副本放在 `scripts/lab/`，
忘了同步 `scripts/`。**规矩：改实验机上的代码后，立刻同步仓库的对应文件。**

### `controller_foyer.py` —— **未处理，需要人判断**

**仓库版比实验机版多 108 行**，其中包含一个 `replay_admissions()` 函数——
2026-09-21 查那 29 分钟停摆时写的诊断：
"重新从头应用整个 admissions 日志，把结果与控制器内存里的状态做对比"。

**它从没部署过。** 而实验机版（跑出 `foyfix_hc` 的那一版）没有它。

**不覆盖的理由**：覆盖会丢掉这份别处没有的工作；而它到底该不该合进实验机版，
需要先读懂那 29 分钟停摆的结论（§二十九 撤回了看门狗解释，机制至今未知）。
**留给人判断。**

### `run_matrix.py` —— **未处理**

仓库里那份与实验机差 111 行。实验机版里有我 2026-09-22 加的
`"charge": "--charge-mode"` 映射，仓库版没有。

**这个文件的身份要理清**：它到底是"仓库里维护的源"还是"实验机上的部署物"？
现在两处都有、都在改，**这是 bug 的来源**。

## 为什么这件事值得单独记

`metadata.json` 里有 `code.run_matrix.py` / `code.session_runner` 的哈希，
**我们一直用它们判断"两条 run 是不是同一代 harness"**。
如果仓库里的代码和跑过的不一致，**哈希比对就失去意义**——
你无法从仓库重建出当时到底跑了什么。

**投稿前必须让这两者一致，否则"可复现"这句话是空的。**

---

# 2026-10-12 结清 —— 三处全部处置，其中一处是**有意保留的例外**

**这份清单在 `docs/` 里躺了 20 天。** 分歧一直在，代价是实的：
2026-10-12 分析 data31 头条时，读的是 `scripts/controller_budget3.py`
（09-23 14:46 修好的版本），而 run 用的是 `TraceLab/replay/scripts/` 那份
（09-23 01:13 的旧版）—— 白查一小时，把 bug 分析反了两次。
（`run_matrix.py` 早就在 `metadata.json` 里记 `path_divergence` 字段，**没人看**。）

## 处置

```
controller_budget3.py   实验机 TraceLab 副本  →  符号链接到 scripts/
                        （09-23 那两行修复此前只在 scripts/ 那份里，已生效）
run_matrix.py           两边取新的：实验机 09-26 版（有 budget3scan 路由 + 割线法
                        memfrac 求解）→ 覆盖 scripts/，再符号链接
controller_foyer.py     ⚠ 【例外】实验机保留 as-run 版 43462c276ec4
```

## 为什么 `controller_foyer.py` 不能统一

上面「未处理」那一节写的理由**今天核实后成立，而且比当时写的更严重**：

> `replay_admissions()` **不是死代码** —— 它在主循环第 **570 行**被调用：
> `fresh = replay_admissions(args.admission_log)`。

所以把它推过去**不是"多一个没人用的函数"，是改变 `foyer` 路由执行什么**。
而 `foyfix_hc` 等已发表结果跑的是 43462c27。**统一 = 破坏复现。**

⇒ 处置是**显式保留这一处分歧**，并把它写进两处守卫：
- `lab:/data/xbw/turnstile/CURRENT.md`（第一节，逐条写明）
- `scripts/deploy.sh --check`（判据：`controller_foyer.py` **必须不是**符号链接，
  且 md5 必须是 43462c276ec4）

同时 `scripts/controller_foyer.py`（仓库版 f101f5b5）**保留**，因为那份
`replay_admissions()` 是别处没有的工作。

## 未决

`run_matrix.py` 那份文档问的「它到底是仓库里维护的源还是实验机的部署物」——
**2026-10-12 定案：仓库是源，实验机是部署目标，单向 `deploy.sh`。**
（这一条现在写在 `CLAUDE.md` 顶部与 `CURRENT.md` 里。）
