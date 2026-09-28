#!/usr/bin/env python3
"""独立复算「墙钟两段分解」—— 【不 import 生成器】，从 metrics.csv 直接算。

为什么要有：C1（墙钟 = busy + idle）是论文的**第一条机制**，而 τ₁ 的分母也在这里
（`τ₁ = W_busy · R̄_busy / G`）—— τ₁ 又喂给 §IV 的 ε、ε 又喂给判据。
`gen_decomp.decompose` 是它唯一的实现，`gen_arm_running.busy_fraction` 等下游都 import 它
（共用定义是对的），但**如果那份实现本身有 off-by-one 或断档处理写错，所有守卫会与它一致地错**。

**规则照抄 `decompose` 的定义**（论文 C1）：
  相邻两个采样之间的那段时长，按【前一个】采样的 `sglang:num_running_reqs` 归类：
  >0 → busy，==0 → idle，None 或 `dt > 3×采样间隔`（断档）→ 既不算 busy 也不算 idle。
  `span = 末采样 ts − 首采样 ts`，且 busy + idle + 断档 必须 == span。

本脚本**另写一遍**（自己读 CSV、自己遍历、自己判断档），与 `paper/data/decomp.csv`
逐行对拍（容差按该表的精度），并**单独报告断档时长**（生成器里是断言 other == 0，
这里把非零的情况打出来而不是直接炸 —— 便于判断是数据问题还是实现问题）。

用法: python3 independent_decomp_check.py <results_dir> <decomp.csv> [采样间隔秒，默认 5]
"""
import csv, os, sys

SAMPLE_S = 5.0


def read_metrics(path):
    """自己读：返回 [(ts, num_running_reqs_or_None)]。"""
    out = []
    with open(path) as f:
        hdr = f.readline().rstrip("\n").split(",")
        if "sglang:num_running_reqs" not in hdr or "ts" not in hdr:
            raise RuntimeError("%s 缺少 ts 或 sglang:num_running_reqs 列" % path)
        i_ts, i_rn = hdr.index("ts"), hdr.index("sglang:num_running_reqs")
        for line in f:
            c = line.rstrip("\n").split(",")
            if len(c) <= max(i_ts, i_rn):
                continue
            try:
                ts = float(c[i_ts])
            except ValueError:
                continue
            v = c[i_rn].strip()
            out.append((ts, None if v in ("", "None") else float(v)))
    return out


def split(rows, sample_s=SAMPLE_S):
    """独立实现的两段分解。返回 (span_min, busy_min, idle_min, idle_pct, other_s)。"""
    span = rows[-1][0] - rows[0][0]
    busy = idle = other = 0.0
    for (t0, r0), (t1, _) in zip(rows, rows[1:]):
        dt = t1 - t0
        if dt <= 0 or dt > sample_s * 3:
            other += dt
        elif r0 is None:
            other += dt
        elif r0 == 0:
            idle += dt
        else:
            busy += dt
    return span / 60, busy / 60, idle / 60, (100 * idle / span if span else 0.0), other


def main():
    root, dec_p = sys.argv[1], sys.argv[2]
    sample_s = float(sys.argv[3]) if len(sys.argv) > 3 else SAMPLE_S
    ref = {r["run"]: r for r in csv.DictReader(l for l in open(dec_p) if not l.startswith("#"))}
    # ⚠ 容差按**被比表真正存的精度**定。我先按「4 位小数」写了 5e-5，于是 34 条全报
    # 「不符」—— 全是**假警报**：`decomp.csv` 的 busy_min / idle_pct 其实存的是
    # **1 位小数**（225.2 / 14.0），本脚本算的是 225.19163 / 14.02612。
    # 判据是「本脚本四舍五入到表的那一位后相等」⇒ 半个末位 0.05。
    # （同一晚我在 ε 那条线上也犯过一次：拿 2e-3 去比两位小数的表。**先看表，再定容差**。）
    tol = 0.05 + 1e-9
    bad = 0
    print("%-16s %9s %9s %9s %9s  %s" %
          ("run", "busy(算)", "busy(表)", "idle%(算)", "idle%(表)", "断档秒"))
    for name in sorted(ref):
        # 目录名：主 trace 是 `pois200_<name>`，第二条 trace 是裸 `<name>`
        d = os.path.join(root, "pois200_" + name)
        if not os.path.exists(os.path.join(d, "metrics.csv")):
            d = os.path.join(root, name)
        mp = os.path.join(d, "metrics.csv")
        if not os.path.exists(mp):
            print("%-16s 找不到 metrics.csv（两种命名都试过）" % name)
            bad += 1
            continue
        rows = read_metrics(mp)
        if len(rows) < 3:
            print("%-16s 采样只有 %d 条" % (name, len(rows)))
            bad += 1
            continue
        span, busy, idle, pct, other = split(rows, sample_s)
        b_ref = float(ref[name]["busy_min"])
        p_ref = float(ref[name]["idle_pct"])
        ok = abs(busy - b_ref) <= tol and abs(pct - p_ref) <= tol
        if not ok:
            bad += 1
        print("%-16s %9.4f %9.4f %9.4f %9.4f  %.1f%s"
              % (name, busy, b_ref, pct, p_ref, other, "" if ok else "   <<<"))
    print()
    if bad:
        print("!! %d 条不符 —— 以本脚本为准去查 gen_decomp.decompose" % bad)
    else:
        print("结论：全部相符（独立重算的 busy/idle 与 decomp.csv 逐行一致）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
