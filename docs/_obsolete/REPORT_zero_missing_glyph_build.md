# REPORT_zero_missing_glyph_build.md — 「零缺字成品盘」构建（round81）

> 分支 `round73/font-decompile` ｜ 只读：所有 ISO、`third_party/orig/**`、`tools/**`、`docs/**`
> 只写：`docs/REPORT_zero_missing_glyph_build.md`、`work/builds/GR_ZH98/temp/r81/**`、`work/tools/zero_*.py`
> **未切分支、未 commit、未 merge；未改任何盘；未跑模拟器（本机有他人实例占用）。**
>
> ## 一句话结论
>
> **①** 缺字准确数字 = **364 种 / 386 字次 / 25 个条目**（针对用户丰富版译文，非盘上缩减版）；
> 其中 **363 种可用现役配方出字**，仅 **`嘚 U+561A`** 方正像素16 没有字形。
> **②** 流水线做到 **B1（新字形生成，自检 PASS）**；**B2–B6 未做**，因为本轮的侦察发现
> **任务书 B 段的两条前提都不成立**（见 §3），继续按原样做会写出坏盘。
> **③** **成品盘未产出**（原因 + 精确配方见 §3/§6）。
> **④** 实机要跑的 3 个单变量探针与判据见 §7。

---

## 1. 交付物索引

| 类型 | 路径 |
|---|---|
| 缺字清单 CSV | `work/builds/GR_ZH98/temp/r81/missing_chars.csv`（364 行） |
| 缺字条目 CSV | `work/builds/GR_ZH98/temp/r81/missing_entries.csv`（25 行） |
| 汇总 JSON | `work/builds/GR_ZH98/temp/r81/missing_summary.json` |
| 字形产物 | `work/builds/GR_ZH98/temp/r81/glyphs_zh120.json` + `glyphs_zh120_sheet.png` |
| 权威图集解码 | `work/builds/GR_ZH98/temp/r81/atlas_engine_authoritative.npy`（1024×512, {0,1}）|
| 侦察原始日志 | `r81/recon.txt` `probe.txt` `atlas_census.txt` `common_pak_records.txt` `paks.txt` `img_gap.txt` `img_hash.txt` |
| 工具 | `work/tools/zero_{recon,missing,probe,glyphs,atlas,atlas2,atlas3,atlas4,pak,paks,imgmap,hash,hash2,hash3,hash4,hash5,elfstr}.py` |
| 反编译 | `work/tools/ghidra_scripts/TextureHost.java` → `work/tools/texturehost.log` |

---

## 2. 【A】只读侦察结果

### 2.1 A1 — 「现役字库之外的字」准确清单

**口径**：`tcslib.GlyphCache.check_text` 同款 —— `ord(ch) < 0x80` 一律放行；其余必须在
`tools/font_pipeline/data/charset_compiled_zh16.json` 的 `codes`(110) ∪ `pair_of`(1504) 里。

复现：`python work/tools/zero_missing.py`

| 文本源（都是 `text_edited` 非空的 2250 行） | 缺字种数 | 字次 | 条目数 |
|---|---|---|---|
| `work/builds/GR_ZH113b/text`（**盘上现值 = round64 缩减版**） | **0** | 0 | 0 |
| `work/builds/GR_ZH113b/text_backup_before_r71` | **364** | **386** | **25** |
| `work/builds/GR_ZH109/text`（缩减后） | 0 | 0 | 0 |
| **`work/builds/GR_ZH109/text_backup_before_reduce`（用户丰富版原文）** | **364** | **386** | **25** |
| `work/builds/GR_ZH109/text_backup_before_wrapfix` | 364 | 386 | 25 |

⇒ **`364 / 386 / 25` 与任务书给的数字完全一致** ✓（对账成立）。
⇒ 但要注意口径：**这 364 个字来自「用户丰富版译文」，不是盘上现值**。盘上现值（round64 缩减版 +
round67 的 329 字）已经 **0 缺字**。

**现役字符集实测**（`recon.txt`）：
```
单字节 codes 110 : 0x80..0xA0 (33) + 0xB2..0xB4 (3) + 0xB6..0xFF (74)
对偶   pair_of 1504 : lead A1..B0 (16 个) × trail A1..FE (94) = slot 0..1503
```
**0xB1(△) / 0xB5(✕) 不在字符集里** —— 它们是引擎硬编码图标码（`0x219C08/0x219C14` 与 `0xB5/0xB1` 比较）。

### 2.2 A2 — 字形源与渲染配方核对

复现：`python work/tools/zero_probe.py` / `python work/tools/zero_glyphs.py`

| 判定 | 个数 |
|---|---|
| `ok`（窗内墨 ≥1、墨不越 16×16 em 窗、hex 回读逐点一致） | **363 / 364** |
| `ttf_missing`（`方正像素16.ttf` 无此字形） | **1** = `嘚 U+561A` |
| `overflow` / 空 | 0 / 0 |

