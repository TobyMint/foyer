#!/usr/bin/env python3
"""SLO / 稳定性 对 实测并发：悬崖在哪，每个策略站在哪一侧。

为什么这张图。2026-09-22 之前我们一直用「墙钟 vs SLO」画 Pareto，
那张图看不出机制。换成「并发 vs SLO」之后悬崖直接现形：
cap1(1.0) 94.8 → cap2(2.0) 89.5 → cap3(2.9) 74.4 → cap4(3.9) 55.7。
而 Foyer 站在 2.06——比 cap2 只高 3.5%，离悬崖还有 30%。
"""
import json, os, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = "/data/xbw/turnstile/results/night"
POOL = 101432
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 140

def tw_conc(D):
    ev = []; p = D + "/admissions.jsonl"
    if not os.path.exists(p): return None
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: e = json.loads(ln)
        except ValueError: continue
        d = {"admit": 1, "release": -1, "resume": 1}.get(e.get("event"))
        if d and e.get("ts") is not None: ev.append((float(e["ts"]), d))
    if len(ev) < 2: return None
    ev.sort(); area = 0.0; cur = 0
    for i, (t, d) in enumerate(ev):
        if i > 0: area += cur * (t - ev[i-1][0])
        cur += d
    sp = ev[-1][0] - ev[0][0]
    return area / sp if sp > 0 else None

def run(nm):
    D = os.path.join(R, nm)
    try: m = json.load(open(D + "/metadata.json")); b = m.get("build") or {}
    except Exception: return None
    st = []
    for ln in open(D + "/steps.jsonl"):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except ValueError: continue
        if r.get("complete_timestamp"): st.append(r)
    st.sort(key=lambda r: r["complete_timestamp"])
    if len(st) < 990: return None
    tt = [r["first_token_ms"] for r in st if r.get("first_token_ms") is not None]
    seg = []
    for k in range(10):
        g = st[k*100:(k+1)*100] if k < 9 else st[900:]
        h = [y["first_token_ms"] for y in g if y.get("first_token_ms") is not None]
        if h: seg.append(100*sum(1 for t in h if t < 10000)/len(h))
    c = tw_conc(D)
    if c is None: return None
    pol = m.get("policy") or ""
    if pol.startswith("static="): kind = "静态 cap" + ("+HC" if b.get("hicache_enabled") else "")
    elif "budget3" in pol and "target=0.95" in pol: kind = "Foyer" + ("+HC" if b.get("hicache_enabled") else "")
    else: kind = None
    if kind is None: return None
    return dict(kind=kind, conc=c, slo=100*sum(1 for t in tt if t < 10000)/len(tt),
                sd=statistics.pstdev(seg) if len(seg) > 1 else 0,
                wall=(st[-1]["complete_timestamp"]-st[0]["submit_timestamp"])/60.0, name=nm)

rows = [r for r in (run(d) for d in sorted(os.listdir(R)) if d.startswith("pois200_")) if r]
COL = {"静态 cap": "#1f77b4", "静态 cap+HC": "#e377c2", "Foyer": "#2ca02c", "Foyer+HC": "#9467bd"}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 6.4))

for ax, key, lab, ttl in ((a1, "slo", "延迟达标率 SLO (%)", "悬崖：SLO 对并发"),
                          (a2, "sd", "run 内 SLO 段标准差 (pp)", "不稳定度对并发")):
    for k, col in COL.items():
        pts = [(r["conc"], r[key]) for r in rows if r["kind"] == k]
        if not pts: continue
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=110, color=col, label=k,
                   zorder=5, edgecolors="white", linewidths=0.8)
    # 静态 cap 的连线只用无 HC 的那条，避免把 +HC 的点也串进去
    base = sorted((r["conc"], r[key]) for r in rows if r["kind"] == "静态 cap")
    if len(base) > 1:
        ax.plot([p[0] for p in base], [p[1] for p in base], "--", color="#888", lw=1.6,
                zorder=2, label="静态 cap 扫描")
    ax.set_xlabel("实测时间加权并发", labelpad=8)
    ax.set_ylabel(lab, labelpad=8)
    ax.set_title(ttl, fontsize=13)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="best" if key == "sd" else "lower left")

a1.axvspan(2.5, 3.2, color="#d62728", alpha=0.10, zorder=0)
a1.annotate("悬崖\n2.9 附近", xy=(2.9, 60), fontsize=11, color="#d62728", ha="center")
a1.annotate("Foyer 停在这里\n（2.06，离悬崖还有 30%）", xy=(2.1, 89.6), xytext=(1.55, 74),
            fontsize=10, color="#2ca02c",
            arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=1.4))
fig.suptitle("泊松 200 档：静态 cap 的悬崖，以及 Foyer 站在哪里（2026-09-22，n=1–3 每次）", fontsize=14)
fig.text(0.5, 0.015, "并发 = 由 admissions 事件算的时间加权平均；SLO = TTFT<10s 的步数占比；"
                     "段标准差 = 把 run 切成十段后各段 SLO 的标准差，衡量 run 内部稳不稳。",
         ha="center", fontsize=9, color="0.35")
fig.tight_layout(rect=[0, 0.035, 1, 0.94])
fig.savefig("/data/xbw/turnstile/scripts/fig_cliff.png")
print("wrote fig_cliff.png")
for r in sorted(rows, key=lambda r: r["conc"]):
    print("  %-28s %-12s conc=%.2f  SLO=%5.1f  SD=%4.1f  wall=%.1f" % (
        r["name"][8:], r["kind"], r["conc"], r["slo"], r["sd"], r["wall"]))
