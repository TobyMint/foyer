#!/usr/bin/env python3
"""把 run 放到静态前沿上判「赢了没有」。

用法:  python3 frontier.py <run> [<run> ...]
       python3 frontier.py --all-foyer

为什么需要它：我们反复在"这个数比那个数好"上打转，而正确的判据只有一个——
**这个点在不在这条 (墙钟, SLO) 静态前沿的上方**。落在两个静态 cap 中间的连线上
不算赢，因为静态方法按时间片混合就能逼近线上任一点（§二十七、§五十二）。

前沿的三个锚点（全部 999 步、HiCache 开、同一代码代）：
    cap4_hc_r2 (209.1, 68.5)   # 重复 run 支配了 cap4_hc，见 paper/data/runs.csv
    cap3_hc_r2 (230.3, 81.9)   # 2026-09-24 更正：cap3_hc 的重复同样在两个轴上都支配它，
                               # 按同一条规矩必须顶掉。原稿以"它超了自己的 cap"为由排除，
                               # 但那是【另一条非 HiCache 的 pois200_cap3_r2】（峰值在飞 5、
                               # 超帽 126 个样本）；cap3_hc_r2 峰值在飞 3、超帽 0，是干净的。
    cap2_hc  (295.0, 91.6)   <- pairB；pairA (304.5, 90.6) 被它支配，不入前沿
低于 213 分钟没有任何静态点，落在那里是平凡获胜。
"""
import json, os, statistics as st, sys

# 结果目录。默认指实验机；本地镜像可用环境变量覆盖：
#   TURNSTILE_RESULTS=results/night python3 frontier.py --csv
# 为什么要这个开关：本地镜像是 rsync 的一部分（2026-09-24 之前只有 21/54 条），
# 于是 --csv 在本地生成时会【静默漏掉】镜像里没有的 run。默认指向实验机不变，
# 保证在实验机上跑出来的值与一直以来的口径一致。
RESULTS = os.environ.get("TURNSTILE_RESULTS", "/data/xbw/turnstile/results/night")
# 上左包络的锚点，按墙钟升序。cap1 没有 HiCache 版本，但它仍然是"静态 cap 能达到的点"，
# 必须放进前沿——否则墙钟超过最右锚点的 run 会被误判成"越过前沿"（cap1 自己就撞过这个）。
# 锚点坐标必须是【全精度】，不能用表里印的 1 位小数。
# 2026-09-24 审稿人抓：这里原来写死 209.1/68.5 等显示值，于是【全篇的 Δ 都是用
# 显示值插值出来的】—— sf0 得 -0.57（全精度 -0.55）、hz1 得 -0.94（-0.93）；
# 更糟的是锚点自己的 Δ 不为 0（cap4_hc_r2 -0.055、cap3_hc_r2 -0.019），
# 而 cap1 因为墙钟 527.4320 > 锚点 527.4 被判成 OUT-OF-RANGE。
# 上一轮把 gen_table 改成 import 本模块，两条管线【一致】了 —— 但一致在显示值上。
# 坐标来自 paper/data/runs_precise.csv（frontier.py --csv 的产物），逐位相符。
# ⚠ 2026-09-25：`cap6_hc`（207.8470，SLO 28.93）是**静态点里最快的**，
# 所以按上左包络的定义它是新的**最左锚点** —— 图 1 一直在这么画（它不硬编码，
# 而是从 runs.csv 现算包络），而这里的 FRONT 是硬编码的、漏了它，
# 于是表 I 把 207.8 分钟的 cap6_hc 报成「left of front」（codex 第 26 轮抓到）。
# 加它**不移动任何已报告的 Δ**：现有控制器臂都比 209.137 慢，插值区间不变。
import envelope as _ENV  # noqa: E402  （同目录共用定义，见该模块 docstring）

FRONT = [(207.846997, 28.928929, "cap6_hc"),
         (209.137154, 68.468468, "cap4_hc_r2"),
         (230.308193, 81.881882, "cap3_hc_r2"),
         (295.020816, 91.591592, "pairB_cap2hc"),
         (527.431963, 94.794795, "cap1")]


def front_slo(wall):
    """前沿在给定墙钟处的 SLO 上界。**实现已抽到 envelope.front_slo 共用**
    （A100 要用同一份逻辑算它自己的前沿，各写一份必然分叉）。
    超出锚点范围返回 None —— 范围外没有可比的前沿，不能给判决。"""
    return _ENV.front_slo(wall, FRONT)


