# round46 报告：字库紧凑重排（每轮构筑自动做）

> 工具：`tools/iso_build/repack_font.py`（新）
> 接入：`tools/iso_build/make_build.py`（新步骤，默认开启，`--no-font-repack` 可关）
> 配套补丁：`tools/iso_build/patch_zh95_ft_single_glyphs.py`（修 6 个一直画不出来的汉字）
> 版本：`GR_ZH95`（= `GR_ZH94` + 重排 + 整体重编码 + 字形修复），sha256 `c1f5d8498c66de2061346a75d482d5485105250a3a2984e8604a20b7eb5afafb`

---

## 0. 一句话结论（给非程序员）

**以后每一轮打包都会自动把字库"压实"一遍：把在用的字全部挪到最前面、把空出来的地方扫干净。
这一轮压完，字库还能再放 90 个新汉字（上一版只有 42 个位置是干净的、能直接写）。**

再往上压不动了，因为 1504 个字形位里有 **95 个是"死格"**：
其中 51 个被"单字节码"的字形占着（比如 `后/向/装/有/雷` 那一排，还有手柄图标 △ ✕ 的采样窗），
另外 44 个被"单字节码/图标码的采样矩形"压着 —— 这些格子写进去就会和别人的字打架，**永远不能用**。

顺带还查实并修好了一个老毛病：**6 个汉字（若 纤 终 脆 膛 著）从它们被加进来的那一版（GR_ZH93）起，
在游戏里一直是空白的**，本轮把它们的字形补到了引擎真正采样的位置 ——
实机截图已证实：老盘那 6 个位置是空白，新盘全部正常显示。

![六个汉字 实机 before/after](img/r46_ft6_before_after.png)

**重排的安全性也实测过了**：同一导航跑重排前/后两张盘，**297 帧逐像素完全相同**
（含武器详情页的 ▲▼ 滚动箭头、长段中文）。

---

## 1. 本轮交付

| 东西 | 位置 |
|---|---|
| 重排工具（可单跑、可重放） | `tools/iso_build/repack_font.py` |
| 接入构筑管线 | `tools/iso_build/make_build.py`（`--no-font-repack` 关闭；`build_info.json` 多一段 `font_repack`） |
| 字形修复补丁 | `tools/iso_build/patch_zh95_ft_single_glyphs.py` |
| 新版本盘 | `work/builds/GR_ZH95/`（`GR_ZH95.iso` + `text/` + `font/` + `build_info.json` + `temp/`） |
| 重排报告 / 搬运明细 / 日志 | `work/builds/GR_ZH95/temp/font_repack/{repack_report.json, repack_moves.json, repack.log}` |
| 逐帧比对工具 | `tools/diag/cmp_dump.py`（新，实机 A/B 回归用） |
| 占用图（一眼看清空位从哪来） | `docs/img/r46_grid_occupancy.png` |

---

## 2. 引擎口径与「可用格」是怎么数出来的

### 2.1 采样规则（沿用 round45 定稿，本轮没有重新逆向）

* **对偶码**（汉字）：`slot=(lead-0xA1)*94+(trail-0xA1)`；`row=slot//62`；`col=slot%62`；
  **`x=16*col`、`y=2+16*(row+3*[row>=12])`（无相位）** —— `tcslib.atlas_cell_xy_engine_view()`。
* **单字节 / ASCII**：走 `FONT.RES` 的 FT **记录矩形** `(u0,v0,u1,v1)` **本身**当采样窗
  （round45 实机 A/B 已证"记录矩形在哪，字就在哪"）。
* **像素容器是 GIF 封包流**（现役 9 段：8 段 `[PT 16B][A+D TRXPOS 16B][IMAGE tag 16B]` + 数据，
  末段 0 长度收尾）。读写一律走 `tcslib.atlas_container_segments()` 算出的**数据区字节偏移**，
  **不按裸图偏移**、**一个字节的 48B 包头都不碰**。

### 2.2 1504 个字形位分成四类（GR_ZH94 实测）

