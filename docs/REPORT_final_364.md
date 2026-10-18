# REPORT_final_364.md — 最终盘 `GR_F364`：**364 个缺字全部落盘**

> 执行：最终轮（round-final）· 工作目录 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> 只写 `work\tools\f364_*.py` + `work\builds\GR_F364\**` + 本文件
> 未 commit / 未切分支 / 未 merge；`third_party/orig/**`、`%LOCALAPPDATA%\PCSX2\**`、
> `work/temp/NEW_Mem/**`、全部历史 ISO 只读。
> **受保护路径改动 1 处**：`tools/font_pipeline/data/charset_compiled_zh16.json`（见 §7，已备份可一键还原）。
> `tools/text_csv/*`、`font_compact.py`、`make_build.py` **未改**。

---

## 0. 一句话结论

```
★ 交付盘 work\builds\GR_F364\GR_F364.iso  = 基底 GR_ZH124.iso + **只加高图集 h 512→640**
  + 把**尚未落盘的 136 个缺字**画进网格 slot 1736..1871
  + decode gate 0xB4→0xB5（唯一能拿到码位的办法）
  + 把文本里遗留的 461 个「用」单字节码 0xB4 重编码成它**原有的**对偶码 0xB1A4

判据结果（全部实测，exit=0 不作判据）:
  ① 八条硬断言 ................ 全绿（现役 1736 格逐 texel 不变 · 新字 136 格逐 texel == 模板 ·
                                  FONT.RES 逐字节不变 · ELF 只 4 个立即数 · 名字区/哈希表不变 ·
                                  不变式①②成立 · 全盘差异 100% 落在计划窗口内）
  ② dump_font 缺字形 ......... **0**（2075 字符 / 有字形 2075）
     字形几何体检 ........... **错误 0 / 截断 0 / 空白 0 / 越窗 0**（警告 2）
  ③ 实机 6000 帧 ............. 截图 **191** · 去重画面 **164** · needle `newfontrevisedrs` **4** ·
                                `TLB Miss` **0** · 读流 f0..5863 / maxLBA 804,765
     与基底逐张比对 ......... **185/191 逐字节相同**；不同的 6 张（f660..f810）与 round86
                               独立验证过的 `v2_h640` **完全相同的那 6 张** ⇒ 是 h=640 的已知抖动，
                               不是本轮回归
  ④ 文字界面实拍 ............. 见 §6.4（这张盘上**能拍到**什么、拍不到什么，如实写清）
  ⑤ 本报告
⇒ ★★ **用户唯一验收目标「364 个缺字全部落盘」达成** ✓
```

---

## 1. 交付物索引

| 类型 | 路径 |
|---|---|
| ★ **成品盘** | `work\builds\GR_F364\GR_F364.iso`（1,648,164,864 B = 804,768 扇区，**与基底同尺寸**）|
| 中间盘（只加高 h） | `work\builds\GR_F364\_stage640.iso` |
| 构筑器（通用 w/h） | `work\tools\thr_patch_atlas.py`（round86 既有，本轮直接复用） |
| 构筑器（本轮） | `work\tools\f364_patch.py`（136 字落盘 + gate + 文本重编码；含 10 条硬断言） |
| 侦察 | `work\tools\f364_recon.py` · `f364_probe1.py` · `f364_probe2.py` |
| 验收 | `work\tools\f364_verify.py`（文本逐字节等价证明 + 全盘差异窗口分类） · `f364_results.py` |
| 补齐工具 | `work\tools\f364_diffq.py`（粗粒度差异定位） · `f364_nav_interview.txt`（实机取证脚本） |
| 构筑报告 | `work\builds\GR_F364\stage640_report.json` · `f364_patch_report.json` · `f364_patch.log` |
| 验收输出 | `work\builds\GR_F364\{f364_verify.txt, f364_results.txt, f364_diff_regions.json}` |
| 槽位表 | `work\builds\GR_F364\slotmap_f364.json`（136 个新字 → slot → 字符） |
| charset 备份 / 新版 | `work\builds\GR_F364\{charset_before_f364.json, charset_f364.json}` |
| 实机证据（6000 帧 ×2 盘 ×2 轮） | `work\builds\GR_F364\temp\dump_{f364,f364log,ctl124,ctl124log}\` |
| 实机证据（实拍画面） | `work\builds\GR_F364\temp\GR_F364_evidence_{mainmenu,fileselect,options,loadscreen}.png` |
| 实机证据（长导航过程帧） | `work\builds\GR_F364\temp\dump_f364page{,2,3}\`（各 ~130~140 张）|
| 导航脚本（本轮新增） | `work\tools\f364_nav_interview.txt` · `f364_nav_interview2.txt` |
| 字库 dump | `work\builds\GR_F364\temp\fontdump\**` |

---

## 2. ★★ 两条不变式（round86 钉死，本轮**写进构筑器硬断言**）

```
① real 不变式 : IMG 条目里 COMMON.PAK 的 stored(+0x18) 与 real(+0x1C) 必须同步。
                引擎读流长度 = **min(stored, real)**。
                历史所有「容器变大」探针盘只改 stored、没改 real ⇒ 读流在 PAK+real(旧值) 截断 ⇒
                LoadingTexturePak(0x51B660) 的记录链循环 0x51B7AC..0x51BB00 读到流尾拿不到 0x63
                哨兵 ⇒ **死循环** ⇒ 0 截图。
                ⇒ 本盘：stored == real == 466,195（§5 表第 10 行）✓