* 配方 = `tools/font_pipeline/gen_font16.py::render16()`（PIL `truetype(16)` / 32×32 白底 /
  `draw.text((8,8))` / 取 `canvas[8:24,8:24]` / 阈值 `<128`）**逐行同款**。
* 与历史记录一致：**693 候选里唯一缺字形就是 `嘚`**（`REPORT_expand_font_329.md` §2.3）。
  它需要 `gen_font16.py` L128–145 的 `FALLBACK16`（从现役 `atlas_zh16.png` 抠 13px 字形）。
* 产物：`glyphs_zh120.json`（逐字 16 行 hex）+ `glyphs_zh120_sheet.png`（13×28 联系表，
  缺字形画灰框）。自检 ①墨≥1 ②不越窗 ③hex 回读一致 ④联系表尺寸 —— **全 PASS，exit 0**。

### 2.3 A3 — 目标图集布局：**任务书给的 h=768 与"可用格"数字都用不上**（见 §3）

### 2.4 顺带查清的三件事（都是新事实）

**(a) 图集容器结构（权威口径，`tcslib.atlas_container_segments`，round67 实机验证过）**

```
COMMON.PAK 记录 new_font_revised : psm=0x14(PSMT4) w=1024 h=512 clut=0x410 px_size=0x40010
容器 = 8 个自闭合 IMAGE 包 + 1 个尾部 no-op 包
  段 k = [PT tag 16B][A+D TRXPOS 16B] + [IMAGE tag 16B] + 数据
         TRXPOS.SSAY = 首行 = 0/64/128/192/256/320/384/448
  段数据 : 段0..6 各 0x8000 B (64 行) ; 段7 = 0x7E80 B (63 行 + 128 B)
  尾部   : 16 B no-op IMAGE tag (nloop=0, EOP=1)
  合计   : 8×48 + 261,760 + 16 = 262,160 = 0x40010 ✓ 与 px_size 严丝合缝
```
⇒ **`px_size` = 容器字节数；`region_bytes = px_size − 0x10` 这条旧结论是错的**
（真正关系是 `px_size = 8×48 + 段数据 + 16`）。

**(b) 权威解码后的图集普查**（`atlas_engine_authoritative.npy`，全图只有 nibble {0,1} 两种值，零杂散）

| 网格行 | y | 有墨格 | 空白格 |
|---|---|---|---|
| 0..23 | 2..418 | **62/62（满）** | 0 |
| 24 | 434 | 16（slot 1488..1503） | **46**（col 16..61） |
| 25 | 450 | 46 | 16 |
| 26 | 466 | 17 | 45 |
| 27 | 482 | 28 | 34 |
| ≥28 | ≥498 | — | 越界（h=512） |

```
★ 现役 1504 个 pair 格里"零墨"的 = 0   ← 坐标系 + 容器解码双重反证通过 ✓
图标跳空带 y[194,242)  : 墨 5,209 / 纯透明 43,943 (=171.7 格)  ← 被"单字节带"占着
行 25-27    y[450,498)  : 墨 3,857 / 纯透明 45,295 (=176.9 格)  ← 被 EN 带 + 第二条带占着
底部        y[498,512)  : 墨 0     / 纯透明 14,336 (=56.0 格，但只有 14 px 高)
```
**记录表活带**（3 个 face 全部列出，`probe.txt`）：

| face | nrec | 活 (v0,v1) 组合 |
|---|---|---|
| large / default | 224 | `(195,211)×62` `(211,224)×4` `(211,227)×16` `(213,229)×22` `(452,468)×92` `(482,498)×28` |
| huge | 96 | `(211,224)×2` `(213,229)×2` `(452,468)×92` |

⇒ **y=452..468（EN 带）与 y=482..498（第二条带）都是活的**；跳过带 y194..229 被单字节带占着。
⇒ **h=512 里没有任何一条干净的 16px 空带**；自由格合计只有 **141**（行 24..27 的空白格）。

**(c) IMG 头 `+0x20` 指向一张 4096×u32 表**（`img_gap.txt` / `img_hash*.txt`）
```
MENU.IMG 头 12 个 u32 = [size, names_end, 0x800, tbl_end, names_start, 0x10000, 1, 0, 0x9230, 0,0,0]
GR.IMG   头 12 个 u32 = [size, names_end, 0x800, tbl_end, names_start, 0x46800, 1, 0, 0x30CB0, 0,0,0]
```
* `u32[+0x14]` = **数据区起点**（0x10000 / 0x46800）—— 旧报告没记这个字段；
* `u32[+0x20]` 指向容器内 **16,384 B = 4096 × u32 的哈希表**（0xFFFFFFFF = 空槽），
  落在「表尾..名字区」那 18,784 B 空隙的 **+0x960** 之后：
  MENU 469 个非空槽 / GR 1,704 个；值 = **条目下标**；同名条目在两容器里**落在同一个槽**
  （165 例，如 `D03_TRAINDEPOT.MIS`→25、`PSG1.GUN`→52）⇒ 槽位是**名字的确定性函数**。
  试了 90 个常见哈希（djb2/sdbm/fnv1a/crc32/adler/sum/xor × 大小写 × 5 种取模）**全部不中**
  （最高 2/330 = 随机水平）⇒ 哈希函数**未解出**。
