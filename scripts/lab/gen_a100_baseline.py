#!/usr/bin/env python3
"""A100 上**无准入控制基线**的两次尝试 —— §\ref{sec:a100} 末段引的每个数都出自这里。

为什么要单独一张表：§A100 现在写着「我们排的干净重跑也没跑成，两个说法一致」，
引了池子 817,527、占用中位 95.3%、watcher 566/566、148.1 分钟、32.9%、222.7 ms、
以及第一次尝试的 23.7 分钟 / 82 of 341。**这些数此前只存在于终端输出里** ——
CLAUDE.md 的证据纪律要求它们落到 `paper/data/*.csv`。

用法: python3 gen_a100_baseline.py <results_dir> <out.csv>
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_a100 as _GA          # noqa: E402  τ₂ / 占用 / 墙钟的唯一实现
import gpu_watch_summary as _GW  # noqa: E402  run_window 的唯一实现

# 两次尝试，顺序即正文顺序。**名字写死**：这两个 run 的身份就是「第几次尝试」，
# 按模式匹配会把以后第三次尝试也算进来，而正文说的正是「两次都没成」。
ATTEMPTS = [("a100_default", 1), ("a100_default_r2", 2)]


def watcher(d):
    """(窗内采样数, 含外人的采样数, 第一条含外人的时刻, 最后一条含外人的时刻)。

    ⚠ **必须按 run 窗口裁**（`gpu_watch_summary.run_window`）：孤儿 watcher 会在
    run 结束之后继续追加几天（2026-09-26 抓到过），不裁窗口的话一条干净 run
    会被判成脏。这里两个 run 的 watcher 都正常，但判据不能靠这个。
    """
    p = os.path.join(d, "gpu_watch.jsonl")
    if not os.path.exists(p):
        return None
    ev = [json.loads(l) for l in open(p) if l.strip()]
    s = [e for e in ev if "n_foreign" in e]
    w = _GW.run_window(d)
    if w:
        s = [e for e in s if w[0] <= e["ts"] <= w[1]]
    bad = [e for e in s if e["n_foreign"] > 0]
    return dict(n=len(s), n_foreign=len(bad),
                first=bad[0]["ts"] if bad else None,
                last=bad[-1]["ts"] if bad else None,
                t_end=w[1] if w else None)


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows, notes = [], []
    for r, k in ATTEMPTS:
        d = os.path.join(root, r)
        if not os.path.exists(os.path.join(d, "steps.jsonl")):
            raise SystemExit("!! %s 不在镜像里 —— 缺 run 不能静默少一行" % d)
        st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
        # 墙钟与 SLO 走 `gen_a100.wall_slo_of`（与 `one()` 同一份实现）——
        # 原来这里各写了一遍，同文件里 τ₂/占用已 import、这两个没 import。
        wall, slo = _GA.wall_slo_of(st)
        # 复用列**不报**：r2 的实测 prompt 比计划少 126,897（2 步失败），
        # `prompt - uncached` 会把缺口算成复用（见 gen_a100.one 的断言）。
        # 正文不用它，这里也就不印，免得下一个人拿去用。
        p50, mean = _GA.occ_stats(d)
        m = json.load(open(os.path.join(d, "metadata.json")))
        w = watcher(d)
        if w is None:
            raise SystemExit("!! %s 没有 gpu_watch.jsonl —— 争用判据缺失，不猜" % d)
        rows.append(dict(
            run=r, attempt=k, pool_tokens=m.get("pool_tokens") or 0,
            wall_min="%.4f" % wall, slo_pct="%.4f" % slo,
            steps=len(st),
            failed_steps=sum(1 for x in st if (x.get("status") or "") != "SUCCESS"),
            tau2_ms="%.4f" % _GA.tau2_of(st),
            occ_p50_pct="%.4f" % p50, occ_mean_pct="%.4f" % mean,
            watch_n=w["n"], watch_foreign=w["n_foreign"],
            dirty_span_min=("%.4f" % ((w["last"] - w["first"]) / 60.0)
                            if w["first"] is not None else ""),
            dirty_before_end_min=("%.4f" % ((w["t_end"] - w["first"]) / 60.0)
                                  if w["first"] is not None else ""),
        ))
        print("%-18s 第 %d 次  pool=%d  wall=%.4f min  SLO=%.4f%%  τ₂=%.1f ms  "
              "占用p50=%.1f%%  watcher %d/%d 含外人"
              % (r, k, rows[-1]["pool_tokens"], wall, slo, float(rows[-1]["tau2_ms"]),
                 p50, w["n_foreign"], w["n"]))

    # 正文引的两个对照量，**现算**而不是写死在注释里：
    # 表 II 十二个静态 run 的 τ₂ 最大值（正文写「ten times the 21.4 ms maximum」），
    # 以及它们占用率的上界（写「against their 2--12%」的是 §a100:limits 里
    # 那三个短池子 run —— 这里只报全表上界，具体区间由那条披露负责）。
    # ⚠ `a100.csv` **同时装着 3090 的对照行**（cap1..cap5），全表 τ₂ 上界是
    # 3090 cap5 的 31.2 ms。正文说的是**这个 tier 上**的静态 run —— 必须按
    # `a100_` 前缀取，否则会写出一个属于另一张卡的数（本项目的「从错的列抄数」）。
    a100 = os.path.join(os.path.dirname(out), "a100.csv")
    if not os.path.exists(a100):
        raise SystemExit("!! 找不到 %s —— 对照量算不出来，不许印问号糊过去" % a100)
    rr = [x for x in csv.DictReader(l for l in open(a100) if not l.startswith("#"))
          if x["run"].startswith("a100") and x.get("tau2_ms")]
    if not rr:
        raise SystemExit("!! %s 里没有 a100_ 开头的行 —— 对照集合是空的" % a100)
    mx, n = max(float(x["tau2_ms"]) for x in rr), len(rr)
    notes.append("# 本 tier 的 %s 个静态 run 的 τ₂ 上界 = %s ms"
                 "（正文写 “ten times the 21.4 ms maximum”）"
                 % (n, "%.1f" % mx if mx is not None else "?"))
    notes.append("# 复用列【不报】：第 2 次尝试有 2 步失败，实测 prompt 比计划少 126,897，"
                 "`prompt - uncached` 会把缺口算成复用（gen_a100.one 的断言会直接退出）。")

    with open(out, "w", newline="") as f:
        for n in notes:
            f.write(n + "\n")
        f.write("# 由 scripts/lab/gen_a100_baseline.py 生成；两次尝试都不是可用的基线\n")
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