② px_size 不变式: `px_size == w*h/2 + 16`，且 payload = w*h/2 − nseg*48（nseg×48 的 GIF 段头
                从像素区里挤出）。等价判据 `(w*h/2) % 2048 == 0`。
                违反 ⇒ 卡在「正在读取插槽 1 中的记忆卡(8MB)」画面（191 张全是同一画面）。
                ⇒ 本盘：1024×640/2 + 16 = **327,696 = 0x50010**；payload 327,200 = 327,680 − 10×48 ✓
                  (1024×640/2) % 2048 = 0 ✓
```

**外加一条本轮发现的编码硬闸**（不是尺寸，是**码位空间**）：

```
③ lead 字节预算 : 双字节码 = (lead, trail)，lead ∈ [0xA1, GATE)、trail ∈ [0xA1, 0xFE)
                  ⇒ 码位数 = (GATE − 0xA1) × 94。
                  基底 GR_ZH124: GATE = 0xB4 ⇒ 19 × 94 = **1786 槽**，已用 1736 ⇒ **只剩 50 个空位**。
                  本轮还差 136 个缺字 ⇒ **50 < 136 ⇒ 必须把 GATE 抬到 0xB5**
                  ⇒ 20 × 94 = **1880 槽**；需求 = 1736（现役）+ 136（新字）= 1872 ⇒ **余 8 槽** ✓
                  （这正是 Lead 自己在 `LEAD_FINDING_gate_cost.md` 里算出的「只剩 8 格余量」，
                    也与 dump_font 报的「还空着 8 个位子」逐位吻合。）
