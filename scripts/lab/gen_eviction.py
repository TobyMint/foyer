#!/usr/bin/env python3
"""生成 paper/data/eviction.csv —— 论文 §3.3 里「驱逐 → 重算」那条因果链的数据。

为什么要有这个脚本：这条链子曾经被错误地"反驳"过，用的两个检验都是恒等式：

  1. "total prefilled tokens == planned prefill, ratio 1.00"
     `sglang:prompt_tokens_total` 计的是**完整提交的 prompt 长度，含 cached 部分**，
     所以它恒等于 sum(prompt_len)，不管重算多少都不会变。这是个恒等式。
     能测出重算的是 `server_uncached_prompt_tokens`，本脚本报的就是它。

  2. "SGLang reports zero retractions"
     radix cache 驱逐记在 `sglang:evicted_tokens_total`；retraction 指的是
     抢占**正在跑**的请求，是另一件事、另一个计数器。拿后者反驳前者是范畴错误。

正确的读法（本脚本的输出）：
  - 设备侧未命中 = 设备没接住的量（prompt − cached_tokens_total）
  - 重算量 = steps 里的 server_uncached_prompt_tokens（真正重新 prefill 的）
  - 两者之差 = host 梯队接住的量
  - 无 HiCache 的五条：host 接住【精确为 0】，设备未命中 == 重算量，1:1
  - 有 HiCache 的八条：host 接住 13~19M
  - 但 HiCache 那一族的 τ 仍然散开（重算恒定 8.7M，τ 22.5~30.6ms）→ 未解释

用法: python3 gen_eviction.py <results_dir> <out.csv> [run ...]
"""
import csv, json, os, statistics, sys, glob

HEADER = ["run", "hicache", "prompt_M", "dev_miss_M", "host_hit_M", "uncached_M",
          "evicted_M", "running", "step_back_ms", "step_perreq_ms",
          # 下面三列是【未舍入】的原始计数，专供下游算比例用。
          # 为什么必须单列：曾经让下游拿舍入到 0.1M 的列去算百分比，cap1 于是印成
          # 69.8% 而真值是 19,934,847/28,526,871 = 69.9%（2026-09-24 审稿人从原始
          # 日志独立求和抓到的）。凡是要算比例的，一律走这三列。
          "prompt_tok", "reuse_tok", "uncached_tok",
          "dev_miss_tok", "host_hit_tok"]
SAMPLE_S = 5.0

# ── 集合的判据（2026-09-24 第 5 轮审查后写死）──────────────────────────────
# 这张表 + gen_reuse.py 产出的 reuse.csv 支撑正文那句「host tier 把兑现率守在
# 72.8–92.5%」。**集合必须能由判据机械地重算出来**，否则就是「集合没说清」——
# 上一版正是这样：正文写「十九条 host-tier run，含每一条控制器臂」，
# 而 `cap2_hc`（763 步）兑现 70.7%、`foyer_rg2`（770 步）兑现 67.1% 都被漏掉了，
# 变量负载族的六条（999 步、HiCache）也不在集合里，其中四条就是控制器臂。
#
# 判据（三条，缺一不可）：
#   1. trace 是主 trace（metadata.trace 以 replay_pois200_l04.csv 结尾）——
#      变量负载族与 25 档用的是别的 trace，**它们不是这个集合的一部分**；
#   2. build.hicache_enabled 为真（host tier 开着）；
#   3. 完成步数 >= 995（999 步的 trace；995–998 是客户端末尾丢的几步）。
#      763 / 770 步那两条是**没跑完**，不是「数字不好看」。
# 另有一条按名字排除：foyer_hz1_r2 —— 引擎侧 prompt token 计数是计划的 1.41×、
# 零 retraction、零重试、τ₁ 也不成比例，无法解释，故不作数（正文写明）。
# 下面 _derive() 会用这套判据重新扫一遍镜像，与 RUNS 不一致就直接报错。
TRACE_MAIN_SUFFIX = "replay_pois200_l04.csv"
MIN_STEPS = 995
EXCLUDED = {"foyer_hz1_r2": "引擎侧 prompt token 计数 1.41x 计划、τ₁ 不成比例（正文已写明排除）"}

