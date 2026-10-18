# REPORT_noautowrap.md — 关闭引擎自动折行（`wrapW` → ∞）：GR_ZH112 实验盘

> 轮次 round66 · 分支 `main`（未切分支、未 commit） · 2026-10-14
> 用户原话：**「发现折行有问题 能不能取消引擎的自动折行 改为全部按照标签折行」**
> 产物 `work/builds/GR_ZH112/GR_ZH112.iso` sha256 `f9b8347f2eaa848241fd1a453ff80532ed70d2e2c0c7888a2249f22406d4c22c`
> 补丁 `tools/iso_build/patch_zh112_noautowrap.py`（**1 个 ELF 词 = 4 字节**）
> 基底 `work/builds/GR_ZH111/GR_ZH111.iso` sha256 `9413efa7dfe431a1…`（用户报障的那一版）

---

## 0. 一句话结论

| 问题 | 结论 |
|---|---|
| `wrapW` 在哪 | **不在任何数据资源里** —— 是 `RSTextComponent::DoWordWrap @0x21CC10` 每次调用当场算的 `comp[0x40] − comp[0xB4]`（§1，字节级证据）。Lead 线索②里的"语言表 `wrapW` 字段"**不存在**（语言表条目 = `{len}{data}{u16 attr}`；特别收录 XML 更只有 `<text>` 正文）。CSV 的 `wrap_w=270` 是 `tcslib.WRAP_PROFILES` 里的**标定常量**。⇒ 首选路线（纯数据）无落点。 |
| 走了哪条 | 改 ELF **单点换词**（不新建 cave）：`0x21CC90 subu s7,v1,v0 (0062B823)` → `lui s7,0x7FFF (3C177FFF)` ⇒ wrapW = 0x7FFF0000 ≈ 2.1e9 ⇒ **自动折行永不触发**。回退 = 换回原词（`--revert`）。 |
| 效果 | 每个 `{br}`/`{p}` 段恰好 1 行 ⇒ 换行只可能来自盘上的标签。**特别收录 37 条里 218 处"引擎自己多断的行"全部消失**（§3）。 |
| 代价（如实） | 语言表（LANG）2232 条里 **`{WRAP}` = 0 个**：模型口径下 255 条长段 + 75 条短条目共 **1335 处**自动断行会消失。**但本轮实测覆盖到的所有界面（引导/读卡/选档/主菜单/特别收录列表/访谈内页/简报屏）逐像素零变化**（§4）—— 破坏是**模型预测**、**未实拍到**，风险集中在"长且无标记"的文本上。⇒ **GR_ZH112 建议只作实验盘**，见 §7 三个方案。 |

---

## 1. `wrapW` 在哪（逐字节证据）

### 1.1 它是代码里当场算的局部量

`RSTextComponent::DoWordWrap @0x21CC10` 序言（裸 ELF；可复跑
`python tools/diag/dis_ee.py work/builds/GR_ZH112/temp/SLUS_206.13.zh111 21CC10 0x400`）：

```
0021CC84  lw   $v1, 0x40($s5)      ; 0x8EA30040   $s5 = this = RSTextComponent*
0021CC88  lbu  $v0, 0xB4($s5)      ; 0x92A200B4   （u8）
0021CC90  subu $s7, $v1, $v0       ; 0x0062B823   ★ wrapW = comp[0x40] − comp[0xB4]
0021CC94  …                        ; 0x72E08E28   move $s1,$s7 —— 当前行预算 = wrapW
```

* `comp[0x40]` = **该文本组件自己的宽度**（UI 布局量）；`comp[0xB4]` = u8 缩进（本作常见 0）。
* 行容量 = `Σ(字宽+tracking) < wrapW`：15 汉字 = 255 < 270 ≤ 272 = 16 汉字
  （汉字 16 / ASCII 8 / 空格 3 / tracking 1，见 `docs/REPORT_wrap_and_title.md` §1.2）。