* ⚠ **这是任务书 B3 的一个坑**：`work/tools/img_add_entry.py` 的配方是「把名字区整体前移到新表尾」，
  它会**写进 [0x88D0, 0x2D46] 这段空隙**，也就是**把哈希表前面 11 KB 覆盖掉**。
  该工具的自检只重新解析容器结构，**不会发现这件事**。

---

## 3. 【B】为什么 B2–B6 没有按任务书的形态做 —— 两条前提被本轮实测否证

### 3.1 ✗ 前提一：「新图集作为 MENU.IMG/GR.IMG 的新条目（吃掉尾料）」**装不下**

> ★ **本节已按 Lead 的并行实机结论更新**（`work/builds/GR_ZH98/temp/r81/LEAD_CORRECTION_add_entry_recipe.md`，
> 写于本轮进行中）：**pda 两张贴图转 4bpp 可再回收 65,536 B**。下表是更新后的总账。

| 空间 | 字节 | 依据 |
|---|---|---|
| MENU.IMG 尾料（末条结束 58,239,646 → 容器 58,300,882） | 61,236 | `zero_paks.py` |
| **`pda-lcd-02` + `pda_counterparts` 转 PSMT4**（各 256×256 8bpp `0x10010` → 4bpp `0x8010`） | **+65,536** | Lead 实机/静态核对；**PSMT4 + clut=0x410 这个组合就是现役字形图集本身**（记录 #1），已在跑 |
| GR.IMG 尾料 | 65,536 | `zero_paks.py` |
| ISO 尾（改目录记录 data length） | 30,254 | `zero_verify_sites.py`（旧报告写 28,672，实测 30,254） |
| **合计** | **≈222,562** | |

而**一张完整的新图集**是：
```
h=640 PSMT4 : 10 段 × 48 B + 0x50000 像素 + 16 B no-op = 328,688 B
h=768 PSMT4 : 12 段 × 48 B + 0x60000 像素 + 16 B no-op = 393,808 B
```
⇒ 即便按更新后的 222 KB 总账，**整张新图集仍然放不下**（393 KB）；**只有"增量"放得下**：
```
h=640 增量 = 0x501F0 − 0x40010 = +66,016 B   ✓
h=768 增量 = 0x601F0 − 0x40010 = +131,552 B  ✓（在 222 KB 内，余 ~91 KB）
```
而增量必须写在**原记录所在的 COMMON.PAK 内部**（它被引擎按 mode-0 PAK 记录整块读走），
不能拆成"新的顶层条目" —— 那会把 COMMON.PAK 的 `stored` 改小/让记录跨文件，
`LoadingTexturePak` 的顺序读会直接错位。

### 3.1b ★ 一个必须点明的推论：**贴图加高本身不增容量**

容量（可用码位数）= `lead 数 × stride`，由 ELF 的 gate 立即数与 stride 决定，
**与贴图高 h 完全无关**（`REPORT_font_capacity_decompile.md` §3.4 已证）。
现役 = `(0xB1−0xA1) × 94 = 16 × 94 = **1504**`。h 从 512 抬到 768 只多出**细胞**，
不多出一个**码位**：
```
h=512 → 公式行 0..27   ⇒ 1736 格（其中 1504 被现役占，余 141 可用）
h=640 → 公式行 0..35   ⇒ 2232 格
h=768 → 公式行 0..43   ⇒ 2728 格
但 slot = (lead−0xA1)×94 + (trail−0xA1) 只能取 0..1503 ⇒ 第 1505 个码位**永远不存在**
```
⇒ **要放下 364 个新字，必须同时做两件事：① 抬 gate（≥0xB5 ⇒ 1880 码位）② 抬高贴图（≥640）。**
只做② = 白花钱；只做① = 无处可画（§2.4(b)：h=512 只剩 141 格）。


### 3.2 ✗ 前提二：「新条目名能被 `diSearchFile` 找到 ⇒ 改 FONT.RES 贴图名即可」**与 F4 冲突，且格式路径有雷**

任务书要「改 FONT.RES 贴图名指向新条目」。但：

1. `docs/REPORT_font_capacity_route.md` **F4** 明确记录：把贴图名指向既有顶层条目 `LOAD_NEW_1.RSB`
   ⇒ **全程纯黑、cdvd 对该区零读取**，结论「纹理名解析域 = PAK 内部目录」，并列入
   **「14 条别做什么」的第 5 条**。