# 被【干净重跑】替代的旧测量：2026-09-24 查出同机 ≥4 条车道 ≥60 分钟会把 τ₂ 抬高
# 25~40%（见 docs/finding_concurrency_contamination_20260924.md），受污的控制器臂
# 已用同名 + `_r2` 重跑。旧名因此仍在镜像里、也仍然满足下面三条判据 —— 判据自检
# 若不认识它们，就会把「重跑替代」误报成「集合没说清」。
#
# ⚠ 与 `cap3_hc`/`cap3_hc_r2` 这类【重复对】区分开：重复对是同一配置跑两次、**两条都
# 进正文**（表 I 各占一行），所以它们都在集合里；SUPERSEDED 里的旧名则是**被撤下的**，
# 只有新名进正文。这个区别是语义的、不是机械的，所以必须在这里手写并写明理由。
SUPERSEDED = {
    "foyer_bres": "争用污染（τ₂ 31.3ms vs 干净 24.8ms），已由 foyer_bres_r2 替代（2026-09-25）",
    "foyer_hz0": "争用污染（τ₂ 33.1ms vs 干净 25.5ms），已由 foyer_hz0_r2 替代（2026-09-25）",
    "foyer_hz2": "争用污染（τ₂ 30.9ms vs 干净 24.0ms），已由 foyer_hz2_r2 替代（2026-09-25）",
}


def _derive(root):
    """按上面的判据从镜像里列出集合 —— 用来断言硬编码的 RUNS 没写错。"""
    import glob as _g
    dev, hc, bad = [], [], []
    for d in sorted(_g.glob(os.path.join(root, "pois200_*"))):
        run = os.path.basename(d)[len("pois200_"):]
        try:
            m = json.load(open(os.path.join(d, "metadata.json")))
        except Exception:
            continue
        if not (m.get("trace") or "").endswith(TRACE_MAIN_SUFFIX):
            continue
        n = sum(1 for l in open(os.path.join(d, "steps.jsonl")) if l.strip()) \
            if os.path.exists(os.path.join(d, "steps.jsonl")) else 0
        if n < MIN_STEPS:
            bad.append((run, n))
            continue
        if run in EXCLUDED or run in SUPERSEDED:
            continue
        if (m.get("build") or {}).get("hicache_enabled"):
            hc.append(run)
        else:
            dev.append(run)
    return dev, hc, bad


# 这张表的集合 = 论文 §III 引「host tier 兑现区间」的那个集合 + 论文点名的五个静态
# device-only cap。**必须与 eviction.csv 的行数一致** —— 原来这里是 13 条，而文件是
# 24 行（上一次是用命令行传的 24 条），裸跑一次就会静默把文件砍掉一半。
RUNS = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5",
        "pairA_cap2hc", "pairB_cap2hc", "cap3_hc", "cap3_hc_r2", "cap4_hc", "cap4_hc_r2",
        "foyer_hc", "foyer_hc_r2", "foyer_hz1", "foyer_hz2_r2", "foyer_hz0_r2", "foyer_bres_r2",
        "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyer_sf0_r2", "foyfix_hc",
        "pairA_foyerhc", "pairB_foyerhc"]


def last_value(path, name):
    """取某一列最后一个有效值（这些是累计计数器）。"""
    hdr = open(path).readline().strip().split(",")
    if name not in hdr:
        return None
    i = hdr.index(name)
    v = None
    for line in open(path).readlines()[1:]:
        c = line.rstrip("\n").split(",")
        if len(c) <= i:
            continue
        try:
            v = float(c[i])
        except ValueError:
            pass
    return v


def col(path, name):
    hdr = open(path).readline().strip().split(",")
    if name not in hdr:
        return []
    i = hdr.index(name)
    out = []
    for line in open(path).readlines()[1:]:
        c = line.rstrip("\n").split(",")
        if len(c) <= i:
            continue
        try:
            out.append(float(c[i]))
        except ValueError:
            pass
    return out


