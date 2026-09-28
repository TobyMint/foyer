#!/usr/bin/env python3
"""汇总 gpu_watch.jsonl：这个 run 期间，那张卡被别人占用过吗？

用法: gpu_watch_summary.py <rundir> [<rundir> ...]
      gpu_watch_summary.py --all        # 扫 results 下所有带 gpu_watch.jsonl 的 run

输出每个 run 的：采样数、被外人占用的采样数占比、最长连续占用时长、
外人用过的最大显存、以及占用者名单。**没被占用过就明确说 VERDICT: CLEAN**，
这样论文里可以直接写"这次测量期间该卡独占"。
"""
import glob, json, os, sys


def run_window(rundir):
    """这条 run 自己的时间窗口 (首 submit, 末 complete)，从 steps.jsonl 现算。

    ⚠ **判据必须按窗口裁**：孤儿 watcher 会在 run 结束后继续往同一个文件里追加
    （2026-09-26 实测：`pois200_foyer_hc_r2` 的窗口是 07:08–12:01，而它的 watcher
    从 11:44 一直写到两天后，9,661 条尾巴采样里有 **695 条含外人**）——
    不裁窗口的话，一条【本来就干净】的 run 会被这份文件判成 DIRTY。
    """
    sp = os.path.join(rundir, "steps.jsonl")
    if not os.path.exists(sp):
        return None
    st = [json.loads(l) for l in open(sp) if l.strip()]
    ts = [x["submit_timestamp"] for x in st if x.get("submit_timestamp")]
    te = [x["complete_timestamp"] for x in st if x.get("complete_timestamp")]
    if not ts or not te:
        return None
    return min(ts), max(te)


def summarize(path, t0=None, t1=None):
    ev = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            ev.append(json.loads(line))
        except ValueError:
            continue
    s = [e for e in ev if "n_foreign" in e]
    n_all = len(s)
    if t0 is not None and t1 is not None:
        # 窗内采样；**窗外的尾巴不是这条 run 的证据**，但要报出被裁掉多少
        s = [e for e in s if t0 <= e["ts"] <= t1]
    if not s:
        return None
    dirty = [e for e in s if e["n_foreign"] > 0]
    # 最长连续被占用时长：按采样间隔乘连续点数估计
    interval = next((e.get("interval") for e in ev if e.get("event") == "start"), 15.0)
    longest = cur = 0
    for e in s:
        cur = cur + 1 if e["n_foreign"] > 0 else 0
        longest = max(longest, cur)
    users = sorted({p["user"] for e in dirty for p in e["procs"] if p["foreign"]})
    # 覆盖率：watch 首条采样距 run 开始多久 —— 判据是「整段都有采样」，
    # 而 2026-09-26 实测 `foyer_hc_r2` 的 watcher **比 run 晚起 276 分钟**，
    # 于是那次「全程独占」的说法其实只覆盖了最后 6% 的时间。
    _first = s[0]["ts"] if s else 0
    return dict(n=len(s), dirty=len(dirty), pct=100.0 * len(dirty) / len(s),
                longest_s=longest * interval,
                max_foreign_mib=max((e["foreign_mib"] for e in dirty), default=0),
                users=users,
                span_s=(s[-1]["ts"] - s[0]["ts"]) if len(s) > 1 else 0,
                trimmed=n_all - len(s),
                late_s=(_first - t0) if t0 is not None else 0)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--all":
        runs = sorted(os.path.dirname(p) for p in
                      glob.glob("/data/xbw/turnstile/results/night/*/gpu_watch.jsonl"))
    else:
        runs = [a.rstrip("/") for a in args]
    if not runs:
        print("没有找到 gpu_watch.jsonl（这个监控是 2026-09-24 才加的，早于它的 run 没有）")
        return
    print("%-30s %7s %9s %10s %10s  %s" %
          ("run", "采样", "被占%", "最长(s)", "外人显存", "占用者"))
    for r in runs:
        _w = run_window(r)
        d = summarize(os.path.join(r, "gpu_watch.jsonl"),
                      *(_w if _w else (None, None)))
        if not d:
            print("%-30s %s" % (os.path.basename(r), "[无有效采样]"))
            continue
        verdict = "CLEAN（全程独占）" if d["dirty"] == 0 else "DIRTY"
        if d["trimmed"] > 0:
            verdict += "（裁掉窗外 %d 条尾巴）" % d["trimmed"]
        if d["late_s"] > 60:
            verdict += " ⚠ 采样比 run 晚起 %.0f 分钟" % (d["late_s"] / 60)
        print("%-30s %7d %8.1f%% %10.0f %9dMB  %s  %s" %
              (os.path.basename(r), d["n"], d["pct"], d["longest_s"],
               d["max_foreign_mib"], ",".join(d["users"]) or "-", verdict))


if __name__ == "__main__":
    main()
