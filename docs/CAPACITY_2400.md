# CAPACITY_2400.md — 几何/容量落地：h=644 / **64 列** / GATE 0xBA ⇒ 对偶槽 2,350

> ⚠ **历史错误断言订正（2026-10-18 收尾轮）**：本文含已被实测/实机否证的表述 —— 见 `docs/CORRECTIONS.md` §1。
> 原文保留作过程记录；**结论冲突时以 `docs/CORRECTIONS.md` + `docs/STATUS.md` 为准**。

> 执行者：**geom2400**（几何/容量落地）· 工作目录 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> 地面真值：`work/builds/GR_ZH98/temp/LEAD_CAPACITY_2400.md`
> 写盘范围（严格）：`work/builds/GR_CAP2400/**` · `work/tools/cap_*.py` · `docs/CAPACITY_2400.md` ·
> `tools/font_pipeline/data/charset_compiled_zh16.json`
> 未 commit / 未切分支 / 未 merge；历史 ISO、`third_party/orig/**`、PCSX2 配置只读。
> **命令证据**：本文每条结论后面都跟"怎么复现"；日志/产物全在 `work/builds/GR_CAP2400/`。

---

## 0. 一句话结论

```
① ★ 任务书指定的几何 **h=644 / 64 列 / GATE 0xBA / 槽 0..2349** 在实机上**成立**：
     191 张截图 / 去重 164 画面（与基底 164 相同）/ `TLB Miss` 0 / `Trap exception` 0 /
     127/191 帧与基底逐字节相同（其余 64 帧的成因见 §6.1）/ **中文主菜单正常**（关键帧见 §6.2）。
② ★ cave 侧只需 **5 个字节**：COLS 62→64（1 B）+ GATE 0xB4→0xBA（4 B）。
     62 是 `addiu $t6,$zero,62` 的**单立即数**（0x4170AC，被 0x4170B0 的 `div` 消费），
     **不是** mul/sll/add 组合编码 ⇒ 改 1 字节即可（§2）。
③ ★★ **但 64 列有一个此前无人记录的真实代价**：图集右边缘 x=992..1023（**正好是第 62/63 列**）
     是**三个 face 共享的 ASCII 字形表**（63 个矩形 / 182 条 FT 记录 / 码位 0x21..0x9C：
     数字、大写字母、标点）。62 列时网格永不采样那里，所以它活得好好的；改成 64 列后
     **必被网格格位覆盖**（h=644 只剩 18 个空格，而这张 ASCII 表要 35 格 ⇒ 塞不下）。
     实机可复现地看到：档案名 `TEQSUNSET` 变成乱码（§3 图，**与抬闸门无关**，单变量已证）。
④ ★ **62 列路线已被实机否证**：62 列要 2350 槽必须 38 行 ⇒ h≥658 ⇒ h=660，
     实测 **h=660 撞闸门③**（画面数 1、读流 f0..5999、95,213 事件；与 round86 的 h=672 同一指纹）。
     单变量对照（只加高、其余一个字不动）复现同一失败 ⇒ **2350 槽只有 64 列这一条路**（§5.3）。
⑤ 探针盘 **槽 0..2349 全部可寻址**已闭环：现役 0..1735 逐 texel == 基底；新增 1736..2349
     图案可解码回槽号；`GR_CAP2400_allpat.iso` 上 **2350/2350** 全部解码成功（§5）。
⑥ charset `pair_of` 已 **1,877 → 2,350**（既有条目与 `codes` 一字未动）；备份 +
     一键还原见 §7。**待办**：`tools/text_csv/tcslib.py` 的 lead 上界仍是 0xB5（属文本路写入范围）。
```

---

## 1. 几何账：h / 列数 → 槽数

引擎格位公式（cave 反汇编，§2）：`slot = (lead-0xA1)*94 + (trail-0xA1)`；
`row = slot / COLS`，`col = slot % COLS`，`row ≥ 12 ⇒ row += 3`；
`U0 = 16*col`，`V0 = 16*row + 2`，`V1 = V0 + 16`。

```
h 方向: 行数 = 满足 2 + 16*(row + 3*[row≥12]) + 16 ≤ h 的最大 row+1
列方向: 槽数 = 行数 × 列数
```

| h | 行数 | **62 列**槽数 | **64 列**槽数 | px_size = 1024·h/2+16 | 实机 |
|---|---|---|---|---|---|
| 512 | 28 | 1,736 | 1,792 | 262,160 | ✓ 基底盘 |
| 640 | 36 | 2,232 | 2,304 | 327,696 | ✓ round86/F364 |
| **644** | **37** | 2,294 | **2,368** | **329,744** | ✓ **本轮（两种列数都跑了）** |
| 648 | 37 | 2,294 | 2,368 | 331,792 | 未跑 |
| 652 | 37 | 2,294 | 2,368 | 333,840 | 未跑 |
| 656 | 37 | 2,294 | 2,368 | 335,888 | 未跑 |
| **660** | **38** | **2,356** | 2,432 | **337,936** | ✗ **本轮实测撞闸门③** |
| 664 / 668 | 38 | 2,356 | 2,432 | 339,984 / 342,032 | 未跑（同族，按单调性大概率 ✗） |
| 672 | 38 | 2,356 | 2,432 | 344,080 | ✗ round86 |

* **目标 2,350 槽**：62 列要 38 行（h≥658，且 h≡0 mod 4 ⇒ 660）⇒ **h=660 实测失败**；
  64 列 37 行（h=644）就有 2,368 格 ⇒ **余 18 格** ✓
* 网格覆盖率：2,350 个 16×16 格 = 601,600 texel / 图集 1,024×644 = 659,456 texel（91.2%）
* 三条硬闸（round86 钉死，本轮全部复核）：
  * `w < 1025`（`UITexture::LoadPS2Img` 的 `slti …,1025`）—— w 未动 ✓
  * `px_size == w*h/2 + 16`，且 `(w*h/2) % 2048 == 0` ⇒ w=1024 时 h 必须是 4 的倍数 ✓
  * `px_size ≤ 329,744` 过（h=644 恰为该值）；**≥ 337,936 挂（本轮新数据点 h=660）**

复现：`python work/tools/cap_build.py --dry-run --h <H> --ncol <62|64>`（日志里有容量表）

---

## 2. cave 常量核对 —— 逐字节改动清单

工具：`work/tools/cap_cave_probe.py`（自写 R5900 解码器 `work/tools/cave_dis.py`，**只读** ISO）
产物：`work/builds/GR_CAP2400/temp/cave_probe.txt` · `cave_changes.json` · `GR_ZH124_SLUS_206.13.elf`

```
ISO = work\builds\GR_ZH124\GR_ZH124.iso (1,648,164,864 B)
ELF = LBA 295, 37,453,732 B, sha256=3780df0d252b1a1d392f3687423dc27eb60f0f95ca4a4a829d7833a508db9b76
PT_LOAD[0] va=0x00100000 off=0x80 ⇒ **ISO = 0x93880 + (VA-0x100000) = VA - 0x6C780**  (3 锚点核对 ✓)
```

### 2.1 ★ 「62 是不是乘法/移位编码？」—— **不是，是单立即数**

```
0x004170AC  ISO 0x003AA92C  240E003E  addiu $t6, $zero, 62      ; ★ 唯一装载点
0x004170B0  ISO 0x003AA930  018E001A  div   $t4, $t6            ; cave 区**唯一**的 div
0x004170B4  ISO 0x003AA934  00006812  mflo  $t5                ; row = slot/62
0x004170B8  ISO 0x003AA938  01AE7018  mult  $t5, $t6
0x004170BC  ISO 0x003AA93C  00007012  mflo  $t6
0x004170C0  ISO 0x003AA940  018E6023  subu  $t4, $t4, $t6      ; col = slot%62
```

* 全 text 段（1,276,736 条指令）里 **imm 62 只有 42 个站点，落在字库窗口内的只有 1 个**（就是它）
* cave 区（0x416E00..0x417600）**只有 1 条 div** ⇒ 没有第二条路径参与列数计算
* 结论：**改 1 个字节**（`3E → 40`）即可把列数改成 64；**不存在** mul/sll/add 组合方案，无需插入代码。

### 2.2 待改字节（VA / ISO 偏移 / 改前 4B / 改后 4B）

| # | VA | ISO 偏移 | 改前（LE 4B） | 改后（LE 4B） | 指令 前 → 后 |
|---|---|---|---|---|---|
| 1 | `0x004170AC` | `0x003AA92C` | `3E 00 0E 24` | `40 00 0E 24` | `addiu $t6,$zero,62` → `...,64` |
| 2 | `0x00416EE8` | `0x003AA768` | `B4 00 A9 2C` | `BA 00 A9 2C` | `sltiu $t1,$a1,0xB4` → `0xBA` |
| 3 | `0x00417160` | `0x003AA9E0` | `B4 00 09 2D` | `BA 00 09 2D` | `sltiu $t1,$t0,0xB4` → `0xBA` |
| 4 | `0x0041751C` | `0x003AAD9C` | `B4 00 4B 2D` | `BA 00 4B 2D` | `sltiu $t3,$t2,0xB4` → `0xBA` |
| 5 | `0x005656A4` | `0x004F8F24` | `B4 00 6C 2D` | `BA 00 6C 2D` | `sltiu $t4,$t3,0xB4` → `0xBA` |

