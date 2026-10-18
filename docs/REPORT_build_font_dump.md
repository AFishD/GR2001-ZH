# 报告：版本文件夹内的「文本 + 字库」快照（构筑产物目录收敛）

> 轮次：round36（分支 `round33/font-dump`）｜实跑日期：2026-10-10
> 交付：`tools/iso_build/dump_font.py`（新）、`tools/iso_build/make_build.py`（改）、
> `tools/text_csv/diff_text_versions.py`（改）、`docs/BUILD_TOOLCHAIN.md`、`tools/text_csv/FORMAT.md`、
> 本报告；测试版本 `work/builds/GR_ZH99_snap/`

## 0. 一句话

**每次构筑完，`work/builds/<版本>/` 里就同时有这一版的「文本 CSV/TXT」和「字库 dump 四件套」；
构筑不再往 `work/` 的任何其它地方写一个字节**（实跑对比：除 `work/builds/` 外**零新增**）。

---

## 1. 产物布局（本轮收敛后）

```
work/builds/<版本>/
  <版本>.iso                      完整盘（1.65 GB）
  build_info.json                 版本/基底/sha256/时间 + text_snapshot 段 + font_dump 段
  text/                           ★ 本版本文本快照
    <版本>_text.csv               完整 CSV（UTF-8 BOM + CRLF，Excel 改 text_edited 后可重新构筑）
    <版本>_text.txt               单行副本：每行 `id<TAB>正文`（换行 \n；已剥离 {WRAP}）
    <版本>_text.meta.json         dump 元信息（格式版本 / 源盘 sha256 / 各资源条数）
  font/                           ★ 本版本字库 dump（新增）
    <版本>_font_atlas.png         图集 1024×512 → 2048×1024（2 倍最近邻），黑=墨 白=空
    <版本>_font_ft.csv            FT 记录表（3 个 face 全部 544 条）
    <版本>_font_charset.csv       字符集清单（1456 个字符）
    <版本>_font_summary.json      统计 + 各文件 sha256（不含时间戳）
  temp/                           注入报告 / 全量文本总表 / 模拟器截图日志
    inject<N>_report.json
    textdump/all_text.xlsx|.csv|summary.*
  extract/ft_font_res.bin  font_new_font_revised.bin  MENU.IMG
```

### 1.1 变与不变（相对 round31–35）

| 位置 | round35 | 现在 | 说明 |
|---|---|---|---|
| `<版本>_text.csv/.txt/.meta.json` | 版本文件夹**根** | `text/` 子目录 | 更清爽；工具两种位置都认（见 §5.1） |
| `work/text_versions/**`（归档 + INDEX.md） | 每次构筑都写 | **不再写** | 新快照只在版本文件夹；该目录已无任何工具依赖，**可整目录删除** |
| `work/tmp/**`（diff 工具的临时 dump） | `tempfile.mkdtemp(dir=work/tmp)` | **系统临时目录** | `diff_text_versions.py` 只读、不留痕 |
| `work/` 其它子目录 | 旧脚本可能写 | **一律不写** | 实跑断言：零新增（§4.2） |
| `font/` 四件套 | 无 | **新增，默认开** | `--no-font-dump` 可关 |
| `temp/`、`extract/`、`<版本>.iso`、`build_info.json` | 同 | 同 | 仍在版本文件夹内 |

---

## 2. 字库 dump 详解（`tools/iso_build/dump_font.py`）

**只读**：只 mmap 读 ISO，绝不改动盘上字节。**可单跑**：

```powershell
& C:\ProgramData\anaconda3\python.exe tools/iso_build/dump_font.py `
    --iso work/builds/GR_ZH99_snap/GR_ZH99_snap.iso `
    --out work/builds/GR_ZH99_snap/font --prefix GR_ZH99_snap [--scale 2] [--no-png]
```

口径**全部复用 `tools/text_csv/tcslib.py`**（`parse_ft_faces` / `parse_pak_records` /
`atlas_cell_xy` / `GlyphCache` / 网格常量），**没有重新逆向任何格式**：