* `$s7` 的全部用处（反汇编逐条）：0x21CC90 计算、0x21CC94 `s1=s7`、0x21CD28 硬断闸门
  `slt at,s7,StringWidth(tok)`、0x21CD98 逐字判定、0x21CEB0 新行预算 —— **只喂折行判定，不动几何**。
* 调用面 4 处（`python tools/diag/xref.py 21CC10 --elf …`）：
  `RSHTML::CreateStrings` +0xEC/+0x1C0/+0x2F4（0x21B97C/0x21BA50/0x21BB84）与
  `RSTextComponent::SetText` +0x24（0x21CFE4）⇒ 特别收录/简报（RSHTML）与菜单/对话框（SetText）
  **共用同一个函数**（这也解释了为什么"只对特别收录生效"不能靠"哪个函数调用"来区分）。

### 1.2 为什么"写在语言表里"这条路线不存在（三条独立证据）

1. **LANG（`EN_STRINGS.RES` #25/#902）条目布局没有宽度字段**（`tcslib.parse_lang` 实证口径）：
   `{u32 组数}` → 每组 `{u32 条数}` → 每条 `{u32 len}{data}{u16 attr}` —— 只有长度、正文、2 字节属性。
2. **SFXML（`EN_SPECIAL_FEATURE.XML` #283）根本没有条目结构**（只有 `<text>…</text>`），
   而特别收录介绍框的折行宽度**恰恰是 270** ⇒ 宽度只能来自**组件**。
3. **工具链自己就是这么记的**：`tools/text_csv/tcslib.py` L214-223 `WRAP_PROFILES`：
   `SFXML: wrap_w=270, source='calibrated'（EE RAM frame 11030: comp[0x40]=270）`；
   `LANG: wrap_w=0, source='unknown'（语言表被多种组件消费, 宽度各不同）`。
   ⇒ CSV 的 `wrap_w` 列是 dump 工具的**标定档位**，不是盘上的字段（LANG 那 2232 行全是 0）。

> 附：`docs/PLACEHOLDER_AND_SYMBOLS.md` L83「宽度由语言表 `wrapW` 决定」的措辞应读作
> "语言表文本被**哪个组件**消费，就用那个组件的 `comp[0x40]`"。本轮未改该文件。

### 1.3 为什么不去改 `comp[0x40]`

`comp[0x40/0x44]` 是组件的宽/高：居中、滚动条、裁剪、命中框全用它；改它 = 顺带改整套 UI 几何。
`wrapW` 只喂折行判定 ⇒ 改它**零几何副作用**，且是**单点**（无需 cave、无需 RAM 恒零复核）。

---

## 2. 改动与回退

```
文件内偏移 0x1B0510 = 295*2048 + 0x80 + (0x21CC90 − 0x100000)
0x21CC90 : 0062B823 (subu $s7,$v1,$v0)  →  3C177FFF (lui $s7,0x7FFF)
```

* 补丁脚本自带断言（全部实跑通过）：① 落点原词 `0x0062B823`；
  ② 上下文词 `0x21CC84=8EA30040 / 0x21CC88=92A200B4 / 0x21CC94=72E08E28` 逐词相符；
  ③ 写盘后**全盘逐块回读比对**：差异恰好 4 字节且落在 `0x1B0510`；④ 大小不变（1,648,164,864 B）；
  ⑤ 幂等（已是新词 ⇒ 不写）；⑥ 与源盘同 sha 校验。
* 回退：`python tools/iso_build/patch_zh112_noautowrap.py <zh112.iso> <out.iso> --revert`
* 构筑：`make_build.py GR_ZH112 --from work\builds\GR_ZH111 --patch tools\iso_build\patch_zh112_noautowrap.py --no-font-compact --no-font-dump --no-textdump`
  （`--no-font-compact` 的理由见 §8.1 —— 与补丁无关，是现役 charset/基盘口径问题。）

---

## 3. 实机验证①：折行点全部落在 `{WRAP}`（特别收录）

### 3.1 用户报的"折行有问题"是什么（先量化，模型口径）

