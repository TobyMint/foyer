# 第 36 轮处置（codex r36 + 独立复核子 agent 第 20 轮）

范围：AIMD 停摆那一段的改正，以及 r35 那一批的守卫。**两条线都报了实质问题，都已处置。**

---

## 一、独立复核子 agent：**两条 major，都是「派生量没人管」的又一次**

### M1｜「twelve clean runs」实际是 **13**，而且守卫**假通过**

§VI 与表 I 表注都写「23.7--27.5 ms across the **twelve** clean runs of the same
controller family」。复核者按**那句话自带的定义**（Foyer 家族 + host-tier +
未被 flag）复算：集合是 **14** 条、区间 23.659--27.541 —— 也就是**区间是从这批 run
算出来的，条数却少写了**。

⚠ **守卫为什么没响**：原来三条都用 `ck()`（全局字符串查），于是
`ck(..., 14, ...)` 被同文件的 `Fourteen of our runs` 接住了
（`has()` 会把数字与英文词互相匹配）—— **打印出来的值贴着正文的 twelve，
却没有任何东西比对。**

已做：按正文自带的口径（**跑满 999 步**）现算 = **13 条**，两处正文改 thirteen，
三条守卫改成 `ck_near` 锚在「clean runs of the same controller family」上。
（区间不受影响：13 条与 14 条是同一个区间，被排除的只有未跑满的 `rg4`。）

### M2｜「Twelve further runs … are not listed」实际是 **17**

表 I 表注枚举了 6（budget/rate-limit）+ 2（matched pair）+ 4（被替代）= 12，
而按那句话的口径（本机 + 本 trace + 跑完 + 不在表 I）现算是 **17** ——
漏掉的是**容量控制那一组**：`cap2_hp` / `cap3_hp` / `cap4_hp`（半池）、
`cap3_p75`（0.75 池）、`cap1_r2`（cap1 的干净重跑）。

守卫同样**假通过**：它算出的 29 被同文件的 `29.3\%` / `29.2` / `29.5` 接住。
已改成按正文口径现算（17）并锚在「further runs on this trace completed」上，
正文补上第五组。

> **M1 与 M2 是同一个形状**：**守卫用全局字符串查「这个数在不在」，
> 而那个数在别处（尤其是一个以它开头的百分数）必然出现。**
> 本项目记过「同一个数在别处出现 ≠ 它用在了这里」——这次是**守卫自己**犯的。

---

## 二、codex r36：**四条新守卫的假通过**（都是真的，都已堵）

| 构造 | 原判据为什么放过 |
|---|---|
| `A re-run is queued`（句首大写） | 禁词表按小写比对，小写拦得住、大写绕过 |
| `has("14 runs", 4) == True` | 整数走**无边界子串**查 —— 「4 of 11」写成「14 of 11」照样过（小数那一支早有 `(?![\d])`，整数这一支一直是裸的） |
| `% \caption{Two bars are hatched.}`（注释里放正确的数、真 caption 写错的数） | caption 解析**不剥 TeX 注释** |
| `Thirty\,two` / `at the time of\nwriting` | 数词与短语正则用字面空格，间距命令与硬换行都能绕开 |

已做：
- 禁词表**不区分大小写**，「逐句列出 queued」**每次都打印**（原来只在 `-v` 下打，
  而那是这条守卫的全部价值）；
- `has()` 的整数加**左边界** `(?<![\d.,])`，并补上**反方向**（传英文词也试阿拉伯数字）。
  ⚠ 加完之后**全量重跑仍是 0 MISS** —— 说明没有哪条检查是靠这个漏洞在过；
- caption 解析**先剥未转义的 `%` 注释**；`\,` `\;` `~` 等等距命令剥成空，
  数词表连**去连字符**的写法一起认；
- 时点词正则的词间改 `\s+`。

---

## 三、其余 minor（均已处置）

