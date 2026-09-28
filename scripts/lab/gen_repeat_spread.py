#!/usr/bin/env python3
"""同一配置的重复 run 之间的墙钟散布 —— paper/data/repeat_spread.csv。

论文 §VI 说「我们报告的 14.3% 差距不当作输，因为这台机器上跨配置与档位的
run-to-run 墙钟散布可达 22.4%」。这个 22.4% 原先是 `xtrace_validation.md` 里
手工算的（不在任何数据文件里），属于「数字追不到源头」那一类。

判据（写死）：把 results 目录下**同 policy + 同 trace + 同 HiCache + 同池子**、
落地 ≥2 条的 run 归为一组，按墙钟取 (max-min)/mean。**必须在实验机上跑**：它是对
run 集合计数，本地镜像不全会少组、把上限压低（这正是 2026-09-24 栽过的那类）。

⚠ 分组键的三个轴都是【配置】，漏一个就会把两次不同的配置当成重复：
  - 代码代 → 第一版漏了，device-only 与 +HC 混组算出 58.2%；
  - HiCache（=上一条的修法，但没推广）；
  - **池子** → 2026-09-25 漏了：`static=4` 的全池 `pois200_cap4` 与半池
    `pois200_cap4_hp` 同 policy、同 trace、同无 HiCache，混成一组算出 **71.47%**，
    把本表上限从 21.96% 顶到 71.47% —— 而论文 §VI 引的正是那个上限。
    同一天 `static=2` 也中招（全池 cap2 配半池 cap2_hp，5.70%）。
    半池那两条还是**因果实验**的对照，把它们当重复，等于把这张表想量的东西量错。
  - **驱逐政策** → 2026-09-27 漏了：`foyer_hc_slru` 与 `foyer_hc`/`foyer_hc_r2`/
    `pairA_foyerhc`/`pairB_foyerhc` 的 **policy 串逐字相同**
    （`budget3:hw=0;target=0.95`）、trace 同、HiCache 同、池子同 ——
    **唯一差别是 server 命令行多一个 `--radix-eviction-policy slru`**，
    而那一格藏在 `build.TURNSTILE_HICACHE_ARGS` 里。不把它当成一根轴，
    这一组就会把「换了驱逐政策的对照」算成「同一配置的重复」，
    正是上面 71.47% 那个病的同一个形状（那次漏的是池子，这次漏的是驱逐政策）。
    ⚠ 轴的值是**机械读出来的**（`--radix-eviction-policy <v>`），读不到就是字面
    `unset` —— 不写「lru」，因为那是**引擎默认值**的断言，不是这份记录的取值。

用法（实验机）: python3 gen_repeat_spread.py <results_dir> <out.csv>
"""
import csv, glob, json, os, re, statistics as sys_st, sys

MIN_RUNS = 40   # 最少要看到这么多带 metadata 的 run，否则拒跑（镜像不全的信号）

# 【争用作废】的旧测量：它们与自己的 _r2 是同一 policy，会天然归成一组，
# 而那一组算出来的不是 run-to-run 噪声，是【污染 vs 干净】的差 —— 拿它当
# 「重复散布」会把上限抬高、把这张表想量的东西量错。判据与 gen_eviction.py
# 的 SUPERSEDED 同一份名单，理由同源（docs/finding_concurrency_contamination_20260924.md）。
# 该 pair 的差值本身照旧引用（§discussion 用它证明体积列看不出污染），
# 只是不进这张表。
SUPERSEDED = {"pois200_foyer_bres", "pois200_foyer_hz0", "pois200_foyer_hz2",
              "pois200_foyer_breshz1",
              }

# 池子容差，与 CLAUDE.md 的「KV pool 必须落在 101,432 ± 20」同源：同配置的重复
# 之间池子本来就有微小差（SGLang 按启动时的空闲显存定池子），差在 20 以内视为
# 同一配置；差得多的是【两次不同的配置】（半池实验故意把池子减半），不算重复。
POOL_TOL = 20