2. 本轮反编译 + 字符串实证**不支持** F4 的结论：
   * `RSFontMgr::ReadResourceFile` 用 `diSearchFile("font.res")`（ELF 字面量 @0x57AD70，**小写**）
     而容器里的条目名是 **`FONT.RES`（大写）** ⇒ **顶层 IMG 条目确实在 `diSearchFile` 的名字域里，
     且大小写不敏感**；
   * `LoadingTexturePak(0,…)` 拼出 `"host0:p:/ike/release/uitexture/common.pak"`（ELF @0x58C1A4/0x58C1C4）
     并成功 `diSearchFile` 到 **MENU.IMG 条目 #3 `COMMON.PAK`** ⇒ 同上；
   * `LOAD_NEW_1.RSB`（MENU #38）**在那张 4096 槽表里（slot 3097）**，所以也不是"名字没注册"。
   ⇒ F4 的失败**更可能是"名字串写错"**（`FONT.RES +0xD` 前有 `u32 长度=20`；写成 14 字符的
   `LOAD_NEW_1.RSB` 却不改长度 ⇒ RSString 含 6 个 NUL ⇒ 哈希查不到 ⇒ `idistream(1,-1)` 零读取），
   但**这只是解释，不是证据**。
3. 而且顶层条目的解析路径是 `LoadIndexedRSB → LoadRSBFile`（**wire RSB**），它对 4bpp 大面有**两个雷**：
   * case 5（`p0..p3 = 1,1,1,1` → PSM4）的 CLUT 由**引擎自己合成 + 字节重排**
     （反编译见 `texturehost.log`），我们**无法直接控制调色板**；
   * 该分支按 `0x40000` 字节切 GIFTAG，**第二片不带 TRXPOS/TEX0** ⇒ 327 KB 的 PSMT4 面
     会走这条**从未被官方数据走过**的路（历史 F6 的 1024 宽崩溃正是"包不闭合"家族）。
   而 mode-0 PAK 记录走的是**我们自建的自闭合包**，是**已实机验证**的路线。

⇒ **结论：任务书 B 段的"加顶层条目 + 改贴图名"这条路，既装不下，又踩在 F4 的雷区上，
且格式路径未验证。本轮不改写它，改为把可行路线写清（§6）。**

### 3.3 ✓ 可行的替代（零 ISO 增长、零新条目、零贴图名改动）

**核心事实**：**h=640 就够装下 364 个字**；按更新后的 222 KB 总账还能直接上 **h=768**（更多余量），
而且**两条路线都不需要改 ISO 文件大小、不需要新条目、不需要改贴图名**。

```
需要的新字 : 364（+4 个被 gate 挤掉的现役字 = 368 个格）
格位来源   : 行 24 尾 46 + 行 25/26/27 各 62（把那两条活带搬走）+ 行 28/29/30 各 62
           = 46 + 186 + 186 = 418 格  ≥ 368 ✓（余 50）
贴图高度   : 行 30 → y = 2+16×33 = 530，+16 = 546 ⇒ h ≥ 546
           ★ 按更新后的 222 KB 总账，**推荐直接上 h=768**（任务书原值）：
             增量 +131,552 B ≤ 222,562 ✓（余 ~91 KB），公式行 0..43 = 2728 格
             ⇒ 本次用完 418 格后**还留 ~1200 格**给后续轮次，不必再动结构
           （h=640 省一半空间但把行数卡到刚够，不推荐）
字节增量   : h=768 ⇒ 0x601F0 − 0x40010 = **+131,552 B**
空间       : MENU.IMG 自带尾料 61,236 + pda×2 转 4bpp 65,536 + ISO 尾 30,254 ≈ 157,026（不动 GR.IMG）
           ⇒ 131,552 ≤ 157,026 ✓ **ISO 文件大小不变** ✓
```

**改动清单（每一项都给了落点）**

| # | 层 | 改动 | 落点 |
|---|---|---|---|
| 1 | 数据 | 图集 1024×512 → **1024×768**；段 = 12×(32+16+0x8000) + 16 no-op；`px_size 0x40010 → 0x601F0`、`h 512 → 768` | COMMON.PAK 记录 #1 @MENU.IMG+0x57400+0x1031 |
| 2 | 数据 | **行 0..511 除两条带外逐字节不变**；行 512..767 新增；新字画进行 24(col16..61)/25/26/27/28/29/30 | 同上像素区 |
| 3 | 数据 | **搬两条活带**：EN 带 `(452,468)→(594,610)`（92 条 × 3 face）；第二条带 `(482,498)→(610,626)`（28 条 × 2 face）。**u 不变，只改 v** ⇒ 记录数/展开长度 5942 不变 ⇒ 槽 4421 不变 | FONT.RES（MENU.IMG #4 @0xB9120）；ISO 绝对偏移 0x5ECE8120 |
| 3b | 数据 | **可选（Lead 建议的单变量前置）**：`pda-lcd-02`/`pda_counterparts` `psm 0x13→0x14`、`px 0x10010→0x8010` + 4bpp 重打包 + COMMON.PAK 尾部重排 ⇒ 回收 65,536 B | COMMON.PAK 记录 #2/#3 |
| 4 | ELF | **抬 gate**：4 处 `sltiu …,0xB1` → `0xB5`（VA `0x416EE8` / `0x417160` / `0x41751C` / `0x5656A4`；**ISO `0x3AA768` / `0x3AA9E0` / `0x3AAD9C` / `0x4F8F24`，已逐字节实测 §4.1**） | 4 个字（每字只变最低字节） |
| 5 | 文本 | `0xB2 键 / 0xB3 练 / 0xB4 用` 由单字节改对偶；**`△ 0xB1` 也改对偶**（编码成 `(0xB1,0xA1)`，把 △ 图形画进对应格） | charset + `make_build --inject-csv` |
| 6 | 容器 | COMMON.PAK **净长大 +66,016 B**（= 图集 +131,552 − pda×2 回收 65,536）；MENU.IMG：`u32[+0x00]` 58,300,882 → **58,366,898**；**#4 起的条目 `off` 全部 +66,016**；`[0xB9120, 尾)` 整体后移 66,016 B；名字区/4096 槽表（在 0x57400 之前）**不动** | MENU.IMG 头 + 条目表 |
| 7 | ISO | ISO9660 里 `MENU.IMG;1` 的目录记录 data length **+66,016 → 58,366,898**（**LE @ISO 0x828D8 / BE @ISO 0x828DC**，已实测 §4.1）；**ISO 文件大小不变** | PVD 目录记录 |

