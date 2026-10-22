#!/usr/bin/env python3
"""从语料建一条 replay trace。**这是唯一的建 trace 脚本**，不要再写一次性的。

## 为什么会有这个脚本

`replay_main31.csv` 当初是用一段临时脚本建的，**那段脚本没留下来** ——
2026-10-12 要建新数据集时，只能从文档里的规则反推着重写一遍，
再拿「能不能逐字节复现 main31」来验证反推对不对。**这个坑不该踩第二次。**

    python3 build_replay_trace.py --verify          # 复现 main31，逐字节对拍
    python3 build_replay_trace.py --long --mod 80 -o replay_long19.csv

## 抽样规则（机械可复现，无人工干预）

```
main31   md5(session_id)[:8] 十六进制 mod 200 == 0
mid17    在 main31 里再 md5("half"+session_id) mod 2 == 0
long     【会话在语料里的全部轮数 ≥ MIN_ROUNDS】的子集，再 md5(session_id)[:8] mod N == 0
```

⚠ **为什么用哈希取模，不用「按 ID 排序取前 N 个」**：语料 71% claude / 29% codex，
ID 以 provider 名开头，**排序会把同一家聚在一起**（实测「前 15 个」拿到 claude 15 /
codex 0）。哈希取模没有这个偏差。

## 三个口径（与文档一致，别改）

```
arrival_time    一律 0        —— 一次性全倒
tool_wait       截到 300_000  —— 与旧的 5 轮 trace 上限一致
轮数            用【全部轮数】—— 不做长度筛选、不做轮数截断
```

工作量的两个口径（`--stats` 会打）：
```
必要 = Σ(input_len + output_len)                     真正要算的 prefill + 生成的
最坏 = Σ(prefix_len + input_len + output_len)        每轮全量重算
倍   = 最坏 / 必要                                   理论浪费上界
```
⚠ 别漏 `output_len` —— 我 2026-10-12 漏过一次，算出来 1.83M 对不上文档的 2.04M。
"""
import argparse
import csv
import hashlib
import os
import sys
from collections import defaultdict

CORPUS = "/data/xbw/turnstile/data/replay_sessions_96k.csv"
TOOL_CAP = 300_000
FIELDS = ["session_id", "round_idx", "prefix_len", "input_len", "output_len",
          "tool_wait_after_ms", "arrival_time"]


def mod8(sid):
    """md5 前 8 位十六进制 —— 与建 main31 / mid17 时用的是同一个函数。"""
    return int(hashlib.md5(sid.encode()).hexdigest()[:8], 16)


def load_corpus(path):
    rows = defaultdict(list)
    with open(path) as f:
        for r in csv.DictReader(f):
            rows[r["session_id"]].append(r)
    for v in rows.values():
        v.sort(key=lambda r: int(r["round_idx"]))
    return rows


def select(rows, mode, mod):
    if mode == "main31":
        return sorted(s for s in rows if mod8(s) % 200 == 0)
    if mode == "mid17":
        m = [s for s in rows if mod8(s) % 200 == 0]
        return sorted(s for s in m if mod8("half" + s) % 2 == 0)
    if mode == "long":
        return sorted(s for s in rows if len(rows[s]) >= 20 and mod8(s) % mod == 0)
    raise SystemExit("未知模式 " + mode)


def write(rows, sel, out):
    tmp = out + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for s in sel:
            for r in rows[s]:
                w.writerow([s, r["round_idx"], r["prefix_len"], r["input_len"],
                            r["output_len"],
                            min(int(r["tool_wait_after_ms"]), TOOL_CAP), 0])
    os.replace(tmp, out)


def stats(rows, sel):
    need = sum(int(r["input_len"]) + int(r["output_len"]) for s in sel for r in rows[s])
    worst = sum(int(r["prefix_len"]) + int(r["input_len"]) + int(r["output_len"])
                for s in sel for r in rows[s])
    rn = sorted(len(rows[s]) for s in sel)
    prov = defaultdict(int)
    for s in sel:
        prov[s.split(":")[0]] += 1
    return dict(sessions=len(sel), steps=rn and sum(rn), need=need, worst=worst,
                ratio=worst / need, rmin=rn[0], rmed=rn[len(rn) // 2], rmax=rn[-1],
                prov=dict(prov))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--out", "-o", default="-")
    ap.add_argument("--mod", type=int, default=80)
    ap.add_argument("--verify", action="store_true",
                    help="复现 main31 并与实验机上那份逐字节对拍")
    ap.add_argument("--long", dest="mode", action="store_const", const="long",
                    help="长会话集合（≥20 轮）")
    ap.add_argument("--mode", choices=["main31", "mid17", "long"], default="long")
    a = ap.parse_args()

    rows = load_corpus(a.corpus)
    print(f"语料: {len(rows)} 会话 / {sum(len(v) for v in rows.values())} 步", file=sys.stderr)

    if a.verify:
        a.mode, a.out = "main31", "/tmp/_verify_main31.csv"
    sel = select(rows, a.mode, a.mod)
    write(rows, sel, a.out)
    st = stats(rows, sel)
    md5 = hashlib.md5(open(a.out, "rb").read()).hexdigest()
    print(f"{a.mode:8s} {st['sessions']:3d} 会话 / {st['steps']:5d} 步 | "
          f"必要 {st['need']/1e6:5.2f}M 最坏 {st['worst']/1e6:6.2f}M 倍 {st['ratio']:5.1f} | "
          f"轮数 {st['rmin']}~{st['rmax']} (中位 {st['rmed']}) | {st['prov']} | md5 {md5[:12]}")

    if a.verify:
        # 文档口径的期望值（见 docs/prereg_atonce_20261010.md）
        exp = {"sessions": 31, "steps": 440, "md5": "e406a8aa8c44"}
        ok = (st["sessions"] == exp["sessions"] and st["steps"] == exp["steps"]
              and md5[:12] == exp["md5"])
        print("  ✓ 复现 main31：逐字节相同" if ok else f"  ✗ 复现失败（期望 {exp}）")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
