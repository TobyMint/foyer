#!/usr/bin/env python3
"""「有会话在等、却一个都不放行」的周期里，到底是什么在挡？

## 撤回记录（2026-09-24）

本脚本的第一版**是错的，且错得方向相反**。它用日志里的 `base` 字段算投影：

    (d.get("base") or 0) + (d.get("growth_sum") or 0) > d["budget"]

但 `base` 被 controller_budget3.py 的候选循环重绑（`base = s["ctx"] or s["prompt0"]`
写在循环内、日志写在循环后），实测在 `pois200_foyer_hc` 的 8784 个周期里
**恒为 0**。于是那一项退化成 `growth_sum` 单独一个量，报出来的
「投影超预算 0.2%」「98.3% 的周期投影 < 90% 预算」「中位 29%」
**全是 growth reserve 的统计量，不是投影的**。

按正确投影（同 gen_projection.py：`max(resident, ctx_sum) + growth_sum`）重算：
被挡周期里 **44.4% 是投影超预算**、只有 43.7% 低于 90% 预算。
也就是说拦人的主要就是**估算值**，与第一版结论相反。

## 归因的可判定性（诚实标注）

准入判定是一个合取式：

    if waiting and not valve and not gate_full and (prev_started or sf_disabled):
        逐个候选试 projection + n <= budget

- `valve`、`gate_full`、正确的 `projection` 都能从日志直接算 —— 可判定。
- `prev_started`（单飞闸门）**日志里没有**。所以「剩下的是什么」无法直接判定：
  在 sf 开着的臂上，剩下的既可能是「单飞闸门没满足」，也可能是
  「试了队首但塞不进」。本脚本把它单列一档 remainder，并明确标注为不可判定。
- **`sf=0` 的臂是天然的探针**：单飞关掉时 `(prev_started or True)` 恒真，
  闸门不可能拦人，所以它的 remainder 只可能是「没有候选者塞得进预算」。
  拿它可给出单飞贡献的上界。
"""
import glob, json, os, sys


def load(p):
    out = []
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if "budget" in d and "ctx_sum" in d and "growth_sum" in d and "waiting_n" in d:
            out.append(d)
    return out


def proj(d):
    """与 gen_projection.py / 部署代码 322-326 行同一算法。"""
    return max(d.get("resident") or 0, d.get("ctx_sum") or 0) + (d.get("growth_sum") or 0)


def main():
    root = sys.argv[1]
    out_path = sys.argv[2]
    # 只统计控制器臂（有 ctx_sum 的），并把集合显式列出来，避免"十八"这种不可复现的口径
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "*", "controller.jsonl"))):
        run = os.path.basename(os.path.dirname(p))
        if run.startswith("_"):
            continue
        L = load(p)
        if len(L) < 200:
            continue
        # 单飞是否关闭（从 metadata 的 policy 读）
        mp = os.path.join(os.path.dirname(p), "metadata.json")
        pol = ""
        if os.path.exists(mp):
            try:
                pol = json.load(open(mp)).get("policy", "") or ""
            except ValueError:
                pass
        sf_off = "sf=0" in pol
        b = L[-1]["budget"]
        blk = [d for d in L if (d.get("waiting_n") or 0) > 0 and (d.get("n_admitted") or 0) == 0]
        if not blk:
            continue
        n = len(blk)
        valve = sum(1 for d in blk if d.get("valve"))
        gate = sum(1 for d in blk if not d.get("valve") and d.get("gate_full"))
        over = sum(1 for d in blk if not d.get("valve") and not d.get("gate_full")
                   and proj(d) > b)
        rem = n - valve - gate - over
        # starve guard：唯一绕过预算的通道
        forced = sum(1 for d in L if d.get("forced"))
        admits = sum(1 for d in L if (d.get("n_admitted") or 0) > 0)
        rows.append(dict(run=run, n=n, blocked=n, valve=valve, gate=gate, over=over, rem=rem,
                         sf_off=sf_off, forced=forced, admits=admits, samples=len(L)))
    rows.sort(key=lambda r: -r["over"] / r["blocked"])
    print("%-26s %6s %8s %7s %7s %8s %9s %6s" % (
        "run", "采样", "被挡", "阀门%", "gate%", "投影超%", "remainder%", "sf关"))
    for r in rows:
        k = r["blocked"]
        print("%-26s %6d %8d %6.1f %6.1f %7.1f %9.1f %6s" % (
            r["run"], r["samples"], k, 100*r["valve"]/k, 100*r["gate"]/k,
            100*r["over"]/k, 100*r["rem"]/k, "Y" if r["sf_off"] else ""))
    with open(out_path, "w") as f:
        f.write("# 「有等待不放行」周期的闸门归因 —— gen_gate_attrib.py 生成\n")
        f.write("# 投影 = max(resident, ctx_sum) + growth_sum（【不是】被重绑污染的 base 字段）\n")
        f.write("# remainder = 排除 valve/gate/投影超预算后剩下的，含【单飞闸门】与【队首塞不进】两类，\n")
        f.write("#   日志里没有 prev_started，无法区分，故不做单飞归因。sf_off=Y 的臂是探针：\n")
        f.write("#   单飞关闭时闸门不可能拦人，其 remainder 只可能是「没有候选者塞得进预算」。\n")
        f.write("run,samples,blocked_cycles,valve_pct,round_gate_pct,projection_over_pct,"
                "remainder_pct,sf_disabled\n")
        for r in rows:
            k = r["blocked"]
            f.write("%s,%d,%d,%.1f,%.1f,%.1f,%.1f,%s\n" % (
                r["run"], r["samples"], k, 100*r["valve"]/k, 100*r["gate"]/k,
                100*r["over"]/k, 100*r["rem"]/k, "Y" if r["sf_off"] else "N"))
    print("-> %s" % out_path)


if __name__ == "__main__":
    main()
