#!/usr/bin/env python3
"""控制器「不放行窗口」审计 —— paper/data/stall.csv。

§V 里有一句断言「11 条 FoyER 臂中有 4 条出现过一段引擎空闲、队列很长、
阀门开着、控制器一个都不放的窗口」。2026-09-24 复核时发现：这句话**复现不出来** ——
原稿写的「单段 150--175 s、占墙钟 0.9%」在任何一版判据下都对不上（这是本项目
「数字要对得上」纪律的一次违反，故补生成器并把正文改成判据能给的数）。

判据（写死在这里，正文与代码必须一致）：
  窗口 = 连续的控制周期，同时满足
    (a) n_admitted == 0           控制器一个都没放行
    (b) valve **为假**            阀门/硬停没有在挡（见下：极性是量出来的）
    (c) 引擎无在跑请求             metrics.csv 的 sglang:num_running_reqs == 0
    (d) waiting_n >= MIN_WAIT     队列确实很长
  且窗口时长 >= MIN_LEN_S。相邻窗口之间以「有一次放行 / 阀门在挡 / 引擎忙 / 队列短」
  分隔。时长用控制周期的时间戳首尾之差。

⚠ **2026-09-26 修正：判据 (b) 原来是反的。** 原写法是 `bool(e["valve"])`，
  注释写「阀门开着（不是阀门挡的）」。实测**恰好相反**：日志里 `valve` 为真的周期
  只有 0.5% 放行过（rg4 29/5348），为假的周期 9.8% 放行过（308/3137）——
  `valve` 为真 = **阀门已经跳闸、正在挡准入**。于是原判据选出来的「窗口」
  正是阀门按设计挡住的那些周期，而正文却写成「阀门开着、控制器却不放人」，
  把「阀门在起作用」说成了「控制器失灵」。下面 `_polarity_check()`
  把这条极性做成**机械断言**：它只依赖同一条 run 自己的日志，不依赖源码 ——
  因为**这批 run 里有的根本不是现盘那一版跑的**（`metadata.json` 的 `code` 记着五个
  不同的 `controller_budget3.py` 哈希：`foyer_hc` 那批是 `2b573829083c`，日志里
  `base_mode`/`base` 是 None；`rg4`/`sf0_r2` 那批是 `f825bc768188`，与现盘一致）。
  读源码去解释老日志正是本项目栽过的那一类（见 CLAUDE.md「`no hw` 不是 no HiCache」）。
  ⚠ **老判据下的数另存在 `n_windows_valve_holding` / `old_total_s` / `old_pct_span`
  三列**：那四条臂（hz0_r2 / bres_r2 / rg4 各一段，foyfix_hc 九段）确实有
  「引擎空闲 + 长队列 + 不放行」的段，但阀在挡（实测这四条的 100% 窗口周期
  `ttft_p50_ms` 都高于 10 s 的 SLO 阈值、`usage` 为 0），所以它们是
  **阀门在工作、记忆比拥塞长**，不是活性缺口。留这几列是因为
  §V 曾经按它写过正文，删掉会让那段历史无从追溯。

用法: python3 gen_stall.py <results_dir> <out.csv>
"""
import bisect, csv, json, os, statistics as st, sys

# 论文 §V 说的「11 条 Foyer 臂」：八条非重复臂 + 两条重复（hc_r2、sf0_r2）+ foyfix
RUNS = ["pois200_foyer_hc", "pois200_foyer_hc_r2", "pois200_foyer_sf0_r2",
        "pois200_foyer_hz0_r2", "pois200_foyer_hz1", "pois200_foyer_hz2_r2", "pois200_foyer_hz2_r3",
        "pois200_foyer_bres_r2", "pois200_foyer_breshz1_r2", "pois200_foyer_nogate",
        "pois200_foyer_rg4", "pois200_foyer_scan", "pois200_foyer_scan_r2", "pois200_foyer_scan_r3",
        "pois200_foyer_hc_slru", "pois200_foyer_sf0_r3", "pois200_foyfix_hc"]