**实际改动 = 5 个字节**（每个字只动小端 imm 低字节）：`0x3E→0x40`、`0xB4→0xBA`×4。

### 2.3 中性常量（本轮**不动**，逐条实证）

| 常量 | 值 | VA | 指令 |
|---|---|---|---|
| stride | 94 | `0x416F9C` / `0x417088` | `addiu $t6,$zero,94` |
| SKIP_ROW | 12 | `0x4170D8` | `addiu $t7,$zero,12` |
| SKIP_ROWS | 3 | `0x4170E8` | `addiu $t5,$t5,3` |
| CW / CH | 16 | `0x4170C4` / `0x4170EC` | `addiu $t7,$zero,16` |
| Y0 | 2 | `0x4170F8` | `addiu $t5,$t6,2` |
| **V1 = Y0+16** | 18 | `0x4170FC` | `addiu $t6,$t6,18` |
| 记录索引偏移 | 224 | `0x417094` | `addiu $a1,$t4,224` |

* **图集宽/高不是常量**：字库窗口内 `imm 512 / 640 / 644` 命中 **0** 个；
  窗口内唯一的 `imm 1024` 是 `0x417140 slti $v0,$a1,1024` 与 `0x4171CC li 1024` ——
  属汉化的**字符串长度上限**（同一段还在 `jal 0x21AD10` 量字宽），与图集几何无关。
* h=644 时最高网格行 row36 ⇒ V1 = 642 ≤ 644 ✓；row36 的格位 y=626..641，**不越界**。

复现：`python work/tools/cap_cave_probe.py`

---

## 3. ★★ 本轮最重要的发现：64 列会吃掉 face 共享的 ASCII 字形表

### 3.1 事实（像素级，可复现）

工具：`work/tools/cap_strip.py` → `temp/strip_compare.txt` + 三张图

```
基底盘 GR_ZH124: 1024x512, 62 列 ⇒ 网格最右格 x ≤ 991, **x=992..1023 永不采样**
但 FONT.RES 里有 **182 条记录**指着 x≥992:
  · 63 个不同矩形 (56 个 8x16 + 7 个 16x16), 共 8,960 texel = 35 个 16x16 格
  · 三个 face 共享同一批矩形: large 63 条 / default 63 条 / huge 56 条
  · 覆盖码位 **0x21..0x9C** —— 即 ASCII 表:
      0x21..0x58 (idx 1..56) = !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWX
      0x96..0x9C (idx 118..124) = 7 个汉字
```

`temp/strip_base.png`（把该区域放大 4 倍）肉眼可读：`!"#$` / `%&'(` / `)*+,` / `-./0` /
`1234` / `5678` / `9:;<` / `=>?@` / `ABCD` … `UVWX`，下面 7 个汉字。
⇒ **这不是"余量"，是活字形表**（旧文档 `REPORT_font_capacity_decompile` §3.4 把它读成
"62 = 64−2 的 2 列余量" —— 本轮更正）。

### 3.2 64 列的后果（离线量化）

```
GR_CAP2400_h644_clean.iso (h=644/64 列, 无图案, 只搬字形):
  63 个 ASCII 矩形中 **58 个逐 texel 被改**, 只有 5 个活下来 (落在跳过带 y194..241 里的那些)
  168 条 FT 记录落进新网格格位; 图集墨量 130,203 → 128,713 texel (−1,490)
  temp/strip_h644.png 一眼可见: ASCII 那几行变成了搬过来的汉字字形
GR_CAP2400_h660.iso (h=660/62 列): 63/63 矩形**逐 texel 不变** (但该盘撞闸门③, 见 §5.3)
```

**为什么不能"把 ASCII 表挪个地方"**：h=644 的 64 列图集只有 18 个空格（row36 的 col46..63）
+ 底部 2 行（y642..643），合计 26 格 < 需要的 35 格；跳过带 y194..241 已被 362 条记录占到
66.2%，**8×16 的空格数是 0**。⇒ 在 h=644/64 列下，2350 槽 + 这张 ASCII 表**装不下**。

### 3.3 实机上看得见（单变量归因）

`temp/cmp_3way_f2700.png`（同一帧，四个盘并排裁剪放大）：

| 盘 | 几何 | GATE | 档案名 `TEQSUNSET` | `—空—` 标签 |
|---|---|---|---|---|
| `GR_ZH124`（基底） | h512 / 62 列 | 0xB4 | **清晰可读** | 正常 |
| `GR_CAP2400_h644_nogate` | h644 / **64 列** | **0xB4（未改）** | **已乱码** | **已乱码** |
| `GR_CAP2400`（探针） | h644 / 64 列 | 0xBA | 与上一行**逐像素相同** | 同左 |
| `GR_CAP2400_h660` | h660 / 62 列 | 0xBA | —（卡在记忆卡画面） | — |

* `probe` vs `nogate` 在同一帧 **0 个像素不同**；全 191 帧里 166 帧逐字节相同、25 帧差 7~36 px。
  ⇒ **乱码来自 64 列（ASCII 表被覆盖），与抬闸门无关**。
* 抬闸门 0xBA 在本次导航里的可见影响 = 那 25 帧里的 7~36 个像素（文本里少量 0xB1..0xB9
  裸单字节被当前导吞掉）—— 正是文本路 `TEXT_MIGRATION_0xBA.md` 迁移的那 3,073 处。

---

## 4. 探针盘：产物、sha256、构筑配方

两段式（与 `REPORT_final_364.md` §4 同一配方）：

```powershell
# ① 只改图集几何 (round86 已验证的构筑器; --report 指到本轮目录, 不写别人的目录)
python work\tools\thr_patch_atlas.py work\builds\GR_ZH124\GR_ZH124.iso `
       work\builds\GR_CAP2400\_stage644.iso --w 1024 --h 644 --real-mode fixed `
       --report work\builds\GR_CAP2400\stage644_report.json
# ② 图集重排 + 探针图案 + ELF 5 字节 (10 条硬断言 + 回读)
python work\tools\cap_build.py --h 644 --ncol 64 --tag h644_c64 `
       --out work\builds\GR_CAP2400\GR_CAP2400.iso `
       --allpat-out work\builds\GR_CAP2400\GR_CAP2400_allpat.iso
```

| 盘 | 用途 | 尺寸 | sha256 |
|---|---|---|---|
| `GR_CAP2400.iso` | ★ **任务书指定的探针盘**：h=644 / 64 列 / GATE 0xBA；槽 0..1735 = 现役字形（逐 texel 搬位）、1736..2349 = 确定性图案 | 1,648,164,864 B（804,768 扇区，**与基底同尺寸**） | `899129db1935ac9e5e399755cd67206cc1780aae1e9fd472eb6c6d1444a7df50` |
| `GR_CAP2400_allpat.iso` | **全部 2,350 槽**都写图案（离线"全槽可寻址"证明盘，不跑模拟器） | 同上 | `43a537cd80fd8f102222029461f281d8ce2e357ede9608983d8bb56eb776e628` |
| `GR_CAP2400_h644_clean.iso` | 同几何但**不写图案**（几何体检取证用；图案的墨紧贴现役格会被判"窗外无主墨"） | 同上 | `3ab3e6eeabcb84845ece7926be768a2ee693a84edd6ba861f400bdd0a53bc554` |
| `GR_CAP2400_h644_nogate.iso` | **单变量盘**：64 列 + GATE 保持 0xB4（把"ASCII 表被覆盖"从"抬闸门"里分离出来） | 同上 | `e490379a04226fa4adfddf5abd20fd835cbecf99422c5b80377d449eba0949e6` |
| `GR_CAP2400_h660.iso` | 62 列备选几何 h=660（**实测失败**，见 §5.3） | 同上 | `d9c43627718d20606d79af94b491ac18a5e87391abe5d85a7627b5d90430841a` |
| `GR_CAP2400_h660_allpat.iso` | 同上全图案变体 | 同上 | `34a27239a85c1dfd722ec41fd005d2052cdc3e505408f1d93f639caca78aaa06` |
| `_stage644.iso` / `_stage660.iso` | 只加高的中间盘 | 同上 | `5aedc783…` / `8e39022c…` |

**两字段都写了**（`REPORT_final_364.md` §4.1 配方）：`COMMON.PAK` 条目
`stored == real == 468,243`（h=644）/ `476,435`（h=660）✓；MENU.IMG 声明长度
58,300,882 → 58,308,608（h=644）/ 58,316,800（h=660）；682 条 `off` 整体 +Δ；
ISO 尺寸**未变**（h=644 的 IMG 增长仍在槽内）。

### 4.1 图案规格（确定性、可解码）

