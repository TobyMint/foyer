#!/usr/bin/env python3
"""并发争用审计 —— 每条 run 在生命周期内与几条别的 run 真正重叠，以及它的 τ₂。

为什么必须做这个：2026-09-24 发现，同机同时跑 >=3 台 SGLang server 会把【逐请求
decode 间隔中位 τ₂】抬高 25~40%。τ₂ 是客户端实测的、不经采样器的量，所以这不是
采样伪影，是真实的步成本上升。受影响 run 的墙钟与 SLO 与其余各行不可比。

证据链（本脚本输出 + probe_concurrency.py 的时间分箱）：
  - cap1 在 1~2 条车道时 τ₂ 恒为 20.3~20.7；02:25 rl90/rl99 起来（3 条）后跳到 22.4~27.5
  - t85 与 rl99 两条独立 run 在 07:09~07:23（rl90 结束前后）同时从 ~30 回落到 ~22~25
  - bres/hz0/hz2/breshz1 四条彼此重叠约 300 分钟（4 条车道），τ₂ 30.9~33.3，
    而同族干净 run 是 23.8~25.7

判据（看数据前定死）：**同时活着的 run 数 >=4 且持续 >=60 分钟** 记 CONTESTED。
两个限定都是必须的：
  - 用「同时数」而不是「重叠对象数+1」——本项目是链式车道，上一条结束下一条就起，
    按对象数会把顺序相接的 2 条误报成 3 条（2026-09-24 犯过，脚本第一版就错在这）。
  - 用「持续时长」而不是峰值——foyer_hz1 峰值到过 4 条但只有 14 分钟，τ₂=24.6 正常。

实测 2~3 条不抬 τ₂（pairB_foyerhc 3 条 277 分钟 τ₂=23.8；cap3_fixed 3 条 163 分钟
τ₂=24.9；sf0_r2/hz1_r2/cap3_hc_r2 都在 3 条下跑，τ₂ 24.3~25.0），4 条才抬。
注意判定是"该 run 的测量窗口里有持续争用"，是保守触发条件；τ₂ 一列是实际是否被抬高的
读数，两者一起看——t85/t90/var_foyer 触发了 CONTESTED 但 τ₂ 正常（只有前半段被抬）。

用法: python3 gen_concurrency.py <results_dir> <out.csv>

**必须在实验机上跑**（RESULTS_DIR 指向 /data/xbw/turnstile/results/night）。
为什么：本脚本是【对 run 集合计数】的 —— 同时活着的条数取决于目录里有哪些 run。
本地镜像是部分 rsync（2026-09-24 实测：本地 116 个目录 vs 实验机 145+，且本地还留着
实验机上已清理的旧 25 档目录），在本地跑会把 var_cap3 从 CONTESTED 误判成 clean
（丢掉的 _failed_4lane_* 与 25 档目录正是它窗口里的那几条）。判据本身没错，
错的是输入集合。下面有 MIN_RUNS 断言，镜像不全时会直接报错而不是静默给错判决。

"""
import csv, glob, json, os, statistics, sys

OVERLAP_MIN_S = 600.0
EXPECT_TAU2 = True


def tau2(root, run):
    """逐请求 decode 间隔中位（与 gen_decomp.py 的口径一致）。"""
    p = os.path.join(root, run, "steps.jsonl")
    if not os.path.exists(p):
        return None
    try:
        steps = [json.loads(l) for l in open(p) if l.strip()]
    except Exception:
        return None
    ok = [s for s in steps
          if (s.get("output_len_actual") or 0) >= 32 and s.get("status") == "SUCCESS"]
    if not ok:
        return None
    return statistics.median(
        (s["total_duration_ms"] - s["first_token_ms"]) / max(1, (s["output_len_actual"] - 1))
        for s in ok)


