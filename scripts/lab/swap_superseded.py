#!/usr/bin/env python3
"""把一条【被争用作废】的旧 run 换成它的干净重跑 —— 生成器一侧的机械改动。

为什么要有这个脚本：2026-09-25 把 `foyer_bres` 换成 `foyer_bres_r2` 时，
改名散落在 **11 个脚本的 15 处**（`gen_runs` / `gen_table` / `gen_occupancy` /
`gen_arm_running`×2 / `gen_attribution` / `gen_stall` / `gen_gate_attrib`×2 /
`slo_sensitivity`×4 / `idle_segments` / `gen_idle_pooled` / `gen_eviction`）。
漏一处不会报错，只会让某个数据文件里那条臂**悄悄变回旧的**或**整个消失** ——
正是 CLAUDE.md 纪律 3 记的那类事故。后面还有三条臂（hz0/hz2/breshz1）要走同一条路。

用法（**先 --dry-run**）:
    python3 scripts/lab/swap_superseded.py foyer_hz0 foyer_hz0_r2 --dry-run
    python3 scripts/lab/swap_superseded.py foyer_hz0 foyer_hz0_r2 --apply

改名只匹配【完整的旧名】（`\\b` 在 Python 里不跨 `_`，所以 `foyer_hz0_r2` 里的
`foyer_hz0` 不会被二次改名 —— `_r2_r2` 是这里最容易犯的错）。

改完**不会**自动重生成数据文件：打印出该跑的生成器命令，由调用者按依赖顺序执行。
SUPERSEDED 名单（gen_eviction.py / gen_repeat_spread.py）也**不自动改** ——
那条要写明理由，理由因 run 而异，必须手写。
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN_DIRS = [HERE, os.path.join(HERE, "..", "..", "paper", "figs")]

# 只改这些后缀的文件，避免误伤 .md / .csv
EXTS = (".py",)


def sites(old):
    """列出所有含【完整旧名】的位置。用 \b 而不是子串：`_` 是词字符，
    所以 `\bfoyer_hz0\b` 不会命中 `foyer_hz0_r2`。"""
    pat = re.compile(r"\b%s\b" % re.escape(old))
    out = []
    for d in SCAN_DIRS:
        d = os.path.abspath(d)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(EXTS):
                continue
            if os.path.abspath(os.path.join(d, name)) == os.path.abspath(__file__):
                continue   # 别改自己（docstring 里举例会命中）
            p = os.path.join(d, name)
            for i, line in enumerate(open(p, encoding="utf-8"), 1):
                if pat.search(line):
                    out.append((p, i, line.rstrip()))
    return out


# 重生成命令按【依赖顺序】排：上游先出，下游才能读到新的集合。
REGEN = [
    ("runs_precise.csv", "TURNSTILE_RESULTS=results/night python3 scripts/lab/frontier.py --csv > paper/data/runs_precise.csv"),
    ("runs.csv",         "python3 scripts/lab/gen_runs.py results/night paper/data/runs.csv"),
    ("table1.csv",       "python3 scripts/lab/gen_table.py paper/data/runs.csv --csv paper/data/table1.csv"),
    ("occupancy.csv",    "python3 scripts/lab/gen_occupancy.py results/night paper/data/occupancy.csv"),
    ("decomp.csv",       "python3 scripts/lab/gen_decomp.py results/night paper/data/decomp.csv <pois200_ 前缀的 run 列表>"),
    ("arm_running.csv",  "python3 scripts/lab/gen_arm_running.py results/night paper/data/arm_running.csv"),
    ("hitrate.csv",      "python3 scripts/lab/gen_hitrate.py results/night paper/data/hitrate.csv <pois200_ 前缀的 run 列表>"),
    ("eviction.csv",     "python3 scripts/lab/gen_eviction.py results/night paper/data/eviction.csv"),
    ("reuse.csv",        "python3 scripts/lab/gen_reuse.py data/replay_pois200_l04.csv paper/data/eviction.csv "
                         "paper/data/arm_running.csv paper/data/decomp.csv paper/data/reuse.csv paper/data/concurrency.csv"),
    ("attribution.csv",  "python3 scripts/lab/gen_attribution.py paper/data/runs.csv paper/data/occupancy.csv "
                         "paper/data/decomp.csv paper/data/attribution.csv"),
    ("idle_seg.csv",     "python3 scripts/lab/idle_segments.py results/night paper/data/idle_seg.csv  # 同时写 idle_seg_raw.csv"),
    ("idle_pooled.csv",  "python3 scripts/lab/gen_idle_pooled.py paper/data/idle_seg_raw.csv paper/data/concurrency.csv paper/data/idle_pooled.csv"),
    ("stall.csv",        "python3 scripts/lab/gen_stall.py results/night paper/data/stall.csv"),
    ("slo_sensitivity.csv", "python3 scripts/lab/slo_sensitivity.py results/night paper/data/slo_sensitivity.csv"),
    ("— 以下必须在实验机上跑 —", ""),
    ("concurrency.csv",  "实验机：gen_concurrency.py <results>/night <out>（判据是同时几条车道）"),
    ("gate_attrib.csv",  "实验机：gen_gate_attrib.py <results>/night <out>（只算跑完的 run）"),
    ("projection.csv",   "实验机：gen_projection.py <results>/night <out>"),
    ("repeat_spread.csv","实验机：gen_repeat_spread.py <results>/night <out>"),
    ("图",               "python3 paper/figs/make_figs.py"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if not (a.dry_run ^ a.apply):
        sys.exit("必须二选一：--dry-run 或 --apply")

    hit = sites(a.old)
    print("完整旧名 `%s` 出现在 %d 处：" % (a.old, len(hit)))
    for p, i, line in hit:
        print("  %-46s %4d  %s" % (os.path.relpath(p), i, line.strip()[:96]))
    if not hit:
        print("  （没有 —— 要么已经改过，要么名字写错了）")

    if a.dry_run:
        print("\n--dry-run：什么都没改。")
    else:
        pat = re.compile(r"\b%s\b" % re.escape(a.old))
        changed = 0
        for p in {p for p, _, _ in hit}:
            s = open(p, encoding="utf-8").read()
            n = len(pat.findall(s))
            s2 = pat.sub(a.new, s)
            assert isinstance(s2, str) and len(s2) > 0
            assert pat.search(s2) is None, "%s 改完还剩 %s" % (p, a.old)
            with open(p, "w", encoding="utf-8") as f:
                f.write(s2)
            print("  改 %-46s %d 处" % (os.path.relpath(p), n))
            changed += n
        print("\n共改 %d 处。" % changed)

    print("\n接下来按依赖顺序重生成（本脚本不代跑）：")
    for name, cmd in REGEN:
        print("  %-22s %s" % (name, cmd))
    print("""
⚠ 手写项（脚本故意不动）：
  1. gen_eviction.py 的 SUPERSEDED 加 `%s`，写明为什么被替代；
  2. gen_repeat_spread.py 的 SUPERSEDED 同样加一条；
  3. paper/data/runs.csv 之外，正文里表 I 那一行、‡ 脚注、归因表、§III 的例证、
     §VI 的阈值敏感性、§II 的「超过 295 分钟的变体」等 —— 见
     docs/finding_rerun_bres_20260925.md 的 12 条清单；
  4. 跑完 check_paper_numbers.py，0 MISS 才算完。""" % a.old)


if __name__ == "__main__":
    main()
