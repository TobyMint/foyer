# 审查范围：**r51 处置之后**的验证（只审这一批处置）

## 背景

r51 双审查（中立 + codex）报了 8 类问题，已全部处置（约 35 处改动）。
**本轮的任务是验证这批处置本身有没有引入新错** —— 本项目的历史是：**每一轮处置都会引入新改动，而每一轮复核都抓到过真错。**

当前：**850 项检查 / 0 MISS / 正文 11 页 / `??` 0 / Overfull 0 / 摘要 265 词**。

## 这批处置改了什么（**逐条都要核**）

### A. 头条退回运行层面（codex 的核心意见）

codex 裁定：**不应**把 `scan` 臂判成「没效果/纯噪声」；证据支持的是
「**有正向读数、臂级越线未确证**」。理由是就绪时钟下三次为 **−0.56 / +0.96 / −1.07**。
- 摘要：`the release rule crosses there` → `both crossings are the release rule's, not the admission decision's`
- `sec_results.tex`：`the release rule beats the envelope` → `the readings above the line are the release rule's`
- 另清了三处同义漏改

**核**：这条新表述**是不是两个方向都不过头**？有没有**新的**说过头（往任一边）？
三处同义处还有没有漏的？

### B. 两处被第三次读数弄假的话

- `sec_discussion.tex:75`：`falling inside the band here` → `falling outside it on one of its three runs`
- `sec_results.tex:35-37`：`more than that band` → `more than the band's $1.0$\,pp half-width and straddling its edge`
  （codex 指出：±1.0 pp 的**半宽** 1.0、**全宽** 2.0；**1.87 超过半宽、小于全宽**）

**核**：两处改对了吗？半宽/全宽的表述**在别处还有没有混用**？

### C. 三条守卫的复活与修复（本项目重犯的坑）

- **C1** 图 2 图注 `thirty-seven` → **`thirty-nine`**（`decomp.csv` 39 行）
- **C2** 检查器里那条守卫**本来就在**，被退役键 `"图2 图注：*"`（**前缀匹配**）吞掉了。
  处置是**把前缀键拆成 4 条精确键**，守卫复活。
- **C3** 修一条**假通过**：图注 `36.3\% for the slowest` 的守卫靠 `ck_near` 的 `window=260`
  命中了同句 52 字符外的 `41.9`。处置是**改锚**（值与配置绑成复合串），并补了区间两端的守卫。

**核**：C2 拆键之后**有没有别的检查被误放出来或误关掉**（跑 `NORE=1` 对拍）？
C3 的新锚**真的绑住了吗**（构造：把 `36.3` 改成 `41.9`，应报 MISS）？

### D. 驱逐对照的披露（第二重要）

`hc_slru` 与两条 lru 对照在 **harness 代、控制器代、卡**三项都不同；且
**`foyer_hc_r2` 的 `gpu_watch` 晚起 283 分钟、覆盖 2.4%**，**`foyer_hc` 根本没有 watcher**。
正文改成：
> `one slru run reads 80.5% against 80.6% for two runs of SGLang's default and 80.87% planned, though that run is on the other card under a later launcher`

**核**：这个披露**够不够**？有没有哪个方向说得比证据强或弱？
`lane_evict_slru.sh` 头部的差异表与 `claims_audit.md` 的 C9 是否与 metadata 逐字段相符？

### E. 一个数从 22 改成 23

`sec_results.tex:133` 的 `Twenty-two further runs` → **`Twenty-three`**。
理由：本地镜像缺 `results/night/pois200_slice23_hc/`（空目录），rsync 补齐后两台机一致 = 23。

**核**：23 对吗？核 `slice23_hc` 是否真的**不在任何表里**（按正文「in no table of ours」的口径它该被数进去）。

### F/G. 文档与判带

- `claims_audit.md` 的 C4（原来停在两轮之前）、C9 已更新
- 判带阈值**不动**；`sec_intro` 改成 `we claim no gain beyond the band \emph{here}---a gain inside it is not excluded---`；
  §II 补 `, not a calibrated confidence bound`
- ⚠ 结论里**不能**写 `reads above it`（hz2 的 +0.22 是**线之上、带之内**）

**核**：F/G 的措辞对不对？特别是**「线之上、带之内」这个区分**在别处有没有被写错？

## 请做的

**逐条独立复核**，给「成立 / 不成立 + 你的复算值 + 出处」。**不要采信我的说法。**

1. A–G 逐条核（上面每一项）。
2. **这批处置有没有引入新错**（反向问）：新增的表述、新拆的退役键、新加的守卫，
   有没有哪一处**让某个主张变强或变弱**？
3. **为守住 11 页删掉的 ~30 词重复文本**：核它删的**真的是重复**（在别处另有同义句），
   不是**唯一出处**。
4. **仍然 11 页吗**：`pdfinfo` + `pdftotext -f N -l N main.pdf - | grep -c "R EFERENCES"` 逐页判。
5. **`??` = 0、0 Overfull、0 Float too large、摘要 ≤265**。

## 硬约束

- **只读**。扰动在 `/tmp` 沙箱，写入前断言 `os.path.realpath(p)` 以沙箱路径开头。
- **不要用 `git checkout`**（工作区就是最新版本，全未提交）。
- 实验机 `ssh lab-3090` 可用。
- 不要重审全稿、不要提篇幅目标、不要编造文献。
- 报告格式：逐条「结论 + 复算值 + 出处」。确证无误的也写一行。
- 最后单列「**我核不动/核不了的**」，写清为什么，不许猜。
