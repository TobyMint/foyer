#!/usr/bin/env python3
"""全篇数字溯源审计：把正文里的数字抽出来，查它是否出现在任何数据文件/原始日志里。

⚠ 本脚本的能力边界（2026-09-24 记）：
  它只把正文数字与 paper/data/*.csv 做匹配，【不理解派生关系】。所以
  「找不到」只是提示"这个数不在 CSV 里"，不等于"它没有出处" —— 项目纪律允许的
  出处是「代码、日志或 paper/data/*.csv」，从 results/ 原始日志当场算出来的
  派生量（比率、区间、极差）本来就不在 CSV 里。
  真要把它们也消掉，办法是给每一组派生量建生成器（本目录下已经有若干个：
  reuse / reuse_x / hitrate / toolwait / idle_pooled / table1 …），不是放宽本脚本。
  2026-09-24 从 85 处降到 30 余处，绝大多数是【建生成器】消掉的，
  过程中还查出本脚本自己两个 bug：千分位花括号匹配不了、负数不取绝对值。

为什么需要：这个项目反复栽在"数字追不到源头"上 —— 手抄表、从错的列抄数、
用了子集却没写下来。审稿人每一轮都能抓到几个。与其等人抓，不如自己先扫一遍。

用法: python3 audit_numbers.py            # 列出所有"可疑"数字（数据文件里找不到的）
      python3 audit_numbers.py --all      # 连找到的一起列，附出处
"""
import glob, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
TEX = sorted(glob.glob(os.path.join(ROOT, "paper", "*.tex")))
DATA = sorted(glob.glob(os.path.join(ROOT, "paper", "data", "*.csv")))

# 正文里可能是"测量值"的数字：至少两位有效数字、不是年份/页码/引用号
# 千分位有两种写法：LaTeX 的 1{,}849 与纯 CSV 的 1,849。原模式里的
# [,{][,}]?\d{3} 匹配不了 {,} —— `{` 后面是 `,` 不是数字，于是 1{,}849 只被
# 匹配到开头的 1，剩下的 849 又被当成一个独立数字报成"找不到源头"，
# 一口气制造 16 处假阳性（2026-09-24 查出来的）。改成显式二选一。
# 另补一条 \d{4,}：不加它的话【裸写】的大整数（如 1849）反而匹配不上 ——
# 前一条要求有千分位分隔符或小数点。
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:(?:\{,\}|,)\d{3})*(?:\.\d+)?|\d{4,}|\d+\.\d+)(?![\w])")

def norm(tok):
    return tok.replace("{,}", "").replace(",", "").replace("\\,", "")

def load_data_numbers():
    """数据文件里出现过的所有数字（字符串形式，含各种舍入）。

    注意：**必须按 CSV 字段解析，不能用正则扫整行** —— 正则里的千分位逗号
    逻辑会把列分隔符也吃掉（"200,999,260" 被当成一个数），于是行内的真值
    反而进不了集合，审计会满屏假阳性。这个 bug 犯过一次。
    """
    import csv as _csv
    vals = set()

    def add(x):
        # d 必须到 4：CSV 里有 4 位小数的列（reuse.csv 的 reuse_frac/realized_frac
        # 就是 %.4f），而 d 只到 3 时 round(0.6917,3)=0.692 ≠ 0.6917，于是这些
        # 明明在数据文件里的值被报成"找不到"——2026-09-24 发现，当时满屏假阳性。
        for d in (0, 1, 2, 3, 4):
            for y in (x, -x, abs(x)):
                # 绝对值也要加：正文里的 Δ 全是负的，写成 $-7.8$，正则提取出的是
                # 正的 7.8，而数据列里是 -7.8 —— 不加 abs 会让整列 Δ 都被报成
                # "找不到源头"（2026-09-24 审计报了十几个）。
                vals.add(round(y, d))
                vals.add(round(y / 100.0, d))     # 百分比 vs 小数
                vals.add(round(y * 100.0, d))

    for p in DATA:
        with open(p, newline="") as f:
            for row in _csv.reader(l for l in f if not l.startswith("#")):
                for cell in row:
                    cell = cell.strip()
                    if not cell:
                        continue
                    try:
                        add(float(cell))
                        continue
                    except ValueError:
                        pass
                    # 单元格里可能嵌着数字（如 "1.42 to 1.30"）
                    for m in NUM.finditer(cell.replace(",", "")):
                        try:
                            add(float(m.group(1)))
                        except ValueError:
                            pass
    return vals

def main():
    have = load_data_numbers()
    show_all = "--all" in sys.argv
    suspicious = []
    for p in TEX:
        # 去掉注释行和 preamble
        for i, line in enumerate(open(p), 1):
            if line.lstrip().startswith("%"):
                continue
            for m in NUM.finditer(line):
                tok = norm(m.group(1))
                try:
                    x = float(tok)
                except ValueError:
                    continue
                # 明显不是测量值的：年份、小节号、页数、常见常量
                if x in (2.0, 10.0, 24.0, 200.0, 3090.0, 2026.0, 2025.0, 2024.0):
                    continue
                if abs(x - round(x)) < 1e-9 and 1 <= x <= 12:
                    continue          # 小节号/枚举
                if x < 0.05:
                    continue          # 概率/比率一类，多半在表里
                hit = any(abs(x - h) < 1e-6 for h in have)
                if not hit:
                    suspicious.append((os.path.basename(p), i, m.group(1), line.strip()[:96]))
                elif show_all:
                    print("OK   %-18s:%-4d %-10s" % (os.path.basename(p), i, m.group(1)))
    print("\n=== 数据文件里找不到的数字：%d 处 ===" % len(suspicious))
    for f, i, tok, ctx in suspicious:
        print("%-18s:%-4d  %-10s  %s" % (f, i, tok, ctx))

if __name__ == "__main__":
    main()
