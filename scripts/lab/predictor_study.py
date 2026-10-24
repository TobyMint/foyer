#!/usr/bin/env python3
""""换个更聪明的预测器有用吗？" —— 离线对照实验（不占卡）。

用法：python3 predictor_study.py data/replay_long19.csv [--csv out.csv]

## 为什么做这个

论文的论点是"不用预测"。但审稿人会问：你怎么知道不是"你们的预测器太笨"？
所以我们要主动把更聪明的预测器（线性回归、小型神经网络、kNN）和**神谕**（直接知道
未来）都试一遍，看它们能不能改变**准入决策**。

## 口径

- 预测目标：`y = ctx_{i+3} − ctx_i`，即未来 3 轮（复用距离中位是 3）的累计增长。
- 所有预测器共用同一个记账规则：`charge = (ctx + ĝ) × 1.15`，
  **余量 R = charge − ctx**。这样比较的是"预测器"，不是"margin 调得多好"。
- 决策指标：`coverage = P(y ≤ R)`、`slack = median((R−y)/ctx)`、
  `fit = 每个时刻能驻留几个会话`（预算 0.95×池子，按升序装）。
- 验证：**留一会话交叉验证**（19 折，每次用 18 个会话训练、1 个预测），
  避免"在训练集上预测训练集"。

## 预测器

| 名字 | 说明 |
|---|---|
| zero | 不留余量（ĝ=0） |
| global | 全局平均增长 × 3 |
| ema3 | **现在部署的**：EMA(0.4) × 3 |
| ridge | 线性回归（闭式解 + L2） |
| mlp | 2 层神经网络（numpy 手写，16 隐单元，Adam） |
| knn | k=5 最近邻 |
| oracle | 直接给真实 y（上界） |
"""
import csv
import sys
from collections import defaultdict

import numpy as np

H = 3          # 预测未来 3 轮的累计增长（= 复用距离中位）
MARGIN = 1.15  # 与部署一致
POOL = 101502
BUDGET = POOL * 0.95


def load(path):
    by = defaultdict(list)
    for r in csv.DictReader(open(path)):
        by[r["session_id"]].append({
            "i": int(r["round_idx"]),
            "ctx": int(r["prefix_len"]) + int(r["input_len"]),
            "out": int(r["output_len"]),
            "tw": float(r["tool_wait_after_ms"]),
            "kind": 0 if r["session_id"].startswith("claude") else 1,
        })
    for v in by.values():
        v.sort(key=lambda x: x["i"])
    return by


def build(by):
    """样本：(features, target, ctx, session)。只在还能看到未来 H 轮的轮次上取。"""
    X, y, ctx, sid, ridx = [], [], [], [], []
    for s, v in by.items():
        for i in range(len(v) - H):
            c = v[i]["ctx"]
            nxt = v[i + H]["ctx"]
            hist = [v[j + 1]["ctx"] - v[j]["ctx"] for j in range(i)]
            last1 = hist[-1] if hist else 0
            m3 = np.mean(hist[-3:]) if hist else 0
            m5 = np.mean(hist[-5:]) if hist else 0
            mx = max(hist) if hist else 0
            X.append([c / 1000.0, i / 10.0, last1 / 1000.0, m3 / 1000.0,
                      m5 / 1000.0, mx / 1000.0, v[i]["kind"], len(hist) / 10.0])
            y.append((nxt - c) / 1000.0)   # 单位：K token
            ctx.append(c)
            sid.append(s)
            ridx.append(i)
    return np.array(X), np.array(y), np.array(ctx), np.array(sid), np.array(ridx)


class Ridge:
    def __init__(self, lam=1.0):
        self.lam = lam

    def fit(self, X, y):
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Z = (X - self.mu) / self.sd
        A = np.hstack([Z, np.ones((len(Z), 1))])
        self.w = np.linalg.solve(A.T @ A + self.lam * np.eye(A.shape[1]), A.T @ y)
        return self

    def predict(self, X):
        Z = (X - self.mu) / self.sd
        A = np.hstack([Z, np.ones((len(Z), 1))])
        return A @ self.w


