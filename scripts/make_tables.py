#!/usr/bin/env python3
"""Rebuild every paper table from the run results — one source of truth.

Reads each run's metadata/summary/steps/controller logs, validates the run (KV pool
must be the aligned 101,432; the trace must match; steps must be complete), computes
the five metrics the paper reports, and prints markdown tables.

Validation is the point: a run whose KV pool shrank (a neighbour held VRAM at server
start) is silently incomparable — that bit us on cap3/cap5@25 and the first
200-tier fixed-config attempt, and faked a quality "regression".

Usage: make_tables.py [results_dir] > tables.md
"""
import json
import os
import statistics as st
import sys

NIGHT = sys.argv[1] if len(sys.argv) > 1 else "/data/xbw/turnstile/results/night"
EXPECT_POOL = 101432
SLO_MS = 10000.0

# ---- which runs make up each table (explicit and auditable) -------------------
TABLES = {
    "§5.1 cliff (25-tier static sweep, aligned pool)": [
        ("cap1", "load25c_cap1"), ("cap2", "load25c_cap2r"), ("cap3", "load25c_cap3r"),
        ("cap4", "load25c_cap4"), ("cap5", "load25c_cap5r"), ("cap6", "load25c_cap6"),
        ("cap7", "load25c_cap7r"), ("cap8", "load25c_cap8r"),
    ],
    "§5.2 main (200-tier, all strategies)": [
        ("default", "budget200c_default"), ("cap1", "budget200c_cap1"),
        ("cap2", "budget200c_cap2"), ("cap3", "budget200c_cap3"),
        ("cap4", "budget200c_cap4"), ("cap5", "budget200c_cap5"),
        ("budget2 (clairvoyant)", "budget200c_budget2"),
        ("aimd2 (Concur repro)", "budget200c_aimd2"),
        ("Foyer (agg+HiCache)", "budget200c_budget3_agg_hc"),
        ("Foyer r3", "budget200c_budget3_r3"),
        ("Foyer fixed cfg", "p200_fix_r2"),
    ],
    "§5.3 predictor attribution (25-tier)": [
        ("zero-growth", "load25c_budget3_zero"), ("global", "load25c_budget3_glob"),
        ("EMA (default)", "load25c_budget3"), ("oracle", "load25c_budget3_oracle"),
        ("EMA, no starve guard", "load25c_budget3_sg0"),
    ],
    "§5.4 HiCache rescue (25-tier cap6)": [
        ("cap6 (no HiCache)", "load25c_cap6"), ("cap6 + HiCache", "load25c_cap6_hc"),
        ("Foyer + HiCache", "load25c_budget3_agg_hc"), ("Foyer (no HiCache)", "load25c_budget3"),
    ],
    "HiCache control (200-tier — low concurrency, no eviction pressure)": [
        ("cap2 (no HiCache)", "budget200c_cap2"), ("cap2 + HiCache", "budget200c_cap2_hc"),
        ("Foyer + HiCache", "budget200c_budget3_agg_hc"),
    ],
    "throttle ablation (25-tier, current code)": [
        ("baseline", "thr25_base"), ("no single-flight", "thr25_nosf"),
        ("no high-water floor", "thr25_nohw"), ("target 0.95", "thr25_t95"),
        ("floor off + target 0.95", "thr25_push"), ("  … repeat", "thr25_push_r2"),
        ("floor off + no single-flight", "thr25_hwsf"),
    ],
    "arrival shape — Poisson λ=0.04/s (200 sessions)": [
        ("no control", "pois200_default"),
        ("cap1", "pois200_cap1"), ("cap2", "pois200_cap2"),
        ("cap3", "pois200_cap3_r2"), ("cap4", "pois200_cap4"),
        ("cap5", "pois200_cap5"),
        ("Concur (paper params)", "pois200_aimd2_paper"),
        ("Concur (retuned)", "pois200_aimd2"),
        ("Foyer", "pois200_foyer"),
        ("Foyer + HiCache", "pois200_foyer_hc"),
        ("Foyer rl90", "pois200_foyer_rl90"),
        ("Foyer rl99", "pois200_foyer_rl99"),
        ("Foyer t90", "pois200_foyer_t90"),
        ("Foyer t85", "pois200_foyer_t85"),
    ],
    "arrival shape — real measured peak hour (117 sessions)": [
        ("cap2", "realhr_cap2"), ("Foyer fixed cfg", "realhr_foyer"),
    ],
}