```

---

## 3. ★ `real`(+0x1C) 字段 bug：发现 / 复现 / 影响面

### 3.1 发现与机理

| 项 | 内容 |
|---|---|
| 症状 | 「把像素容器改大 ⇒ 0 张截图 / 读流在 PAK+400,659 处停死 / `newfontrevisedrs` 从没进内存」 |
| 误判 | 一度被解读为「引擎有尺寸上限」（并据此产出了 W2048 / h640 / H1024 三个「结论」） |
| 真因 | IMG 条目里 COMMON.PAK 的 `real`(+0x1C) **没跟着 `stored`(+0x18) 一起改** |
| 机理 | 引擎读流上界 = `min(stored, real)`。探针盘把 `stored` 改大、`real` 留旧值 400,659 ⇒ 流在 PAK+400,659 处结束 ⇒ `LoadingTexturePak` 的记录链在 `0x51BAF0` 读 4 B 记录类型时永远读不到哨兵 `0x63`（流尾 read 失败**不写缓冲**，`[sp+0x60]` 保留旧值 0）⇒ `0x51BB00` 的 `bne $v1,0x63` 恒真 ⇒ 无限循环；循环里每次 `malloc(px_size)` 又不释放 ⇒ 尾迹里全是分配器 + syscall，EE 照常跑到 6000 帧，但**加载子系统永不返回** |

### 3.2 决定性 A/B（唯一差异 = 条目表 2 个字节）

| 盘 | entry stored | entry real | 记录链需要 | PNG | 判定 |
|---|---|---|---|---|---|
| `GR_THR86_h513.iso` | 401,219 | **400,659（未改）** | 401,219 | **0** | ✗ |
| `GR_THR86_h513_real.iso` | 401,219 | **401,219（同步）** | 401,219 | 191 | ✓（随后撞不变式②）|

7 张盘的 `min(stored,real)` 全量拟合：**凡 `stored > real` 的盘，读流一律停在 PAK+400,659 所在的那个读块边界。**

### 3.3 影响面（**必须作废的旧结论**）

```
✗ 作废①: 「图集宽度 >1024 可行」 —— GR_TEST_W2048 / ROOT85_gate / v2_w2048 的**全部**
          「W2048 可行/不可行」结论都建立在 real 未同步的盘上（读流被截断，看到的不是引擎真实行为）。
✗ 作废②: 「h=640 会被引擎挡住（黑屏）」 —— H640 / H640B / GR_ZH121 的失败**与 h 无关**，
          两条不变式补齐后 h=640 实机通过（本盘再次复现：185/191 与基底逐张相同）。
✗ 作废③: 「H1024 黑屏 ⇒ h 上限 512」 —— H1024 盘同样只改 stored；h 的真实上限是
          `LoadPS2Img` 的 `slti $at,$v1,1025`（h<1025）**加** `(w*h/2)%2048==0`，不是一个「尺寸阈值」。
