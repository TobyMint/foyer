#!/usr/bin/env python3
"""跑实验期间盯住那张卡：有没有别人的进程挤进来。

## 为什么需要

池子守卫（run_matrix 的 pool guard）只在【启动时】检查一次显存 —— 它保证起跑
那一刻池子是 101,432。但**跑到一半别人往同一张卡上挂进程**，这件事现在完全看
不见：被偷走的算力和显存会让这一段的 τ、SLO、墙钟全部偏低，而数据看上去正常。

2026-09-24 用户提出这一点。查了一下，现有 run 目录里确实没有任何这类记录。

## 它记什么

每 INTERVAL 秒采一次：
  - 卡的 memory.used / utilization.gpu
  - 该卡上所有【计算进程】的 pid / 属主 / 显存
  - 属主不是本 run 属主的进程，单独标成 foreign

输出 append 到 <rundir>/gpu_watch.jsonl，一行一个采样点。

## 用法

作为后台进程与 lane 并行：

    gpu_watch.py --gpu 3 --out results/night/<run>/gpu_watch.jsonl &
    ...
    kill %1

⚠ **`kill %1` 常常被忘掉**（2026-09-26 抓到两个跑了两天的孤儿）。所以本脚本现在
**自己会在 `<rundir>/summary.json` 出现时退出**（`--no-stop` 关掉）。

汇总用 gpu_watch_summary.py。
"""
import argparse, json, os, subprocess, time


def sh(cmd, timeout=10):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=timeout).stdout.strip()
    except Exception:
        return ""


def owner_of(pid):
    out = sh("ps -o user= -p %s" % pid)
    return out.strip() or "?"


def sample(gpu, me):
    tot = sh("nvidia-smi --query-gpu=memory.used,utilization.gpu "
             "--format=csv,noheader,nounits -i %d" % gpu).split(",")
    used = int(tot[0]) if len(tot) > 0 and tot[0].strip().isdigit() else None
    util = int(tot[1]) if len(tot) > 1 and tot[1].strip().isdigit() else None
    procs = []
    raw = sh("nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader -i %d" % gpu)
    for line in raw.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        pid = int(parts[0])
        mem = int(parts[1].split()[0]) if parts[1].split() else 0
        u = owner_of(pid)
        procs.append(dict(pid=pid, user=u, mem_mib=mem, foreign=(u != me)))
    return dict(ts=round(time.time(), 3), gpu=gpu, mem_used_mib=used,
                util_pct=util, procs=procs,
                n_foreign=sum(1 for p in procs if p["foreign"]),
                foreign_mib=sum(p["mem_mib"] for p in procs if p["foreign"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=15.0)
    ap.add_argument("--me", default=None, help="本 run 的属主（默认取当前用户）")
    ap.add_argument("--stop-when-done", action="store_true", default=True,
                    help="run 写出 summary.json 之后自行退出（默认开）")
    ap.add_argument("--no-stop", dest="stop_when_done", action="store_false")
    a = ap.parse_args()
    me = a.me or sh("id -un")
    rundir = os.path.dirname(a.out)
    os.makedirs(rundir, exist_ok=True)
    with open(a.out, "a", buffering=1) as f:
        f.write(json.dumps(dict(ts=round(time.time(), 3), event="start",
                                gpu=a.gpu, owner=me, interval=a.interval)) + "\n")
        while True:
            try:
                f.write(json.dumps(sample(a.gpu, me)) + "\n")
            except Exception as e:
                f.write(json.dumps(dict(ts=round(time.time(), 3), error=str(e))) + "\n")
            # ⚠ **run 跑完就自己退**。2026-09-26 实测：两个 Sep 24 的孤儿 watcher
            # 一直往【已结束】的 run 的 gpu_watch.jsonl 追加了两天 ——
            # `foyer_hc_r2` 的窗口是 07:08–12:01，而文件里多出 9,661 条窗外采样，
            # 其中 695 条含外人。没有窗口过滤的判据会把一条本来干净的 run 判成 DIRTY。
            # 判据用 `summary.json`（项目里「跑完」的统一判据，见 CLAUDE.md）。
            # 没有 summary 的（崩溃/中止的 run）由启动方 kill —— 它们本来就该有人收尾。
            if a.stop_when_done and os.path.exists(os.path.join(rundir, "summary.json")):
                f.write(json.dumps(dict(ts=round(time.time(), 3), event="stop",
                                        reason="summary.json 出现，run 已结束")) + "\n")
                return
            time.sleep(a.interval)


if __name__ == "__main__":
    main()