| 类别 | 数量 | 说明 |
|---|---:|---|
| **可用格** | **1409** | 引擎会采样、又不压着任何"别人的采样窗" |
| 被单字节/图标记录码整格占死 | 51 | `ATLAS_ENGINE_SINGLE_CELLS`：行19 col0..33（`后放置不切命向…` 那一排）、行24 col0..5/12、行21/22 col5..8、行23 col8/9 |
| 被 FT 记录矩形压着（本轮**新查实**） | 44 | 行11 col1..17（码 0xAF..0xC1）、行18 col37..61（码 0xC2..0xDA）、行24 col8/9 —— 这些格以前**没登记**，是自动扫出来的 |
| 合计 | 1504 | 1409 可用 + 95 死格 |

★ 自检：**51 个显式禁用格 100% 落在 544 条 FT 记录矩形内**（`forbidden_not_in_ft_rect = 0`），
说明"显式禁用表"与"自动扫矩形"两套口径互相印证、没有打架。

### 2.3 容量的两个口径（都如实列出，不互相掩盖）

| 口径 | GR_ZH94（重排前） | GR_ZH95（重排后） | 含义 |
|---|---:|---:|---|
| **本工具口径：可用格 − 在用字形** | 1409 − 1319 = **90** | **90** | ★ "以后还能再放多少个新字"的上限 |
| 其中**格是白的、又真能用** | **42** | **90** | 立刻就能写的位置 |
| `dump_font.py` 口径（含"空但不能用"的格） | 50（订正前 34） | 93 | 见 §7.1（本轮订正了一处坐标混用） |
| `dump_font.py` 最严格口径（连别人的采样窗都不碰） | 41（订正前 26） | 88 | 最保守 |

> ★ 口径对照：`dump_font` 的 93 里含 3 个"格是空的、但被记录码/图标占死、永远不能用"的格，
> 所以比本工具的 90 多 3；最严格口径又要避开与全部活字形采样窗的**矩形交叠**，
> 再少 2 个 ⇒ 88。三个数都对，只是问的问题不同。

> 空槽总数两版都是 **185**，但其中 **95 个永远不能用**，所以真正上限是 **90**，不是 185。
> 重排**没有也不可能**变出新的格子 —— 它做的是把"能用的格子"从"被旧墨糊着/散落各处"变成"干净且连成一片"。

![字库格位占用图](img/r46_grid_occupancy.png)

---

## 3. 分配算法（确定性 + 幂等 + 空位最大化）

1. **枚举**：`slot 0..1503` 全部走引擎格位公式，按 §2.2 分成 可用 / 记录码 / 记录矩形 / 越界 四类；
2. **顺序**：在用字形按 **当前槽位升序**（= 图集行主序，天然保持相邻字相邻；同槽按码点）——
   这是唯一的排序键，写死在 `ORDER_KEY = 'current_slot_asc'`；
3. **分配**：第 *i* 个字 → 第 *i* 个可用格（可用格也按槽位升序 = 行主序）。
   这是**单射**，所以"重排后空白的可用格数" = `可用格 − 在用字形` = **理论最大值**，不存在"排得更紧"的余地；
4. **确定性**：同一张盘 + 同一份 charset ⇒ 逐字节同样的结果（本轮连跑两次构筑，产物 sha256 相同）；
5. **幂等**：槽位号本身就是行主序 ⇒ 排完之后"按槽位升序"就是刚才的搬运顺序 ⇒
   再跑一次 = **0 改动**：不写盘、不改 charset、**不产出任何文件**，产物 sha256 不变（§8.2 实测）。

> 为什么不是"保留原位、只填空隙"：那样空位数也一样是 90，但**空位仍然散落各处**、旧墨仍然糊在
> 可用格里，下一轮加新字还得再判一次"这格干净吗"。现在排完之后，**新字直接从第 1320 个可用格
> 往后接着放**，一眼就知道还剩几格。

---

## 4. 搬像素：怎么保证不出错

```
读： 引擎图 (x,y) ──GIF 分段表──▶ 容器数据区字节偏移 + 半字节
写： 清空全部可用格 ▶ 每个字形原样写进新格 ▶ 保护掩码最后说了算 ▶ 整块回写容器
```

写盘前后各一道硬校验，任何一条不过就**报错退出、不产出盘**：