* 字表 `MENU.IMG #4 FONT.RES`（槽 @0xB9120，存 4421 B → LZO 展开 5942 B，3 个 face）
* 图集 `MENU.IMG #3 COMMON.PAK` 的 `new_font_revised`（1024×512、psm=0x14 PSMT4、像素 @PAK+0x146D）
* `texel 0 = 墨`（黑）/ 非 0 = 空（白）；PSMT4 每字节 2 texel（偶 x 低 nibble）
* 对偶码走网格公式 `slot=(b1-0xA1)*94+(b2-0xA1)`、`row=slot//62`、`x=4+16*col`、
  `y=2+16*(row+3*[row>=12])`；ASCII/单字节走 FT 记录表（`idx=code-0x20`，采样有 +4/+2 实测偏置）

### 2.1 `<VER>_font_atlas.png`（一眼看字形）

整张图集的二值化视图（黑=有墨），默认 **2 倍最近邻**放大到 2048×1024、**约 46 KB**。
不是全黑/全白 —— 实测 99136 / 524288 texel 有墨（18.91%），肉眼可见完整汉字网格、
底部的 ASCII 带（`A-Z 0-9` 与符号）以及小写字母处的**空白格**。

### 2.2 `<VER>_font_ft.csv`（码位 → 图集位置）

列：`face,face_name,index,code,advance,u0,v0,u1,v1,slot_x,slot_y,ink_px,has_ink`

| 列 | 含义 |
|---|---|
| `face` / `face_name` | face 序号（0/1/2）与名字（`large` / `default` / `huge`） |
| `index` | 记录序号（0..nrec-1）；`code` = 该记录对应码位 = `index + 0x20` |
| `advance` | 记录第 2 字节（字宽；现役 = 8） |
| `u0,v0,u1,v1` | 记录矩形（u 水平 / v 垂直）—— 与盘上字表逐字节一致（§4.3 已逐条核对） |
| `slot_x,slot_y` | 引擎实际采样处 = `u0+4, v0+2`（实测偏置，见 `FONT_CURRENT_STATE.md`） |
| `ink_px` | 记录矩形内的墨点数 |
| `has_ink` | 该码位**画得出来**吗（记录矩形 / `+4,+2` 矩形 / ±邻域 三处任一有墨） |

### 2.3 `<VER>_font_charset.csv`（本盘字符集清单）

列：`char,unicode,kind,bytes_hex,slot,cell_x,cell_y,has_glyph,note`

| 列 | 含义 |
|---|---|
| `kind` | `ascii`（0x20..0x7E）/ `single`（单字节码）/ `pair`（对偶码）/ `icon`（未映射控制字节） |
| `bytes_hex` | 盘上字节（`AF` / `A2F6` / `B1`…） |
| `slot` | 网格槽号（只对 `pair` 有意义） |
| `cell_x,cell_y` | 字形左上角：`pair` = 网格公式；`ascii`/`single` = FT 记录矩形左上 |
| `has_glyph` | 盘上真有字形吗（`tcslib.GlyphCache` 的原判据） |
| `note` | 人话说明（FT 记录号、网格坐标、死 pair 警告、缺字形原因…） |

★ 私有区占位字符按工程约定写成 `{{BTN:XXXX}}` 标记（CSV 里**不允许**出现 Excel 看不见的私有区字符）。

### 2.4 `<VER>_font_summary.json`（统计与指纹）

`faces` / `counts`（face 数、记录数、字符数、有字形、缺字形、各类计数）/
`font_res`（槽偏移、存储/展开长度、sha256）/ `atlas`（尺寸、psm、像素 sha256、墨点数）/
`grid`（网格配方）/ `files`（**各文件路径 + 字节数 + sha256**）/ `png`（放大倍数、墨像素数）/ `notes`。

