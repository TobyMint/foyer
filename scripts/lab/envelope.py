#!/usr/bin/env python3
"""上-左包络的插值 —— **共用定义**，3090 与 A100 两套前沿都用它。

为什么抽出来（CLAUDE.md 纪律 2：两个脚本算同一个量，必须共用定义）：
`frontier.py` 里的 `front_slo(wall)` 把锚点表 `FRONT` 写死在 3090 上；
A100 要算「控制器相对 A100 自己的静态前沿」的 Δ，如果再写一份插值，
两边迟早分叉 —— 本项目已有一次同形事故（`gen_table.py` 与 `frontier.py`
各算一遍 Δ，同一条臂给出 −0.55 与 −0.57）。

所以：锚点表由调用方传入，插值逻辑只此一份。
调用方：`frontier.py`（3090 的 FRONT 与 gen_table 的对照）、
`gen_a100_delta.py`（A100 的静态前沿）。
"""


# 容差：锚点 run 自己的墙钟与锚点表里的字面量会差几个 ulp，不加容差会把
# 锚点自己判成「超出范围」（2026-09-24 全精度化之后暴露出来的）。
EPS = 1e-6


def piecewise(x, pts, eps=EPS):
    """分段线性插值 —— **本项目里唯一的一份**。

    `pts` = [(x, y, ...), ...]，**只用到前两个元素**，按 x 升序（内部会再排一次）。
    超出锚点范围（容差 `eps` 之外）返回 None：范围外不给参照，不端点外推。

    调用方：`front_slo`（3090 前沿 / A100 前沿 / `gen_table` 的对照）、
    `gen_pool50.py`（全池「兑现率 ~ R̄」曲线上取同 R̄ 的参照值）。

    ⚠ 抽这一份的原因（codex 第 29 轮，2026-09-26）：`gen_pool50.py` 里原来自己写了
    一份 `interp()`，边界容差与重合锚点的处理都不同 —— 数值上当时碰巧一致，
    所以任何测试都不会响。CLAUDE.md 纪律 2：两个脚本算同一个量必须共用定义，
    **而「共用」的判据是全仓库只剩一份实现，不是「我改了一处」。**

    重合锚点（x0 == x1）取**较大的 y**：前沿的竖直段取上界才是界；对单调曲线
    （如 gen_pool50 的兑现率曲线）不会触发。
    """
    if not pts:
        return None
    pts = sorted(pts)
    if x < pts[0][0] - eps or x > pts[-1][0] + eps:
        return None
    for a, b in zip(pts, pts[1:]):
        x0, y0, x1, y1 = a[0], a[1], b[0], b[1]
        # 容差要加在这里，不只是上面的范围检查：锚点 run 自己的墙钟比锚点表里的
        # 字面量小 5.7e-8，于是 x0 <= x 为假、整条循环都不匹配，锚点被自己的前沿
        # 判成「超出范围」。
        if x0 - eps <= x <= x1 + eps:
            return max(y0, y1) if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def front_slo(wall, front):
    """前沿在给定墙钟处的 SLO 上界。

    `front` = 按 wall 升序的 [(wall, slo, name), ...]（上-左包络的锚点）。

    **超出锚点范围返回 None** —— 范围外没有可比的前沿，不能给判决，
    否则端点外推会凭空造出「越过」。左端尤其危险：A100 的静态扫描只到 cap5
    而墙钟随 cap 单调下降时，「LEFT-OF-FRONT」只说明**扫描没扫到头**，
    不说明控制器赢了（见 docs/finding_a100_controller_20260925.md）。
    """
    return piecewise(wall, front)


def upper_left(points):
    """上-左包络，按 x 升序：只保留 y 创新高的点。

    与 frontier.py 的 FRONT 构造同义。**元素可以是 (x, y) 或 (x, y, name)** ——
    只读前两个分量、原样保留了其余（`gen_elasticity_x` 用的是二元组，
    它原来自己写了一份一模一样的包络，2026-09-26 codex 第 30 轮抓到）。
    """
    pts = sorted(points)
    env, best = [], float("-inf")
    for p in pts:
        if p[1] > best:
            env.append(p)
            best = p[1]
    return env
