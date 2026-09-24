#!/usr/bin/env python3
"""单飞闸门干预实验的配对分析 —— sf=0 对基础臂。

## 这个实验是什么

`pois200_foyer_sf0`（以及重跑 `_r2`）与 `pois200_foyer_hc`(`_r2`) 的配置**逐字相同**
（budget3:hw=0;target=0.95），只差一个 flag：前者 `sf=0`（关掉单飞闸门）。
同一 trace、同一池子、同型号卡。

它检验的是 §V 里那条归因：控制器「有会话在等却一个不放」的周期里，最大的一项
测不出是「单飞闸门」还是「队首塞不进」。关掉单飞就能把这一项隔离出来。

## 判据（看结果前定死）

1. 主判据：墙钟与 SLO@10s（口径同 run_summary.py / frontier.py），
   并按 frontier.py 的锚点算相对前沿的距离 Δ。
   |Δ| <= 1.0pp 记为打平。
2. 机制判据：若 sf=0 生效，它的准入周期占比应显著高于基础臂，
   且「有等待不放行」的周期占比应显著低于基础臂 —— 否则说明这个 flag
   没有真正改变行为，实验无效（先报这个，再报性能）。
3. 无效条件：任一条 run 未跑满 999 步，或非成功步 > 0，则不与跑满的比较，
   只作部分观测报告。
"""
import json, os, sys, csv, statistics

N = "/data/xbw/turnstile/results/night"
PAIRS = [("pois200_foyer_hc", "单飞开（基准）"),
         ("pois200_foyer_hc_r2", "单飞开（重复）"),
         ("pois200_foyer_sf0", "单飞关（第一次，曾被 SIGTERM）"),
         ("pois200_foyer_sf0_r2", "单飞关")]


def runinfo(d):
    p = os.path.join(N, d, "summary.json")
    if not os.path.exists(p):
        return None
    s = json.load(open(p)); r = s.get("replay", {})
    return dict(attempted=r.get("attempted_steps"), success=r.get("success_steps"),
                failed=r.get("failed_steps"))


def ctrlstats(d):
    """从 controller.jsonl 读：准入周期占比、有等待不放行占比、投影超预算占比。"""
    p = os.path.join(N, d, "controller.jsonl")
    if not os.path.exists(p):
        return None
    n = admit = wq = over = 0
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if "budget" not in j or "ctx_sum" not in j:
            continue
        n += 1
        if (j.get("n_admitted") or 0) > 0:
            admit += 1
        if (j.get("waiting_n") or 0) > 0 and (j.get("n_admitted") or 0) == 0:
            wq += 1
        proj = max(j.get("resident") or 0, j.get("ctx_sum") or 0) + (j.get("growth_sum") or 0)
        if proj > j["budget"]:
            over += 1
    if n == 0:
        return None
    return dict(n=n, admit_pct=100.0 * admit / n, waiting_blocked_pct=100.0 * wq / n,
                proj_over_pct=100.0 * over / n)


def main():
    print("%-26s %-22s %8s %8s %8s" % ("run", "说明", "步数", "成功", "失败"))
    for d, note in PAIRS:
        i = runinfo(d)
        if i:
            print("%-26s %-22s %8s %8s %8s" % (d, note, i["attempted"], i["success"], i["failed"]))
        else:
            print("%-26s %-22s %8s" % (d, note, "[无 summary]"))
    print()
    print("=== 机制判据：flag 是否真的改变了行为 ===")
    print("%-26s %10s %12s %12s" % ("run", "周期数", "准入周期%", "有等待不放行%"))
    for d, note in PAIRS:
        c = ctrlstats(d)
        if c:
            print("%-26s %10d %11.1f%% %11.1f%%" % (d, c["n"], c["admit_pct"], c["waiting_blocked_pct"]))
    print()
    print("=== 性能（由 run_summary.py 提供，本脚本不重复实现）===")
    print("    跑: python3 scripts/run_summary.py pois200_foyer_hc pois200_foyer_hc_r2 \\")
    print("            pois200_foyer_sf0_r2")
    print("    判决: python3 frontier.py pois200_foyer_hc pois200_foyer_sf0_r2")


if __name__ == "__main__":
    main()