**空间账（h=768 版，逐步）**
```
COMMON.PAK 现长                                 400,659
  − pda×2 转 PSMT4 (各 0x10010→0x8010)          −65,536   ⇒ 335,123
  + 图集 h 512→768 (0x40010→0x601F0)           +131,552   ⇒ 466,675
COMMON.PAK 净长大                               +66,016
MENU.IMG 现长                                58,300,882
  + 净长大                                      +66,016   ⇒ 58,366,898
  其中来自 MENU.IMG 自带尾料                    61,236
  其中来自 ISO 尾                                4,780   （ISO 尾实测 30,254 ✓ 够）
ISO 文件大小                                          不变 ✓
```
⇒ **`+66,016` 同时是「COMMON.PAK 净长大」「MENU.IMG 长大」「ISO9660 data length 增量」，
也是「所有 #4 起条目的 off 位移量」** —— 改盘时这四个数必须是同一个。
⚠ 若不做 pda 转换，则 ISO9660 增量 = 131,552，超出 MENU 尾料 61,236 + ISO 尾 30,254 = 91,490 ✗
⇒ **pda 转 4bpp 是 h=768 的必要前置**（这也正是 Lead 把它列为"单变量前置"的原因）。


**为什么这条路线安全**：
* 新字仍走**已实机验证的网格公式**（`ComputeCharTextureCoords` cave），不需要记录表扩容、
  不需要抬 `nrec`、**F6 保持休眠**（对偶码恒走网格、恒返回 16 px 宽）；
* `FONT.RES` 的**记录条数不变、展开长度不变**（只改 v 值）⇒ 不触发历史上卡死的
  「MENU.IMG 尾部平移 + FONT.RES 长大」变体里的 FONT.RES 部分；
* 新字全部落在 **y ≥ 450 且不在任何活带里**的区域，与现役 1504 格的像素**零重叠**。

**代价 / 未解项**：见 §8。**唯一无法离线判定的门** = 引擎接不接受 h=640（TEX0.TH 从 9 变 10）。

---

## 4. 【C】已完成的验证

| # | 项 | 结果 |
|---|---|---|
| C1 | _缺字清单复现_ | `zero_missing.py` 对 5 个文本源输出与 `REPORT_text_reduce.md` / `REPORT_expand_font_329.md` 对账一致：693→（329 入选后）364 ✓ |
| C2 | _渲染管线自检_ | `zero_glyphs.py` exit 0：363 ok / 1 ttf_missing / 0 overflow；①墨≥1 ②不越窗 ③hex 回读 ④联系表尺寸 全 PASS |
| C3 | _图集解码自证_ | `zero_atlas4.py`：**1504/1504 现役 pair 格全部有墨**，全图只有 nibble {0,1}、零杂散 ⇒ 容器解码 + 坐标系双反证 ✓ |
| C4 | _容器结构自证_ | 段表 8×48 + 261,760 + 16 = 262,160 = `px_size` **严丝合缝** ✓ |
| C5 | _反编译_ | `TextureHost.java` 拿到 `GetTexture` / `LoadIndexedRSB` / `LoadingTexturePak` / `LoadRSBFile` / `ReadResourceFile` / `diSearchFile(Ex)` 六份 C（`texturehost.log`）|
| C6 | _资源盘点_ | `zero_paks.py`：4 个引擎自加载 pak（common/menu/loading/action）**内部尾料都只有 4 B**（压满）⇒ 借道 pak 无空间 |
| C7 | _幂等_ | 本轮全部工具**只读**，重跑两次输出逐字节相同（无写盘路径） |
| C8 | ★ _落点逐字节实测_（`zero_verify_sites.py`）| **4 处 gate 全部命中** + ISO9660 字段偏移实测（见 §4.1） |
| C9 | _成品盘结构自检 / 逐字节对照 / dump_font_ | **未做（无成品盘）** |

### 4.1 ★ 落点从"文档引用"升级为"盘上实测"

