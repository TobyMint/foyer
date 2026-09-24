#!/usr/bin/env python3
"""重跑落地后的对照 —— 旧（受争用）vs 新（干净）。

用途：四条被同机争用损害的臂（bres/hz0/hz2/breshz1）与 cap1 正在重跑。
它们一落地就要回答三个问题，这个脚本一次给出：
  1. 判决变不变 —— 新的 Δ 是还在线下，还是进了打平带甚至越线
  2. 争用到底抬了多少 —— 墙钟 / SLO / τ₂ 的差
  3. 体积列有没有被动过 —— 复用率与重算量（论文声称争用只动时间不动体积，
     这是那个声明的检验）

判据与 frontier.py / gen_table.py 完全一致（同一个 front_slo，不另写插值）。

用法:
  python3 compare_rerun.py <results_dir> <old_run> <new_run> [<old> <new> ...]
例:
  python3 compare_rerun.py results/night \\
      pois200_foyer_bres pois200_foyer_bres_r2 \\
      pois200_foyer_hz0  pois200_foyer_hz0_r2
"""
import csv, json, os, statistics, sys


def front_mod():
    import importlib.util
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontier.py")
    spec = importlib.util.spec_from_file_location("_fr", fp)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def tau2(root, run):
    p = os.path.join(root, run, "steps.jsonl")
    if not os.path.exists(p):
        return None
    st = [json.loads(l) for l in open(p) if l.strip()]
    ok = [s for s in st if (s.get("output_len_actual") or 0) >= 32
          and s.get("status") == "SUCCESS"]
    if not ok:
        return None
    return statistics.median(
        (s["total_duration_ms"] - s["first_token_ms"]) / max(1, (s["output_len_actual"] - 1))
        for s in ok)


def volumes(root, run):
    """复用率与重算量 —— 检验「争用只动时间不动体积」。"""
    sp = os.path.join(root, run, "steps.jsonl")
    if not os.path.exists(sp):
        return None, None
    st = [json.loads(l) for l in open(sp) if l.strip()]
    prompt = sum(s.get("prompt_len") or 0 for s in st)
    unc = sum(s.get("server_uncached_prompt_tokens") or 0 for s in st)
    return (prompt - unc) / prompt if prompt else None, unc


def main():
    root = sys.argv[1]
    pairs = list(zip(sys.argv[2::2], sys.argv[3::2]))
    FR = front_mod()
    print("%-26s %8s %7s %8s %9s %8s %9s" % (
        "run", "wall", "SLO%", "front", "delta", "τ₂", "复用%"))
    for old, new in pairs:
        for tag, r in (("OLD(争用)", old), ("NEW(干净)", new)):
            d = FR.summarise(r)
            if not d:
                print("%-26s  -- 缺日志 --" % r)
                continue
            f = FR.front_slo(d["wall"])
            dl = "" if f is None else "%+.2f" % (d["slo"] - f)
            rf, unc = volumes(root, r)
            print("%-26s %8.1f %7.1f %8s %9s %8s %9s   %s" % (
                r, d["wall"], d["slo"], "" if f is None else "%.1f" % f, dl,
                "%.1f" % (tau2(root, r) or float("nan")),
                "%.2f" % (rf * 100) if rf is not None else "?",
                tag))
        # 差值
        do, dn = FR.summarise(old), FR.summarise(new)
        if do and dn:
            fo, fn = FR.front_slo(do["wall"]), FR.front_slo(dn["wall"])
            ro, uo = volumes(root, old)
            rn, un = volumes(root, new)
            print("    %-22s %8.1f %7.1f %8s %9s %8s %9s" % (
                "  Δ(new-old)",
                dn["wall"] - do["wall"], dn["slo"] - do["slo"], "",
                "" if (fo is None or fn is None) else "%+.2f" % ((dn["slo"] - fn) - (do["slo"] - fo)),
                "%.1f" % ((tau2(root, new) or 0) - (tau2(root, old) or 0)),
                "" if (ro is None or rn is None) else "%+.2f" % ((rn - ro) * 100)))
            # 判决是否改变
            def verdict(slo, f):
                if f is None:
                    return "OUT"
                d = slo - f
                return "ABOVE" if d > 1 else "TIE" if d >= -1 else "BELOW"
            vo = verdict(do["slo"], fo) if fo is not None else "OUT"
            vn = verdict(dn["slo"], fn) if fn is not None else "OUT"
            if vo != vn:
                print("    *** 判决改变: %s -> %s ***" % (vo, vn))
            else:
                print("    判决不变（%s）" % vn)
        print()


if __name__ == "__main__":
    main()
