#!/usr/bin/env python3
"""Generate a human-readable registry of every night run: name, config, tier,
pool, wall, when. Source of truth = each run dir's metadata.json.

Usage: python gen_registry.py [results_dir] [out_md]
"""
import json
import os
import sys
import time

NIGHT = sys.argv[1] if len(sys.argv) > 1 else "/data/xbw/turnstile/results/night"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/runs_registry.md"

rows = []
for name in sorted(os.listdir(NIGHT)):
    d = os.path.join(NIGHT, name)
    mp = os.path.join(d, "metadata.json")
    if not os.path.isfile(mp):
        continue
    try:
        m = json.load(open(mp))
    except Exception:
        continue
    trace = os.path.basename(m.get("trace", "") or "").replace(".csv", "")
    digits = "".join(ch for ch in name.split("_")[0] if ch.isdigit())
    tier = digits or "—"
    pool = m.get("pool_tokens")
    rows.append({
        "run": name,
        "policy": m.get("policy", "?"),
        "tier": tier,
        "trace": trace.replace("replay_", ""),
        "pool": pool,
        # a pool that is not the aligned 101,432 means another job held VRAM at
        # server start: the run is not comparable to the current tables
        "pool_warn": "" if pool == 101432 else f" ⚠{pool}" if pool else " ⚠?",
        "wall_min": round((m.get("wall_s") or 0) / 60, 1) if m.get("wall_s") else None,
        "started": time.strftime("%m-%d %H:%M", time.localtime(m["started"])) if m.get("started") else "?",
        "lane": m.get("lane", ""),
    })

rows.sort(key=lambda r: r["started"], reverse=True)

with open(OUT, "w") as f:
    f.write("# Run registry (auto-generated — source: each run's metadata.json)\n\n")
    f.write("Config vocabulary: `static=N` = fixed concurrency cap | "
            "`budget3` = capacity-accounting controller (defaults: target=0.75, margin=1.15) | "
            "`budget3:k=v` overrides: `target` = fraction of pool usable, "
            "`sf=0` = single-flight admission OFF, `hw=0` = high-water floor OFF, "
            "`sg=0` = starve guard OFF, `predictor=` = growth forecaster | "
            "`aimd2` = Concur-style reactive control | `budget2` = clairvoyant reservation (non-deployable)\n\n")
    f.write("⚠ = KV pool differs from the aligned 101,432 — another job held VRAM at "
            "server start, so the run is NOT comparable to the current tables "
            "(run_matrix now aborts on this instead of recording it)\n\n")
    f.write("| run | policy | tier | trace | pool | wall(min) | started |\n")
    f.write("|---|---|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r['run']} | `{r['policy']}` | {r['tier']} | {r['trace']} | "
                f"{r['pool'] or '?'}{r['pool_warn']} | "
                f"{r['wall_min'] if r['wall_min'] is not None else '—'} | {r['started']} |\n")
print(f"{len(rows)} runs -> {OUT}")
