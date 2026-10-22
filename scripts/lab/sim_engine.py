#!/usr/bin/env python3
"""离线模拟器：不烧卡就能试准入策略。

## 为什么要有它

改一次准入策略要起一次 server、跑 2~3 小时、还得等卡。而策略的迭代是要试十几次的。
这个模拟器把「引擎 + 池子 + 会话」做成一个可复现的玩具，**先用它把设计空间走一遍，
只把活下来的那一两个策略拿去上卡**。

## 它必须先在【真值】上标定过，否则结论不能信

    long19_foyer    工作量 6.72M   整批 165.2 分   冷回来 21.4%
    long19_default  工作量 22.79M  整批 236.1 分   冷回来 86.7%

`--calibrate` 会跑这两条并打误差。**标定不过关，模拟器说什么都不算。**

## 模型（诚实说明它哪里是假的）

真的部分：
  · 每轮的服务时间 ∝ 要算的 token 数（prefill + decode），且随并发 N 变慢（弹性 ε）
  · 池子是硬约束：Σ 驻留会话的上下文 ≤ pool，超了就必须驱逐
  · 驱逐按 LRU 选会话；被驱逐的会话下一轮要【整段重算】
  · 工具等待是强制的（会话在这段时间不能跑，但【可以】继续占着池子）

假的部分（这些是简化，改动机制时要记住）：
  · 驱逐是【整会话】粒度的，真实引擎是块粒度（所以真值的冷回来是概率性的）
  · 前缀共享：所有会话共享同一个 7,606 token 的系统前缀（从 trace 的 prefix_len 观测）
    —— 这只影响容量的绝对占用，不影响策略间的相对比较
  · 并发超限时的排队是 FCFS，真实引擎有自己的调度
"""
import argparse
import csv
import sys
from collections import defaultdict

# ---------- 服务模型（从真值标定出来的）----------
TTFT_S = 0.316          # 无争用时的首字延迟（p10，实测）
TAU_PER_TOKEN = 0.0221  # 每 token 解码秒数（p10，实测）
EPSILON = 0.5           # 服务时间对并发的弹性：N 个并发时，每个慢 N^ε 倍
# ⚠ SVC_SCALE 是【标定因子】，不是物理量：它吸收这个玩具模型没有表示的
#    引擎侧排队（请求进了 SGLang 但拿不到 KV，要等驱逐）。实测真值的
#    「busy 时间 / 步数」约 22 s，而 p10 无争用模型只给 9.6 s ⇒ 差 2.3 倍。
#    标定目标是复现真值的整批时间；**它只保证【相对比较】有意义，绝对值不算数**。
SVC_SCALE = float(__import__("os").environ.get("SVC_SCALE", "1.0"))
GLOBAL_PRIOR = 2848.0   # 全局平均的每轮增长（实测，controller.jsonl 的 glob_growth_prior）
SLOTS = 2               # 引擎同时最多跑几个请求


def load_trace(path):
    s = defaultdict(list)
    with open(path) as f:
        for r in csv.DictReader(f):
            s[r["session_id"]].append(r)
    for v in s.values():
        v.sort(key=lambda r: int(r["round_idx"]))
    return s


def ctx_of(r):
    return int(r["prefix_len"]) + int(r["input_len"])


def step_work(r, warm):
    """这一轮要算多少 token。warm=False 时整段重算前缀。"""
    pre, inp, out = int(r["prefix_len"]), int(r["input_len"]), int(r["output_len"])
    return (inp if warm else pre + inp), out


def duration(pre_tok, dec_tok, n_running):
    slow = max(1, n_running) ** EPSILON
    return SVC_SCALE * ((TTFT_S * slow) + dec_tok * TAU_PER_TOKEN * slow)


