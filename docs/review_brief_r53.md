# r53 审查：验证 **r52 处置 + 检查器卫生**（只审这一批）

## 现状
**850 项检查 / 0 MISS / 0 个 `!!`（退役未生效）/ 正文 11 页 / `??` 0 / 摘要 265 词。**

论文投 RTAS 2027（技术正文硬限 11 页，已达标）。

## r52 处置改了什么（**逐条都要核**）

1. **`sec_results.tex` 加回 `the arm for`** —— 之前为压字数删了它，导致
   `charges the permit wait it imposes` 的 `it` 指到了「钟」而不是「臂」。
2. **同一文件的重写句**：`the readings above the line come from the \emph{release} rule,
   not from the budget rule admission acts on`（原来是 `admission control is not what we measured`，
   与「测了九种准入变体」相抵）。
3. **`not a stable crossing`**（原 `not a reproducible crossing` —— codex 指出前两次确实重复越线）。
4. **`sec_discussion.tex:165`**：`One arm's readings are above **the band** on two of its three runs`
   （原 `above it`，而 hz2 的 +0.22 是「线之上、带之内」）。
5. **四处限定词还原**（`same controller revision` / `not a clean estimate of one revision's noise` /
   `not four independent replications`）。
6. **驱逐句**：`though it differs from both in card and launcher and from one in controller
   revision, so it cannot isolate the eviction policy's effect`。
7. **`sec_intro.tex`**：`we **observe** no gain beyond the band here`（原 `claim`）。
8. **`claims_audit.md` / `lane_evict_slru.sh`** 的「覆盖 2.4%」→「覆盖本次测量窗 5.8%」。
9. **`CLAUDE.md` 的 `NORE=1` 判据描述改正**（原文「看哪些检查从通过变成 MISS」**恒为空集**，
   因为 `ck`/`ck_near` 先查值后查退役）。并**给检查器加了 `!! 退役未生效` 机制**。
10. **检查器卫生**（我做的）：三个前缀退役键造成的吞并已修 ——
    - `"host-tier run 条数（§I*"` 的 `§I` **是 `§III` 的前缀**，吞了两条活守卫 ⇒ 拆精确键
    - `"斜率 main*"` / `"斜率 xtrace*"` 同理 ⇒ 拆成 10 条精确键（值确实不在正文的才退），
      让活着的 `斜率 xtrace 1.076->1.160`（31.2，值仍在正文）复活

## 请核（逐条给「成立/不成立 + 复算值 + 出处」）

1. **第 1–7 项的正文改动**：逐句核 —— 有没有**新引入**的语法/指代/事实问题？
   特别是第 2 项那个重写句，语义对不对？第 4 项的 `above the band` 是否准确？
2. **`!!` 机制**：它真的能在「退役项的值仍在正文」时报警吗？**在沙箱里构造验证**
   （把某条退役键留着、把它盯的值写回正文 ⇒ 应打 `!!`）。
3. **三个前缀键的拆分有没有误伤**：核 `host-tier run 条数（§III）`、
   `斜率 xtrace 1.076->1.160` 现在**真的在跑**（`-v` 下应印 OK），
   而其余 **12 条**（10 条斜率 = 5 main + 5 xtrace，加 2 条 §I 的 host-tier 条数）
   **真的退了**（`NORE=1` 下应全报 MISS）。
   ⚠ 原文写「其余 9 条」——**错的**，r53 复核实测 12（判据：
   `NORE=1 python3 scripts/lab/check_paper_numbers.py -v | grep -c "MISS 斜率\|MISS host-tier run 条数（§I"`）。
   ⚠ r53 处置后其中 `斜率 xtrace 1.076->1.160` **也退役了**（它「复活」的依据只是
   字符串撞车，见 CLAUDE.md 的 `STR_ELSEWHERE`）：它现在印 `~~`（不是 OK），
   而 `NORE=1` 下它印 **OK 不是 MISS** —— 所以「其 12 条」里它不算，**12 这个数不变**。
4. **为守 11 页删的 ~31 词**：逐处 `grep` 里面的每个数，确认**不是唯一出处**。
   ⚠ 本项目记过：「删一句之前先 grep 它里面的每一个数，只出现一次 ⇒ 那是在承载证据」。
5. **篇幅与排版**：`pdfinfo` + 逐页 `grep -c "R EFERENCES"`；`??` 0；0 Overfull；
   **摘要 ≤265**（现在**恰好 265**）。
6. **反向问**：这一批处置有没有让**某个主张变强或变弱**？往任一边都算。

## 硬约束
- **只读**。扰动在 `/tmp` 沙箱，写入前断言 `os.path.realpath(p)` 以沙箱路径开头。
- **不要用 `git checkout`**。**不要改仓库里任何文件**。
- ⚠ **从仓库根目录跑检查器**（从 `/tmp` 跑会把探针脚本算成「第二份实现」报假 MISS —— r52 复核者撞到过）。
- 报告：逐条「结论 + 复算值 + 出处」；确证无误的也写一行。
- 最后单列「**我核不动/核不了的**」。