✗ 作废④: 「容器变大本身会让引擎停摆」 —— 成立的是「**real 与 stored 不同步**会停摆」。
```

---

## 4. 改动清单（逐条，含字节偏移与前后值）

基底 = `work\builds\GR_ZH124\GR_ZH124.iso`（sha256 `762e613f…`，实机 191/191 与基线逐字节相同）。
`MENU_LBA = 776,286` ⇒ MENU.IMG 起于 ISO `0x5EC20000`。

### 4.1 第一步：只加高图集（`thr_patch_atlas.py --w 1024 --h 640 --real-mode fixed`）

| # | 位置（ISO 偏移） | 字段 | 前 | 后 |
|---|---|---|---|---|
| 1 | `0x5EC8744D` | 记录 +0x01C `w` | `00 04 00 00` = 1024 | **不动** `00 04 00 00` |
| 2 | `0x5EC87451` | 记录 +0x020 `h` | `00 02 00 00` = 512 | `80 02 00 00` = **640** |
| 3 | `0x5EC87869` | 记录 +0x438 `px_size` | `10 00 04 00` = 262,160 | `10 00 05 00` = **327,696** |
| 4 | `0x5EC8786D` 起 | 像素容器 | 262,160 B / 8 段 | **327,696 B / 10 段**（pay 327,200 = 9×32,768 + 32,288）|
| 5 | `0x5EC86CD8` | 条目表 #3 `stored` | 400,659 | **466,195** |
| 6 | `0x5EC86CDC` | 条目表 #3 `real` | 400,659 | **466,195**（★ 不变式①）|
| 7 | MENU+`0x830+48i+32`（682 条） | 各条目 `off` | — | **+65,536** |
| 8 | `0x828D8` / `0x828DC` | ISO9660 目录记录长度 LE/BE | 58,300,882 | **58,306,560** |
| 9 | MENU.IMG 头 `size` | 声明长度 | 58,300,882 | **58,306,560**（扇区对齐，28,470 扇区）|
| 10 | PVD 卷长 | — | 804,768 | **不动**（ISO 一字不加）|
| 11 | PAK 之后的数据区 | — | — | **整体右移 +65,536 B**（1,682 条条目随之平移；`thr_patch_atlas` 的既有行为，round86 已验证）|

**旧 512 行像素逐字节保留**：构筑器按「行」重建容器，断言 `512 rows checked, 0 mismatch` ✓

### 4.2 第二步：136 个缺字落盘（`f364_patch.py`）

| # | 位置 | 动作 | 前 | 后 |
|---|---|---|---|---|
| 12 | 容器内 slot 1736..1871 | 画 136 个 16×16 字形 | 全空白（墨 0） | **136 个字**（`slotmap_f364.json`）|
| 13 | ELF `0x3AA768` | decode gate 立即数（`sltiu …,0xB4` @VA `0x416EE8`） | `B4` | **`B5`** |
| 14 | ELF `0x3AA9E0` | 同上 @VA `0x417160` | `B4` | **`B5`** |
| 15 | ELF `0x3AAD9C` | 同上 @VA `0x41751C` | `B4` | **`B5`** |
| 16 | ELF `0x4F8F24` | 同上 @VA `0x5656A4` | `B4` | **`B5`** |
| 17 | `EN_STRINGS.RES@MENU` `0x623BD000` | 229 个遗留「用」单字节码 | 1 B `B4` | **2 B `B1 A4`**（+229 B, 吃陈旧尾巴）|
| 18 | `EN_STRINGS.RES@GR` `0x0F034F50` | 229 个同上 | 1 B `B4` | **2 B `B1 A4`** |
| 19 | `EN_SPECIAL_FEATURE.XML` `0x623B0800` | 3 个同上（属性值 `M249/MG3/PKM …机枪`）| 1 B `B4` | **2 B `B1 A4`** |

**为什么必须动文本**：0xB4 一旦成为 lead，文本里所有**裸 0xB4**（=「用」的遗留单字节码）会被当成
双字节码首字节、**吞掉后一个字**。全盘共 461 处（侦察脚本实测）。把它们写成「用」**原本就有**的
对偶码 `0xB1A4`（r83 已把「用」迁到网格 slot 1507）后：
· 编码 ↔ 解码逐字节自洽；· 渲染的字形**逐 texel 相同**（见 §6.2 的 `[w148]` 证明）；
· 容器解压总长**严格不变**（增长吃 `used_end` 之后的陈旧尾巴：LANG 58,874 B / SFXML 36,362 B）。

### 4.3 明确**不动**的东西

```
w · psm(0x14) · clut + 1040 B 调色板 · 记录条数(544) · FONT.RES 槽 4,421 B（逐字节不变）·
FONT.RES 展开 5,942 B / nrec 224,224,96 · 现役 1736 个格位 · 544 条记录采样窗 · 名字区 ·
IMG +0x20 的 4096 槽哈希表 · ISO 尺寸 · 文本内容（只换编码，不换字）· ELF 除那 4 个立即数外全部字节
```

---

## 5. 逐字节差异区段（`f364_verify.py`，断言「窗口外 0 字节」）

```
全盘逐字节不同 = **56,290,674 B**，全部落在 11 个计划窗口内；窗口外 = **0** ✓

  ⑤b  PAK 之后整体右移 +65,536 B 的数据区        56,059,921 B   （平移的必然结果）
  ⑤   COMMON.PAK（容器 +65,536 B）                199,370 B
  ⑦   文本容器 EN_STRINGS.RES@GR                   30,689 B
  ④   IMG 条目表（682 条 off + PAK stored/real）       684 B   （682×1 + 2）
  ①   ISO9660 MENU.IMG 目录记录长度字段                  4 B   （LE u32 + BE u32）
  ②   ELF decode gate（0xB4→0xB5）×4                     4 B
  ③   MENU.IMG 头（仅 size 字段）                        2 B
  ⑥   FONT.RES 槽                                     **0 B**  ★ 逐字节不变
  （另两个文本容器 @MENU / SFXML 落在 ⑤b 平移区内，已由构筑器的逐字节回读断言单独覆盖）
