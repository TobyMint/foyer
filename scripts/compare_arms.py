#!/usr/bin/env python3
"""Compare a set of runs on the two metrics that matter, plus the decomposition.

Written for the Foyer guardrail arms: the question they exist to answer is whether
charging each session what it actually costs (rather than the worst case) raises
concurrency and cuts wall time without giving away the cache-hit advantage.

    python3 compare_arms.py <results_dir> run1 run2 ...

Reports per run:
  wall          total makespan (metadata.wall_s — the primary metric)
  hit%          engine prefix-cache hit rate
  SLO%          share of successful steps with TTFT < 10s
  conc          time-average concurrency
  done_p50/p90  when a session finishes, relative to the replay start
  wait/exec     how much of that is waiting outside vs occupying a slot
  gpu_busy      share of samples with the engine's own token_usage > 0.3

Note on `wait`: the trace clock and the wall clock are aligned by the session that
waited least, which pins the offset exactly when any session was admitted on
arrival and slightly under-estimates every wait otherwise (conservative).
"""
import json
import os
import statistics as st
import sys

SLO_MS = 10000.0


def read_jsonl(path):
    out = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    return out


def pct(v, q):
    if not v:
        return float("nan")
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))]


def wall_from_runner_out(d):
    """Fallback when run_matrix died before finalising metadata (no wall_s).

    The runner prints its own elapsed on every progress line, so the LAST line
    carries the run's true duration. This is not the same number run_matrix would
    have written — that is `time.time() - t0` around runner.wait(), which includes
    the runner's startup — but it is measured by the same run and is the best
    available. Callers must treat it as a fallback, which is why the source is
    reported alongside the value rather than silently substituted.
    """
    last = None
    try:
        with open(os.path.join(d, "runner.out")) as f:
            for line in f:
                if "elapsed=" in line:
                    last = line
    except FileNotFoundError:
        return None
    if not last:
        return None
    # the field reads "elapsed=22019.7s" — strip the unit before parsing
    try:
        return float(last.rsplit("elapsed=", 1)[1].split()[0].rstrip("s")) / 60.0
    except (IndexError, ValueError):
        return None


def metrics(d):
    meta = json.load(open(os.path.join(d, "metadata.json")))
    summ = json.load(open(os.path.join(d, "summary.json")))
    rep = summ.get("replay", {})

    steps = read_jsonl(os.path.join(d, "steps.jsonl"))
    ok = [r for r in steps if r.get("status") == "SUCCESS"]
    ttfts = [r["first_token_ms"] for r in ok if r.get("first_token_ms") is not None]

    arr, adm, rel = {}, {}, {}
    for r in steps:
        sid = r.get("session_id")
        if sid and r.get("arrival_time_ms") is not None:
            arr[sid] = min(arr.get(sid, 1e18), r["arrival_time_ms"])
        if sid and r.get("submit_timestamp") and r.get("complete_timestamp"):
            cur = adm.setdefault(sid, [r["submit_timestamp"], r["complete_timestamp"]])
            cur[0] = min(cur[0], r["submit_timestamp"])
            cur[1] = max(cur[1], r["complete_timestamp"])
    for e in read_jsonl(os.path.join(d, "admissions.jsonl")):
        sid = e.get("session_id")
        if not sid:
            continue
        if e.get("event") == "admit":
            adm.setdefault(sid, [e["ts"], e["ts"]])[0] = min(
                adm.get(sid, [e["ts"], e["ts"]])[0], e["ts"])
        elif e.get("event") == "release":
            adm.setdefault(sid, [e["ts"], e["ts"]])[1] = max(
                adm.get(sid, [e["ts"], e["ts"]])[1], e["ts"])

    conc = done_p50 = done_p90 = wait_med = exec_med = float("nan")
    if adm:
        t0 = min(v[0] for v in adm.values())
        t1 = max(v[1] for v in adm.values())
        if t1 > t0:
            conc = sum(v[1] - v[0] for v in adm.values()) / (t1 - t0)
        done = sorted((v[1] - t0) / 60 for v in adm.values())
        done_p50, done_p90 = pct(done, .5), pct(done, .9)
        common = [s for s in arr if s in adm]
        if common:
            off = min(adm[s][0] - arr[s] / 1000.0 for s in common)
            wait_med = pct([(adm[s][0] - off - arr[s] / 1000.0) / 60 for s in common], .5)
            exec_med = pct([(adm[s][1] - adm[s][0]) / 60 for s in common], .5)

    busy = float("nan")
    mrows = []
    try:
        with open(os.path.join(d, "metrics.csv")) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) > 1:
                    try:
                        mrows.append(float(parts[1]))
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    if mrows:
        busy = 100.0 * sum(1 for x in mrows if x > 0.3) / len(mrows)

    # wall_s is what run_matrix records around runner.wait(). When run_matrix is
    # killed before it finalises, fall back to the runner's own last elapsed and
    # say so — an unflagged substitution would misrepresent the number's origin.
    wall_src = "metadata.wall_s"
    wall = (meta.get("wall_s") or 0) / 60
    if not wall:
        fb = wall_from_runner_out(d)
        if fb:
            wall, wall_src = fb, "runner.out elapsed (metadata unfinished)"
        else:
            wall_src = "MISSING"

    return dict(
        wall=wall, wall_src=wall_src,
        pool=meta.get("pool_tokens"),
        policy=meta.get("policy"),
        hit=100 * (rep.get("server_prefix_hit_rate") or 0),
        slo=100 * sum(1 for x in ttfts if x < SLO_MS) / len(ttfts) if ttfts else float("nan"),
        fails=rep.get("attempted_steps", 0) - rep.get("success_steps", 0),
        steps=len(steps), conc=conc, done_p50=done_p50, done_p90=done_p90,
        wait_med=wait_med, exec_med=exec_med, busy=busy)


def main():
    results = sys.argv[1]
    names = sys.argv[2:]
    if not names:
        print(__doc__)
        return 1
    rows = []
    for n in names:
        d = os.path.join(results, n)
        if not os.path.exists(os.path.join(d, "summary.json")):
            print("  %-24s (还没有 summary.json — 未完成)" % n)
            continue
        try:
            rows.append((n, metrics(d)))
        except Exception as e:
            print("  %-24s 读取失败: %s" % (n, e))

    if not rows:
        return 1
    print("%-24s %8s %7s %7s %7s %7s %7s %7s %7s" % (
        "run", "墙钟", "命中%", "SLO%", "并发", "完成p50", "完成p90", "等待中位", "执行中位"))
    print("-" * 104)
    for n, m in rows:
        print("%-24s %7.1f分 %6.1f %6.1f %7.2f %6.0f分 %6.0f分 %6.0f分 %6.1f分" % (
            n, m["wall"], m["hit"], m["slo"], m["conc"], m["done_p50"], m["done_p90"],
            m["wait_med"], m["exec_med"]))
    print()
    for n, m in rows:
        flag = "" if m["pool"] == 101432 else "   ⚠ 池子=%s 非对齐值！" % m["pool"]
        src = "" if m["wall_src"] == "metadata.wall_s" else "   ⚠ 墙钟来源: %s" % m["wall_src"]
        print("  %-24s policy=%-34s 步数=%d 失败=%d 引擎忙占比=%.0f%%%s%s" % (
            n, m["policy"], m["steps"], m["fails"], m["busy"], flag, src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
