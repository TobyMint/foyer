# 审查范围：**09-27 两条 run 落地之后**的当前状态（只审这一批，不要重审全稿）

## 背景（事实，请**独立复核**，不要采信）

2026-09-27 早上两条重复 run 落地：

- **`pois200_foyer_scan_r2`**：全篇唯一越过 ±1.0pp 那条臂（`foyer_scan` Δ=**+1.3044**）的第一次重复。
  实测 **Δ = +2.1600 ⇒ ABOVE**。⇒ **越线复现**（跑前预写的三种预期里的 (a)）。
- **`pois200_foyer_sf0_r3`**：第二近那条臂（`foyer_sf0_r2` Δ=−0.5519）的重复。
  实测 **Δ = +0.1310 ⇒ ON（带内）**。

⇒ 论文**头条被改写**：从「第十条臂一次读数越线、unresolved」升级为
「**该臂两次读数都越线**，改的是 *release* 规则而非准入决策」。

## 请做的（A：逐条验「这一批改对了没有」）

下面每一条都是我**声称已改**的。**逐条独立复核**，给「成立 / 不成立 + 你的复算值」，
回 `paper/*.tex` 与 `paper/data/*.csv` 自己算。**不要采信我的说法。**

1. **两条新 run 干净吗**：`results/night/pois200_foyer_scan_r2` 与 `..._sf0_r3` 的
   `metadata.json`（pool 必须 101432±20、主 trace、policy 串）、`steps.jsonl`
   （999 步、`failed=0`、**`prompt_len` 合计是否等于 trace 计划 28,526,871**）、
   `gpu_watch.jsonl`（窗内有没有外人）。
2. **Δ 与判词**：`paper/data/table1.csv` 里这两条的 `delta_pp` 与 `verdict`；
   用 `frontier.classify` 独立核判词。
3. **头条的三处改写**（§I、摘要、§V 的 scan 段）：数值是否逐位相符？
   §V 写了「the two clear it by $0.30$ and $1.16$\,pp」—— 核这两个余量。
   §V 还写 ready 时钟下「first run $-0.07$, repeat $+1.51$」—— 核对。
4. **§VI 的表**：新加了两行（`scans the queue (2nd run)` 与 `single-flight off (2nd run)`），
   逐个格子对 `paper/data/slo_sensitivity.csv`（**注意短名**：`scan_r2`/`sf0_r3`）。
   表前那句「five of them cross」与它引的三个值，逐个核。
5. **§VI 表后那段**：`+1.30` / `+2.16` / 余量 `1.16` 与 `0.30` /「the only arm here
   above the line at 5, 10 and 20s」—— 这一句是本轮最强的主张，**请重点反查**：
   真的只有它吗？（把 `slo_sensitivity.csv` 里每条臂在每个阈值下都过一遍。）
6. **`gen_eviction.py` 的集合 26 → 28**：正文六处「twenty-eight host-tier runs」
   与「the host serves 3.1--19.3M」/「59.7--92.5%」两个区间是否仍成立？
7. **§V/§VI 的「0.5 to 4.6pp」与「the tightest of the five groups at 0.5pp」**：
   现在是**五组**（base 1.91 / hz1 4.65 / hz2 0.51 / scan 0.86 / sf0 0.68）。
   ⚠ **基准**：必须用 `runs_precise.csv` + `frontier.front_slo()`（用 `table1.csv`
   会把 `pairA_foyerhc`/`pairB_foyerhc` 漏掉 ⇒ base 组变 n=2 ⇒「最紧」的结论**相反**）。
8. **§VI ready 子集**：「twenty-eight of the thirty-five 200-session runs in
   Table I, the rest being the no-control baseline, four host-tier runs and two
   controller repeats」—— ⚠ 分母是**表 I 在 LaTeX 里印了几行**（35），
   **不是** `table1.csv` 的行数（37，它多含 `pairA_cap2hc` 与 `aimd2_paper` 两条不印的）。
9. **§V 的 projection / gate_attrib / occupancy 三个计数**：
   `twenty-five` / `1.75`、`31.8% / 5.9% / fifty`、`thirty-three` —— 逐个核 CSV。
