#!/usr/bin/env python3
"""一个简单、可部署的 cap 切换基线 —— 变负载实验的对照臂。

为什么必须有它：只拿「固定 cap」去比「Foyer」是不公平的对照。固定 cap 本来
就没法应对负载变化，赢它是应该的。要检验「复杂控制器是否值得」，必须给一个
任何人都会写的简单切换规则。

规则在**看变负载结果之前**就定死（codex 顾问 2026-09-23 建议，此处照抄）：
  - 以**到达事件**计算过去 10 分钟的到达率
  - 连续两个窗口 > hi_rate，就把上限从 low_cap 降到 high_cap
  - 连续两个窗口 < lo_rate，才升回 low_cap
  - 降档时让已有会话**自然结束**，不强制驱逐

两个 cap 值取自既有恒定负载数据的工作点（低载 cap3 ≈ 91% SLO、高载 cap2），
**不用变负载 trace 自己的结果调参**。

它不改 runner、不改 run_matrix：static=N 模式会读一个纯文本 cap 文件，本体只
需要按规则改写那个文件。

用法:
  cap_switcher.py --cap-file F --admission-log L --decision-log D \
                  [--low-cap 3] [--high-cap 2] [--hi-rate .025] [--lo-rate .020] \
                  [--window 600] [--interval 2]
"""
import argparse, json, os, time

EVENTS = ("queued",)


def read_new(path, pos):
    """从 pos 起读新增的 JSONL 行，返回 (新增事件列表, 新位置)。"""
    if not os.path.exists(path):
        return [], pos
    out = []
    with open(path) as f:
        f.seek(pos)
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return out, f.tell()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-file", required=True)
    ap.add_argument("--admission-log", required=True)
    ap.add_argument("--decision-log", required=True)
    ap.add_argument("--low-cap", type=int, default=3)
    ap.add_argument("--high-cap", type=int, default=2)
    ap.add_argument("--hi-rate", type=float, default=0.025)
    ap.add_argument("--lo-rate", type=float, default=0.020)
    ap.add_argument("--window", type=float, default=600.0)
    ap.add_argument("--interval", type=float, default=2.0)
    args = ap.parse_args()

    arrivals = []          # 到达时刻（秒）
    pos = 0
    cap = args.low_cap
    wrote = None
    hi_streak = lo_streak = 0
    log = open(args.decision_log, "a", buffering=1)

    while True:
        evs, pos = read_new(args.admission_log, pos)
        for e in evs:
            if e.get("event") in EVENTS and e.get("ts"):
                arrivals.append(float(e["ts"]))

        now = time.time()
        recent = [t for t in arrivals if t >= now - args.window]
        rate = len(recent) / args.window

        # 连续计数：只有连续两个窗口同向才动，避免抖动
        if rate > args.hi_rate:
            hi_streak += 1; lo_streak = 0
        elif rate < args.lo_rate:
            lo_streak += 1; hi_streak = 0
        else:
            hi_streak = lo_streak = 0

        nxt = cap
        if hi_streak >= 2 and cap != args.high_cap:
            nxt = args.high_cap
        elif lo_streak >= 2 and cap != args.low_cap:
            nxt = args.low_cap

        if nxt != cap or wrote is None:
            cap = nxt
            tmp = args.cap_file + ".tmp"
            with open(tmp, "w") as f:
                f.write(str(cap))
            os.replace(tmp, args.cap_file)   # 原子替换，runner 不会读到半个数
            wrote = now
            log.write(json.dumps({"ts": now, "cap": cap, "rate": round(rate, 4),
                                  "n_recent": len(recent), "hi_streak": hi_streak,
                                  "lo_streak": lo_streak}) + "\n")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
