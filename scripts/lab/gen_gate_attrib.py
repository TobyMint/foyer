#!/usr/bin/env python3
"""「有会话在等、却一个都不放行」的周期里，到底是什么在挡？

## ⚠⚠ 2026-09-27（中立复核 r48 第 6 条）：**本机与实验机的集合数不一致**

- **实验机上跑**（脚本 docstring 说必须在机器上跑）：**48 行 / 上中位 31.3%**
- **本地镜像上跑**：**49 行 / 上中位 30.6%** —— 与随文件发布的
  `paper/data/gate_attrib.csv`（49 个数据行）**逐字相同**
- 正文 §V 写的是 **49 / 30.6%**，且句子里点名了范围：「over every completed run
  **in that file**」—— 那个 "file" 就是 `gate_attrib.csv`。所以**正文与工件自洽**，
  本地镜像也能逐字复现它。

差的那一行是 `load25c_budget3_sf0`（25 档、池 101432、trace `replay_night25.csv`、
policy `budget3:margin=1.0;sf=0`）。**它的目录在实验机上已被清理，本地镜像还留着。**

⇒ **本轮的决定是保留 49/30.6%**，理由：正文说的是「那份文件里的每一条」，
而那份文件就是发布出去的那个 49 行的文件；本脚本的选 run 判据是
`glob(*/controller.jsonl)` + 池子匹配，**不区分档位**，所以 25 档那条本来就该在。

✅ **2026-09-27 08:1x 已复验**：按 docstring 在实验机上重跑，机器值与仓库里的
`gate_attrib.csv` **逐字节相同**（同一个 50 行、同一批数）—— 因此上面那段
「机器 48 / 本地 49」的**历史分歧已随两条新 run 落地而消失**（三条 run 的原集合
现在两侧一致）。同类复验一次做完了四张机器端表：`gen_concurrency` /
`gen_gate_attrib` / `gen_projection` / `gen_repeat_spread` **全部逐字节相同**。

（历史记录，保留供追溯）⚠ **下一个人应当知道**：此前在实验机上按 docstring 跑会得到 **48**，
与正文差一行。**不是正文错，是机器上少了一个目录。** 谁要把这个分歧消灭掉，
要动的是**镜像**（找回或正式声明删除那个 run），不是改正文的数。

⚠ 同类风险还有一处（同一天发现，方向相反）：`gen_eviction.py` 的集合在
**本地少一条、实验机多一条**（`slice23_hc`）。**同一天同一个病出现两次，
两个方向各一次** —— 凡「正文数字 = 本地镜像数字」的地方，都要问一句
「实验机给的也是这个数吗」。


## 撤回记录（2026-09-24）

本脚本的第一版**是错的，且错得方向相反**。它用日志里的 `base` 字段算投影：

    (d.get("base") or 0) + (d.get("growth_sum") or 0) > d["budget"]

但 `base` 被 controller_budget3.py 的候选循环重绑（`base = s["ctx"] or s["prompt0"]`
写在循环内、日志写在循环后），实测在 `pois200_foyer_hc` 的 8784 个周期里
**恒为 0**。于是那一项退化成 `growth_sum` 单独一个量，报出来的
「投影超预算 0.2%」「98.3% 的周期投影 < 90% 预算」「中位 29%」
**全是 growth reserve 的统计量，不是投影的**。

按正确投影（同 gen_projection.py：`max(resident, ctx_sum) + growth_sum`）重算：
被挡周期里 **44.4% 是投影超预算**、只有 43.7% 低于 90% 预算。
也就是说拦人的主要就是**估算值**，与第一版结论相反。

## 归因的可判定性（诚实标注）

准入判定是一个合取式：

    if waiting and not valve and not gate_full and (prev_started or sf_disabled):
        逐个候选试 projection + n <= budget

- `valve`、`gate_full`、正确的 `projection` 都能从日志直接算 —— 可判定。
- `prev_started`（单飞闸门）**日志里没有**。所以「剩下的是什么」无法直接判定：
  在 sf 开着的臂上，剩下的既可能是「单飞闸门没满足」，也可能是
  「试了队首但塞不进」。本脚本把它单列一档 remainder，并明确标注为不可判定。
- **`sf=0` 的臂是天然的探针**：单飞关掉时 `(prev_started or True)` 恒真，
  闸门不可能拦人，所以它的 remainder 只可能是「没有候选者塞得进预算」。
  拿它可给出单飞贡献的上界。
"""
import glob, json, os, sys