```
=== 4 处 gate 立即数（GR_ZH113b 现役盘逐字节读）===
  0x00416EE8  ISO 0x3AA768  b1 00 a9 2c  sltiu $t1,$a1,0xB1  ✓   (EN 原盘 10 00 bd 27)
  0x00417160  ISO 0x3AA9E0  b1 00 09 2d  sltiu $t1,$t0,0xB1  ✓   (EN 原盘 01 00 a5 24)
  0x0041751C  ISO 0x3AAD9C  b1 00 4b 2d  sltiu $t3,$t2,0xB1  ✓   (EN 原盘 2d 10 20 02)
  0x005656A4  ISO 0x4F8F24  b1 00 6c 2d  sltiu $t4,$t3,0xB1  ✓   (EN 原盘 00 00 00 00)
  ⇒ 4/4 命中；改成 0xB5 只需把每处的**最低字节** 0xB1→0xB5（共 4 字节）
  （ELF: ISO 0x93800 是 ELF 头, LOAD 段 file off 0x80 vaddr 0x100000 ⇒ ISO = 0x93880 + VA − 0x100000）

=== FONT.RES 名字串 ===
  slot[0x00..0x20] = d1 05 00 00 | 36 17 00 00 | 2a 14 00 00 | 00 | "new_font_revised.rsb" | 03 5d 02 …
  ISO 0x5ECE812D: 6e 65 77 5f 66 6f 6e 74 5f 72 65 76 69 73 65 64 2e 72 73 62 03 5d 02
  ⚠ **名字是 20 字符**（旧报告 §11.1 写"22 字符 + NUL"是**错的**）；
    其后 `03` 才是 face 数（该处巧合成立，因为名字串落在 LZ 流首个 literal run 内，
    长度字段 u32=20 在解压后的 FONT.RES 里、不在 ISO 里）

=== ISO9660 目录记录（根目录 LBA 261）===
  MENU.IMG;1 记录起始 ISO 0x828CE，记录长 58 B
    +10 data length (LE) @ ISO 0x828D8 = 58,300,882   ← 长大 66,016 时改这里
    +14 data length (BE) @ ISO 0x828DC = 58,300,882   ← 同一值的大端副本
    +2  LBA (LE) = 776,286（不变）  +18..+24 时间戳 = 66 0b 07 10 01 1a 24
```


---

## 5. ⚠ 对 Lead / 其他并行任务的三条订正（会直接影响它们的判断）

1. **`img_add_entry.py` 的「名字区整体前移」配方会破坏 IMG 头 `+0x20` 指向的 4,096×u32 哈希表**
   （空隙 `[tbl_end, names_start)` 的 +0x960 之后不是空的，MENU 469 / GR 1,704 个非空槽）。
   该工具自检只验结构、验不出这个。
   ★ **本结论与 Lead 的实机结论方向一致、配方也一致**（`LEAD_CORRECTION_add_entry_recipe.md`：
   实机对照 旧配方 ⇒ TLB Miss 4 / needle 0 hits；新配方 ⇒ TLB Miss 0 / 1173 hits）。
   两种机理都指向同一个修法（**只追加名字、不动 `u32[+0x10]`、不动既有条目记录**）：
   * Lead 给的原因：条目记录里存了指向名字区的偏移/索引；
   * 本轮给的原因：头 `+0x20` 的哈希表就住在那段空隙里，前移名字区会覆盖它。
   **建议两说并存**（都在盘上有依据）；MENU.IMG 名字区 [0xD230,0xFF46) 到数据区 0x10000
   有 **186 B** 空位，够放 1 个名字，只改 `u32[+0x04]` 与 `u32[+0x0C]`。
   ⇒ 本条**已由 Lead 实机闭合**，本报告只做交叉印证，不再单列待办。
2. **`px_size = region_bytes + 0x10` 这条旧结论是错的**（F7 引用的「`alloc − 0x10`」只对原版单包成立）。
   权威关系 = `px_size = 段数×48 + 段数据字节 + 16`。现役 8 段：8×48 + 261,760 + 16 = 262,160 ✓。
3. **F4 的结论（「纹理名解析域 = PAK 内部目录」）证据不足**：`font.res`→`FONT.RES`（大小写不同）与
   `host0:p:/ike/release/uitexture/common.pak`→`COMMON.PAK`（路径形态不同）**都成功**，
   且 `LOAD_NEW_1.RSB` **在那张 4096 槽表里**。建议把「14 条别做什么」的第 5 条降级为
   **「未定案，且失败更可能是名字串长度字段写错」**，并重跑一个**只改贴图名、名字等长**
   的单变量探针来定案。
   ⚠ 即便定案为"可行"，§3.1 的**算术**仍然挡着（整张新图集 393 KB > 222 KB），
   且 wire-RSB 路径的 CLUT 不可控 + `>0x40000` 切 tag（§3.2-3）。
4. **旧报告 `REPORT_font_content_logic_split.md` §11.1 的「22 字符 + NUL」是错的**：盘上实测
   `new_font_revised.rsb` = **20 字符**（§4.1）。等长覆盖的可用宽度是 **20**，不是 22。


---