def summarise(run):
    p = os.path.join(RESULTS, run, "steps.jsonl")
    if not os.path.exists(p):
        return None
    rows = [json.loads(l) for l in open(p)]
    ts = [r["submit_timestamp"] for r in rows if r.get("submit_timestamp")]
    te = [r["complete_timestamp"] for r in rows if r.get("complete_timestamp")]
    tt = [r["first_token_ms"] for r in rows if r.get("first_token_ms") is not None]
    if not ts or not tt:
        return None
    wall = (max(te) - min(ts)) / 60.0
    slo = 100.0 * sum(1 for x in tt if x <= 10000) / len(tt)
    # 实测并发：按 30 秒采样活跃请求数
    N = 300
    act = []
    for i in range(N):
        t = min(ts) + (max(te) - min(ts)) * i / (N - 1)
        act.append(sum(1 for r in rows if r.get("submit_timestamp") and r.get("complete_timestamp")
                       and r["submit_timestamp"] <= t < r["complete_timestamp"]))
    # 分段 SLO 标准差（十等分）
    seg = []
    for i in range(10):
        s = tt[i * len(tt) // 10:(i + 1) * len(tt) // 10]
        if s:
            seg.append(100.0 * sum(1 for x in s if x <= 10000) / len(s))
    sd = st.pstdev(seg) if len(seg) > 1 else 0.0
    return dict(run=run, steps=len(rows), wall=wall, conc=sum(act) / N, slo=slo, sd=sd)


TIE_PP = 1.0   # ±1.0 pp 打平带 —— **唯一定义**，envelope.classify 与这里共用


def classify(delta):
    """由 Δ 给判词。**与 gen_a100_delta.py 共用同一份阈值与判词表**（CLAUDE.md 纪律 2：
    两个脚本算同一个量必须共用定义；2026-09-25 codex r28 指出那边各写了一份）。"""
    # ⚠ 边界必须**两侧一致**。正文（sec_background.tex）写的是「more than $+1.0$pp
    # 算上方，less than $-1.0$pp 算下方，两者之间算 on」—— 即 **恰好 −1.0 落在带内**。
    # 原来下界写的是 `delta > -TIE_PP`，于是恰好 −1.0 被判成 BELOW，**与正文相反**
    # （2026-09-26 codex 第 30 轮抓到；现有报告点没有恰好落在 −1.0 的，所以一直没响）。
    # 上界本来就是对的：`delta > TIE_PP` 让恰好 +1.0 落回 ON。
    if delta > TIE_PP:
        return "ABOVE  (越过前沿)"
    if delta >= -TIE_PP:
        return "ON     (在线上, 不算赢)"
    return "BELOW  (在线下)"


# ⚠⚠ 2026-09-27（中立复核 r49 第 C17 条）：**短标签版，从 `classify` 派生**。
# 为什么要有：`gen_table.py` 与 `compare_rerun.py` 各自**内联**了 ±1.0 的阈值比较，
# 而检查器里那条「打平带只有 frontier.py 一处定义」的守卫，正则只认**赋值式**
# （`^\s*([A-Za-z_]\w*)\s*=\s*1\.0\s*$`）—— **内联的 `> 1.0` 它永远看不到**。
# 也就是说那条不变量**当时是假的**，而守卫报 0 MISS（「看起来在守」）。
# 现在把短标签也收进 frontier：**判据只有一份**，两处调用它。
_SHORT = {"ABOVE": "ABOVE", "ON": "TIE", "BELOW": "BELOW"}


def classify_short(delta):
    """`classify` 的短标签版（CSV 的 `verdict` 列用 `ABOVE`/`TIE`/`BELOW`）。

    **从 `classify` 派生**（而不是重写一遍 if）：分支结构只有一处，
    改阈值/改边界两侧都自动跟着走。
    """
    return _SHORT[classify(delta).split()[0]]


def verdict(d):
    f = front_slo(d["wall"])
    d["front"] = float("nan") if f is None else f
    if f is None:
        d["delta"] = float("nan")
        d["verdict"] = ("LEFT-OF-FRONT (无静态点在更左, 平凡获胜)"
                        if d["wall"] < FRONT[0][0] else "OUT-OF-RANGE (超出现有静态点范围)")
        return d
    d["delta"] = d["slo"] - f
    d["verdict"] = classify(d["delta"])
    return d


def emit_csv():
    """全精度导出 —— 给 gen_table.py 用。

    为什么需要：runs.csv 是手抄 run_summary.py 打印的【1 位小数】表得来的，
    而本脚本从原始日志算的是全精度。同一条插值公式，输入 263.3/86.3 与
    263.340318/86.286286 会给出差 0.02pp 的 delta —— 于是表 I 写 -0.55、
    正文写 -0.57（2026-09-24 审稿人抓到的对不上）。让两条管线共用这一个
    全精度来源，而不是各自去读不同精度的表。
    """
    import csv as _csv
    w = _csv.writer(sys.stdout)
    # 表头注释：这张表**被正文引用**（§results 的脚注与 §repro 各一处），
    # 而它此前没有一行说明是谁生成的 —— 与「每张表都要能追到生成器」不符。
    w.writerow(["# 全精度坐标 —— 由 scripts/lab/frontier.py --csv 生成，勿手改"])
    w.writerow(["# 只收【跑完的】run（判据：summary.json 存在）—— 在跑的 run 的部分日志不算，"])
    w.writerow(["#   跑完但不足 999 步的算（rg4 998 / no-control 997），步数落在最后一列。"])
    w.writerow(["run", "wall_min", "slo_pct", "steps"])
    short = []
    for nm in sorted(os.listdir(RESULTS)):
        if not nm.startswith("pois200_"):
            continue
        # ⚠ **还在跑的 run 不能进这张表。** 「不过滤步数」的初衷是让【跑完了但
        # 步数不足】的 run（rg4 998、no-control 997）也有全精度坐标，可它同时
        # 把【在跑的】run 的部分日志也收了进来 —— 2026-09-26 实测：`foyer_hz1_r3`
        # 以 **31/999 步**的残缺行进了 `runs_precise.csv`，而它当时正在跑。
        # 判据用 `summary.json`：**跑完的才有**（跑完但只有 998 步的也有）。
        # 这与「缺了多少步在数据里看得见」不冲突：看见的是【终态】的步数。
        if not os.path.exists(os.path.join(RESULTS, nm, "summary.json")):
            continue
        d = summarise(nm)
        if not d:
            continue
        # 【不再过滤步数】。原来的 `steps < 999: continue` 让表 I 里四条
        # 步数不足 999 的 run（hz0 995、hz2 997、rg4 998、no-control 997）
        # 拿不到全精度坐标，gen_table 只能回落到 runs.csv 的 1 位小数，
        # 于是表里的 Δ 与 frontier.py 复算的值差 0.01~0.04pp
        # （2026-09-24 审稿人抓；正文那四条本来就【列在表里】）。
        # 数据文件负责给全精度值，是否可比由判据决定 —— 步数落成列，
        # 缺了多少步在数据里看得见，而不是只在正文里说。
        w.writerow([nm, "%.6f" % d["wall"], "%.6f" % d["slo"], d["steps"]])
        if d["steps"] < 999:
            short.append((nm, d["steps"]))
    for nm, n in short:
        print("# 注意：%s 只有 %d/999 步" % (nm, n), file=sys.stderr)


def main():
    runs = sys.argv[1:]
    if runs == ["--csv"]:
        emit_csv()
        return 0
    if runs == ["--all-foyer"]:
        runs = sorted(r for r in os.listdir(RESULTS)
                      if r.startswith("pois200_foyer") or r.startswith("pois200_cap"))
    out = []
    for r in runs:
        d = summarise(r)
        if d and d["steps"] >= 999:
            out.append(verdict(d))
    print("%-30s %5s %8s %7s %7s %8s %8s  %s" %
          ("run", "步数", "墙钟min", "并发", "SLO%", "前沿SLO", "差(pp)", "判决"))
    for d in sorted(out, key=lambda x: x["wall"]):
        print("%-30s %5d %8.1f %7.2f %7.1f %8.1f %+8.2f  %s" %
              (d["run"], d["steps"], d["wall"], d["conc"], d["slo"], d["front"], d["delta"], d["verdict"]))
    print("\n注意：步数 < 999 的 run 一律不列（未跑完的不能与跑完的比，§多处的教训）。")


if __name__ == "__main__":
    main()