| # | 问题 | 处置 |
|---|---|---|
| m1 | 第一次尝试的 `INTERVENTION.md` **自相矛盾**（「reaper 杀掉了控制器**和它的监督 bash 循环**」vs 同文「aimd2 路由没有监督循环」） | 追加**更正段**：后半对、前半错（那个循环**从来不存在**）；并写明「`ctrl.out` 为空」当时为真、现在是假（那行是五小时后写的） |
| m2 | 重跑那份 INTERVENTION 说控制器哈希「与上次相同」 | 实为 51602440d103 vs **8e995d1f6633**。已更正：**两次不是同一份控制器代码**，同一个失效却都出现 ⇒ 指向启动路径而非控制器 |
| m3/m4 | `aimd_stall.csv` 的两列含义含混、且第 1 行 `queued_never_admitted=0` 与正文的「24」并排会被误读 | 拆成 **`queued_at_log_gap`（第 1 次 = 24，正文引的）/ `queued_at_last_cycle`（第 2 次 = 2，正文引的）**；另加 `admit_gap_min`（第 1 次 31.9 → 正文的「32 minutes」）—— 它与日志中断（31.4）**不是同一个量**，两个都印 |
| m5 | 正文没有点名 `aimd_stall.csv` | §V 已加指针，两个新数各加一条守卫（反向测试都报 MISS） |
| m7 | §A100「前七个十分位内相差 4 s 以内」依赖分位定义 | 正文补「taking the upper of the two middle values」 |
| m8 | §VI「Fourteen of our runs are … killed four runs outright … we report none of the four」读起来互斥 | 改成「two of them are counted above and two are on the moving-load trace---and none of the four appears in our tables」 |

## 四、复核者独立复算并确认【对】的

§V 新句的三件事（控制器末条 13:15:37、`release` 与最后一步同毫秒、989 行、
恰好 2 条 queued 未 admit）；**根因判断**（且给的两条独立证据比作者引的那条更硬：
`controller_aimd2.py` 里自己写着 "no supervisor (unlike budget3)"；第一次的
`ctrl.out` 有监督循环的回声而 r2 的 `ctrl.out` 0 字节）；
`aimd_stall.csv` 16 个字段逐位；第一次的 32/28/24 三个数；
不放行窗口的 11/4/3/4；A100 的 88.6/88.3/4 s；33.3 ms 的归属；
「flagged window 是 run 的 31%–50%」。

⚠ 复核者同时指出一条**我们无法再核**的：r2 的「控制器进程 exited（僵尸）」
只有当时现场的 `ps` 记录作证，现在无法复算 —— 日志能证的只是「13:15:37 之后
不再写任何周期」。**这一处正文写的是「exited mid-run and never came back」，
是照现场记录写的**；若要求更保守，可改成「stopped logging and never resumed」。
（保留现写法，理由是 `controller.jsonl` 之后**一行都没有**、且 `ctrl.out` 无输出，
与「退出」一致；但这条已在此写明其证据等级。）

## 四·补、**「completed」这个词对那 17 条里的两条是假的**（我自己扫出来的）

改完 M2 之后核了一遍那 17 条到底有没有跑完：

| run | 尝试步数 | 失败步 |
|---|---|---|
| `cap3_hp` | **807** | 50 |
| `cap4_hp` | **549** | 116 |
| 其余 15 条 | 995--999 | 0--2 |

`cap3_hp` 与 `cap4_hp` 是那两条 **OOM fault**（`runner_rc=0` 但被中途放弃、
连 `runner.out` 都没有）—— **「Seventeen further runs … completed」对它们不成立**，
而正文别处自己分得很清（「Two runs stopped short of 999 … and both finished」）。

已改成「Seventeen further runs on this trace **are not listed**」，
并在半池那一组里点名「the last two stopped early, at 807 and 549 of the 999 steps」，
加一条守卫查**整串**「at 807 and 549 of the」（只查 807 会假 MISS —— 它后面跟的是 and）。

## 五、状态

**29 页**、0 Float/Overfull、0 悬空引用、**652 项检查 0 MISS**、**45 张表逐位可重生成**。