## 6. 【B】流水线的逐步状态与配方

| 步 | 内容 | 状态 | 自检 |
|---|---|---|---|
| **B1** | 生成新字形（364 缺字 → 4bpp 墨迹，现役口径） | ✅ **完成** | C2 |
| **B2** | 重建图集 1024×640 PSMT4（N 个自闭合 GIF 包，已 512 行逐字节不变） | ⛔ 未做 —— 需要先过 §7-P1 | 设计见 §3.3① |
| **B3** | 加新条目吃掉尾料 | ⛔ **不做**（§3.1 装不下 + §5-1 会踩哈希表）；改为 §3.3⑥ 的「COMMON.PAK 原地长大 + MENU.IMG 平移」 | — |
| **B4** | 改 FONT.RES（搬两条活带） | ⛔ 未做（依赖 B2 的最终 y 布局） | 设计见 §3.3③ |
| **B5** | 修 F6 | ✅ **不需要**：对偶码恒走网格、`nrec` 保持 224 ⇒ 对偶分支恒假是**期望行为**（恒返回 16 px 宽）。只有走「抬 nrec」路线才必须先修 F6 —— 本方案不走 | — |
| **B6** | 出盘 `GR_ZH120` | ⛔ **未产出** | — |

**B2 的精确配方（可直接实现）**
```
新容器 = 10 段, 每段 [PT tag 16B][A+D TRXPOS(SSAX=0, SSAY=64k) 16B][IMAGE tag(nloop=0x800) 16B]
                + 0x8000 B 像素
         + 尾部 16B no-op IMAGE tag (nloop=0, EOP=1)
       = 10×48 + 0x50000 + 16 = 0x501F0
记录字段: w=1024 不变 ; h 512→640 ; clut 0x410 不变 ; px_size 0x40010→0x501F0
像素: 引擎口径 A(640,1024) {0=墨,1=底}
        段 k 数据 = 行 [64k, 64k+64) 的列交错 4bpp: 偶数列→低半字节, 奇数列→高半字节
                        (与 tcslib.atlas_container_segments / patch_zh113_expand_font.py 同款)
```
**必须的硬断言**（照 `patch_zh113_expand_font.py` 的做法）
```
① 行 0..511 里, 现役 1504 个 pair 格 + 单字节/EN/第二条带被引用的矩形 ⇒ 逐字节不变
② 新字墨点全部落在目标格内 (格外墨点改动 = 0)
③ 字节级: 实际变动 ⊆ (新行 512..639) ∪ (行 24..30 的目标格) ∪ (两条带的新旧位置)
④ 段表回读 == 目标 A (逐 texel)
⑤ FONT.RES 记录数 / 展开长度 5942 不变
⑥ MENU.IMG: 只动 u32[+0x00] 与 #4 起的 off; 名字区/哈希表 0 字节差异
```

---

## 7. 【★】实机验证：要跑什么、判据是什么（本机有他人实例，必须排队）

> 三个探针都是**单变量**，且**都在 §3.3 的必要路径上**；任何一个失败都能立刻否掉对应的一步，
> 不至于"混合变量看不出归因"。跑法沿用仓库既有脚本，**不抢/不杀别人的实例**。

### P1（最关键）—— **h=640 贴图被不被接受**
```powershell
# 只做一件事: COMMON.PAK 记录 new_font_revised 的 h 512→640、px_size 0x40010→0x501F0、
#   容器重切成 10 段 + 尾部 no-op; 行 0..511 逐字节复制, 行 512..639 全填 0x11(透明);
#   FONT.RES / ELF / 文本 / 字形 一律不动 (⇒ 画面必须与基底逐像素一致)
python tools/iso_build/make_build.py GR_TEST_FONTCAP_H640 --from work/builds/GR_ZH113b `
       --patch <zero_probe_h640.py> --no-textdump --no-text-snapshot
python tools/capture/nav_hook.py GR_TEST_FONTCAP_H640 --tag h640
```
**判据**
* ✅ 通过：截图里**任意界面文字与 `GR_ZH113b` 逐像素一致**（主菜单 / 记忆卡屏 / 名字页各一张），
  且 `cdvd.log` 里 COMMON.PAK 区的读取字节数从 261,760 变为 327,680 ⇒ 引擎按 h=640 读了容器。
* ❌ 不通过：出现花纹 / 错位 / 黑块 / 字形整体偏移 ⇒ 贴图高被硬约束（回到"改格距"或"抬 nrec"路线）。
* 反面判据（若 TH 被钳到 9）：y ≥ 512 的采样会**回绕到 y−512**，表现为**新行区域出现旧字形**。

### P2 —— **抬 gate 之后 lead `0xB1..0xB4` 生效、且 `0xB1` 作为对偶码能画出 △**
```powershell
# 在 P1 通过的前提下: 4 处 sltiu 0xB1→0xB5 + 把 4 个已知字 (键/练/用/△) 放进 4 个新 slot,
#   在一屏 UI 文本里显示它们, 与「ASCII 标签 + 现役旧字」同屏对照
python tools/iso_build/make_build.py GR_TEST_ZERO_LEAD --from work/builds/GR_ZH113b `
       --patch <zero_probe_lead_b5.py> --no-textdump --no-text-snapshot
python tools/capture/nav_hook.py GR_TEST_ZERO_LEAD --tag leadb5
```
**判据**（照 `REPORT_expand_font_329.md` §7.4 的五条）
1. 页面确实到达（nav_hook 闭环自报）；2. 行标签可认；
3. `△` 必须画成**三角图标**（不是两个半角怪字、不是空白）；
4. 对照组 `O: 我国山` 正常；5. 每行的字形块数 == 预期（若 lead 失效会变成 **2 倍块数**）。