对现役盘 58 条特别收录长段逐条跑引擎折行模型（`tools/text_csv/tcslib.wrap_seg`，270）：

| 量 | 值 | 出处 |
|---|---|---|
| `{WRAP}` 标记 | **1705 个 / 58 条**（全部在 SFXML；语言表 0 个） | `temp/wrap_stats.py` |
| 模型判定"引擎会**额外**断行"的位置 | **218 处 / 37 条** | `temp/wrap_diff_analysis.py` |
| 这 218 处的所在行宽 | **全部 > 270**（271–374；16 字 = 272 最多） | `temp/why_extra_wrap.py` |
| 引擎实际第一行 | **恒 255 = 15 汉字**（16 字 = 272 超一行 ⇒ 断在 15 字后） | 同上 |
| 成因分类 | A 类（行宽>270）**218** / B 类（行宽够但被 token 开销挤掉）**0** | 同上 |

⇒ 用户看到的"折行有问题" = **我们自己按 16–22 字排的行，引擎只能放 15 字，于是多断一行**，
常常留下一个"孤字行"。实例（`SFXML:T0067` 开发手记：第一辑，盘上第 17/36/41/50/52/54/63/67/68… 行）
—— 详见 §3.3 的表。

### 3.2 双盘同 nav 同帧对照（实机）

| 项 | GR_ZH111（基线） | GR_ZH112（本补丁） |
|---|---|---|
| 命令 | `nav_hook.py GR_ZH111 --tag hook111` | `nav_hook.py GR_ZH112 --tag hook112` |
| 结果 | ★ 成功到达「开发访谈 1」（345 s） | ★ 成功到达「开发访谈 1」（347 s） |
| 截图 | `work/builds/GR_ZH111/temp/dump_hook111/hook111_page.png` | `work/builds/GR_ZH112/temp/dump_hook112/hook112_page.png` |
| drawlog | `…/dump_hook111/drawlog.txt`（窗 16558–20758） | `…/dump_hook112/drawlog.txt`（窗 16560–20760） |
| 每行文本 | `temp/page_lines_zh111.txt` | `temp/page_lines_AB.txt` |

**逐帧行序列对照**（`temp/cmp_page_lines.py`，取文本框 x=128 的全部绘制行）：

```
帧窗 16558-20760: 两盘共同帧 1798, 行序列相同 1794, 不同 4
```

4 个不同的帧（F17559/17560/18061/18560）差异**不是断行点**，而是**滚动位置整体差 1 行**
（ZH112 顶部多一行「制作人：达伦·丘基图斯」、ZH111 底部多一行）——
因为关掉自动折行后该条目的**总行数从 131 变 111**（20 处多余断行消失），滚动窗口随之偏移。
⇒ 这一屏（该条目首屏）两盘**断行点完全一致**：因为首屏那 17 行本来就都 ≤ 270。

### 3.3 "218 处"的可见性：奖章页对照（首屏即可见）★ 核心证据

`SFXML:T0043`（奖章类第一条「国会最高勋章」）全文只有 **10 个非空硬行**、**整段在一屏内**，
其中 3 行宽 **272 / 306 / 272**（16/18/16 字）⇒ 引擎会多断 3 次、**不用滚动就能看到**。

| 项 | GR_ZH111（自动折行 ON） | GR_ZH112（OFF） |
|---|---|---|
| 命令 | `nav_hook.py GR_ZH111 --tag medal111 --sf-target-idx 4`（324 s） | `nav_hook.py GR_ZH112 --tag medal112 --sf-target-idx 4`（324 s） |
| 页快照 | `…/GR_ZH111/temp/dump_medal111/medal111_pg0_down.png` | `…/GR_ZH112/temp/dump_medal112/medal112_pg0_down.png` |
| 对照图 | **`work/builds/GR_ZH112/temp/fig_medal_AB.png`**（文本框 3× 放大，上=ZH111 / 下=ZH112） | 同左 |
| 行序列 | `temp/page_lines_medal_AB.txt` | 同左 |