| 校验 | 判据 |
|---|---|
| 包头没被动过 | 逐段比较 48B 前缀字节，完全相同 |
| 别人的采样窗没被动过 | `En[protect] == 原图[protect]`，**0 像素差异** |
| 每个字形原样落到新格 | 1319/1319 个 16x16 块**逐像素相等**（`np.array_equal`） |
| 新格一定可用 | 没有一个字被分到禁用格/被压格 |
| 回读一致 | 从**写好的 ISO** 重新解出引擎图，与目标图**逐像素相等**，且逐字再比一次字形 |
| 容器外没动 | COMMON.PAK 里像素容器以外的字节逐字节不变 |

「空」用哪个调色板索引：取容器里出现最多的非 0 nibble（实测 = 背景色），
不写死数字 —— 换盘/换调色板也不会写错。

---

## 5. 接入构筑管线（`make_build.py`）

### 5.1 位置与语义

```
patch / --expand-entry  ▶  ★ 字库紧凑重排  ▶  文本注入（--inject-csv）  ▶  文本快照 / 字库 dump
```

* 默认**开启**；`--no-font-repack` 关闭（唯一理由：只想出一张和基底逐字节相同的盘）。
* **重排改了「字节↔字符」映射 ⇒ 盘上所有旧编码文本必须整体重编码**（铁律）。
  构筑器自动完成：把每份 `--inject-csv` 表拷一份、**只清 `text_zh` 列**
  （用户译文 `text_edited` **一字不动**）⇒ 注入器认为每行都被人工改过 ⇒ 用新 charset 重编。
  **用户命令行不用改**，注入时自动换成那份副本。
* **0 改动时什么都不做** ⇒ 不改 ISO、不改 charset、不出重编码表 ⇒ 产物 sha256 与基底**完全相同**。
* **有改动却一个 `--inject-csv` 都没给** ⇒ 直接失败（`exit 4`）且**不改任何文件** ——
  否则盘上文本会整段乱码。
* 注入失败时**把 charset 回滚**到重排之前（`_CHARSET_ROLLBACK`）——
  否则 "charset 已经变成新映射、盘还在旧版本" 会让下一轮构筑读到不一致的口径。
  （round46 实测踩过这个坑：第一次构筑在注入预检处失败，charset 已经改了。）

### 5.2 产物与日志（全在版本文件夹内）

```
work/builds/GR_ZH95/temp/font_repack/
  repack_report.json     重排 summary（容量/搬运数/码位变更/交叉核对）
  repack_moves.json      逐字搬运明细（1319 行: slot/字符/新格坐标）
  repack.log             人话版报告
  charset_before.json    重排前的 charset（回滚用 / 复现用）
  reencode/inject1/      强制重编码的文本表副本（只清 text_zh）
```
`build_info.json` 新增 `font_repack` 段：`changed / moved / codes_changed / usable_cells /
blocked_record_cells / blocked_ft_rect_cells / blank_usable_before / remaining_capacity /
iso_sha256_before / iso_sha256_after / iso_unchanged / report / moves / log / one_line`。

### 5.3 不破坏既有契约

`--inject-csv` 语义（目录 / 多表 / 版本名都照旧）、字库预检（缺字 `exit 3`）、
`text/` 快照、`font/` 快照、`audit_inventory.py` 全部保持可用（§8 逐条实测）。

---

## 6. ★ 顺带查实并修好的既有缺陷：6 个汉字一直画不出来

### 6.1 怎么发现的

重排会把图集里**行 23 的格子全部重写**。重写之后，注入器的「字库覆盖预检」第一次报出：

```
[!!] 发现 5 个「有问题的字」:
  ── U+7EC8 「终」  原因: FT 记录 0x9E 的矩形 (16,434,32,450) 及邻域在图集里是空的
  ── U+8106 「脆」  原因: FT 记录 0x9F 的矩形 (32,434,48,450) …
  ── U+819B 「膛」  原因: FT 记录 0xA0 的矩形 (48,434,64,450) …
  ── U+82E5 「若」  原因: FT 记录 0x92 的矩形 (64,434,80,450) …
  ── U+8457 「著」  原因: FT 记录 0xFF 的矩形 (192,434,208,450) …
```

### 6.2 根因（三张盘对照，逐字节可复现）

GR_ZH93 扩容时给 7 个新单字节码改了 FT 记录，指到**图集最底下一行（网格行 24，y=434..450）**：