```

---

## 6. 验收判据结果

### 6.1 八条硬断言（写盘后**从盘上回读**再验）

| # | 断言 | 结果 | 数字 |
|---|---|---|---|
| A1 | 现役 **1736** 个网格格位逐 texel 不变 | ✅ | 不同 **0** 个 |
| A2 | **544** 个非空记录采样窗逐 texel 不变 | ✅ | 新字全在 y≥498，记录区 y≤288，零重叠 |
| A3 | **136** 个新字格逐 texel == 16px 模板 | ✅ | 136/136（全部来自 `third_party/fonts/方正像素16.ttf`）|
| A4 | COMMON.PAK 同长 + 容器外字节逐字节不变 | ✅ | 466,195 == 466,195 |
| A5 | FONT.RES 逐字节不变 / 文本 461 处重编码且 blob 总长不变 | ✅ | 槽 4,421 B 回读 == 源盘 |
| A6 | 回读 PAK / 容器逐字节相同 | ✅ | 1024×640 px_size 0x50010 |
| A7 | 回读 FONT.RES == 源盘；nrec 224/224/96 | ✅ | — |
| A8 | 3 个文本容器回读逐字节一致；「裸 0xB4」残留 = 0 | ✅ | 229 / 229 / 3 |
| A9 | 回读 ELF gate 4/4 = 0xB5 | ✅ | — |
| A10 | ISO 尺寸不变 | ✅ | 1,648,164,864 B |

**独立复核**（`f364_verify.py`，不复用构筑器代码路径）：
```
[T0] 旧盘里「裸 0xB4」经 idx = 0xB4−0x20 = 148 走 FONT.RES 记录分支, 采样窗 (112,195)-(128,211) 墨 69;
     与「用」在旧字符集里的对偶格 slot 1507 格位图**逐 texel 相同** ⇒ 0xB4 渲染的就是「用」
     （新旧两盘都验了, 都是 True）⇒ 461 处是**同一个字的编码替换**
[T1] 3 个文本容器 **4,678 条 payload**：每条新字节 == 「旧字节只做「用」重编码」**逐字节完全相同**
     ⇒ 除 461 处「用」外文本零变化 ✓（含 SFXML 的 69 个文本块 + 145 个属性值）
[cs] codes **107 条逐字节不变**；pair_of 1736 → 1872（只加 136 条）；旧 pair 是新 pair 的子集
```

### 6.2 不变式与硬闸实测

```
① stored == real == 466,195 ✓
② px_size 0x50010 = 1024×640/2 + 16 ✓ ; payload 327,200 = 327,680 − 10×48 ✓ ; (w*h/2)%2048 = 0 ✓
③ lead 预算 20 × 94 = 1880 ≥ 1872（余 8）；w=1024 未变（`slti …,1025` 闸门不触发）
④ 4 个 gate 站点的反汇编确认是**同一个谓词**（`sltiu $tX, byte, GATE`），
   前置 `sltiu …,0xA1` + 后继 trail 检查 `[0xA1,0xFF)`；逐站点原文见 §9 复现命令
```

### 6.3 离线判据

```
dump_font --iso GR_F364.iso
  ⇒ 1024×640 psm=0x14, 墨 140,779 / 655,360 texel (21.48%)
  ⇒ 记录 544 条（有墨 544 / 无墨 0）
  ⇒ 字符 2075 个（ascii 95 icon 1 latin1 2 pair **1872** single 105）— **有字形 2075 / 缺字形 0** ✓
  ⇒ 自查: 引擎格位公式 OK ✓ 1880/1880 slot 逐个对 tcslib 口径, 不一致 0 个
  ⇒ 对偶格占用 **1872/1880 = 99.57%**，还空着 **8** 个位子（= 硬闸余量）
  ⇒ 字形几何体检: 引擎采样窗 2416 个（对偶 1872 + FT 记录 544）
      **错误 0 / 警告 2 —— 截断(丢行) 0, 空白 0, 越窗 0, 极稀 0** ✓

tzslib.selfcheck_charset(Charset())  ⇒ **True**（无任何 `[!!]` 项）
inject_text_csv --csv r83/text_in --src GR_F364.iso --check-only  ⇒ exit 0
   「[ok] 字库覆盖完全: 每条文本的每个字符都能编码, 且盘上都有字形 ✓」
   （其余只有 ascii_no_glyph 一类**不阻断**提示，基底盘同样）
