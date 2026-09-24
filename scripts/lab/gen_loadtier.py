#!/usr/bin/env python3
"""节流开关在两个负载档上的反向效应 —— paper/data/loadtier.csv。

**为什么要有这个脚本**：这张表原来**没有生成器**、是手维护的（2026-09-25 自查发现：
`paper/data/*.csv` 里唯一一张没有生成器的），而**图 5 和 §Load Dependence 都引它**。
汇总表手维护违反本项目第一条血的教训（「手算的表一定会错」）——
`horizon.csv` 就是这样在图注里留下了一句方向反了的话。

**四个数的来源**：
  200 档 —— `table1.csv` 的 `foyer_hc`（thr=on，基线）与 `foyfix_hc`（thr=off，全关）；
  25 档  —— `thr25_base` 与 `thr25_push` 两条 run 的原始步骤日志（现算墙钟与 SLO）。
            这两条是**旧 harness**，与 200 档不同代 —— 表里带 `harness=old` 标记，
            正文与图注都写明「只能作方向、不能作量级」。**这一点不随重跑消失**：
            同代的 25 档对照 `pois200_foyer_push_25` 在 `tier25.csv` 里，不含这一条臂。

用法: python3 gen_loadtier.py <results_dir> <table1.csv> <out.csv>
"""
import csv, json, os, sys

SLO_MS = 10000.0
# (层, 表里的 arm 名, thr, table1.csv 的 run 名 或 None)
NEW_TIER = [("200", "foyer_hc", "on", "foyer_hc"),
            ("200", "foyfix_hc", "off", "foyfix_hc")]
# 旧 harness 的两条 run（目录名）
OLD_25 = [("25", "base", "on", "thr25_base"),
          ("25", "push", "off", "thr25_push")]


def wall_slo(d):
    """墙钟与 SLO —— 与 run_summary.py / gen_decomp.py 同一口径（max(complete) − min(submit)）。"""
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [s["submit_timestamp"] for s in st if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in st if s.get("complete_timestamp")]
    tt = [s["first_token_ms"] for s in st if s.get("first_token_ms") is not None]
    if not subs or not comps or not tt:
        raise SystemExit("!! %s 的时间戳不全" % d)
    return (max(comps) - min(subs)) / 60.0, 100.0 * sum(1 for x in tt if x < SLO_MS) / len(tt)


def main():
    root, t1_p, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
    t1 = {r["run"]: r for r in csv.DictReader(l for l in open(t1_p) if not l.startswith("#"))}
    rows, missing = [], []
    for tier, arm, thr, run in NEW_TIER:
        r = t1.get(run)
        if r is None:
            missing.append(run)
            continue
        rows.append({"tier": tier, "arm": arm, "throttle": thr,
                     "wall_min": "%.1f" % float(r["wall_min"]),
                     "slo_pct": "%.1f" % float(r["slo_pct"]), "harness": "new"})
    for tier, arm, thr, run in OLD_25:
        d = os.path.join(root, run)
        if not os.path.isdir(d):
            missing.append(run)
            continue
        w, s = wall_slo(d)
        rows.append({"tier": tier, "arm": arm, "throttle": thr,
                     "wall_min": "%.1f" % w, "slo_pct": "%.1f" % s, "harness": "old"})
    if missing:
        raise SystemExit("!! 缺这些 run，别写半张表：%s" % "、".join(missing))

    with open(out_p, "w", newline="") as f:
        f.write("# 节流开关在两个负载档上的反向效应 —— gen_loadtier.py 生成，勿手改\n")
        f.write("# 200 档取 table1.csv；25 档取 thr25_base / thr25_push 的原始步骤日志（现算墙钟与 SLO）。\n")
        f.write("# ⚠ 25 档那两行是【旧 harness】，与 200 档不同代，只能作方向、不能作量级；\n")
        f.write("#   同代的 25 档对照在 tier25.csv 里（pois200_*_25），不含全关节流这条臂。\n")
        w = csv.DictWriter(f, fieldnames=["tier", "arm", "throttle", "wall_min", "slo_pct", "harness"])
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out_p, len(rows)))
    for r in rows:
        print("  %-4s %-10s thr=%-4s %6s 分钟  SLO %5s%%  (%s harness)"
              % (r["tier"], r["arm"], r["throttle"], r["wall_min"], r["slo_pct"], r["harness"]))
    # 反向效应的两个数（正文与图注用的）
    d = {(r["tier"], r["throttle"]): float(r["wall_min"]) for r in rows}
    for tier in ("25", "200"):
        on, off = d.get((tier, "on")), d.get((tier, "off"))
        if on and off:
            print("  → %s 档：thr off 相对 on %+.1f%%（%.1f → %.1f 分钟）"
                  % (tier, 100.0 * (off - on) / on, on, off))


if __name__ == "__main__":
    main()
