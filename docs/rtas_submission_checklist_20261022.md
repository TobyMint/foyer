# RTAS 2027 提交清单（2026-10-22 起草）
> ⚠ **2026-10-23 更新**：RTAS 2027 的投稿内容改为【新论文（10 月长会话线）】；9/28 冻结的旧稿**不投**。
> 本清单里的截止日期/格式/双盲/GenAI 披露要求仍适用，但提交物要等新论文写完（见 `docs/plan_positive_paper_20261023.md`）。

## 0. 硬事实（2026-10-22 从官网核对）

```
deadline   2026-11-05 23:59 AoE = 北京时间 2026-11-06 19:59   （还剩 15 天）
venue      RTAS 2027, CPS-IoT Week 2027, 2027-05-17~20
格式       \documentclass[10pt,conference]{IEEEtran}
页数       技术正文 ≤ 11 页；参考文献/致谢不计；camera-ready ≤ 12 页
评审       双盲（double-anonymous），违反可能 desk reject
补充材料   PDF 或 ZIP，≤600 MB，评审鼓励但不强制看
提交       HotCRP: https://rtas27.hotcrp.com/
ORCID      每个作者都需要
GenAI      必须在 Acknowledgments 披露（CFP §6 + TCRTS Transparency Oct-2026）
```

## 1. 已验证的稿件状态（2026-10-22 实测）

| 项 | 结果 | 命令/来源 |
|---|---|---|
| 干净重建 | 13 页 PDF；REFERENCES 从 p11 起 ⇒ 技术正文 ≤11 页 ✓ | `latexmk -C && latexmk -pdf main.tex` |
| 与冻结 PDF 一致性 | `pdftotext` 文本 **逐字相同**（diff=0） | 干净副本 vs `paper/main.pdf` |
| 数字检查器 | **882 项 / 0 MISS** | `python3 scripts/lab/check_paper_numbers.py` |
| 摘要 | 257–263 词（上限 265） | main.tex |
| 匿名 | 正文/supplement 无 URL、无姓名；PDF 元数据无作者 | 扫描 + `pdfinfo` |
| supplement | 14 页 PDF，已存在 | paper/supplement.pdf |
| **缺** | **GenAI 披露**（必须补）；AE tar（2027-02-18 才需要，可后补） | — |

## 2. 需要拍板的事

### ① 仓库可见性（今天必须处理）
`origin` = https://github.com/TobyMint/foyer，**当前 public**，且 `paper/` 全文已推上去。
双盲要求下两个选项：

- **(a) 提交前把仓库转 private** —— 最省事，不需要通知 PC chair。若师兄/合作者需要看，
  转 private 后把对方加成 collaborator 即可。我建议这个。
- (b) 保持 public —— TCRTS FAQ 对 arXiv 先例的口径是「可以投，但必须提前发邮件告知
  PC chair」；GitHub 公开稿同理，需要给 PC chair 发邮件说明。

⚠ 在定之前**不要 push 本地新 commit**（commit `5a02e68` 已在本地，含十月新线与原始数据）。

### ② GenAI 披露文本
草稿见 `docs/rtas_ai_disclosure_draft_20261022.md`。确认后我插入 `paper/main.tex`，
重编 + 重跑 882 项检查（预计只增加一段，页数有余量）。

## 3. 提交当天顺序

1. `cd paper && latexmk -C && latexmk -pdf -interaction=nonstopmode main.tex`
2. `python3 scripts/lab/check_paper_numbers.py` → 必须 882/0；`pdfinfo main.pdf` 页数 13
3. `pdftotext -layout main.pdf - | grep -n "EFERENCES\|Anonymous"` 目视
4. HotCRP：填 title / abstract / keywords / authors + ORCID / conflicts；上传
   `main.pdf` + `supplement.pdf`；确认 double-blind 声明
5. 提交后 `git tag rtas2027-submitted`，论文冻结，不再改

## 4. 提交前不要做的事

- 不再改负结果的数字与结论（除非审查抓到 hard error），不要在截止前 48 小时动版面
- 不要把 `results/oct2026_evidence/` 或十月新线的东西打包进 supplement
- 不要 push 到 public 仓库

## 5. 投稿之后

- 2027-01-11~15 rebuttal（若进第二轮）；2027-01-28 通知
- 2027-02-18 AE deadline（artifact 可选；`regen_all.sh` 可重建交付包）
- 转回「正结果论文」计划：`docs/plan_positive_result_20261022.md`