**实测行序列**（drawlog 里 x=128 的全部绘制行，两盘各取同一"按下之后"的稳态帧，相差 5 帧）

```
GR_ZH111  F16861 (auto-wrap ON)              GR_ZH112  F16856 (auto-wrap OFF)
  士兵可获得此勋章：                            1. 多次暴露于敌方火力之下。
  1. 多次暴露于敌方火力之下。                     2. 消灭至少30名敌人。
  2. 消灭至少30名敌人。                         最高勋章由总统以国会名义发给获奖者，  ← 盘上 {WRAP} 行原样 (306)
  最高勋章由总统以国会名义发给获   ← 引擎断的      所以又称“国会最高勋章”。
  奖者，                     ← 孤字行 ✗        它被视为对果敢作战的最高奖励。
  所以又称“国会最高勋章”。                       用于奖励那些极为突出，且冒着
  它被视为对果敢作战的最高奖励。                   非同寻常的生命危险，足以令获奖者     ← 盘上行原样 (272)
  用于奖励那些极为突出，且冒着                     远超战友的果敢行为。
```

（另在 F15662/F15657 一帧上，ZH111 首行是孤立的 `的` —— 那是第 0 行 272 单位被断成 15+1 的残尾。）

* **两处孤字行（`的` / `奖者，`）在 ZH112 上完全消失**，每一行的断点与盘上的 `{WRAP}` **逐行一致** ✓
  ⇒ 这就是用户要的"只按标签折行"。
* 帧窗 15360–19560 共 1764 帧，两盘**全部**不同（因为 A 侧每屏都多 2 行孤字行 ⇒ 滚动窗口整体位移）；
  逐行内容差异**只**出现在那 3 处超宽行上（`temp/page_lines_medal_AB.txt`）。
* **超宽行的表现 = 溢出（画出来、不裁切、不断开）**：306 单位的行（18 汉字）右端超出 270 宽的
  文本框约 36 单位，落在文本框与右侧图片之间的空隙里（`temp/fig_medal_overflow.png` 4× 放大）；
  更宽的行（如 374 单位 ≈ 68 单位溢出）会直接压到右侧图片上。

### 3.4 访谈页（开发访谈 1）与奖章页的差别说明

* 访谈页（§3.2）首屏那 17 行本来就 ≤ 270 ⇒ 两盘**渲染完全相同**，只有滚动位置差 1 行；
  该条目真正多断的 20 行在第 17/36/41/50/52/54/63/67/68… 行（**在首屏之外**，需继续下滚才看得到）。
* 奖章页（§3.3）3 处超宽行**就在首屏** ⇒ 视觉差异一目了然。
* 两处合起来说明：**218 处多断行是"逐条目、逐行"分布的**，只有"行宽 > 270"的那些才会现形。

---

## 4. 实机验证②：其它界面有没有被搞坏（如实报告）

### 4.1 结论：本轮实测覆盖到的界面**逐像素零变化**

| 覆盖面 | 方法 | 结果 |
|---|---|---|
| 引导/读卡/选档/主菜单/特别收录列表/内页（41 张快照，f500–20500） | `tools/diag/snapdiff_all.py` | 14 张逐像素一致；27 张有差异 —— 差异**全部**落在 **y[385,399] 的底部滚动帮助条**（style 0x52，每帧 x−2 横滚）与片头动画帧（f1000/f1500）⇒ **动效相位差，不是折行/布局回归**（`temp/diff_region.py`、`temp/helpbar_phase.py`） |
| 简报屏（nav_p2，92 张快照 f3300–9500） | `tools/diag/snapdiff_all.py` | **92/92 逐像素一致** |
| 读卡提示框（f500） | sha256 | 两盘**完全相同**（`a87b1c81…`） |
| 访谈内页（f17559–20560） | 行序列对照 | 1794/1798 帧行序列相同（其余 4 帧 = 滚动位置差 1 行） |
| 奖章内页（f15360–19560） | 行序列对照 | 1764/1764 帧不同 —— **这是预期的**：孤字行消失 ⇒ 每屏行序列整体变化（§3.3） |

