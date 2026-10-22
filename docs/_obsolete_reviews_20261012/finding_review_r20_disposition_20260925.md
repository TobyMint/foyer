# codex 第 20 轮（窄范围复读）处置记录（2026-09-25）

只核两轮改动引入的八项。**五项 RESOLVED、两项 PARTIALLY**，另指出一条新歧义。
codex 仍给 **5–15%**（与第 19 轮同），理由是三条受污染臂待重测。

## RESOLVED（它逐条复算过）

- **§V 的非支配读法与 §II 口径一致**。
- **表 I 脚注的 ‡ 算术**：`concurrency.csv` 里 CONTESTED 且仍在 `table1.csv` 的是
  **5 行**，表 I 显示 5 个 ‡，第六行是已替代的旧 `bres` ——「六行曾带旗、五行仍然带」准确。
- **host-tier 集合**：`reuse.csv` 的 hicache 族 **19 行**，1.41× 那条与被替代那条均不在内。
- **§II 的 harness 保真度**：cap1 的 799 次转换要求均值 15.82 = 实测均值 15.82，
  比值中位 1.0007（→1.001）；**要求间隔的中位 0.34s**。
- **§VI 的 ε = −0.28 / R̄ 1.16–1.29** 与 `elasticity_x.csv` 相符。
- **+51% / −42% 的跨代限定**：按墙钟复算为 **50.68% 更快 / 42.46% 更慢**，
  两处限定与 §VII 一致。

## PARTIALLY → 已补齐

### 1. 摘要的「nearest」有歧义

`4.4pp` 是相对**更快的那条前沿锚点**（cap3+HC repeat，81.88%）；而按墙钟距离
理解，最近的静态点是 **cap5（260.9 分钟）**，差值是 **59.2pp**。
**已改成**「4.4\,pp above the nearest static point that is \emph{faster} than it」。

### 2. 三处降级**没有贯彻到全篇**（这是本轮最有价值的一条）

我上一轮改了摘要的三处措辞，但同一件事在正文里还有别的说法：

| 摘要（已降级） | 正文残留 | 处数 |
|---|---|---|
| 「tracks the memory tier」 | §III 小标题仍写「the tier, not the policy, **decides**」 | 1 |
| 「1.79× the occupancy the engine reports」 | 仍写「1.79× **the truth**」 | §V 与结论，2 处 |
| 「does not show they could have taken the room」 | 仍写「the engine **had room**. Our controllers **did not take it**」 | §IV 与结论，2 处 |

**全部已改。** §III 小标题改为「What tracks reuse is the tier, not the policy」
（与正文「cross-policy association」同口径）；两处「1.79× the occupancy the engine
reports，其中 growth reserve 占预算 28%」；两处改成否定式并补一句
「这不等于证明了他们在别处能赢（§V）」。

## 本轮暴露的一条通则

**降级一处措辞时，必须把同一个说法的所有出现处一起找出来改。** 我上一轮只改了摘要，
codex 一查就把正文里的四处全列了出来 —— 这与 CLAUDE.md 里
「连锁改名要按【数字】清点，不只按【名字】清点」是同一类：**同一个主张会在全篇
用不同的词说好几遍**，改一处不等于改完。已加进 CLAUDE.md。

## 自检

`check_paper_numbers.py`：**366 项、0 MISS**；编译 **24 页、0 Overfull、无 undefined**。