MIN_WAIT = 85        # 队列里等待准入的会话数下限
MIN_LEN_S = 150.0    # 窗口时长下限


def _cycles(d):
    C = []
    for ln in open(os.path.join(d, "controller.jsonl")):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if e.get("ts") is not None:
            C.append(e)
    C.sort(key=lambda e: e["ts"])
    return C


def _metrics(d):
    M = []
    for x in csv.DictReader(open(os.path.join(d, "metrics.csv"))):
        try:
            M.append((float(x["ts"]), float(x["sglang:num_running_reqs"] or 0)))
        except (ValueError, TypeError):
            pass
    return M


def _fifo_order(d):
    """放行顺序是不是严格按到达时间 —— 「只看队首」的日志指纹。

    为什么要有：正文说「驱动我们全部 run 的那个控制器只看队首」，而**跑出这些
    日志的源码与今天磁盘上的那一份不是同一版**（见 docstring），所以这条不能靠读源码。
    但它是可测的：只看队首的规则**不可能**在「更早到达的会话还在等」时放行别人 ——
    实测九条单飞开着的臂各 200 次放行里乱序 0 次；两个考虑整个队列的臂
    （`sf=0`）是 40% 与 58%。这个对比就是证据本身。
    """
    E = []
    for ln in open(os.path.join(d, "admissions.jsonl")):
        ln = ln.strip()
        if ln:
            try:
                E.append(json.loads(ln))
            except ValueError:
                pass
    q = {e["session_id"]: e["ts"] for e in E if e.get("event") == "queued"}
    adm = sorted((e for e in E if e.get("event") == "admit"), key=lambda e: e["ts"])
    done, viol = set(), 0
    for e in adm:
        sid = e["session_id"]
        if any(t < q.get(sid, 0) and s not in done and s != sid for s, t in q.items()):
            viol += 1
        done.add(sid)
    return len(adm), viol


def _single_flight(d):
    """这条臂是不是开着单飞（`sf=0` 是关掉）。用于给上面那条断言划范围。"""
    try:
        pol = json.load(open(os.path.join(d, "metadata.json"))).get("policy", "")
    except Exception:
        return None                      # 读不到就不判，不假装判过
    return "sf=0" not in pol


# ⚠ 2026-09-27：`budget3scan:` 是**唯一**一条「单飞名义上开着、实际看整个队列」的臂 ——
# 它就是工作副本 f825bc768188 上只改放行那一行（`waiting[:1]` → `waiting`）的变体，
# 所以上面那条「只看队首」的断言对它必须**反向**成立。控制器身份看 **policy 前缀**，
# 不看 run 名字（run 名字不是判据，本项目记过）。实测 76/200 = 38% 乱序，
# 与另两条看整个队列的臂（40% / 58%）同族 —— 这同时是「修复真的生效」的日志证据，
# 与「跑出日志的源码可能不是磁盘上那一份」无关。
SCAN_PREFIX = "budget3scan"


def _policy_prefix(d):
    try:
        return (json.load(open(os.path.join(d, "metadata.json"))).get("policy") or "").split(":")[0]
    except Exception:
        return None                      # 读不到就不判


def _polarity_check(C, tag):
    """`valve` 为真必须【抑制】放行 —— 否则这条审计的极性就是反的。

    只用这条 run 自己的日志，所以它与「跑它的源码是哪一版」无关。
    """
    vt = [e for e in C if e.get("valve")]
    vf = [e for e in C if not e.get("valve")]
    if len(vt) < 20 or len(vf) < 20:
        return None                      # 样本太少，不判（也不假装判过）
    rt = sum(1 for e in vt if (e.get("n_admitted") or 0) > 0) / len(vt)
    rf = sum(1 for e in vf if (e.get("n_admitted") or 0) > 0) / len(vf)
    assert rt < rf, (
        "!! %s 的 valve 极性与判据相反：valve 为真时放行率 %.3f >= 为假时 %.3f。"
        "判据 (b) 要跟着改，不许直接照抄。" % (tag, rt, rf))
    return rt, rf


