# 审查范围：**09-27 这一批改完之后**的当前状态（只审这一批，不重审全稿）

## 背景

09-27 凌晨两条新 run 落地（`pois200_foyer_scan` Δ=+1.3044 ABOVE、`pois200_foyer_hz2_r3`
Δ=+0.2167 TIE），头条照实改写；随后两轮审查（codex r47 + 中立子 agent 第 1 轮）报了
**14 处真错**，已逐条处置。这一轮的审查对象是**改完之后的稿子**。

## 请做的（A：逐条验「改对了没有」）

下面 14 条是我**声称已修**的。**逐条独立复核**，给「成立 / 不成立 + 你的复算值」。
**不要采信我的说法** —— 每一条都要回 `paper/*.tex` 与 `paper/data/*.csv` 自己算。

1. §V 现在说 `scans the queue` 是「扫全队、**每周期只放行第一个装得下的**」，
   并引 `8030` 个控制周期、`210` 次放行、「never two」。
   → 核 `results/night/pois200_foyer_scan/controller.jsonl` 的 `n_admitted` 分布。
2. 「0.5 到 4.6pp」= **同配置重复的 Δ 全距**（base 1.91 / hz1 4.65 / hz2 0.51）。
   → 自己按 `replicates.csv` 的分组重算 Δ 全距。
3. §VI 现在写 `horizon=1` 的两次重复「−2.3, **below the band**, and −0.03, **inside it**」。
   → 用 `frontier.classify` 核 −0.03 的判词。
4. §III idle 的第二个区间现在写 **6.4% to 42.5%**（按墙钟）。
   → 用 `decomp.csv` 的 `idle_min / wall_min` 复算。
5. §III host-tier 集合 **26**（六处）+ 排除项「**five** runs ... one whose engine
   prompt-token counter reads 1.41×, and four superseded measurements」。
   → 核 `reuse.csv` 的 hicache 行数与排除清单。
6. §V projection **23**；gate_attrib **48** / **31.3%**。
   → 这两张表只能在实验机上重生成（`/data/xbw/turnstile/scripts/`），可以用 ssh 跑。
7. §V 归因表 **13** 行（加了 `scans the queue & 54.3 & 1.439 & 28.6 & unused mem.`），
   计数句写「Of the **thirteen** arms, **seven** are attributed: **six** to unused memory」。
8. §V/§VI 同族干净 run **fifteen**（两处）。
9. §V「the ratio of mean running requests to mean live sessions is **0.21 to 0.64**
   across the **thirty-one** runs we have both columns for」。
10. 图 1 的标注是**从 `table1.csv` 现取**的（标签/坐标/Δ/条数全派生），
    且 pdf 上不再印出反斜杠（原来 `\,` 落在数学模式外）。
11. 检查器的 `_C11` / `_CTRL` 已改成**从 `arrival_slo.csv` 现算**，且**两侧边界**都查。
    → 读代码 + 自己设计反向测试。
12. `NORE=1` 已实现（`os.environ`）。→ 跑一次，报 MISS 条数。
13. `slo_sensitivity` 不再对锚点 `round(...,1)`，10s 列与 `table1.csv` 逐位一致。
14. `gen_stall` 的表头是**一行**完整列名（`max_per_cycle` 已加），
    且 `foyer_scan` 的 `max_per_cycle=1`、`foyer_sf0_r2` 的是 `2`。

## 请做的（B：反向问 —— **这一批改动有没有【引入】新错**）

15. §V 那段现在把「观测」与「推断」分开写（「this run is above the band」/「we do not
    read it as the controller having crossed」）。这个区分站得住吗？有没有哪里又把两者混回去？
16. 「the same controller revision and the same flags as the base's own repeat,
    with exactly one expression changed」——**逐字核**：`metadata.json` 的 `code` 块、
    policy 串、以及实验机上两个控制器文件的 diff。**这句话有没有说过头或说不够？**
17. §VI 新加的 harness 披露（`run_matrix.py` 哈希在两对比较里都不同、旧版被就地覆盖、
    无法 diff、只能说「控制器源码与记录的参数/build 一致」）——**准确吗？有没有该说而没说的？**
18. **方向审查**：这一批改动里，有没有哪一处**把结果说得比证据更强**？又有没有哪一处
    **把结果说得比证据更弱**？（后者是本项目所有审查都漏过的一类，已经栽过一次。）
19. 篇幅：我把 §I / §III 容量对照 / §VII 单变量分解 / Related Work / 两个题注压过。
    **有没有在压缩中删掉了一个仍然成立的限定语或对冲？**（这是「压缩会静默关掉守卫」的同类。）

## 硬约束

- **只读**。要扰动就在 `/tmp` 下自建沙箱，写入前断言 `os.path.realpath(p)` 以沙箱路径开头。
- **不要用 `git checkout`**（工作区就是最新版本）。
- 不要重审全稿、不要提篇幅目标、不要提撤回记录本身、不要编造文献。
- 报告格式：逐条给「结论 + 复算值 + 出处」，确证无误的也写一行，不要只报问题。
- 最后单列一节「**我核不动/核不了的条目**」，写清为什么，不许猜。
