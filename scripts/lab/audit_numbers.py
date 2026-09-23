#!/usr/bin/env python3
"""全篇数字溯源审计：把正文里的数字抽出来，查它是否出现在任何数据文件/原始日志里。

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
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:[,{][,}]?\d{3})*(?:\.\d+)?|\d+\.\d+)(?![\w])")

def norm(tok):
    return tok.replace("{,}", "").replace(",", "").replace("\\,", "")

def load_data_numbers():
    """数据文件里出现过的所有数字（字符串形式，含各种舍入）。"""
    vals = set()
    for p in DATA:
        with open(p) as f:
            for line in f:
                if line.startswith("#"):
                    continue
                for m in NUM.finditer(line):
                    v = norm(m.group(1))
                    try:
                        x = float(v)
                    except ValueError:
                        continue
                    for d in (0, 1, 2):
                        vals.add(round(x, d))
                        vals.add(round(x / 100.0, d))   # 百分比 vs 小数
                        vals.add(round(x * 100.0, d))
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