def main():
    root, out_path = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    # 判据自检：镜像上按判据重算一遍，与给定的 run 列表比对（多一条少一条都报错）
    dev_d, hc_d, short_d = _derive(root)
    # 只对【host-tier 那一半】做判据比对：device-only 那一半是论文里点名的
    # 「五个静态 cap」（cap1..cap5），不是按判据筛出来的族 —— 主 trace 上还有
    # default/aimd2/rl90 等别的 device-only run，它们不属于那张表。
    want_hc = {r for r in runs if r in hc_d or r.startswith(("foyer_", "pair", "cap3_hc", "cap4_hc", "foyfix"))}
    want_hc = {r for r in runs if r not in ("cap1", "cap2", "cap3_fixed", "cap4", "cap5")}
    missing, extra = sorted(want_hc - set(hc_d)), sorted(set(hc_d) - want_hc)
    print("判据重算：host-tier %d 条；未达 %d 步被排除 %d 条 %s（另有 device-only %d 条不在本判据内）"
          % (len(hc_d), MIN_STEPS, len(short_d),
             " ".join("%s(%d)" % t for t in short_d), len(dev_d)))
    if missing or extra:
        raise SystemExit("!! host-tier 集合与判据不一致：判据里有而列表没有 %s；列表里有而判据不认 %s\n"
                         "   （判据见本脚本顶部注释；改判据要同步改正文）"
                         % (missing, extra))
    rows, bad, missing = [], [], []
    for r in runs:
        d = os.path.join(root, "pois200_" + r)
        mp = os.path.join(d, "metrics.csv")
        sp = os.path.join(d, "steps.jsonl")
        if not (os.path.exists(mp) and os.path.exists(sp)):
            missing.append(r)
            continue
        try:
            # ⚠ prompt 必须与 uncached **同源**，否则 reuse = prompt - uncached 是拿
            # 两个不同来源相减。原来这里取 metrics.csv 的 sglang:prompt_tokens_total，
            # 而 uncached 是 steps.jsonl 的求和 —— cap3_fixed 上两者差 43,112 tokens
            # （0.15%），兑现率因此从 78.9% 变 79.0%（2026-09-24 审稿人抓）。
            # 下面的断言 1 本来就要求 prompt == 计划 prefill（1% 内），直接用它即可。
            steps = [json.loads(l) for l in open(sp) if l.strip()]
            prompt = sum(s.get("prompt_len") or 0 for s in steps)
            cached = last_value(mp, "sglang:cached_tokens_total")
            evicted = last_value(mp, "sglang:evicted_tokens_total")
            uncached = sum(s.get("server_uncached_prompt_tokens") or 0 for s in steps)
            plan = prompt

            # 断言 1：prompt_tokens_total 必须等于计划 prefill —— 这是恒等式，
            # 挡住的是列读错（读错列不会有这个性质）
            _mp_tot = last_value(mp, "sglang:prompt_tokens_total")
            assert _mp_tot and abs(_mp_tot - plan) / plan < 0.01, \
                "prompt_tokens_total %.1fM 与计划 %.1fM 不符，列可能读错了" % (
                    (_mp_tot or 0) / 1e6, plan / 1e6)

            # 断言 2：cached 必须是 prompt 的一部分（不是独立的量）
            assert cached is not None and 0 <= cached <= prompt * 1.01, \
                "cached_tokens_total 不在 [0, prompt] 内"
            # 注意：prompt − cached == steps 的未命中数，这条【只在无 HiCache 时成立】。
            # 有 HiCache 时两者差很多（cap4_hc: 22.4M vs 9.1M），因为
            # sglang:cached_tokens_total 只计【设备侧】radix cache 的命中，
            # host 梯队接住的那部分不进这个计数器，但逐请求 usage 里算作 cached。
            # 所以本表以 steps 的未命中数为准（那才是真正重新 prefill 的量），
            # 并把设备侧命中单列出来，两者的差就是 host 梯队的贡献。
            dev_miss = prompt - cached   # 设备侧未命中

            rn = col(mp, "sglang:num_running_reqs")
            # HiCache 判定：优先读 metadata 的 build.hicache_enabled（新 run 都有），
            # 读不到再退回硬编码集合。**不能只靠硬编码** —— 原来那份漏了
            # foyer_breshz1（它 host 接住 14.4M，确实是 host-tier run），
            # 于是 §III 的"八条 host-tier run"其实是九条，报的区间是从少一个
            # 成员的集合算的，而漏掉的那个恰是最极端的一点（2026-09-24 审稿人抓）。
            HC_FALLBACK = {"pairB_cap2hc", "cap3_hc", "cap4_hc", "foyer_hc",
                           "foyer_hz1", "foyer_hz2_r2", "foyer_hz0_r2",
                           "foyer_bres_r2", "foyer_breshz1"}
            _mj = os.path.join(d, "metadata.json")
            hc_flag = None
            if os.path.exists(_mj):
                try:
                    hc_flag = json.load(open(_mj)).get("build", {}).get("hicache_enabled")
                except Exception:
                    hc_flag = None
            if hc_flag is None:
                hicache = r in HC_FALLBACK
            else:
                hicache = bool(hc_flag)
            rows.append({
                "run": r,
                "hicache": "1" if hicache else "0",
                "prompt_M": round(prompt / 1e6, 1),

                "uncached_M": round(uncached / 1e6, 1),
                "evicted_M": round((evicted or 0) / 1e6, 1),
                "dev_miss_M": round(dev_miss / 1e6, 1),
                "host_hit_M": round((dev_miss - uncached) / 1e6, 1),   # 设备没接住、但也没重算的
                "running": round(statistics.mean(rn), 2) if rn else "",
                "step_back_ms": "", "step_perreq_ms": "",
                "prompt_tok": int(prompt),
                "reuse_tok": int(prompt - uncached),
                "uncached_tok": int(uncached),
                "dev_miss_tok": int(dev_miss),
                "host_hit_tok": int(dev_miss - uncached),
            })
        except Exception as e:
            bad.append((r, str(e)))

    if missing:
        print("!! 以下 run 在 %s 下不存在（镜像不全？）—— 静默丢掉会让数据文件的集合" % root)
        print("!! 与正文引用的集合不一致（2026-09-24 就这样漏掉过 foyer_hz1）：")
        for r in missing:
            print("   %s" % r)
    if bad:
        print("!! 未通过校验：")
        for r, why in bad:
            print("   %-14s %s" % (r, why))

    with open(out_path, "w", newline="") as f:
        f.write("# 驱逐 vs 重算 —— 由 scripts/lab/gen_eviction.py 生成，勿手改\n")
        f.write("# dev_miss_M: prompt - cached_tokens_total —— 【设备侧】没接住的部分\n")
        f.write("# host_hit_M: dev_miss - uncached —— 设备没接住、但也没重算的那部分 = host 梯队接住的。\n#             无 HiCache 时精确为 0（五条全是），有 HiCache 时 13~19M\n")
        f.write("# uncached_M: steps.jsonl 的 server_uncached_prompt_tokens 累加（真正重新 prefill 的量）\n")
        f.write("# evicted_M: metrics.csv 的 sglang:evicted_tokens_total 末值\n")
        f.write("# host_hit_M 是最关键的一列：无 HiCache 的五条精确为 0.0，有 HiCache 的八条 13~19M。\n")
        f.write("# evicted_M 单列出来只作参照——驱逐量本身不决定重算量，dev_miss 才决定。\n")
        w = csv.DictWriter(f, fieldnames=HEADER)
        f.write("# prompt_tok/reuse_tok/uncached_tok: 未舍入的原始计数，算比例用这三列\n")
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out_path, len(rows)))
    for r in rows:
        print("  %-13s hc=%s 设备未命中 %5.1fM host命中 %5.1fM 重算 %5.1fM 驱逐 %5.1fM" % (
            r["run"], r["hicache"], r["dev_miss_M"], r["host_hit_M"],
            r["uncached_M"], r["evicted_M"]))


if __name__ == "__main__":
    main()
