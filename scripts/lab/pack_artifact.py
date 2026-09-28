#!/usr/bin/env python3
"""把 Artifact Evaluation 要交付的东西**组装到一个目录**（再打成 tar.gz）。

## 设计判据（每一条都对应一个前面的实测）

1. **只收复现真正需要的文件** —— `results/night` 是 749MB，但复现只读 7 种文件
   （`steps.jsonl` / `summary.json` / `metadata.json` / `metrics.csv` /
   `controller.jsonl` / `admissions.jsonl` / `gpu_watch.jsonl`）⇒ **416MB**。
   `runner.out`（400MB）与 `ctrl.out` 一个字节都不需要。
2. **目录结构照仓库**（`scripts/lab/`、`paper/data/`、`data/`、`results/night/`）——
   这样 `regen_all.sh` 一行不用改就能跑。
3. **不收 `paper/*.tex` 的正文**？**要收** —— `check_paper_numbers.py` 要读它们，
   而且「论文里每个数都能追到」这条判据依赖正文本身。
4. **写一份 MANIFEST**（每个文件的 sha256 + 字节数），让审稿人能验完整性。
5. ⚠ **只读仓库**：产物写到 OUT，从不写回。
"""
import hashlib
import json
import os
import shutil
import sys

REPO = "/root/paper/foyer"
OUT = "/tmp/ae_artifact/foyer-artifact"

