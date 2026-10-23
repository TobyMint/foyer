#!/usr/bin/env python3
"""三臂的"时间去哪了"分解：引擎忙/闲、device/host 命中、重算税。

用法：python3 gen_work_decomp.py <run_dir> [<run_dir> ...] [--csv out.csv]

## 每个量从哪来（写清楚，免得下次又去猜）

| 量 | 来源 |
|---|---|
| 忙/闲 | `metrics.csv` 的 `sglang:num_running_reqs`：>0 算忙 |
| prompt / cached(device) / cached(host) / evicted | `metrics.csv` 的累计计数器（末值 − 首值） |
| append（真正新增的 token） | `steps.jsonl` 的 `input_len` 之和 |
| completion | `steps.jsonl` 的 `server_completion_tokens` 之和 |

## 两个定义，正文引数时必须一起说

- **重算税** = uncached_prefill / append。完美保留状态时它等于 1（只 prefill 新增的
  token）；完全不复用时它趋近 prompt/append。
- **命中率** 分 device 与 host 两行报，**不合并**：host 命中意味着一次 PCIe 搬运，
  device 命中才是零成本。合并会把两种完全不同的代价说成同一个数。

⚠ `metrics.csv` 是**采样**的（约 1 s），累计计数器要在窗口内取首末值；忙/闲按采样占比
算，所以它是"采样到的忙比例"，不是精确积分。正文里写"sampled busy fraction"。
"""
import json
import os
import sys


def read_metrics(path):
    rows = []
    with open(path) as f:
        # 表头里的引号是 CSV 转义：""sglang:...{cache_source=""device""}"" →
        # 去掉外层引号后还要把成对的 "" 还原成 "，否则查不到这两列（踩过一次）。
        head = [h.strip().strip('"').replace('""', '"')
                for h in f.readline().strip().split(",")]
        for line in f:
            parts = line.rstrip("\n").split(",")
            if len(parts) != len(head):
                continue
            d = {}
            for k, v in zip(head, parts):
                if v == "":
                    continue
                try:
                    d[k] = float(v)
                except ValueError:
                    pass
            rows.append(d)
    return rows


def col(rows, name):
    return [r[name] for r in rows if name in r]


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

    out = []
    for d in dirs:
        mp = os.path.join(d, "metrics.csv")
        sp = os.path.join(d, "steps.jsonl")
        if not os.path.exists(mp):
            print("!! %s 缺 metrics.csv" % d)
            continue
        m = read_metrics(mp)
        if len(m) < 2:
            print("!! %s metrics 采样太少" % d)
            continue
        t0, t1 = m[0]["ts"], m[-1]["ts"]
        wall = t1 - t0
        run = col(m, "sglang:num_running_reqs")
        busy_frac = (sum(1 for x in run if x > 0) / len(run)) if run else float("nan")

        def delta(name):
            v = col(m, name)
            return (v[-1] - v[0]) if len(v) >= 2 else 0.0

        prompt_m = delta("sglang:prompt_tokens_total")
        evict = delta("sglang:evicted_tokens_total")
        # cache_source 分解：**列名带引号**，解析时要去掉引号，否则永远取不到（踩过）。
        # 老 run（2026-09/10 那批）没有这两列，那时只能报聚合命中率。
        dev = delta('sglang:cached_tokens_total{cache_source="device"}')
        host = delta('sglang:cached_tokens_total{cache_source="host"}')

        app = dec = 0.0
        cached = 0.0
        unc_step = 0.0
        nsteps = 0
        if os.path.exists(sp):
            for line in open(sp):
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get("status") != "SUCCESS":
                    continue
                nsteps += 1
                app += r.get("input_len") or 0
                dec += r.get("server_completion_tokens") or 0
                cached += r.get("server_cached_prompt_tokens") or 0
                unc_step += r.get("server_uncached_prompt_tokens") or 0

        prompt = prompt_m if prompt_m > 0 else cached
        # 引擎累计计数器与逐步求和必须对得上（同源断言）：差超过 1% 直接报出来，
        # 不要静默挑一个用。
        if prompt_m > 0 and cached > 0 and abs(prompt_m - (cached + unc_step)) / prompt_m > 0.01:
            print("⚠ %s: 引擎 prompt 累计 %.3fM 与逐步 cached+uncached %.3fM 差 >1%%"
                  % (os.path.basename(d.rstrip("/")), prompt_m / 1e6,
                     (cached + unc_step) / 1e6))
        unc = max(prompt - (dev + host if (dev + host) > 0 else cached), 0.0)
        o = {
            "run": os.path.basename(d.rstrip("/")),
            "wall_min": round(wall / 60.0, 1),
            "busy_pct": round(100 * busy_frac, 1),
            "idle_min": round((1 - busy_frac) * wall / 60.0, 1),
            "n_steps": nsteps,
            "prompt_Mtok": round(prompt / 1e6, 2),
            "cached_Mtok": round(cached / 1e6, 2),
            "uncached_Mtok": round(unc / 1e6, 2),
            "append_Mtok": round(app / 1e6, 2),
            "decode_Mtok": round(dec / 1e6, 2),
            "hit_pct": round(100 * (dev + host if (dev + host) > 0 else cached) / prompt, 1) if prompt else float("nan"),
            "dev_hit_pct": round(100 * dev / prompt, 1) if (prompt and dev) else float("nan"),
            "host_hit_pct": round(100 * host / prompt, 1) if (prompt and host) else float("nan"),
            "evict_Mtok": round(evict / 1e6, 2),
            "reread_x": round(unc / app, 2) if app else float("nan"),
        }
        out.append(o)

    head = ["run", "wall_min", "busy_pct", "idle_min", "n_steps", "prompt_Mtok",
            "cached_Mtok", "uncached_Mtok", "evict_Mtok",
            "append_Mtok", "decode_Mtok", "hit_pct", "dev_hit_pct", "host_hit_pct",
            "reread_x"]
    print("%-16s %8s %7s %8s %9s %9s %9s %8s %7s" % (
        "run", "wall", "busy%", "idle", "prompt", "cached", "uncached", "append", "reread"))
    for o in out:
        print("%-16s %7.1fm %6.1f%% %7.1fm %8.2fM %8.2fM %8.2fM %8.2fM %6.2fx" % (
            o["run"], o["wall_min"], o["busy_pct"], o["idle_min"], o["prompt_Mtok"],
            o["cached_Mtok"], o["uncached_Mtok"], o["append_Mtok"], o["reread_x"]))

    if csv_out:
        os.makedirs(os.path.dirname(os.path.abspath(csv_out)), exist_ok=True)
        with open(csv_out, "w") as f:
            f.write(",".join(head) + "\n")
            for o in out:
                f.write(",".join(str(o[k]) for k in head) + "\n")
        print("\n写 %s（%d 行）" % (csv_out, len(out)))


if __name__ == "__main__":
    main(sys.argv[1:])
