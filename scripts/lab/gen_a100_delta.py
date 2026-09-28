#!/usr/bin/env python3
"""A100 上「控制器 vs A100 自己的静态前沿」的 Δ —— 机械产出，不许用文字绕过。

用法（本地，run 已 rsync 到 results/night）：
    python3 scripts/lab/gen_a100_delta.py paper/data/a100.csv results/night \\
        a100_foyer_hz2 [a100_foyer_hz1 ...]

**为什么要有这个脚本**：2026-09-25 在 A100 上第一次跑了控制器
（`a100_foyer_hz2`，88.3 min / SLO 100.0%，静态最快 `a100_cap5` 是 96.4 min）。
单看两个数像是「越过了前沿」，但那是**肉眼判决**，本项目的老规矩是
「判决由脚本机械产出」。同时它必须把两件事一起报出来：

1. **前沿的左端在哪** —— 静态扫描只到 cap5 而墙钟随 cap 单调下降时，
   「比所有静态点都快」只说明**扫描没扫到头**，不说明控制器赢了。
   脚本会把 `front 的左端墙钟` 与「是否有静态点比控制器更左」一并印出，
   并在 LEFT-OF-FRONT 时显式警告。
2. **控制器有没有真的在限流** —— 若安全阀从未开、池子利用率很低、准入等待很短，
   那么控制器实质等于**没在限流**，它比静态 cap 快最经济的解释是「它没挡路」，
   不是「它做了更好的准入决策`。这个读数从 `controller.jsonl` 与 `admissions.jsonl` 现算。
   ⚠ **不许用 `gate_full`**：那个字段在 `round_gate=0`（默认、且 run_matrix 从不传）
   下**恒为 False**，任何 run 都是 0.0% —— 是恒等式不是观测（见 `gate_stats` 注释）。

定义一律共用：墙钟 / SLO / R̄ / τ 调 `gen_a100.one()`（与 `a100.csv` 同一个函数），
插值调 `envelope.front_slo`（与 3090 的 `frontier.py` 同一份实现）。
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envelope as ENV      # noqa: E402
import gen_a100             # noqa: E402
import importlib.util as _iu  # noqa: E402
# ⚠ ±1.0pp 打平带与 ABOVE/ON/BELOW 判词**必须与 3090 的 frontier.py 共用一份**。
# 2026-09-26 codex r29 指出：这里原来自己写了 `TIE=1.0` 和三个判词串，
# 数值碰巧相同 —— 那正是本项目「口径一致不能写在注释里」那一条禁止的形态。
_sp = _iu.spec_from_file_location("_fr_d", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "frontier.py"))
_FR = _iu.module_from_spec(_sp); _sp.loader.exec_module(_FR)
TIE = _FR.TIE_PP


def _precise(run, root):
    """从 steps.jsonl 现算【全精度】墙钟与 SLO —— 与 frontier.summarise 同一口径。

    ⚠ `a100.csv` 的 `wall_min` 是 **1 位小数**，而 3090 那条管线 2026-09-24 已经
    专门改成读 `runs_precise.csv` 的 6 位（`frontier.py` 的注释记的就是那次事故：
    锚点自己的 Δ 不为 0）。A100 这边**同一个 bug 一直活着**：拿 88.3 / 96.4 建包络
    会得到 Δ=+0.1000，而全精度是 **+0.099975**（2026-09-26 独立复核子 agent 第 18 轮抓）。
    判决不变，但「与 3090 同一份实现」只对**函数**成立 —— 输入也要同精度。
    """
    p = os.path.join(root, run, "steps.jsonl")
    st = [json.loads(l) for l in open(p) if l.strip()]
    ts = [x["submit_timestamp"] for x in st if x.get("submit_timestamp")]
    te = [x["complete_timestamp"] for x in st if x.get("complete_timestamp")]
    tt = [x["first_token_ms"] for x in st if x.get("first_token_ms") is not None]
    return (max(te) - min(ts)) / 60.0, 100.0 * sum(1 for t in tt if t <= 10000) / len(tt)


def static_front(csv_p, root=None):
    """A100 的静态点 → 上-左包络。**有 root 就取全精度坐标**（见 `_precise`）。"""
    rows = [r for r in csv.DictReader(l for l in open(csv_p) if not l.startswith("#"))]
    pts = []
    for r in rows:
        if not r["machine"].startswith("A100"):
            continue
        if root:
            try:
                w, sl = _precise(r["run"], root)
            except (OSError, KeyError, ZeroDivisionError):
                w, sl = float(r["wall_min"]), float(r["slo_pct"])
        else:
            w, sl = float(r["wall_min"]), float(r["slo_pct"])
        pts.append((w, sl, r["run"]))
    return ENV.upper_left(pts), pts


def gate_stats(d):
    """控制器自己的日志：闸门卡住的比例、池子利用率峰值、峰值会话数。"""
    p = os.path.join(d, "controller.jsonl")
    if not os.path.exists(p):
        return None
    rows = []
    for ln in open(p):
        ln = ln.strip()
        if ln:
            try:
                rows.append(json.loads(ln))
            except ValueError:
                pass
    if not rows:
        return None
    us = [r.get("usage") for r in rows if r.get("usage") is not None]
    an = [r.get("active_n") for r in rows if r.get("active_n") is not None]
    # ⚠⚠ **`gate_full` 不能用**：`controller_budget3.py:389` 是
    #   `gate_full = bool(args.round_gate) and running_n >= args.round_gate`，
    #   而 `round_gate` 默认 0、`run_matrix.py` 从不传 `--round-gate`，
    #   于是这个字段**恒为 False** —— 「0.0% 的周期为真」是**恒等式，不是观测**。
    #   （2026-09-25 独立复算抓到；我原先把它写进了论文。）
    # 改用三条**真的会变**的观测：
    #   valve      安全阀（usage 到 0.85 才开）—— 全程 False 说明池子从没接近上限
    #   shed_n     被丢弃的会话数 —— 恒 0
    #   admit_wait 准入等待时长（只看 `admit` 事件；`queued` 的 waited_ms 恒 0、
    #              `release` 的是会话驻留时长，混着算会得出差 10 倍的 p90）
    valve = [r.get("valve") for r in rows if "valve" in r]
    shed = [r.get("shed_n") for r in rows if r.get("shed_n") is not None]
    aw = []
    ap = os.path.join(d, "admissions.jsonl")
    if os.path.exists(ap):
        for ln in open(ap):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if r.get("event") == "admit" and r.get("waited_ms") is not None:
                aw.append(float(r["waited_ms"]))
    aw.sort()
    return dict(n=len(rows),
                valve_true_pct=(100.0 * sum(1 for x in valve if x) / len(valve)) if valve else None,
                shed_max=max(shed) if shed else None,
                usage_max=max(us) if us else None,
                active_max=max(an) if an else None,
                admit_wait_p50=aw[len(aw) // 2] if aw else None,
                admit_wait_max=aw[-1] if aw else None,
                admit_n=len(aw))


def main():
    csv_p, root = sys.argv[1], sys.argv[2]
    # 可选：--csv <out> 把读数写成 paper/data/*.csv —— 论文里引的每个数都要能
    # 追到数据文件，不能只存在于某次终端输出里（CLAUDE.md 证据纪律）。
    out_p = None
    contested = set()
    argv = sys.argv[3:]
    if argv[:1] == ["--csv"]:
        out_p, argv = argv[1], argv[2:]
    # `--contested r1,r2` 显式声明哪些 run **受同机争用**（判据是 gpu_watch 的 foreign
    # 采样与逐请求 decode 间隔的抬升）。**必须显式传**，不许在这里猜：
    # gpu_watch.jsonl 不在本地镜像里，脚本无从判断。
    if argv[:1] == ["--contested"]:
        contested = set(x.strip() for x in argv[1].split(",") if x.strip())
        argv = argv[2:]
    runs = argv
    front, pts = static_front(csv_p, root)
    print("A100 静态点 %d 个；上-左包络 %d 个锚点:" % (len(pts), len(front)))
    for w, s, n in front:
        print("    %-16s %8.1f min  SLO %5.1f%%" % (n, w, s))
    print("  包络左端 = %.1f min（%s）" % (front[0][0], front[0][2]))
    print()
    out_rows = []
    for r in runs:
        d = os.path.join(root, r)
        if not os.path.exists(os.path.join(d, "summary.json")):
            print("%s: 没有 summary.json —— 跳过（不猜）" % r)
            continue
        x = gen_a100.one(d)
        # ⚠ **臂也要全精度**，与锚点同源。用 `one()` 的 1 位小数会让 88.3 落回
        # 全精度锚点 88.3372 的**左边**，判决从 ON 翻成 LEFT-OF-FRONT ——
        # 2026-09-26 改锚点精度时就当场翻了一次（两者只差 **0.6 秒**）。
        w, s = _precise(r, root)
        f = ENV.front_slo(w, front)
        print("=== %s ===" % r)
        print("  wall %.4f min   SLO %.4f%%   步 %s   R̄busy %s   占用p50 %s%%"
              % (w, s, x["steps"], x["Rbar_busy"], x["occ_p50_pct"]))
        if f is None:
            if w < front[0][0]:
                print("  判决: LEFT-OF-FRONT —— 没有任何静态点比它更左")
                print("  ⚠ **这不等于赢**：只说明静态扫描的左端停在 %.1f min。"
                      % front[0][0])
                print("     池子不绑定的卡上，墙钟常随 cap 单调下降 —— 扫描没扫到头时，")
                print("     任何跑到更大并发的策略都会「更左」。先补更大 cap 的静态点。")
            else:
                print("  判决: OUT-OF-RANGE（比所有静态点都慢）")
        else:
            delta = s - f
            v = (_FR.classify(delta).split("(")[0].strip() or "BELOW")
            print("  前沿在 %.1f min 处的 SLO = %.2f%%   Δ = %+.2f pp   -> %s"
                  % (w, f, delta, v))
        g = gate_stats(d)
        if g:
            print("  观测: 安全阀为真的采样 %s%%；shed 峰值 %s；池子利用率峰值 %s；"
                  "峰值会话 %s；准入等待 p50 %s / max %s（%d 会话，%d 采样）"
                  % ("%.1f" % g["valve_true_pct"] if g["valve_true_pct"] is not None else "?",
                     g["shed_max"], "%.1f%%" % (100 * g["usage_max"]) if g["usage_max"] is not None else "?",
                     g["active_max"],
                     "%.0fms" % g["admit_wait_p50"] if g["admit_wait_p50"] is not None else "?",
                     "%.0fms" % g["admit_wait_max"] if g["admit_wait_max"] is not None else "?",
                     g["admit_n"], g["n"]))
            if g["valve_true_pct"] == 0.0 and g["usage_max"] is not None and g["usage_max"] < 0.7:
                print("  ⚠ 安全阀从未开、池子利用率峰值不到 70% —— 控制器实质等于【没在限流】，")
                print("     它相对静态 cap 的优势要先按「不限流」解释，再看能否排除。")
        out_rows.append(dict(
            run=r, contested=("CONTESTED" if r in contested else "clean"),
            wall_min="%.4f" % w, slo_pct="%.4f" % s, steps=x["steps"],
            Rbar_busy=x["Rbar_busy"], occ_p50_pct=x["occ_p50_pct"],
            tau1_ms=x["tau1_ms"], tau2_ms=x["tau2_ms"], reuse_frac=x["reuse_frac"],
            front_left_min="%.1f" % front[0][0], front_left_anchor=front[0][2],
            front_slo_at_wall="" if f is None else "%.4f" % f,
            delta_pp="" if f is None else "%.4f" % (s - f),
            verdict=("LEFT-OF-FRONT" if (f is None and w < front[0][0]) else
                     "OUT-OF-RANGE" if f is None else
                     _FR.classify(s - f).split()[0]),
            valve_true_pct="" if not g or g["valve_true_pct"] is None else "%.4f" % g["valve_true_pct"],
            shed_max="" if not g or g["shed_max"] is None else g["shed_max"],
            usage_max_pct="" if not g or g["usage_max"] is None else "%.4f" % (100 * g["usage_max"]),
            active_max="" if not g or g["active_max"] is None else g["active_max"],
            admit_wait_p50_ms="" if not g or g["admit_wait_p50"] is None else "%.1f" % g["admit_wait_p50"],
            admit_wait_max_ms="" if not g or g["admit_wait_max"] is None else "%.1f" % g["admit_wait_max"],
            admit_n="" if not g else g["admit_n"],
            ctrl_samples="" if not g else g["n"]))
        print()

    if out_p and out_rows:
        with open(out_p, "w", newline="") as fh:
            fh.write("# A100 上控制器 vs A100 自己的静态前沿 —— gen_a100_delta.py 生成\n")
            fh.write("# 墙钟/SLO/R̄/τ 调 gen_a100.one()（与 a100.csv 同一函数）；\n")
            fh.write("# 前沿插值调 envelope.front_slo（与 3090 的 frontier.py 同一实现）。\n")
            fh.write("# verdict=LEFT-OF-FRONT **不等于赢** —— 先看 front_left_min 是不是\n")
            fh.write("# 扫描的端点，以及 valve/shed/准入等待那三列说没说「没在限流」。\n")
            fh.write("# contested=CONTESTED 的行**受同机争用**（由 --contested 显式声明），\n")
            fh.write("# 它的墙钟只能当上界用：争用会抬高它，不会压低它。\n")
            w0 = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
            w0.writeheader()
            w0.writerows(out_rows)
        print("写入 %s：%d 行" % (out_p, len(out_rows)))


if __name__ == "__main__":
    main()