```
16x16 ink 掩码:  row0 全墨(上边框) · row13 全墨(下边框) · col0/col15 全墨(左右边框)
                 row14 = 偶列 2..14 墨 (同步字 A) · row15 = 奇列 1..13 墨 (同步字 B)
                 rows 1..12 cols 2..13 = **12 bit 槽号** (bit k ⇒ 该行全墨)
⇒ 槽号 0..4095 唯一可编码; 解码只数墨、与 nibble 顺序无关 ⇒ 可当"寻址探针"。
```

### 4.2 构筑器 10 条硬断言（`cap_build_h644_c64.log` 原文）

```
[A1] 现役槽 1,736 个在新布局格里逐 texel == 基底盘同槽: ✓ (不同 0)
[A2] 槽 1736..2349 图案解码回槽号: ✓ (失败 0)
[A3] FT 记录 544 条非空: 与任一网格格位**不相交**的 376 条 → 逐 texel 不变 ✓
[A3] 与网格格位相交的 168 条 (全部落在右边缘 ASCII 条带)
[A4] 3 行跳过带 (y 194..241, 记录带所在) 逐字节不变 ✓
[A5] 新区域 (y>=512, 67,584 B) 的改动**全部落在新格内**: 格外的改动字节 = 0 ✓
[ct ] 容器 329,744 B / 11 段 / payload 329,200 == w*h/2 - 11*48 ✓ ; 容器↔引擎面 回环逐字节相同 ✓
[pak] 468,243 B (同长) ; rec#1 1024x644 px_size=0x50810 ✓ ; 容器外字节逐字节不变 ✓
[R4 ] 回读 现役槽 == 基底: 1736/1736 ; 新槽图案解码: 614/614 ✓
[D  ] 全盘差异: 计划窗口内 56,533,886 B ; **窗口外 0 B** ✓
     (允许窗口 = ELF 5 字节 ∪ MENU.IMG 全体 ∪ ISO9660 目录记录长度 ∪ PVD 卷长 ∪ 尾部新增区)
```

---

## 5. 离线核对（dump_font 家族 + 独立读回）

工具：`work/tools/cap_verify.py`（把 `tcslib.NCOL / LEAD_HI / PAIR_LEAD_HI` **在运行时**
改成该盘几何，再调 `tools/iso_build/dump_font.py` 的 `dump_font()`）+
`work/tools/cap_recon.py` + `cap_strip.py`。产物在 `work/builds/GR_CAP2400/temp/dump_*`。

### 5.1 槽 0..2349 全部可寻址（三条独立证据）

```
[geom] 槽 0..2349: 越界 **0** ; 格位重复 **0** ; 不同格位 **2350**
[geom] 用到的网格行 0..36 ; 每行 y 区间都 ≤ h-16=628 ; 余 18 格
[addr] 现役槽 0..1735 逐 texel == 基底盘同槽: **1736/1736 相同** (不同 0) ✓
[addr] 新槽 1736..2349 图案解码 == 槽号: **614/614** ✓
[allpat] **全部 2350 个槽**写入图案并解码回槽号: **2350 ✓**
```
（`work/builds/GR_CAP2400/cap_verify_h644_c64.txt` / `.json`）

### 5.2 字形几何体检（dump_font 的 `glyph_geometry`）

| 盘 | 采样窗 | 截断 | 空白 | 越窗 | 错 **误** | 警告 | 判定 |
|---|---|---|---|---|---|---|---|
| `GR_ZH124` 基底（对照） | 2,280（对偶 1,736 + 记录 544） | 0 | 0 | 0 | **0** | 2 | ✓ |
| `_stage660.iso`（只加高，无图案） | 2,280 | 0 | 0 | 0 | **0** | 2 | ✓ |
| `GR_CAP2400_h644_clean.iso`（64 列 + 搬字形） | 2,280 | 0 | 0 | 0 | **0** | 2 | ✓ |
| `GR_CAP2400.iso`（64 列 + **探针图案**） | 2,280 | 0 | 0 | 55 | 55 | 2 | ✗（**预期**） |
| `GR_CAP2400_h660.iso` | 2,280 | 0 | 0 | 53 | 53 | 2 | ✗（**预期**） |

```
★ "越窗"这 53~55 条 = 探针图案的墨紧贴在现役格的下/右侧, 被 glyph_geometry 判成
  "窗外无主墨"。**不是几何错误**: 同一几何、不写图案的 clean 盘 = 错误 0（与基底逐项相同）。
  探针盘上这一项必然非 0（图案本身就是人为墨）, 故把"几何体检 0 错"的判据落在
  **GR_CAP2400_h644_clean.iso**（以及 _stage660.iso）上, 两者都 **0 错 / 2 警告**。
★ 用**全量 charset**（对偶 1,872）跑探针盘会多报 64 条"与模板不符" —— 那 136 个 charset
  条目（slot 1736..1871）在探针盘上放的是图案, 本来就对不上模板。
```

### 5.3 ★ 62 列路线被实机否证（h=660）

```
盘                                   PNG  画面数  =基底  读事件   frame 跨度  maxLBA   判定
GR_ZH124 (基底对照)                  191   164    191    50787   0..5863   804733   ✓
GR_CAP2400 (h644/64列/GATE BA)       191   164    127    50819   0..5860   804765   ✓
GR_CAP2400_h644_nogate (64列/B4)     191   164    127    50819   0..5860   804765   ✓
GR_CAP2400_h660 (h660/62列/GATE BA)  191   **1**   11     95213   0..5999   804768   ✗ 闸门③
_stage660 (h660/62列, 其余一字未改)  191   **1**   11     95213   0..5999   804768   ✗ 闸门③
（round86 的 h=672 指纹: 95,221 事件 / f0..5999 / 804,768 —— 与本轮 h=660 同一条）
```
* `_stage660` 是**单变量对照**（没有 GATE 补丁、没有图案、没有列数改动）⇒ 失败**只**能归因于 h。
* ⇒ w=1024 时闸门③的真实边界在 **329,744（h=644 过）与 337,936（h=660 挂）之间**，
  即 h_max ∈ [644, 656]（h≡0 mod 4）。**本轮没有测 648/652/656 —— 那是仍未解的部分**。
* ⇒ **62 列最多 2,294 槽（h=644）**，要 2,350 槽必须 38 行 ⇒ 只有 64 列一条路。

---

## 6. 实机判据（研究模拟器；一次只跑一个实例，跑前跑后确认无残留进程）

命令（**逐字照任务书**，不加任何额外旗标）：

```powershell
third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe `
  -grdumpdir <out> -grmaxframes 6000 -grsnap 30 -grinput tools\capture\nav_menu_only.txt `
  -grmemcards <out>\mc -logfile <out>\emulog.txt -- <iso>
```
跑法：`python work\tools\cap_run.py --iso <iso> --dump <out>`（内含"无残留进程"检查；
每次 102 s；**exit=0 不作判据**）。汇总：`python work\tools\cap_results.py <dump…>`

### 6.1 判据矩阵（`exit` 一律 0，全部不作判据）

| 盘 | 截图 | 去重画面 | `TLB Miss` | `Trap exception` | needle `newfontrevisedrs` | 读流 | 与基底逐张相同 |
|---|---|---|---|---|---|---|---|
| `GR_ZH124`（对照，本轮实测） | 191 | 164 | **0** | **0** | 2,886 | f0..5863, maxLBA 804,733 | — |
| **`GR_CAP2400`（探针，判据盘）** | **191** | **164** | **0** | **0** | 2,885 | f0..5860, maxLBA 804,765 | **127/191** |
| `GR_CAP2400_h644_nogate` | 191 | 164 | **0** | **0** | 2,885 | f0..5860, 804,765 | 127/191 |
| `GR_CAP2400_h660` | 191 | **1** | 0 | 0 | 2,885 | f0..5999, 804,768 | 11/191 ✗ |
| `_stage660`（单变量） | 191 | **1** | 0 | 0 | 2,885 | f0..5999, 804,768 | 11/191 ✗ |

* 191 ≥ 190 ✓ · 去重 164 == 对照 164 ✓（只看张数会被"卡死也出 191 张"骗，见 round86）
* 64 张与基底不同：f660/690/720/750/780/810（round86/F364 记录的 **h 抖动 6 张**）+
  f1230..f1860（每张 60~160 px）+ f1890/1920/1950（场景时序分叉，95.7%/100%/100%）+
  f2220..f2340（~900 px）+ f2490..f3300（每张 473 px = **ASCII 表损坏**，见 §3.3）
* **无残留 `pcsx2-gsrunner` 进程**（每次跑后检查，5 次全部"无"）

### 6.2 关键帧（中文主菜单 —— 判据"能到中文主菜单"）