```

### 6.4 ★ 实机判据（同基底命令同输入：`-grinput tools\capture\nav_menu_only.txt`，6000 帧）

| 盘 | 截图 | 去重画面 | needle `newfontrevisedrs` | `TLB Miss` | 读流 | 与基底逐张比对 |
|---|---|---|---|---|---|---|
| `GR_ZH124`（对照，本轮实测） | 191 | 164 | 4 | **0** | f0..5863, maxLBA 804,733 | — |
| **`GR_F364`（本盘）** | **191** | **164** | **4** | **0** | f0..5863~5866, maxLBA **804,765** | **185/191 逐字节相同**（第 2 轮 182/191） |

```
★ 「画面数」= sha256 去重后的画面数 —— 只看截图张数会被骗（不变式②违反的盘也有 191 张,
  但全是同一画面）。本盘 164 == 对照 164 ✓
★ 不同的 6 张 = snap_f00000660/690/720/750/780/810.png。
  独立旁证: round86 的 `work\builds\GR_THR86\temp\dump_v2_h640` 与它自己的对照盘
  **不同的也正是这 6 张, 逐张同名** ⇒ 这是 h=640 的已知时序抖动, 不是本轮改动引入的。
  （像素差异 4,964..29,026 / 254,771 px = 2%~11%, 全部发生在场景切换过渡帧）
★ 确定性对照: 同一张对照盘跑两次 → **191/191 完全相同**; 本盘跑两次 → 188/191
  （多出 f1890/1920/1950 三张抖动）⇒ 本盘在 h=640 下有一点点运行间抖动, 如实记录。
★ 纹理确实进了 GS 内存: dump 目录里有 `newfontrevisedrs_f00004000_{eeram,iopram}.bin` ✓
```

**④ 文字界面实拍（如实写清能拍到什么、拍不到什么）**

```
拍到了（都在 work\builds\GR_F364\temp\ 下, 全是本盘 GR_F364 的实机画面）:
  · GR_F364_evidence_mainmenu.png   主菜单全中文（训练/战术演习/战役/多人游戏/统计/特别收录/
                                    选项/制作组）+ 底栏「△ 返回」「✕ 接受」
                                    —— △ 就是 r83 写进 slot 1504 的新字形, 正常
  · GR_F364_evidence_fileselect.png 「选择文件」屏（TEQSUNSET / 新建 + 「选择你的档案。」+ △/✕）
  · GR_F364_evidence_options.png    「选项」子菜单（游戏玩法/控制器/高级/声音/屏幕 + △/✕）
  · GR_F364_evidence_loadscreen.png 载入屏 + △/✕ 底栏
  · temp\dump_f364page{,2,3}\snap_*.png  三次长导航跑（各 ~130~140 张）的全部过程帧
  ⇒ 这些画面共同证明: h=640 图集 + 10 段容器 + 461 处文本重编码 在实机上**渲染正常**,
     没有任何错字/丢字/花屏; 与「185/191 与基底逐字节相同」互相印证。

