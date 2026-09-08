#!/usr/bin/env python3
"""Aggregate night-matrix runs into a comparison table + the first figure.

Session completion time per session = max(complete_timestamp) - run start epoch
(arrival_time_ms == 0 for every session in the night CSV, so arrival == run start;
gated policies pay admission wait inside this span — that is the quantity we study).
"""
import csv
import json
import os
import sys

NIGHT = "/data/xbw/turnstile/results/night"


def load_run(path):
    out = {}
    meta_p = os.path.join(path, "metadata.json")
    if os.path.exists(meta_p):
        out["meta"] = json.load(open(meta_p))
    sum_p = os.path.join(path, "summary.json")
    if os.path.exists(sum_p):
        out["summary"] = json.load(open(sum_p))
    steps = os.path.join(path, "steps.jsonl")
    if os.path.exists(steps):
        sessions = {}
        with open(steps) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = rec.get("session_id")
                if not sid or rec.get("status") != "SUCCESS":
                    continue
                cur = sessions.setdefault(sid, {"first": 1e18, "last": 0.0, "steps": 0})
                cur["first"] = min(cur["first"], rec.get("submit_timestamp", 0) or 0)
                cur["last"] = max(cur["last"], rec.get("complete_timestamp", 0) or 0)
                cur["steps"] += 1
        out["sessions"] = sessions
    retr = 0.0
    metrics = os.path.join(path, "metrics.csv")
    if os.path.exists(metrics):
        with open(metrics) as f:
            rows = [r for r in csv.DictReader(f)]
        vals = [float(r["sglang:num_retracted_reqs"]) for r in rows if r.get("sglang:num_retracted_reqs")]
        retr = max(vals) if vals else 0.0
    out["retractions"] = retr
    return out


def pct(xs, p):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def main():
    runs = sorted(d for d in os.listdir(NIGHT) if os.path.isdir(os.path.join(NIGHT, d)))
    table = []
    for name in runs:
        r = load_run(os.path.join(NIGHT, name))
        meta = r.get("meta", {})
        summary = r.get("summary", {})
        sessions = r.get("sessions", {})
        start = meta.get("started")
        durations = [s["last"] - start for s in sessions.values()
                     if start and s["last"] > 0]
        waits = []
        if start:
            for s in sessions.values():
                waits.append(s["first"] - start)  # admission wait (first submit)
        row = {
            "run": name,
            "policy": meta.get("policy", "?"),
            "wall_s": meta.get("wall_s"),
            "rc": meta.get("runner_rc"),
            "n_sessions_done": len(sessions),
            "p50_sess_min": pct(durations, 50) / 60,
            "p95_sess_min": pct(durations, 95) / 60,
            "p99_sess_min": pct(durations, 99) / 60,
            "p50_admit_wait_s": pct(waits, 50),
            "p95_admit_wait_s": pct(waits, 95),
            "retractions": r.get("retractions"),
            "steps_ok": summary.get("replay", {}).get("success_steps"),
            "steps_total": summary.get("replay", {}).get("attempted_steps"),
            "server_hit": summary.get("replay", {}).get("server_prefix_hit_rate"),
        }
        table.append(row)

    cols = ["run", "policy", "rc", "wall_s", "n_sessions_done", "p50_sess_min",
            "p95_sess_min", "p99_sess_min", "p50_admit_wait_s", "p95_admit_wait_s",
            "retractions", "steps_ok", "steps_total", "server_hit"]
    with open(f"{NIGHT}/comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in table:
            w.writerow(row)

    print(f"{'run':<10} {'rc':<8} {'wall_min':>8} {'sess':>5} {'p50min':>7} {'p95min':>7} "
          f"{'admit_p50s':>10} {'admit_p95s':>10} {'retr':>6} {'hit%':>6}")
    for row in table:
        wall = f"{row['wall_s']/60:.0f}" if row["wall_s"] else "-"
        hit = f"{row['server_hit']*100:.1f}" if row["server_hit"] is not None else "-"
        print(f"{row['run']:<10} {str(row['rc']):<8} {wall:>8} {row['n_sessions_done']:>5} "
              f"{row['p50_sess_min']:>7.1f} {row['p95_sess_min']:>7.1f} "
              f"{row['p50_admit_wait_s']:>10.1f} {row['p95_admit_wait_s']:>10.1f} "
              f"{row['retractions']:>6.0f} {hit:>6}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        names = [r["run"] for r in table if r["p95_sess_min"] == r["p95_sess_min"]]
        t_p95 = [r["p95_sess_min"] for r in table if r["run"] in names]
        t_p50 = [r["p50_sess_min"] for r in table if r["run"] in names]
        retr = [r["retractions"] for r in table if r["run"] in names]
        x = range(len(names))
        axes[0].bar([i - 0.18 for i in x], t_p50, 0.36, label="p50")
        axes[0].bar([i + 0.18 for i in x], t_p95, 0.36, label="p95")
        axes[0].set_xticks(list(x))
        axes[0].set_xticklabels(names, rotation=20, ha="right")
        axes[0].set_ylabel("session completion (min)")
        axes[0].legend()
        axes[0].set_title("Session completion by admission policy")
        axes[1].bar(names, retr, color="tab:red")
        axes[1].set_ylabel("max retracted reqs")
        axes[1].set_title("Retraction storm intensity")
        axes[1].tick_params(axis="x", rotation=20)
        plt.tight_layout()
        plt.savefig(f"{NIGHT}/first_figure.png", dpi=150)
        print(f"\nfigure -> {NIGHT}/first_figure.png")
    except Exception as exc:
        print("figure skipped:", exc)


if __name__ == "__main__":
    main()
