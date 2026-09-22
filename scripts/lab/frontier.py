#!/usr/bin/env python3
"""把 run 放到静态前沿上判「赢了没有」。

用法:  python3 frontier.py <run> [<run> ...]
       python3 frontier.py --all-foyer

为什么需要它：我们反复在"这个数比那个数好"上打转，而正确的判据只有一个——
**这个点在不在这条 (墙钟, SLO) 静态前沿的上方**。落在两个静态 cap 中间的连线上
不算赢，因为静态方法按时间片混合就能逼近线上任一点（§二十七、§五十二）。

前沿的三个锚点（全部 999 步、HiCache 开、同一代码代）：
    cap4_hc  (213.0, 63.4)
    cap3_hc  (236.4, 81.1)
    cap2_hc  (295.0, 91.6)   <- pairB；pairA (304.5, 90.6) 被它支配，不入前沿
低于 213 分钟没有任何静态点，落在那里是平凡获胜。
"""
import json, os, statistics as st, sys

RESULTS = "/data/xbw/turnstile/results/night"
# 上左包络的锚点，按墙钟升序。cap1 没有 HiCache 版本，但它仍然是"静态 cap 能达到的点"，
# 必须放进前沿——否则墙钟超过最右锚点的 run 会被误判成"越过前沿"（cap1 自己就撞过这个）。
FRONT = [(213.0, 63.4, "cap4_hc"), (236.4, 81.1, "cap3_hc"),
         (295.0, 91.6, "cap2_hc"), (527.4, 94.8, "cap1")]


def front_slo(wall):
    """前沿在给定墙钟处的 SLO 上界（分段线性插值）。超出锚点范围返回 None——
    范围外没有可比的前沿，不能给判决，否则端点外推会凭空造出"越过"。"""
    if wall < FRONT[0][0] or wall > FRONT[-1][0]:
        return None
    for (w0, s0, _), (w1, s1, _) in zip(FRONT, FRONT[1:]):
        if w0 <= wall <= w1:
            return s0 + (s1 - s0) * (wall - w0) / (w1 - w0)
    return None


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


def verdict(d):
    f = front_slo(d["wall"])
    d["front"] = float("nan") if f is None else f
    if f is None:
        d["delta"] = float("nan")
        d["verdict"] = ("LEFT-OF-FRONT (无静态点在更左, 平凡获胜)"
                        if d["wall"] < FRONT[0][0] else "OUT-OF-RANGE (超出现有静态点范围)")
        return d
    d["delta"] = d["slo"] - f
    if d["delta"] > 1.0:
        d["verdict"] = "ABOVE  (越过前沿)"
    elif d["delta"] > -1.0:
        d["verdict"] = "ON     (在线上, 不算赢)"
    else:
        d["verdict"] = "BELOW  (在线下)"
    return d


def main():
    runs = sys.argv[1:]
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
