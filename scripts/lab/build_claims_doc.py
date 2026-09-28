#!/usr/bin/env python3
"""生成 AE 文档的 `CLAIMS.md`：每张数据文件 ← 哪个生成器 ← 读什么。

**判据从 `regen_all.sh` 的 `run` 行解析**（那是「谁生成谁」的唯一权威记录），
不另写一份映射 —— 两份必然分叉。
用法: python3 build_claims_doc.py > CLAIMS.md   （在 artifact 根目录跑）
"""
import os, re, sys, glob

def _reads_results(txt):
    """这个生成器读不读 `results/` 下的东西？

    ⚠⚠ 2026-09-28（r66 中立复核）：原来两处判据都是裸子串 `"results" in …`。
    于是 `gen_table.py`（正文里印的 LaTeX 标签 `sec_results:aimd`）与
    `gen_wall_split.py`（docstring 里提到 `sec_results`）都被判成「读 results」，
    而它们**一个 results 下的文件都没读**（复核者用审计钩子逐次 open 实测过）。
    错的方向是「把输入说得更宽」，对复现无害，但交付文档里那句话是假的。
    ⇒ 收紧成**路径/变量形态**：`results/night`、`RESULTS`（run 行的 `$RESULTS`）、
      `<results_dir>`（argv 约定）、或带引号的 `"results"`（`os.path.join(…, "results", …)`）。
    """
    for t in ("results/night", "RESULTS", "results_dir", '"results"', "'results'"):
        if t in txt:
            return True
    return False


root = "."
regen_p = os.path.join(root, "scripts", "lab", "regen_all.sh")
if not os.path.exists(regen_p):
    sys.exit("!! 找不到 %s（请在 artifact 根目录跑）" % regen_p)
txt = open(regen_p, encoding="utf-8").read()

# `run <名字> <输出[,输出]> $P scripts/lab/<生成器> …`（空格数不定、行尾可能有 `\`）
gen_of = {}
for m in re.finditer(r"^\s*run\s+(\S+)\s+(\S+\.csv(?:,\S+\.csv)*)\s+\$P\s+scripts/lab/(\S+\.py)",
                     txt, re.M):
    for o in m.group(2).split(","):
        gen_of[o] = m.group(3)

out = ["""# Where each number comes from

Every number the paper quotes has a row in one of the 48 files under
`paper/data/`. This table says, for each file, which generator produces it and
what that generator reads. Regenerate with
`python3 scripts/lab/build_claims_doc.py`.

The generator column is authoritative: it is parsed from `regen_all.sh`, the
one place that records which script writes which file. Run a generator as
`python3 scripts/lab/<generator> <args>` from the artifact root. Most carry their usage line in the
module docstring, but that is not a guarantee: of the 44 generators, 38 exit
non-zero when given no arguments. Three files are marked *frozen input* — their
content depends on which runs had finished when they were produced, so they
are carried rather than regenerated (see `README.md`).

| Data file | Generator | Reads |
|---|---|---|"""]

