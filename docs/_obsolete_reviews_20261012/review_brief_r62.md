# 审查范围：**r61 处置之后**的验证（只审这一批）

## 背景
论文投 RTAS 2027（技术正文硬限 11 页，已达标）。**本轮验证 r61 处置本身有没有引入新错。**
本项目历史：**每轮处置都会引入新改动，而每轮复核都抓到过真错（最近十一轮全中）。**
**最近四轮的错误形态是同一种：判据的作用域比它声称的窄。**

## 当前实测（请自行复算，别采信）
```
仓库：861 项检查 / 0 MISS / 0 个 !!   常规 与 python -O 相同；NORE=1 = 263
      13 页（技术正文 11 页，REFERENCES 起于 p11）/ ?? 0 / Overfull 0
supplement：14 页 / 0 Overfull / 0 字面 markdown
AE artifact：/tmp/ae_artifact/foyer-artifact/（1460 文件 / 424 MB / tar.gz 54 MB）
      regen 48/48 rc=0 ｜ checker 861/0 ｜ 五条独立线 rc=0 ｜ 1460 条哈希全过
```

## 这批改了什么（逐条核）
1. **supplement 两处可见缺陷**：markdown 的 `**three**` 字面进了 PDF；`…admissions.jsonl) and Two of them…` 的断句 splice。**都改了。**
2. **正文 §V 的承诺改了**：`per-cycle readings` → `per-run readings`（因为 `projection.csv` 是每 run 一行）；
   守卫关键词同步（`per cycle` → `occupancy projection`）。
3. **AE README**：写死的 "860 assertions" → 不写死；`168→183/52→54/57→59` → `168→182/52→53/57→58`；
   「每个脚本只用标准库」→「复现路径上的一切只用标准库」。
4. **打包闸门**：改成「`pdf` 必须**存在**且不旧于 `tex`」（原来 PDF 缺失时跳过、还印「✓」）；
   **闸门挪到 `rmtree(OUT)` 之前**（原来被拒绝时已经删掉了上一次的产物）。
5. **`build_claims_doc.py` 的死变量**：标题与说明段建在 `out` 里从不打印 ⇒ 交付的 `CLAIMS.md` 没标题。已修。

## 请核
1. 这批有没有让某个主张**变强或变弱**？⚠ 特别是**正文 §V 那句改动**（`per-cycle`→`per-run`）是否与 supplement 实际提供的一致。
2. **supplement 的 PDF 里还有没有别的排版/记号问题** ——
   ⚠ **`pdftotext` 全文过一遍**（字面 markdown 记号 `**`/`|`/`#`、断句 splice、重复词、`??`、未解析引用）。
   ⚠ 上一轮的两处就是**这么漏掉的**，所以这是本轮最该被打的地方。
3. **打包闸门三条**：PDF 缺失 ⇒ 拒绝；PDF 旧于 tex ⇒ 拒绝；正常 ⇒ 通过。
   ⚠ 还有没有第四种形状（目录、符号链接、空文件）？
4. **`build_claims_doc.py`**：重跑与交付的 `CLAIMS.md` **逐字节相同**吗？内容与 `regen_all.sh` 的 `run` 行一致吗？
5. **`MANIFEST.json`**：改一个字节 ⇒ 报？删一个文件 ⇒ 报？条目集合与磁盘逐条相等吗？
6. **`build_supplement.py`**：重跑与交付的 `supplement.tex` 逐字节相同？只写一个文件？
   ⚠ 它把 `/root/paper/foyer` 写死在 `D`/`PAPER`/`results` 三处 —— **在别的机器上会静默产出没有数据表的 supplement**，
   而 README **没有**让审稿人跑它。这个边界够不够（请judge）？
7. **AE artifact 独立可用**：三条命令 + 哈希校验 + `CLAIMS` 可复现。
8. **反向问**：这批有没有引入**新的假通过通道**？
   ⚠ **「没有别的假通过通道」这句不许下结论**。**继承这条克制。**

## 硬约束
- **只读**。扰动只在 `/tmp`，写入前断言 `realpath` 以沙箱路径开头。
  ⚠ **bash 的 `ln`/`cp`/`mv`/`rm`/`>` 与 Python 写入同等对待**（本项目已因此出过三次事故）。
- **不要改仓库里任何文件，也不要留下任何副作用**（上一轮有位复核者报告它在收尾时造成了一个 mtime 副作用）。
- 从仓库根目录跑检查器；`results/` 用符号链接别拷。

## 报告格式
逐条 1–8：结论 + 复算值 + 出处。最后单列「**我核不动/核不了的**」。**不许猜，不许为了显得严格而编造弱点。**
