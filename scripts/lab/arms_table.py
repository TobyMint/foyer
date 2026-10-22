#!/usr/bin/env python3
"""把一个轨迹上的所有臂拉成一张表。用法：

    python3 arms_table.py <结果根目录> <run名>:<标签> [<run名>:<标签> ...]

只读 steps.jsonl，输出 makespan / 命中率 / 有效算力 / 浪费 / 冷启动 / 吞吐。
所有臂默认都截到【共同完成集】，避免"谁跑得多谁占便宜"。
加 --full 则用各自的全部步。
"""
import json, sys, os

def load(root, run):
    p = os.path.join(root, run, "steps.jsonl")
    out = []
    for l in open(p):
        r = json.loads(l)
        if r.get("status") == "SUCCESS":
            out.append(r)
    return out

def metrics(steps):
    t0 = min(float(r["submit_timestamp"]) for r in steps)
    t1 = max(float(r["complete_timestamp"]) for r in steps)
    p = sum(int(r["server_prompt_tokens"]) for r in steps)
    c = sum(int(r["server_cached_prompt_tokens"]) for r in steps)
    u = sum(int(r["server_uncached_prompt_tokens"]) for r in steps)
    g = sum(int(r["server_completion_tokens"]) for r in steps)
    n = sum(int(r["input_len"]) + int(r["output_len_actual"]) for r in steps)
    cold = sum(1 for r in steps
               if int(r["round_idx"]) > 0
               and int(r["server_uncached_prompt_tokens"]) > 0.9 * int(r["prompt_len"]))
    mk = (t1 - t0) / 60.0
    return dict(steps=len(steps), mk=mk, hit=100.0 * c / max(p, 1),
                work=(u + g) / 1e6, need=n / 1e6, waste=(u + g) / max(n, 1),
                cold=cold, thr=(u + g) / 1e6 / mk,
                sess=len(set(r["session_id"] for r in steps)))

def main():
    root = sys.argv[1]
    specs = [a for a in sys.argv[2:] if not a.startswith("--")]
    full = "--full" in sys.argv
    data = {}
    for s in specs:
        run, lab = s.split(":", 1)
        data[lab] = {k: r for r in load(root, run)
                     for k in [(r["session_id"], int(r["round_idx"]))]}
    common = set.intersection(*[set(d) for d in data.values()]) if len(data) > 1 else None
    print(f"{'臂':>22}{'步':>6}{'makespan':>11}{'命中率':>8}{'有效算力':>10}"
          f"{'必要量':>9}{'浪费':>7}{'冷启动':>7}{'吞吐':>9}{'会话':>6}")
    for lab, d in data.items():
        sub = [d[k] for k in (common if (common and not full) else d)]
        m = metrics(sub)
        print(f"{lab:>22}{m['steps']:>6}{m['mk']:>10.1f}分{m['hit']:>7.1f}%"
              f"{m['work']:>9.2f}M{m['need']:>8.2f}M{m['waste']:>6.2f}x"
              f"{m['cold']:>7}{m['thr']:>8.4f}{m['sess']:>6}")
    if common and not full:
        print(f"\n(共同完成集 {len(common)} 步)")
    labs = list(data)
    if len(labs) >= 2:
        a, b = data[labs[0]], data[labs[1]]
        sub = common if (common and not full) else None
        ma = metrics([a[k] for k in sub] if sub else list(a.values()))
        mb = metrics([b[k] for k in sub] if sub else list(b.values()))
        print(f"\n{labs[0]} / {labs[1]}: 整批 {ma['mk']/mb['mk']:.2f}x  "
              f"算力 {ma['work']/mb['work']:.2f}x  吞吐 {mb['thr']/ma['thr']:.2f}x")

if __name__ == "__main__":
    main()