def simulate(trace, policy, pool=101432, dt=0.25, max_t=40000.0):
    """把「引擎 + 池子 + 会话」跑一遍。

    ## 核心模型：**准入 ≠ 驻留**（这一条写错过一次，整轮标定都废了）

        控制器决定   这个会话【可以进来】—— 一次决定，之后不再变
                      （真实控制器不知道引擎踢没踢它，所以不会重新放行）
        引擎决定     它的前缀【还在不在池子里】—— LRU，随时可能被踢
                      （被踢 ⇒ 下次回来整段重算 ⇒ 这就是浪费的来源）

    把两者合成一个标志，就会让「被踢的会话去重新申请准入」——
    而真实系统里它【不申请，直接冷着跑】，于是模拟出的浪费比真值高 3 倍。

    ## 池子占用每步从状态重算
    增量记账写错过一次（跑完不释放 ⇒ used 只增不减 ⇒ 池子永远是满的）。
    """
    S = {s: dict(k=0, admitted=False, warm=False, state="new", left=0.0,
                 first_admit=None) for s in trace}
    pool_holder = []          # LRU 顺序：谁的前缀在池子里（最后 = 最近用过）
    t = 0.0; running = 0; done = 0
    work = need = 0; cold = warm_n = 0; idle = 0.0
    next_cycle = 0.0

    def ctx_now(s):
        d = S[s]
        return ctx_of(trace[s][d["k"]]) if d["k"] < len(trace[s]) else 0

    def used_now():
        return sum(ctx_now(s) for s in pool_holder if S[s]["warm"])

    def evict_to(pool, used):
        """LRU 驱逐：池子装不下就扔掉最久没碰过的那个会话的前缀"""
        while used > pool and pool_holder:
            x = pool_holder.pop(0)                 # 最久没碰过
            if S[x]["warm"]:
                used -= ctx_now(x); S[x]["warm"] = False
        return used

    while done < len(trace) and t < max_t:
        # ① 推进计时器
        for s, d in S.items():
            if d["state"] == "run":
                d["left"] -= dt
                if d["left"] <= 0:
                    running -= 1
                    r = trace[s][d["k"]]; d["k"] += 1
                    if d["k"] >= len(trace[s]):
                        d["state"] = "done"; done += 1
                        if s in pool_holder: pool_holder.remove(s)
                        d["warm"] = False
                    else:
                        # ★ 这一轮算完 ⇒ 它的完整上下文进了池子（真实引擎就是这样）
                        d["warm"] = True
                        if s in pool_holder: pool_holder.remove(s)
                        pool_holder.append(s)
                        used_now()   # 顺序更新，下一步 ② 会真正驱逐
                        w = min(int(r["tool_wait_after_ms"]), 300000) / 1000.0
                        d["state"], d["left"] = ("wait", w) if w > 0 else ("ready", 0.0)
            elif d["state"] == "wait":
                d["left"] -= dt
                if d["left"] <= 0: d["state"] = "ready"

        # ② 池子：从状态重算 + LRU 驱逐到装得下
        evict_to(pool, used_now())

        # ③ 控制周期：只决定【准入】，不决定驻留
        if t >= next_cycle:
            next_cycle = t + policy["interval"]
            if policy.get("obs"): policy["obs"](t, S, trace, ctx_now)
            notyet = [s for s, d in S.items() if not d["admitted"] and d["state"] != "done"]
            for s in policy["fn"](t, S, trace, ctx_now, notyet, pool, used_now()):
                S[s]["admitted"] = True
                if S[s]["first_admit"] is None: S[s]["first_admit"] = t

        # ④ 起跑：谁【被准入过】且【现在能跑】就跑（引擎按先来后到）
        for s in sorted(S, key=lambda x: (S[x]["first_admit"] if S[x]["first_admit"] is not None else 1e18)):
            if running >= SLOTS: break
            d = S[s]
            if not d["admitted"] or d["state"] not in ("new", "ready"): continue
            r = trace[s][d["k"]]
            pre, dec = step_work(r, d["warm"])
            d["state"] = "run"; d["left"] = duration(pre, dec, running + 1)
            running += 1
            work += pre + dec
            need += int(r["input_len"]) + int(r["output_len"])
            if d["k"] > 0:
                if d["warm"]: warm_n += 1
                else: cold += 1
            if s not in pool_holder: pool_holder.append(s)   # 跑起来就算最近用过
            else:
                pool_holder.remove(s); pool_holder.append(s)
        if running == 0: idle += dt
        t += dt

    return dict(makespan=t, done=done, need=need, work=work,
                waste=work / max(need, 1), cold=cold, warm=warm_n,
                cold_pct=100 * cold / max(cold + warm_n, 1),
                idle_pct=100 * idle / max(t, 1))


