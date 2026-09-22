#!/usr/bin/env python3
"""任意长度的 run 都能量：墙钟 / 并发 / SLO / 命中 / run 内稳定性。

为什么需要它。现有脚本（fig_poisson_status.py 等）都写死了"必须跑满 999 步"，
于是短 trace（r2 = 399 步）的 run 会被静默跳过——而短 trace 正是快速迭代要用的。
这个脚本不假设长度，段数按实际步数除以十取整，短 run 也不会崩。

    run_summary.py <run 名> [<run 名> ...]
    run_summary.py --prefix pois200_          # 列出所有匹配的
"""
import json, os, statistics, sys

R = "/data/xbw/turnstile/results/night"
POOL = 101432


def tw_conc(D):
    """时间加权平均并发（不是按 admit 事件数加权——那会被高并发时刻带偏）。"""
    ev = []
    p = D + "/admissions.jsonl"
    if not os.path.exists(p):
        return None
    for ln in open(p):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        d = {"admit": 1, "release": -1, "resume": 1}.get(e.get("event"))
        if d and e.get("ts") is not None:
            ev.append((float(e["ts"]), d))
    if len(ev) < 2:
        return None
    ev.sort()
    area = 0.0
    cur = 0
    for i, (t, d) in enumerate(ev):
        if i > 0:
            area += cur * (t - ev[i - 1][0])
        cur += d
    sp = ev[-1][0] - ev[0][0]
    return area / sp if sp > 0 else None


def summary(nm):
    D = os.path.join(R, nm)
    if not os.path.isdir(D):
        return None, "目录不存在"
    try:
        m = json.load(open(D + "/metadata.json"))
        b = m.get("build") or {}
    except Exception as e:
        return None, "metadata 读不到: %s" % e
    st = []
    try:
        for ln in open(D + "/steps.jsonl"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if r.get("complete_timestamp"):
                st.append(r)
    except Exception as e:
        return None, "steps 读不到: %s" % e
    if not st:
        return None, "没有完成的步骤"
    st.sort(key=lambda r: r["complete_timestamp"])
    tt = [r["first_token_ms"] for r in st if r.get("first_token_ms") is not None]
    if not tt:
        return None, "没有 TTFT 样本"
    hit = [r["server_prefix_hit_rate"] for r in st if r.get("server_prefix_hit_rate") is not None]
    nseg = max(2, min(10, len(st) // 20))
    seg = []
    for k in range(nseg):
        g = st[k * len(st) // nseg:(k + 1) * len(st) // nseg]
        h = [y["first_token_ms"] for y in g if y.get("first_token_ms") is not None]
        if h:
            seg.append(100 * sum(1 for t in h if t < 10000) / len(h))
    return dict(
        policy=m.get("policy"), hc=bool(b.get("hicache_enabled")),
        steps=len(st), done=os.path.exists(D + "/summary.json"),
        # 墙钟 = 最后一个完成 − 最早一个提交。
        # 不能用 st[0]["submit_timestamp"]：st 是按【完成时间】排的，
        # 最早完成的请求未必是最早提交的（GPT 审查 2026-09-22 指出，
        # 实测在本 trace 上差 0.1%，但口径本身是错的）。
        wall=(max(r["complete_timestamp"] for r in st)
              - min(r["submit_timestamp"] for r in st if r.get("submit_timestamp"))) / 60.0,
        conc=tw_conc(D),
        slo=100 * sum(1 for t in tt if t < 10000) / len(tt),
        ttft=statistics.median(tt),
        hit=100 * sum(hit) / len(hit) if hit else None,
        sd=statistics.pstdev(seg) if len(seg) > 1 else 0.0,
        trend=seg[-1] - seg[0] if len(seg) > 1 else 0.0,
        seg=seg,
    ), None


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    names = []
    if args[0] == "--prefix":
        p = args[1]
        names = sorted(d for d in os.listdir(R) if d.startswith(p))
    else:
        names = args
    print("%-26s %6s %7s %7s %7s %6s %7s %7s  %s" % (
        "run", "步数", "墙钟min", "并发", "SLO%", "段SD", "首-末", "TTFT50", "策略"))
    bad = 0
    for nm in names:
        d, err = summary(nm)
        if d is None:
            print("%-26s  SKIP  %s" % (nm[:26], err))
            bad += 1
            continue
        flag = " " if d["done"] else "*"   # * = 还没跑完
        print("%-26s %6d %7.1f %7.2f %7.1f %6.1f %+7.0f %7.0f %s%s" % (
            nm[:26], d["steps"], d["wall"], d["conc"] or 0, d["slo"], d["sd"],
            d["trend"], d["ttft"], flag, (d["policy"] or "")[:34]))
        print("%-26s   段SLO: %s" % ("", " ".join("%2.0f" % x for x in d["seg"])))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
