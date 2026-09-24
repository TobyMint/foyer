#!/usr/bin/env python3
"""控制器「不放行窗口」的审计 —— paper/data/stall.csv。

§V 里有一句断言「11 条 FoyER 臂中有 4 条出现过一段引擎空闲、队列很长、
阀门开着、控制器一个都不放的窗口」。2026-09-24 复核时发现：这句话**复现不出来** ——
原稿写的「单段 150--175 s、占墙钟 0.9%」在任何一版判据下都对不上（这是本项目
「数字要对得上」纪律的一次违反，故补生成器并把正文改成判据能给的数）。

判据（写死在这里，正文与代码必须一致）：
  窗口 = 连续的控制周期，同时满足
    (a) n_admitted == 0           控制器一个都没放行
    (b) valve 为真                SLO 阀门开着（不是阀门挡的）
    (c) 引擎无在跑请求             metrics.csv 的 sglang:num_running_reqs == 0
    (d) waiting_n >= MIN_WAIT     队列确实很长
  且窗口时长 >= MIN_LEN_S。相邻窗口之间以「有一次放行 / 阀门关 / 引擎忙 / 队列短」
  分隔。时长用控制周期的时间戳首尾之差。

用法: python3 gen_stall.py <results_dir> <out.csv>
"""
import bisect, csv, json, os, statistics as st, sys

# 论文 §V 说的「11 条 Foyer 臂」：八条非重复臂 + 两条重复（hc_r2、sf0_r2）+ foyfix
RUNS = ["pois200_foyer_hc", "pois200_foyer_hc_r2", "pois200_foyer_sf0_r2",
        "pois200_foyer_hz0_r2", "pois200_foyer_hz1", "pois200_foyer_hz2",
        "pois200_foyer_bres_r2", "pois200_foyer_breshz1", "pois200_foyer_nogate",
        "pois200_foyer_rg4", "pois200_foyfix_hc"]
MIN_WAIT = 85        # 队列里等待准入的会话数下限
MIN_LEN_S = 150.0    # 窗口时长下限


def scan(d):
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
    M = []
    for x in csv.DictReader(open(os.path.join(d, "metrics.csv"))):
        try:
            M.append((float(x["ts"]), float(x["sglang:num_running_reqs"] or 0)))
        except (ValueError, TypeError):
            pass
    ts = [t for t, _ in M]

    def engine_idle(t):
        i = bisect.bisect_right(ts, t) - 1
        return M[i][1] == 0 if 0 <= i < len(M) else False

    wins, cur = [], None
    for e in C:
        ok = ((e.get("n_admitted") or 0) == 0 and bool(e.get("valve"))
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
    wall = (M[-1][0] - M[0][0]) if len(M) > 1 else 0
    wins = [w for w in wins if w[1] - w[0] >= MIN_LEN_S]
    return wins, wall


def main():
    root, out_p = sys.argv[1], sys.argv[2]
    rows = []
    print("%-24s %6s %-30s %9s %10s" % ("run", "窗口数", "时长(s)", "占墙钟%", "waiting中位"))
    for r in RUNS:
        d = os.path.join(root, r)
        if not os.path.exists(os.path.join(d, "controller.jsonl")):
            raise SystemExit("!! %s 缺 controller.jsonl —— 缺 run 不静默跳过" % r)
        wins, wall = scan(d)
        lens = [w[1] - w[0] for w in wins]
        ws = [x for w in wins for x in w[2]]
        rows.append(dict(run=r.replace("pois200_", ""), n_windows=len(wins),
                         total_s=round(sum(lens), 1), max_s=round(max(lens), 1) if lens else "",
                         pct_wall=round(100 * sum(lens) / wall, 2) if wall else "",
                         waiting_med=round(st.median(ws)) if ws else "",
                         lengths="|".join("%.0f" % x for x in lens)))
        print("%-24s %6d %-30s %9s %10s" % (
            rows[-1]["run"], rows[-1]["n_windows"],
            ",".join("%.0f" % x for x in lens) or "-", rows[-1]["pct_wall"],
            rows[-1]["waiting_med"]))
    hdr = ["# 控制器「不放行窗口」审计 —— 由 scripts/lab/gen_stall.py 生成，勿手改",
           "# 判据：连续控制周期内 (a) 不放行 (b) 阀门开 (c) 引擎空闲 (d) waiting_n>=%d，" % MIN_WAIT,
           "#       且窗口 >= %d s。详见脚本 docstring。" % MIN_LEN_S,
           "run,n_windows,total_s,max_s,pct_wall,waiting_med,lengths"]
    body = "\n".join(hdr) + "\n" + "\n".join(
        "%s,%d,%.1f,%s,%s,%s,%s" % (r["run"], r["n_windows"], r["total_s"], r["max_s"],
                                    r["pct_wall"], r["waiting_med"], r["lengths"] or "-")
        for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as f:
        f.write(body)
    print("-> %s（%d 行）" % (out_p, len(rows)))


if __name__ == "__main__":
    main()
