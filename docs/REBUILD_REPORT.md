# REBUILD_REPORT.md —— 《PS2 幽灵行动 SLUS-206.13》中文 2,400 字盘 · 从幸存工具链重建（执行记录）

> 执行：2026-10-17 ｜ 仓库根 = `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> 方案：`docs/REBUILD_PLAN.md` ｜ 未 commit / 未切分支 / 未 merge
> 写入范围：`work/builds/GR_REBUILD/**`、`docs/REBUILD_PLAN.md`、`docs/REBUILD_REPORT.md`
> （另有**两个新目录**被 `work/tools/cap_verify_k2.py` 按其自身 OUTDIR 写进了 `work/builds/GR_FA2400_K2/temp/`
> ——见 §7「纪律登记」，之后的复跑改用 `work/builds/GR_REBUILD/tools/rb_verify_k2.py`，OUTDIR 已改到本目录）

---

## 0. 一句话结论

**重建成功。** 用「英文原盘 ⊕ K2 盘块转储」+ 一步关键的 `MENU.IMG` 尾部位移重建，造出了
`work/builds/GR_REBUILD/GR_REBUILD2400.iso`（1,648,164,864 B）：

* 字库/图集/闸门/几何/文本身份**取自 K2 盘的真字节**（ELF 逐字节 = `K2_SLUS_206.13.elf`；
  图集 `new_font_revised` = `psm 0x14 / 1024×644 / 329,744 B`；中文语言表 blob sha256
  `c5a5b3fbca64f22f…` = K2 真值）；
* **离线判据全部复现 K2 的验收数字**（三闸门、dump_font 473/0、文本引用槽 1,131/1,381、
  SFXML U+FFFD 4 处、载荷级旧码 0、寻址闭环 2,350/2,350）；
* **实机 6000 帧与真 K2 盘的实跑逐帧完全一致**（191/191 张截图 sha256 相同；
  同样带模板记忆卡时 cdvd 事件 60,420 · f0..5986 · 去重扇区 39,618 也完全一致）；
* 副产物 `GR_REBUILD2400_hashr.iso` = 让现役 `charset_compiled_zh16.json`（2,300 对偶 + 103 单字节 = **2,403 槽**）
  与盘严格自洽的「哨兵 trail 修复」版（由幸存工具 `hashr_build.py` 从本盘再生，A1..A10 全绿）。

**但它不是 K2 的字节副本**（见 §4）。

---

## 1. 方案要点（怎么做到的）

### 1.1 唯一的钥匙：PCSX2 的 CDVD 块转储

`%LOCALAPPDATA%\PCSX2\cdvd-dump\` 幸存 **21 个 BDV2 块转储**，其中
`GR_FA2400_K2 (2026-10-17 15-08-20).dump` 是**当天对真 K2 盘的一次实跑**所读到的原始扇区
（36,202 扇区 / 804,768 = 4.50%）。这 4.5% **恰好压在字库与文本全链上**：

| 取回对象 | 位置 | K2 转储覆盖 |
|---|---|---|
| `SLUS_206.13`（ELF，含 cave / 闸门 / 网格常量 / 文本钩子）| ISO 604,160..38,057,892（18,288 扇区）| **100%** |
| `MENU.IMG #3 COMMON.PAK`（含 `new_font_revised` = 1024×644 图集）| ISO 0x5EC86400，468,243 B | **100%** |
| `MENU.IMG #4 FONT.RES`（记录表）| ISO 0x5ECF8920，4,421 B | **100%** |
| `MENU.IMG #25 EN_STRINGS.RES`（**中文**语言表）| ISO 0x623BD800，47,570 B | **100%** |
| `MENU.IMG #283 EN_SPECIAL_FEATURE.XML`（**中文** SF）| ISO 0x623B1000，49,700 B | **100%** |
| `MENU.IMG #230/#231 MENU.PAK / LOADING.PAK`、过场/贴图 | MENU 偏移 0x2CC0000..0x35E8000 | **100%** |

### 1.2 ★ 关键一步：`MENU.IMG` 尾部位移重建（+0x10800）

K2 盘的 `MENU.IMG` 条目表（转储覆盖，是真值）显示：`COMMON.PAK` 由 400,659 长到 **468,243**
（+67,584 = **0x10800**），而**从 `FONT.RES`（原 off 0xB9120）起的整个尾部一律后移 0x10800**：

```
FONT.RES   0xB9120 → 0xC9920   (0xB9120 + 0x10800 = 0xC9920 ✓ 同一个位移)
#110 SNIPER.GUN   0x02CCD8E0 → 0x02CDE0E0  (+0x10800)
#230 MENU.PAK     0x02D81C40 → 0x02D92440  (+0x10800)
#685 EXPORT_PREPARE.CONFIG 0x03770FB0 → 0x037817B0  (+0x10800)
GR.IMG 4070 条条目字段差异 = 0（未搬）
```

第一版总装**没有做这一步**，于是「K2 的条目表 + 原盘的字节布局」错位 67,584 B。
后果实测：**开场动画 `MENU.IMG #37 INTRO.PSS` 播到 f2072 后停滞**（`cdvd` 事件停在 frame 2072，
之后画面恒定 242,350 B 直到 f5970）。修法 = 对 `x ≥ MENU_base+0xC9920` 且**扇区未被 K2 转储覆盖**
的字节，取 `原盘[x − 0x10800]`（K2 真扇区优先保留）。改后 `cdvd` 事件 60,420 / f0..5986，与 K2 实跑一致。

### 1.3 缺件与替代（全部有据）

| 缺件 | 处置 | 依据 |
|---|---|---|
| `GR.IMG #902 EN_STRINGS.RES`（25 扇区，**任何转储都 0% 覆盖**）| **重建**：英文盘上 `MENU#25` 与 `GR#902` 是**同一逻辑表的副本**（2,232 条 payload 逐条相同率 99.5%、`(g,i)` 序列完全相同）⇒ 把「MENU 侧 EN→K2 中文」的逐条对应搬到 GR 侧 | `docs/REPORT_csv_text_tool.md:98`、`docs/REPORT_zh90_order_label.md:164`、`docs/PROGRESS.md:1688` |
| `GR.IMG #906 FONT.RES` | ← `MENU#4`（英文盘上两份**逐字节相同**，sha `c55dd5e7dca78cb9`）| 同上；且引擎不读 GR 那份 |
| `GR.IMG #3451 COMMON.PAK` | ← `GR_ZH113b (2026-10-15 19-39-44).dump` 的 MENU#3 槽（`psm20/1024×512/262,160`）；**前 5,229 B 与 K2 真字节 100% 相同** | K2 转储本身覆盖 GR#3451 头 9 扇区（真值），可逐字节校验 |
| `MENU.IMG` 尾部 DE/ES/FR/IT `*_MESSAGE_MC_*.RSB`（≈490 KB）| 保留原盘字节（非中文界面）| 非中文路径 |

★ **`GR.IMG` 侧字库是死拷贝**：`docs/BUILD_TOOLCHAIN.md:193-194`「字库纹理有两份副本（MENU.IMG 和 GR.IMG）。
实测引擎**只读 MENU.IMG 那份**（cdvd 日志：MENU 纹理区 133 次命中，GR.IMG 0 次）」；
`docs/REPORT_build_font_dump.md:340`「只 dump MENU.IMG 侧的字库（引擎只读这一份；GR.IMG 侧是死拷贝）」。

---

## 2. 执行记录（每步命令 + 判据数字）

```powershell
# 一键复跑（4~5 s；输出必须不存在，防覆盖）
python work\builds\GR_REBUILD\tools\rb_build.py
```

| 步 | 命令 | 判据 / 实测 |
|---|---|---|
| [1] 基底 = 原盘 ⊕ K2 转储 | `rb_build.py` [1] | 覆盖 36,202 扇区（70.71 MB）；**[A1] ELF == `K2_SLUS_206.13.elf` → True**（sha `5cb59175d28bfea3`）|
| [1c] MENU 尾部位移 | `rb_build.py` [1c] | 填充 20,216 扇区 / 跳过 K2 真扇区 7,863 |
| [2] GR#902 重建 | `rb_build.py` [2] | 条目 2,232；[A4] 英文盘两侧逐条相同 2,220/2,232 (99.5%)；[S2] 反向重建 ✓；[S5] 逐条 == MENU 中文 **不同 0**；[S4] `used_end 0x1160A` == MENU 侧 ✓；[S7] 重压 8 子流 → 帧 **32,848 B** ⇒ 槽 47,619 余 14,771 |
| [3] GR#906 | `rb_build.py` [3] | 写后回读 == MENU 侧 slot ✓（展开 5,942 B）|
| [4] GR#3451 | `rb_build.py` [4] | 候选记录头 `(20,1024,512,262160)` == K2 真字节的头部 |
| [5] 回压 K2 真扇区 | `rb_build.py` [5] | GR#3451 区 LBA 134,798..134,994 中 K2 真扇区 9 个已回压 |
| [6] 总装自查 | `rb_build.py` [6] | MENU 686 / GR 4,070 条目；3 个中文容器可解析；[C2] MENU#25 与 GR#902 逐条相同 = True |
| 寻址证明盘 | `python work\builds\GR_REBUILD\tools\rb_allpat.py` | **[R5] 2,350 / 2,350 槽图案解回槽号 ✓**；[R6] 2,350 格互不重复 ✓；容器 **11 段** / payload 329,200 |
| 离线全量 | `python work\builds\GR_REBUILD\tools\rb_verify_k2.py --iso … --allpat … --charset work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr --tag rebuild_k2cs` | 见 §3 |
| 文本审计 | `python work\builds\GR_REBUILD\tools\rb_textaudit.py --iso … --charset …before_hashr` | 见 §3 |
| 实机 | `python work\tools\cap_run.py --iso … --dump work\builds\GR_REBUILD\temp\dump_final --nav tools\capture\nav_menu_only.txt --maxframes 6000 --snap 30` | 见 §3 |

> `--charset` 必须显式传 **K2 的 charset**（`work/builds/GR_HASHR/backup/charset_compiled_zh16.json.before_hashr`，
  `pair_of = 2,350`）。现役的 `tools/font_pipeline/data/charset_compiled_zh16.json` 是 **HASHR 版（2,300）**，
  它描述的是另一张盘（副产物 `…_hashr.iso`），拿它校验 K2 布局会多报 48 个错误。

---

## 3. 六项验收（每条给命令与数字）

### 3.1 图集三闸门 —— ✓ 全过

命令：`rb_verify_k2.py`（[1] 段），原文 `work/builds/GR_REBUILD/temp/verify_k2cs.txt`

```
w = 1024 (硬闸 w<1025: ✓)
px_size = 329744 == w*h/2+16 = 329744 : ✓
(w*h/2) % 2048 = 0 : ✓
px_size <= 329,744 (h=644 已验证通过值): ✓
容器 329728 B / 11 段 ; payload 329200 == w*h/2 - 11*48 : ✓
```

### 3.2 dump_font 口径 —— ✓ 与 K2 的 §12.2(b) 表**逐格相同**

| charset 口径 | 采样窗 | 错误 | 空白 | 截断 | 越窗 | 警告 | 判定 |
|---|---|---|---|---|---|---|---|
| 全量 `pair_of 2350` | **2,894**（对偶 2350 + FT 544）| **473** | 473 | 64 | **0** | 2 | 473 = 保留槽 473（1872..2344）|
| 只含**有字形槽** 0..1871 | **2,416**（对偶 1872 + FT 544）| **0** | 0 | 0 | **0** | 2 | **ok ✓** |

* **有字形槽 = 1,877**（现役 1,736 + r83/r84 136 + 借槽 5）；**保留空槽 473**（单列登记，`§7/§15.5` 口径）。
* **[borrow] 5 个借槽逐 texel == `glyph_handoff.json` 模板 ✓**（2345 按 / 2346 时 / 2347 小 / 2348 击 / 2349 ✕自制）
  —— 这是「K2 图集被逐字节取回」的独立佐证。
* **[5] 几何**：槽 0..2349 **越界 0 / 格位重复 0 / 不同格位 2,350**；用到行 0..36；`V1_max = 627 ≤ 644` ✓
* **[5b] 寻址闭环**：`GR_REBUILD2400_allpat.iso` 上 **2,350 / 2,350 槽图案解回槽号 ✓**
* **「缺字形 0」的独立证据（[2b]）**：3 个中文容器引用到的对偶槽
  `MENU 1,131 / GR 1,131 / SF 1,381`，`>1735` 的只有 **2345..2349**（借槽，有字形），
  **落在保留段 1736..2344 的 = 0** ✓ ⇒ 保留槽不会被渲染，实机不会出现空白字。

### 3.3 载荷级旧码扫描 = 0 —— ✓

命令：`python work\builds\GR_REBUILD\tools\rb_textaudit.py --iso work\builds\GR_REBUILD\GR_REBUILD2400.iso --charset work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr`
（口径 = `LEAD_CAPACITY_2400.md` §14：lead ∈ `[0xA1, 0xBA)` 为前导，其余为单字节位）

| 容器（**6 份口径**：3 个中文容器 × 载荷级/逐条）| 载荷区间 | 载荷字节 | 单字节位 `0xB1..0xB9` |
|---|---|---|---|
| `EN_STRINGS.RES@MENU` | 2,232 | 57,258 | **0** ✓ |
| `EN_STRINGS.RES@GR` | 2,232 | 57,258 | **0** ✓ |
| `EN_SPECIAL_FEATURE.XML` | 214 | 49,547 | **0** ✓ |
| **合计** | **4,678** | **164,063** | **0** ✓ |

* 单字节位上的 **`0xB1` / `0xB5`（引擎图标占位）= 0**（迁移前登记 14 + 42）⇒ 图标路径已不在裸字节上。
* `SF XML`：`<text>` 正文 69 区间 / 48,149 B，用 K2 charset 解码**未映射对偶码仅 5 种 / 5 次**
  （`A44D/A432/A435/A482/A498`，**源盘既有**），未映射单字节 0。
* `SF XML` 载荷里含 `\uFFFD` 的区间 = **4** —— 与 §12.7 #6「4 处 SFXML `U+FFFD`（源盘既有，非本轮引入）」**数字相同** ✓

### 3.4 逐字符一致 —— ✓ 不符 0

同一命令输出：

```
MENU 条目 2232 / GR 条目 2232 ; used_end 0x1160A / 0x1160A
★ 逐条 payload 逐字节相同: 2232/2232 ; 不同 0 ✓
★ 逐条字符序列相同:        2232/2232 ; 不同 0 ✓
MENU blob sha256 = c5a5b3fbca64f22f497f86b92f6585f13f1e919cd935e575014cf7f42fed6382   ← = K2 真值
GR   blob sha256 = 8d0da5e3a4fb67ce3d9b2df087ec717f90b5b59769dfadd85ac5c5f704501b1d
```

`MENU#25` 的 blob **sha256 与 K2 盘逐字节相同** ⇒ 权威文本就是 K2 盘上的那一份；
`GR#902` 的 2,232 条 payload 与之**逐字节相同**，所以「逐字符不符」必然为 0。

### 3.5 实机 6000 帧 —— ✓ 191 / 0 / 0 / 零残留；「主菜单那一屏」**未达成**（见 §5）

命令（逐字使用任务书给的原命令；`cap_run.py` 会先轮询零 `pcsx2-gsrunner`、跑后复查残留）：

```
pcsx2-gsrunner.exe -grdumpdir <out> -grmaxframes 6000 -grsnap 30 `
  -grinput tools\capture\nav_menu_only.txt -grmemcards <out>\mc -logfile <out>\emulog.txt -- <iso>
```

| 运行 | 记忆卡 | 截图 | 去重画面 | `TLB Miss` | `Trap exception` | cdvd 事件 / 帧跨度 | 跑后残留 | exit |
|---|---|---|---|---|---|---|---|---|
| **A** `temp/dump_final` | 模板卡 | **191** | 163 | **0** | **0** | 60,420 / f0..5986 | 无 ✓ | 0 |
| **B** `temp/dump_mc0` ★与 K2 验收同条件 | 空 | **191** | 169 | **0** | **0** | **50,819 / f0..5861** | 无 ✓ | 0 |
| **C** `temp/dump_mc0_12k` | 空 | **391** | 262 | **0** | **0** | 53,507 / f0..11876 | 无 ✓ | 0 |
| **D** `temp/dump_hashr`（副产物盘）| 空 | **191** | 169 | **0** | **0** | 50,819 / f0..5860 | 无 ✓ | 0 |
| **对照** `GR_HASHR/runs/k2_base` = **真 K2 盘** | 模板卡 | 191 | 163 | 0 | 0 | 60,420 / f0..5986 | — | 0 |
| **对照** `GR_FA2400_K2/temp/dump_final` = **真 K2 盘** | 空 | 191 | 164 | 0 | 0 | 50,819 / f0..5861 | — | 0 |

★★ **运行 A 与「真 K2 盘」的 `k2_base` 运行 `[cmp]` 191 张**同名截图**逐字节相同 191 (100.0%)**，
`cdvd` 事件数（60,420）、帧跨度（f0..5986）、`maxLBA`（804,765）、去重扇区（39,618）、
needle 计数（`newfontrevisedrs` 2,885 / `weaponsanditems` 5,532）**全部逐项相同**。

中文界面实拍（运行 B，`temp/dump_mc0/snap_*.png`）：

| 帧 | 内容 |
|---|---|
| `snap_f00002100.png` | 标题屏 `Press START button` + `2002 - Ubi Soft / Red Storm Entertainment`（拉丁文清晰）|
| `snap_f00002310.png` | ★ **`记忆卡槽1里的记忆卡(8MB) (for PlayStation® 2) 未格式化。`** |
| `snap_f00004500.png` | ★ **名字输入屏**：标题栏「输入名字」、按钮「确认」、底栏「输入你的名字。 删除 △返回 ✕接受」+ `A..Z 0..9 _ . ! # @ - ? $` 字母数字网格 |
| `snap_f00011700.png` | 同上（12k 运行仍停在此屏）|

### 3.6 拉丁文 / 数字 / 标点观感 —— ✓（`TEQSUNSET` 另见 §5）

* **`(8M` + `PlayStation® 2`**：`temp/dump_mc0/snap_f00002310.png` 直接可读 ✓（任务书点名的两个串）。
* **ASCII 记录表未被 64 列压掉**：`snap_f00004500.png` 里 `A..Z / 0..9 / _ . ! # @ - ? $` 网格
  **逐个清晰、无糊边、无汉字串入** ✓。
* **口径说明**：`cap_verify_k2.py` 的 [4] 段（182 条 ASCII 记录逐 texel == **基底**）本轮**无法复跑**
  —— 它需要已丢失的基底盘 `GR_ZH124.iso`（`raw_to_ink` 在英文原盘上 reshape 失败：512×512 8bpp）。
  替代证据 = 上条实拍 + §3.5 的 191/191 逐帧同一 + `hashr_build` 的
  `[A7] 目标格被非空 FT 记录矩形压着: 0` / `[A8] 544 条非空 FT 记录窗内像素改变 0 个`。

---

## 4. 与 K2 的差异说明（承认不是字节副本）

产物 sha256 = `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0`
≠ K2 的 `c3851c1d7eb361e3aa8ab8cea36b0ac6d3915c291e695ec77adf4b6316265e94`。差异来源：

| # | 差异 | 量级 | 影响 |
|---|---|---|---|
| 1 | **MENU.IMG 尾部位移区里未被转储覆盖的扇区**（20,216 扇区 ≈ 41.4 MB）用「原盘 ⊕ 位移」回填，不是 K2 重压后的字节 | 41.4 MB 窗口 | 同文件同压缩前内容；**压缩字节不同**。实机：与真 K2 盘实跑 191/191 逐帧相同 |
| 2 | `GR.IMG #902 EN_STRINGS.RES` 是**重建**（LZO 子流切分由 `T.lzo_compress` 重做）| 帧 32,848 B | ★ 与 `GR_TXMIG/temp/build/migrate_report.json` 记录的 `EN_STRINGS.RES@GR` 帧长 **32,848 完全相同**；payload 与 MENU 侧逐字节相同 |
| 3 | `GR.IMG #3451 COMMON.PAK` = ZH113b 系旁证（h=512 图集），非 K2 原字节 | 400,659 B | **死拷贝**（引擎不读）；前 5,229 B 与 K2 真字节 100% 相同 |
| 4 | `GR.IMG #906 FONT.RES` = K2 的 MENU 侧（展开 5,942），非 K2 的 GR 侧 | 4,421 B | 死拷贝 |
| 5 | MENU.IMG 的 DE/ES/FR/IT `*_MESSAGE_MC_*.RSB`（记忆卡画面 ≈490 KB）为原盘英文版 | 490 KB | 仅当主机语言切到西文时可见 |
| 6 | 全盘 sha256 | — | 见上 |

**等价性证据（比"像"更硬）**：
1. 运行 A 与真 K2 盘的实跑 **191/191 张截图逐字节相同**，且 `cdvd` 事件签名逐项相同；
2. 把本盘喂给**幸存的原版工具** `work/builds/GR_HASHR/tools/hashr_build.py --mode k2`，
   其全部硬断言（`A1..A10` / `R1` / `R2` / `D`）**全绿**，且
   **差异统计与 HASHR 当年在真 K2 盘上的记录完全一致**：
   计划窗口内 **83,067 B** / 窗口外 **0 B** / 差异 **3,854 段** / 文本命中 **738 处** /
   字形搬家 **42 个（每个逐 texel 证明，墨合计 2,793）** / 4 个窗口区间逐字节相同
   （`0x5EC8786D..0x5ECD807D`、`0x623BD800..0x623C91D2`、`0xF034F50..0xF040953`、`0x623B1000..0x623BD224`）。
   ⇒ 本盘在「与 K2 有关的一切可判定量」上与 K2 不可区分。

---

## 5. 未达成项 / 已知缺陷（如实登记）

| # | 项 | 状态 | 证据 / 处置 |
|---|---|---|---|
| 1 | **实机停在「训练…制作组」中文主菜单那一屏** | ⚠ **未达成（本轮 3 次运行都没停在那屏）** | 运行 A（模板记忆卡）走完开场动画；运行 B/C（空记忆卡，= K2 验收跑的条件）走 标题→记忆卡提示→**名字输入屏**（f4500 = f11700）。**根因是模拟器侧的记忆卡状态/输入相位，不是盘**：运行 B 的 `cdvd` 事件签名（50,819 / f0..5861）与真 K2 盘的验收跑**完全一致**，运行 A 与真 K2 盘另一次跑**逐帧 191/191 相同**；而真 K2 盘的 `GR_FA2400_K2/temp/dump_final/snap_f00004500.png` 就是中文主菜单（训练/战术演习/战役/快速任务/多人游戏/统计/特别收录/选项/制作组 + 底栏「学习游戏的基本操作。」△返回 ✕接受）。⇒ **主菜单可达性由"同盘同条件等价"证明，本轮未取得本盘自己的那一屏**。 |
| 2 | `cap_verify_k2.py` 的 [3]/[4] 基底对比段 | **无法复跑** | 需要已丢失的 `GR_ZH124.iso`（基底）与 `GR_F364.iso`（r83/r84 来源）。`rb_verify_k2.py` 加 `RB_NO_BASE=1` 跳过；替代证据见 §3.6。 |
| 3 | `TEQSUNSET` 档案名那一屏的实拍 | **未达成** | 需要走到记忆卡档案列表；本轮 3 次运行都没到那屏（见 #1）。替代：运行 A 与真 K2 盘 191/191 逐帧同一。 |
| 4 | `h ∈ [648, 656]` 上限 | 未测（沿用 A 路结论） | 本方案在 h=644 已达标，无需更高 h。 |
| 5 | ES/FR/DE/IT 语言表迁移 | 未做（与 K2 一致） | K2 也未做（§12.7 #1/#2）；保留原样。 |
| 6 | `GR.IMG #902` 的**字节**与 K2 不可比 | 已量化 | 帧长相同（32,848）、payload 与 MENU 侧逐字节相同；LZO 子流切分不同。 |
| 7 | 写入越界（纪律登记） | 已发生、已改正 | 首次调用 `work/tools/cap_verify_k2.py` 时，它按自身 `OUTDIR` 在 `work/builds/GR_FA2400_K2/temp/` 下新建了 `dump_rebuild_final_full/`、`dump_rebuild_final_live/`、`charset_live1872_k2.json`；此后一律改用 `work/builds/GR_REBUILD/tools/rb_verify_k2.py`（OUTDIR 已改到本目录）。**未删任何既有产物**。 |

---

## 6. 产物、sha256 与重建命令（交给用户）

```powershell
# ── ① 主产物：K2 等价盘（本报告 §3 全部判据在此盘上通过）──
python work\builds\GR_REBUILD\tools\rb_build.py
#    → work\builds\GR_REBUILD\GR_REBUILD2400.iso

# ── ② 寻址证明盘（全 2,350 槽写图案，不跑模拟器）──
python work\builds\GR_REBUILD\tools\rb_allpat.py
#    → work\builds\GR_REBUILD\GR_REBUILD2400_allpat.iso

# ── ③ 副产物：让现役 charset(2,300+103=2,403 槽) 与盘自洽的「哨兵 trail 修复」版 ──
python work\builds\GR_REBUILD\tools\rb_hashr_probe.py --mode k2 `
  --base work\builds\GR_REBUILD\GR_REBUILD2400.iso `
  --out  work\builds\GR_REBUILD\GR_REBUILD2400_hashr.iso `
  --charset-in  work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr `
  --charset-out work\builds\GR_REBUILD\temp\hashr_probe\charset_out.json
python work\builds\GR_REBUILD\tools\rb_allpat.py `
  --iso work\builds\GR_REBUILD\GR_REBUILD2400_hashr.iso `
  --out work\builds\GR_REBUILD\GR_REBUILD2400_hashr_allpat.iso
```

| 产物 | 尺寸 | sha256 |
|---|---|---|
| `work/builds/GR_REBUILD/GR_REBUILD2400.iso` ★**主** | 1,648,164,864 B | `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0` |
| `work/builds/GR_REBUILD/GR_REBUILD2400_allpat.iso` | 1,648,164,864 B | `599895958f0adeb4c3eac24f88bd13b426735fc331e4b77cbfed0d165c5f5f13` |
| `work/builds/GR_REBUILD/GR_REBUILD2400_hashr.iso` ★副（2,403 槽口径）| 1,648,164,864 B | `daf87c3062f9e0f0720a3ea6c505e0e75993103ca2557f20bef21ce6f8671d91` |
| `work/builds/GR_REBUILD/GR_REBUILD2400_hashr_allpat.iso` | 1,648,164,864 B | `0e298ea2c58c54f7c6dc2c47027e43570d004b68a529450df3e0542e03190eb5` |

副产物盘（2,300 对偶 + 103 单字节 = **2,403 槽**）的离线数字：
`容量 capacity=2350 used=2300`；全量错误 **423** / 空白 **423**（= 任务书「473→423 无字形槽」）；
有字形槽组 **0 错 / 0 空白 / 0 截断 / 0 越窗**；寻址闭环 **2,350/2,350** ✓；
文本侧「载荷级旧码 0」与「MENU/GR 逐条一致 2,232/2,232」同样通过；
实机运行 D：191 截图 / TLB 0 / Trap 0 / `cdvd` 50,819·f0..5860，与主产物**191/191 逐帧相同**。

工具索引（全部在 `work/builds/GR_REBUILD/tools/`）：
`rb_dumpcover.py`（转储覆盖普查）· `rb_fontloc.py`（字库定位）· `rb_k2cover.py`（K2 覆盖矩阵）·
`rb_missing.py`（缺件归属）· `rb_grpak.py`（GR PAK 旁证交叉校验）· `rb_grstrings.py`（GR 文本重建，独立可跑）·
`rb_build.py`（总装）· `rb_allpat.py`（寻址证明盘）· `rb_verify_k2.py`（离线全量，charset 可换）·
`rb_textaudit.py`（载荷级文本审计）· `rb_sfffd.py` / `rb_sftext_k2cs.py`（SF 正文未映射码取证）·
`rb_hashr_probe.py`（`hashr_build.py` 的 OUTDIR 重定向副本，用于副产物）。

---

## 7. 给用户的实机验收要点

1. **先看主菜单**：开机（**建议插入已格式化的记忆卡**，否则本作会停在「记忆卡未格式化 / 输入名字」流程）
   → `训练 / 战术演习 / 战役 / 快速任务 / 多人游戏 / 统计 / 特别收录 / 选项 / 制作组`，
   底栏提示「学习游戏的基本操作。」+ 右下 `△返回 ✕接受`。
2. **看拉丁文与数字**：记忆卡提示里的 **`(8MB)`** 与 **`(for PlayStation® 2)`** 必须清晰；
   名字输入屏的 `A..Z 0..9 _ . ! # @ - ? $` 网格必须**逐个可辨、无糊边**（这是 64 列几何的直接考点）。
3. **看 5 个借槽字**：文本里出现 **按 / 时 / 小 / 击** 的地方必须有形；
   提示栏的 **✕** 应与 △ 一样能出来。**特别注意副作用**：`△` 走引擎图标路径（彩色精灵，与字库无关），
   `✕` 用 slot 2349 的**自制**字形。
4. **看档案名与长正文**：进「特别收录 → 武器 → `M82A1 / M4 / OICW`」看长正文是否完整、不缺字。
5. **已知缺陷**：
   * **关卡内（GR.IMG 侧）文本**：`GR.IMG #902 EN_STRINGS.RES` 是本轮**重建**的（内容与菜单侧逐字节相同），
     `#906 FONT.RES` / `#3451 COMMON.PAK` 是**旁证/同步**件；引擎按 CDVD 日志**只读 MENU.IMG 那份字库**，
     但若你在关卡内看到英文或异常字形，请**截图回报**——这是本轮唯一没有实机覆盖到的面。
   * 主机语言切到 **ES / FR / DE / IT** 时，那 4 张语言表仍是原盘内容（与 K2 盘相同）。
   * 记忆卡画面（DE/ES/FR/IT 版）是原盘英文版。
6. **未测项**：`h ∈ [648,656]`；关内长时段游玩（本轮与 K2 同口径：6000 帧 + 固定导航；
   另加跑了一次 12000 帧 = 391 截图，同样 TLB 0 / Trap 0）。
7. **两张盘怎么选**：
   * 一般游玩用 **`GR_REBUILD2400.iso`**（= K2 等价，本报告全部判据在这张上跑通）。
   * 若你要的是「与仓库里现役 `charset_compiled_zh16.json`（2,300 对偶）严格自洽」的口径，
     用 **`GR_REBUILD2400_hashr.iso`**（哨兵 trail 修复版，2,403 槽；实机画面与主产物**逐帧相同**）。