# ---------- 两个参照策略 ----------
def pol_default(interval=2.0):
    """完全不管：谁想跑就让谁跑（引擎的贪心行为）"""
    def fn(t, S, trace, ctx_now, waiters, pool, used):
        return waiters
    return {"fn": fn, "interval": interval}


def pol_turnstile(interval=2.0, margin=1.15, horizon=3, alpha=0.4):
    """我们的机制：投影 + 预测增长 ≤ 预算"""
    budget = int(101432 * 0.95)
    ema, last_ctx = {}, {}
    ALPHA = alpha
    def obs(t, S, trace, ctx_now):
        # 每轮开始时，用「本轮 prompt − 上一轮 prompt」更新 EMA
        for s, d in S.items():
            if d["state"] == "run" and d["k"] > 0:
                cur = ctx_now(s)
                prev = last_ctx.get(s)
                if prev is not None and cur > prev:
                    g = float(cur - prev)
                    ema[s] = g if s not in ema else ALPHA*g + (1-ALPHA)*ema[s]
                last_ctx[s] = cur
            elif d["state"] in ("new", "wait", "ready") and d["k"] > 0:
                last_ctx.setdefault(s, ctx_now(s))
    def fn(t, S, trace, ctx_now, waiters, pool, used):
        gsum = 0.0
        for s, d in S.items():
            if d["admitted"] and s in ema:      # 控制器眼里"已经进来的人"
                gsum += ema[s] * horizon
        proj = used + gsum
        out = []
        for s in waiters:                      # waiting 是按到达排的（原样）
            c = ctx_now(s)
            f = (ema[s] * horizon) if s in ema else GLOBAL_PRIOR
            n = (c + f) * margin
            if proj + n <= budget:
                out.append(s)
                proj += n
                break                          # ★ 单飞：一拍只放一个（扫描全队，停在第一个装得下的）
        return out
    return {"fn": fn, "obs": obs, "interval": interval}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default="/tmp/replay_long19.csv")
    ap.add_argument("--policy", default="turnstile", choices=["default", "turnstile"])
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--margin", type=float, default=1.15)
    ap.add_argument("--horizon", type=int, default=3)
    ap.add_argument("--calibrate", action="store_true")
    a = ap.parse_args()

    tr = load_trace(a.trace)
    if a.calibrate:
        print("=== 标定：模拟器 vs 真值 ===")
        print(f"{'':<18}{'工作量':>12}{'整批(min)':>11}{'冷回来%':>9}")
        print("真值 long19_foyer     6.72M      165.2      21.4")
        print("真值 long19_default  22.79M      236.1      86.7")
        for lab, p in (("模拟 turnstile", pol_turnstile(a.interval, a.margin, a.horizon)),
                       ("模拟 default", pol_default(a.interval))):
            r = simulate(tr, p)
            print(f"{lab:<18}{r['work']/1e6:>10.2f}M{r['makespan']/60:>11.1f}{r['cold_pct']:>9.1f}  (完成 {r['done']}/19)")
        return
    p = pol_turnstile(a.interval, a.margin, a.horizon) if a.policy == "turnstile" else pol_default(a.interval)
    r = simulate(tr, p)
    for k, v in r.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