# results 里复现真正会读的文件（其余如 runner.out / ctrl.out 不收）
NEEDED = {"steps.jsonl", "summary.json", "metadata.json", "metrics.csv",
          "controller.jsonl", "admissions.jsonl", "gpu_watch.jsonl"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def copy_tree(src, dst, keep=None, skip=None):
    n = 0
    for dp, dns, fns in os.walk(src):
        rel = os.path.relpath(dp, src)
        if "__pycache__" in rel.split(os.sep):
            continue                      # ⚠ 按**目录名**排除（skip 只比文件名 ⇒ 从来没生效）
        for f in fns:
            if keep and f not in keep:
                continue
            if f.endswith(".pyc"):
                continue
            if skip and f in skip:
                continue
            s = os.path.join(dp, f)
            d = os.path.join(dst, rel, f)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    return n


def main():
    # ⚠⚠ 2026-09-27（收尾时被这条咬了两次 + r61 复核补两条）：
    # **(a) 顺序**：`build_supplement.py` 直接写 `paper/`，所以「验证生成器可复现」
    #     这个动作**本身**就会把 `.tex` 写得比 `.pdf` 新 ⇒ artifact 立刻多一条 MISS。
    # **(b) `pdf` 不存在时整条闸门被跳过、还照印「pdf 不旧于 tex ✓」** ——
    #     一句与实际相反的肯定句（r61 复核构造）。而**整条链上「supplement.pdf 丢了」
    #     本来是零守卫**（检查器也不响）。
    # ⇒ 判据：**`pdf` 必须存在且不旧于 `tex`**，否则拒绝打包。
    # ⚠⚠⚠ 2026-09-27（r62 中立复核）：**判据又窄了。** 上面只查了「存在」与 mtime，
    # 而复核者构造出四种照样印 ✓ 的形状：**`tex` 缺失**（✓ 在 if 外面）、
    # **`pdf` 是目录**、**`pdf` 是 0 字节**、**`pdf` 是指向 `tex` 的符号链接**（mtime 相等）。
    # 最重的是 **0 字节**：`gs` 之外的整条链——连检查器——都放行（检查器也只查 exists+mtime）
    # ⇒ **一个空 PDF 可以全程绿灯交付**。
    # ⇒ 判据：**两边都要是「非空的常规文件」**，且 pdf 不旧于 tex。
    _t = os.path.join(REPO, "paper", "supplement.tex")
    _p = os.path.join(REPO, "paper", "supplement.pdf")
    _bad = []
    if not (os.path.isfile(_t) and os.path.getsize(_t) > 0):
        _bad.append("supplement.tex 不是非空常规文件")
    if not (os.path.isfile(_p) and os.path.getsize(_p) > 0):
        _bad.append("supplement.pdf 不是非空常规文件")
    elif os.path.islink(_p) and os.path.realpath(_p) == os.path.realpath(_t):
        _bad.append("supplement.pdf 是指向 supplement.tex 的符号链接")
    elif os.path.getmtime(_p) < os.path.getmtime(_t):
        _bad.append("supplement.pdf 比 supplement.tex 旧")
    if _bad:
        print("!! 不能打包：%s" % "；".join(_bad))
        print("   先在 paper/ 里跑两遍 pdflatex 再打包。")
        return 3
    print("  supplement 次序   两边都是非空常规文件，且 pdf 不旧于 tex ✓")
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    manifest = {}
    tot = 0

    # 1. 脚本（AE 要能读、能跑）
    n = copy_tree(os.path.join(REPO, "scripts"), os.path.join(OUT, "scripts"),
                  skip={"__pycache__"})
    print("  scripts/          %4d 文件" % n)

    # 2. 论文本体 + supplement（checker 要读；supplement 是投稿件之一）
    # ⚠⚠ 2026-09-27（打包时实测）：**什么都不要排除**。
    # 第一版排除了 `main.aux` / `main.log` / `main.fdb_latexmk`，结果 artifact 里
    # 检查器报 **854 项 / 2 MISS**（仓库里是 860/0）——
    #   ① 「main.log 不存在（没编译过？排版卫兵无从判起）」
    #   ② 「缺 paper/main.log（这条守卫没跑起来）」
    # 排版守卫（Overfull / 页数 / 源码与上次编译一致）**全都要读这些产物**。
    # ⇒ `paper/` 本来就只有几百 KB，**整份收进去**，审稿人拿到就能跑全量检查。
    #   （README 里另说明：`latexmk -pdf main.tex` 可重新生成它们。）
    n = copy_tree(os.path.join(REPO, "paper"), os.path.join(OUT, "paper"),
                  skip={"__pycache__"})
    print("  paper/            %4d 文件" % n)

    # 3. trace
    n = copy_tree(os.path.join(REPO, "data"), os.path.join(OUT, "data"))
    print("  data/             %4d 文件" % n)

    # 4. 原始日志：**只收复现会读的那 7 种**
    n = copy_tree(os.path.join(REPO, "results", "night"),
                  os.path.join(OUT, "results", "night"), keep=NEEDED)
    print("  results/night/    %4d 文件（只收复现会读的 %d 种）" % (n, len(NEEDED)))

    # 5. AE 文档（README / REQUIREMENTS / CLAIMS）—— 它们**必须**在 artifact 根目录，
    #    因为它们引用的是 artifact 里的相对路径。
    import shutil as _sh
    for f in ("README.md", "REQUIREMENTS.md", "CLAIMS.md"):
        src = "/tmp/ae_docs/" + f
        if os.path.exists(src):
            _sh.copy2(src, os.path.join(OUT, f))
    _got = [f for f in ("README.md", "REQUIREMENTS.md", "CLAIMS.md")
            if os.path.exists(os.path.join(OUT, f))]
    if len(_got) != 3:
        print("!! AE 文档不全，只找到 %s —— 拒绝打包（它们在 /tmp/ae_docs/）" % _got)
        return 3
    print("  AE 文档           3 文件（README/REQUIREMENTS/CLAIMS）")


    # 5b. 校验器（与 MANIFEST 一起交付；上面 note 里点名的就是它）
    open(os.path.join(OUT, "verify_manifest.py"), "w", encoding="utf-8").write(
        '''#!/usr/bin/env python3
"""Verify MANIFEST.json against this directory. Exits non-zero on any mismatch.

Checks **both directions**: a listed file whose bytes changed, and a file on disk
that the manifest does not list. (An earlier one-liner in the manifest's `note`
did neither: it printed MISMATCH but exited 0, and only walked the entries.)
"""
import hashlib, json, os, sys

root = os.path.dirname(os.path.abspath(__file__))

def _skip(rel):
    """字节码缓存**不是交付内容**：跑任何一条命令都会让 Python 生成/重写
    `__pycache__/*.pyc`。不排除的话，评审人跑完命令 2 再校验就会看到
    `changed`/`extra`（r67 中立复核实测：`cp -r` 后重写 11 个 .pyc ⇒ rc=1，
    而数据与源码一个字节没动）。"""
    return "__pycache__" in rel.split(os.sep) or rel.endswith(".pyc")
m = json.load(open(os.path.join(root, "MANIFEST.json")))["entries"]
bad = []
for rel, meta in m.items():
    if _skip(rel):
        continue
    p = os.path.join(root, rel)
    try:
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    except FileNotFoundError:
        bad.append((rel, "missing")); continue
    if h != meta["sha256"]:
        bad.append((rel, "changed"))
listed = set(m)
for dp, _, fns in os.walk(root):
    for f in fns:
        rel = os.path.relpath(os.path.join(dp, f), root)
        if _skip(rel):
            continue
        if rel not in listed and rel not in ("MANIFEST.json", "verify_manifest.py"):
            bad.append((rel, "extra"))
print("all %d entries verified" % len(m) if not bad else "MISMATCH: %s" % bad[:8])
sys.exit(1 if bad else 0)
''')
    print("  校验器            verify_manifest.py")

    # 6. 清单
    for dp, _, fns in os.walk(OUT):
        for f in fns:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, OUT)
            if rel == "MANIFEST.json":
                continue
            manifest[rel] = {"sha256": sha(p), "bytes": os.path.getsize(p)}
            tot += os.path.getsize(p)
    # ⚠⚠⚠ 2026-09-27（我自己抓到的）：**第一版只 dump 了汇总，把逐文件 sha256 丢了** ——
    # 而 `note` 里却写着「sha256 per file」。**声称强于产物**，正是这个项目反复栽的那一类，
    # 而这次是在 **AE 交付物**里、给审稿人看的。
    # ⇒ 逐文件哈希必须真的写出去；`note` 里写清楚**怎么用**（给出可直接跑的命令）。
    json.dump({
        "files": len(manifest),
        "bytes": tot,
        # ⚠⚠ 2026-09-27（r62 中立复核）：原来那条命令**报 MISMATCH 但退出码 0** ——
        # 拿它当门禁就是「报了却不算失败」。而且它**只遍历 entries**，
        # **看不见「多出来的文件」**。⇒ 改成 `sys.exit(1)` + 双向检查。
        "note": "Each entry maps a path to its sha256 and byte count. Verify with: "
                "python3 verify_manifest.py   (exits non-zero on any mismatch, "
                "in either direction: a changed file or an extra one)",
        "entries": manifest,
    }, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1, sort_keys=True)
    print("\n  合计 %d 文件 / %.0f MB" % (len(manifest), tot / 1e6))
    print("  产物在 %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
