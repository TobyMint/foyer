#!/usr/bin/env python3
"""25 档同代对照表（论文表 II）—— paper/data/tier25.csv 的生成器。

这张表原来是 2026-09-23 从实验机 run_summary.py 的打印输出【手工导出】的，
仓库里没有生成器。「每个数字都能追到脚本」在这张表上原本是打折扣的。

本脚本直接 **import run_summary.py 并调用它的 summary()**，不复制实现 ——
口径（墙钟 / tw_conc / SLO / 段 SD / TTFT 中位）与实验机逐字相同，
包括那个容易踩的点：段数 nseg = max(2, min(10, 完成步数 // 20))，
所以 125 步是 **6 段**而不是 10 段（表 II 的 Seg. SD 列就是这个口径）。

用法: python3 gen_tier25.py <results_dir> <out.csv>
"""
import csv, importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 表 II 的四条臂；name 是表里印的名字，run 是目录名
ARMS = [("cap2_25", "pois200_cap2_25", "static=2"),
        ("cap3_25", "pois200_cap3_25", "static=3"),
        ("cap4_25", "pois200_cap4_25", "static=4"),
        ("foyer_push_25", "pois200_foyer_push_25", "budget3:hw=0;target=0.95")]


def rs_mod():
    spec = importlib.util.spec_from_file_location("_rs25", os.path.join(HERE, "run_summary.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    root, out_p = sys.argv[1], sys.argv[2]
    RS = rs_mod()
    RS.R = root
    rows = []
    print("%-16s %5s %9s %7s %7s %8s %9s" % ("run", "步数", "墙钟min", "Concurrency", "SLO%", "SegSDpp", "TTFT中位ms"))
    for name, run, policy in ARMS:
        d, err = RS.summary(run)
        if not d:
            raise SystemExit("!! %s 读不到：%s —— 缺 run 不静默跳过" % (run, err))
        if d["steps"] != 125:
            raise SystemExit("!! %s 只有 %d 步（25 档应为 125）" % (run, d["steps"]))
        rows.append(dict(run=name, steps=d["steps"], wall_min=round(d["wall"], 1),
                         conc=round(d["conc"], 2), slo_pct=round(d["slo"], 1),
                         seg_sd_pp=round(d["sd"], 1), ttft_p50_ms=round(d["ttft"]),
                         policy=policy))
        print("%-16s %5d %9.4f %7.2f %7.1f %8.1f %9.0f" % (
            name, d["steps"], d["wall"], d["conc"], d["slo"], d["sd"], d["ttft"]))
    hdr = ["# 25 档（125 步）同代 harness 对照 —— 由 scripts/lab/gen_tier25.py 生成，勿手改",
           "# 口径与实验机的 run_summary.py 逐字相同（本脚本直接 import 它，不复制实现）。",
           "# ⚠ 段数 nseg = max(2, min(10, 完成步数//20))：125 步是 6 段，999 步才是 10 段，",
           "#   所以本表的 Seg. SD 与表 I 的 sd_pp 不是同一个段数，不可直接比。",
           "# 四条臂的 code hash 相同（同一代 harness）；cap4 与 Foyer 臂是为本次修订补跑的。",
           "run,steps,wall_min,conc,slo_pct,seg_sd_pp,ttft_p50_ms,policy"]
    body = "\n".join(hdr) + "\n" + "\n".join(
        "%s,%d,%.1f,%.2f,%.1f,%.1f,%d,%s" % (r["run"], r["steps"], r["wall_min"], r["conc"],
                                             r["slo_pct"], r["seg_sd_pp"], r["ttft_p50_ms"],
                                             r["policy"]) for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as f:
        f.write(body)
    print("-> %s（%d 行）" % (out_p, len(rows)))


if __name__ == "__main__":
    main()