def cluster_by_pool(runs):
    """把同一 (policy, trace, HiCache) 下的 run 再按【池子】分一次。

    runs 元素是 (run, wall_s, fp, pool)。按池子排序后贪心聚类：与簇内最小池子
    相差 > POOL_TOL 就另起一簇。run 数很少（<=4），贪心足够；用它而不是
    「把池子四舍五入进桶」，是因为桶边界会把一对合法重复拆开、静默丢掉一组。
    池子读不到的（老 run 没有这个字段）记 0，它们自己成一簇，行为与改动前一致。
    """
    out, cur = [], []
    for r in sorted(runs, key=lambda x: x[3] or 0):
        if cur and (r[3] or 0) - (cur[0][3] or 0) > POOL_TOL:
            out.append(cur)
            cur = []
        cur.append(r)
    if cur:
        out.append(cur)
    return out


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
    # ⚠ hicache_enabled 对**一半的 run 根本不存在**（2026-09-25 实测 78/155，含正文引用的
    # pois200_cap2 / pois200_cap4 / cap4 / realhr_cap2）。老 run 的 metadata 里没有任何
    # HiCache 记录，字段缺失与 False 在下面被当成同一个值。
    # 不按【run 名字里的 _hc】去补：那是把命名约定当科学事实（本项目栽过：`no hw`
    # 不是 no HiCache，是 high-water）。也不按 None/False 拆组：那样会把「一条记了字段、
    # 一条没记」的合法重复对拆散，比现在更坏。**只披露** —— hc_src 列标出这一组的
    # HiCache 记录来自哪里，unknown 的组可能混了 HC 与 device-only。
    _b = m.get("build") or {}
    hc = bool(_b.get("hicache_enabled"))
    hc_src = "meta" if "hicache_enabled" in _b else "unknown"
    # ⚠ 驱逐政策是**配置的第四根轴**（见模块 docstring 最后一条）。从
    # `build.TURNSTILE_HICACHE_ARGS` 里机械读 `--radix-eviction-policy <v>`；
    # 读不到一律记字面 `unset`（**不猜引擎默认值** —— 那是另一个断言）。
    # 为什么必须进分组键：`foyer_hc_slru` 与 `foyer_hc` 的 policy 串逐字相同，
    # 不进键就会被算成「同一配置的重复」。
    _evm = re.search(r"--radix-eviction-policy[=\s]+(\S+)",
                     str(_b.get("TURNSTILE_HICACHE_ARGS") or ""))
    ev = _evm.group(1) if _evm else "unset"
    # 分组用 (policy, trace, HiCache, 驱逐政策, 池子)；池子在 cluster_by_pool 里按 POOL_TOL
    # 再分。代码指纹不定，只作为「这一组是否同代码代」的标注。
    return ((m.get("policy"), os.path.basename(m.get("trace") or ""), hc, ev),
            fp, m.get("wall_s"), m.get("pool_tokens"), hc_src)


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
            key, fp, wall, pool, hc_src = one(d)
        except Exception:
            continue
        if not key[0] or not key[1] or not wall:
            continue
        groups.setdefault(key, []).append((run, float(wall), fp, pool, hc_src))
    rows = []
    for (pol, tr, hc, ev), runs in sorted(groups.items()):
        for cl in cluster_by_pool(runs):
            if len(cl) < 2:
                continue
            w = [x for _, x, _, _, _ in cl]  # wall_s（秒）——与论文别处用分钟不同，这里只算比例
            spread = 100.0 * (max(w) - min(w)) / (sum(w) / len(w))
            same_gen = len({fp for _, _, fp, _, _ in cl}) == 1 and cl[0][2].strip("|")
            _pools = [p for _, _, _, p, _ in cl if p]
            _srcs = {s for _, _, _, _, s in cl}
            rows.append(dict(policy=pol + ("+HC" if hc else ""), trace=tr, n=len(cl),
                             # ⚠ 驱逐政策也要印出来（同 `pool` 的理由：分组键含它，
                             # 读者必须能自己判断两条 run 是不是同一个配置）。
                             ev=ev,
                             hc_src=("meta" if _srcs == {"meta"} else
                                     "unknown" if _srcs == {"unknown"} else "mixed"),
                             # 池子必须印出来：本表的分组键含它，读者要能看出这一组是哪一次
                             # 配置。区间（min~max）也要给，否则「同池子」只是脚本的说法。
                             pool=("%d~%d" % (min(_pools), max(_pools))) if _pools else "?",
                             same_code_gen="Y" if same_gen else "N",
                             wall_min_min="%.2f" % (min(w) / 60),
                             wall_min_max="%.2f" % (max(w) / 60),
                             # 两位小数：论文 §VI 引的是「1.6%」与「0.02%」，
                             # 一位小数会把后者印成 0.0%（2026-09-25 codex 抓到的追溯缺口）。
                             spread_pct="%.2f" % spread,
                             runs=" ".join(r for r, _, _, _, _ in cl)))
    # 自检：分组键里的每一轴都真的分开了。若同一 (policy, trace, hc, 池子) 的组里
    # 出现跨池子的成员，说明聚类没生效 —— 那正是 2026-09-25 的 71.47% 那个 bug。
    for r in rows:
        if r["pool"] == "?":
            continue
        _lo, _hi = (int(x) for x in r["pool"].split("~"))
        assert _hi - _lo <= POOL_TOL, (
            "%s / %s：组内池子跨度 %d 超过容差 %d（%s）—— 聚类失效，"
            "这一组算出来的不是 run-to-run 噪声" % (r["policy"], r["trace"], _hi - _lo,
                                                     POOL_TOL, r["runs"]))
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
           "# 判据：同 policy + 同 trace + 同 HiCache + 同驱逐政策 + 同池子 且落地 >=2 条；散布 = (max-min)/mean，单位 %。",
           "# 论文 §VI 引的上限（跨配置与档位）就是本表的 max；全表 %d 组，min %.1f%%、max %.2f%%。"
           % (len(rows), min(sp), max(sp)),
           "# 分组键 = policy + trace + HiCache + 驱逐政策 + 池子（池子按 ±%d 聚类），只算【跑完的】run；" % POOL_TOL,
           "#   same_code_gen 标注该组是否同代码代（代码在两次之间会变，所以精确同代的分组太稀疏），",
           "#   pool 列给出该组的池子区间 —— 缺了它，读者无法判断两条 run 是不是同一个配置。",
           "#   ev 列给出该组的驱逐政策（从 build.TURNSTILE_HICACHE_ARGS 里机械读，"
           "读不到记字面 unset）——",
           "#     它是 2026-09-27 补的第四根轴：foyer_hc_slru 与 foyer_hc 的 policy 串逐字相同，",
           "#     只差 --radix-eviction-policy slru，不进键就会被当成「同一配置的重复」。",
           "# 不进表：被争用作废的旧测量（%s）—— 它与 _r2 同 policy 但不同类，" % " ".join(sorted(SUPERSEDED)),
           "# ⚠ hc_src=unknown 的组：那一组的 run 的 metadata 里【没有】hicache_enabled 字段",
           "#   （老 run，2026-09-25 实测 78/155 缺该字段），因此这一组可能把 +HiCache 与",
           "#   device-only 混在一起 —— 名字里的 _hc 只是线索不是证据，不能据此改分组。",
           "#   全表只在 policy 列显示 +HC，hc_src=unknown 的行【不代表】该组是 device-only。",
           "policy,trace,n,pool,ev,hc_src,same_code_gen,wall_min_min,wall_min_max,spread_pct,runs"]
    # ⚠ 手拼表头 + 手拼行：**加列时两处都要改**（本项目记过一次）。
    body = "\n".join(hdr) + "\n" + "\n".join(
        "%s,%s,%d,%s,%s,%s,%s,%s,%s,%s,\"%s\"" % (r["policy"], r["trace"], r["n"], r["pool"],
                                                  r["ev"],
                                                  r["hc_src"], r["same_code_gen"],
                                                  r["wall_min_min"], r["wall_min_max"],
                                                  r["spread_pct"], r["runs"]) for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as f:
        f.write(body)
    print("-> %s（%d 组；min %.1f%% max %.1f%%）；跳过 %d 条（未跑完或无 code 块）"
          % (out_p, len(rows), min(sp), max(sp), len(skipped)))


if __name__ == "__main__":
    main()