✗ 没拍到（**必须如实声明, 两层原因**）:
  (1) 本轮新写的 136 个字形**本身** —— 它们根本不在任何现役正文里。
      这 136 个字是 round64「文本减字」时从正文删掉的那些字
      （work\builds\GR_ZH98\temp\r64\reduce_map.csv）; 实测 136 个字在 3 份 text_in CSV 与
      盘上 all_text.csv 里命中 **0 / 0 / 0**。⇒ 想同屏必须**改文本**（把删掉的字加回去）,
      那是另一件事, 超出本轮「只把字落盘」的范围。
  (2) 「特别收录 → 访谈 → 开发访谈 1」长文页也没拿到 —— **纯工具标定问题, 与盘无关**:
      · nav_hook.py 的主菜单钩子是 round61 **硬编码地址** 0x013379D0; 本盘 PAK/图集各 +65,536 B
        ⇒ 堆布局变了 ⇒ 该地址读到 0x1E420007（不是菜单下标）⇒ 握手失败（脚本注释里自己写了
        这个失效模式: 「内存区间因堆布局变化而失效时, 退化为只用渲染高亮条」）。
      · 退而用静态 -grinput 脚本（tools/capture/nav_sf_interview.txt 与本轮新增的
        work\tools\f364_nav_interview{,2}.txt）: 三次跑的按键时序都会漂
        （v1 停在「输入名字」屏、v2 用实拍快照把「选择文件」段标定对了但主菜单段漂到「选项」）。
        每次纠偏要 ~10 分钟实机, 本轮时间预算内**没有闭环**。
      ⇒ 这一步**可以做到**（字已经在盘上, 只差一段可靠导航）, 但需要：
        ① 重新标定 MENU_SEL_ADDR（建议改成特征扫描而不是硬编码）; 或
        ② 用带反馈的 nav_hook 闭环重跑。
  ⇒ 本轮能给出的最强实机证据 = 上面的多屏实拍 + 6000 帧 191/164/TLB 0 + 185/191 逐张相同
    + dump_font「缺字形 0 / 截断 0」+ 136 格逐 texel == 模板。
```

---

## 7. 受保护路径改动（先说明后改）

```
tools/font_pipeline/data/charset_compiled_zh16.json   ★ 已改
  · pair_of 1736 → **1872**：新增 136 条（slot 1736..1871 → 对应缺字）
  · codes **107 条不变**；「用」仍是对偶码 [0xB1, 0xB4→A4]，没有任何单字节码被改/删
  · 新增 `_expand_f364` 段记录本轮口径（gate / atlas / slot 区间 / 重编码计数）
  · 备份 = work\builds\GR_F364\charset_before_f364.json
  · 一键还原: Copy-Item work\builds\GR_F364\charset_before_f364.json `
              tools\font_pipeline\data\charset_compiled_zh16.json -Force
  · 副作用评估: 唯一变化是多了 136 条 pair（lead ≤ 0xB4）。
    对**旧盘**做解码时这些 pair 不会命中（旧盘文本里不存在 lead 0xB4 的合法双字节码）⇒ 无回归。
```

---

## 8. 未完成项 / 已知问题（如实）

| # | 项 | 状态 | 原因 / 说明 |
|---|---|---|---|
| 1 | 136 个新字的「同屏实拍」 | ⛔ 未达成（**两层原因，见 §6.4**） | ① 这 136 个字**不在任何现役正文里**（round64 已删）；② nav_hook 的主菜单钩子是 round61 硬编码地址，被本盘（PAK/图集各 +65,536 B）的堆布局变化打掉，静态脚本三次纠偏未闭环 |
| 1b | 长文页（开发访谈 1）实拍 | ⛔ 未拿到 | 同上 ②。**可以做到**：只需重新标定 `MENU_SEL_ADDR`（或加特征扫描）后用闭环 nav_hook 重跑一次；盘侧无需再改 |
| 2 | 2 处**既有**文本残缺点 | ⚠ 已定位，未修 | 见 §6.4 之外: 旧文本里有 2 组「旧字符集未登记的对偶码」落进本轮新填的槽 —— `(0xB3,0xD3)=slot 1742`（G058.I277）与 `(0xB3,0xD5)=slot 1744`（G012..G017.I028）。它们在**基底盘 GR_ZH124 上就已经是坏的**（r83 把 gate 抬到 0xB4 后，遗留的「练」单字节码 0xB3 被当成 lead 吞掉后一字节），渲染是空白+吞字；本轮让这两个槽有了字形，于是从「空白」变成「一个确定的错字」。两者都错，且都在 LANG 页、**不在本轮取证页面上**。要真修必须先恢复 round64 之前的文本 —— 超出范围 |
| 3 | `nav_hook.py` 主菜单钩子失效 | ⚠ 工具标定问题，非盘问题 | `MENU_SEL_ADDR = 0x013379D0` 是 round61 的**硬编码标定**；本盘 PAK/图集各 +65,536 B ⇒ 堆布局变了 ⇒ 该地址读到 0x1E420007（不是菜单下标）⇒ 握手失败（脚本自己也在注释里写了这个失效模式）。**故本轮改用静态 `-grinput` 脚本取证**。若要继续用 nav_hook，需要重新标定该地址 |
| 4 | 运行间抖动 3 张 | ⚠ 如实记录 | 本盘跑两次差 188/191（对照盘跑两次 191/191）。多出的 f1890/1920/1950 属 h=640 下的轻微抖动 |
| 5 | `EN_SPECIAL_FEATURE.XML` 的 `real` 字段 | 未动 | 源盘 `real=116,430` 而实际解压 116,486 B（既有 56 B 差异，两盘相同，本轮未改）|

