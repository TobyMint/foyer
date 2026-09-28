# C9 重算与更正（2026-09-27）

**触发方式**：为跑驱逐政策对照（`slru`）去读 `claims_audit.md` 的 C9，发现它的
「数字」行给的是 88.8--89.8%、计划值 89.8% —— 而这两个数**在 `hitrate.csv` 里找不到**。
往下追，是三个独立的错，外加一个对照设计问题。

---

## 一、那三个数是**同几条 run 的 SLO**

| C9 印的 | 它其实是什么 |
|---|---|
| 88.8% | `pois200_foyer_scan_r2` 的 **SLO** = 88.888889（`runs_precise.csv`） |
| 89.8% | `pois200_foyer_hc` 的 **SLO** = 89.8（`runs.csv`） |
| 89.8% | `pois200_foyer_t85` 的 **SLO** = 89.889890（`runs_precise.csv`） |

「命中率」与「SLO」在这批 run 上**恰好都在 78--90 这个区间**，所以抄错列不会显得突兀。
这正是 `CLAUDE.md` 那条「从错的列抄数」的第 N 次 —— 前四次是人抄汇总表，
这次是**往主张登记册里抄**。

## 二、trace 上没有 89.8 这个计划值

`planned_prefix_hit_rate` 是 `steps.jsonl` 的**逐步字段**，`gen_hitrate.py` 取
`round_idx >= 1` 的逐步非加权均值。主 trace（`replay_pois200_l04.csv`）上是 **80.87%**。

扫全机 **166 条有 `steps.jsonl` 的 run**，round-1+ 计划值的分布：

```
89.7%  1 条  pois200_cap4_fixed        ← 唯一落在 88--90 的
89.1%  1 条  realhr_cap1
87.4%  9 条  realhr_cap2/3/4/4_r2 ...
81.0% 42 条  load25_* ...
80.9% 73 条  _stale_*, aimd2_*, budget200c_* ...
```

**没有任何一批的计划值是 89.8。** C9 点名的四条全是主 trace，计划值 80.87。

## 三、「差 ≤1pp」不成立

| run | 政策 | HiCache | round-1+ 步数 | 实测 | 计划 | 差 |
|---|---|---|---|---|---|---|
| `pois200_foyer_hc` | `budget3:hw=0;target=0.95` | 开 | 800 | 80.6% | 80.87% | −0.2 |
| `pois200_cap3_hc` | `static=3` | 开 | 800 | 79.6% | 80.87% | −1.3 |
| `pois200_foyer_t85` | `budget3:hw=0;target=0.85` | **关** | 800 | 78.0% | 80.87% | **−2.9** |
| `pois200_cap2_hc` | `static=2` | 开 | **763** | 80.8% | 81.05% | −0.2 |

**复算命令**（在实验机上跑，只读）：

```python
import json, statistics, os
root = "/data/xbw/turnstile/results/night"
for r in ["pois200_foyer_hc", "pois200_cap3_hc", "pois200_foyer_t85", "pois200_cap2_hc"]:
    st = [json.loads(l) for l in open(os.path.join(root, r, "steps.jsonl")) if l.strip()]
    r1 = [s for s in st if s.get("round_idx", 0) >= 1]
    obs = statistics.mean((s.get("server_prefix_hit_rate") or 0) for s in r1) * 100
    plan = statistics.mean((s.get("planned_prefix_hit_rate") or 0) for s in r1) * 100
    print(r, len(r1), "%.1f %.2f %+.1f" % (obs, plan, obs - plan))
```

**方向仍然成立**（准入政策推不动命中率：全部落在计划值下方 0.2--2.9pp），
但幅度必须按上表印。

## 四、对照集合本身也不是单轴的（这一条比数字更要紧）

- **`pois200_foyer_t85` 的 `hicache_enabled = False`** —— 它是 **device-only** 那一侧的臂，
  而其余三条都开着 HiCache。C9 把它与三条 host-tier 臂并列成「四个不同政策」，
  读者会以为四者同 tier。**混了 tier 的对比不能支撑「政策不是变量」** ——
  它同时动了 tier 这根轴。
- **`pois200_cap2_hc` 只有 763/999 步、且没有 `summary.json`** —— 是一条部分运行。
  按本项目的判据（`summary.json` 是「跑完」的唯一判据），它不该与跑完的 run 并列。
  这也解释了它为什么不在 `hitrate.csv` 里：那份表的名单是
  `default + gen_arm_running.ARMS + STATIC`，而这两条 run **两者都不在名单里**。

⇒ 引用 C9 时**要么只取前两条**（同为 host tier、同为满 999 步），
**要么把这两个限定写明**。已按这个写法更新 `claims_audit.md` 的 C9。

## 五、顺带量出来的：`hitrate.csv` 与它的规范名单有漂移

`gen_hitrate.py` 的 run 列表是 `sys.argv[3:]`（命令行传，脚本内无默认值）——
`CLAUDE.md` 记过这个模式**没有守卫**。把 `paper/data/hitrate.csv` 的实际行集合
与规范名单（`default + ARMS + STATIC` = **38** 条）对拍：

```
应有 38 条 / 实有 37 条
少了: pois200_pairA_foyerhc, pois200_pairB_foyerhc
多了: pois200_aimd2_paper          ← 已被 aimd2_paper_r3 替代的那条
```

**影响：无当前引用受影响。** 两条被漏掉的实测都是 **80.6%**（与 `foyer_hc` 相同，
正文印的 80.6 不会因此变化）；多出来的那条是**已被替代**的 run，
按本项目「生成器要有已作废名单」的规矩不该在表里。

⚠ 值得记的是**守卫的形状**：`check_paper_numbers.py` 是**按 CSV 的行**逐条查正文的
（10 条标 P、其余标 S）。也就是说 **CSV 少一行 = 守卫少查一行**，
而「少查」不会报任何东西 —— 与「退役名单会静默吞掉检查」是同一族：
**守卫的覆盖面由被检查的数据决定。**

## 六、这一条**没有影响论文**

正文里 `hit rate` 只出现在两处（`sec_results.tex:359`、`sec_model.tex:213`），
用的都是 `hitrate.csv` 的 **80.x** 口径，与本次复算逐位相符：

- `sec_model.tex:213`「falls from 80.8% to 32.8% across the device-only caps and holds at
  80.7% to 78.7% across the three host-tier caps」——
  `cap1` 80.8 / `cap5` 32.8 / `cap2+HC` 80.7 / `cap4+HC` 78.7 ✓ **逐条对得上**。
- `sec_results.tex:359`「falls only from 80.6% to 79.7%」—— `foyer_hc` 80.6 ✓。

**错的只有主张登记册（`claims_audit.md`）与历史日志（`claim_register_20260921.md`），
不是论文。**
