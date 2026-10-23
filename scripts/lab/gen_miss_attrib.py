#!/usr/bin/env python3
"""重算税归因：每一步的 uncached prefill 是谁造成的 —— 首轮、我们自己挂起、还是引擎驱逐。

用法：python3 gen_miss_attrib.py <run_dir> [<run_dir> ...] [--csv out.csv]

## 三类，判据写死在代码里

对会话 s 的第 i 轮（i>0），在「上一轮完成」到「本轮 submit」之间：

- **first**    i == 0（会话的第一轮，没有前缀可复用，谁也省不掉）
- **suspended** 窗口里出现过该会话的 `pause` 事件（是我们让它等的）
- **continuous** 没有 pause，但仍然 uncached 很多（引擎自己的驱逐）

窗口用 `steps.jsonl` 的 `complete_timestamp`（上一轮）与 `submit_timestamp`（本轮）夹出来，
admissions.jsonl 的 `ts` 是同一时钟（都是 epoch 秒）。

## 输出

每类：步数、uncached 总量、占 uncached 的比例、以及该类每步的 append（真正新增）。
正文引用时要说清"这是按【步】归因，不是按 token 归因"。
"""
import json
import os
import sys
from collections import defaultdict


def load_steps(d):
    by = defaultdict(list)
    for line in open(os.path.join(d, "steps.jsonl")):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("status") != "SUCCESS" or r.get("first_token_ms") is None:
            continue
        by[r["session_id"]].append(r)
    for v in by.values():
        v.sort(key=lambda r: r.get("round_idx", 0))
    return by


def load_events(d):
    p = os.path.join(d, "admissions.jsonl")
    ev = defaultdict(list)
    if not os.path.exists(p):
        return ev
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("session_id") and r.get("ts") is not None:
            ev[r["session_id"]].append(r)
    for v in ev.values():
        v.sort(key=lambda r: r["ts"])
    return ev


def classify(d):
    S = load_steps(d)
    E = load_events(d)
    out = defaultdict(lambda: {"steps": 0, "uncached": 0.0, "append": 0.0, "prompt": 0.0})
    for sid, v in S.items():
        evs = E.get(sid, [])
        for i, r in enumerate(v):
            if i == 0:
                cls = "first"
            else:
                prev = v[i - 1]
                lo, hi = prev["complete_timestamp"], r["submit_timestamp"]
                paused = any(e.get("event") == "pause" and lo <= e["ts"] <= hi for e in evs)
                cls = "suspended" if paused else "continuous"
            o = out[cls]
            o["steps"] += 1
            o["uncached"] += r.get("server_uncached_prompt_tokens") or 0
            o["append"] += r.get("input_len") or 0
            o["prompt"] += r.get("server_prompt_tokens") or 0
    return out



def suspension_stats(d):
    """挂起区间：次数、总时长、以及挂起期间引擎在跑别的请求的采样占比。

    为什么单列：论文用它支撑"挂起换来的槽位真的被用了"（72.1%）。这个数只能从
    admissions.jsonl（pause/resume）+ metrics.csv（num_running_reqs）联合算，
    不属于任何一步，所以不能放进 classify()。
    """
    ev = load_events(d)
    steps = load_steps(d)
    if not steps:
        return None
    t_end = max(r["complete_timestamp"] for r in steps.values().__iter__().__next__()) \
        if False else max(r["complete_timestamp"] for v in steps.values() for r in v)
    spans, opened = [], {}
    for sid, evs in ev.items():
        for e in evs:
            if e.get("event") == "pause":
                opened[sid] = e["ts"]
            elif e.get("event") == "resume" and sid in opened:
                spans.append((opened.pop(sid), e["ts"]))
    for sid, ts in opened.items():
        spans.append((ts, t_end))

    # metrics 采样
    mt, mr = [], []
    mp = os.path.join(d, "metrics.csv")
    if os.path.exists(mp):
        with open(mp) as f:
            head = [h.strip().strip('"').replace('""', '"')
                    for h in f.readline().strip().split(",")]
            if "ts" in head and "sglang:num_running_reqs" in head:
                it, ir = head.index("ts"), head.index("sglang:num_running_reqs")
                for line in f:
                    p = line.rstrip("\n").split(",")
                    if len(p) <= max(it, ir) or p[ir] == "":
                        continue
                    try:
                        mt.append(float(p[it]))
                        mr.append(float(p[ir]))
                    except ValueError:
                        pass

    tot = busy = 0
    for a, b in spans:
        for t, n in zip(mt, mr):
            if a <= t <= b:
                tot += 1
                busy += 1 if n > 0 else 0
    return {
        "n_spans": len(spans),
        "span_hours": sum(b - a for a, b in spans) / 3600.0,
        "engine_busy_pct": (100.0 * busy / tot) if tot else float("nan"),
        "samples": tot,
    }

def main(argv):
    dirs, csv_out = [], None
    i = 0
    while i < len(argv):
        if argv[i] == "--csv":
            i += 1
            csv_out = argv[i]
        else:
            dirs.append(argv[i])
        i += 1
    if not dirs:
        raise SystemExit(__doc__)

    rows = []
    for d in dirs:
        run = os.path.basename(d.rstrip("/"))
        c = classify(d)
        tot_unc = sum(x["uncached"] for x in c.values()) or 1.0
        tot_steps = sum(x["steps"] for x in c.values()) or 1
        print("== %s ==" % run)
        print("%-12s %6s %8s %9s %9s %10s" % ("class", "steps", "steps%", "uncached", "unc%", "append"))
        for k in ("first", "suspended", "continuous"):
            o = c.get(k, {"steps": 0, "uncached": 0, "append": 0})
            print("%-12s %6d %7.1f%% %8.2fM %8.1f%% %9.2fM" % (
                k, o["steps"], 100.0 * o["steps"] / tot_steps,
                o["uncached"] / 1e6, 100.0 * o["uncached"] / tot_unc, o["append"] / 1e6))
            rows.append({
                "run": run, "class": k, "steps": o["steps"],
                "steps_pct": round(100.0 * o["steps"] / tot_steps, 1),
                "uncached_Mtok": round(o["uncached"] / 1e6, 2),
                "uncached_pct": round(100.0 * o["uncached"] / tot_unc, 1),
                "append_Mtok": round(o["append"] / 1e6, 2),
                "excess_x": round(o["uncached"] / o["append"], 2) if o["append"] else float("nan"),
            })
        st = suspension_stats(d)
        if st:
            print("suspension: spans=%d  hours=%.2f  engine_busy=%.1f%%  (samples=%d)" % (
                st["n_spans"], st["span_hours"], st["engine_busy_pct"], st["samples"]))
            for k, v in st.items():
                rows.append({"run": run, "class": "suspension", "steps": "",
                             "steps_pct": "", "uncached_Mtok": "", "uncached_pct": "",
                             "append_Mtok": "", "excess_x": "",
                             "stat": k, "value": round(v, 2) if isinstance(v, float) else v})
        print()

    if csv_out:
        os.makedirs(os.path.dirname(os.path.abspath(csv_out)), exist_ok=True)
        head = ["run", "class", "steps", "steps_pct", "uncached_Mtok", "uncached_pct",
                "append_Mtok", "excess_x", "stat", "value"]
        with open(csv_out, "w") as f:
            f.write(",".join(head) + "\n")
            for r in rows:
                f.write(",".join(str(r.get(k, "")) for k in head) + "\n")
        print("写 %s（%d 行）" % (csv_out, len(rows)))


if __name__ == "__main__":
    main(sys.argv[1:])