def load(p):
    out = []
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if "budget" in d and "ctx_sum" in d and "growth_sum" in d and "waiting_n" in d:
            out.append(d)
    return out


def proj(d):
    """与 gen_projection.py / 部署代码 322-326 行同一算法。"""
    return max(d.get("resident") or 0, d.get("ctx_sum") or 0) + (d.get("growth_sum") or 0)


# 论文正文引用的统计集合 —— 【显式列名】，不再用"十九条"这种无法复现的口径。
# 这是 Table I 的控制器段（九条 Foyer 变体 + 两个 AIMD 设置）。
# 九条 Foyer 变体里，有八条留了 controller.jsonl；foyfix_hc 与两个 AIMD 没有
# （AIMD 走另一套控制器），所以它们不在本表里 —— 正文必须按这八条写。
# 论文里引用的臂，显式列出（避免"十八条"这种不可复现的口径）。
# ⚠ foyer_sf0_r2 必须在里面：§V 用它的 remainder/projection-over 两个数论证
# 单飞闸门占约十五个点，而那两个数曾经【只存在于正文里、不在任何 CSV 里】，
# 且与仓库脚本复算的值对不上（正文 39.9/43.5，复算 39.7/44.0）——
# 2026-09-24 审稿人抓到的。纳进来之后正文只能引用 CSV。
PAPER_SET = ["pois200_foyer_hz0_r2", "pois200_foyer_hz1", "pois200_foyer_hz2_r2",
             "pois200_foyer_hc", "pois200_foyer_bres_r2", "pois200_foyer_breshz1_r2",
             "pois200_foyer_nogate", "pois200_foyer_rg4",
             "pois200_foyer_sf0_r2", "pois200_foyer_hc_r2"]


# 必须在实验机上跑：本表统计【所有】带 controller.jsonl 的 run，本地镜像是部分快照
# （2026-09-24 实测：本地 34 行 vs 实验机 46 行），在本地跑会把正文引用的
# 「over every run in that file」那两个中位数算错（27.0/5.4 是 22 行的旧快照，
# 实验机 46 行给 27.4/5.3）。见 CLAUDE.md「本地镜像是部分快照」。
MIN_ROWS = 40


