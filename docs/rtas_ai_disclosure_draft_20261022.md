# RTAS 2027 GenAI 披露草稿（2026-10-22）

## 一、政策要求（原文要点）

- **RTAS 2027 CFP §6**：「If generative AI tools were used in preparing the manuscript,
  authors must explicitly disclose their use in the **Acknowledgments** section ...」
- **TCRTS Transparency（Oct 2026）**：能生成新文本/论证/引文/重写整节/画图的工具
  「must be carefully supervised, and their use must be disclosed in the acknowledgments.
  This disclosure is required to state **which Generative-AI tools were used**, as well as
  providing a **detailed cross reference** to the text (paragraphs, subsections, sections),
  diagrams, images, and underpinning research (e.g., code, implementations) that the
  Generative-AI assisted in the creation of.」
- ⚠ 政策冲突：TCRTS 双盲要求「submitted manuscripts should not include any
  acknowledgments (including funding)」。建议的处理：放一个**不含身份/资助/单位信息**的
  「Generative-AI disclosure」段落（CFP 明文要求的合规内容，不泄露身份），
  并在给 PC chair 的邮件里提一句（如果决定发信）。

## 二、建议文本（英文，可直接放进 main.tex）

### 版本 A：完整版（推荐）

```latex
\section*{Generative-AI disclosure}
\label{sec:genai}
Generative-AI tools were used in preparing this manuscript and the research it
reports. Anthropic's Claude (accessed through the Claude Code command-line
agent) was used to draft and edit the text of all sections and the abstract;
to implement and debug the controller and replay-runner changes described in
\S\ref{sec:model} and \S\ref{sec:discussion} and in the supplementary
material; to write the experiment-orchestration, table-generation and
figure-generation scripts; to run experiments and analyse the resulting
logs; and to generate Figs.~\ref{fig:frontier}--\ref{fig:cancel} and the
tables. OpenAI's Codex was used, in a read-only reviewing role, to audit the
manuscript and the numeric-consistency checker. All research questions,
experimental designs, interpretations and conclusions are the authors'; every
number in the paper is linked to the raw logs by an automated consistency
check, and the authors have verified all technical claims and take sole
responsibility for the content.
```

按插入位置：`main.tex` 中 `\bibliography{refs}` 之前。约 150 词（页数有余量）。

### 版本 B：最小版

```latex
\section*{Generative-AI disclosure}
Anthropic's Claude (via Claude Code) was used to draft and edit the manuscript
text, to implement the controller and experiment code, and to generate the
tables and figures; OpenAI's Codex was used for read-only reviewing. The
authors designed the research, verified every reported number against the raw
logs, and take sole responsibility for the content.
```

## 三、插入前必须确认

- [ ] 工具清单准确：Claude Code（Anthropic）是否就是实际用的入口；是否提 Codex
- [ ] 「实验是我们跑的、AI 协助执行」这个程度描述是否准确（按实际：AI 在作者指令下执行了 run）
- [ ] **不含任何可去匿名化的字符串**：仓库路径、URL、机构、姓名、显卡型号之外的机器信息
- [ ] 双盲下是否同时给 PC chair 发一封说明邮件（推荐发，一句话即可）
- [ ] 插入后重跑 `check_paper_numbers.py`（882/0）并重新数页数

## 四、给 PC chair 的邮件草稿（可选，和仓库可见性一起决定）

> Subject: RTAS 2027 submission #__ — anonymity and generative-AI disclosure
>
> Dear Program Chairs,
>
> We are submitting a paper to RTAS 2027. Two procedural notes: (i) [if the
> repository stays public] the work is being developed in a public code
> repository that contains the manuscript source; we are happy to make it
> private if you prefer. (ii) The manuscript includes a brief generative-AI
> disclosure paragraph (required by the CFP); as it contains no identifying
> information we have placed it in the submitted PDF under double-anonymous
> review.
>
> Sincerely, [author]
