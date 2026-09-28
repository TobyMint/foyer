#!/usr/bin/env python3
"""每步时间的构成：prefill 份量 vs decode 份量 —— 检验「控制器步成本更高是不是因为 prefill 扎堆」。

动机：gen_wall_split.py 测出 foyer_bres 与 cap3_hc 的 Rbar 几乎相同（1.48 vs 1.51），
tau 却差 22%（34.1 vs 28.0 ms）。epsilon 框架假设 tau 只是 Rbar 的函数，解释不了这个。
一个可测的假设：控制器每 2 秒一个准入周期、一次放多个会话，prefill 因此扎堆；
静态 cap 的名额随会话结束逐个释放，准入被摊平。

若成立：控制器的 prefill 占比（prompt token / 总 token）应系统性高于同 Rbar 的静态 cap。

口径：全部来自 metrics.csv 的累计计数器，取 run 末值。
  prefill_share = prompt_tokens_total / (prompt_tokens_total + generation_tokens_total)
注意 sglang:token_usage 是【分数】不是 token 数（本项目犯过这个错），这里不用它。
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
DEC = os.path.join(ROOT, "paper", "data", "decomp.csv")

def last_counters(path):
    with open(path) as f:
        hdr = f.readline().strip().split(",")
        if "sglang:prompt_tokens_total" not in hdr:
            return None
        ip, ig = hdr.index("sglang:prompt_tokens_total"), hdr.index("sglang:generation_tokens_total")
        last = None
        for line in f:
            c = line.rstrip("\n").split(",")
            if len(c) <= max(ip, ig):
                continue
            try:
                last = (float(c[ip]), float(c[ig]))
            except ValueError:
                continue
        return last

def main():
    dec = {r["run"]: r for r in csv.DictReader(l for l in open(DEC) if not l.startswith("#"))}
    # 找每个 run 的 metrics.csv
    cand = [os.path.join(ROOT, "results", "night"), os.path.join(ROOT, "results")]
    rows = []
    for run in dec:
        p = None
        for c in cand:
            # ⚠⚠ 2026-09-27（r57 中立复核）：**顺序原来是反的** ——
            # 先试裸名 `<run>`、再试 `pois200_<run>`，而本地镜像里
            # `aimd2_paper` / `cap4` / `default` **三个短名目录与 `pois200_` 目录同时存在**
            # ⇒ 裸名**遮蔽**了长名，读到的是**另一个 run** 的计数器
            # （实测 `aimd2_paper` 那行从 28469904/705216 变成 3114662/78733，约 1/9）。
            # `pois200_` **优先**：它是本工作负载的规范家族，也是 `decomp.csv` 的 run 列
            # 唯一能对上的一族（39 条全部 1:1 映射到 `pois200_*`，反解 0 条落空）。
            # ⚠ 同一个坑在 `scripts/lab/regen_all.sh` 的 `recover_runs()` 里也出现过一次 ——
            # **凡「短名 vs 前缀名」并列可解析的地方，一律前缀优先。**
            for d in (os.path.join(c, "pois200_" + run), os.path.join(c, run)):
                if os.path.exists(os.path.join(d, "metrics.csv")):
                    p = os.path.join(d, "metrics.csv"); break
            if p: break
        if not p:
            print("  [缺 metrics] %s" % run); continue
        ct = last_counters(p)
        if not ct:
            print("  [缺列] %s" % run); continue
        pt, gt = ct
        tot = pt + gt
        share = pt / tot if tot else float("nan")
        r = dec[run]
        rows.append((run, float(r["running"]), float(r["step_back_ms"]), share, pt, gt))

    rows.sort(key=lambda x: x[1])
    print("%-14s %6s %9s %10s %12s %12s" % ("run", "Rbar", "tau1(ms)", "prefill占比", "prompt_tok", "gen_tok"))
    for run, rb, tau, share, pt, gt in rows:
        print("%-14s %6.2f %9.1f %9.1f%% %12.0f %12.0f" % (run, rb, tau, 100 * share, pt, gt))

    # 分组对照：同 Rbar 区间内，控制器 vs 静态 cap
    print()
    statics = [r for r in rows if not r[0].startswith(("foyer", "aimd"))]
    ctrls   = [r for r in rows if r[0].startswith(("foyer", "aimd"))]
    def mid(v): 
        v = sorted(v); return v[len(v)//2] if v else float("nan")
    print("静态 cap   prefill 占比 中位 %.1f%%（%d 条）" % (100 * mid([r[3] for r in statics]), len(statics)))
    print("控制器臂   prefill 占比 中位 %.1f%%（%d 条）" % (100 * mid([r[3] for r in ctrls]), len(ctrls)))

    out = os.path.join(ROOT, "paper", "data", "prefill_share.csv")
    with open(out, "w") as f:
        f.write("# prefill 占比 vs 步成本 —— gen_prefill_share.py 生成\n")
        f.write("# 口径：metrics.csv 累计计数器末值；prefill_share = prompt/(prompt+generation)\n")
        f.write("run,Rbar_busy,tau1_ms,prefill_share,prompt_tokens,generation_tokens,family\n")
        for run, rb, tau, share, pt, gt in rows:
            fam = "controller" if run.startswith(("foyer", "aimd")) else "static"
            f.write("%s,%.3f,%.1f,%.4f,%.0f,%.0f,%s\n" % (run, rb, tau, share, pt, gt, fam))
    print("-> %s" % out)

if __name__ == "__main__":
    main()