def read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, errors="replace") as f:
        for line in f:
            line = line.strip().replace("\x00", "")
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def run_trace(name):
    """Trace basename for a run, or None.

    The heading of each table is DERIVED from its runs rather than trusted as
    written. Two 200-tier tables sit in this file -- one over the flash-crowd
    generation (budget200c_*) and one over the Poisson generation (pois200_*) --
    and on 2026-09-21 the headings alone were enough for me to take the wrong one
    for the paper's main table, then conclude the draft's numbers could not be
    reproduced and strike out a correct ledger entry. They reproduce fine.

    A heading is a claim like any other, so it gets computed.
    """
    p = os.path.join(NIGHT, name, "metadata.json")
    if not os.path.exists(p):
        return None
    try:
        return os.path.basename(json.load(open(p)).get("trace") or "") or None
    except (ValueError, OSError):
        return None


def run_metrics(name):
    d = os.path.join(NIGHT, name)
    m, p, meta_missing = {}, None, False
    if os.path.exists(f"{d}/metadata.json"):
        m = json.load(open(f"{d}/metadata.json"))
    else:
        meta_missing = os.path.exists(f"{d}/summary.json")   # early runs lack metadata
    if os.path.exists(f"{d}/summary.json"):
        p = json.load(open(f"{d}/summary.json")).get("replay", {})
    if p is None:
        return {"name": name, "missing": True}

    # completeness + validity: an incomplete or pool-mismatched run is not a result
    n_ok = p.get("success_steps", 0)
    n_att = p.get("attempted_steps", 0)
    warn = []
    if meta_missing:
        warn.append("no metadata: wall from step spans, pool unchecked")
    elif m.get("pool_tokens") != EXPECT_POOL:
        warn.append(f"pool={m.get('pool_tokens')}")
    if n_att == 0 or n_ok == 0:
        warn.append("no steps")

    # SLO% and time-average concurrency from the per-step log
    ttfts, sessions = [], {}
    for r in read_jsonl(f"{d}/steps.jsonl"):
        if r.get("status") != "SUCCESS":
            continue
        ft = r.get("first_token_ms")
        if ft is not None:
            ttfts.append(ft)
        sid, s, c = r.get("session_id"), r.get("submit_timestamp"), r.get("complete_timestamp")
        if sid and s and c:
            cur = sessions.setdefault(sid, {"first": s, "last": c})
            cur["first"] = min(cur["first"], s)
            cur["last"] = max(cur["last"], c)
    conc, span_min = None, None
    if sessions:
        t0 = min(v["first"] for v in sessions.values())
        t1 = max(v["last"] for v in sessions.values())
        if t1 > t0:
            conc = sum(v["last"] - v["first"] for v in sessions.values()) / (t1 - t0)
            span_min = (t1 - t0) / 60
    n_adm = sum(1 for r in read_jsonl(f"{d}/controller.jsonl") if r.get("candidate"))

    wall_s = m.get("wall_s")
    return {
        "name": name,
        "policy": m.get("policy", "budget2" if name.endswith("budget2") else "?"),
        "wall": wall_s / 60 if wall_s else span_min,
        "hit": 100 * (p.get("server_prefix_hit_rate") or 0),
        "ttft_p50": p.get("ttft_ms_p50"),
        "slo": 100 * sum(1 for x in ttfts if x < SLO_MS) / len(ttfts) if ttfts else None,
        "fails": n_att - n_ok,
        "attempted": n_att,
        "conc": conc,
        "admissions": n_adm or None,
        "warn": "; ".join(warn),
    }


def fmt(v, nd=1, suffix=""):
    return "—" if v is None else f"{v:.{nd}f}{suffix}"


for title, runs in TABLES.items():
    # Which trace generation this table is actually over. Mixed generations in one
    # comparison table are not comparable, so say so loudly rather than silently.
    _t = {}
    for _lbl, _name in runs:
        _tr = run_trace(_name)
        if _tr:
            _t[_tr] = _t.get(_tr, 0) + 1
    _span = ""
    if _t:
        _span = "  [trace: " + " + ".join(f"{k} ×{v}" for k, v in sorted(_t.items())) + "]"
        if len(_t) > 1:
            _span += "  ⚠ MIXED GENERATIONS — not comparable"
    title = title + _span
    print(f"\n### {title}\n")
    print("| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |")
    print("|---|---|---|---|---|---|---|---|")
    bad = []
    for label, name in runs:
        r = run_metrics(name)
        if r.get("missing"):
            print(f"| {label} | `{name}` | — | — | — | — | — | — |")
            bad.append(f"{name}: no result yet")
            continue
        mark = f" ⚠ {r['warn']}" if r["warn"] else ""
        if r["warn"]:
            bad.append(f"{name}: {r['warn']}")
        print(f"| {label}{mark} | `{r['policy']}` | {fmt(r['wall'])} | {r['fails']} | "
              f"{fmt(r['hit'])} | {fmt(r['ttft_p50'], 0)} | {fmt(r['slo'])} | "
              f"{fmt(r['conc'], 2)} |")
    if bad:
        print("\n> ⚠ issues: " + "; ".join(bad))
