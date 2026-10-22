# 审查范围：`foyer_scan` 越线后的头条改写（只审这一批，不要重审全稿）

## 背景（事实，请**独立复核**，不要采信）

2026-09-27 两条新 run 落地，正文因此改写：

- `pois200_foyer_scan`：新增的第十条控制器臂。作者的说法是「与 base 的重复同控制器修订、
  同 flags，**只改了一个表达式**（`head = waiting if args.disable_single_flight else waiting[:1]`
  → `head = waiting`，见实验机上 `TraceLab/replay/scripts/controller_budget3_scan.py`，
  与 `controller_budget3.py` 的 diff 只有这一个 hunk）」。它的 Δ = **+1.3044** ⇒ 判据
  `> +1.0` ⇒ **ABOVE**（全篇唯一的正 Δ）。
- `pois200_foyer_hz2_r3`：头条那条臂（`horizon=2`）的**第一次重复**，Δ = **+0.2167** ⇒ TIE。

## 请做的（A：独立复核事实）

从 `results/night/*/metadata.json`、`steps.jsonl`、`paper/data/*.csv`、以及你能 ssh 到的
实验机（`lab-3090`）独立核下面每一条，**逐条给「成立/不成立 + 你的复算值」**：

1. `paper/data/table1.csv` 里 `foyer_scan` 的 Δ 与判决；`foyer_hz2_r3` 的 Δ 与判决。
2. 「同控制器修订、同 flags、只改一个表达式」：`metadata.json` 的 `code` 块逐键对比
   `pois200_foyer_scan` vs `pois200_foyer_hc_r2`；并真的去实验机 `diff` 那两个控制器文件，
   确认**只有一个 hunk**、且非注释的实质差异只有那一行。
   ⚠ 也要核 `pois200_foyer_hz2_r2` vs `pois200_foyer_hz2_r3` 的 `code` 块（作者称二者
   只差 `run_matrix.py` 的哈希）。
3. 正文（`paper/sec_results.tex` §V 的第二段）说：那条修订「除非显式关掉单飞，否则只放行
   队首」，而 scan 臂「放行整个队列，别的什么都没改」。核 `controller_budget3.py` 里
   `disable_single_flight` 的**全部**出现位置，确认作者对 `single-flight off` 的描述
   （「同一个 flag 还关掉了另外两处」）是否成立。
4. `paper/sec_results.tex`：「its wall clock is 26.9 minutes (9.2%) below the base's own
   repeat at 1.0pp lower SLO」——「base 的重复」指哪条？数与实值是否逐位相符？
5. `paper/sec_results.tex`：「smaller than the 0.5pp that separates our two closest repeats
   of any one configuration」——把**所有**同配置重复对的 Δ 散布都算出来，确认 0.5pp 真的是
   最小值（注意 anchors 的 Δ 是 0，要判断它们算不算「重复对」）。
6. `paper/sec_results.tex`：`single-flight off`「lands 0.55pp below the line」。
7. `paper/sec_discussion.tex` §VI 阈值表：五行新/改过的格子（`scans the queue`、
   `horizon=2 (2nd run)`、`horizon=1` 的 5s、`horizon=1 (3rd run)` 的 20s、`Concur-style
   AIMD` 的 5s）是否与 `paper/data/slo_sensitivity.csv` 逐位相符（按正文精度）。
8. `paper/sec_discussion.tex`：`horizon=1` 的两次重复在 20s 下是 $-2.3$ 与 $-0.03$、
   `horizon=2` 的重复是 $+0.49$ —— 逐位核。
9. `paper/sec_discussion.tex` 的「four different hashes of `controller_budget3.py`, and none
   of the four matches the repository copy」与「22 lines, in two places」是否仍成立。
10. `pois200_foyer_scan` 这条 run 本身干净吗：池子是否 `101,432±20`、`gpu_watch.jsonl`
    窗内有没有外人、`steps.jsonl` 是否 999 步且 `failed=0`、**计划 prompt 是否等于实测
    prompt**（这一条是本项目栽过的：退化响应会把兑现率虚报 30pp）。

## 请做的（B：反向问，本项目的老毛病）

11. **有没有哪一处比证据更强？** 尤其：「not one of the nine」这个划法是不是在把一条越线的臂
    挪出计分范围？如果换成「十条臂里有一条越线，那条是改了一行的版本」，结论会不一样吗？
12. **有没有哪一处比证据更弱？**（本项目所有审查都在防「把负说成正」，**「把正说得更负」
    没人防** —— 已经栽过一次。）例如把 `+1.30` 说成「我们不当作越线」，是不是过度收窄？
13. 「the same flags as the base's own repeat」——scan 的 policy 串前缀是 `budget3scan`，
    base 的是 `budget3`。说「同 flags」精确吗？
14. `run_matrix.py` 的哈希在 `hz2_r2`/`hz2_r3` 之间、以及 `hc_r2`/`scan` 之间**不同**
    （`b866b92c6eed`/`a8605b1e77d5` → `cfd46f9b1ea2`）。正文该不该披露这一点？
    披露在哪儿合适？（`paper/sec_discussion.tex` 的 Limitations 里有一段讲重复的可靠性。）

## 请做的（C：陈旧说法扫描）

15. 两条 run 进表之后，**所有派生量**都可能过期：条数、名次、区间端点、分组计数、集合规模、
    「only / never / none / exactly one」这类绝对词、以及**围绕同一张表的表前句/表后句**。
    请把 `paper/*.tex` 通读一遍，列出**任何**你怀疑已过期的地方（给行号 + 原文 + 你的复算）。
    已经改过的（供你核对改得对不对）：§I、摘要、§III 的 34→36、§IV 脚注 6→7 组、
    §V 的九条段与 occupancy 条数/Spearman、§V 的 11→13、§VI 阈值段与表、§VI ready-clock
    的 24/31→26/33、§VII 的 6→7 与结论、以及 §VII 的控制器 artifact 段。

## 硬约束

- **不要改任何文件**（只读审查）；要扰动就自己在 `/tmp` 建沙箱，且写入前断言
  `os.path.realpath(p)` 在沙箱内（`islink(文件)` 挡不住父目录是符号链接，本项目栽过两次）。
- **不要用 `git checkout`**（本仓库工作区就是最新版本，这么干会静默丢掉一整天的工作）。
- 不要重审全稿、不要提篇幅、不要提撤回记录里的主张、不要编造文献。
- 报告格式：每条给「结论 + 你复算的值 + 你用的文件/命令」。
