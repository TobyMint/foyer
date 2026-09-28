# `breshz1_r2` 落地 + `cap5_hc` 入表（2026-09-25）

这一页记两件事：**(一) 数据与判决怎么变的**，**(二) 我在这一轮里犯了什么错**。
第二件和第一件同等重要 —— 本项目的规矩是「手算的表一定会错」，而这一轮
错的是**我手工传的 run 列表**。

---

## 一、两条 run 落地

### 1. `foyer_breshz1` → `foyer_breshz1_r2`（争用污染重跑）

判据：τ₂ 中位 **33.31 ms**（落在被损害区间 30.9–33.3，与 `bres`/`hz0`/`hz2` 同族），
干净同族值是 23.8–25.7 ms。重跑后 **25.47 ms** ✓ 干净。

| | 旧 `breshz1` | 新 `breshz1_r2` |
|---|---|---|
| 墙钟 | 310.9 分 | **257.0 分**（快 53.9 分）|
| SLO | 72.3% | **77.6%**（+5.3 pp）|
| Δ（混合前沿） | −19.54 | **−8.31** |
| 判决 | BELOW | BELOW |
| `contested` | CONTESTED | **clean** |
| τ₂ 中位 | 33.31 ms | **25.47 ms** |

**判决级**：Δ 改善 11.23 pp，是九条变体里第二大的单次改善（仅次于 `bres` 的 −21.4→−1.33）。

### 2. `cap5_hc` 是**新臂**，加进了表 I

227.6 分 / conc 4.74 / SLO 47.3% / Δ **−32.84** / BELOW / clean。

它是预注册 cap 扫描的一部分（`lane_cap_hc_ext_g2` 脚本早已就位），
补齐了 HiCache 系列的 cap5 —— 此前 HiCache 只有 cap2/cap3/cap4。

### 3. 因此 §IV 的 HiCache 弹性多了一段

`paper/data/elasticity_hc.csv`：

    hicache  pairB_cap2hc → cap3_hc   R̄ 1.25→1.51  τ 27.0→28.0  ε = +0.192
    hicache  cap3_hc      → cap4_hc   R̄ 1.51→1.73  τ 28.0→29.8  ε = +0.458
    hicache  cap4_hc      → cap5_hc   R̄ 1.73→1.75  τ 29.8→30.8  ε = +2.872   ← 新

脚本末行的统计从「HiCache 0/2」变成 **1/3**。正文原来写「over it ε never
approaches one」，**被这一段反驳了**，已改成如实三分段：

- 覆盖控制器操作区间（1.35–1.69）的两段 ε < 0.5；
- 第三段的系数大得多（+2.87），但**它的分母接近零** —— R̄ 只动 0.02（1.73→1.75）
  而步成本动了 1.0 ms；
- 它标出的是**区间之外**的拐点，不是区间之内的。

**这条不是「找借口」**：R̄ 1.73→1.75 是 1.2%，τ 29.8→30.8 是 3.4%，
弹性在这两个数上的比就是 2.87，且它对 τ 的 ±0.5 ms 误差极度敏感。
写清楚「分母接近零」是**披露**，不是辩解 —— 审稿人自己算也会看到。

### 4. 一个里程碑：**四条被污染的臂全部重测完毕**

`bres` / `hz0` / `hz2` / `breshz1` 四条在 2026-09-24 被主机争用损害，
到本轮**全部**有了干净重跑。后果：

- 表 I 表注从「Six rows carried the flag; three still do ... Three of those
  four have since been re-measured; the last one is still out」改成
  **「two still do ... All four have since been re-measured」**；
- `check_paper_numbers.py` 里「受损组（host-tier 的 CONTESTED run）」**集合空了**
  —— 那两条检查没有对象了。已改成**显式打印说明**而不是静默跳过；
- §VI/背景段里「两条臂超过 295 分钟」的讨论**只剩 `foyfix_hc` 一条**，
  「the class has two members and not five」改成 **one member**。

---

## 二、**我这一轮犯的错**（记在这里，因为它最难查）

### 错误 1：我把 `decomp.csv` / `hitrate.csv` 的 run 列表弄小了

`gen_decomp.py` 与 `gen_hitrate.py` 的 run 列表是**命令行传的**，脚本里没有默认值。
我图省事，用了 `eviction.csv` 的 **25 条**（那是「有复用数据」的集合），
而正确列表是 **`default` + `gen_arm_running.py` 的 `ARMS` + `STATIC` = 29 条**。

后果（一度全部写错，已修正）：

| 量 | 我弄错时 | 正确 |
|---|---|---|
| 图 2 的条数 | 25 | **29** |
| 图注 `default` 的 idle 名次 | （来不及算）| **seventh of twenty-nine** |
| `default` 的 duration 名次 | — | **twentieth** |
| §III 的 excess_pct 下界 | 12.9 | **8.4** |
| §III 的 τ₂ 上界 | 31.2 | **39.2** |

**为什么难查**：`gen_decomp.py` 对「列表里不存在的 run」**不报错**
（它只对「名字对不上镜像」的进 `bad` 列表），而**列表本身是我给的** ——
它无从判断我给全了没有。**跑得通、退不出错、表也写出来了**，
只是表比该有的少 4 行。

