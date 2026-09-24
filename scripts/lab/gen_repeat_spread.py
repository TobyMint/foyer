#!/usr/bin/env python3
"""同一配置的重复 run 之间的墙钟散布 —— paper/data/repeat_spread.csv。

论文 §VI 说「我们报告的 14.3% 差距不当作输，因为这台机器上跨配置与档位的
run-to-run 墙钟散布可达 22.4%」。这个 22.4% 原先是 `xtrace_validation.md` 里
手工算的（不在任何数据文件里），属于「数字追不到源头」那一类。

判据（写死）：把 results 目录下**同 policy + 同 trace**、落地 ≥2 条的 run 归为一组，
按墙钟取 (max-min)/mean。**必须在实验机上跑**：它是对 run 集合计数，本地镜像不全会
少组、把上限压低（这正是 2026-09-24 栽过的那类）。

用法（实验机）: python3 gen_repeat_spread.py <results_dir> <out.csv>
"""
import csv, glob, json, os, statistics as sys_st, sys

MIN_RUNS = 40   # 最少要看到这么多带 metadata 的 run，否则拒跑（镜像不全的信号）

# 【争用作废】的旧测量：它们与自己的 _r2 是同一 policy，会天然归成一组，
# 而那一组算出来的不是 run-to-run 噪声，是【污染 vs 干净】的差 —— 拿它当
# 「重复散布」会把上限抬高、把这张表想量的东西量错。判据与 gen_eviction.py
# 的 SUPERSEDED 同一份名单，理由同源（docs/finding_concurrency_contamination_20260924.md）。
# 该 pair 的差值本身照旧引用（§discussion 用它证明体积列看不出污染），
# 只是不进这张表。
SUPERSEDED = {"pois200_foyer_bres", "pois200_foyer_hz0"}


def one(d):
    """分组键必须把【配置与代码代】也带上。

    第一版只用 (policy, trace)，于是把 `static=4` 的 device-only 与 +HiCache 两条、
    以及不同代码代的 run 归成一组，算出 58.2% 的「散布」——那不是 run-to-run 噪声，
    是配置与代码代的差异。判据要的是【同一配置、同一代码代】的重复。
    """
    m = json.load(open(d))
    code = m.get("code") or {}
    # 代码代指纹：controller_budget3 + session_runner + run_matrix 的哈希拼起来
    # 用【整个 code 块】当指纹：不同代码代的键集合本身就不一样（老 run 没有
    # controller_foyer.py 等），写死键名会得到半空指纹，把本该同代的 run 拆散。
    fp = "|".join("%s=%s" % (k, code[k]) for k in sorted(code))
    hc = bool((m.get("build") or {}).get("hicache_enabled"))
    # 分组只用 (policy, trace, HiCache)；代码指纹不定，只作为「这一组是否同代码代」的标注。
    return (m.get("policy"), os.path.basename(m.get("trace") or ""), hc), fp, m.get("wall_s")


def main():
    root, out_p = sys.argv[1], sys.argv[2]
    n_dirs = len(glob.glob(os.path.join(root, "*", "metadata.json")))
    assert n_dirs >= MIN_RUNS, (
        "只有 %d 个 run 目录（需要 >=%d）—— 这多半是部分镜像，本脚本要在实验机上跑。"
        % (n_dirs, MIN_RUNS))
    groups = {}
    skipped, superseded = [], []
    for d in sorted(glob.glob(os.path.join(root, "*", "metadata.json"))):
        run = os.path.basename(os.path.dirname(d))
        if run.startswith("_"):
            continue
        if run in SUPERSEDED:
            superseded.append(run)
            continue
        # 只算【跑完的】run：中止/超时的 run（如 _timedout_591steps）进组会把
        # 「散布」算成 58%（第一版就是这样），那不是噪声是事故。
        if not os.path.exists(os.path.join(os.path.dirname(d), "summary.json")):
            skipped.append(run)
            continue
        try:
            key, fp, wall = one(d)
        except Exception:
            continue
        if not key[0] or not key[1] or not wall:
            continue
        groups.setdefault(key, []).append((run, float(wall), fp))
    rows = []
    for (pol, tr, hc), runs in sorted(groups.items()):
        if len(runs) < 2:
            continue
        w = [x for _, x, _ in runs]     # wall_s（秒）——与论文别处用分钟不同，这里只算比例
        spread = 100.0 * (max(w) - min(w)) / (sum(w) / len(w))
        same_gen = len({fp for _, _, fp in runs}) == 1 and runs[0][2].strip("|")
        rows.append(dict(policy=pol + ("+HC" if hc else ""), trace=tr, n=len(runs),
                         same_code_gen="Y" if same_gen else "N",
                         wall_min_min="%.2f" % (min(w) / 60), wall_min_max="%.2f" % (max(w) / 60),
                         # 两位小数：论文 §VI 引的是「1.6%」与「0.02%」，
                         # 一位小数会把后者印成 0.0%（2026-09-25 codex 抓到的追溯缺口）。
                         spread_pct="%.2f" % spread,
                         runs=" ".join(r for r, _, _ in runs)))
    rows.sort(key=lambda r: -float(r["spread_pct"]))
    # 供论文引用的两个端点：两条 trace 上的重复对与全表
    _tr = {"replay_pois200_l04.csv", "replay_realhr.csv"}
    _two = [float(r["spread_pct"]) for r in rows if r["trace"] in _tr]
    if _two:
        print("   两条 trace 上的重复对：%d 组，min %.2f%%、max %.2f%%"
              % (len(_two), min(_two), max(_two)))
    print("%-42s %-30s %3s %8s  %s" % ("policy", "trace", "n", "散布%", "runs"))
    for r in rows:
        print("%-42s %-30s %3d %8s  %s" % (r["policy"][:42], r["trace"][:30], r["n"],
                                           r["spread_pct"], r["runs"][:60]))
    sp = [float(r["spread_pct"]) for r in rows]
    hdr = ["# 同 policy + 同 trace 的重复 run 之间的墙钟散布 —— gen_repeat_spread.py 生成（实验机上跑）",
           "# 判据：同 policy + 同 trace 且落地 >=2 条；散布 = (max-min)/mean，单位 %。",
           "# 论文 §VI 引的上限（跨配置与档位）就是本表的 max；全表 %d 组，min %.1f%%、max %.2f%%。"
           % (len(rows), min(sp), max(sp)),
           "# 分组键 = policy + trace + HiCache，只算【跑完的】run；same_code_gen 标注该组是否同代码代",
           "#   （代码在两次之间会变，所以精确同代的分组太稀疏 —— 上界因此含少量代码漂移）。",
           "# 不进表：被争用作废的旧测量（%s）—— 它与 _r2 同 policy 但不同类，" % " ".join(sorted(SUPERSEDED)),
           "policy,trace,n,same_code_gen,wall_min_min,wall_min_max,spread_pct,runs"]
    body = "\n".join(hdr) + "\n" + "\n".join(
        "%s,%s,%d,%s,%s,%s,%s,\"%s\"" % (r["policy"], r["trace"], r["n"], r["same_code_gen"],
                                         r["wall_min_min"], r["wall_min_max"],
                                         r["spread_pct"], r["runs"]) for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as f:
        f.write(body)
    print("-> %s（%d 组；min %.1f%% max %.1f%%）；跳过 %d 条（未跑完或无 code 块）"
          % (out_p, len(rows), min(sp), max(sp), len(skipped)))


if __name__ == "__main__":
    main()