def scan(d):
    C = _cycles(d)
    M = _metrics(d)
    ts = [t for t, _ in M]

    def engine_idle(t):
        i = bisect.bisect_right(ts, t) - 1
        return M[i][1] == 0 if 0 <= i < len(M) else False

    def windows(want_valve):
        wins, cur = [], None
        for e in C:
            ok = ((e.get("n_admitted") or 0) == 0
                  and bool(e.get("valve")) == want_valve
                  and engine_idle(e["ts"]) and (e.get("waiting_n") or 0) >= MIN_WAIT)
            if ok:
                if cur is None:
                    cur = [e["ts"], e["ts"], [e.get("waiting_n") or 0]]
                else:
                    cur[1] = e["ts"]; cur[2].append(e.get("waiting_n") or 0)
            else:
                if cur:
                    wins.append(cur); cur = None
        if cur:
            wins.append(cur)
        return [w for w in wins if w[1] - w[0] >= MIN_LEN_S]

    # 窗口结束后第一次放行是不是「饥饿逃生」（forced）—— 机制判据，进数据文件
    def resume_forced(t_end):
        for e in C:
            if e["ts"] > t_end and (e.get("n_admitted") or 0) > 0:
                return bool(e.get("forced"))
        return None

    wins = windows(False)
    old = windows(True)
    wall = (M[-1][0] - M[0][0]) if len(M) > 1 else 0
    return wins, old, wall, C, resume_forced