def main():
    root, out_path = sys.argv[1], sys.argv[2]
    # 镜像完整性护栏：本脚本的判据是"同时活着几条"，少一个 run 目录就少一条车道，
    # 判决会静默变松。实测 2026-09-24 本地镜像 116 目录 vs 实验机 145，把
    # var_cap3 从 CONTESTED 变成 clean。宁可拒绝跑，也不要给出看着合理的错判决。
    MIN_RUNS = 140
    n_dirs = len(glob.glob(os.path.join(root, "*", "metadata.json")))
    assert n_dirs >= MIN_RUNS, (
        "只找到 %d 个带 metadata.json 的 run 目录（需要 >=%d）。"
        "这多半是部分镜像 —— 本脚本必须在实验机上跑。" % (n_dirs, MIN_RUNS))
    rows, skipped = [], []
    for d in glob.glob(os.path.join(root, "*", "metadata.json")):
        try:
            m = json.load(open(d))
        except Exception:
            continue
        s, f = m.get("started"), m.get("finished")
        # finished 缺失时【回退】到 started + wall_s，不能直接 continue ——
        # 静默跳过会让数据文件少了 run，而正文还在引用它：pois200_aimd2 与
        # pois200_aimd2_paper 就因此不在本表里，而 §V 用后者论证"唯一的步成本
        # 归因在干净 run 上"（2026-09-24 审稿人查不到那一行）。本项目的
        # 「生成器静默丢 run」已经栽过两次（foyer_hz1、这里）。
        fallback = ""
        if not f and m.get("wall_s"):
            f = s + float(m["wall_s"]); fallback = "wall_s"
        if not f:
            # 最后回退：从 steps.jsonl 的首末时间戳推窗口 —— frontier.py 用的同一个来源。
            # pois200_aimd2 / pois200_aimd2_paper 的 metadata 里 finished 与 wall_s
            # 都是 None（run 却跑完了、有 summary.json），只靠 wall_s 回退仍会丢它们。
            sp = os.path.join(os.path.dirname(d), "steps.jsonl")
            if s and os.path.exists(sp):
                try:
                    st = [json.loads(l) for l in open(sp) if l.strip()]
                    f = max(x["complete_timestamp"] for x in st); fallback = "steps.jsonl"
                except Exception:
                    pass
        if not s or not f:
            skipped.append(os.path.basename(os.path.dirname(d)))
            continue
        rows.append({"run": os.path.basename(os.path.dirname(d)),
                     "started": s, "finished": f, "gpu": m.get("gpu"),
                     "window_src": fallback or "metadata"})
    rows.sort(key=lambda r: r["started"])

    # 关键：并发数必须是【同时活着的条数】，不是"重叠对象数+1"。
    # 后者会把顺序相接的链式车道当成同时（本项目是链式：上一条结束下一条就开始），
    # 于是把 2 条误报成 3 条。这里用事件扫描算真实同时数，再统计【持续多久】。
    def lanes_over_time(lo, hi):
        """返回 (峰值同时数, 同时数>=4 的总秒数, 同时数>=3 的总秒数)。"""
        ev = []
        for o in rows:
            a, b = max(lo, o["started"]), min(hi, o["finished"])
            if b > a:
                ev.append((a, 1))
                ev.append((b, -1))
        ev.sort()
        cur = peak = 0
        ge4 = ge3 = 0.0
        prev = lo
        for t, d in ev:
            if cur >= 4:
                ge4 += t - prev
            if cur >= 3:
                ge3 += t - prev
            cur += d
            peak = max(peak, cur)
            prev = t
        return peak, ge4, ge3

    for r in rows:
        peak, ge4, ge3 = lanes_over_time(r["started"], r["finished"])
        r["peak_lanes"] = peak
        r["min_at_ge4"] = round(ge4 / 60.0, 1)
        r["min_at_ge3"] = round(ge3 / 60.0, 1)
        # 判据定在 >=4 条【持续】超过 60 分钟：实测 2~3 条的 run 的 τ₂ 都在同族正常范围
        # （pairB_foyerhc 3 条 277 分钟 τ₂=23.8；cap3_fixed 3 条 163 分钟 τ₂=24.9），
        # 而 4 条的（bres/hz0/hz2/breshz1，各约 300 分钟）τ₂ 30.9~33.3。
        # 只看峰值不看时长会把 hz1（峰值 4 但只有 14 分钟）误判，故按时长判。
        r["verdict"] = "CONTESTED" if r["min_at_ge4"] >= 60.0 else (
            "watch" if r["min_at_ge3"] >= 60.0 else "clean")
        r["tau2_ms"] = tau2(root, r["run"])

    header = "\n".join([
        "# 并发争用审计 —— 由 scripts/lab/gen_concurrency.py 生成，勿手改",
        "# peak_lanes: 生命周期内同时活着的 run 数峰值（事件扫描，不是重叠对象数+1）",
        "# min_at_ge4: 同时 >=4 条持续的分钟数 —— 判据用它，因为只有持续争用才抬 τ₂",
        "# verdict: min_at_ge4>=60 记 CONTESTED（墙钟/SLO 与其余各行不可比，须重测）；",
        "#          min_at_ge3>=60 记 watch（实测 3 条无一致抬升，但记录在案）",
        "# tau2_ms: 逐请求 decode 间隔中位（客户端实测，不经采样器）；争用会把它抬高 ~25~40%",
        "run,peak_lanes,min_at_ge4,min_at_ge3,tau2_ms,verdict"])
    fields = ["run", "peak_lanes", "min_at_ge4", "min_at_ge3", "tau2_ms", "verdict"]
    # 一次写成一个 str（本项目教训：open(p,"w") 先截断后报错，内容非 str 会把文件清空）
    lines = [header]
    for r in rows:
        lines.append(",".join(str(r[k]) for k in fields))
    body = "\n".join(lines) + "\n"
    assert isinstance(body, str)
    with open(out_path, "w") as fh:
        fh.write(body)

    nbad = sum(1 for r in rows if r["verdict"] == "CONTESTED")
    nw = sum(1 for r in rows if r["verdict"] == "watch")
    if skipped:
        print("!! 以下 run 的 metadata 既没有 finished 也没有 wall_s，未能纳入（会静默丢数据）：")
        for n in skipped:
            print("   %s" % n)
    from collections import Counter
    c = Counter(r.get("window_src") for r in rows)
    print("写入 %s：%d 行，CONTESTED %d 行，watch %d 行；窗口来源 %s"
          % (out_path, len(rows), nbad, nw, dict(c)))
    for r in rows:
        if r["verdict"] == "CONTESTED":
            print("  CONTESTED %-30s 峰值%d条  >=4条共%.0f分钟  τ₂=%.1f" % (
                r["run"], r["peak_lanes"], r["min_at_ge4"], r["tau2_ms"] or float("nan")))


if __name__ == "__main__":
    main()