| 画面 | 路径 | 内容 |
|---|---|---|
| ★ **中文主菜单** | `work/builds/GR_CAP2400/temp/dump_probe644/snap_f00004500.png` | 训练 / 战术演习 / 战役 / 快速任务 / 多人游戏 / 统计 / 特别收录 / 选项 / 制作组 + 底栏「学习游戏的基本操作。」+ △返回 / ✕接受 |
| 载入成功 | `…/dump_probe644/snap_f00002370.png` | 「载入成功。」+ logo 行 |
| 标志画面 | `…/dump_probe644/snap_f00002040.png` | GHOST RECON logo（烘焙图，非字库） |
| ★ 损坏对照（同帧 4 盘并排） | `work/builds/GR_CAP2400/temp/cmp_3way_f2700.png` | 档案名 TEQSUNSET 在 64 列盘上乱码 |
| 同帧裁剪对照 | `temp/cmp_f00002700.png` · `cmp_f00001500.png` · `cmp_f00002280.png` | 上=基底 / 下=探针 |

**说明（如实）**：主菜单本身**渲染正常**（中文全是网格字形, 与 ASCII 表无关）；
损坏只出现在**用 ASCII 表的那些码位**（大写字母/数字/标点, 例如档案名 `TEQSUNSET`、
`—空—` 的破折号）。所以"能到中文主菜单"达标, 但**"所有画面与基线一致"不达标**。

---

## 7. charset 更新（受保护路径；先备份）

工具：`work/tools/cap_charset.py`；日志 `work/builds/GR_CAP2400/cap_charset.log`。

```
基线（运行前）: tools/font_pipeline/data/charset_compiled_zh16.json
   sha256 = 42f3620dfa06beb0c2dde25c29001057ec0023724ac70d33a0d8d9b7cbbc2f89
   pair_of 1,877 (slot 0..1871 + 2345..2349) ; codes 103 条
   ★ 注意: 这个基线**已被另一路 (round-FA2400) 写过一次** —— 它把 h/列数/gate 与
     击/小/时/按/✕ 的 5 条 pair 先落了, 并在元数据里写明 `reserved_slots=[1872,2344]`
     留给几何路 ⇒ 本轮补的就是这 473 个槽, **没有覆盖它的任何改动**。
备份: work/builds/GR_CAP2400/charset_before_cap2400.json (sha256 同上, 一键还原)
应用: pair_of 1,877 → **2,350** ; codes **103 条一个字段未动**
   sha256 = 7fe2bf5922b5a3505fdf44a93fb9217aadf7a8fb249a327cb9efce4b6eb7fac5
```

| slot | 内容 | 依据 |
|---|---|---|
| 0..1871 | **原样不动**（既有 1,872 条逐条比对通过） | — |
| 1872..1935 | **64 个真实备选字**：`tools/hanliu/texts/pc_official_zh.csv`（PC 官方中文文本）里本工程尚未登记的 CJK 字，频次降序 + 码位升序 = 确定性。例：鼠(119 次)/弧/撒/兽/埋/匍/匐/签/趴/钮… | 真实文本需求 |
| 1936..2344 | **409 个预留槽占位** `U+E200..U+E398`，每个 1 槽 | 「槽位就绪、**字符与字形待补**」 |
| 2345..2349 | 击/小/时/按/✕（round-FA2400 已落, 本轮原样保留） | 文本路借槽协议 |

```
[chk1] pair_of 2,350 条 / slot 连续 0..2349 / lead ∈ [0xA1,0xBA) / trail ∈ [0xA1,0xFE) ✓
[chk2] 既有 1,877 条逐条不动 ✓ ; codes 103 条逐条不动 ✓
[chk3] selfcheck_charset: 用**未更新**的 tcslib 常量(0xB5) = False ;
       把 lead 上界按 gate 0xBA 对齐后 = **True**(失败项 0)
[chk4] encode/decode 对称 (64 个新备选字 + 80 个既有字 + 击/小/时/按) ✓
[chk6] 占位 U+E200 → 0xB5D9 → 回读一致 ✓
```

### 7.1 ★ 两处必须让 Lead 知道的事（都与"任务书字面"不同）

**(1) 本轮相对任务书有一处**共同**偏离 —— 但已被上游做过, 本轮只是承接**
任务书说"pair_of 从 1,872 扩到 2,350 + 不改 codes 的既有条目"。
实测：**pair_of 用到 lead 0xB9 ⇒ codes 里不能留 0xB6..0xB9**（单字节码落在对偶 lead 区间内
会被 `tcslib.selfcheck_charset` 判为硬失败, 且编码器会写出裸前导字节）。
**round-FA2400 已经把 codes 从 107 删到 103**（删掉 击/小/时/按 的 0xB6..0xB9）——
这也是文本路 `TEXT_MIGRATION_0xBA.md` §P1/§7 的请求。本轮**承接该基线, codes 一字未动**,
所以"不改 codes"这条在本轮**字面成立**。

**(2) ★ 仍存在的工具链缺口：`tools/text_csv/tcslib.py` 的 lead 上界没跟上 gate**

```
L58  LEAD_LO, LEAD_HI = 0xA1, 0xB5            ← 应为 0xA1, 0xBA
L59  PAIR_LEAD_LO, PAIR_LEAD_HI = 0xA1, 0xB5  ← 应为 0xA1, 0xBA
后果: charset 的 selfcheck 报 [!!] "字表里 lead 越界的死 pair: 按时小击✕趴钮冶";
      该失败**基线就有**(round-FA2400 的 5 条 pair 已经踩到), 不是本轮引入;
      把这两个常量按 gate 改 0xBA 后, 基线与本轮 charset **都立刻 selfcheck=True**。
该文件属**文本迁移路写入范围**(LEAD §3-B), 本轮按纪律不写 ⇒ 列为待办。
```

### 7.2 与文本路的接口状态（对 `TEXT_MIGRATION_0xBA.md` §7-P1）

| B 路要求 | 状态 |
|---|---|
| ① pair_of 增加 5 条借槽对偶码 | ✅ **已登记**（round-FA2400 落的，本轮保留；slot 2345..2349） |
| ② codes 删除 击/小/时/按 | ✅ **已删**（同上，本轮不动） |
| ③ 图集在这 5 个 slot 画字形 | ⚠️ **不在本轮探针盘范围**：探针盘在这 5 槽放的是图案；成品盘的字形需由成品构建落（B 给的 glyph PNG 可 blit） |
| ④ 合并后重跑 migrate_legacy.py | ⛔ 未做（不在本任务范围） |

---

## 8. 未达成项 / 未解项 / 风险（如实）

| # | 项 | 状态 | 说明 |
|---|---|---|---|
| 1 | **ASCII 字形表（x≥992, 63 矩形/182 记录/码位 0x21..0x9C）在 64 列下被覆盖** | ⛔ **未解决** | 实机可复现（档案名/破折号乱码）。h=644 装不下"2350 槽 + 35 格 ASCII 表"（只余 18+8 格）。**三条出路**见 §9。 |
| 2 | 「所有画面与基线一致」 | ⛔ 未达成 | 127/191 逐字节相同；64 张不同 = h 抖动 6 张 + 时序分叉 3 张 + **ASCII 表损坏 ~33 张** + 抬闸门微差。任务书的 5 条判据（≥190 张 / TLB 0 / 无 Trap / 到中文主菜单）**全部达标**。 |
| 3 | 闸门③ 在 644~656 之间的精确边界 | ⚠️ 未测 | 已知 329,744(h644) 过 / 337,936(h660) 挂。648/652/656 没跑（且对 2350 槽无影响，64 列 37 行已够）。**"h 的 644~668 上限"这一项本轮**部分推进**：把已证上限从"h≤644"收紧到"h∈[644,656]"。 |
| 4 | 探针盘 1736..2349 的字形是**图案**不是真字 | 如实登记 | 任务书要求"确定性测试图案"，本轮照做；真字形属成品构建轮。 |
| 5 | `tools/text_csv/tcslib.py` lead 上界仍 0xB5 | ⚠️ 未改（非本路范围） | 见 §7.1(2)。 |
| 6 | 预留槽 409 个只有占位字符（无字形/无字符） | 如实登记 | "槽位就绪、字形待补"；替换只需改 charset 的键，码位不变。 |
| 7 | 跳过带（y194..241）在 64 列下**没有**被网格压到 | ✅ 已证 | 逐字节不变 + 376 条记录逐 texel 不变（§4.2 [A3]/[A4]）。 |
| 8 | 探针盘 `stored==real` 两字段 | ✅ 已证 | 468,243 == 468,243（窗口外 0 字节差异）。 |
| 9 | 实机只跑了 **6000 帧 + 固定导航**（`nav_menu_only.txt`） | 如实登记 | 未做长导航/深菜单；ASCII 表的影响面判断依赖离线像素证据 + 该单帧实拍。 |

---

## 9. 给 Lead 的三条出路（ASCII 表怎么救）