10. **§IV/§II 的重复组**：组数 `nine`、枚举 `0.3, 0.5, 0.7, 0.8, 1.0, 1.0, 4.4, 4.9, 5.1`、
    §II 区间 `0.3 to 5.1` —— 核 `replicates.csv`。
11. **图 1**：现在 37 个点；标注文本是「scans the queue / (+1.3 and +2.2 pp, two runs)」。
    `_n_rep` 我改成了**按配置名计数**（剥掉「(2nd run)」后缀），核这个改法对不对。
    **把图渲出来看**（`pdftoppm -r 300`）：有没有压点、有没有画出轴外、有没有印出反斜杠。
12. **`gen_table.py` 的 `Conc.` 位数**：我把它从「一律 2 位」改成「>10 用 1 位」
    （`no control` 那行 94.91 → 94.9），与检查器里那条守卫的约定对齐。核这个改动
    有没有影响别的行。

## 请做的（B：反向问 —— **这一批有没有引入新错**）

13. **头条改写有没有说过头？** 「crossing reproduces」是不是站得住？
    ⚠ 两次读数相差 **0.8556pp**，而 §V 同时写「同配置重复的 Δ 全距是 0.5--4.6pp」——
    0.86 落在那个区间里，**这算不算「复现」还是「落在重复散布内」**？请给判断与依据。
    （这是本轮**最可能被审稿人攻击**的一处。）
14. **有没有说得比证据更弱？**（本项目所有审查都在防「把负说成正」，
    **反过来那类没人防**，已栽过一次。）本轮把「unresolved」升级成「crossing」，
    是不是反过来在某处**过度收紧了**？例如 ready 时钟下两次读数一内一外
    （−0.07 / +1.51），正文的措辞够不够准确？
15. **§V 的「single-flight off」那句**：现在写「lands 0.55pp below the line on its
    first run and +0.13pp on its repeat」—— 核这两个数，以及这句话现在还算不算
    「扫队列不必然赢」的**反例**（它的配对是 −0.55/+0.13，都没越线）。
16. **陈旧说法扫描**：两条 run 进表之后，**所有派生量**都可能过期 ——
    条数、名次、区间端点、分组计数、集合规模。有没有哪一处**守卫没覆盖到**？
    （提示：本轮我自己就抓到三处守卫覆盖不到或算错的口径，见下。）

## 请做的（C：本轮已知的「守卫自己算错」记录 —— 请复核我的修法）

17. `landing_triage.py` 的分支判断原来写 `if v1 == "ABOVE"`，而 `frontier.classify`
    返回 `"ABOVE  (越过前沿)"` ⇒ **恒落到 else**，把「两次都越线」报成「不复现」。
    已改成 `startswith`。**请核是否还有同类的等号比较**（全仓库）。
18. `gen_eviction.py` 的判据在实验机上曾给 27 而名单是 26（`slice23_hc`
    满足机械判据但不是单一配置）⇒ 生成器**在机器上直接报错退出**。
    已加 `NOT_SINGLE_CONFIG` 类别。**请核这个类别名与正文判据句是否一致。**
19. §VI 的「N of the M runs in Table I」那两个数，判据是**LaTeX 表印了几行**。
    我一度用 `table1.csv`（超集）当分母、**差点把一句正确的话改错**。
    已加一条「铺满性断言」（表 I 行数 == 有日志的 + 排除的）。**请反向测试这条断言。**

## 硬约束

- **只读**。要扰动就在 `/tmp` 下自建沙箱，写入前断言 `os.path.realpath(p)` 以沙箱路径开头。
- **不要用 `git checkout`**（工作区就是最新版本）。
- 实验机 `ssh lab-3090` 可用（**60 秒超时内返回**）；脚本在 `/data/xbw/turnstile/scripts/`
  （**不是** `scripts/lab/`），结果在 `/data/xbw/turnstile/results/night/`。
- 不要重审全稿、不要提篇幅目标、不要编造文献。
- 报告格式：逐条给「结论 + 复算值 + 出处」，确证无误的也写一行。
- 最后单列「**我核不动/核不了的条目**」，写清为什么，不许猜。
