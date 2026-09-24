# 第 14 轮 codex 审查（针对第二条 trace 扫描完成后的改动）与处置

codex 给 **20–35%**（它明确说「flagged 的重跑与排队的半池实验不算缺陷」）。五项里
**三项 MATCH**（第二条 trace 的八行兑现率、逐段斜率、新图与 `reuse.csv`/`reuse_x.csv` 逐点相符），
两处需要改，另有两处小的表述问题。全部处置如下。

## 一、数值错（已改）

**`14.27%` 应为 `14.26%`**：我用了 `elasticity_x.csv` 里印出的 66.2（一位小数）当分母，
codex 从原始时间戳复算是 **66.2050** 分钟 → 75.6448/66.2050 − 1 = **14.2584%** → 14.26%。
这是本项目反复出现的那一类（「用显示值算派生量」），这次是我写的。

## 二、主张强于证据（已改，是本轮最重要的一条）

我在摘要、结论、§VI、§criterion 四处都写了第二条 trace 的弹性「turns expensive」。
codex 指出：**ε > 1 在那条 trace 上只是「碰了一下」而不是「持续在 1 以上」** ——
三段是 +1.0、+0.18、+0.87（CSV 的未舍入值是 +0.98），而判据里 ε=1 的定义是
「加并发不再提升忙时吞吐」的门槛，主 trace 是 +1.15 越过后**留在上面**。

改法：四处统一为
- 摘要/结论：「the elasticity also **turns positive**……rising to 1.0 where the main trace's reaches 1.15」；
- §VI：「**approach** the criterion's expensive branch……**touches** one in the first of the three segments」；
- §criterion：「The ε>1 regime is **touched and not held** there……So the direction transfers and the
  location does not, and on this trace we can say no more than that added concurrency stopped paying.」

## 三、集合规则与条数对不上（已改）

正文写「十九条 host-tier run —— 同一条 trace、HiCache 开、≥995 步」，但**这三条条件本身筛出
二十条**（第四条排除是按名字写的那条引擎计数异常的 run）。已改为
「That rule on its own selects **twenty**, and we name the four runs it is not meant to catch」，
并把四条排除（两条短 run、变量负载族、那条异常的）都列在同一句里。

## 四、Limitations 与事实冲突（已改）

原文「one 24GB accelerator, one 7B model and **one trace family**; generality is untested」——
第二条 trace 就是对 workload 轴的检验，这句话自相矛盾。改为
「one 24GB accelerator and one 7B model. The workload axis we did test once more (§VI);
the hardware axis we did not, so generality across devices is untested.」

## 五、排版错误（已改）

`sec_model.tex` 里有一个 `exttt{realhr\_cap2}`（漏了反斜杠、前面还多一个制表符）——
编译不报错但正文里会印成错字。已修。

## 复核

全部改完后：`check_paper_numbers.py` **272 项、0 MISS**；编译 22 页、0 Overfull。
