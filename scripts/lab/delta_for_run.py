#!/usr/bin/env python3
"""给【任意一条 run】算它在论文那条前沿上的 Δ —— 判决机器与正文共用同一套定义。

**为什么要有**：新 run 落地时（`hz2_r3` / `sf0_r3` / 扫队列的 `foyer_scan`），
要问的第一个问题是「它落在哪」。手算就意味着**再写一份插值**，而本项目已经因为
「同一个量两份实现」栽过多次（插值算式曾散在四个文件里，见 CLAUDE.md）。
这个脚本**只做接线**：墙钟与 SLO 从 `steps.jsonl` 现算（与 `frontier.py` 同口径），
包络用 `envelope.piecewise`，判决用 `frontier.classify`，**一个算式都不新写**。

⚠ 它**不**判断这条 run 该不该进表 I —— 那是论文层面的决定（比如扫队列那条是
修复版的第十条变体，不属于那九条）。它只回答「落在线的哪一侧、差多少」。

用法:
  python3 delta_for_run.py <results_dir> <run> [<run> ...]
  例: python3 delta_for_run.py results/night hz2_r3 sf0_r3 foyer_scan
（run 名可带可不带 `pois200_` 前缀，目录名两种都试。）
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envelope as ENV      # noqa: E402  分段线性插值的唯一实现
import frontier as FR       # noqa: E402  FRONT / classify 的唯一实现

THRESH = 10000.0            # 10 s，论文全篇用的那个阈值


def one(d):
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [x["submit_timestamp"] for x in st if x.get("submit_timestamp")]
    comps = [x["complete_timestamp"] for x in st if x.get("complete_timestamp")]
    if not subs or not comps:
        return None
    wall = (max(comps) - min(subs)) / 60.0
    ok = sum(1 for x in st
             if x.get("first_token_ms") is not None and x["first_token_ms"] < THRESH)
    # ⚠ 两个不同的量：`miss` 是**超过 10 s 阈值的步**（SLO 的分母里那些），
    # `err` 才是**请求失败**（`error` 非空）。第一版把前者标成「失败」，会误导。
    miss = len(st) - ok
    err = sum(1 for x in st if x.get("error"))
    return wall, 100.0 * ok / len(st), len(st), miss, err


def main():
    root = sys.argv[1]
    runs = sys.argv[2:]
    if not runs:
        raise SystemExit("用法: delta_for_run.py <results_dir> <run> [<run> ...]")
    front = [(w, s) for w, s, _ in FR.FRONT]
    print("前沿锚点（%d 个）: %s" % (len(front),
          " -> ".join("%.1f/%.1f" % (w, s) for w, s in front)))
    print("\n%-18s %9s %8s %9s %9s  %-9s %s"
          % ("run", "墙钟(min)", "SLO%", "线在该处", "Δ(pp)", "判决", "steps/超时/失败"))
    for r in runs:
        # 论文里的短名（`hz2_r2`）与目录名（`pois200_foyer_hz2_r2`）都对得上
        for cand in ("pois200_" + r, "pois200_foyer_" + r, r):
            d = os.path.join(root, cand)
            if os.path.exists(os.path.join(d, "steps.jsonl")):
                break
        else:
            print("%-18s 找不到（两种命名都试过）" % r)
            continue
        got = one(d)
        if not got:
            print("%-18s steps.jsonl 里没有时间戳（没跑完？）" % r)
            continue
        wall, slo, n, nmiss, nerr = got
        line = ENV.piecewise(wall, front)
        if line is None:
            print("%-18s %9.4f %8.4f %9s %9s  %-9s %d/%d/%d"
                  % (r, wall, slo, "范围外", "不给 Δ", "OUT-OF-RANGE", n, nmiss, nerr))
            continue
        d_pp = slo - line
        print("%-18s %9.4f %8.4f %9.4f %+9.4f  %-9s %d/%d/%d"
              % (r, wall, slo, line, d_pp, FR.classify(d_pp), n, nmiss, nerr))
    print("\n（判决口径与正文一致：> +1.0pp 上方、< -1.0pp 下方、之间 on/tie）")


if __name__ == "__main__":
    main()
