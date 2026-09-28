# codex 第 40 轮：**审「压缩有没有把限定吃掉」**

## 背景

作者反馈 PDF 太长（30 页），要求压到 8--15 页，并说「不重要的细节可以直接不要」。
本轮把正文从 **29,400 词压到 20,043 词、30 页 → 20 页**，由五条并行的压缩线完成。

压缩是**最危险的一类编辑**：删掉一句限定，文章读起来更顺、主张更强，而**没有任何东西会报错**。
本项目为此立过一条纪律（「审查一直在防把负说成正，所以把正说得更负没人防」），
而这一轮是**规模化**地做这件事。

## 请专门查这一个问题：**压缩有没有把某处主张说强**

判据：**对每一处论断，问「它现在写出来的强度，与它引的证据匹配吗」，而不是「它读起来顺不顺」。**
具体扫这几类（在 `paper/sec_*.tex` 里）：

1. **被删掉的让步**：原稿里凡有「though / however / although / but / on the other hand /
   it is not the same as / we do not claim / stricter is not the same as valid」的句子，
   压缩后还在不在？**特别是有没有哪一处，让步没了、只剩主张。**
   （已知一处：§III 的 `though at a stricter one it does` 是子 agent 顶着指令加回来的；
   请查还有没有同类。）
2. **被删掉的「我们没测」**：`we did not run / we cannot / not distinguishable / no error bars /
   one run each / indicative / provisional / association rather than intervention`。
3. **统计口径**：区间与条数被删后，剩下的句子有没有变成「普遍成立」的口吻
   （原句是「33 条里有 8--40%」，删成「τ₁ 高于 τ₂」就变强了）。
4. **打平带与判决**：±1.0pp、`on the line`、`below the line`、`tie` 的措辞有没有被压成
   「赢/输」。
5. **A100 那条**：必须是「**更弱的结论**」，不许被压成「复现」。
   （原句 `The negative result is a weaker claim on this evidence, and we scope it rather
   than let the tie carry it`。）

## 也请查这两件

6. **检查器的退役名单**（`scripts/lab/check_paper_numbers.py` 里的 `RETIRED`，81 条）：
   每条的 `R1/R2/R3` 理由**与正文现状是否相符**。特别查有没有哪条是
   **「承重数字」被退役掉了**（那本该是「恢复」而不是「退役」）。
   判据：把那条描述里的数拿去全稿 `grep`；若全稿都没有，而它支撑的论断还在 → 那条退役是错的。
7. **图与正文是否还对得上**：图 2、图 3 现在只画 **17 条臂**（原来 34），
   图注与正文都改成了「画 17 条、统计对 34 条算」。请核**每一处**提到这两张图的句子
   （`Fig.~\ref{fig:decomp}` / `fig:steptime`），有没有哪处还按 34 条的口吻写。

## 输出

`## Major issues` / `## Minor issues` / `## Questions requiring clarification`。
每条给：**文件:行号 + 现在的原句 + 它为什么比证据强（或为什么退役错了）**。

**不要报**：错别字、排版、守卫的字符串匹配边界、参考文献格式。
**不要为了显得严格而编造**；核不到就写「核不到，因为……」。
