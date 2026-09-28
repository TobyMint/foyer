#!/usr/bin/env python3
"""MISS 分诊：把「值不在正文里」的每条 MISS 判成【该退役】还是【该补数】。

## 为什么需要它

结构性删减（整块外移到 supplement）之后，检查器会报出一批 MISS —— 每一条都是
「正文引用过的值，现在找不到了」。本项目的规矩是：**每一条只有两种合法处置**
（见 CLAUDE.md「退役 = 主动把守卫关掉」那一节）：

  (a) 它支撑的**主张也一起删了** ⇒ 诚实退役，且**必须写明「值现在在哪」**
      （写不出「在哪」的条目，默认按「该恢复」处理）；
  (b) 它支撑的**主张还在正文里** ⇒ **必须把数补回去** ——
      否则就是把主张说得比证据强，这是本项目最防的一件事。

**判据是「那句话的锚还在不在正文里」**，不是读一遍凭感觉。

用法（在纸稿仓库根目录）:
    python3 scripts/lab/miss_triage.py            # 只打印分诊表
    python3 scripts/lab/miss_triage.py --nore     # 把退役名单关掉再跑（NORE=1）

⚠ 跑之前必须有一次**干净构建**（`latexmk -outdir=/tmp/build`），否则读的是
别的进程写了一半的 main.log。本脚本会先检查 `paper/main.log` 比 `.tex` 新。
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAPER = os.path.join(ROOT, "paper")


def strip_tex(s):
    """剥注释与命令，用于「这句话还在不在」的关键词匹配（空白归一化）。"""
    s = re.sub(r"(?<!\\)%.*", "", s)
    return re.sub(r"\s+", " ", s)


def main():
    nore = "--nore" in sys.argv
    env = dict(os.environ)
    if nore:
        env["NORE"] = "1"

    # 一次干净构建（独立 outdir，避免与别的进程抢 main.pdf）
    subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode",
                    "-outdir=/tmp/miss_triage_build", "main.tex"],
                   cwd=PAPER, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    r = subprocess.run([sys.executable, "scripts/lab/check_paper_numbers.py"],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr

    # 正文拼一份（空白归一化），用于「锚还在不在」
    body = []
    for f in sorted(os.listdir(PAPER)):
        if f.endswith(".tex"):
            body.append(strip_tex(open(os.path.join(PAPER, f), encoding="utf-8").read()))
    body = " ".join(body)

    miss = [l for l in out.splitlines() if l.strip().startswith("MISS")]
    print("=" * 78)
    print("MISS 分诊%s —— 共 %d 条" % ("（NORE=1，退役名单已关）" if nore else "", len(miss)))
    print("=" * 78)

    retire, restore, unknown = [], [], []
    for l in miss:
        # 锚在 `须在「xxx」附近` 里；没有锚的（如排版卫兵）另算
        m = re.search(r"须在[「『](.+?)[」』]附近", l)
        desc = l.strip()[4:].strip()
        if not m:
            unknown.append((desc, "无锚（排版/结构类）"))
            continue
        anchor = re.sub(r"\s+", " ", m.group(1)).strip()
        # 关键词是空白无关的（与 ck_near 同口径）
        pat = re.compile(r"\s+".join(re.escape(w) for w in anchor.split()))
        n_hit = len(pat.findall(body))
        if n_hit == 0:
            retire.append((desc, anchor))
        elif n_hit > 3:
            # ⚠⚠ **锚不独特 ⇒ 这条分诊不可信。** `spent` / `against` / `horizon}$=2$`
            # 这类常见词在正文里到处都是，锚「还在」并不说明**那句话**还在 ——
            # 我第一版就是按「锚在不在」二分，于是把一大批已经随块外移的检查
            # 报成了「该补数」（最严重的那一类），**这是假警报**。
            # 本项目早有这条：「`ck()` 的短数字会撞上同一文件里的别处」——
            # 这次是**锚**撞上了别处。判据：锚出现 > 3 次就不许自动判，要人工核。
            unknown.append((desc, "锚「%s」出现 %d 次，不独特 ⇒ 需人工核" % (anchor[:40], n_hit)))
        else:
            restore.append((desc, anchor))

    def dump(title, rows, hint):
        print("\n### %s（%d 条）%s" % (title, len(rows), hint))
        for d, a in rows:
            print("   - %s\n       锚：%s" % (d[:100], a[:70]))

    dump("该【退役】—— 锚不在正文里，那句话已随外移删掉",
         retire, "\n    ⇒ 写进 check_paper_numbers.py 的 RETIRED，理由写「值现在在 supplement §Sx」")
    dump("该【补数】—— 锚还在正文里，但值没了 ⇒ 这就是「主张强于证据」",
         restore, "\n    ⇒ ⚠ 必须把数补回正文")
    dump("另类（无锚）", unknown, " ⇒ 排版/结构类，逐条看")
    return 0


if __name__ == "__main__":
    sys.exit(main())
