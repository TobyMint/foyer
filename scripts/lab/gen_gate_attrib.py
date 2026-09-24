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


# 论文正文引用的统计集合 —— 【显式列名】，不再用"十九条"这种无法复现的口径。
# 这是 Table I 的控制器段（九条 Foyer 变体 + 两个 AIMD 设置）。
# 九条 Foyer 变体里，有八条留了 controller.jsonl；foyfix_hc 与两个 AIMD 没有
# （AIMD 走另一套控制器），所以它们不在本表里 —— 正文必须按这八条写。
# 论文里引用的臂，显式列出（避免"十八条"这种不可复现的口径）。
# ⚠ foyer_sf0_r2 必须在里面：§V 用它的 remainder/projection-over 两个数论证
# 单飞闸门占约十五个点，而那两个数曾经【只存在于正文里、不在任何 CSV 里】，
# 且与仓库脚本复算的值对不上（正文 39.9/43.5，复算 39.7/44.0）——
# 2026-09-24 审稿人抓到的。纳进来之后正文只能引用 CSV。
PAPER_SET = ["pois200_foyer_hz0", "pois200_foyer_hz1", "pois200_foyer_hz2",
             "pois200_foyer_hc", "pois200_foyer_bres", "pois200_foyer_breshz1",
             "pois200_foyer_nogate", "pois200_foyer_rg4",
             "pois200_foyer_sf0_r2", "pois200_foyer_hc_r2"]


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
    # 论文正文用的集合，单独汇总并写进 CSV（含名单），使那两个中位数可复现
    sel = [r for r in rows if r["run"] in PAPER_SET]
    if sel:
        k = lambda key: sorted(100.0 * r[key] / r["blocked"] for r in sel)
        vp, op, rp = k("valve"), k("over"), k("rem")
        mid = lambda v: v[len(v) // 2]
        print()
        print("论文集合（%d 条，名单见 CSV 注释）：阀门中位 %.1f%%、投影超预算中位 %.1f%%、"
              "remainder 中位 %.1f%%" % (len(sel), mid(vp), mid(op), mid(rp)))
        # 正文用的集合是【八条非重复的 Foyer 臂】（foyfix 与两条 AIMD 跑的是别的
        # 控制器、不记闸门状态）。原来只落 10 条的 PAPER_SET，于是正文引的
        # 「八条」中位数在文件里查不到，而 PAPER_SET 的中位数又对不上正文
        # （2026-09-24 审稿人抓：正文把投影中位 32.7 写进了阀门那一格）。
        eight = {"foyer_bres", "foyer_hc", "foyer_hz2", "foyer_hz1",
                 "foyer_breshz1", "foyer_nogate", "foyer_hz0", "foyer_rg4"}
        s8 = [r for r in rows if r["run"].replace("pois200_", "") in eight]
        k8 = lambda key: sorted(100.0 * r[key] / r["blocked"] for r in s8)
        v8, p8 = k8("valve"), k8("over")
        print("八条非重复 Foyer 臂（正文用的集合）：阀门中位 %.1f%%、投影超预算中位 %.1f%%"
              % (mid(v8), mid(p8)))
        with open(out_path, "a") as f:
            f.write("# 正文用的集合（八条非重复 Foyer 臂）：%s\n" % " ".join(sorted(
                r["run"] for r in s8)))
            f.write("# eight_median,valve_pct=%.1f,projection_over_pct=%.1f\n"
                    % (mid(v8), mid(p8)))
            f.write("# eight_range,valve=%.1f~%.1f,projection_over=%.1f~%.1f\n"
                    % (v8[0], v8[-1], p8[0], p8[-1]))
            f.write("# 论文正文引用的集合：%s\n" % " ".join(sorted(r["run"] for r in sel)))
            f.write("# paper_set_median,valve_pct=%.1f,projection_over_pct=%.1f,remainder_pct=%.1f\n"
                    % (mid(vp), mid(op), mid(rp)))
            f.write("# paper_set_range,valve=%.1f~%.1f,projection_over=%.1f~%.1f\n"
                    % (vp[0], vp[-1], op[0], op[-1]))
    print("-> %s" % out_path)


if __name__ == "__main__":
    main()
