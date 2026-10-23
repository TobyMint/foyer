#!/usr/bin/env python3
"""画论文的时间线图：一个会话的 admit/suspend/resume + 引擎在跑数。

用法：
    python3 fig_timeline.py <run_dir> [--session SID] [--out fig.pdf]

上panel：该会话每一轮的执行区间（submit → complete），颜色表示这一轮是
        冷 prefill（红，uncached/prompt>0.9）、暖（蓝，<0.2）还是中间（灰）；
        灰色阴影是该会话被我们挂起（pause → resume）的区间。
下panel：引擎的 `num_running_reqs`（0/1/2…），说明"它被挂起的时候，卡有没有被别人用"。

为什么这张图重要：它把"准入 = 可行性判定"从抽象变成可见的东西 —— 会话在轮边界被
暂停、让位、再回来；回来时是冷是暖，一眼能看出来。
"""
import argparse
import json
import os
import sys


def load_jsonl(p):
    out = []
    for line in open(p):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--session", default=None)
    ap.add_argument("--out", default="fig_timeline.pdf")
    ap.add_argument("--window", type=float, default=0.0,
                    help="只画前 N 分钟（0 = 全程）")
    a = ap.parse_args()

    steps = [r for r in load_jsonl(os.path.join(a.run, "steps.jsonl"))
             if r.get("status") == "SUCCESS" and r.get("first_token_ms") is not None]
    if not steps:
        raise SystemExit("没有可用步")
    t0 = min(r["submit_timestamp"] for r in steps)

    # 选会话：默认取被挂起次数最多的那个
    ev = load_jsonl(os.path.join(a.run, "admissions.jsonl"))
    if a.session is None:
        from collections import Counter
        c = Counter(e["session_id"] for e in ev if e.get("event") == "pause")
        a.session = c.most_common(1)[0][0]
    sid = a.session

    mine = sorted([r for r in steps if r["session_id"] == sid],
                  key=lambda r: r.get("round_idx", 0))
    if not mine:
        raise SystemExit("会话 %s 没有步" % sid)

    evs = sorted([e for e in ev if e.get("session_id") == sid and e.get("ts")],
                 key=lambda e: e["ts"])
    # pause → 下一个 resume 的区间
    spans, open_ts = [], None
    for e in evs:
        if e["event"] == "pause":
            open_ts = e["ts"]
        elif e["event"] == "resume" and open_ts is not None:
            spans.append((open_ts, e["ts"]))
            open_ts = None
    if open_ts is not None:
        spans.append((open_ts, mine[-1]["complete_timestamp"]))

    # 引擎在跑数
    mt, mr = [], []
    with open(os.path.join(a.run, "metrics.csv")) as f:
        head = [h.strip().strip('"').replace('""', '"') for h in f.readline().strip().split(",")]
        ir = head.index("sglang:num_running_reqs")
        it = head.index("ts")
        for line in f:
            p = line.rstrip("\n").split(",")
            if len(p) <= ir or p[ir] == "":
                continue
            try:
                mt.append(float(p[it]))
                mr.append(float(p[ir]))
            except ValueError:
                continue

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tmax = a.window if a.window else None
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 1.85), sharex=True,
                                   gridspec_kw={"height_ratios": [2.1, 1]})

    for (s, e) in spans:
        for ax in (ax1, ax2):
            ax.axvspan((s - t0) / 60, (e - t0) / 60, color="0.9", lw=0, alpha=0.8, zorder=0)

    for r in mine:
        x0 = (r["submit_timestamp"] - t0) / 60
        x1 = (r["complete_timestamp"] - t0) / 60
        frac = (r["server_uncached_prompt_tokens"] / max(r["server_prompt_tokens"], 1))
        color = "#c0392b" if frac > 0.9 else ("#2471a3" if frac < 0.2 else "0.55")
        ax1.barh(0, max(x1 - x0, 0.01), left=x0, height=0.55, color=color, lw=0, zorder=3)

    ax1.set_yticks([])
    ax1.set_ylabel("round", rotation=0, labelpad=10, fontsize=5.5)

    from matplotlib.patches import Patch
    ax1.legend(handles=[Patch(color="#c0392b", label="cold prefill"),
                        Patch(color="#2471a3", label="warm (reused)"),
                        Patch(color="0.55", label="partial"),
                        Patch(color="0.9", label="suspended")],
               fontsize=5.2, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.62),
               frameon=False, handlelength=1.2, columnspacing=1.4, handletextpad=0.4)

    ax2.step([(t - t0) / 60 for t in mt], mr, where="post", color="0.15", lw=0.8)
    ax2.set_ylabel("running", fontsize=5.5)
    ax2.set_xlabel("time since run start (min)", fontsize=5.5)
    ax2.set_ylim(-0.2, max(3, max(mr) + 0.5))
    for ax in (ax1, ax2):
        ax.tick_params(labelsize=5.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    if tmax:
        ax2.set_xlim(0, tmax)
    else:
        ax2.set_xlim(0, (mine[-1]["complete_timestamp"] - t0) / 60)

    fig.tight_layout(pad=0.15)
    fig.savefig(a.out, bbox_inches="tight")
    print("写 %s（会话 %s，%d 轮，%d 次挂起）" % (a.out, sid, len(mine), len(spans)))


if __name__ == "__main__":
    main()