```
0x92 若 / 0x9D 纤 / 0x9E 终 / 0x9F 脆 / 0xA0 膛 / 0xAE 荐 / 0xFF 著
```

但位图被写在 **flat 容器坐标** `(u0, v0)`，而引擎按**引擎图坐标** `(u0, v0)` 采样。
行 24 属于第 6 段 ⇒ flat 列比引擎列多 `96×7=672` texel：

```
flat(u0, 434)  ↔  引擎((u0−672) mod 1024, 433)      ← 字形掉进了行 23 的某个**对偶格**
```

后果：这 6 个字**在游戏里画出来是空白**，而它们所在的那几个对偶格被别人的字形顶着。

* GR_ZH93 的旧口径 `GlyphCache` 读 flat 行 ⇒ 当年判"有字形"，没发现；
* round45 把 `_nibbles` 改成读引擎行以后就露馅了 —— 但行 23 相邻字形的**1~2 行像素渗进
  ±4/±2 容差窗**，于是预检又被"蒙"过去（假通过）；
* round46 的紧凑重排把行 23 的格子全部重写 ⇒ 渗漏消失 ⇒ **整体重编码时预检如实报出缺字**。

> 也就是说：这是**既有缺陷**，不是重排造成的；重排只是让它**第一次无处可藏**。

### 6.3 修法（`patch_zh95_ft_single_glyphs.py`）

把 6 个字写到**引擎真正采样的位置** = 记录矩形本身。位图来源：
`third_party/fonts/方正像素16.ttf`，按 `tools/font_pipeline/gen_font16.py::render16` 同款配方渲染，
**并与 GR_ZH93 里当年写进去的 flat 位图逐像素核对**：

| 码位 | 字 | 记录矩形 | TTF 墨点 | ZH93 原图墨点 | **IoU** | ZH94 引擎窗原有墨 |
|---|---|---|---:|---:|---:|---:|
| 0x92 | 若 | (64,434,80,450) | 72 | 72 | **1.000** | 0 |
| 0x9D | 纤 | (0,434,16,450) | 59 | 59 | **1.000** | 10（非字形残渣，已覆盖） |
| 0x9E | 终 | (16,434,32,450) | 60 | 60 | **1.000** | 0 |
| 0x9F | 脆 | (32,434,48,450) | 90 | 90 | **1.000** | 0 |
| 0xA0 | 膛 | (48,434,64,450) | 89 | 89 | **1.000** | 0 |
| 0xFF | 著 | (192,434,208,450) | 87 | 87 | **1.000** | 0 |

⇒ 补回去的**就是原来那张图**，不是重新造的字。`0xAE 荐` 在 round40 已改成对偶码，
它的记录是**休眠**的 ⇒ 不动（补丁明确跳过并记录理由）。

补丁自带的安全前提：目标窗必须**要么全空**、**要么只剩"与正确字形 IoU<0.5 且墨量<40%"的残渣**
（纤 那 10 个像素就是残渣：与正确字形 IoU=0.015、只有正确字形的 17%），否则**拒绝覆盖**。

---

## 7. 改了哪些既有工具的口径（都是被重排"顶"出来的，逐条说明理由）

### 7.1 `tools/iso_build/dump_font.py`：修一处坐标混用

`capacity_report()` 数"这个格是不是空的"时用 `atlas_cell_xy_engine()`（**flat 列** = `16*((col+PHI[row])%64)`），
但 `GlyphCache.cell_ink()` 从 round45 起按**引擎图**取行 ⇒ 两者混用会去读**别的格子**的墨。
于是"现在就能直接放新字的只有 N 个"这个数不可信：GR_ZH94 旧口径 **34**（还带着 26 的最严格值），
订正成引擎采样格后是 **50 / 41**；更要紧的是，重排后旧口径会给出远低于真值的数。
**改动仅限 3 个"数墨"调用点**（`_live_rects` 的对偶格 + `capacity_report` 的 vacuum/strict）；
CSV 的 `cell_x/cell_y` 列语义**不变**（仍是 `atlas_cell_xy_engine`，`_grid_selfcheck` 照旧 1504/1504 通过）。

### 7.2 `tools/text_csv/tcslib.py`：`selfcheck_charset` 不再钉死 的/你 的码位

