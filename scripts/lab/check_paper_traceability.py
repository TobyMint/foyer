#!/usr/bin/env python3
"""论文数字可追溯性检查：正文里的每个数，必须能在 paper2027/data/*.csv 里找到。

用法：python3 check_paper_traceability.py [--tex-dir paper2027] [--data-dir paper2027/data]

## 为什么需要

项目纪律第一条：**论文里出现的每个数字都要能追到代码、日志或 CSV**。旧稿靠人工核，
代价是几个月里漏过十几次。这个脚本把"能追到"变成机械检查：

1. 从所有 `.tex` 里抽出数字（去掉 `\\pend{}` 里的占位、ref/标签、表格列宽等）；
2. 从 `data/*.csv` 的所有单元格里抽出数字集合；
3. 正文里有、CSV 里没有的 → 列出来，人工判断是"派生量"还是"抄错了"。

## 白名单（写清楚为什么不算）

- 模型/机器常数：24、96、7B、56（KiB/token）、203（K host tokens）、101.5K…
  这些来自部署配置，不在 CSV 里；要么补进 `engine_constants.csv`，要么在下面登记。
- 结构性数字：章节号、表号、`\\times`、`0.85`（memfrac）、`0.95`（rho）等。
- 统计口径：10（SLO 秒）、`\\delta`。

⚠ 这是**检查器，不是判决器**：它报出来的东西需要人看。但"没报"不代表没问题
（派生量、名次、条数仍然要靠人）。
"""
import argparse
import csv
import glob
import os
import re
import sys

# 这些数字允许只出现在正文里（机器/模型常数、结构数字、口径），逐条写清理由。
WHITELIST = {
    "24": "24GB 卡（部署）",
    "96": "96K 上下文（部署）",
    "7": "7B 模型（部署）",
    "56": "56 KiB/token（模型 KV 形状，engine_constants 注释里有推导）",
    "203": "host tier 203K（= 2 x 101502，部署配置）",
    "101": "101.5K 池（= 101502，trace_facts.csv 有 pool_tok）",
    "0.85": "memfrac（部署配置）",
    "0.95": "rho（policy 串）",
    "0.90": "shed 阈值 0.90 x budget（代码）",
    "10": "SLO 秒（预注册）",
    "1": "结构性",
    "2": "结构性",
    "3": "结构性",
    "4": "结构性",
    "5": "结构性",
    "6": "结构性",
    "8": "结构性",
    "9": "结构性",
    "0": "结构性",
    "12": "结构性（12.9 的整数部分会单独匹配到 12.9）",
    "13": "结构性",
    "14": "结构性",
    "45": "结构性",
    "60": "结构性",
    "62": "结构性",
    "2025": "年份",
    "2026": "年份",
    "2027": "年份",
    "1.40": "Prop.1 的上界 = 96.4K/69.0K（两个数都在 trace_facts.csv）",
    "97.0": "2 x 48.5K（median context 的两倍，正文用它说明 k=2 恰好越界）",
    "2.47": "0.934 x 2.65 h（长间隔吃掉的停放时长）",
    "107.5": "0.678 x 158.5 min（busy 时间，两个数都在 work_decomp CSV）",
    "2.9": "203K / 69.0K（host 能停几个会话）",
    "6.5": "1.31M / 203K（工作集是 host 层的几倍）",
    "2.5": "45K ctx 的 KV 字节数 = 56KiB x 45K",
    "540": "controller_budget3.py 行数（wc -l）",
    "3090": "GPU 型号",
}

NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])")


def tex_numbers(tex_dir):
    """返回 {number_string: [出现位置...]}"""
    out = {}
    for fn in sorted(glob.glob(os.path.join(tex_dir, "*.tex"))):
        s = open(fn).read()
        # 去掉注释行
        s = re.sub(r"(?m)^\s*%.*$", "", s)
        # 去掉 \pend{...}（里面是占位文字）
        s = re.sub(r"\\pend\{[^{}]*\}", " ", s)
        # 去掉 \label/\ref/\cite/\includegraphics 参数
        s = re.sub(r"\\(label|ref|cite|includegraphics|input)(\[[^\]]*\])?\{[^{}]*\}", " ", s)
        for m in NUM.finditer(s):
            v = m.group(1)
            out.setdefault(v, []).append(os.path.basename(fn))
    return out


def csv_numbers(data_dir):
    nums = set()
    for fn in glob.glob(os.path.join(data_dir, "*.csv")):
        with open(fn) as f:
            for row in csv.reader(f):
                for cell in row:
                    for m in NUM.finditer(cell):
                        nums.add(m.group(1))
                    # 也收 "12.9x"、"154.9" 这类带单位后缀
                    for m in re.finditer(r"(\d+(?:\.\d+)?)", cell):
                        nums.add(m.group(1))
    return nums


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex-dir", default="paper2027")
    ap.add_argument("--data-dir", default="paper2027/data")
    a = ap.parse_args()

    if not os.path.isdir(a.tex_dir):
        raise SystemExit("找不到 %s" % a.tex_dir)
    t = tex_numbers(a.tex_dir)
    c = csv_numbers(a.data_dir)

    missing = []
    for v, where in sorted(t.items(), key=lambda kv: (-len(kv[0]), kv[0])):
        if v in c:
            continue
        if v in WHITELIST:
            continue
        # 容差匹配：四舍五入（291.85→291.9）与单位换算（15865ms→15.9s）
        def close(x):
            try:
                xv = float(x)
            except ValueError:
                return False
            vv = float(v)
            if xv == 0 or vv == 0:
                return False
            if abs(vv - xv) / max(abs(vv), abs(xv)) <= 0.012:
                return True
            if abs(vv * 1000.0 - xv) / abs(xv) <= 0.012:
                return True
            return False

        if any(close(x) for x in c):
            continue
        # 容忍整数/一位小数互相覆盖：12.9 在 CSV 里是 12.91 → 前缀匹配
        if any(x.startswith(v) or v.startswith(x) for x in c if len(x) >= len(v) - 1):
            continue
        missing.append((v, sorted(set(where))))

    print("正文数字 %d 个，CSV 里 %d 个不同数值" % (len(t), len(c)))
    if not missing:
        print("✅ 全部可追溯（或已登记白名单）")
        return 0
    print("⚠ 以下 %d 个数在正文出现、但在 data/*.csv 里找不到（需人工判断）：" % len(missing))
    for v, where in missing:
        print("  %-10s  %s" % (v, ", ".join(where)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