帮助条的差异实例：`temp/fig_helpbar_f3000.png`、`temp/fig_helpbar_zoom.png`
（同一句「选择你的档案。」，字与字距一致，只是横滚相位差 ~2 px）。
⇒ **菜单/列表/选档/读卡/简报这些界面没有被搞坏**；唯一按设计变化的界面是特别收录内页。

### 4.2 但"语言表长段"这一风险**没有被实拍到**（诚实登记）

* `temp/long_draws.py` 扫两次简报 run 的 drawlog：**≥20 字的被绘串 = 0 个**（两盘都是 0）
  ⇒ 本轮 nav 覆盖的界面里**根本没有显示过**那些长段。
* 语言表长段（255 条，形态 = 「地点：…{br}{br}欢迎来到…」段内无标记，最长 3638 单位 ≈ 214 汉字）
  出现在**任务简报/任务介绍**类界面 —— 本轮 nav（快速任务→简报屏）没有走到显示它们的那一屏。
* 而且 **`wrapW` 是逐组件的**：模型里的 270 只对"特别收录介绍框"标定过；语言表被多种组件消费
  （`tcslib` 明说"宽度各不同，不猜"）。所以"1335 处断行会消失"是**按 270 的估计**：
  更宽的组件少消失一些（例如读卡提示框那种 ~330+ 的框，两盘就没变化），更窄的更多。
* ⇒ **风险结论**：`GR_ZH112` 的破坏面是"**长且无标记**"的文本；本轮**没有实测到破坏**，
  也**没有实测到安全**。要用它当发布盘，必须先把那些界面逐屏抓一遍（或按 §7 方案乙走）。

---

## 5. 排版须知（关掉自动折行之后怎么写）

### 5.1 一行能放多少（特别收录介绍框，实测标定）

| 单位 | 宽度 | 备注 |
|---|---|---|
| 汉字 / 全角标点 | **16 + 1 = 17** | tracking 1/字 |
| ASCII | **8 + 1 = 9** | |
| 半角空格 | **3 + 1 = 4** | |
| 一行容量 | **270 ⇒ 15 个汉字（255）** | 第 16 个汉字 = 272 ⇒ 超宽 |

* **建议每行 ≤ 15 汉字**（= 255）；含 ASCII 时按上表折算；含空格的行还要再留 4/空格的余量。
* 换行写法：`text_edited` 里写 `{WRAP}` / `{Warp}`（大小写不限）或直接敲回车；
  空行 = 敲一个空行；位置非法（行首/行尾/紧邻标记或换行）注入器**拒绝**（`FORMAT.md` §3）。

### 5.2 超宽会怎样：**溢出（画出来），不裁切、不断开**（实拍）

* 实拍：`temp/fig_medal_overflow.png`（4× 放大）+ `temp/fig_medal_AB.png`（3× 放大）。
* 306 单位（18 汉字）的行在 270 宽的文本框里**完整画出来**，右端超出 ~36 单位，
  落在文本框与右侧图片之间的空隙；再宽（如 374 单位）就会压到图片上。
* **不会被裁掉、也不会被引擎断开** —— 这正是"关掉自动折行"的语义：排版责任完全交给文本。
* 副作用提醒：超宽行会**盖住相邻 UI**（本页是右侧图片），过宽的行可能跑出屏幕（画不出来）。

### 5.3 现有 1705 个标记的位置评估

| 项 | 值 |
|---|---|
| 展开 1705 个标记后的硬行总数 | 1999 |
| **超宽行（> 270）** | **218 行 / 37 条**（271–374，最宽 374 ≈ 22 汉字） |
| 最宽的 8 条 | T0068(374) T0048(357) T0069(357) T0063(340) T0067(340) T0054(323) T0065(323) T0043(306) |
| 需要"往前挪"的字数 | 1–7 字（超宽量 17–119 单位；分布见 `temp/fix_plan_218.tsv`） |
| 逐条超宽行数（前几名） | T0069:68 · T0068:39 · T0067:20 · T0065:12 · T0054:8 · T0060:8 |

