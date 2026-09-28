# 「One switch, two regimes」不是同一个开关 —— 2026-09-26

**一句话**：论文用「**同一个**节流开关在轻载与重载下符号相反（+51% / −42%）」来论证
「本工作负载正是自适应控制该赢的那种情形，而它没赢」。核下来**两档的「off」臂
不是同一个开关，甚至不是同一个控制器**，而 25 档那一对还**动了两根旋钮**。

## 事实（全部来自 `metadata.json` 的 `policy` 字段）

| 档 | 「on」臂 | 「off」臂 | 差在哪 |
|---|---|---|---|
| 200 | `pois200_foyer_hc`：`budget3:hw=0;target=0.95` | `pois200_foyfix_hc`：`foyer:target=0.95;hw=0;sf=0;sg=0` | **换了控制器**（`budget3` → `foyer`），且 `sf`（单飞）与 `sg`（饥饿保护）也关了 |
| 25 | `thr25_base`：`budget3`（**target 默认 0.75**，hw 开） | `thr25_push`：`budget3:hw=0;target=0.95` | 关了 hw，**并且 target 0.75 → 0.95** |

`--target-util` 的默认值是 **0.75**（`controller_budget3.py:94`，`run_matrix.py` 的
`controller_params` 也记 0.75），所以 25 档那一对**不是单变量**。

⇒ 「**One switch**, two regimes」在**两档上都不成立**：
- 25 档动了两根旋钮；
- 两档用的**不是同一个开关**（开关的集合、控制器都不同）。

## 怎么发现的

codex 第 39 轮报「这一句混入了控制器与开关差异」时，我按它说的去核 `policy` 前缀，
顺手把 25 档那一对也核了 —— 于是发现 25 档的 target **也变了**。
（codex 只报了 200 档那一半。）

## 改法（四处全改）

1. **§VII 开篇**：把两个对照**分别**按各自的实际差异写出来（轻载：同一个控制器、两根旋钮；
   重载：换了控制器、三个节流关掉），并明写
   `These are not the same intervention on the two tiers`，最后收口到
   「这一对确立的是**方向**，不是单一旋钮的剂量-响应」。
2. **§VII 末段**：`the same switch that is worth +51%` → `the aggressive setting that is worth +51%`。
3. **图 5 图注**：`The same throttle switch, two load tiers` → 改写为
   `The aggressive end of the same controller family … not the same intervention`。
4. **§I 的贡献条**：`the same throttle configuration worth +51% at 25 costs −42% at 200`
   → 改成「这个控制器族**激进的那一端**」，并加一句「两档动的不是同一组旋钮，§VII 有说明」。

## 这条为什么该记

它是本项目**第三条**「关于实验条件的词必须有出处」的实例，而且是**最贵的一条**：
前面两条（`no hw` 不是 no HiCache、`same-card` 没回 metadata 核）都只影响一句话，
这一条影响的是**论文的一条贡献陈述**。

**判据（不变）**：`policy` 串是**唯一**能确定「哪根旋钮动了」的字段；
`arm` 标签（`on` / `off`）、图例、run 名字都**不是**。
两档之间比较时，**先把两张 policy 串并排抄下来，逐项对**。

## 残留

- 25 档那一对**仍然是一个有效的对照**：同一个控制器、同一个 harness 代，动了两根旋钮。
  它说明「在这套控制器里，更激进的一端在轻载下好得多」，**但不是**「关掉水位线的效果」。
- 重载那一对也仍然有效，只是它的主语是**另一个控制器**。
- **要一个真正的单变量对照**（同一控制器、只关 hw、两档都跑），本轮没有跑；
  论文现在**不声称**它是单变量的，所以不需要补，但这是留给作者的选项之一。
