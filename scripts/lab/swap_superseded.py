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

改名只匹配【完整的旧名】，且**两种写法都匹配**（短名 `foyer_hz0` 与带目录前缀的
`pois200_foyer_hz0`）—— 规则与踩过的坑见 `_pat()` 的 docstring。右侧的 `\b` 保证
`foyer_hz0_r2` 里的 `foyer_hz0` 不会被二次改名（`_r2_r2` 是这里最容易犯的错）。

改完**不会**自动重生成数据文件：打印出该跑的生成器命令，由调用者按依赖顺序执行。
SUPERSEDED 名单（gen_eviction.py / gen_repeat_spread.py）也**不自动改** ——
那条要写明理由，理由因 run 而异，必须手写。
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN_DIRS = [HERE, os.path.join(HERE, "..", "..", "paper", "figs")]

# 只改这些后缀的文件，避免误伤 .md / .csv
EXTS = (".py",)


# 【只用于记录“谁被谁替代”的文件】—— 这些文件里的旧名是**定义**，不是 run 列表项，
# 改名会把它们改成「自己替代自己」。2026-09-25 就拿这个脚本改坏了 gen_superseded.py
# 的 PAIRS 与 gen_eviction.py 的 SUPERSEDED，是审查之外自己发现的。
NEVER_TOUCH = {"gen_superseded.py", "swap_superseded.py"}
# 同上，按【行内语境】判：SUPERSEDED 的定义块、以及注释。
DEF_CONTEXT = ("SUPERSEDED = {", "SUPERSEDED=")

# 【按文件+行内模式】判定的定义处 —— 上面两条按语境判不出来、但确实是定义的地方。
# 判据：这一行里的 run 名**不是「表里有哪几条」的列表项，而是「谁属于哪个语义集合」的成员**。
# 机械替换会把【干净重跑】塞进那个语义集合里，集合的名字就不再成立。
#
# 2026-09-25 由 codex 第 21 轮抓出：`gen_idle_pooled.py` 的
#     damaged = {"foyer_hz2", "foyer_hz0", "foyer_breshz1"}
# 是「被争用损害的【重跑前】那三条」这个定义本身 —— 不加这条，改完名会把
# foyer_hz0_r2（干净的那条）算成「受损」，而 minus_damaged3 那一行正是靠它排除受损臂的。
# 加名单时**只加证明得了是定义的**，拿不准就留成 run 并在 dry-run 里人工过一遍。
DEF_LINE = [
    ("gen_idle_pooled.py", r"^\s*damaged\s*="),
    # compare_rerun.py 的 docstring 里那两行是**用法示例**，写的正是「旧 run 新 run」这个对。
    # 按语境规则判不出来（docstring 不是 `#` 注释），于是被算成 run —— 改名会把它变成
    # `pois200_foyer_hz0_r2  pois200_foyer_hz0_r2`，即「自己替代自己」，
    # 正是这个脚本存在的理由。2026-09-25 在临时副本上跑 --apply 后人工核查时发现的。
    ("compare_rerun.py", r"^\s+pois200_\w+"),
]

# 三引号字符串的检测：**只用来在 dry-run 里加警示，不参与分类。**
# 理由是不对称 —— 把该改的 run 行误判成 definition，会让那个文件静默留在旧 run 上
# （生成器照样读得到旧数据、照样出数，正是纪律 3 那类事故）；把 docstring 里的示例
# 误判成 run，最坏只是示例变成自指。所以宁可提示人看，也不自动改判。
def _doc_lines(lines):
    """粗略标出处在三引号块里的行号（含首尾行）。不做转义处理 —— 本项目没有靠 \\" 藏引号的写法。"""
    inside, out, q = False, set(), None
    for i, line in enumerate(lines, 1):
        if not inside:
            for cand in ('"""', "'''"):
                if cand in line:
                    if line.count(cand) >= 2:
                        out.add(i)          # 单行 docstring，整行都算
                    else:
                        inside, q = True, cand
                        out.add(i)
                    break
        else:
            out.add(i)
            if q in line:
                inside, q = False, None
    return out


