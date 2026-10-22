# codex 第 19 轮（全稿）处置记录（2026-09-25）

codex 给 **5–15%**，八项机械核对里 **五项 MATCH、三项 MISMATCH**，五条 major、五条 minor。
它自己跑了两套复算：作者的 `check_paper_numbers.py`（当时 342 项、0 MISS）与新增的
`independent_frontier_check.py`，并从原始日志另算了 5/10/20 秒阈值。
**它明确说核心的 10 秒数值与 20 秒那条重复经得起独立复算** —— 争的是结论强度，不是算术。

**五条 major 里有两条是我在这一轮自己引入的**，这是本轮的教训。

## Major

### M1 结论的「cannot」比可分辨的结果强

结论写「on our system it cannot」，而直接测到的较窄事实是：九条里六条可比较、
六条都没观测到越过**插值线**；最近的一条只有一次、落在平局带内、且审计级别是 `watch`。

**已改**：「On our system we could not build one that does」——把它讲成「我们没能造出
一条做到的」，并点明插值前沿是两种基线里**更严**的那条（它高于离散静态点）。

### M2 结论误称「一张卡」（**我自己引入的**）

**已改**：「measured on one trace family, and the matched pair behind it ran on two cards
a day apart; the controlled version---one card, back to back---is queued rather than done」。

### M3 §V 预测三条重测臂「重要但不足以越线」是无根据外推（**我自己引入的**）

**这条最该记。** 我写这句话是为了让「修正方向对我们有利」读起来安慰，但算术恰好相反：
把已完成那次的 **+6.5 pp** 原样加在 `hz2` 的 **−4.81** 上是 **+1.7，越线**。

**已改**：明写「a warning about extrapolating from it rather than a reassurance」，
把 `hz2` 的 +1.7 算给读者看，并说**修正有可能越线、我们无法从现有数据排除**。
判据不变，只是不再替结果打包票。

### M4 第四条路线（执行粒度）声称「被测量否证」，但测量没测到它

`gate=4` 只在被阻塞周期的 **0.6%** 上生效（与没开门的臂相同），`gate=2` 只跑到 770 步。

**已改**：贡献列表改为「被**论证**否证（permit 机制表达不了那个控制）；我们跑成的
那一条臂不构成检验，因为它的闸门只在 0.6% 的周期里生效」。

### M5 §III「工具等待期间没有活可干」

那句话只对**正在等工具的那个会话**成立，对整个队列不成立 —— 队列里中位 66 个会话在等。

**已改**：区分「对该会话无活可干」与「对池子有」；并指出 §V 已经测过这条补救
（去记账臂把总空转从 47.4 降到 37.9 分钟）且它不改变判决。

## Minor（全部已改）

| 项 | 改法 |
|---|---|
| §IV 把「忙时吞吐不再上升」写成「墙钟变慢」 | 改为忙时口径，并写出反例：`cap4` 总墙钟比 `cap3` **快 8.8 分钟**（忙时 +3.3、空转 −10.4） |
| 图 3 图注把五个争用标记一概说成步时间膨胀 | 改为「五个带旗，其中三个实测抬高、两个无可测损害」 |
| §III 说主机服务的前缀「仍驻留设备」 | 与 `host_hit` 的定义（**设备未命中**且未重算）相反；改为按计数器定义陈述 |
| §VI「本文唯一一处越线」 | 改为「这条 trace 上的一处」，并指向 §VI 阈值段里主 trace 那条同样不复现 |
| `paper/data/` 里的旧快照 | `frontier_split.csv` 给 hz1 **+0.22**（正文 −0.93）、`wall_split.csv` 仍用已作废的 `bres` |

## 辅助表的重生成（值得单记，因为暴露了两处口径漂移）

`gen_frontier_split.py` 是**正文没引用**的辅助表，但它给 hz1 的混合前沿 +0.22，
而正文是 −0.93 —— 读者打开 `paper/data/` 会追到互相矛盾的答案。重生成时发现它有两处独立的口径问题：

1. **墙钟取的是 `decomp.csv` 的 1 位小数**，而表 I 用全精度（foyer_hc 得 −1.13 vs −1.24）；
2. **HiCache 锚点只有三条，漏了 `cap3_hc_r2` / `cap4_hc_r2`** —— 而论文的 FRONT
   正是用重复顶掉首跑的，所以它的包络是错的。

改成从 `runs_precise.csv` 读全精度、并把 `mixed` 那一组的锚点**直接 import
`frontier.py` 的 `FRONT`**（不自己再写一份）之后，九条臂的混合判决与表 I **逐条相符**。
并在 `check_paper_numbers.py` 里加了一条跨文件核对，防止它再漂。

这是同一个病的第三次：**两条管线算同一个量，必须共用定义**（前两次是表 I ↔ §V、
slo_sensitivity）。三次里有两次是自查扫出来的。

## 我自己犯的一处工具事故（已修，值得记）

为修上面那张表，我跑了 `swap_superseded.py foyer_bres foyer_bres_r2 --apply`。
**它把 `gen_superseded.py` 的旧/新对照对改成了「自己对自己」**，还把
`gen_eviction.py` 的 `SUPERSEDED` 名单里的 `foyer_bres` 改成了 `foyer_bres_r2`
（那等于把**干净的那条**排除出集合）——因为那个脚本只会按名字做全局替换，
分不清「run 列表项」和「谁替代谁的定义」。

**已回滚**（`git checkout` 五个文件），并把脚本改成三分类：
`run` / `comment` / `definition`，**默认只改 `run`**，其余要显式 `--force`。
`gen_superseded.py` 进了 `NEVER_TOUCH`。

教训与第七节那条同源：**连锁改名的风险不在漏改，在改到不该改的地方。**

## 自检

`check_paper_numbers.py`：**351 项、0 MISS**（本轮 342 → 351：frontier_split 的九条跨文件核对）。
编译 **24 页、0 Overfull、无 undefined**。
