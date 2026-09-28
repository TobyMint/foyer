# 审查范围：**r59 双审查处置之后**的验证（只审这一批，不审全稿）

## 背景

论文投 **RTAS 2027**（技术正文硬限 **11 页**，已达标）。r59 两条线都报了真问题，已全部处置。
**本轮任务是验证这批处置本身有没有引入新错。**
本项目历史：**每一轮处置都会引入新改动，而每一轮复核都抓到过真错**（最近九轮全中），
**其中至少五次是处置者自己引入的**。

**当前实测：**
```
861 项检查 / 0 MISS / 0 个 !!      常规 与 `python -O` **结果相同**
NORE=1：861 项 / 263 条 MISS
13 页（技术正文 11 页，REFERENCES 起于 p11）/ ?? 0 / Overfull 0
supplement：14 页 / 0 Overfull / 0 ??
AE artifact：`/tmp/ae_artifact/foyer-artifact/`（1459 文件 / 423 MB）
  regen_all.sh 48/48 rc=0 ｜ checker 861/0 ｜ 五条独立线 rc=0
```

## 这一批改了什么（**逐条都要核**）

### A. `regen_all.sh`（AE 门禁 —— 最该被打的地方）
1. **`projection_sat.csv` 的跳过改成有条件**：原来 `[ "$f" = "projection_sat.csv" ] && continue`
   **无条件跳过** ⇒ 交付一张错的它也报 48/48（codex 构造过：31 字节 vs 生成版 2473 字节）。
   现在**只在交付树里没有它时才跳过**。
2. **加了符号链接守卫**：`[ -L "$REPO/paper/data" ] && exit 3` ——
   因为 `cp -r` **保留符号链接**，沙箱里 `paper/data` 会直接指向活树，`rm -f` 删的是交付树。
3. **加了 mktemp 守卫**：`[ -n "$SB" ] && [ -d "$SB" ] || exit 3` ——
   `mktemp` 失败时 `$SB` 为空 ⇒ `cp -r … "$SB/"` 展开成写 `/`。
4. **删掉了 `run projection` 那一行**（它被 `run` 与 `frozen` 各登记一次，
   先重生成再被交付版覆盖 ⇒ `gen_projection.py` 一失败就把一张「声明不重建」的表报成 `!!`）。
5. **删掉了 `SELF` 变量**（自检改成记账后它已无任何引用，注释也过时）。

### B. `build_supplement.py` + `paper/supplement.{tex,pdf}`
6. **装错的文件已换掉**：原来装的是中文合并版，而 supplement 由英文版生成 ⇒
   重跑会静默丢掉整个 `\section{Per-arm re-derivation}`。现在**重跑与交付版逐字节相同**。
7. **宽表改横向页**（`pdflscape`）+ 收紧列距 + `\sloppy`：
   原来 **4 处 Overfull（最大 305.4pt）**，14 列那张表的**最右四列被裁在纸外**——
   `566 of 566`、`147.5941` 那组读数**正文引用它、PDF 里一个字都没有**。现在 **Overfull 0**，14 页。
8. **四处说强了的陈述改准**：检查器「857 项」（实为 861）→ 不写死数字；
   「每个数据文件由一个生成器写出一张 CSV」（有 3 张冻结、2 个生成器各写两张）；
   「逐周期读数」（那张表是每 run 一行的中位数汇总）；「三次基线尝试」表只有两行（补了第三次的说明）。

### C. `check_paper_numbers.py`
9. **新增 supplement 排版卫兵**（读 `supplement.log`）—— 起因：主论文的三条排版卫兵
   **只读 `main.log`**，而 supplement 是独立编译的 ⇒ **它一个卫兵都没有**。
10. **覆盖守卫收紧成「关键词必须出现在某一节的标题里」** ——
    原来查「关键词在不在文档里」，复核者逐节删掉 11 节试出**只有 6 节会报 MISS**。

## 请核（逐条给「成立 / 不成立 + 复算值 + 出处」）

1. **这批改动有没有让某个主张变强或变弱**？往任一边都算。
2. **`projection_sat` 的有条件跳过真的关掉了吗**（构造：交付一份错的 `projection_sat.csv` ⇒ 应报不一致 + rc≠0）；
   ⚠ 反面：**交付树里没有它**时是否仍能正常跳过（不要变成永远报错）。
3. **两条新守卫真的会拦吗**：`paper/data` 是符号链接 ⇒ rc=3；`mktemp` 失败路径 ——
   ⚠ 后者**别真的构造**（会向 `/` 写），只按 shell 语义评。
4. **`run projection` 删掉之后**：`projection.csv` 是否仍被正确当作冻结输入？
   `MANAGED` 里还有没有重复登记？
5. **`build_supplement.py` 重跑** ⇒ 与交付的 `supplement.tex` **逐字节相同**吗？
6. **supplement 的排版**：`supplement.log` 的 Overfull 是否 **0**？
   ⚠ **那四列（`watch n` / `watch foreign` / `dirty span min` / `dirty before end min`）
   现在真的在 PDF 里吗**（`pdftotext` 查）？
7. **supplement 的四处改准**：新写法与实情相符吗？有没有**改出新错**？
8. **两条新守卫的反向测试**：往 `supplement.log` 塞一条 Overfull ⇒ 应报；
   改掉 `\section{Per-arm re-derivation}` ⇒ 覆盖守卫应报。
9. **AE artifact 仍然可用吗**：在 `/tmp/ae_artifact/foyer-artifact/` 里跑三条命令
   （`regen_all.sh` / `check_paper_numbers.py` / `run_independent_checks.sh`），
   ⚠ **注意它是我在上一批之后重建的**，若与本 brief 描述不符请报出来。
10. **反向问**：这一批有没有**引入新的假通过通道**？
    ⚠ **「没有别的假通过通道」这句不许下结论** —— 只能报「点名测过哪几类、结果是怎样」。**继承这条克制。**

## 硬约束

- **只读**。扰动只在 `/tmp` 沙箱，写入前断言 `os.path.realpath(p)` 以沙箱路径开头。
  ⚠⚠ **bash 的 `ln`/`cp`/`mv`/`rm`/`>` 与 Python 写入同等对待** ——
  本项目已用这个形状出过三次事故（`open(w)`、无参数兜底调用、`ln -s` 的目录目的）。
- **不要用 `git checkout`**。**不要改仓库里任何文件。**
- ⚠ **从仓库根目录跑检查器**。`results/`（749MB）**别拷**，用符号链接。
- 参考材料：`/root/paper/reference_paper/rtas2026/`（24 篇 RTAS 2026 录用论文 + `INDEX.md`）。

## 报告格式

逐条 1–10：**结论（成立 / 不成立）+ 复算值 + 出处**。确证无误的也写一行。
最后单列「**我核不动 / 核不了的**」，写清为什么，**不许猜**。

⚠ **不要为了显得严格而编造弱点。没有问题的就写「成立」。**