⇒ **标记位置总体合适**（1781/1999 行 ≤ 270），218 行需要微调。**注意这 218 行与引擎多断的 218 处是同一批** ——
所以"把这 218 行改到 ≤255"与"关掉自动折行"是**两条都能消除同一现象**的路（§7 甲/乙）。

---

## 6. 复现命令

```powershell
$PY = 'C:\ProgramData\anaconda3\python.exe'

# ① 补丁自检 (不写盘) / ② 出盘
& $PY tools\iso_build\patch_zh112_noautowrap.py work\builds\GR_ZH111\GR_ZH111.iso `
      work\builds\GR_ZH112\temp\dryrun.iso --dry-run
& $PY tools\iso_build\make_build.py GR_ZH112 --from work\builds\GR_ZH111 `
      --patch tools\iso_build\patch_zh112_noautowrap.py --no-font-compact --no-font-dump --no-textdump

# ③ 只读分析 (全部在 work/builds/GR_ZH112/temp/)
& $PY work\builds\GR_ZH112\temp\wrap_stats.py        work\builds\GR_ZH112\text
& $PY work\builds\GR_ZH112\temp\line_width_eval.py   work\builds\GR_ZH112\text
& $PY work\builds\GR_ZH112\temp\why_extra_wrap.py    work\builds\GR_ZH112\text
& $PY work\builds\GR_ZH112\temp\wrap_diff_analysis.py work\builds\GR_ZH112\text
& $PY work\builds\GR_ZH112\temp\fix_plan_218.py      work\builds\GR_ZH112\text
& $PY work\builds\GR_ZH112\temp\sfxml_profile.py     work\builds\GR_ZH112\text

# ④ 实机 (单实例! 下一条必须等上一条退出)
& $PY tools\capture\nav_hook.py GR_ZH112 --tag hook112
& $PY tools\capture\nav_hook.py GR_ZH111 --tag hook111
& $PY tools\capture\nav_hook.py GR_ZH112 --tag medal112 --sf-target-idx 4
& $PY tools\capture\nav_hook.py GR_ZH111 --tag medal111 --sf-target-idx 4
& $PY tools\capture\run_opt.py brief112 tools\capture\nav_p2.txt 9500 100 3300 9500   # GR_ISO=…ZH112
& $PY tools\capture\run_opt.py brief111 tools\capture\nav_p2.txt 9500 100 3300 9500   # GR_ISO=…ZH111

# ⑤ 对照分析
& $PY tools\diag\snapdiff_all.py work\builds\GR_ZH111\temp\dump_hook111 work\builds\GR_ZH112\temp\dump_hook112 12
& $PY work\builds\GR_ZH112\temp\diff_region.py   work\builds\GR_ZH111\temp\dump_hook111 work\builds\GR_ZH112\temp\dump_hook112 3000 4000 8500
& $PY work\builds\GR_ZH112\temp\cmp_page_lines.py work\builds\GR_ZH111\temp\dump_hook111\drawlog.txt `
      work\builds\GR_ZH112\temp\dump_hook112\drawlog.txt --frames 16558-20760
