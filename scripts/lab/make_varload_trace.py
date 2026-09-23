#!/usr/bin/env python3
"""生成【变负载】replay trace：到达率在同一个 run 内从低切到高。

为什么需要：论文 §V 的负载依赖结论全部建立在【两个各自恒定的档位】上
（25 档 vs 200 档），而 codex 与子 agent 都指出这回答不了「自适应在负载
变化时是否有用」——那正是自适应存在的理由。这个脚本造一条负载中途变化的
trace，让「同一个 run 内低→高」成为可测的。

刻意不改 make_arrival_trace.py：那个脚本被现有 lane 用着，改它有连带风险。

用法:
  make_varload_trace.py SRC DST LOW_LAM HIGH_LAM SWITCH_SESSIONS [SEED]

  前 SWITCH_SESSIONS 个会话按 LOW_LAM 到达，其余按 HIGH_LAM。
  到达顺序在会话之间随机打乱（与 session_id 顺序无关），沿用原脚本的做法。

输出末尾会打印两段的实际到达跨度，用来确认切点符合预期。
"""
import csv, random, sys

src, dst = sys.argv[1], sys.argv[2]
lo, hi = float(sys.argv[3]), float(sys.argv[4])
switch_n = int(sys.argv[5])
seed = int(sys.argv[6]) if len(sys.argv) > 6 else 20260923

rows = list(csv.DictReader(open(src)))
order, seen = [], set()
for r in rows:
    if r["session_id"] not in seen:
        seen.add(r["session_id"])
        order.append(r["session_id"])

rng = random.Random(seed)
shuffled = order[:]
rng.shuffle(shuffled)

arrival, t, switch_t = {}, 0.0, None
for i, sid in enumerate(shuffled):
    if i == switch_n:
        switch_t = t
    t += rng.expovariate(lo if i < switch_n else hi)
    arrival[sid] = t * 1000.0

fields = list(rows[0].keys())
if "arrival_time" not in fields:
    fields = fields + ["arrival_time"]
with open(dst, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        r["arrival_time"] = f"{arrival[r['session_id']]:.1f}"
        w.writerow(r)

total = max(arrival.values()) / 1000.0
print("%s -> %s" % (src, dst))
print("  %d 个会话；前 %d 个 λ=%.4f/s（%.1f 分钟），其余 λ=%.4f/s（%.1f 分钟）"
      % (len(order), switch_n, lo, switch_t / 60, hi, (total - switch_t) / 60))
print("  切点在 t=%.1f 分钟，最后一次到达 %.1f 分钟" % (switch_t / 60, total / 60))
