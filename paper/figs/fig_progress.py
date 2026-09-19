#!/usr/bin/env python3
"""进度图（只画最新 Foyer 配置）——从 run 产物直接出图，保证与表格同源。

最新 Foyer 配置 = `budget3:hw=0;target=0.95`（高水位地板已回收、target=0.95），
它是唯一在四种场景（25 / 200 齐射 / 泊松 / 真实高峰）下都未改参数使用的配置。

Usage: fig_progress.py <results_dir> <out_dir>
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = sys.argv[1] if len(sys.argv) > 1 else "/data/xbw/turnstile/results/night"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
EXPECT_POOL = 101432
SLO_MS = 10000.0

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 140

GREEN = "#2ca02c"
BLUE = "#1f77b4"
ORANGE = "#ff7f0e"
RED = "#d62728"


def read_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def load(name):
    """One run -> dict. Raises if the KV pool is not the aligned one."""
    d = os.path.join(RESULTS, name)
    meta = json.load(open(os.path.join(d, "metadata.json")))
    summ = json.load(open(os.path.join(d, "summary.json")))
    pool = meta.get("pool_tokens")
    if pool != EXPECT_POOL:
        raise RuntimeError(f"{name}: pool {pool} != {EXPECT_POOL}, refusing to plot")
    steps = read_jsonl(os.path.join(d, "steps.jsonl"))
    ok = [r for r in steps if r.get("status") == "SUCCESS"]
    ttft = [r["first_token_ms"] for r in ok if r.get("first_token_ms") is not None]
    spans = [(r["submit_timestamp"], r["complete_timestamp"]) for r in steps
             if r.get("submit_timestamp") and r.get("complete_timestamp")]
    wall = (meta.get("wall_s") or 0) / 60 or (
        (max(c for _, c in spans) - min(s for s, _ in spans)) / 60 if spans else None)
    conc = None
    if spans:
        t0, t1 = min(s for s, _ in spans), max(c for _, c in spans)
        cur = {}
        for r in steps:
            sid, s, c = r.get("session_id"), r.get("submit_timestamp"), r.get("complete_timestamp")
            if sid and s and c:
                cur.setdefault(sid, [s, c])
                cur[sid][0] = min(cur[sid][0], s)
                cur[sid][1] = max(cur[sid][1], c)
        if t1 > t0:
            conc = sum(c - s for s, c in cur.values()) / (t1 - t0)
    return {
        "name": name,
        "policy": meta.get("policy", "?"),
        "wall": wall,
        "hit": 100 * (summ["replay"].get("server_prefix_hit_rate") or 0),
        "ttft_p50": summ["replay"].get("ttft_ms_p50"),
        "slo": 100 * sum(1 for t in ttft if t < SLO_MS) / len(ttft) if ttft else None,
        "conc": conc,
        "fails": summ["replay"].get("failed_steps"),
        "n_steps": len(steps),
    }


# ---- 数据（run 名 -> 图中含义） -------------------------------------------------
CAP25 = [("cap1", "load25c_cap1"), ("cap2", "load25c_cap2r"), ("cap3", "load25c_cap3r"),
         ("cap4", "load25c_cap4"), ("cap5", "load25c_cap5r"), ("cap6", "load25c_cap6"),
         ("cap7", "load25c_cap7r"), ("cap8", "load25c_cap8r")]
CAP200 = [("cap1", "budget200c_cap1"), ("cap2", "budget200c_cap2"), ("cap3", "budget200c_cap3"),
          ("cap4", "budget200c_cap4"), ("cap5", "budget200c_cap5")]
FOYER25 = "thr25_push"
FOYER200 = "p200_fix_r2"
CONCUR200 = "budget200c_aimd2"
DEFAULT200 = "budget200c_default"

SCENARIOS = [
    ("齐射\n200 会话", "budget200c_cap2", FOYER200),
    ("泊松 λ=0.04/s\n200 会话", "pois200_cap2", "pois200_foyer"),
    ("真实高峰小时\n117 会话", "realhr_cap2", "realhr_foyer"),
]

FOYER_LABEL = "Foyer（最新配置）"


def fig_cliff():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, (title, caps, foyer_name, xmax) in zip(axes, [
            ("25 会话档", CAP25, FOYER25, 8), ("200 会话档", CAP200, FOYER200, 5)]):
        runs = [(lbl, load(n)) for lbl, n in caps]
        foyer = load(foyer_name)
        xs = list(range(1, len(runs) + 1))
        hit = [r["hit"] for _, r in runs]
        wall = [r["wall"] for _, r in runs]
        ax.plot(xs, hit, "o-", color=BLUE, lw=2, ms=7, label="命中率（左轴）")
        ax.set_ylabel("前缀缓存命中率 (%)", color=BLUE)
        ax.tick_params(axis="y", labelcolor=BLUE)
        ax.set_xlabel("静态并发上限 cap-N")
        ax.set_xticks(xs)
        ax.set_title(title, fontsize=13)
        ax.grid(alpha=0.25)
        ax2 = ax.twinx()
        ax2.plot(xs, wall, "s--", color=RED, alpha=0.55, lw=1.6, ms=6, label="墙钟（右轴）")
        ax2.set_ylabel("端到端墙钟 (min)", color=RED)
        ax2.tick_params(axis="y", labelcolor=RED)
        for x, (_, r) in zip(xs, runs):
            ax.annotate(f"{r['hit']:.1f}", (x, r["hit"]), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=9, color=BLUE)
        ax.scatter([foyer["conc"]], [foyer["hit"]], marker="*", s=420, color=GREEN,
                   zorder=6, label=FOYER_LABEL)
        ax.annotate("Foyer 最新", (foyer["conc"], foyer["hit"]), textcoords="offset points",
                    xytext=(10, 6), fontsize=10, color=GREEN, fontweight="bold")
        ax.set_xlim(0.5, xmax + 0.5)
        if title.startswith("25"):
            ax.set_ylim(0, 80)
        else:
            ax.set_ylim(0, 80)
        ax.legend(loc="lower left", fontsize=9)
    fig.suptitle("静态 cap 的悬崖 vs 最新 Foyer（统一 KV 池 101,432 token，RTX 3090）", fontsize=14)
    fig.text(0.5, 0.005, "Foyer 点横坐标 = 实测时间平均并发（它没有 cap 这个参数）；Foyer 最新配置："
                         "25 档 64.4% / 33.0min（n=2：33.0、33.9）、200 档 64.8% / 311.4min；全部 run 池子已校验",
             ha="center", fontsize=9, color="0.3")
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(os.path.join(OUT, "fig_cliff_latest.png"))
    plt.close(fig)


def fig_pareto():
    fig, ax = plt.subplots(figsize=(11, 6.5))
    pts = [(lbl, load(n)) for lbl, n in CAP200]
    xs = [r["wall"] for _, r in pts]
    ys = [r["hit"] for _, r in pts]
    ax.plot(xs, ys, "o--", color=BLUE, alpha=0.5, ms=9, label="静态 cap 扫描（cap1–cap5）")
    for (lbl, r) in pts:
        dx, ha = (-9, "right") if lbl == "cap1" else (8, "left")
        ax.annotate(lbl, (r["wall"], r["hit"]), textcoords="offset points",
                    xytext=(dx, 4), fontsize=10, color=BLUE, ha=ha)
    conc = load(CONCUR200)
    ax.scatter([conc["wall"]], [conc["hit"]], marker="s", s=130, color=ORANGE,
               label="Concur 忠实复现", zorder=5)
    ax.annotate(f"{conc['hit']:.1f}% / {conc['wall']:.0f}min\n被 cap3 支配",
                (conc["wall"], conc["hit"]), textcoords="offset points",
                xytext=(30, -22), fontsize=10, color=ORANGE, ha="left")
    foy = load(FOYER200)
    ax.scatter([foy["wall"]], [foy["hit"]], marker="*", s=520, color=GREEN,
               label="Foyer（最新，零调参）", zorder=6)
    ax.annotate(f"{FOYER_LABEL}\n{foy['hit']:.1f}% / {foy['wall']:.0f}min",
                (foy["wall"], foy["hit"]), textcoords="offset points",
                xytext=(14, -30), fontsize=10, color=GREEN, fontweight="bold")
    dflt = load(DEFAULT200)
    ax.scatter([dflt["wall"]], [0], marker="x", s=180, color=RED, lw=3,
               label="不限流（崩溃）", zorder=6)
    ax.annotate("不限流：命中率 0%\n121/200 个会话失败\n（228min 是崩溃后的假墙钟）",
                (dflt["wall"], 0), textcoords="offset points", xytext=(10, 16),
                fontsize=10, color=RED)
    ax.set_xlabel("端到端墙钟 (min)  —— 越低越好")
    ax.set_ylabel("前缀缓存命中率 (%)  —— 越高越好")
    ax.set_title("200 会话齐射：质量 vs 吞吐（只画最新 Foyer）", fontsize=14)
    ax.grid(alpha=0.3)
    ax.set_ylim(-4, 78)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.92)
    fig.text(0.5, 0.005, "cap2 是扫遍 cap1–8 才找到的点；全部 run 统一 KV 池 101,432 token；"
                         "Concur 复现 5 个 arm 中 2 个完成（其余在跑）；budget2（池子未校验）已剔除；本图不含旧版 Foyer。",
             ha="center", fontsize=9, color="0.3")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_pareto_200_latest.png"))
    plt.close(fig)


def fig_arrival():
    rows = [(label, load(cap), load(foy)) for label, cap, foy in SCENARIOS]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    x = range(len(rows))
    w = 0.36
    ax = axes[0]
    ax.bar([i - w / 2 for i in x], [c["wall"] for _, c, _ in rows], w,
           color="0.65", label="静态 cap2（质量匹配的静态最优）")
    ax.bar([i + w / 2 for i in x], [f["wall"] for _, _, f in rows], w,
           color=GREEN, label=FOYER_LABEL)
    for i, (_, c, f) in enumerate(rows):
        ax.annotate(f"{c['wall']:.0f}", (i - w / 2, c["wall"]), ha="center",
                    textcoords="offset points", xytext=(0, 4), fontsize=10)
        ax.annotate(f"{f['wall']:.0f}", (i + w / 2, f["wall"]), ha="center",
                    textcoords="offset points", xytext=(0, 4), fontsize=10, color=GREEN,
                    fontweight="bold")
        delta = (f["wall"] - c["wall"]) / c["wall"] * 100
        ax.annotate(f"{delta:+.0f}%", (i, max(c["wall"], f["wall"]) * 1.13), ha="center",
                    fontsize=11, color=GREEN if delta < 0 else RED, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels([r[0] for r in rows])
    ax.set_ylabel("端到端墙钟 (min)  —— 越低越好")
    ax.set_title("墙钟", fontsize=13)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(max(c["wall"], f["wall"]) for _, c, f in rows) * 1.3)
    ax.legend(fontsize=9, loc="upper right", framealpha=0.95)
    ax = axes[1]
    ax.bar([i - w / 2 for i in x], [c["hit"] for _, c, _ in rows], w, color="0.65")
    ax.bar([i + w / 2 for i in x], [f["hit"] for _, _, f in rows], w, color=GREEN)
    for i, (_, c, f) in enumerate(rows):
        ax.annotate(f"{c['hit']:.1f}%", (i - w / 2, c["hit"]), ha="center",
                    textcoords="offset points", xytext=(0, 4), fontsize=10)
        ax.annotate(f"{f['hit']:.1f}%", (i + w / 2, f["hit"]), ha="center",
                    textcoords="offset points", xytext=(0, 4), fontsize=10, color=GREEN,
                    fontweight="bold")
        ax.annotate(f"SLO {f['slo']:.0f}%", (i + w / 2, f["hit"] * 0.45), ha="center",
                    fontsize=9, color="white", fontweight="bold")
        ax.annotate(f"SLO {c['slo']:.0f}%", (i - w / 2, c["hit"] * 0.45), ha="center",
                    fontsize=9, color="white")
    ax.set_xticks(list(x))
    ax.set_xticklabels([r[0] for r in rows])
    ax.set_ylabel("前缀缓存命中率 (%)")
    ax.set_ylim(0, 80)
    ax.set_title("命中率与 SLO", fontsize=13)
    ax.grid(axis="y", alpha=0.3)
    fig.suptitle("三种到达形状：最新 Foyer vs 质量匹配的静态最优（cap2）", fontsize=14)
    fig.text(0.5, 0.005, "三个形状绝对负载不同，只可比相对位置；泊松档 cap3/cap4 墙钟更快"
                         "（259/258min）但命中率只有 49.8%/45.9%，故对照取 cap2；各点 n=1（真实高峰 n=1）。",
             ha="center", fontsize=9, color="0.3")
    fig.tight_layout(rect=(0, 0.035, 1, 0.94))
    fig.savefig(os.path.join(OUT, "fig_arrival_shapes.png"))
    plt.close(fig)


if __name__ == "__main__":
    fig_cliff()
    fig_pareto()
    fig_arrival()
    print("wrote fig_cliff_latest.png, fig_pareto_200_latest.png, fig_arrival_shapes.png ->", OUT)