原来自检写死 `的 == (A8,BA)`、`你 == (A8,BB)`（round40 的落点）。重排是**机器分配**码位，
钉死它会让**每一次重排之后 `dump_text_csv.py` 直接拒绝出表**（本轮实测：构筑在文本快照处 `exit 1`）。
现在保留真正的不变量：**必须是对偶码 + lead 在 `0xA1..0xB0` + 「编码↔解码」逐字节自洽**；
"0xAF/0xB0 不再是单字节码"由紧邻的第 3 条单独把关，与码位取值无关。
文案锚点 `G058.I195`（命令→顺序）本来就有 `MUTABLE_TEXT_ANCHORS` 降级机制，未改。

### 7.3 一个**已知局限**（如实写出来）

重排按 `charset` 给的"当前槽位"去图集里取字形 ⇒ 如果 charset 是**别的版本**的映射
（手工换过、或某次构筑半途失败没回滚），取到的就是**别的格子的像素**。
`plan()` 里加了一道粗探针（"某个在用字的槽位整格是空的"超过 2% 就拒绝），
但它只能抓**大面积取空**；两版图集都很满时，取到"别人的字形"是**看不出来**的
（实测：GR_ZH94 的盘 + GR_ZH95 的 charset，探针不响，只会报"搬运 0 个字"）。

真正的保障是流程 + 一道可查的记录：

1. 构筑管线里 charset 与盘**同进同退**：`make_build` 在重排前备份 charset，
   **注入失败**或**重排自身失败**都会**回滚**（§5.1）；
2. 每次构筑成功后，构筑器会把"**这份 charset 配的是哪张盘**"戳进 charset JSON
   （`_font_repack.iso_sha256` / `iso_version`，旁证字段，写失败不影响构筑）；
3. `plan()` 读这个戳：**对得上就不吭声**（正常构筑里下一轮的基底就是上一轮的产物，
   天然对得上）；对不上就打一条 note 提醒 —— 人工单跑时这就是"你可能拿错 charset 了"的信号。
   实测：输入 GR_ZH95 → 静默、0 改动；输入 GR_ZH94（配 GR_ZH95 的 charset）→ 打出 note。
   （注意：构筑时若先打了 `--patch`，这一轮的 sha 必然对不上 —— 那是正常的，
    note 的措辞已把这两种情况分开说。）
4. 人工单跑本工具时**必须用与这张盘同一版本的 charset**（构筑器每次都会把重排前的
   charset 备份到 `<版本>/temp/font_repack/charset_before.json`）。

---

## 8. 验收（全部实跑，逐条对照）

### 8.1 重排效果

```
可用格 1409 = 1504 − 记录码/图标占死 51 − 被 FT 记录矩形压着 44
重排后还能再放  90 个新字
重排前"格是白的、又真能用"的只有  42 个（另有 50 个可用格被旧字形残墨糊着）
搬运 636 个字（原地不动 683 个）；码位变更 636 个；像素改动 59489；清零 90 个可用格
图集墨点: GR_ZH94 105488  →(字形修复 +457/−10) 105935  →(重排清残墨 −1187) 104748
```
（上述 42 / 636 / 59489 是把 GR_ZH94 配它**自己那一版** charset 跑出来的 —— 见 §7.3，
 用错版本的 charset 会得到"搬运 0 个字"的假结果。）

### 8.2 幂等（对 GR_ZH95 再跑一次）

```
字库紧凑重排 — 无需重排 (0 改动)
  在用字形 1319 (搬运 0, 原地不动 1319)
  ★ 剩余容量: 90 个新字
  [幂等] 无需重排 ⇒ **不产出 idem.iso** (产物就是输入盘本身, sha256 不变)
ISO sha256  重排前 c1f5d849…5afafb  →  重排后 c1f5d849…5afafb   （未变 ✓）
charset sha256 1ad9cf0a…ef1af       （未变 ✓，未产出任何文件 ✓）
```

### 8.3 实机回归（同一导航、重排前 vs 重排后，逐像素）

**297/297 帧逐像素完全相同**（含武器详情页滚动箭头）；另用测试文案盘取证「6 个补回的字形确实显示出来了」。
详见 §9。