class MLP:
    """2 层 numpy 网络（16 隐单元，tanh，Adam）。"""

    def __init__(self, hidden=16, epochs=800, lr=0.01, seed=0, wd=1e-4):
        self.h, self.epochs, self.lr, self.seed, self.wd = hidden, epochs, lr, seed, wd

    def fit(self, X, y):
        rng = np.random.default_rng(self.seed)
        # 内部验证集做早停（19 个会话、545 个样本，不早停必过拟合）
        n = len(X)
        perm = rng.permutation(n)
        nv = max(20, n // 5)
        vidx, tidx = perm[:nv], perm[nv:]
        Xv, yv = X[vidx], y[vidx]
        X, y = X[tidx], y[tidx]
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Z = (X - self.mu) / self.sd
        ym, ys = y.mean(), y.std() + 1e-9
        T = (y - ym) / ys
        d = Z.shape[1]
        W1 = rng.normal(0, 1 / np.sqrt(d), (d, self.h))
        b1 = np.zeros(self.h)
        W2 = rng.normal(0, 1 / np.sqrt(self.h), (self.h, 1))
        b2 = np.zeros(1)
        params = [W1, b1, W2, b2]
        ms = [np.zeros_like(p) for p in params]
        vs = [np.zeros_like(p) for p in params]
        best, best_p, best_ep = 1e18, None, 0
        for t in range(1, self.epochs + 1):
            Hh = np.tanh(Z @ W1 + b1)
            out = (Hh @ W2 + b2).ravel()
            err = out - T
            gW2 = Hh.T @ err[:, None] / len(Z)
            gb2 = np.array([err.mean()])
            gH = (err[:, None] @ W2.T) * (1 - Hh ** 2)
            gW1 = Z.T @ gH / len(Z)
            gb1 = gH.mean(0)
            for k, g in enumerate([gW1, gb1, gW2, gb2]):
                ms[k] = 0.9 * ms[k] + 0.1 * g
                vs[k] = 0.999 * vs[k] + 0.001 * g * g
                mh = ms[k] / (1 - 0.9 ** t)
                vh = vs[k] / (1 - 0.999 ** t)
                params[k] -= self.lr * mh / (np.sqrt(vh) + 1e-8)
            W1, b1, W2, b2 = params
            if t % 25 == 0:
                Zv = (Xv - self.mu) / self.sd
                pv = ((np.tanh(Zv @ W1 + b1) @ W2 + b2).ravel()) * ys + ym
                vl = float(np.mean(np.abs(pv - yv)))
                if vl < best:
                    best, best_ep = vl, t
                    best_p = [p.copy() for p in params]
        self.p = best_p if best_p is not None else params
        self.ym, self.ys = ym, ys
        self.best_ep = best_ep
        return self

    def predict(self, X):
        W1, b1, W2, b2 = self.p
        Z = (X - self.mu) / self.sd
        return ((np.tanh(Z @ W1 + b1) @ W2 + b2).ravel()) * self.ys + self.ym


class KNN:
    def __init__(self, k=5):
        self.k = k

    def fit(self, X, y):
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        self.Z, self.y = (X - self.mu) / self.sd, y
        return self

    def predict(self, X):
        Z = (X - self.mu) / self.sd
        out = []
        for z in Z:
            d = ((self.Z - z) ** 2).sum(1)
            idx = np.argsort(d)[:self.k]
            out.append(self.y[idx].mean())
        return np.array(out)


def metrics(ghat, y, ctx):
    """所有预测器共用的记账与决策指标。单位都是 K token。"""
    R = (ctx / 1000.0 + ghat) * MARGIN - ctx / 1000.0     # 余量（K）
    cov = 100.0 * np.mean(y <= R)
    slack = 100.0 * np.median((R - y) / (ctx / 1000.0))
    mae = float(np.mean(np.abs(ghat - y)))
    return mae, cov, slack


def fit_count(charges_by_round):
    """按【轮次】分组算能装下几个，再取中位。混在一起算会把早轮的小上下文和晚轮
    的大上下文搅在一起，得出 8 这种假数（踩过）。"""
    ks = []
    for i, ch in charges_by_round.items():
        ch = sorted(ch)
        s = 0
        k = 0
        for c in ch:
            if s + c * 1000 <= BUDGET:
                s += c * 1000
                k += 1
            else:
                break
        ks.append(k)
    return (int(np.median(ks)) if ks else 0,
            100.0 * sum(1 for k in ks if k >= 2) / len(ks) if ks else 0.0)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data/replay_long19.csv"
    csv_out = None
    if "--csv" in sys.argv:
        csv_out = sys.argv[sys.argv.index("--csv") + 1]

    by = load(path)
    X, y, ctx, sid, ridx = build(by)
    sessions = sorted(set(sid))
    print("样本 %d，会话 %d，目标 = 未来 %d 轮累计增长（K token）" % (len(y), len(sessions), H))

    preds = {k: np.zeros(len(y)) for k in
             ("zero", "global", "ema3", "ridge", "mlp", "knn", "oracle")}
    ema_vals = []
    for s, v in by.items():
        for i in range(len(v) - H):
            ema = None
            for j in range(i):
                g = v[j + 1]["ctx"] - v[j]["ctx"]
                ema = g if ema is None else 0.4 * g + 0.6 * ema
            ema_vals.append((s, i, (ema or 0) * H / 1000.0))
    ema_map = {(s, i): val for s, i, val in ema_vals}
    keys = []
    for s, v in by.items():
        for i in range(len(v) - H):
            keys.append((s, i))
    for n, k in enumerate(keys):
        preds["ema3"][n] = ema_map[k]

    # 留一会话交叉验证
    for hold in sessions:
        tr = sid != hold
        te = ~tr
        preds["global"][te] = y[tr].mean()
        preds["ridge"][te] = Ridge(1.0).fit(X[tr], y[tr]).predict(X[te])
        preds["mlp"][te] = np.mean([MLP(seed=s_).fit(X[tr], y[tr]).predict(X[te])
                                    for s_ in (1, 2, 3)], axis=0)
        preds["knn"][te] = KNN(5).fit(X[tr], y[tr]).predict(X[te])
    preds["oracle"] = y.copy()

    print("\n%-8s %8s %10s %10s %6s %10s" % ("predictor", "MAE(K)", "coverage", "slack", "fit", "fit>=2"))
    rows = []
    for name in ("zero", "global", "ema3", "ridge", "mlp", "knn", "oracle"):
        g = np.maximum(preds[name], 0)
        mae, cov, slack = metrics(g, y, ctx)
        # fit：用中位时刻的 charge 估算（把所有样本的 charge 分布当近似）
        charge = (ctx / 1000.0 + g) * MARGIN
        by_round = {}
        for i, c in zip(ridx, charge):
            by_round.setdefault(int(i), []).append(c)
        fit, fit2 = fit_count(by_round)
        print("%-8s %8.2f %9.1f%% %9.1f%% %6d %10.1f%%" % (name, mae, cov, slack, fit, fit2))
        rows.append((name, round(mae, 2), round(cov, 1), round(slack, 1), fit, round(fit2, 1)))

    if csv_out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(csv_out)), exist_ok=True)
        with open(csv_out, "w") as f:
            f.write("predictor,mae_k,coverage_pct,slack_pct,fit,fit_ge2_pct\n")
            for r in rows:
                f.write("%s,%.2f,%.1f,%.1f,%d,%.1f\n" % r)
        print("\n写 %s" % csv_out)


if __name__ == "__main__":
    main()
