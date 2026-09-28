#!/usr/bin/env python3
"""25 档（旧 harness）的单变量分解 —— paper/data/tier25_old.csv。

**为什么要有这个文件**：正文 §VII 的「节流开关方向相反」那句引了
`58.4 -> 28.8 分钟（快 51%）`，而这两个数**在 `paper/data/` 里查不到** ——
它们只活在 `docs/claim_register_20260921.md`（9-21 的旧登记）与日志里。
本项目的判据是「数字要能追到代码、日志或 `paper/data/*.csv`」，而
「日志里有」是**必要条件不是充分条件**（日志会被覆盖/清理，数据文件是版本化的）。

**顺带解决一个更值钱的问题**：正文现在的口径是「轻载那一对动了两根旋钮，
所以只当方向、不当剂量-反应」。但**单变量的那些臂本来就已经跑过**：

    thr25_base   budget3                  （默认 target 0.75、hw 开）   58.4 min
    thr25_nohw   budget3:hw=0             （只关 hw）                    38.1
    thr25_t95    budget3:target=0.95      （只抬 target）                39.7
    thr25_push   budget3:hw=0;target=0.95 （两根都动）                  28.8
    thr25_nosf   budget3:sf=0             （只关单飞）                   49.5
    thr25_hwsf   budget3:hw=0;sf=0        （hw + 单飞）                  30.3

⇒ 每根旋钮**单独**大约各值三分之一，两根一起值一半（**次可加**）。
这是一条**已测但没写进论文**的读数，不是新实验。

⚠ 全部是**旧 harness**（与 `thr25_base` 是同代，与 200 档不是），正文必须一起标。
⚠ **红线扫描（t80/t85/t90）不在本文件里**：那三条是**当前 harness** 的 run
（名字是 `load25c_budget3_t*`，不是 `thr25_*`），与这里不同代 ——
把 33.5（当前 harness 的 t85）与 39.7（旧 harness 的 t95）并列就是一个跨代比较，
所以正文**不写**扫描的非单调性。
⚠ 墙钟口径与 `paper/data/table1.csv` 逐字相同：`max(complete_timestamp) -
min(submit_timestamp)`（不是 `metadata.wall_s` —— 后者是 runner 自报的、系统性偏大
约 4 分钟，本项目「两条管线算同一个量必须共用定义」那一条）。

用法: python3 gen_tier25_old.py <results_dir> <out.csv>
"""
import csv, json, os, sys

ARMS = [
    ("thr25_base",    "budget3",                    "default: target 0.75, high-water on"),
    ("thr25_nohw",    "budget3:hw=0",               "high-water off only"),
    ("thr25_t95",     "budget3:target=0.95",        "red line 0.95 only"),
    ("thr25_push",    "budget3:hw=0;target=0.95",   "both knobs (the pair quoted in the paper)"),
    ("thr25_push_r2", "budget3:hw=0;target=0.95",   "both knobs, repeat"),
    ("thr25_nosf",    "budget3:sf=0",               "single-flight off only"),
    ("thr25_hwsf",    "budget3:hw=0;sf=0",          "high-water off + single-flight off"),
]
THRESH = 10000.0


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = []
    for name, policy, what in ARMS:
        d = os.path.join(root, name)
        sp = os.path.join(d, "steps.jsonl")
        if not os.path.exists(sp):
            raise SystemExit("!! %s 缺 steps.jsonl —— 没跑过的臂不许进数据文件" % name)
        st = [json.loads(l) for l in open(sp) if l.strip()]
        meta = json.load(open(os.path.join(d, "metadata.json")))
        # policy 串是「哪根旋钮动了」的唯一判据（run 名字不是）—— 不一致直接炸
        if str(meta.get("policy")) != policy:
            raise SystemExit("!! %s 的 policy 是 %r，期望 %r —— 臂的配置变了"
                             % (name, meta.get("policy"), policy))
        subs = [x["submit_timestamp"] for x in st if x.get("submit_timestamp")]
        comps = [x["complete_timestamp"] for x in st if x.get("complete_timestamp")]
        wall = (max(comps) - min(subs)) / 60.0
        slo = 100.0 * sum(1 for x in st if x.get("first_token_ms") is not None
                          and x["first_token_ms"] < THRESH) / len(st)
        rows.append({"run": name, "policy": policy, "what_moved": what,
                     "steps": len(st), "wall_min": "%.4f" % wall,
                     "slo_pct": "%.4f" % slo})
    base = [r for r in rows if r["run"] == "thr25_base"]
    if not base:
        raise SystemExit("!! 缺基线臂 thr25_base")
    b = float(base[0]["wall_min"])
    for r in rows:
        r["speedup_vs_base_pct"] = "%.1f" % (100.0 * (b - float(r["wall_min"])) / b)
    hdr = [
        "# 25 档（旧 harness）的单变量分解 —— 由 gen_tier25_old.py 生成，勿手改",
        "# wall_min 口径与 table1.csv 逐字相同（steps.jsonl 的 submit->complete，",
        "#   不是 metadata.wall_s —— 后者系统性大约偏 4 分钟）。",
        "# speedup_vs_base_pct = (基线墙钟 - 本臂墙钟)/基线墙钟。",
        "# ⚠ 全部是【旧 harness】：与 thr25_base 同代，与 200 档不同代。",
        "run,policy,what_moved,steps,wall_min,slo_pct,speedup_vs_base_pct",
    ]
    # ⚠ 2026-09-26：**手工拼逗号会把带逗号的字段拆开** —— `what_moved` 里
    # 「default: target 0.75, high-water on」那一行把列整体错位一格，
    # `wall_min` 读成了 125（步数）。本项目栽过「手写的输出表头」（`gen_toolwait.py`），
    # 这次是**手拼的数据行**，而且它**不报错、只是安静地给错列**。
    # 改用 `csv.DictWriter`：引号与转义由它负责。
    assert isinstance(out, str)
    with open(out, "w", newline="") as f:
        for _h in hdr:
            f.write(_h + "\n")
        _fields = ("run", "policy", "what_moved", "steps", "wall_min", "slo_pct",
                   "speedup_vs_base_pct")
        _w = csv.DictWriter(f, fieldnames=list(_fields))
        _w.writerows(rows)
    for r in rows:
        print("  %-14s %-30s %6s min  SLO %5s  %s%% faster"
              % (r["run"], r["policy"], r["wall_min"], r["slo_pct"],
                 r["speedup_vs_base_pct"]))
    print("-> %s" % out)


if __name__ == "__main__":
    main()