### 8.4 文案不变

```
python tools/text_csv/diff_text_versions.py GR_ZH95 GR_ZH94
只在 A 消失 0 ; 只在 B 新增 0 ; 内容不同 **0** ; 内容相同 **2261**
条目 2261 → 2261 (+0) ; 字符 65271 → 65271 (+0) ; 中文字 45771 → 45771 (+0)
```

### 8.5 审计 / 预检 / 字库自查

| 检查 | 命令 | 结果 |
|---|---|---|
| ELF 补丁在役 | `audit_inventory.py work/builds/GR_ZH95/GR_ZH95.iso` | 在役 44 条，**缺失 0 条**，其它 1 条（`0x21AC90` 是别的子代理本轮在改的 hook，非本工程回归） |
| 字库预检（新盘 + 自己的表） | `inject_text_csv.py --csv GR_ZH95/text --src GR_ZH95.iso --check-only` | **exit 0** |
| 字库预检（新盘 + **全量重编码表**，2261 行全写 ⇒ 每个字都过检查） | `--csv …/font_repack/reencode/inject1 --check-only` | **exit 0** |
| 格位公式自查 | `dump_font` | 1504/1504 逐个比对，**不一致 0**；`grid_row_alignment` **全 0** |
| 缺字形 | `dump_font` | GR_ZH94 `0` → GR_ZH95 `0`（**未增加**） |
| 容器自洽 | `make_build --verify-img` | MENU.IMG 686 条目 / GR.IMG 4070 条目，越界未对齐 0、重叠 0 |

### 8.6 构筑链路

`GR_ZH95` 全程 **exit 0**：
`work/builds/GR_ZH95/{GR_ZH95.iso, build_info.json, text/, font/, temp/, extract/}` 齐全；
`temp/font_repack/` 6 件产物齐全；`text/` 3 张可注入表 + 10 张 view 表 + meta + txt。
完整构筑日志：`work/builds/GR_ZH95/temp/r46/make_build_zh95.log`。

### 8.7 边界行为（都实测过）

| 场景 | 期望 | 实测 |
|---|---|---|
| 需要重排但**没给** `--inject-csv` | `exit 4`，**不改任何文件** | ✓ exit 4；charset 未变；ISO 与基底**逐字节相同** |
| `--no-font-repack` | 跳过本步，产物 = 基底 | ✓ exit 0；ISO sha == 基底 sha；charset 未变；`build_info.font_repack = null` |
| 对已重排的盘再跑 | 0 改动、不产出文件 | ✓ 见 §8.2（跑了 3 次都一样） |
| charset 与盘对不上 | 报警 / 大面积取空时拒绝 | ⚠ 见 §7.3（只抓粗错，真正保障是流程） |

---

## 9. 实机回归（真机跑，逐像素比对）

### 9.1 重排前 vs 重排后：**297/297 帧逐像素完全相同**

```
$env:GR_ISO='…\work\builds\GR_ZH94\GR_ZH94.iso'; python tools\capture\run_opt.py r46w nav_weapons2.txt 30000 100
$env:GR_ISO='…\work\builds\GR_ZH95\GR_ZH95.iso'; python tools\capture\run_opt.py r46w nav_weapons2.txt 30000 100
python tools\diag\cmp_dump.py work\builds\GR_ZH94\temp\dump_r46w work\builds\GR_ZH95\temp\dump_r46w
```
```
[cmp] A=…\GR_ZH94\temp\dump_r46w (297 帧)
[cmp] B=…\GR_ZH95\temp\dump_r46w (297 帧)
[cmp] 配对帧 297; **逐像素完全相同 297**; 不同 0; 尺寸/读取异常 0
```

这一跑覆盖：开机 → Ubi 片头 → 记忆卡 → 主菜单（大量汉字）→ 特别收录分类列表 →
**武器详情页（长段中文 + 左侧 ▲▼ 滚动箭头 + 标题栏 ◄ ►）** → 武器图库。
**滚动箭头那一屏（帧 22700..23900）逐像素相同** —— round45 曾经因为擦掉图标矩形让箭头变暗，
本轮专门复查，没有复发。

![武器详情页 A/B](img/r46_weapons_detail_ab.png)

### 9.2 受影响汉字的实机取证（测试文案盘）

