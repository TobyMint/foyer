#!/usr/bin/env python3
"""每个 paper/data/*.csv 里提到的 run，本地镜像里到底有没有 —— 一遍过。

为什么需要：本项目的「生成器静默丢 run」已经栽过三次（foyer_hz1 从 eviction.csv
无声消失、runs_precise.csv 漏掉四条步数不足 999 的 run、本地镜像比实验机少 20+
个目录让 gen_concurrency 把 var_cap3 从 CONTESTED 判成 clean）。前两次是列表不全，
第三次是【镜像不全】—— 这一类比列表更难发现，因为脚本本身没错、输入看着也正常。

本脚本不修任何东西，只回答：paper/data 里被引用的 run，本地有没有它的原始日志？
输出分三档：OK / 缺目录 / 目录在但缺关键文件。**只对本地镜像负责** ——
真正权威的是实验机上的目录。

用法: python3 data_run_coverage.py [results_dir]
"""
import csv, glob, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DATA = os.path.join(ROOT, "paper", "data")
ROOT_DIRS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "night")

# 一份 CSV 里哪一列是 run 名（不是所有表都叫 run）
RUNCOL = {"reuse.csv": "run", "reuse_x.csv": "run", "runs.csv": "run",
          "runs_precise.csv": "run", "table1.csv": "run", "slope.csv": "from_run",
          "concurrency.csv": "run", "eviction.csv": "run", "occupancy.csv": "run",
          "decomp.csv": "run", "arm_running.csv": "run", "attribution.csv": "run",
          "tier25.csv": "run", "horizon.csv": "run", "elasticity.csv": "run",
          "elasticity_hc.csv": "run", "projection.csv": "run", "replicates.csv": "run",
          "gate_attrib.csv": "run", "nocontrol.csv": "run", "idle_seg_raw.csv": "run",
          "elasticity_x.csv": "run", "slo_sensitivity.csv": "run"}
# 除 run 名之外还有第二个 run 列的表
EXTRA = {"slope.csv": ["to_run"], "table1.csv": []}


def main():
    have = {}
    for d in os.listdir(ROOT_DIRS):
        p = os.path.join(ROOT_DIRS, d)
        if os.path.isdir(p):
            have[d] = set(os.listdir(p))
    print("镜像目录 %d 个：%s" % (len(have), ROOT_DIRS))
    missing_dir, missing_file, seen = [], [], 0
    for f in sorted(glob.glob(os.path.join(DATA, "*.csv"))):
        base = os.path.basename(f)
        col = RUNCOL.get(base)
        if not col:
            continue
        rows = list(csv.DictReader(l for l in open(f) if not l.startswith("#")))
        if not rows or col not in rows[0]:
            continue
        names = {r[col] for r in rows if r.get(col)}
        for c2 in EXTRA.get(base, []):
            names |= {r[c2] for r in rows if r.get(c2)}
        for n in sorted(names):
            seen += 1
            # run 名的三种写法都试：短名（cap1）、pois200_ 前缀、控制器短名
            # （slo_sensitivity.csv 里写的是 hz1/hc/bres，目录是 pois200_foyer_hz1）。
            # 纯数字的格子不是 run 名（slo_sensitivity.csv 的阈值列曾把 "10.0" 当 run）。
            try:
                float(n); continue
            except ValueError:
                pass
            cands = [n] + ([] if n.startswith("pois200_") else
                           ["pois200_" + n, "pois200_foyer_" + n])
            d = next((c for c in cands if c in have), None)
            if d is None:
                missing_dir.append((base, n)); continue
            # 关键文件：没有 steps.jsonl 就无法从原始日志复算
            if "steps.jsonl" not in have[d]:
                missing_file.append((base, n))
    print("\n被 paper/data 引用的 run 名 %d 个" % seen)
    print("  缺目录（本地镜像没有）：%d" % len(missing_dir))
    for b, n in missing_dir:
        print("     %-24s %s" % (b, n))
    print("  目录在但缺 steps.jsonl：%d" % len(missing_file))
    for b, n in missing_file:
        print("     %-24s %s" % (b, n))
    print("\n注意：本地镜像不全不代表数据错 —— 权威在实验机。缺的要么补 rsync，"
          "要么确认该 CSV 的生成器是在实验机上跑的。")


if __name__ == "__main__":
    main()