| 方案 | 做法 | 代价 / 风险 | 本轮证据支持 |
|---|---|---|---|
| **A. 接受现状** | 就用 h=644/64 列；ASCII 码位（0x21..0x9C）改用**别的来源**：这些码位的 FT 记录是"任意矩形"，可把它们指到图集里任何空位（需要改 `FONT.RES` 记录） | 需要 `FONT.RES` 记录手术（182 条 u/v）；空位只有 18+8 格 + 跳过带碎片 ⇒ **装不下 35 格**，除非同时放弃几个槽 | §3.2 的容量算术 |
| **B. SKIP_ROWS 3→2** | 跳过带从 3 行减到 2 行 ⇒ 多出 1 个网格行（38 行 × 64 = 2,432 格）⇒ 富余 82 格，足够安置 ASCII 表（35 格）+ 让路的记录 | 复现 round73 §L3 的"中高风险"：要搬 y213..241 的 ~50 条记录 + 图表；`FONT.RES` 手术；△/✕ 的硬编码 UV（y198..218）仍在 2 行跳过带内 ✓ 不受影响 | 容量算术 + round73 §7 L3 |
| **C. 62 列 + 更高 h** | 已被否 | h=660 实测挂闸门③；h≥660 全族按单调性大概率同样挂 | §5.3 两次独立实机 |

> 我的建议：**先走 A 的"能不能少要几个槽"版本** —— 若要保住全部 2,350 槽，只有 **B**；
> 若可接受 2,315 槽（2,350 − 35），可把 ASCII 表整块搬到 row36 之后的 18 格 + 底部 2 行
> （需 `FONT.RES` 记录改写 182 条），槽数损失 35。两者都需要一次 `FONT.RES` 手术 + 复测。

---

## 10. 复现命令（全部可重跑）

```powershell
# ① cave 反汇编核对 (只读; 出 VA/ISO/字节清单)
python work\tools\cap_cave_probe.py
# ② 基底盘侦察 (现役槽/记录带/墨量/新布局交叠)
python work\tools\cap_recon.py
# ③ 造盘 (两段式; 每步都有硬断言; --dry-run 不写盘)
python work\tools\thr_patch_atlas.py work\builds\GR_ZH124\GR_ZH124.iso `
       work\builds\GR_CAP2400\_stage644.iso --w 1024 --h 644 --real-mode fixed `
       --report work\builds\GR_CAP2400\stage644_report.json
python work\tools\cap_build.py --h 644 --ncol 64 --tag h644_c64 `
       --out work\builds\GR_CAP2400\GR_CAP2400.iso `
       --allpat-out work\builds\GR_CAP2400\GR_CAP2400_allpat.iso
python work\tools\cap_build.py --h 644 --ncol 64 --no-pattern --tag h644_c64_clean `
       --out work\builds\GR_CAP2400\GR_CAP2400_h644_clean.iso       # 几何体检用
python work\tools\cap_build.py --h 644 --ncol 64 --no-pattern --keep-gate `
       --tag h644_c64_nogate --out work\builds\GR_CAP2400\GR_CAP2400_h644_nogate.iso
python work\tools\cap_build.py --h 660 --ncol 62 --tag h660_c62 `
       --out work\builds\GR_CAP2400\GR_CAP2400_h660.iso `
       --allpat-out work\builds\GR_CAP2400\GR_CAP2400_h660_allpat.iso
# ④ 离线核对 (dump_font 家族 + 独立读回)
python work\tools\cap_verify.py --iso work\builds\GR_CAP2400\GR_CAP2400.iso `
       --allpat work\builds\GR_CAP2400\GR_CAP2400_allpat.iso --tag h644_c64 --h 644 --ncol 64
python work\tools\cap_strip.py                 # ASCII 条带三盘对照 + PNG
# ⑤ 实机 (串行独占; 跑前后自动查残留进程)
python work\tools\cap_run.py --iso work\builds\GR_CAP2400\GR_CAP2400.iso `
       --dump work\builds\GR_CAP2400\temp\dump_probe644
python work\tools\cap_results.py work\builds\GR_CAP2400\temp\dump_probe644 `
       work\builds\GR_CAP2400\temp\dump_base