**正确的做法（已写进 NEXT.md）**：这个列表**从 `gen_arm_running.py` 现读**，
不手写：

    RUNS=$(python3 -c "
    import re
    src = open('scripts/lab/gen_arm_running.py', encoding='utf-8').read()
    def grab(n):
        m = re.search(n + r'\s*=\s*\[(.*?)\]', src, re.S)
        return re.findall(r'\"([^\"]+)\"', m.group(1))
    print(' '.join('pois200_'+r for r in ['default'] + grab('ARMS') + grab('STATIC')))")

### 错误 2：我差点从 label 推断出**错误结论**

`breshz1` 的 label 是 `"horizon$=$1, no hw"`。我看到 `gen_frontier_split.py` 报出
它在 **device-only 前沿**上是 **+6.85（在线上方）**，于是推断「`no hw` = 没有
HiCache → 它与 device-only 静态点**同配置** → **论文的『零条越过』论断被推翻了**」。

**这个推断是错的。** 读 `metadata.json` 才看到：

    "TURNSTILE_HICACHE_ARGS": "--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"

**它开着 HiCache。** `no hw` 里的 `hw` 是 **high-water（水位线阈值）**，不是 hardware。
policy 串是 `budget3:hw=0;target=0.95;horizon=1;base=resident`。

所以它和另外八条一样，对 device-only 前沿是**跨配置**比较 ——
`gen_wall_split.py:28` 的注释早就写着「HiCache 臂只对 HiCache 锚点，
跨配置外推正是 codex 抓到的错」。**论断没被推翻。**

**教训**：`no hw` 这种缩写**不是证据**。本项目的红线里有一条
「从表里抄一个数，抄完回头确认它在原表里是哪一列」—— 这是它的同类：
**认出一个缩写，回头确认它在 metadata 里指什么**。

（顺带：`device-only` 前沿下 9 条臂里有 **6 条「在线上方」**，但那 6 条全是
HiCache 臂，判定无效。真正同配置的只有 device-only 静态点自己的比较。）

---

## 三、`check_paper_numbers.py`：修了 3 个 bug、加了 8 条检查

检查数 **392 → 405**，全部 0 MISS。

### 修的 bug（都是**静默**的那种）

1. **`swap_superseded.py` 的 apply 断言错了第二版。** 第一版写反
   （「改完还得含有旧名」）；我改成 `left == len(run_lines) - n`，它**隐含假设
   「只有 run 类行含旧名」** —— 但注释行也含（`gen_eviction.py:203` 就是）。
   于是「run 类行 + 注释行」的文件必然断言失败；而写入是**逐文件**做的、
   遍历又是 set 的**哈希序**，中止点落在哪儿不确定 →
   **留下任意位置的半改**。第三版按「非 run 类行原本的旧名数」正着写。
   **这一轮它真的触发了**，9 个文件已改、15 个没改。

2. **`has()` 被传列表时 `str()` 掉。** `num_words()` 返回 `[基数, 序数]`
   （`['five','fiveth']`），而 `has()` 第一行是 `s = str(v)` —— 列表被
   str 成 `"['five', 'fiveth']"` 再去做**字面子串**匹配，必然落空。
   后果：**5 条新检查全部假 MISS，而正文其实是对的**。
   **假 MISS 和假通过一样坏 —— 它会让人去改对的数。** `ck_near` 现已展开列表。

3. **`_WORD` 词表只到 30。** `num_words(45)` 返回**空列表** → 检查静默变成
   「什么都不查」。已扩到 60。

### 新加的 8 条（全部是**派生量**）

本项目记过「检查器的系统性盲区是派生量」，这一轮又暴露 6 处：

| 检查 | 值 | 为什么原来漏了 |
|---|---|---|
| §III pooling 的 mean 区间 | 18.9–20.9 | 只查了 n_segments |
| §III pooling 的 >20s 占比区间 | 66.0–70.2 | 同上 |
| §III all_runs 的 mean | 20.89 | 只查了占比 |
| §V gate_attrib 全量集合规模 | forty-five | 集合**规模**，且是英文词 |
| §V 归因：内存没用满的条数 | five | 分组计数 |
| §V 归因：残差条数 | four | 分组计数（`breshz1_r2` 从「τ high」变「residual」）|
| 图2 图注：`default` 的 idle 名次 | seventh | **名次**，集合一变就变 |
| 图2 图注：`default` 的 duration 名次 | twentieth | 同上 |

**已做反向测试**：故意把 `seventh` 改回 `sixth`、`forty-five` 改回 `forty-four`，
两条新检查**都报 MISS**；恢复后回到 0 MISS。**新检查不是假通过。**

---

## 四、这一轮之后的状态

- 正文：**25 页**，0 Overfull，0 undefined，`check_paper_numbers.py` **405 项 0 MISS**
- 判决口径**未变**：混合前沿下九条变体 **零条越线**，两条打平（`hz1` −0.93、`hz2_r2` −0.30）
- 四条被污染的臂**全部**换成干净重跑
- **仍未做**：A100 的判决（`cap1` 还在跑，985/999）、`cap1_r2`、`cap5/6/8_hc` 的其余、
  同卡层级配对 `cap3_pd`/`cap3_ph`、25 档同代对照
- **仍未做**：页数 25→23 与摘要 1045 词的瘦身（**等实验全落地后一次做，一条限定都不许丢**）