```

---

## 7. 结论与建议（三个方案）

| 方案 | 做什么 | 代价/风险 | 适用 |
|---|---|---|---|
| **甲（本轮已实现）** | 关掉引擎自动折行（1 词 / 4 字节） | 语言表"长且无标记"的文本失去折行（模型 1335 处）；本轮**未实拍到破坏**（覆盖到的界面 92/92 + 41 张快照零变化），但也未证安全；补标签需要**逐屏标定组件宽度**（`LANG` 宽度未标定） | 用户坚持"全游戏只按标签折行" |
| **乙（推荐，零 ELF）** | **不动引擎**：把 §5.3 那 218 行改到 ≤255（15 汉字），引擎就**不再多断** | 纯文本改动：218 行各挪 1–7 字（需按"段"整体重排，不能逐行截断）；改完特别收录 100% 跟 `{WRAP}` 走，语言表/简报**零影响**；代价 = 以后每行都得 ≤255，否则引擎又会多断 | 只想解决"折行有问题"、不想动引擎 |
| **丙** | 只对特别收录关自动折行（小 cave：`comp[0x40]==270` 或 `ra∈RSHTML::CreateStrings` 时用大 wrapW） | 需要先把"简报面板/其它 RSHTML 组件多宽、走哪条路"逐屏钉死（本轮未做，故**未实现**）；落点可用 `0x417220–0x4174FF`（V 系洞穴簇），但按 ZH58 纪律仍需多帧 RAM 恒零复核 | 只想改特别收录、且要保留语言表行为 |

**甲/乙的实测对比（奖章页 §3.3，同一屏）**

| | 结果 |
|---|---|
| 甲（ZH112，本轮） | 孤字行消失，行 = 盘上 `{WRAP}` 逐行一致；超宽行溢出到框外（不裁切） |
| 乙（未实跑，按 §3.1 的引擎规则推断） | 把 3 处超宽行改到 ≤255 后，引擎**不会**再断 ⇒ 同样是"行 = 标记"，且**没有任何溢出**；语言表不受影响 |

> **给用户的一句话**：你要的"只按标签折行"已经做出来了（GR_ZH112，1 个词就能开/关），
> 特别收录页 218 处"引擎自己多断的行"确实没了（奖章页实拍：`fig_medal_AB.png`）；
> 但**语言表 2232 条里一个标签都没有** —— 那些长段落（任务简报等）以后就没人替你折行了。
> 所以要么接受方案甲 + 给语言表补 `{WRAP}`，要么走方案乙：只把那 218 行改短，
> 引擎自然不再多断（等于用文本达到同样效果，且不碰引擎）。

---

## 8. 备注与已知情况（诚实清单）

1. **`--no-font-compact`**：现役 `charset_compiled_zh16.json` 记录的"上次写盘"是 `d2a93316…`，
   与 `GR_ZH111`(`9413efa7…`)/`GR_ZH112`(`f9b8347f…`) 都不符 ⇒ 字库紧凑重排以
   `CompactError: 329/1504 个在用字在 charset 指的槽位上是空的` 拒绝执行。
   **实测未打补丁的 `GR_ZH111` 报同一句话**（`temp/check_font_compact.py`）⇒ 与本次补丁无关，
   是**基盘/charset 口径的历史状态**。⚠ 这意味着**现在任何一次默认构筑都会在字库步中止**，建议 Lead 处置。
2. **实机撞车（环境问题，非盘侧）**：第一轮 `nav_hook GR_ZH112`（9:43 起）在 F12738 被
   `Stop-Process -Force` 杀掉（rc=0xFFFFFFFF = .NET `Process.Kill` 特征码），同时工作区里出现了
   并发的 `GR_ZH113`（9:42/9:46）与 `GR_ZH98/temp/r67|r68|r69`（9:49-9:50）—— 不是本轮产物。
   本轮随后的抓帧全部**串行化**（脚本先等前一实例退出再起），重跑成功。
3. 本轮**未改**：任何历史 ISO、`work/builds/GR_ZH111/text/`、`tools/text_csv/tcslib.py`、
   `tools/text_csv/inject_text_csv.py`；未 commit、未切分支。
4. `GR_ZH112` 的 `text/` 快照里 `text_edited` 是**展开后的换行**（本轮没走 `--inject-csv` 的 carry），
   编辑面请继续用 `GR_ZH111/text/`（或带 `--inject-csv` 构筑）。两版**盘上文本逐字节相同**
   （`text_zh` 58/58 相同 + 全盘只差 4 字节）。
5. 分析脚本全部在 `work/builds/GR_ZH112/temp/`（只读 CSV/drawlog，不写盘内数据）；
   对照图在 `work/builds/GR_ZH112/temp/fig_*.png`。