# ⚠⚠ 2026-09-27（r61 中立复核）—— **这是【已修好】的历史记录，不是现状**：
# **原来**标题与说明段建在 `out` 里、然后从不打印，于是交付的 `CLAIMS.md`
# 直接从表格行开始（没有标题、没有「怎么跑生成器」的说明）。与 `pack_artifact.py`
# 那个 MANIFEST bug 同形：东西建好了，dump 时漏掉。
# **下面这行 `print("\n".join(out))` 就是那次修复**（2026-09-28 r66 中立复核指出：
# 本仓库的惯例是在记录型注释里点出「原来」，这一处没写，下一个人可能会去「修」一个
# 已经修好的东西）。
print("\n".join(out))
print()
for f in sorted(os.path.basename(x) for x in glob.glob(os.path.join(root, "paper/data/*.csv"))):
    FROZEN = ("concurrency.csv", "gate_attrib.csv", "projection.csv")
    # ⚠ 少数表不由 `run` 行生成（`runs_precise.csv` 走 `frontier.py --csv`，
    # 由 `regen_all.sh` 里一个手工分支写；`projection_sat.csv` 不是交付件）。
    MANUAL = {"runs_precise.csv": "frontier.py --csv (a hand-written branch in regen_all.sh)"}
    g = ("**frozen input**" if f in FROZEN
         else MANUAL.get(f, gen_of.get(f, "—")))
    # ⚠⚠ 2026-09-27（r63 中立复核 5）：**`Reads` 原来是从生成器源码里带引号的
    # `*.csv` 字面量猜的** —— 而 `gen_horizon.py` / `idle_pooled` / `slope` 走的是
    # `sys.argv`，于是它们的 Reads 全印成 `—`（= 什么也不读），**四行是错的**。
    # 而**输入就写在 `regen_all.sh` 的 `run` 行里**（文档自己称它是唯一权威记录），
    # 却没被解析。⇒ 改成**先解析 `run` 行**，源码只作补充。
    reads = []
    # ⚠⚠ 2026-09-27（r64 codex 复核 4）：**`run` 调用有 `\` 续行**，而原来只取
    # `[^\n]*`（**第一行**）⇒ `toolwait` 的 trace、`a100` 的 `--csv` 全丢，
    # 至少 8 行的 Reads 是错的。⇒ **先把续行拼成一行**再解析。
    txt_flat = re.sub(r"\\\s*\n\s*", " ", txt)
    for m in re.finditer(r"^\s*run\s+(\S+)\s+(\S+\.csv(?:,\S+\.csv)*)\s+\$P\s+scripts/lab/(\S+\.py)([^\n]*)",
                         txt_flat, re.M):
        if f not in m.group(2).split(","):
            continue
        tail = m.group(4)
        if _reads_results(tail):
            reads.append("`results/night/` logs")
        for t in sorted(set(re.findall(r"data/(replay_\w+\.csv)", tail))):
            reads.append("`data/%s`" % t)
        _outs = set(m.group(2).split(","))          # 同一次运行的**输出**，不是输入
        for t in sorted(set(re.findall(r"paper/data/(\w+\.csv)", tail))):
            if t != f and t not in _outs:
                reads.append("`paper/data/%s`" % t)
        break
    # 源码兜底：**只看引号里的 `*.csv` 文件名**（不要求整条路径）——
    # 因为这些生成器多用 `os.path.join(HERE, "..", "..", "paper", "data", "decomp.csv")`
    # 拼路径，整条路径**不是**一个字面量（我第一版就是按整条路径找的，全落空）。
    gp = os.path.join(root, "scripts", "lab", g)
    if g.endswith(".py") and os.path.exists(gp):
        src = open(gp, encoding="utf-8").read()
        if _reads_results(src):
            reads.append("`results/night/` logs")
        # ⚠⚠ 2026-09-28（r65 中立复核）：`_outs` 原来**只加在 `run` 行那条分支上**，
        # 兜底分支没有 ⇒ `a100.csv` 把共同输出 `a100_elasticity.csv` 列成自己的输入。
        _co = {k for k, v in gen_of.items() if v == g}
        for t in sorted(set(re.findall(r'"([A-Za-z_0-9]+\.csv)"', src))):
            if t == f or t in _co:
                continue
            # ⚠⚠ 2026-09-28（r65 中立复核）：**「源码里有这个字面量」不等于「读它」**。
            # 构造：`TRACE_MAIN_SUFFIX = "replay_pois200_l04.csv"`（后缀常量）与
            # `_tr = {"replay_…", …}`（集合键）都被算成了输入，而它们**从不 open**。
            # ⇒ 判据：该字面量所在的**逻辑行**里有 `join(`/`open(`/`load(` 才算读。
            _ls = src.splitlines()
            # 「逻辑行」= 跨括号续行的物理行合并。**真读全是多行 `os.path.join` 的续行**
            # （`"..", "..", "data", "replay_…csv")` 自己那一行里没有 `join(`），
            # 所以只按物理行判会把真的读砍掉（第一版就是这么错的）。
            _dep, _st = 0, 0
            _starts = []
            for _L in _ls:
                if _dep <= 0:
                    _st = len(_starts)
                _starts.append(_st)
                _c = re.sub(r'"[^"]*"', '""', _L)
                _dep += sum(_c.count(c) for c in "([{") - sum(_c.count(c) for c in ")]}")
                if _dep < 0:
                    _dep = 0
            _hit = [i for i, L in enumerate(_ls) if '"%s"' % t in L]
            if not any(any(("join(" in L or "open(" in L or "load(" in L)
                           for L in _ls[_starts[i]:i + 1]) for i in _hit):
                continue
            if t.startswith("replay_"):
                if ("`data/%s`" % t) not in reads:
                    reads.append("`data/%s`" % t)
            elif os.path.exists(os.path.join(root, "paper/data", t)):
                if ("`paper/data/%s`" % t) not in reads:
                    reads.append("`paper/data/%s`" % t)
    print("| `%s` | `%s` | %s |" % (f, g, ", ".join(dict.fromkeys(reads)) or "—"))