def _pat(old):
    """旧名的匹配式：**左边不能用 \\b，右边必须用 \\b**。

    右边：`_` 是词字符，所以 `foyer_hz0\\b` 不会命中 `foyer_hz0_r2` —— 这是防 `_r2_r2`
    那道保险，必须留。
    左边：**不能**用 `\\b`。这个项目的 run 名有两种写法 —— 短的 `foyer_hz0` 和
    带目录前缀的 `pois200_foyer_hz0` —— 而 `pois200_` 结尾是 `_`（词字符），
    `\\bfoyer_hz0` 在前面是 `_` 时**不成立**，于是带前缀的那些写法一处都匹配不到。
    2026-09-25 在临时副本上跑 --apply 时露出来的：`gen_backlog.py` / `gen_stall.py` /
    `gen_gate_attrib.py` 三个文件**在 dry-run 里根本没出现**，会静默留在旧的受污染 run 上
    （而旧 run 还在镜像里，生成器照样读得到、照样出数）。改成「前面不是字母数字」
    就两种写法都命中，且仍然排除 `xfoyer_hz0` 这类。
    """
    return re.compile(r"(?<![A-Za-z0-9])%s\b" % re.escape(old))


def sites(old):
    """列出所有含【完整旧名】的位置，并把每一处标成 run / comment / definition。

    **只有 `kind == "run"` 的会被 --apply 改**，其余要显式 --force 才动。
    """
    pat = _pat(old)
    out = []
    for d in SCAN_DIRS:
        d = os.path.abspath(d)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(EXTS):
                continue
            p = os.path.join(d, name)
            if name in NEVER_TOUCH:
                for i, line in enumerate(open(p, encoding="utf-8"), 1):
                    if pat.search(line):
                        out.append((p, i, line.rstrip(), "definition"))
                continue
            lines = open(p, encoding="utf-8").read().split("\n")
            doc = _doc_lines(lines)
            for i, line in enumerate(lines, 1):
                m = pat.search(line)
                if not m:
                    continue
                if line.lstrip().startswith("#") or ("#" in line[:m.start()]):
                    kind = "comment"
                elif any(re.search(rx, line) for fn, rx in DEF_LINE if fn == name):
                    kind = "definition"
                elif any(c in "\n".join(lines[max(0, i - 30):i]) for c in DEF_CONTEXT):
                    kind = "definition"
                else:
                    kind = "run"
                if i in doc and kind == "run":
                    kind = "run?"
                out.append((p, i, line.rstrip(), kind))
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
    ("fit.csv",          "python3 scripts/lab/gen_fit.py paper/data paper/data/fit.csv  # §III 的 r 与最大残差"),
    ("stall.csv",        "python3 scripts/lab/gen_stall.py results/night paper/data/stall.csv"),
    ("slo_sensitivity.csv", "python3 scripts/lab/slo_sensitivity.py results/night paper/data/slo_sensitivity.csv"),
    ("— 以下必须在实验机上跑 —", ""),
    ("concurrency.csv",  "实验机：gen_concurrency.py <results>/night <out>（判据是同时几条车道）"),
    ("gate_attrib.csv",  "实验机：gen_gate_attrib.py <results>/night <out>（只算跑完的 run）"),
    ("projection.csv",   "实验机：gen_projection.py <results>/night <out>"),
    ("repeat_spread.csv","实验机：gen_repeat_spread.py <results>/night <out>"),
    ("loadtier.csv",     "python3 scripts/lab/gen_loadtier.py results/night paper/data/table1.csv paper/data/loadtier.csv"),
    ("horizon.csv",      "python3 scripts/lab/gen_horizon.py paper/data/table1.csv paper/data/horizon.csv"),
    ("a100.csv",         "python3 scripts/lab/gen_a100.py data/replay_pois200_l04.csv results/night results/night paper/data/a100.csv "
                         "# ⚠ 会同时重写 a100_elasticity.csv；本地必须已有 a100_cap1..5，否则静默丢行"),
    ("pool50.csv",       "python3 scripts/lab/gen_pool50.py results/night paper/data/pool50.csv "
                         "# 还在跑的 run 用 --pending=<name> 声明；真缺会报错退出"),
    ("a100_delta.csv",   "python3 scripts/lab/gen_a100_delta.py paper/data/a100.csv results/night --csv paper/data/a100_delta.csv a100_foyer_hz2"),
    ("图",               "python3 paper/figs/make_figs.py"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="连注释与 SUPERSEDED 定义行一起改（默认不改）")
    a = ap.parse_args()
    if not (a.dry_run ^ a.apply):
        sys.exit("必须二选一：--dry-run 或 --apply")

    hit = sites(a.old)
    nrun = sum(1 for *_, k in hit if k in ("run", "run?"))
    nq = sum(1 for *_, k in hit if k == "run?")
    print("完整旧名 `%s` 出现在 %d 处（其中 run 列表 %d 处，其余是注释/定义）："
          % (a.old, len(hit), nrun))
    for p, i, line, kind in hit:
        print("  [%-10s] %-40s %4d  %s" % (kind, os.path.relpath(p), i, line.strip()[:84]))
    if not hit:
        print("  （没有 —— 要么已经改过，要么名字写错了）")
    if nq:
        print("\n⚠ 有 %d 处标了 run?：它们**在三引号字符串里**（docstring），已被当成 run。"
          "\n  请人看一眼 —— 如果那行是「旧 run 新 run」这种成对示例，它其实是定义，"
          "\n  要加进 DEF_LINE；如果是普通列表，就不用管。" % nq)
    if not a.force and any(k not in ("run", "run?") for *_, k in hit):
        print("\n⚠ 上面标 comment/definition 的那些**不会**被改 —— 它们里的旧名是文档或"
              "\n  「谁被谁替代」的定义，改了会变成自己替代自己。确实要改就加 --force。")

    if a.dry_run:
        print("\n--dry-run：什么都没改。")
    else:
        pat = _pat(a.old)
        changed = 0
        if not a.force:
            pat_line = pat
            for p in {p for p, _, _, _ in hit}:
                lines = open(p, encoding="utf-8").read().split("\n")
                # `run?` 也算 run：它只是「这行在三引号块里，请人复核」的提示，
                # 不是「别改」。让它不被改就成了静默跳过 —— 那是危险的那个方向。
                run_lines = {hi for hp, hi, _, hk in hit
                             if hp == p and hk in ("run", "run?")}
                out, n = [], 0
                for i, line in enumerate(lines, 1):
                    if i in run_lines and pat_line.search(line):
                        out.append(pat_line.sub(a.new, line)); n += 1
                    else:
                        out.append(line)
                if n:
                    body = "\n".join(out)
                    # 断言必须【正着写】：改完这一处，剩下来的旧名应当恰好是
                    # 「非 run 类」的那些。2026-09-25 这里写反了 ——
                    # 原句是 `pat_line.search(body) is not None`，即「改完还得含有旧名」，
                    # 于是「所有出现处都是 run 类」的文件必然断言失败；而文件是逐个写的，
                    # 前面的已经落盘 → 留下【部分改名】，正是最难查的那种坏法。
                    # 是 codex 第 21 轮在 --dry-run 里发现的（hz0/hz2 各有 15 个文件会踩中）。
                    assert isinstance(body, str)
                    left = len(pat_line.findall(body))
                    # 第三版（2026-09-25）。第二版写的是 `left == len(run_lines) - n`，
                    # 它**隐含假设「只有 run 类行含旧名」** —— 但注释行也含
                    # （gen_eviction.py:203 的 `# foyer_breshz1（它 host 接住 14.4M…）`）。
                    # 于是「run 类行 + 注释行」的文件必然断言失败；而写入是**逐文件**做的、
                    # 遍历又是 set 的**哈希序**，中止点落在哪儿不确定 →
                    # 留下【任意位置的半改】，比全不改更难查。
                    # 按「非 run 类行原本的旧名数」正着写，就没有那个隐含假设：
                    # 多出来说明有 run 类行没改到，少了说明改坏了非 run 类行。
                    keep = sum(len(pat_line.findall(ln))
                               for i, ln in enumerate(lines, 1) if i not in run_lines)
                    assert left == keep, (
                        "%s：改完还剩 %d 处旧名，预期恰好 %d 处（非 run 类行原本的旧名数）"
                        " —— 多了=有 run 类行漏改，少了=改坏了非 run 类行"
                        % (os.path.relpath(p), left, keep))
                    assert len(out) == len(lines), "%s：行数变了" % os.path.relpath(p)
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(body)
                    print("  改 %-46s %d 行（只动 run 列表）" % (os.path.relpath(p), n))
            print("\n（未加 --force：注释与 definition 行原样保留）")
            _report(a)
            return
        for p in {p for p, _, _, _ in hit}:
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

    _report(a)


def _report(a):
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