★ **不含时间戳** ⇒ **同一个 `font/` 目录**下对同一 ISO 两次 dump，四个文件 sha256 完全相同（§4.5 实测）。
生成时间只写在 `build_info.json::font_dump.generated` 里。
（`summary.json` 里记了各文件的输出路径 ⇒ 换目录 dump 时它的 sha 会变；另三个文件与目录无关。）

### 2.5 `build_info.json::font_dump` 段

```json
"font_dump": {
 "dir": "work/builds/GR_ZH99_snap/font",
 "generated": "2026-10-10 14:23:07",
 "deterministic": "四件套不含时间戳; 同一 ISO 两次 dump 的 sha256 完全相同",
 "atlas_png":     {"path": ".../font/GR_ZH99_snap_font_atlas.png",   "bytes": 46805,  "sha256": "6bd21a04…"},
 "ft_csv":        {"path": ".../font/GR_ZH99_snap_font_ft.csv",      "bytes": 25901,  "sha256": "d759fdf7…"},
 "charset_csv":   {"path": ".../font/GR_ZH99_snap_font_charset.csv", "bytes": 122891, "sha256": "07395960…"},
 "summary_json":  {"path": ".../font/GR_ZH99_snap_font_summary.json","bytes": 3932,   "sha256": "3240c5b4…"},
 "atlas": {"width": 1024, "height": 512, "psm": 20, "pixel_sha256": "bf7d5233…"},
 "faces": 3, "ft_records": 544, "chars": 1456,
 "by_kind": {"ascii": 95, "single": 76, "pair": 1281, "icon": 4},
 "has_glyph": 1423, "missing_glyph": 33, "missing_glyph_chars": ["^","_","`","a", … ,"欣","袁"],
 "ft_records_with_ink": 451, "ft_res_sha256": "a2e13097…"
}
```

---

## 3. 代码改动清单

| 文件 | 改动 |
|---|---|
| `tools/iso_build/dump_font.py` | **新增**：字库 dump（四件套），只读、可复现、可单跑、可 import |
| `tools/iso_build/make_build.py` | 文本快照改写到 `text/`；**删掉** `work/text_versions/**` 归档与 `INDEX.md` 生成；新增 `--no-font-dump` 与 `font_dump` 段；`--inject-csv` 支持版本名/版本目录/新旧两种路径；头部文档与产物清单重写 |
| `tools/text_csv/diff_text_versions.py` | 默认查找位置改为 `work/builds/<版本>/text/`（并保留旧布局与 `work/text_versions/` 只读兜底）；临时 dump 从 `work/tmp/` 改到**系统临时目录**；`--list` 同时列出新旧位置并标注 |
| `docs/BUILD_TOOLCHAIN.md` | §2 工具链与 §2.1 产物布局、§8.2/8.3/8.4/8.5 路径、§8.6 限制、**新增 §8.7 字库 dump** |
| `tools/text_csv/FORMAT.md` | §0 三步上手（路径改到版本文件夹 `text/`）、**新增 §6.5 字库 dump 怎么看**、§9 快照路径与 `{WRAP}` 视图差异、§10 失效路径注记 |

**没有改**：`dump_text_csv.py`、`inject_text_csv.py`、`tcslib.py`、`iso_tools.py`、现役盘 `GR_ZH91.iso`、
英文基线 `GR_EN_ORIG.iso`、`GR.IMG`/`MENU.IMG` 的任何条目偏移；**没动 git**。

---

## 4. 实跑验证（全部真实执行，输出摘录）

### 4.1 构筑测试版本 `GR_ZH99_snap`（基底 = 现役盘 `GR_ZH91`）

```
> python tools/iso_build/make_build.py GR_ZH99_snap --from work/builds/GR_ZH91
[base] work/builds/GR_ZH91\GR_ZH91.iso (sha 42d04a4f61982a00...)
[iso] ...\work\builds\GR_ZH99_snap\GR_ZH99_snap.iso (1.65 GB)
[extract] 字表 4421B + 字库记录 263244B + MENU.IMG 55MB → extract/
[textdump] CSV: ...\temp\textdump\all_text.csv (7716 行)
[textdump] xlsx 写出: ...\temp\textdump\all_text.xlsx (7716 行, 7 个 sheet)
──── [text-snapshot/dump] ... dump_text_csv.py --iso ...\GR_ZH99_snap.iso --out ...\text\GR_ZH99_snap_text.csv
  [ok] 全部 2261 行逐字节往返一致 ✓
  [ok] 已扫描 2261 行 × 4 个文本列的 389347 个字符: PUA 私有区 0 个 / 不可见控制字符 0 个 ✓
[text-snapshot] 2261 条 / 长段 313 / 65716 字符 (中文 45732)  — 耗时 2.8s
[text-snapshot] CSV work/builds/GR_ZH99_snap/text/GR_ZH99_snap_text.csv (844 KB)  sha b9b9cbb96a73…
[text-snapshot] 都在版本文件夹内: work/builds/GR_ZH99_snap/text/

──── [font-dump] 字库 dump → work/builds/GR_ZH99_snap/font/
[font] 字表 FONT.RES #4 @0x5ECE8120: 存 4421 B → 展开 5942 B, 3 个 face
[font] 图集 COMMON.PAK #3 new_font_revised: 1024×512 psm=0x14, 墨 99136/524288 texel (18.91%)
[font] 记录 544 条 (有墨 451 / 无墨 93) → work/builds/GR_ZH99_snap/font/GR_ZH99_snap_font_ft.csv
[font] 字符 1456 个 (ascii 95 icon 4 pair 1281 single 76) — 有字形 1423 / 缺字形 33
[font] 图集图 2048×1024 (2 倍) 46 KB → ...\font\GR_ZH99_snap_font_atlas.png
[info] work/builds/GR_ZH99_snap/build_info.json
[done] 本版本文本副本: work/builds/GR_ZH99_snap/text/GR_ZH99_snap_text.txt (2261 条 / 65716 字符, 中文 45732)
[done] 本版本字库 dump: work/builds/GR_ZH99_snap/font (face 3 / 记录 544 / 字符 1456, 缺字形 33)
[status: completed, exit code: 0]
```

版本文件夹实测内容（全部产物都在里面）：

```
      1,648,164,864  GR_ZH99_snap.iso
             58,300,882  extract\MENU.IMG
                263,244  extract\font_new_font_revised.bin
                  4,421  extract\ft_font_res.bin
                  3,376  build_info.json
                864,335  text\GR_ZH99_snap_text.csv
                202,070  text\GR_ZH99_snap_text.txt
                  3,455  text\GR_ZH99_snap_text.meta.json
                 46,805  font\GR_ZH99_snap_font_atlas.png
                 25,901  font\GR_ZH99_snap_font_ft.csv
                122,891  font\GR_ZH99_snap_font_charset.csv
                  3,932  font\GR_ZH99_snap_font_summary.json
              1,148,650  temp\textdump\all_text.csv
              1,022,102  temp\textdump\all_text.xlsx
                    732  temp\textdump\summary.txt
                    371  temp\textdump\summary.json
```

`build_info.json` 字段齐全：`version / base / patch / inject_csv / iso_sha256 / iso_bytes / built /
text_table / text_snapshot{csv,txt,meta,sha256,entries,long,chars,cjk_chars,resources} /
font_dump{dir,atlas_png,ft_csv,charset_csv,summary_json,counts…}`（见 §2.5）。

### 4.2 ★ 目录收敛断言：`work/` 除 `work/builds/` 外**零新增**

用同一份脚本在**构筑前 / 全部验证操作后**各扫一遍 `work/`（排除 `work/builds/`，目录与文件都算）：

```
构筑前 (work/ 除 builds/ 外): ['builds/']
全部操作后 (work/ 除 builds/ 外): ['builds/']
★ 新增: (零新增 ✓)   消失: (无)
```

⇒ 构筑（含文本 dump / 文本总表 / 字库 dump / 注入）**没有在版本文件夹以外产生任何一个文件或目录**，
`work/text_versions/`、`work/tmp/` 也确认没有被重新创建。

### 4.3 字库 dump 正确性抽查（独立复核，用 `tcslib` 重解析同一张盘）

复核脚本独立于 dump 代码：**重新**用 `tcslib.parse_ft_faces` / `GlyphCache` 解析同一 ISO，
再与 CSV/PNG 逐项比：

```
[ok] FT CSV 行数 544 == FT 记录数 544
[ok] FT CSV 每个 face 的行数 {'large': 224, 'default': 224, 'huge': 96} == 磁盘各 face 记录数
[ok] FT CSV 逐条与磁盘字表一致 (face/码位/advance/矩形/采样点; 不一致 0 条)
[ok] 抽查 的: CSV kind=single bytes=AF has_glyph=1 cell=(16,178) ⟷ tcslib 有字形 (FT rec=(16,178) 墨(邻域判定)=有)
[ok] 抽查 好: CSV kind=pair  bytes=A2F6 has_glyph=1 cell=(884,34) ⟷ tcslib 有字形 (grid slot=179 cell=(884,34) 墨=61)
[ok] 抽查 攻: CSV kind=pair  bytes=A1F4 has_glyph=1 cell=(340,18) ⟷ tcslib 有字形 (grid slot=83  cell=(340,18) 墨=68)
[ok] PNG 尺寸 2048×1024 (2 倍放大) — 实际 (2048, 1024)
[ok] PNG 既非全黑也非全白: 黑(墨) 396544 px / 白(空) 1700608 px (占 18.91% 是墨)
[ok] charset CSV 行数 1456 == ascii 95 + single 76 + pair 1281 + icon 4
★ 复核结论: 全部通过 ✓
```

另外与权威文档交叉印证（`docs/FONT_CURRENT_STATE.md` 的实测表）：

```
default face, code 65 ('A') → 记录 (0, 8, 256, 452, 264, 468)   ← 文档记的正是这四个值 ✓
huge face 96 条、large/default 各 224 条                        ← 与文档 224/224/96 一致 ✓
图集 psm=0x14(PSMT4)、1024×512、像素 @COMMON.PAK+0x146D        ← 与文档一致 ✓
字形网格 NCOL=62 / CW=CH=16 / Y0=2 / SKIP_ROW=12 / SKIP_ROWS=3 ← 与文档一致 ✓
```

缺字形的 33 个（可解释，非 bug）：`^ _ \` a-z | ~`（小写 ASCII，字形在别的 face，实机可读）
+ `欣` `袁`（只有 lead≥0xAE 的**死 pair**、网格格实测是空的）。

### 4.4 `--no-font-dump` 生效 + 顺带验证「上一轮 CSV → 下一轮注入」链路

```
> python tools/iso_build/make_build.py GR_ZH98_nofont_snap --from work/builds/GR_ZH91 `
      --inject-csv work/builds/GR_ZH99_snap/text/GR_ZH99_snap_text.csv --no-font-dump --no-textdump
（无任何 [font] 输出；exit 0）

font/ 目录          : 不存在 ✓ (--no-font-dump 生效)
build_info.font_dump: None ✓
build_info.inject_csv: [{csv: .../GR_ZH99_snap/text/GR_ZH99_snap_text.csv,
                         report: .../GR_ZH98_nofont_snap/temp/inject1_report.json,
                         iso_sha256: 42d04a4f…}]
产物 ISO sha256     : 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
基线 GR_ZH91 sha256 : 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88  ⇒ 逐字节相同 ✓
```

⇒ ① `--no-font-dump` 确实不产出 `font/`；② 新布局的 `text/<版本>_text.csv` 直接喂给
`--inject-csv` 可用，且"一个字不改直接注入 ⇒ 产物与基底 sha256 完全相同"这条既有性质仍成立。
（该一次性验证版本 `GR_ZH98_nofont_snap` 已由本次操作**删除**，`work/builds/` 只剩
`GR_EN_ORIG` / `GR_ZH91` / `GR_ZH99_snap`。）

### 4.5 字库 dump 可复现性

同一张盘 `GR_ZH91.iso`，向**同一目录**连跑两次 `dump_font.py`，逐文件比 sha256：

```
文件                                    第一次        第二次        相同?
GR_ZH91_font_atlas.png                 6BD21A043930  6BD21A043930  True
GR_ZH91_font_ft.csv                    D759FDF7810C  D759FDF7810C  True
GR_ZH91_font_charset.csv               073959605E3D  073959605E3D  True
GR_ZH91_font_summary.json              BE91FEA88013  BE91FEA88013  True
```

并且**独立 dump 现役盘**得到的三个内容文件（PNG / ft.csv / charset.csv），与 `GR_ZH99_snap`
（同一份盘内容）里的对应文件 sha256 完全相同（`6bd21a04…` / `d759fdf7…` / `07395960…`）
⇒ 换目录、换调用方式都不影响结果。

⚠ 唯一的例外：`_font_summary.json` 里**记了各文件的输出路径**，所以把它 dump 到**另一个目录**
得到的 summary.json 内容不同（sha 不同）。同一版本、同一个 `font/` 目录下重复 dump 则完全一致 ——
这正是实际用法（一个版本一个 `font/`）。

### 4.6 `diff_text_versions.py` 用版本文件夹路径工作正常

```
> python tools/text_csv/diff_text_versions.py --list
  work/builds/GR_ZH91/GR_ZH91_text.csv                    ← 旧布局(版本文件夹根)，兜底也认
  work/builds/GR_ZH99_snap/text/GR_ZH99_snap_text.txt     ← 新布局
  work/builds/GR_ZH99_snap/text/GR_ZH99_snap_text.csv

> python tools/text_csv/diff_text_versions.py work/builds/GR_ZH91/GR_ZH91_text.csv work/builds/GR_ZH99_snap/text/GR_ZH99_snap_text.csv
# A = GR_ZH91          ← work/builds/GR_ZH91/GR_ZH91_text.csv          （旧布局，兜底也认）
# B = GR_ZH99_snap     ← work/builds/GR_ZH99_snap/text/GR_ZH99_snap_text.csv   （新布局）
只在 A 消失 : 0 条 / 只在 B 新增 : 0 条 / 内容不同 : 0 条 / 内容相同 : 2261 条
字符数 75004 → 75004 (+0)   中文字 45732 → 45732 (+0)          ⇒ 测试版本 = 现役盘内容，零差异 ✓

> python tools/text_csv/diff_text_versions.py GR_ZH99_snap <把 LANG:G058.I195 改成「顺序ZZZ」的 CSV>
两边都有、内容不同 : 59 条
[~] LANG:G058.I195   (A 1 行 → B 1 行)
    - 顺序
    + 顺序ZZZ                                                  ⇒ 真差异能被准确报出 ✓
```

（那 59 条里 58 条是"CSV 带 `{WRAP}` 建议断点 / TXT 已剥离"的**视图差异**，
见 `FORMAT.md` §9；两边同格式对比时为 0 条。）

也验证了 `diff_text_versions.py` 直接吃 ISO 的路径：`diff_text_versions.py GR_ZH91 GR_ZH99_snap`
（`GR_ZH91` 当时没有快照 ⇒ 自动临时 dump 它的 ISO）→ 临时文件落在**系统临时目录**，用完即删，
`work/` 下没有 `tmp/` 出现。

---

## 5. 兼容性

1. **两种文本快照位置都认**：新构筑写 `text/`；`diff_text_versions.py` 与
   `make_build.py --inject-csv` 都按 `text/<版本>_text.*` → `<版本>_text.*`（旧布局）→
   `work/text_versions/<版本>_text.*`（更早归档，**只读**）的顺序查找。
   ⇒ 老的版本文件夹（例如 `work/builds/GR_ZH91/` 里那份版本文件夹根目录的 CSV）照旧能用。
2. `--inject-csv` 现在也接受**版本名**（`--inject-csv GR_ZH92`）或版本目录，用户不用记子目录。
3. `--no-text-snapshot` / `--no-textdump` / `--verify-img` / `--expand-entry` 行为未变。
4. 字库 dump 失败**不会**让构筑失败（它是只读旁证；盘已产出）——`build_info.json` 记
   `font_dump_error` 并打印单跑命令。文本快照失败仍按原语义让构筑非 0 退出。

---

## 6. 已知限制

1. **`has_glyph` 对 ASCII/单字节只查 `FONT.RES` 的 default face**（`tcslib.GlyphCache` 的既有口径）
   ⇒ 小写 `a-z`、`^ _ \` | ~` 会标成"缺字形"，但引擎的 ASCII 单字节路径在别的 face 有字形、
   实机可读（`FORMAT.md` §6.4）。**这一类只当告警看**；汉字（单字节/对偶）的判定与注入器的
   预检完全同源，可以直接信。
2. `kind=icon` 是"字符表未映射、引擎直接给 UV 画图标/特殊符号"的字节（现役 4 个：
   `0xB1 0xB5 0xE7 0xF1`）。**语义仍未逆向**，只写码位不编键名；`0xE7/0xF1` 很可能是
   重音字母 `ç/ñ` 而非按键（round34 旁证）。
3. 只 dump **MENU.IMG 侧**的字库（引擎只读这一份；GR.IMG 侧是死拷贝）。
4. PNG 是**纯二值化**、没画网格线（保证"黑=墨"可逐像素反推）；网格几何在
   `summary.json::grid` 里，看图时请对照它。
5. `_font_ft.csv` 的 `slot_x/slot_y` 是"记录矩形的绘制采样原点（+4/+2 偏置）"，
   **不是**对偶码的网格槽号（网格槽号只在 `_font_charset.csv` 的 `slot` 列）。
6. 字库 dump 反映的是**图集与记录表的静态内容**：它能回答"这个字盘上有没有墨"，
   但**不能**替代实机验证（渲染路径、颜色、居中偏移等仍需模拟器截图）。
7. `_font_summary.json` 里记了各文件的**输出路径** ⇒ 换一个 `--out` 目录 dump，summary 的 sha256
   会变（另外三个文件不受影响）。同一版本的 `font/` 目录下重复 dump 则四个文件全同。
8. 文本快照仍是 dump 的**渲染视图**（长段带 `{WRAP}` 提示），不是字节级镜像；
   字节级证据请用 `inject_text_csv.py` 的「全盘差异窗口」断言。
9. `dump_font.py` 内部为"所有 face 的判墨"临时替换了 `GlyphCache` 的记录表
   （复用它的 `_check_record` 私有方法）—— 这是**同仓库内复用**，不是重新实现；
   若将来 `tcslib` 改了该方法签名，需要同步 `ft_rows()`。

---

## 7. 复现命令（给工程侧）

```powershell
$py = 'C:\ProgramData\anaconda3\python.exe'
# 1) 版本构筑（默认就出 text/ + font/）
& $py tools/iso_build/make_build.py GR_ZH99_snap --from work/builds/GR_ZH91
# 2) 只看字库（不构筑）
& $py tools/iso_build/dump_font.py --iso work/builds/GR_ZH99_snap/GR_ZH99_snap.iso `
      --out work/builds/GR_ZH99_snap/font --prefix GR_ZH99_snap
# 3) 跨版本对比
& $py tools/text_csv/diff_text_versions.py GR_ZH91 GR_ZH99_snap
```

---

## 8. 给用户的一句话

**以后每构筑一轮，`work/builds/<版本>/` 里就自带这一版的文本表（`text/`，Excel 直接改）
和字库快照（`font/`，打开那张 PNG 就能一眼看到哪些字有、哪些是空白），
所有东西都只在这个版本文件夹里，不会再往 `work/` 别处散落文件。**
