#!/usr/bin/env python3
"""把三条 run 的全部指标合成一张表（论文表 II/III/IV 的唯一数据源）。

用法：
    python3 gen_arms_table.py --arm A=<run_dir> --arm B=<run_dir> --arm C=<run_dir> \
        [--csv out.csv] [--common]

它本身**不实现任何指标**：三个量分别由
    slo_goodput.py     （makespan / 端到端 / round latency / miss / goodput）
    gen_work_decomp.py （busy-idle / device-host 命中 / 重读税）
    gen_miss_attrib.py （重算归因）
算出来，这里只负责调用 + 按 (metric, arm) 拼成宽表。这样口径永远只有一份。

`--common`：先算三条 run 的**共同完成集**（`atonce_report.common_set`），
再在共同集上重算 makespan/工作量。三臂少跑的轮次不一样（C 就因为一个会话
在第 21 轮连接断开而少了 59 轮），直接比 makespan 不公平。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run_script(script, args, out_csv):
    cmd = [sys.executable, os.path.join(HERE, script)] + args + ["--csv", out_csv]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("!! %s 失败：%s" % (script, r.stderr.strip()[:300]))
        return None
    return out_csv


def read_kv(path):
    """两列 key,value 的 CSV → dict（gen_trace_facts / gen_engine_constants 用这种格式）。"""
    import csv
    d = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            d[row["key"]] = row["value"]
    return d


def read_rows(path):
    import csv
    with open(path) as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, help="NAME=dir")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--common", action="store_true")
    a = ap.parse_args()

    arms = []
    for spec in a.arm:
        name, d = spec.split("=", 1)
        arms.append((name, d))

    tmp = tempfile.mkdtemp(prefix="arms_")
    table = {}   # metric -> {arm: value}

    def put(metric, arm, val):
        table.setdefault(metric, {})[arm] = val

    for name, d in arms:
        # 1) SLO / 端到端
        p = run_script("slo_goodput.py", [d], os.path.join(tmp, "slo_%s.csv" % name))
        if p:
            for row in read_rows(p):
                for k, v in row.items():
                    if k != "run":
                        put("slo." + k, name, v)
        # 2) 分解
        p = run_script("gen_work_decomp.py", [d], os.path.join(tmp, "wd_%s.csv" % name))
        if p:
            for row in read_rows(p):
                for k, v in row.items():
                    if k != "run":
                        put("wd." + k, name, v)
        # 3) 重算归因
        p = run_script("gen_miss_attrib.py", [d], os.path.join(tmp, "ma_%s.csv" % name))
        if p:
            for row in read_rows(p):
                cls = row.pop("class")
                row.pop("run", None)
                for k, v in row.items():
                    put("ma.%s.%s" % (cls, k), name, v)

    # 4) 共同完成集（可选）
    if a.common:
        sys.path.insert(0, HERE)
        from atonce_report import common_set, report_on
        dirs = [d for _, d in arms]
        common, _ = common_set(dirs)
        print("共同完成集：%d 步" % len(common))
        for name, d in arms:
            r = report_on(d, common)
            for k in ("makespan_min", "work_Mtok", "n_steps", "n_sessions"):
                put("common." + k, name, r[k])

    # ---- 输出宽表 ----
    arm_names = [n for n, _ in arms]
    metrics = sorted(table)
    if a.csv:
        os.makedirs(os.path.dirname(os.path.abspath(a.csv)), exist_ok=True)
        with open(a.csv, "w") as f:
            f.write("metric," + ",".join(arm_names) + "\n")
            for m in metrics:
                f.write(m + "," + ",".join(str(table[m].get(n, "")) for n in arm_names) + "\n")
        print("写 %s（%d 行指标 × %d 臂）" % (a.csv, len(metrics), len(arm_names)))

    # ---- 控制台摘要（论文里真会引的那些）----
    keys = ["slo.makespan_min", "slo.n_steps", "slo.e2e_med_min", "slo.e2e_p90_min",
            "slo.round_p50_s", "slo.round_p90_s", "slo.miss10_round_pct",
            "slo.goodput_steps_per_h", "slo.work_Mtok",
            "wd.busy_pct", "wd.idle_min", "wd.hit_pct", "wd.dev_hit_pct",
            "wd.host_hit_pct", "wd.reread_x", "wd.evict_Mtok",
            "ma.suspended.uncached_pct", "ma.suspended.excess_x"]
    if a.common:
        keys = ["common.n_steps", "common.makespan_min", "common.work_Mtok"] + keys
    print("%-28s %s" % ("metric", " ".join("%12s" % n for n in arm_names)))
    for k in keys:
        if k in table:
            print("%-28s %s" % (k, " ".join("%12s" % table[k].get(n, "-") for n in arm_names)))


if __name__ == "__main__":
    main()