def main():
    root, out_p = sys.argv[1], sys.argv[2]
    rows = []
    print("%-24s %6s %-28s %9s %10s %8s" % ("run", "窗口数(正)", "时长(s)",
                                            "占墙钟%", "waiting中位", "逃生恢复"))
    for r in RUNS:
        d = os.path.join(root, r)
        if not os.path.exists(os.path.join(d, "controller.jsonl")):
            raise SystemExit("!! %s 缺 controller.jsonl —— 缺 run 不静默跳过" % d)
        wins, old, wall, C, rf = scan(d)
        _polarity_check(C, r)
        n_adm, fifo_bad = _fifo_order(d)
        # 一个控制周期里**最多**放行几个 —— 单飞的定义之一（`--disable-single-flight`
        # 会连带去掉 `if not args.disable_single_flight: break`，于是能一次放多个）。
        # 2026-09-27 加：正文用「它每周期只放一个、从没放过两个」把 `scans the queue`
        # 与 `single-flight off` 区分开，而那是**承重**的一句（见 §V）。不落盘就追不到。
        _per = [int(e.get("n_admitted") or 0) for e in C]
        max_per_cycle = max(_per) if _per else ""
        sf = _single_flight(d)
        if _policy_prefix(d) == SCAN_PREFIX:
            # 反向断言：这条臂的定义就是「扫队列」，日志上必须看得出乱序放行。
            assert fifo_bad > 0, (
                "!! %s 的 policy 说它扫队列，日志里却 %d/%d 次放行全按到达序 —— "
                "「扫队列」这个说法在日志上不成立" % (r, fifo_bad, n_adm))
        elif sf is True:
            assert fifo_bad == 0, (
                "!! %s 开着单飞，却有 %d/%d 次放行不是队首 —— 「只看队首」这句站不住"
                % (r, fifo_bad, n_adm))
        lens = [w[1] - w[0] for w in wins]
        ws = [x for w in wins for x in w[2]]
        lens_old = [w[1] - w[0] for w in old]
        rows.append(dict(
            run=r.replace("pois200_", ""), n_windows=len(wins),
            n_windows_valve_holding=len(old),
            old_total_s=round(sum(lens_old), 1) if lens_old else "",
            # ⚠ 正文在修正段里印了旧判据下那条臂的 12% —— 它**不再是** pct_span
            # （那是正判据下的占比）。少了这一列，正文那个 12 就无处可追
            # （2026-09-26 检查器正是这么报出来的：读 pct_span 得到 0）。
            old_pct_span=(round(100 * sum(lens_old) / wall, 2) if (lens_old and wall) else ""),
            total_s=round(sum(lens), 1), max_s=round(max(lens), 1) if lens else "",
            pct_span=round(100 * sum(lens) / wall, 2) if wall else "",
            waiting_med=round(st.median(ws)) if ws else "",
            resume_forced=("" if not wins else
                           ("yes" if rf(wins[0][1]) else "no")),
            admits=n_adm, fifo_out_of_order=fifo_bad, max_per_cycle=max_per_cycle,
            fifo_pct=round(100.0 * fifo_bad / n_adm, 1) if n_adm else "",
            lengths="|".join("%.0f" % x for x in lens)))
        print("%-24s %6d %-28s %9s %10s %8s" % (
            rows[-1]["run"], rows[-1]["n_windows"],
            ",".join("%.0f" % x for x in lens) or "-", rows[-1]["pct_span"],
            rows[-1]["waiting_med"], rows[-1]["resume_forced"]))
    hdr = ["# 控制器「不放行窗口」审计 —— 由 scripts/lab/gen_stall.py 生成，勿手改",
           "# 判据：连续控制周期内 (a) 不放行 (b) valve【为假】= 阀门没在挡 (c) 引擎空闲",
           "#       (d) waiting_n>=%d；且窗口 >= %d s。详见脚本 docstring。" % (MIN_WAIT, MIN_LEN_S),
           "# ⚠ 2026-09-26 修正：判据 (b) 原来写成 valve【为真】，实测极性相反 ——",
           "#   那选出来的是「阀门正在挡」的周期。旧数见 n_windows_valve_holding 列。",
           "# pct_span：窗口时长 / metrics 的**采样跨度** —— 不是 run_summary 的墙钟",
           "#   （两者差约 6 分钟；列名原来叫 pct_wall，字面与含义不符，2026-09-26 改）。",
           "# resume_forced：窗口结束后第一次放行走的是不是饥饿逃生（forced）。",
           "# admits/fifo_out_of_order/fifo_pct：放行次数、其中【在更早到达的会话仍在等时",
           "#   放行别人】的次数与占比 —— 「只看队首」的日志指纹（脚本里带断言）。",
           # ⚠ 2026-09-27：**注释必须是独立的列表元素，且列名行必须是【一个】元素**。
           # 我第一版把注释插在列名串中间，它与相邻的字符串**隐式拼接**、被拼进了
           # 表头行；生成器照跑不误 —— 是检查器读 CSV 时 `int("fifo_out_of_order")`
           # 崩掉才暴露的。本项目早有一条「手工拼表头的生成器加列时两处都要改」，
           # 这是它的变体：**隐式拼接让「插一行」静默改变列名行**。
           "# max_per_cycle：一个控制周期里最多放行几个 —— 单飞关掉时会 >1。",
           "run,n_windows,total_s,max_s,pct_span,waiting_med,resume_forced,"
           "n_windows_valve_holding,old_total_s,old_pct_span,"
           "admits,fifo_out_of_order,fifo_pct,max_per_cycle,lengths"]
    body = "\n".join(hdr) + "\n" + "\n".join(
        "%s,%d,%.1f,%s,%s,%s,%s,%d,%s,%s,%d,%d,%s,%s,%s" % (
            r["run"], r["n_windows"], r["total_s"], r["max_s"], r["pct_span"],
            r["waiting_med"], r["resume_forced"], r["n_windows_valve_holding"],
            r["old_total_s"], r["old_pct_span"], r["admits"],
            r["fifo_out_of_order"], r["fifo_pct"], r["max_per_cycle"],
            r["lengths"] or "-")
        for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as f:
        f.write(body)
    print("-> %s（%d 行）" % (out_p, len(rows)))


if __name__ == "__main__":
    main()