def main():
    root = sys.argv[1]
    out_path = sys.argv[2]
    # 只统计控制器臂（有 ctx_sum 的），并把集合显式列出来，避免"十八"这种不可复现的口径
    rows = []
    # ⚠ 2026-09-27（独立复核 + codex r48）：**按池子把别的机器排除掉**。
    # 本地镜像里混进了 A100 的 run（`a100_foyer_hz2`，池子 983{,}728），而本表是给
    # **3090 部署**用的：一个 9.7 倍大的池子上的投影比值跑进来，会把区间从
    # 1.32--1.96 悄悄撑到 1.32--2.00，读者看不出来。
    # 判据用项目自己的有效性规则（CLAUDE.md：KV pool 必须落在 101,432 ± 20，
    # 否则该 run 作废）—— 池子不是 101,432 的，就不是 3090 的 run。
    POOL_3090, POOL_TOL = 101432, 20

    def _pool_ok(d):
        try:
            m = json.load(open(os.path.join(d, "metadata.json")))
        except Exception:
            return False
        pt = m.get("pool_tokens")
        return pt is not None and abs(pt - POOL_3090) <= POOL_TOL

    for p in sorted(glob.glob(os.path.join(root, "*", "controller.jsonl"))):
        if not _pool_ok(os.path.dirname(p)):
            continue
        run = os.path.basename(os.path.dirname(p))
        if run.startswith("_"):
            continue
        # 只算【跑完的】run：本表的 all_rows 中位数是对「所有带 controller.jsonl 的 run」
        # 取的，在跑的 run（还没写 summary.json）会带着任意长度的日志混进来 ——
        # 2026-09-25 实测：在跑的 foyer_hz0_r2（275 个周期）把 all_rows 的投影超预算
        # 中位从 27.4 拖到 27.3。生成器必须在实验机上跑，而实验机上永远有 run 在跑，
        # 所以这条过滤是必须的，不是可选的。
        if not os.path.exists(os.path.join(os.path.dirname(p), "summary.json")):
            continue
        L = load(p)
        if len(L) < 200:
            continue
        # 单飞是否关闭（从 metadata 的 policy 读）
        mp = os.path.join(os.path.dirname(p), "metadata.json")
        pol = ""
        if os.path.exists(mp):
            try:
                pol = json.load(open(mp)).get("policy", "") or ""
            except ValueError:
                pass
        sf_off = "sf=0" in pol
        b = L[-1]["budget"]
        blk = [d for d in L if (d.get("waiting_n") or 0) > 0 and (d.get("n_admitted") or 0) == 0]
        if not blk:
            continue
        n = len(blk)
        valve = sum(1 for d in blk if d.get("valve"))
        gate = sum(1 for d in blk if not d.get("valve") and d.get("gate_full"))
        over = sum(1 for d in blk if not d.get("valve") and not d.get("gate_full")
                   and proj(d) > b)
        rem = n - valve - gate - over
        # starve guard：唯一绕过预算的通道。§V 用 foyer_hc 的三个数论证
        # 「投影超预算时只有它能进来」：全部超预算周期数、其中放了人的、其中被强制的。
        # 这三个数 2026-09-24 之前只在正文里（3,700 / 9 / 9），文件里没有，于是落列。
        forced = sum(1 for d in L if d.get("forced"))
        admits = sum(1 for d in L if (d.get("n_admitted") or 0) > 0)
        over_all = [d for d in L if proj(d) > b]
        over_adm = [d for d in over_all if (d.get("n_admitted") or 0) > 0]
        over_forced = [d for d in over_adm if d.get("forced")]
        rows.append(dict(run=run, n=n, blocked=n, valve=valve, gate=gate, over=over, rem=rem,
                         sf_off=sf_off, forced=forced, admits=admits, samples=len(L),
                         over_all=len(over_all), over_all_admitted=len(over_adm),
                         over_all_forced=len(over_forced)))
    assert len(rows) >= MIN_ROWS, (
        "只统计到 %d 行的闸门归因（需要 >=%d）—— 这多半是部分镜像，本脚本必须在实验机上跑"
        % (len(rows), MIN_ROWS))
    rows.sort(key=lambda r: -r["over"] / r["blocked"])
    print("%-26s %6s %8s %7s %7s %8s %9s %6s" % (
        "run", "采样", "被挡", "阀门%", "gate%", "投影超%", "remainder%", "sf关"))
    for r in rows:
        k = r["blocked"]
        print("%-26s %6d %8d %6.1f %6.1f %7.1f %9.1f %6s" % (
            r["run"], r["samples"], k, 100*r["valve"]/k, 100*r["gate"]/k,
            100*r["over"]/k, 100*r["rem"]/k, "Y" if r["sf_off"] else ""))
    with open(out_path, "w") as f:
        f.write("# 「有等待不放行」周期的闸门归因 —— gen_gate_attrib.py 生成\n")
        f.write("# 投影 = max(resident, ctx_sum) + growth_sum（【不是】被重绑污染的 base 字段）\n")
        f.write("# remainder = 排除 valve/gate/投影超预算后剩下的，含【单飞闸门】与【队首塞不进】两类，\n")
        f.write("#   日志里没有 prev_started，无法区分，故不做单飞归因。sf_off=Y 的臂是探针：\n")
        f.write("#   单飞关闭时闸门不可能拦人，其 remainder 只可能是「没有候选者塞得进预算」。\n")
        f.write("run,samples,blocked_cycles,valve_pct,round_gate_pct,projection_over_pct,"
                "remainder_pct,sf_disabled,forced_admits,total_admits,"
                "cycles_over_budget,admitted_while_over,forced_while_over\n")
        for r in rows:
            k = r["blocked"]
            f.write("%s,%d,%d,%.1f,%.1f,%.1f,%.1f,%s,%d,%d,%d,%d,%d\n" % (
                r["run"], r["samples"], k, 100*r["valve"]/k, 100*r["gate"]/k,
                100*r["over"]/k, 100*r["rem"]/k, "Y" if r["sf_off"] else "N",
                r["forced"], r["admits"], r["over_all"], r["over_all_admitted"],
                r["over_all_forced"]))
    # 论文正文用的集合，单独汇总并写进 CSV（含名单），使那两个中位数可复现
    sel = [r for r in rows if r["run"] in PAPER_SET]
    if sel:
        k = lambda key: sorted(100.0 * r[key] / r["blocked"] for r in sel)
        vp, op, rp = k("valve"), k("over"), k("rem")
        mid = lambda v: v[len(v) // 2]
        print()
        print("论文集合（%d 条，名单见 CSV 注释）：阀门中位 %.1f%%、投影超预算中位 %.1f%%、"
              "remainder 中位 %.1f%%" % (len(sel), mid(vp), mid(op), mid(rp)))
        # 正文用的集合是【八条非重复的 Foyer 臂】（foyfix 与两条 AIMD 跑的是别的
        # 控制器、不记闸门状态）。原来只落 10 条的 PAPER_SET，于是正文引的
        # 「八条」中位数在文件里查不到，而 PAPER_SET 的中位数又对不上正文
        # （2026-09-24 审稿人抓：正文把投影中位 32.7 写进了阀门那一格）。
        eight = {"foyer_bres_r2", "foyer_hc", "foyer_hz2_r2", "foyer_hz1",
                 "foyer_breshz1_r2", "foyer_nogate", "foyer_hz0_r2", "foyer_rg4"}
        s8 = [r for r in rows if r["run"].replace("pois200_", "") in eight]
        k8 = lambda key: sorted(100.0 * r[key] / r["blocked"] for r in s8)
        v8, p8 = k8("valve"), k8("over")
        print("八条非重复 Foyer 臂（正文用的集合）：阀门中位 %.1f%%、投影超预算中位 %.1f%%"
              % (mid(v8), mid(p8)))
        # 两种中位口径（上中位 vs 两数均值）在八条臂上的差 —— 正文 §V 专门有一段
        # 「约定说明」，引的就是这两个数；原来它们只在正文里，文件里没有。
        def mean2(v):
            v = sorted(v); n = len(v)
            return (v[n // 2 - 1] + v[n // 2]) / 2 if n % 2 == 0 else v[n // 2]
        print("两种中位口径在八条臂上的差：投影 %.1fpp、阀门 %.1fpp"
              % (mid(p8) - mean2(p8), mid(v8) - mean2(v8)))
        # 【全表】的上中位也要落成一行：正文写「over every run in that file they are
        # 27.0% and 5.4%」，这两个数【不在】前面任何一行里（eight_* 是八条臂、
        # paper_set_* 是十条），只能从逐行重算 —— 那就不满足「数字要能追到文件」。
        va = sorted(100.0 * r["valve"] / r["blocked"] for r in rows)
        pa = sorted(100.0 * r["over"] / r["blocked"] for r in rows)
        ra = sorted(100.0 * r["rem"] / r["blocked"] for r in rows)
        print("全表（%d 条）：阀门上中位 %.1f%%、投影超预算上中位 %.1f%%、remainder 上中位 %.1f%%"
              % (len(rows), mid(va), mid(pa), mid(ra)))
        with open(out_path, "a") as f:
            f.write("# all_rows_median（%d 条，正文「over every run in that file」用的就是这一行）,"
                    "valve_pct=%.1f,projection_over_pct=%.1f,remainder_pct=%.1f\n"
                    % (len(rows), mid(va), mid(pa), mid(ra)))
        with open(out_path, "a") as f:
            f.write("# 正文用的集合（八条非重复 Foyer 臂）：%s\n" % " ".join(sorted(
                r["run"] for r in s8)))
            f.write("# eight_median,valve_pct=%.1f,projection_over_pct=%.1f\n"
                    % (mid(v8), mid(p8)))
            f.write("# eight_range,valve=%.1f~%.1f,projection_over=%.1f~%.1f\n"
                    % (v8[0], v8[-1], p8[0], p8[-1]))
            f.write("# convention_delta（上中位 − 两数均值，八条臂）,"
                    "projection_pp=%.1f,valve_pp=%.1f\n"
                    % (mid(p8) - mean2(p8), mid(v8) - mean2(v8)))
            f.write("# 论文正文引用的集合：%s\n" % " ".join(sorted(r["run"] for r in sel)))
            f.write("# paper_set_median,valve_pct=%.1f,projection_over_pct=%.1f,remainder_pct=%.1f\n"
                    % (mid(vp), mid(op), mid(rp)))
            f.write("# paper_set_range,valve=%.1f~%.1f,projection_over=%.1f~%.1f\n"
                    % (vp[0], vp[-1], op[0], op[-1]))
    # ---- 【部分运行】的闸门臂：正文引了它们的百分比，但上面「只算跑完的 run」
    # 的过滤把它们排除了（没有 summary.json），于是那两个数**此前只活在正文里**，
    # 不在任何文件里 —— 2026-09-26 codex 第 31 轮抓到。
    # 落成**注释行**而不是数据行：进数据行会改 `all_rows` 的条数与中位数，
    # 而正文引的正是那个中位数（45 条 / 30.6%）。注释行不进任何统计。
    for _run in ("pois200_foyer_rg2", "pois200_foyer_rg3", "pois200_foyer_rg4"):
        _d = os.path.join(root, _run)
        _cp = os.path.join(_d, "controller.jsonl")
        if not os.path.exists(_cp):
            print("!! %s 不在镜像里 —— 正文引了它的闸门百分比，缺了就对不上" % _run)
            continue
        _L = load(_cp)
        _blk = [d for d in _L if (d.get("waiting_n") or 0) > 0
                and (d.get("n_admitted") or 0) == 0]
        if not _blk:
            continue
        _g = sum(1 for d in _blk if not d.get("valve") and d.get("gate_full"))
        _sp = os.path.join(_d, "steps.jsonl")
        _n = sum(1 for l in open(_sp) if l.strip()) if os.path.exists(_sp) else 0
        # ⚠ `finished` 的判据**不是**「summary.json 在不在」—— `rg4` 有 summary，
        # 但它是 **998 attempted / 1 failed**（codex 第 32 轮抓到：只看 summary 会把它
        # 标成 Y，而正文说「三条里两条是部分运行」用的却是 999/0 的口径）。
        # 判据统一成**999 步、0 失败**，并把 attempted/failed 一起落进那一行。
        _sum = os.path.join(_d, "summary.json")
        _att = _fail = None
        if os.path.exists(_sum):
            try:
                _rp = json.load(open(_sum)).get("replay", {})
                _att, _fail = _rp.get("attempted_steps"), _rp.get("failed_steps")
            except ValueError:
                pass
        _fin = "Y" if (_att == 999 and _fail == 0) else "N"
        print("  named arm %-20s cycles %5d blocked %5d round_gate %.1f%% steps %d "
              "attempted=%s failed=%s 999/0=%s"
              % (_run, len(_L), len(_blk), 100.0 * _g / len(_blk), _n,
                 _att, _fail, _fin))
        with open(out_path, "a") as f:
            f.write("# named_arm,%s,cycles=%d,blocked=%d,round_gate_pct=%.1f,steps=%d,"
                    "attempted=%s,failed=%s,finished_999_0=%s\n"
                    % (_run, len(_L), len(_blk), 100.0 * _g / len(_blk), _n,
                       _att, _fail, _fin))
    print("-> %s" % out_path)


if __name__ == "__main__":
    main()