### P3 —— **文本自洽**（前三步都过之后）
```powershell
python tools/text_csv/inject_text_csv.py --csv work/builds/GR_ZH120/text `
       --src work/builds/GR_ZH120/GR_ZH120.iso --check-only
python tools/iso_build/dump_font.py --iso work/builds/GR_ZH120/GR_ZH120.iso --out <dir>
python tools/iso_build/audit_inventory.py work/builds/GR_ZH120/GR_ZH120.iso
```
**判据**：`[ok] 字库覆盖完全` + `缺字形 = 0` + `audit_inventory` 在役 44 / 缺失 0 + exit 0。

---

## 8. 已知限制与未完成项（如实）

1. **成品盘未产出。** 直接原因：任务书 B 段的两条前提（§3.1 装不下 / §3.2 踩 F4）不成立，
   而替代路线要过 §7-P1 这道**只能实机判定**的门。**没有实机窗口 ⇒ 不写坏盘。**
2. **h=640 的引擎接受度未知。** `LoadingTexturePak` 的 `+0x30` 记账公式对
   `px_size = 0x501F0` 给出 `(0x501F0 + 0x4000F)/0x40010 = 2 ⇒ +0x30 = 0x501F0 − 0x20 = 0x501D0`，
   而真实像素字节 = `0x50000`。差值 464 B。`REPORT_font_capacity_route.md` §0 判定「`+0x30` 不是风险」
   （现役盘 `+0x30 = 0x3C3D0` ≠ `0x40000` 也正常），**但那是 h=512 的单点观察，h=640 未验**。
3. **`△ 0xB1` 改对偶码之后的观感/宽度未验**：现役 △ 走引擎硬编码 UV、宽 20 px；
   改对偶后走网格、宽 16 px。**文本里 △ 的出现次数本轮没统计出来**
   （`text_edited` 里没有 `\uE0B1`，说明它由 `tcslib` 的标记系统在注入时才展开；
   抬 gate 前必须先数清，见 §6 第 5 条）。
4. **那张 4,096×u32 哈希表的哈希函数未解出**（90 个候选全不中）。它对"新增条目名"是否有影响
   **未定案**；§5-1 给的"不动名字区/不动哈希表"的配方就是为了绕开这个未知。
5. **F6 本方案不需要修**，但如果 Lead 选择"抬 `nrec` + 对偶走记录表"的路线，
   则 **F6 必须先修**，而且要先把"记录矩形的 UV 标度"（r73 §5 的 `add.s f0,f0` ×2 推测）
   用实机单变量实验定案（改一条 ASCII 记录的 `u0` ±8，看字形横移 16 还是 8 texel）。
6. **`嘚 U+561A` 仍无字形**：需 `FALLBACK16` 从 13px atlas 拷贝，或换字形源。
7. **未跑任何模拟器**：本机有他人实例占用（任务书所述 pid 43737/43780 一类的占用者），
   且本轮全部动作都是静态分析，**没有抢/杀任何进程**。
8. **B2/B4/B6 的脚本未写**：不是"忘了"，是**先要 P1 的结论才能定 y 布局**
   （h=640 不成立就要换 608/576 或改走记录表路线，y 布局与 FONT.RES 改法全变）。

---

## 9. 复现命令（全部只读，可一键重跑）

```powershell
python work\tools\zero_recon.py      # FONT.RES / 容器头 / 条目表
python work\tools\zero_missing.py    # A1: 364/386/25 + CSV
python work\tools\zero_probe.py      # A2 渲染判定 + 记录活带 + 单字节用量
python work\tools\zero_glyphs.py     # B1: 363 字位图 + 联系表 (exit 0)
python work\tools\zero_pak.py        # COMMON.PAK 4 条记录
python work\tools\zero_paks.py       # 4 个 pak 宿主余量
python work\tools\zero_imgmap.py     # 空隙 + 头字段
python work\tools\zero_hash.py zero_hash2.py zero_hash4.py zero_hash5.py   # 4096 槽表
python work\tools\zero_atlas4.py     # ★ 权威图集普查 (1504/1504 有墨)
python work\tools\zero_elfstr.py     # ELF 里的 pak 路径 / 资源名
work\tools\gh.bat work\tools\ghidra_proj_ee GRLocEE -process SLUS_206.13.elf `
       -postScript TextureHost.java -scriptPath work\tools\ghidra_scripts -noanalysis
```