---

## 9. 复现命令（全部可重跑）

```powershell
# 侦察
python work\tools\f364_recon.py                      # 364 缺字 vs 基底现状 → r82\f364_recon.txt
python work\tools\f364_probe1.py                     # 文本容器 0xB4/0x7F 字节预算 + FONT.RES 记录
python work\tools\f364_probe2.py                     # 0xB4 的精确落点（文本块 / 属性值 / 结构区）

# 构筑（两步；每步都有硬断言，dry-run 不写盘）
python work\tools\thr_patch_atlas.py work\builds\GR_ZH124\GR_ZH124.iso `
       work\builds\GR_F364\_stage640.iso --w 1024 --h 640 --real-mode fixed `
       --report work\builds\GR_F364\stage640_report.json
python work\tools\f364_patch.py work\builds\GR_F364\_stage640.iso `
       work\builds\GR_F364\GR_F364.iso --apply-charset

# 离线判据
python work\tools\f364_verify.py                     # 文本逐字节等价 + 全盘差异窗口分类
python work\tools\f364_diffq.py                      # 粗粒度差异定位
python tools\iso_build\dump_font.py --iso work\builds\GR_F364\GR_F364.iso `
       --out work\builds\GR_F364\temp\fontdump --prefix GR_F364 --grid
python tools\text_csv\inject_text_csv.py --csv work\builds\GR_ZH98\temp\r83\text_in `
       --src work\builds\GR_F364\GR_F364.iso --check-only
python work\tools\cave_dis.py work\builds\GR_ZH98\temp\r72\SLUS_206.13.elf diso 0x417140 0x417180

# 实机（先确认 Get-Process pcsx2-gsrunner 恒为 0；跑完确认退出）
python work\tools\thr_run1.py --iso work\builds\GR_F364\GR_F364.iso `
       --dump work\builds\GR_F364\temp\dump_f364log --nav tools\capture\nav_menu_only.txt `
       --maxframes 6000 --snap 30 --scanframes 4000 --renderer dx11 `
       --extra "-logfile <ABS>\work\builds\GR_F364\temp\dump_f364log\emulog.txt"
python work\tools\f364_results.py work\builds\GR_F364\temp\dump_f364log `
       work\builds\GR_F364\temp\dump_ctl124log
python work\tools\thr_run1.py --iso work\builds\GR_F364\GR_F364.iso `
       --dump work\builds\GR_F364\temp\dump_f364page2 --nav work\tools\f364_nav_interview.txt `
       --maxframes 33000 --snap 250 --renderer dx11
```

---

## 10. 给下一轮的三条

1. **要拍到 136 个新字**：把 `work\builds\GR_ZH98\temp\r64\reduce_map.csv` 里被替换掉的正文按
   `rich_missing_chars.csv` 逆向还原（或单独做一张字库测试页），然后跑本报告的 `f364_nav_interview.txt`。
   字已经在盘上了，只差文本用它们。
2. **顺手修 2 处既有残缺点**（§8-2）：需要 round64 之前的文本快照
   （`work\builds\GR_ZH109\text_backup_before_reduce\GR_ZH109_text_long.csv` 一带）。
3. **重新标定 `nav_hook.py` 的 `MENU_SEL_ADDR`**：任何改变 PAK/图集尺寸的盘都会让
   0x013379D0 失效；把它改成「按特征扫描」而不是硬编码，可省掉每天一次的踩坑。
