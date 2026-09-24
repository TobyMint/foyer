#!/usr/bin/env python3
"""前缀复用的天花板 vs 内存梯队 —— paper/data/reuse.csv。

这条是把 §III 的 token 账从「驱逐→重算」推进到「梯队决定复用能不能兑现」。
出发点是一个此前没被拆开的量：**总复用** = 设备侧命中 + host 侧接住。

从 paper/data/eviction.csv 读（那三个量已在那里带断言算出），本脚本只做派生，
不重新数日志 —— 避免同一个量在两处各算一遍然后对不上。

```
device-only（池子 = 101432 token，无 host 梯队）
  cap1        R̄ 1.00   复用 19.9 M   重算  8.6 M
  cap2        R̄ 1.27   复用 19.3 M   重算  9.2 M
  cap3_fixed  R̄ 1.53   复用 17.0 M   重算 11.5 M
  cap4        R̄ 1.65   复用 13.1 M   重算 15.4 M
  cap5        R̄ 1.84   复用  7.8 M   重算 20.7 M   <- 天花板兑现不了

HiCache（设备池同样 101432，另有 host 梯队）
  pairB_cap2hc R̄ 1.25  复用 19.9 M   重算  8.6 M
  cap3_hc      R̄ 1.51  复用 19.6 M   重算  8.9 M
  cap4_hc      R̄ 1.73  复用 19.4 M   重算  9.1 M   <- 天花板守住了
```

**天花板本身是 trace 的性质**（该 trace 前缀结构允许的复用上限 ≈ 19.9 M，对应计划
命中率 ~70%），**由谁兑现是配置的性质**。device-only 在 R̄ 过了 1.3 就兑现不了，
HiCache 在控制器整个运行区间内都兑现。

注意 HiCache 的**设备侧命中反而更少**（cap4_hc 设备未命中 22.4 M，比 device-only 的
cap4 的 15.4 M 还多）—— 设备 miss 多而复用不少，差额正是 host 接住的 13.3 M。
所以「看设备命中率」会得出与「看复用」相反的方向，这也是为什么这一列必须单列。

用法: python3 gen_reuse.py paper/data/eviction.csv paper/data/arm_running.csv \
                        paper/data/decomp.csv paper/data/reuse.csv
"""
import csv, os, sys


def load(p):
    return {r["run"]: r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))}


def main():
    ev_p, ar_p, dc_p, out_p = sys.argv[1:5]
    ev, ar, dc = load(ev_p), load(ar_p), load(dc_p)
    # 争用标记：被主机争用抬高了 tau 的 run 不能拿 tau 列当证据。
    # 复用列（reuse_*/recompute_M）是【体积比】，与时间无关，不受争用影响 ——
    # 实测这四条臂的 reuse 与同族干净 run 一致（0.691~0.694），只有 tau 被抬高。
    conc = {}
    if len(sys.argv) > 5 and os.path.exists(sys.argv[5]):
        # 注意去掉 pois200_ 前缀再配对：eviction.csv 用的是短名（cap1 / foyer_hz2），
        # concurrency.csv 用的是 run 目录名（pois200_cap1 / pois200_foyer_hz2）。
        # 不归一化会静默全部落空，contested 列全变成 "?"（2026-09-24 犯过一次）。
        conc = {r["run"].replace("pois200_", ""): r["verdict"] for r in
                csv.DictReader(l for l in open(sys.argv[5]) if not l.startswith("#"))}
        assert len(conc) > 50, "concurrency.csv 只读到 %d 行，路径或格式不对" % len(conc)

    rows, bad = [], []
    for run, e in ev.items():
        a, d = ar.get(run), dc.get(run)
        if not a or not d:
            bad.append((run, "arm_running 或 decomp 里没有这条"))
            continue
        prompt = float(e["prompt_M"])
        dev_miss = float(e["dev_miss_M"])
        host_hit = float(e["host_hit_M"])
        unc = float(e["uncached_M"])
        reuse_dev = prompt - dev_miss
        reuse_tot = reuse_dev + host_hit

        # 断言 1：设备未命中 = host 接住 + 真正重算。这是这套记账的定义式，
        # 挡住的是从 eviction.csv 抄错列（抄错不会有这个性质）。
        assert abs(dev_miss - (host_hit + unc)) < 0.15, \
            "%s: dev_miss %.1f != host_hit %.1f + uncached %.1f" % (run, dev_miss, host_hit, unc)
        # 断言 2：复用 + 重算 = 总 prompt
        assert abs(reuse_tot + unc - prompt) < 0.15, \
            "%s: reuse %.1f + uncached %.1f != prompt %.1f" % (run, reuse_tot, unc, prompt)

        rows.append({
            "run": run,
            "family": "hicache" if e["hicache"] == "1" else "device_only",
            "Rbar_busy": a["running_busy"],
            "prompt_M": "%.1f" % prompt,
            "reuse_dev_M": "%.1f" % reuse_dev,
            "reuse_host_M": "%.1f" % host_hit,
            "reuse_total_M": "%.1f" % reuse_tot,
            "reuse_frac": "%.3f" % (reuse_tot / prompt),
            "recompute_M": "%.1f" % unc,
            "tau1_ms": d["step_back_ms"],
            "contested": conc.get(run, "?"),
        })

    rows.sort(key=lambda r: (r["family"], float(r["Rbar_busy"])))
    header = "\n".join([
        "# 前缀复用的天花板 vs 内存梯队 —— 由 scripts/lab/gen_reuse.py 生成，勿手改",
        "# reuse_dev_M   = prompt - dev_miss       设备侧 radix cache 兑现的复用",
        "# reuse_host_M  = host 梯队接住的（device-only 恒为 0）",
        "# reuse_total_M = 两者之和 = 真正没有重算的那部分 prompt",
        "# reuse_frac    = reuse_total / prompt —— device-only 随 R̄ 塌，hicache 守住",
        "# 天花板（trace 允许的最大复用）≈ 19.9 M；兑现它与否是【配置】的属性",
        "# contested: 该 run 是否落在主机争用窗口里（见 concurrency.csv）。CONTESTED 的",
        "#            tau1_ms 列不可用；reuse_* 是体积比，与时间无关，不受争用影响。",
        "run,family,Rbar_busy,prompt_M,reuse_dev_M,reuse_host_M,reuse_total_M,reuse_frac,recompute_M,tau1_ms,contested"])
    fields = ["run", "family", "Rbar_busy", "prompt_M", "reuse_dev_M", "reuse_host_M",
              "reuse_total_M", "reuse_frac", "recompute_M", "tau1_ms", "contested"]
    body = header + "\n" + "\n".join(",".join(str(r[k]) for k in fields) for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as fh:
        fh.write(body)

    print("写入 %s：%d 行" % (out_p, len(rows)))
    for r in rows:
        print("  %-16s %-11s R̄ %-6s 复用 %5s M (%.3f)  重算 %5s M  τ₁ %-6s %s" % (
            r["run"], r["family"], r["Rbar_busy"], r["reuse_total_M"],
            float(r["reuse_frac"]), r["recompute_M"], r["tau1_ms"],
            "<<CONTESTED" if r["contested"] == "CONTESTED" else ""))
    if bad:
        print("!! 未写入：")
        for n, why in bad:
            print("   %-16s %s" % (n, why))


if __name__ == "__main__":
    main()