# ⑥ charset (先备份; 自检不过不写)
python work\tools\cap_charset.py --apply
```

---

## 11. 本轮脚本 / 产物索引

| 文件 | 说明 |
|---|---|
| `work/tools/cap_cave_probe.py` | cave 常量反汇编 + 逐字节改动清单（VA/ISO/前后 4B） |
| `work/tools/cap_recon.py` | 基底盘只读侦察（现役槽 1,736 / 544 条记录 / 墨量 / 新布局交叠） |
| `work/tools/cap_build.py` | 探针盘构筑器（10 条硬断言 + 回读 + 全盘差异窗口分类；`--no-pattern`/`--keep-gate`/`--h`/`--ncol`） |
| `work/tools/cap_verify.py` | dump_font 家族（运行时改 NCOL/LEAD_HI）+ 独立读回 |
| `work/tools/cap_strip.py` | ASCII 条带取证（63 矩形 / 182 记录 / 三盘 PNG 对照） |
| `work/tools/cap_run.py` · `cap_results.py` | 实机跑（原命令逐字）+ 判据汇总（画面数/TLB/Trap/needle/读流/逐张比对） |
| `work/tools/cap_charset.py` | charset 扩容（备份 + 自检 + 一键还原） |
| `work/builds/GR_CAP2400/cap_build_*_report.json` + `.log` | 构筑报告与全部断言原文 |
| `work/builds/GR_CAP2400/temp/cave_probe.txt` · `recon.txt` · `strip_compare.txt` | 反汇编/侦察/条带取证 |
| `work/builds/GR_CAP2400/temp/dump_*/` | dump_font 产物（PNG/CSV/summary.json/truncation_report）+ `DUMP_SUMMARY.json` |
| `work/builds/GR_CAP2400/temp/dump_probe644/` · `dump_probe660/` · `dump_nogate644/` · `dump_ctl_stage660/` · `dump_base/` | 五次实机的 `snap_*.png` / `emulog.txt` / `grlog.txt` / `cdvd.log` / `RUN.txt` |
| `work/builds/GR_CAP2400/temp/cmp_3way_f2700.png` 等 | 关键帧对照图 |
| `work/builds/GR_CAP2400/cap_verify_h644_c64.txt` · `cap_charset.log` | 核对与 charset 日志 |

*（本轮**只**写了 `work/builds/GR_CAP2400/**`、`work/tools/cap_*.py`、`docs/CAPACITY_2400.md`、
`tools/font_pipeline/data/charset_compiled_zh16.json`；未 commit / 未切分支 / 未 merge。）*

---

## ★ 收尾出盘（GR_FA2400）—— 成品盘报告见 `docs/CAPACITY_2400_FA2400.md`

> 本节由**收尾出盘**执行者追加（不改上文任何内容）。
> 成品盘 = `work/builds/GR_FA2400/GR_FA2400.iso`（1,648,164,864 B，
> sha256 `f5e4ac42de9147c3c5d068ad36c5ccb70ac6335345199ab6c43fe509d5e262f7`）。
> 全量验收（三闸门 / dump_font / 载荷级旧码扫描 0 处 / 逐字符一致 / 实机 191 截图 · TLB 0 · 无 Trap ·
> 到中文主菜单 / 条目级全盘差异）**逐项结果 + 未达成项 + 你这份报告 §3/§9 的 ASCII 条带问题的
> 精确容量复算（缺 3,168 px ⇒ 现几何搬不动）** 全部写在 **`docs/CAPACITY_2400_FA2400.md`**。
> 另有两条**合并盘遗留缺陷**已在本轮修掉（SFXML 二次迁移 32 单元乱码；槽 1736..1871 的 r84 字形
> 被探针图案覆盖 ⇒ 已从 `GR_F364/F365` 恢复），同样在该文件 §6。

---

## 12. ★★ SKIP=2 重做（ASCII 表安置 / 5 借槽字形 / 文本合并 / 全量验收）

> 执行者：**k2**（关键路径）· 依据 `work/builds/GR_ZH98/temp/LEAD_CAPACITY_2400.md` §16.1 / §16.4 / §15.2 /
> §13 / §14 / §7 / §10.1。写盘范围：`work/builds/GR_FA2400_K2/**`、`work/tools/cap_*.py`（新增
> `cap_build_k2.py` / `cap_verify_k2.py` / `cap_k2_*.py`）、`docs/CAPACITY_2400.md`。
> **未 commit / 未切分支 / 未 merge**；`third_party/orig/**`、历史 ISO、PCSX2 配置只读；
> `tools/font_pipeline/data/charset_compiled_zh16.json` **一个字节都没动**
> （sha256 `7fe2bf5922b5a3505fdf44a93fb9217aadf7a8fb249a327cb9efce4b6eb7fac5`，与 §7 基线相同）。

### 12.0 一句话结论

```
★ 成品盘 = work/builds/GR_FA2400_K2/GR_FA2400_K2.iso
   1,648,164,864 B (804,768 扇区, **与基底同尺寸**) ; sha256 c3851c1d7eb361e3aa8ab8cea36b0ac6d3915c291e695ec77adf4b6316265e94

① 几何: h=644 / **64 列 / SKIP_ROWS=2 / Y0=3** / GATE 0xBA ⇒ 38 行 × 64 = 2,432 格;
   槽 0..2349 占行 0..36; **row37 整行 + row36 col46..63 = 82 格**成为"让出来的那一行", ASCII 表就安置在这里。
② ★ ASCII 字形表 (x≥992 的 63 个矩形 / **182 条记录** / 码位 0x21..0x9C) 全部搬到下方货架,
   **182/182 条逐 texel == 基底** (§16.4-2 达标); 右边缘条带 0 残留、0 越窗。
③ ★ 5 个借槽字形: 2345 按 / 2346 时 / 2347 小 / 2348 击 = handoff bitmap(与基底记录窗逐 texel 相等);
   **2349 ✕ = 自制 16×16** (盘上无现成 ✕/×/X)。
④ 闸门+文本迁移: `migrate_legacy.py --no-elf` 迁移 **3,298 处** (3 个中文容器); ★ **载荷级裸旧码 = 0 处**;
   **逐字符不同 = 0**。
⑤ 实机 6000 帧: **191 截图 / 164 去重画面 (== 基底) / TLB Miss 0 / Trap 0 / 到中文主菜单 (含 △返回 ✕接受 图标)**
   / 跑前跑后无残留进程。
⑥ 全盘差异: **窗口外 0 字节**; ISO 尺寸不变。
⑦ ★ **「拉丁文乱码」根因已消除**: 档案名 `TEQSUNSET` 与基底同帧逐像素对比 —— 除基带自身的
   右边缘采样瑕疵外**完全一致**, 且**比基底更干净** (见 §12.6)。
```

### 12.1 关键设计: 为什么是 `SKIP 3→2` **加上** `Y0 2→3`

§16.1 裁决了 `SKIP_ROWS 3→2`。执行时发现**只改 SKIP 还不够**，两个坑：

| # | 事实（实测） | 后果 |
|---|---|---|
| 坑 1 | 只改 SKIP（Y0 仍 2）⇒ grid row12 由 y=242 **上移到 y=226**，而跳过带里的 EN/ASCII 记录窗是 **y=195..226**（Row A 195..210 + Row B 211..226）⇒ **226 这一行被两边同时采样** | 实测：记录窗含网格墨 **335 条 / 114 个不同矩形**；而且 grid row12 的**整格写入**会把窗内 y=226 的墨**抹掉**（首轮 `[A3]` 就抓到 3 条记录各差 3~4 texel）⇒ ASCII 字形底边会糊/露汉字墨 |
| 坑 2 | 若把 Row B 整体上移 1~2 行，又会压到 Row A / (211,224) 组，需要搬 ~904 px 的窗 | 货架只有 1,312 px，装不下（strip 1,234 px + 904 px） |

★ **解法（1 个额外字节对）**：`SKIP=2` **同时把 `Y0 2→3`**（`V0 = 16·row + Y0`，`V1 = V0+16`）：

```
grid row11 = y 179..194 ; **grid row12 = y 227..242**  ⇒ 跳过带实得 y 195..226 = EN/ASCII 表原封不动 ✓
grid 最后一行 row37 = y 627..642 (≤ 642 < h=644 ✓)
槽 0..2349 占行 0..36 ; 空出的 row36 col46..63 (y 611..626) + row37 (y 627..642) = 货架 A/B
```

⇒ 只有**真正被 64 列压到**的矩形需要搬：**66 个不同矩形 / 218 条记录**（63 个 ASCII 条带矩形中的 59 个
+ (213,229) 组的 5 个 + 10×16「宽空格」1 个 + 2 个 16×16），货架用量 **A 282 px + B 352 px = 634 px / 1,312 px**
（余 678 px）。**「逐 texel 不变」的槽位一个都没牺牲**（2,350 槽全保留，18 格富余仍在）。

ELF 改动 = **8 个字节**（§2.2 那张表 + 本轮新增 2 处）：

| VA | ISO | 前 → 后 | 指令 |
|---|---|---|---|
| `0x004170AC` | `0x003AA92C` | `240E003E` → `240E0040` | `COLS 62→64` |
| `0x004170E8` | `0x003AA968` | `25AD0003` → `25AD0002` | ★ `SKIP_ROWS 3→2` |
| `0x004170F8` | `0x003AA978` | `25CD0002` → `25CD0003` | ★ `Y0 2→3` |
| `0x004170FC` | `0x003AA97C` | `25CE0012` → `25CE0013` | ★ `V1 (V0+16) 18→19` |
| `0x00416EE8` `0x417160` `0x41751C` `0x5656A4` | `0x3AA768` `0x3AA9E0` `0x3AAD9C` `0x4F8F24` | `…B4` → `…BA` | `GATE 0xB4→0xBA` ×4 |

### 12.2 逐条判据（§14 + §16.4 + 任务书，逐项给命令）

产物均在 `work/builds/GR_FA2400_K2/`，取证文本在 `temp/`。

| 判据 | 命令 | 结果 |
|---|---|---|
| **(a) 图集三闸门** | `python work\tools\cap_verify_k2.py --iso …\GR_FA2400_K2.iso --allpat …\GR_FA2400_K2_allpat.iso --tag k2_final` | `w=1024 <1025 ✓` / `px_size 329744 == w*h/2+16 ✓` / `(w*h/2)%2048==0 ✓` / `px_size ≤ 329,744 ✓` / 容器 329,744 B / 11 段 / payload 329,200 ✓ |
| **(b) dump_font** | 同上（脚本运行时把 `tcslib.NCOL=64 / GRID_SKIP_ROWS=2 / GRID_Y0=3 / LEAD_HI=PAIR_LEAD_HI=0xBA` 改到本盘几何） | 见下表「保留槽 / 有字形槽分开计数」；`V1_max=627 ≤ 644`；槽 0..2349 越界 0 / 格位重复 0 |
| **(c) 载荷级旧码扫描 = 0** | `python work\tools\migrate_legacy_audit.py work\builds\GR_FA2400_K2\GR_FA2400_K2.iso --ref-iso …\_geom.iso --gate 0xBA --base-gate 0xB1` | 3 个中文容器 `0xB1..0xB9 单字节位 = **0 处** ✓`；`逐字符不同 = **0** ✓`；`⇒ 总判据全部通过` |
| **(d) ASCII 表 182 条** | `cap_verify_k2.py`（[4] 段 + `temp/dump_k2_final/ascii_182_records.json`） | **182/182 条「记录 → 新矩形 → 逐 texel == 基底」✓**（63 矩形；170 条被搬、12 条原位） |
| **(e) 实机 6000 帧** | `python work\tools\cap_run.py --iso …\GR_FA2400_K2.iso --dump …\temp\dump_final` + `python work\tools\cap_results.py …\temp\dump_final …\temp\dump_base` | **191 截图 / 164 去重画面（== 基线 164）/ `TLB Miss` 0 / `Trap exception` 0 / needle 2,885 / cdvd 50,819 事件 · f0..5861 · maxLBA 804,765 / 跑后残留进程 无 ✓ / 到中文主菜单（`dump_final/snap_f00004500.png`：训练…制作组 + 底栏「学习游戏的基本操作。」+ △返回 ✕接受）** |
| **(f) 拉丁文实拍** | `python work\tools\cap_k2_latin.py --base-dump …\dump_base --new-dump …\temp\dump_final` | `latin_f2700_cmp.png` / `latin_report.json`；见 §12.6 |
| **(g) 全盘差异** | `python work\tools\cap_k2_diff.py --final …\GR_FA2400_K2.iso --base …\GR_ZH124.iso` | 计划窗口 12 个；**窗口内 56,572,034 B / 窗口外 0 B ✓**；`Δ 尺寸 = +0 B` |
| **槽 0..2349 全可寻址闭环** | `cap_verify_k2.py` [5b]（`--allpat` 盘） | **2,350/2,350 槽图案解码回槽号 ✓** |

**(b) 保留槽 / 有字形槽分开计数**（`temp/dump_k2_final_full` 与 `…_live` 两次 dump_font）：

| charset 口径 | 采样窗 | 错误 | 空白 | 截断 | 越窗 | 警告 | 判定 |
|---|---|---|---|---|---|---|---|
| 全量 `pair_of 2350` | 2,894（对偶 2350 + FT 544） | **473** | 473 | 64 | 0 | 2 | 473 = **保留槽 473 个**（1872..2344） |
| 只含**有字形槽** 0..1871 | 2,416（对偶 1872 + FT 544） | **0** | 0 | 0 | 0 | 2 | **ok ✓** |

⇒ 有字形槽 **1,877 个**（现役 1,736 + r83/r84 136 + 借槽 5）**0 错**；保留槽 473 个按 §7/§15.5 登记
**「槽位就绪、字形待补」**（空模板 = 全透明 0x11，不写可辨图案，避免任何界面出现方块）。

★ **「缺字形 0」的独立证据**：对成品盘 3 个容器的载荷做闸门口径扫描，**文本引用到的对偶槽只有
0..1735 与 2345..2349**（MENU/GR 各 1,131 个槽、SF 1,381 个槽），**落在保留段 1736..2344 的 = 0 个** ✓
⇒ 保留槽不会被渲染 ⇒ 实机不会出现空白字（`cap_verify_k2.py` [2b]）。

### 12.3 5 个借槽字形（§10.1 / §15.2）

| 槽 | 字/码 | 来源 | 图集格 (新映射) | 墨 | 证明 |
|---|---|---|---|---|---|
| 2345 | 按 (0xB9) | `glyph_handoff.json` bitmap | (656, 611) | 69 | bitmap **逐 texel == 基底记录 (176,195,192,211)** ✓ |
| 2346 | 时 (0xB8) | 同上 | (672, 611) | 60 | == 基底记录 (160,195,176,211) ✓ |
| 2347 | 小 (0xB7) | 同上 | (688, 611) | 31 | == 基底记录 (144,195,160,211) ✓ |
| 2348 | 击 (0xB6) | 同上 | (704, 611) | 58 | == 基底记录 (128,195,144,211) ✓ |
| 2349 | ✕ (U+2715, 代码 0xB5) | ★ **自制 16×16** | (720, 611) | **25** | 见下 |

* ★ bitmap 口径已实证：`handoff` 的 `bitmap` 里 **0 = 墨**（5/5 条目与基底记录窗逐 texel 相等，
  见 `temp/k2_glyphchk.txt`）—— JSON 里那句「0 = 透明/背景」是**反的**，本报告以实测为准。
* **新映射重算**：handoff 的 `target_cell` 是按 `SKIP=3` 给的 (y=626)；本轮 `SKIP=2 + Y0=3` ⇒
  槽 2345..2349 = row36 col41..45 ⇒ **格 (656..720, y=611)**（不是 626）—— 已按新映射落盘并回读。
* **✕ 自制件规格**（§15.2 要求的画法/阈值/原点/墨量）：
  `画框 = 格内 row 1..13 / col 1..13`（与 r84 手绘 △「slot 1504」同一画框，见 `temp/k2_glyphchk.txt`）；
  `两条 45° 1px 对角线 (1,1)→(13,13) 与 (13,1)→(1,13)`；`阈值 = 二值（墨/背景，无灰度）`；
  `原点 = 格左上角 (0,0)`；`墨 = 25 texel`（13+13−1，中心点共享）。**盘上确实没有现成的 ✕/×/X 字形**
  （charset 里只有 `✕`=2349 自己这一条；`×`/`X`/`⨯` 都不在 charset）⇒ 按 §15.2 自制。
  *（备选口径：`CAPACITY_2400_FA2400.md` §3.2 用的是 `render16(方正像素16.ttf,'×')`（墨 17）。
  两者都符合 §15.2；本轮用 1px 线框自制件，与 △ 线宽一致。切换只需改 `cap_build_k2.py::xmark()` 一处。）*

### 12.4 r83/r84 槽 1736..1871：**136 个真字形已恢复**（不重犯合并盘那次覆盖）

`GR_ZH124`（h=512/62 列）只能寻址 0..1735 ⇒ 槽 1736..1871 在它上面**本来是空的**；
但 §7 明确「1,504..1,871 = r83(232)+r84(136) **已落盘的字，逐 texel 不变**」，且
`CAPACITY_2400_FA2400.md` §6.2 记录过「合并盘曾把这 136 个字覆盖成探针图案」。

本轮做法：**从 `GR_F364` 逐 texel 取回**（`--r84-from`）：

```
[GR_F364 vs GR_ZH124] 槽 0..1735 逐 texel 相同 1736/1736 ✓  ⇒ GR_F364 是基底的严格超集
[恢复] 槽 1736..1871 共 **136 个**字形 (墨 47..111) 全部有墨
[断言 A2] 新盘 1736..1871 逐 texel == GR_F364 ✓ ; [R4 回读] 136/136 ✓
[独立复核] cap_verify_k2.py [5] 段直接对比成品盘 vs GR_F364: **136/136** ✓
```

⇒ 有字形槽 = 0..1871 + 2345..2349（**1,877**）全部就位；保留段收窄为 **1872..2344（473 个）**。

### 12.5 与文本层合并（§13 第 3 步）

```
python work\tools\migrate_legacy.py work\builds\GR_FA2400_K2\GR_FA2400_K2_geom.iso \
       work\builds\GR_FA2400_K2\GR_FA2400_K2.iso --no-elf \
       --skip ES_STRINGS.RES@MENU --skip ES_STRINGS.RES@GR \
       --skip FR_STRINGS.RES@MENU --skip FR_STRINGS.RES@GR
```

* `--no-elf` ✓（源盘 4/4 站点 imm 已 == 0xBA —— 由几何路设好；工具自检通过后才继续）
* 迁移 **3,298 处**；逐码 `0xB1:73 0xB2:456 0xB3:424 0xB4:447 0xB5:42 0xB6:524 0xB7:463 0xB8:486 0xB9:383`
* 3 个中文容器：`EN_STRINGS.RES@MENU` 帧 32,696→32,847（槽 47,570 余 14,723）·
  `EN_STRINGS.RES@GR` 32,697→32,848（槽 47,619 余 14,771）· `EN_SPECIAL_FEATURE.XML` 41,307→41,443（槽 49,700 余 8,257）
  ⇒ **条目表（off/stored/real）一个字段未动** ✓，ISO 尺寸不变 ✓
* `[S8]` 全盘差异 104,156 B 全部落在 3 个计划窗口内 ✓

### 12.6 ★ 判据 (f)：`TEQSUNSET` 实拍逐像素对比（含"为什么与基底不同"的完整归因）

**取证**：`temp/latin_f2700_cmp.png`（上=基底 / 中=成品 / 下=差异，4×）、`temp/latin_report.json`。

```
f2700  裁剪 (104,104,216,156): 不同像素 106 / 5824
f1500  0 / 5824 ✓ 逐像素相同      （该帧该裁剪区两侧墨量均为 0 = 无字区域）
f2280  0 / 5824 ✓ 逐像素相同      （"正在读取数据…" 行，墨量 1,855 == 1,855）
```

**这 106 px 是什么？** 逐像素放大后（`temp/_name_zoom.png`）事实是：

| 盘 | 档案名行 (y119..133, x120..199) |
|---|---|
| 基底 `GR_ZH124` | `[残缺装饰][TEQSUNSET 整体右移 8px]` —— 首个 `T` 的**横杠被装饰吃掉**，两端各有一块**无法在图集里找到对应**的碎墨（26/25 texel） |
| 成品 `GR_FA2400_K2` | **`TEQSUNSET` 九个字母完整、清晰、无碎墨**（首字母 T 的横杠齐全） |

★ **单变量归因（这是 §16.4-1 要求的"与基底同帧逐像素对比"的完整答案）**：

| 对照 | f2700 差异 | 结论 |
|---|---|---|
| 基底 vs 基底（复跑） | **0 px** | 模拟器对同一盘是确定性的（`temp/dump_base_rerun`） |
| 基底 vs **nogate 控制盘**（h644/64列/SKIP2/Y0=3/ASCII 搬迁，**GATE 保持 0xB4**） | **106 px（与上一行完全相同）** | 差异 100% 来自**几何** |
| nogate 控制盘 vs **成品盘**（只差闸门 0xBA + 文本迁移） | **0 px**（全 191 帧） | **闸门 + 文本迁移的像素贡献 = 0** |

⇒ 那 106 px 是**基底自身的右侧边缘采样瑕疵**：涉及的字形记录矩形 **u1 = 1024（正好贴图集右边界）**
（`T`=0x54 rect(1016,192,1024,208)、`(`=0x28 rect(1016,16,1024,32) 等）。本轮把这批字形整体搬到
**货架 (u1 ≤ 1010)** ⇒ **瑕疵消失**。同类证据还有 f2220..f2340（"…记忆卡(8M / (for PlayStation® 2)…"
里的 `(`/`8`/`P`）：基底是糊的、成品是干净的（`temp/_f2280_cmp.png`）。

**实机 191 帧分类（成品 vs 基底，全帧逐像素）**：127/191 张**逐字节相同**；64 张不同，构成：

| 类别 | 张数 | 说明 |
|---|---|---|
| h 抖动（f660/690/720/750/780/810） | 6 | **h=644 的既有现象**：round86/F364 的 h=640 盘记录过同样 6 张（§6.1），与 SKIP/ASCII 无关 |
| 右边缘采样瑕疵修好（f2220..f2340） | 5 | 基底糊 → 成品干净（§12.6 的同一类） |
| 档案名行瑕疵修好（f2490..f3300） | 28 | 每张 106 px（同 §12.6） |
| 场景时序分叉（f1890/1920/1950） | 3 | 与 A 路 `GR_CAP2400` 记录的同一现象（整帧差异，非字形） |
| 小幅抖动（f1230..f1860，6..35 px） | 22 | ★ **模拟器 run-to-run 抖动**：同一帧在两次自跑之间也有 1..16 px 差 |

⇒ **ASCII 表损坏（A 路探针盘 f2490..f3300 每张 473 px）已归零** ✓

### 12.7 未达成项 / 已知缺陷（如实登记）

| # | 项 | 状态 | 证据 / 处置 |
|---|---|---|---|
| 1 | **§15.3 的 ES/FR 语言表迁移** | ⛔ **未达成（被容量卡住）** | `ES_STRINGS.RES@MENU` 需 +28 B 而 `used_end` 之后陈旧尾巴只有 8 B（差 20）；`FR_STRINGS.RES@MENU` 需 +29 B / 尾巴 8 B（差 21）。解压总长被 IMG 条目表 `real` 钉死，`migrate_legacy.py` **拒绝改条目表**。⇒ 本轮 `--skip` 了 ES/FR 四个拷件；**残留 114 处**（ES 56 + FR 58）。**若主机语言 = ES/FR，抬闸门后这些裸字节仍会吞后一字节** ⇒ 需 Lead 决定结构性扩容（改 `stored/real` + 搬移后续数据）或接受 |
| 2 | DE/IT 语言表 | ⛔ 已知缺陷（§15.3 明确不动） | 解析失步（`unpack_from requires a buffer of at least 19`）；残留 150 处（DE 74 + IT 76） |
| 3 | 保留槽 473 个（1872..2344）只有占位字符、无字形 | 如实登记 | §7/§15.5 的既定策略；**当前文本 0 引用**（§12.2 [2b]）⇒ 实机无空白字 |
| 4 | `h ∈ [648, 656]` 未测 | 未达成（沿用 A 路结论） | 本方案在 h=644 下已达标，无需更高 h |
| 5 | 实机只跑 6000 帧 + 固定导航 | 如实登记 | 与 A 路/基线同一口径 |
| 6 | 4 处 SFXML `U+FFFD` | **源盘既有**（非本轮引入） | `migrate_legacy.py` [S6] 逐处登记（`@0x545E/0x5FA6/0x65F8/0x6962`） |
| 7 | "闸门+文本迁移像素贡献"的空档复跑 | 部分未达成 | 决定性对照在 r84 恢复**之前**完成（nogate vs 成品 = 0 px / 191 帧）；r84 恢复后成品 vs 旧控制盘出现 **25 帧 ≤16 px** 的差异，归因于**模拟器 run-to-run 抖动**（同帧在自跑间也有 1..16 px；两次跑的 cdvd 帧跨度 0..5861 vs 0..5863 不同）。**同盘复跑的空档实测未做**：另一路（`GR_MEMDRIFT`、80,000 帧）的模拟器实例当时正在占用，按"一次只跑一个实例"纪律不并发 |

### 12.8 用户实机验收要点（交给 Lead / 用户）

1. **看档案名**：记忆卡界面档案名应是**干净的 `TEQSUNSET`**（基底上原本两端有碎墨、首字母 T 缺横杠 —— 那是旧盘瑕疵，本轮顺手修好）。
2. **看 ASCII**：菜单里的数字/大写字母/标点（`(8M`、`PlayStation® 2`、`—空—` 等）应当**清晰无糊边**。
3. **看 5 个借槽字**：文本里出现 **按/时/小/击** 的地方必须有形（这几字原先是单字节码 0xB6..0xB9）；
   提示栏里的 **✕** 与 △ 一样要能出来（△ 走的是引擎图标路径，✕ 用 slot 2349 的自制字形）。
4. **看图标**：`△返回 / ✕接受`（快捷键系统的彩色精灵，与字库无关）必须照旧。
5. **注意已知缺陷**：若把主机语言切到 **ES/FR/DE/IT**，那 4 张语言表里还有 324 处裸旧码会吞字节（§12.7 #1/#2）；
   **主线（中文/英文界面）不受影响**。
6. 未测项：h∈[648,656]；长导航/深菜单（本轮与基线同一口径：6000 帧 + 固定导航）。

### 12.9 本轮工具 / 产物索引（全部可重跑）

```powershell
# ① 只读侦察 (FONT.RES 结构 / 污染面 / 空地账 / 借槽字形核对)
python work\tools\cap_k2_recon.py      # temp/k2_recon.txt
python work\tools\cap_k2_records.py    # temp/k2_records.txt  (544 条记录逐条)
python work\tools\cap_k2_space.py      # temp/k2_space.txt    (占用/污染/空闲)
python work\tools\cap_k2_bleed.py      # temp/k2_bleed.txt    (格内逐行墨分布)
python work\tools\cap_k2_glyphchk.py   # temp/k2_glyphchk.txt (handoff bitmap vs 基底)
# ② 造盘 (10 条硬断言 + 回读 + 全盘差异窗口)  ★ 复用 cap_build.py 的容器/图案/比对内核
python work\tools\cap_build_k2.py                    # → GR_FA2400_K2_geom.iso + _allpat.iso
python work\tools\cap_build_k2.py --keep-gate --tag k2_nogate `
       --out work\builds\GR_FA2400_K2\GR_FA2400_K2_nogate.iso            # 单变量对照
# ③ 合并 (闸门已设好, 必带 --no-elf)
python work\tools\migrate_legacy.py work\builds\GR_FA2400_K2\GR_FA2400_K2_geom.iso `
       work\builds\GR_FA2400_K2\GR_FA2400_K2.iso --no-elf --skip ES_STRINGS.RES@MENU `
       --skip ES_STRINGS.RES@GR --skip FR_STRINGS.RES@MENU --skip FR_STRINGS.RES@GR
# ④ 全量核对
python work\tools\cap_verify_k2.py --iso work\builds\GR_FA2400_K2\GR_FA2400_K2.iso `
       --allpat work\builds\GR_FA2400_K2\GR_FA2400_K2_allpat.iso --tag k2_final
python work\tools\migrate_legacy_audit.py work\builds\GR_FA2400_K2\GR_FA2400_K2.iso `
       --ref-iso work\builds\GR_FA2400_K2\GR_FA2400_K2_geom.iso --gate 0xBA --base-gate 0xB1
python work\tools\cap_k2_diff.py --final work\builds\GR_FA2400_K2\GR_FA2400_K2.iso `
       --base work\builds\GR_ZH124\GR_ZH124.iso
# ⑤ 实机 (串行独占) + 判据 + 拉丁实拍
python work\tools\cap_run.py --iso work\builds\GR_FA2400_K2\GR_FA2400_K2.iso `
       --dump work\builds\GR_FA2400_K2\temp\dump_final
python work\tools\cap_results.py work\builds\GR_FA2400_K2\temp\dump_final `
       work\builds\GR_CAP2400\temp\dump_base
python work\tools\cap_k2_latin.py --base-dump work\builds\GR_CAP2400\temp\dump_base `
       --new-dump work\builds\GR_FA2400_K2\temp\dump_final --frames 2700,1500,2280
```

| 产物 | 说明 | 尺寸 / sha256 |
|---|---|---|
| `work/builds/GR_FA2400_K2/GR_FA2400_K2.iso` | ★ **成品盘**（几何 + 5 借槽字形 + ASCII 表 + 文本迁移） | 1,648,164,864 B · `c3851c1d7eb361e3aa8ab8cea36b0ac6d3915c291e695ec77adf4b6316265e94` |
| `…/GR_FA2400_K2_geom.iso` | 几何盘（未合文本；供复核/重跑合并） | `1ea161e2f602d07f6baa94399d34e0827e44b6d13024dc79eef973b12782ad9f` |
| `…/GR_FA2400_K2_allpat.iso` | 全 2,350 槽写图案的**寻址证明盘**（不跑模拟器） | `91e0cdb96d85cfbbfdb09842c0cc56fafcb3b3fdbd1df58fe17846f804e6881e` |
| `…/GR_FA2400_K2_nogate.iso` | **单变量对照盘**（GATE 保持 0xB4，其余同成品几何） | `f34b35e9859864283dfcebb890450293b675675d265a848ed3d74c2e6015d385` |
| `…/temp/dump_final/` · `dump_nogate/` · `dump_base_rerun/` | 三次实机取证（snap_*.png / emulog.txt / grlog.txt / cdvd.log / RUN.txt） | — |
| `…/temp/dump_k2_final_full/` · `…_live/` | dump_font 全量 / 有字形槽两组 | — |
| `…/temp/latin_f2700_cmp.png` · `latin_report.json` · `ascii_182_records.json` | 拉丁实拍对照 / 182 条 ASCII 证明 / 逐条明细 | — |
| `…/cap_build_k2.log` · `cap_verify_k2_final.txt` · `cap_results_k2_final.txt` · `cap_k2_diff.txt` | 全部断言原文 | — |

*（本轮**只**写了 `work/builds/GR_FA2400_K2/**`、`work/tools/cap_build_k2.py` · `cap_verify_k2.py` ·
`cap_k2_*.py`（并给 `work/tools/cap_build.py::compare_windows` 加了一个**向后兼容**的 `extra=()` 参数）、
`docs/CAPACITY_2400.md`；charset / 文本工具 / `third_party/**` 均未改动；未 commit / 未切分支 / 未 merge。）*