交付盘的**用户文案一个字都没改**。取证用的是专门造的「测试文案盘」：
把《特别收录》菜单前 6 个分类名各换 1 个字（长度不变，都是 2 个汉字 = 4 字节）：

| id | 原文 | 测试文 |
|---|---|---|
| `LANG:G058.I739` | 影片 | **若**片 |
| `LANG:G058.I740` | 设定图 | **纤**定图 |
| `LANG:G058.I741` | 音乐 | **终**乐 |
| `LANG:G058.I742` | 武器 | **脆**器 |
| `LANG:G058.I743` | 奖章 | **膛**章 |
| `LANG:G058.I744` | 背景 | **著**景 |

两张测试盘都用同一导航 `nav_weapons2.txt`（同一帧 21600）：

![六个汉字 实机 before/after](img/r46_ft6_before_after.png)

* **BEFORE（从 `GR_ZH94.iso` 造）**：6 个字的位置**全是空白** —— 老盘上它们确实画不出来；
* **AFTER（从 `GR_ZH95.iso` 造）**：`若片 / 纤定图 / 终乐 / 脆器 / 膛章 / 著景` **全部正常显示**。

> ⚠ 造 BEFORE 盘时必须把 charset 换回 GR_ZH94 那一版：否则注入器会用**新**码位把文本写进
> **老**图集（老图集那些格里是别的字）⇒ 整屏乱码。这也侧面说明「改映射就必须整体重编码」这条铁律
> 是双向的。交付盘 `GR_ZH95/text` 的三张表 sha256 与 `build_info.json` 记录**完全一致**，
> 且表里不含任何测试文案（已脚本核对）。

### 9.3 实机命令（可复现）

```powershell
# 主回归（两盘各跑一次，串行，不并发）
$env:GR_ISO='C:\…\work\builds\GR_ZH94\GR_ZH94.iso'
python tools\capture\run_opt.py r46w nav_weapons2.txt 30000 100
$env:GR_ISO='C:\…\work\builds\GR_ZH95\GR_ZH95.iso'
python tools\capture\run_opt.py r46w nav_weapons2.txt 30000 100
python tools\diag\cmp_dump.py work\builds\GR_ZH94\temp\dump_r46w work\builds\GR_ZH95\temp\dump_r46w

# 测试文案盘取证（交付盘不受影响）
python tools\text_csv\inject_text_csv.py --csv work\builds\GR_ZH95\temp\r46\test_text `
    --src work\builds\GR_ZH95\GR_ZH95.iso --dst …\GR_ZH95_test_text.iso
python tools\capture\run_r45.py --iso …\GR_ZH95_test_text.iso --nav tools\capture\nav_weapons2.txt `
    --dump …\dump_r46T --maxframes 22400 --snap 100
```

> 注意：`run_opt.py` 不做路径绝对化，`GR_ISO` 必须给**绝对路径 + 反斜杠**，否则 gsrunner 秒退
> （本轮实测踩过；相对路径/正斜杠都是 `exit=1 elapsed=0s`）。

---

## 10. 复现命令

```powershell
# ① 只看"现在能压出多少空位"（不写盘）
python tools/iso_build/repack_font.py --iso work\builds\GR_ZH94\GR_ZH94.iso --dry-run

# ② 单跑一次重排（出新盘 + 改 charset + 出重编码表）
python tools/iso_build\repack_font.py --iso <src.iso> --out-iso <dst.iso> `
    --text-src work\builds\GR_ZH94\text --reencode-out <out>\temp\font_repack\reencode `
    --report <out>\temp\font_repack\repack_report.json

# ③ 幂等复核（对已重排过的盘）: 应报"无需重排"，且不产出任何文件
python tools/iso_build/repack_font.py --iso work\builds\GR_ZH95\GR_ZH95.iso --out-iso tmp.iso

# ④ 整套构筑（重排 + 重编码 + 注入 一条龙，用户命令行与以前一样）
python tools/iso_build/make_build.py GR_ZH96 --from work\builds\GR_ZH95 `
    --inject-csv work\builds\GR_ZH95\text

# ⑤ 实机 A/B 逐帧比对
python tools/diag/cmp_dump.py <转储A> <转储B>
```
