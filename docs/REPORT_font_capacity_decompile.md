# REPORT_font_capacity_decompile.md — 字库容量上限的**反编译**逆向（round73）

> ⚠ **历史错误断言订正（2026-10-18 收尾轮）**：本文含已被实测/实机否证的表述 —— 见 `docs/CORRECTIONS.md` §5。
> 原文保留作过程记录；**结论冲突时以 `docs/CORRECTIONS.md` + `docs/STATUS.md` 为准**。

> 分支 `round73/font-decompile`（未切分支、未 commit、未 merge）。执行者 = 反编译子代理。
> 工具：Ghidra 12.1.2 headless（`work/tools/gh.bat`）+ 自写 MIPS/EE 解码器（Python/Java）。
> **只读**：所有 ISO / ELF / `tools/text_csv/*` / `tools/font_pipeline/*` / `charset_compiled_zh16.json`。
> **只写**：`docs/REPORT_font_capacity_decompile.md`、`work/tools/ghidra_scripts/Font*.java`、
> `work/builds/GR_ZH98/temp/r73/**`。
> 未做探针盘（原因见 §9-1），未占用任何 `GR_ZH<数字>` 号。

---

## 0. 一句话结论

**「1504」不是引擎上限，是汉化自己写的常量。** 整条 DBCS 判定 / 字符解码 / 字形寻址 /
网格公式**全部是汉化补丁自己写进 ELF 的代码**（原文的 `RSFont::ComputeCharTextureCoords`
只认单字节记录表，根本没有网格）。因此：

| 结论 | 值 |
|---|---|
| 图集尺寸（1024×512）是**资源里带的**，ELF 里**没有任何** 1024/512 常量 | ★ **可放大贴图** |
| 对偶码容量 = `(gate − 0xA1) × 94`，`gate` 是汉化代码里的**立即数** `0xB1`（4 处） | ★ **可抬 gate** |
| 当前盘 `GR_ZH113b`：对偶码 **1504/1504 已用满**，单字节带 **110/110 用满** | 实际需求缺口 = **364 字**（`REPORT_expand_font_329` §3.3） |
| **推荐路线**：图集 1024×512 → **1024×1024** + gate `0xB1` → `0xB5` + 给网格行 ≥25 加 2 行跳空 | **+376 槽（净 ≈ +372）** ⇒ 总容量 **1876** 对偶码 |
| 若还要余量：把 trail 下界 `0xA1` → `0x40`（stride `94` → `191`） | 每个 lead **+97**（×2 容量），无需再动 gate |

---

## 1. 方法与工具（可复现）

| 脚本 | 作用 |
|---|---|
| `work/tools/ghidra_scripts/FontSites.java` | 符号表筛查 + **全段立即数扫描** + 字面量 xref |
| `work/tools/ghidra_scripts/FontRaw.java` | **与反汇编无关的裸字节模式扫描** + 自带 MIPS/EE 解码器逐条打印 |
| `work/tools/ghidra_scripts/FontDecomp.java` | 批量反编译 + 调用者 + 邻近指令 |
| `work/tools/ghidra_scripts/FontDeep.java` | 单函数深挖（**超时 900 s**；实测 120 s 会静默返回空 C） |
| `work/builds/GR_ZH98/temp/r73/r73_elf_diff.py` | **原版 ELF ↔ 现役 ELF 全文件差分**（本次最关键的证据来源） |
| `…/r73_capacity.py` / `r73_band_census.py` / `r73_slot_ink.py` | 只读容量/占用普查 |
| `…/r73_probe_bytes.py` / `r73_hardcoded_offsets.py` | 字节核对 / 硬编码偏移搜索 |

**Ghida 语言**：新建项目 `GRLocEE`，用 `-processor r5900:LE:32:default`
（插件 `ghidra-emotionengine-reloaded`，已解压到 `work/tools/ghidra/Ghidra/Extensions/`）。
默认 `MIPS:LE:64:64-32R6addr` 会把 MMI 指令显示成 `special2(...)`/`halt_baddata()`，
**换 EE 语言后 `lq/sq` 等 EE 指令正常解码**（见 `ee_decomp` 输出里的 `_moveq`/`lq`）。

> ⚠ **坑（已踩并绕过）**：`work/tools/ghidra_proj/GRLoc` 里那份 `SLUS_206.13.elf`
> **不是现役 ELF** —— 它在字库 code cave 区与盘上字节不同（例：VA `0x4170F4` 项目内是
> `00007071`，现役 ELF 是 `00007012 mflo t6`）。所以**所有代码结论都以磁盘上的 ELF 字节为准**
> （我用 `r73_probe_bytes.py` 独立复核，并自写解码器逐条解码），Ghidra 只用来拿符号名与 C。

---

## 2. A —— 贴图尺寸是硬编码还是资源？（**最大的一根杠杆**）

### 2.1 结论：**完全是资源驱动的。ELF 里没有 1024 / 512 这两个常量。**

### 2.2 反编译实证①：PAK 记录解析器（`UITextureMgr::LoadingTexturePak`，VA `0x51B660`）

反编译原文（`work/builds/GR_ZH98/temp/r73/deep_part.txt` L53–L133，节选）：

```c
  lVar3 = diSearchFile(acStack_82c0);          // "common.pak" (kind 0)
  if (-1 < lVar3) {
    iStack_82d0 = 0;
    __ct__9idistreamFi(auStack_8180,1);
    read__...(auStack_8180,&iStack_82d0,4);              // u32 record type
    while (iStack_82d0 != 99) {                          // 0x63 = 结束哨兵
      read__...(auStack_8180,&iStack_82cc,4);            // u32 nameLen
      read__...(auStack_8180,auStack_81c0,iStack_82cc);  // name
      ...
      if (iStack_82d0 == 0) {                            // type 0 = 纹理
        *(undefined1 *)(iVar5 + 0x2a) = 0;
        read__...(auStack_8180, iVar5 + 8,   4);         // ★  iVar5[+0x08] = psm
        read__...(auStack_8180, iVar5 + 0x10, 4);        // ★  iVar5[+0x10] = w
        read__...(auStack_8180, iVar5 + 0x12, 4);        // ★  iVar5[+0x12] = h
        iStack_82c8 = 0;
        read__...(auStack_8180, &iStack_82c8, 4);        //    clut_size
        if (iStack_82c8 != 0) { ...nwa...read(clut)... }  //    CLUT 数据
        read__...(auStack_8180, &iStack_82c4, 4);        //    px_size
        uVar2 = __nwa__FUi(iStack_82c4);
        *(undefined4 *)(iVar5 + 0x1c) = uVar2;
        read__...(auStack_8180, *(undefined4 *)(iVar5 + 0x1c), iStack_82c4);
        iVar4 = (uint)*(ushort *)(iVar5 + 0x10) * (0x10000 / *(ushort *)(iVar5 + 0x10)) * 4 + 0x10;
        *(int *)(iVar5 + 0x30) = iStack_82c4 + ((iStack_82c4 + iVar4 + -1) / iVar4) * -0x10;
      }
```

**⇒ `psm` / `w` / `h` / `clut_size` / `px_size` 全部从 `COMMON.PAK` 记录里读进
`UITexture` 对象（+0x08/+0x10/+0x12），像素容器长度 `px_size` 也是读出来的。**
**没有任何一处代码把 1024 或 512 写进纹理几何。**

### 2.3 反编译实证②：psm 分支

同文件 L122：

```c
if ((*(int *)(iVar5 + 8) == 0x13) || (*(int *)(iVar5 + 8) == 0x14)) {
    read__...(auStack_8180, iVar5 + 0x4c, 4);      // CLUT 长度
    ... read(clut) ...
}
```
⇒ 引擎**按资源里的 psm 决定要不要读 CLUT**（PSMT8 `0x13` / PSMT4 `0x14`）。
现役盘 psm = `0x14`（`r73_capacity.py` 实测），**原版是 `0x13`**。

### 2.4 反编译实证③：全 ELF 差分 —— 汉化一共只改了 567 个 4 字节字

`r73_elf_diff.py`（原版 `third_party/orig/ps2/slus_out/SLUS_206.13` ↔ 现役 r72 ELF）：

```
=== 567 differing 4-byte words over 5106944 bytes (0.0444%) ===
=== 50 changed ranges (coalesced, gap<=16B) ===
```

**改动全部集中在**：
* 文本/字体模块 `0x219A70..0x21D948`（`RSFontMgr` / `RSFont` / `RSTextComponent`）
* 汉化自己的 code cave：`0x407078` / `0x408928` / `0x411690` / `0x416ED0..0x4176E8` / `0x565670..0x565A48`
* 少量 UI 常量（`0x1FF8D0` / `0x2071B4` / `0x216578` / `0x22E218` / `0x2BEE5C` / `0x2DE5A4` / `0x3070B4`）
* ELF 内嵌英文字符串表改成中文：`0x577FA0..0x578074`

**⇒ 纹理加载器 / 显存分配 / GS 上传路径一处都没改**（唯一在 `0x51xxxx` 的改动是
`0x519AC8 beq a2,v1 → nop`，位于 `UIPacket::SetLinearSampling`，是**采样滤波**开关，与尺寸无关）。

**⇒ 原版 PSMT8 512×512 改成 PSMT4 1024×512 而工程能在实机跑通**，这一事实本身就证明
**尺寸/格式/像素容器全部由数据决定**。

### 2.5 反编译实证④：字形寻址代码里**没有**宽度/高度

汉化的网格公式 cave（§3 全文）只出现 `94 / 62 / 16 / 2 / 12 / 3 / 0xE0`，
**一处 1024 或 512 都没有**。`RSFont::ComputeCharTextureCoords` 输出的是**纹素坐标的 float**
（`mtc1 → cvt.s.w → swc1`），不做任何归一化除法（不除以宽高）。

### 2.6 那么"放大贴图"具体能多放多少字？（数字）

现役图集 **1024×512 PSMT4**，网格公式 `yrow(r) = 2 + 16·(r + 3·[r≥12])`。
放进 1024 高的贴图后（`r73_capacity.py` 实测输出）：

| 贴图高 h | 可容纳网格行 | 网格总格 | 相对现役最后一行(row 24) 之上的行 | 原始新增格 |
|---|---|---|---|---|
| **512（现役）** | 0..27（28 行） | 1736 | 3 行 | 186 |
| **768** | 0..43（44 行） | 2728 | 19 行 | **1178** |
| **1024** | 0..59（60 行） | 3720 | 35 行 | **2170** |
| 1280 | 0..75（76 行） | 4712 | 51 行 | 3162 |
| 2048 | 0..123（124 行） | 7688 | 99 行 | 6138 |

但**不是全部可用**：

* 网格行 **25、26**（y=450 / 466）被 **ASCII/符号带**（FT 记录 v0/v1 = 452/468）占着 ⇒ 必须留给它；
* 网格行 **12、13、14** 是**图标带**（△/✕ 硬编码 UV `(1,198)-(21,218)` / `(25,198)-(45,218)`，
  见 §3.4）⇒ 现役的 `+3` 跳行就是为它让路；
* 现役行 0..24 已被 slot 0..1503 占满（其中行 24 只用到 col 15，**col 16..61 共 46 格被浪费**）。

**⇒ 1024 高贴图的实际可用新格 = 行 27..59（33 行 × 62）= 2046 格。**
**⇒ 768 高贴图 = 行 27..43（17 行 × 62）= 1054 格。**

（另见 §5 的 `README` 口径：`h=1024` 时 512..1023 的新行只要保证零墨，历史内容一位不动。）

---

## 3. B —— `62 / 16 / 3 行间隔 / 512` 这些常量在哪

### 3.1 ★ 先定性：**这些常量全在汉化自己的 cave 里，不在引擎里**

`r73_elf_diff.py` 显示 VA `0x417050..0x417130` 在**原版里是另一个函数的正常代码**
（`move a0,s1` / `jr ra` / `addiu sp,sp,0xD0` …），现役被汉化**整段重写成网格公式**。
同时 `RSFont::ComputeCharTextureCoords`（VA `0x21ADE0`）的**头两条指令被换成 `j 0x417050`**：

```
原版 0x21ADE0  8C8A0028  lw   t2,0x28(a0)      →  现役 08105C14  j 0x00417050
原版 0x21ADE4  30A300FF  andi v1,a1,0x00FF     →  现役 00000000  nop
```

### 3.2 网格公式 cave 逐条（现役 ELF 字节，自写解码器）

```
0x417050  8C8A0028  lw   t2,40(a0)          ; t2 = this->mFontDef  (RSFont+0x28)
0x417054  30A300FF  andi v1,a1,0x00FF       ; v1 = 低字节 (trail / 单字节码)
0x417058  00056202  srl  t4,a1,8            ; t4 = 高字节 (0 ⇒ 单字节码)
0x41705C  15800006  bne  t4,zero,0x417078   ; ★ 高字节≠0 ⇒ DBCS 网格分支
0x417064  81450020  lb   a1,32(t2)          ; 单字节: def+0x20 = face 首字符
0x417068  00651823  subu v1,v1,a1
0x41706C  306500FF  andi a1,v1,0x00FF       ; idx = code - base
0x417070  10000009  b    0x417098
------------------------------- DBCS 分支 -------------------------------
0x417078  318C00FF  andi t4,t4,0x00FF
0x41707C  258CFF5F  addiu t4,t4,-161        ; t4 = lead - 0xA1
0x417080  306D00FF  andi t5,v1,0x00FF
0x417084  25ADFF5F  addiu t5,t5,-161        ; t5 = trail - 0xA1
0x417088  240E005E  addiu t6,zero,94        ; ★★ stride = 94
0x41708C  018E6018  mult t4,t6
0x417090  018D6021  addu t4,t4,t5           ; t4 = slot = (lead-0xA1)*94 + (trail-0xA1)
0x417094  258500E0  addiu a1,t4,224         ; a1 = slot + 0xE0
0x417098  8D430044  lw   v1,68(t2)          ; v1 = def+0x44 = nrec
0x41709C  00A3102B  sltu v0,a1,v1
0x4170A0  14400024  bne  v0,zero,0x417134   ; ★ (slot+224) < nrec ⇒ 走**记录表**分支
0x4170A8  24ACFF20  addiu t4,a1,-224        ; 还原 t4 = slot
0x4170AC  240E003E  addiu t6,zero,62        ; ★★ NCOL = 62
0x4170B0  018E001A  div  t4,t6
0x4170B4  00006812  mflo t5                ; t5 = row = slot/62
0x4170B8  01AE7018  mult t5,t6
0x4170BC  00007012  mflo t6
0x4170C0  018E6023  subu t4,t4,t6           ; t4 = col = slot%62
0x4170C4  240F0010  addiu t7,zero,16        ; ★★ CW = 16
0x4170C8  018F7018  mult t4,t7
0x4170CC  00007012  mflo t6                ; t6 = 16*col
0x4170D0  25C50000  addiu a1,t6,0           ; u0 = 16*col
0x4170D4  25CC0010  addiu t4,t6,16          ; u1 = 16*col + 16
0x4170D8  240F000C  addiu t7,zero,12        ; ★★ SKIP_ROW = 12
0x4170DC  01AF782A  slt  t7,t5,t7
0x4170E0  15E00002  bne  t7,zero,0x4170EC
0x4170E8  25AD0003  addiu t5,t5,3           ; ★★ SKIP_ROWS = 3   (row += 3)
0x4170EC  240F0010  addiu t7,zero,16        ; CH = 16
0x4170F0  01AF7018  mult t5,t7
0x4170F4  00007012  mflo t6                ; t6 = 16*row
0x4170F8  25CD0002  addiu t5,t6,2           ; ★★ Y0 = 2           v0 = 16*row + 2
0x4170FC  25CE0012  addiu t6,t6,18          ;                       v1 = 16*row + 18
0x417100  44850000  mtc1 a1,f0
0x417104  46800020  cvt.s.w f0,f0
0x417108  E4C00000  swc1 f0,0(a2)           ; *out_u0
0x41710C  448D0000  mtc1 t5,f0
0x417110  46800020  cvt.s.w f0,f0
0x417114  E4E00000  swc1 f0,0(a3)           ; *out_v0
0x417118  448C0000  mtc1 t4,f0
0x41711C  46800020  cvt.s.w f0,f0
0x417120  E5000000  swc1 f0,0(t0)           ; *out_u1
0x417124  448E0000  mtc1 t6,f0
0x417128  46800020  cvt.s.w f0,f0
0x41712C  03E00008  jr   ra
0x417130  E5200000  swc1 f0,0(t1)           ; *out_v1   (延迟槽)
0x417134  8D4A0038  lw   t2,56(t2)           ; 记录表分支: t2 = def+0x38
0x417138  08086B88  j    0x0021AE20         ; ★ 跳回**原版**的记录矩形代码
```

### 3.3 立即数清单（"要改什么"就改这些）

| 常量 | 值 | VA（现役） | 语义 | 能不能改 |
|---|---|---|---|---|
| stride | **94** | `0x417088`（网格本体）/ `0x416F9C`（宽度函数）| `slot=(lead-0xA1)*94+(trail-0xA1)` | ✅ 改了必须**同步**改 trail 下界（§6 L4） |
| NCOL | **62** | `0x4170AC` | `row=slot/62, col=slot%62` | ✅ 但改了**全部**对偶码格位都变 ⇒ 必须重排整张图集 |
| CW / CH | **16** | `0x4170C4` / `0x4170EC` | 格宽/格高 | ⚠ 改了要重渲字形 |
| SKIP_ROW | **12** | `0x4170D8` | 跳行起点 | ✅ |
| SKIP_ROWS | **3** | `0x4170E8` | 跳行数（图标带） | ✅ 见 §6 L3 |
| Y0 | **2** | `0x4170F8` | 首行 y 偏移 | ✅ |
| **512** | — | **不存在** | 贴图高 | **资源里的 `h`**（§2） |
| **1024** | — | **不存在于字库路径** | 贴图宽 | **资源里的 `w`**（§2） |

### 3.4 ★ 特别确认："列数 62 是不是 1024/16 − 2 列回绕？"

**实测语义**：`x = 16·col`，`col ≤ 61` ⇒ `x ≤ 976`，`x1 ≤ 992 ≤ 1024`。
`1024/16 = 64`，**62 = 64 − 2**，留 2 列（32 texel）余量 ⇒ **永不采样 x ≥ 992**。
这与 `docs/FONT_CURRENT_STATE.md` §6.1 的"引擎一行只有 62 格 ⇒ 回绕"记录一致，
但**回绕是历史写盘侧的相位问题，公式本身没有回绕**（`atlas_cell_xy_engine_view` 的注释已订正）。

**加宽到 1280 / 1536 能不能让列数 > 62？**
* 能：`16·col + 16 ≤ w` ⇒ `col_max = w/16 − 1`。1280 ⇒ 79 列；1536 ⇒ 95 列。
* **但纯加宽本身不增容量** —— 容量 = `(gate − 0xA1) × 94`，与列数无关；
  改 NCOL 只会把同一批 slot **重新排布**（少占行数），而且会让**全部 1504 个已用格位错位**，
  必须整张图集重排 + 重渲。
* 加宽的**唯一**收益是"少占行"：1504 slot 在 62 列下要 25 行，在 64 列下只要 24 行，
  在 79 列下只要 20 行。**这个收益应该用"加高贴图"来实现，而不是加宽**（加高不动已用格位）。

---

## 4. C —— 字符 → 字形记录的查找方式

### 4.1 两级查找（反编译 + 反汇编双证）

```
① 输入文本 → 汉化解码器（VA 0x416ED0，被 RSFontMgr::DrawString 的字符循环
   在 0x219BCC 处 jal 进来）：
     0x416ED0  andi a1,a1,0x00FF
     0x416ED4  sh   a1,0(a0)          ; 先按"单字节码"写结果
     0x416ED8  24020001  li v0,1      ; len = 1
     0x416EDC  2CA900A1  sltiu t1,a1,0xA1
     0x416EE0  15200014  bne t1,zero,0x416F34        ; <0xA1 ⇒ 单字节
     0x416EE8  2CA900B1  sltiu t1,a1,0xB1            ; ★★ GATE（上界）
     0x416EEC  11200011  beq t1,zero,0x416F34        ; ≥0xB1 ⇒ 单字节
     0x416F08  91EB0001  lbu t3,1(t7)                ; t3 = 下一个字节 (trail)
     0x416F0C  2D6900A1  sltiu t1,t3,0xA1            ; trail 下界
     0x416F10  15200008  bne t1,zero,0x416F34
     0x416F18  2D6900FF  sltiu t1,t3,0xFF            ; trail 上界
     0x416F1C  11200005  beq t1,zero,0x416F34
     0x416F24  00056200  sll  t4,a1,8
     0x416F28  018B6025  or   t4,t4,t3
     0x416F2C  A48C0000  sh   t4,0(a0)               ; ★ 结果 = u16 码 = lead<<8|trail
     0x416F30  24020002  li v0,2                     ; len = 2
     0x416F34  A082FFFF  sb   v0,-1(a0)              ; ★ (a0-1) = 该字符占几个输入字节
     0x416F38  03E00008  jr ra
```
⇒ **字符 → 码**：`len∈{1,2}` + `u16 code`。**码位空间 = 16 位**（所以不存在 3 字节字符）。

```
② 码 → 字形矩形（VA 0x417050..0x417138，见 §3.2）：
     高字节 = 0            ⇒  记录表： idx = code − (def+0x20)，跳回原版 0x21AE20
     高字节 ≠ 0            ⇒  网格：  slot = (lead-0xA1)*94 + (trail-0xA1)
                                   if (slot + 224 < nrec) ⇒ **也走记录表**（idx = slot+224）
                                   else                   ⇒ 网格公式算 (u0,v0,u1,v1)
```
**⇒ 是"按码位直接算下标"，不是线性扫描、不是分段的表。**

### 4.2 记录表的容量上限（反编译原文）

`RSFontMgr::ReadResourceFile`（VA `0x219380`）反编译（`deep_part.txt` L237–L266）：

```c
    read__...(auStack_8240,&iStack_a0,4);      // fld[4]
    read__...(auStack_8240,&iStack_9c,4);      // fld[5]
    iVar6 = iStack_a0 * iStack_9c;             // ★ nrec = fld[4] * fld[5]
    lVar3 = __nwa__FUi(iVar6 * 10 + 0x10);     // ★ 记录数组 = nrec × 10 字节，运行时分配
    ...
        read(...,1); read(...,1);              //   f0, f1
        for 4: read(...,2);                    //   u0, v0, u1, v1
    ...
    iVar6 = *(int *)(param_1 + 0x10);                                   // 当前 face 数
    IncreaseToSize_Array__25RSArray<14FontDefinition>Fi(param_1 + 0xc, iVar6 + 1);
```

* **记录条数 `nrec` 完全是资源字段**（现役 32×7 = **224 / 224 / 96**，实测 `r73_capacity.py`）。
* 记录数组是 `__nwa` **运行时分配**，**没有 224 上限、没有 4 KB 上限**。
* **face 数也没有上限**：`RSArray<FontDefinition>` 用 `IncreaseToSize_Array` 增长；
  `RSArray<RSFont>`（style 数）同样（L297）。现役 face = 3、style = 8。

### 4.3 那"加记录"能不能换来容量？—— **不增容量，而且路被堵死**

* **不增容量**：记录只是改"某个码位画哪块矩形"。码位总量仍受 gate/trail 限制。
* 唯一诱人的用法是**让对偶码也走记录表**（把 `nrec` 抬到 `224 + 1504 = 1728`），
  这样字形可以摆在图集**任意位置**（含跳过带、含 y480..495 的 12px 带）。
* **但 `FONT.RES` 里的记录数据必须真的存在**（L238 按 `nrec*10` 分配、L246-262 按 `nrec`
  逐条 `read`）。而 `FONT.RES` 是 `MENU.IMG` 的**第 4 个条目**，其 stored 长度 4421 B
  （展开 5942 B）—— 加 1504 条记录 = 展开 +15040 B，LZO 后约 +11 KB。
* 历史记录 `docs/REPORT_names_and_12px.md` §二·发现 2 记着"`MENU.IMG` 内部偏移不可移动"，
  并实测**平移尾部数据会卡死在记忆卡界面**；同文"已排除的方案"表里写着
  「扩 `nrec`（改 `fld[4]`/`fld[5]`）⇒ ❌ 渲染错乱（`top` 变垃圾值）」。
  **本次解释了这个失败的原因**：只改计数、不补记录 ⇒ L246-262 会多读 `nrec` 条 10 字节，
  **把后面的字节流整体错位**（`top` 就是被错位读出来的垃圾），并不是"引擎不支持大 nrec"。
* ⇒ **结论：记录路线要先解决"`FONT.RES` 扩容"，而这撞上 `MENU.IMG` 布局冻结问题。
  本轮判定为"可用但被 MENU.IMG 堵住"，不作为推荐路线。**

> ⚠ **新证据（与本项目既有结论冲突，请注意）**：我用 `r73_hardcoded_offsets.py` 在现役 ELF
> 主段（5,046,944 B）里搜 `0xB9120`（FONT.RES 在 MENU.IMG 内的偏移）、`0x58431`、`0x61D0F`、
> `0x61D13`、`0x4044C` —— **全部 0 命中**。即"ELF 里有硬编码 MENU.IMG 内部偏移"这句话
> **在 ELF 镜像里找不到任何对应常量**。所以"COMMON.PAK 不能长大"这条约束**证据不足**，
> 应当重测（§8 R1 正是要长大 COMMON.PAK）。

---

## 5. D —— 12px 带能不能当第二套字库？

**结论：不能。12px 带与 16px 是【同一张贴图】的两块区域，而且它只能靠记录表寻址。**

| 问题 | 实测答案 | 依据 |
|---|---|---|
| 同一张还是两张？ | **同一张 1024×512 PSMT4 图集** | `patch_zh12px.py` L90-91 `BAND_V = 480`；`patch_font_huge.py` `BAND_V, STEP = 480, 14` |
| 它在网格上吗？ | **不在**。`yrow(r)=2+16(r+3·[r≥12])`，r=30 ⇒ y=530 > 511 ⇒ **网格永远采不到 y480..495** | `r73_band_census.py`：`is a grid row? False` |
| 现役盘这块有没有被占？ | **有墨**：`row30 y=480..495 : 1722 texel`（`r73_band_census.py`） | 说明 12px 带**已在使用**，不是空白 |
| 怎么寻址的？ | 只能走 **FT 记录矩形**（任意 u/v）。`patch_zh12px.py` L1 记「引擎采样 `u = 记录 u0 − 288`」 | ⇒ 必须靠记录 |
| 能不能当第二套容量？ | ❌ **不能**：记录条数 `nrec` 固定 224（§4.2），而 12px 字形必须有记录才能被采样；加记录要扩 `FONT.RES`（§4.3 被堵） | — |
| 历史上成功过吗？ | ❌ `REPORT_names_and_12px.md` §二·发现 3 记录：只改 UV 宽 8→12 / `f1=12` / 6 种变体 **全部渲染错乱**；把字形放进"已验证可寻址的 ASCII 带"仍渲染出**别的**字形 ⇒ 当时结论是"引擎对 ASCII 码位的字形源坐标有未查明的解析规则" | — |

> ★ **本轮为上面那个"未查明"提供了一条强候选解释**：`ComputeCharTextureCoords` 的
> 记录分支（原版 `0x21AE20` 起，反汇编见 §3.2 尾）返回值做过 **`add.s f0,f0,f0`（×2）**，
> 而网格分支（cave，`0x417100..0x417130`）**没有 ×2**。两个分支的 UV 标度不同 ⇒
> 用记录路径改 `u0` 时，实际采样位置 = `2·u0` 而不是 `u0`。这与
> `docs/FONT_CURRENT_STATE.md` §7.2「单字节记录口径 `(u0+576) mod 1024`」的混乱是同一件事。
> **这条只是推测（未实机验证），但它给出一个可判定实验**：把某条 ASCII 记录的 `u0`
> 改 ±8，看实机字形横移 16 还是 8 texel。

---

## 6. E —— 还有没有别的字形来源？

| 候选 | 结论 | 证据 |
|---|---|---|
| **ELF 内嵌字体** | ❌ **没有**。ELF 里唯一"中文"数据是**字符串表**，不是字形 | `r73_elf_diff.py`：`0x577FA0..0x578074` 从英文改成中文，每槽 16 B（`A7A1A9A2 2E2E2ED6 00000000 00000000` = 中文 + "..." 填充） |
| **第二张贴图** | ✅ **已经绑好了！** `pda_counterparts.rsb` | 反编译 `RSFontMgr::ReadResourceFile` L276-280：<br>`GetTexture(ui_text_mgr, mgr+0x1c /* new_font_revised.rsb */)` → `SetTexture(mgr+0x28)`<br>`RSFilename("pda_counterparts.rsb" @0x578650)` → `GetTexture` → `SetTexture(mgr+0x4c)` |
| 能当第二套**字形图集**用吗？ | ⚠ **未证**。字形绘制走的是 `UIModel1 = mgr+0x28`；`mgr+0x4C` 是**第二个 UIModel**。要用它必须先找到"谁用 `mgr+0x4C` 画字"（现役代码里只看到 `SetTexture`，没看到绘制调用） | 需要下一轮专门逆向 |
| **RES 里的其它字体** | ❌ 未见。`RSFontMgr` 只读一个 `font.res`（`kFontResourceFilename @0x57ABE0`，`IkeUIMgr::Create` 有单例短路 ⇒ 只读一次，见 `FONT_CURRENT_STATE` §4补） | — |
| **GR.IMG 侧的字库** | ❌ **死拷贝**（`FONT_CURRENT_STATE` §4补 硬约束 2：MENU 侧读 3/3 扇区、GR 侧 0/3） | — |
| **巨大的 `huge` face（96 条记录）** | ❌ 不增容量，只是另一套尺寸参数 | `r73_capacity.py`：`huge nrec=96 fld=[10,16,52,42,16,6,...]` |

---

## 7. F —— 杠杆汇总表

> 单位：**能多放多少个汉字（码位）**。基准 = `GR_ZH113b`（对偶 1504/1504 用满，缺字 **364**）。

| # | 杠杆 | 增量 | 要改什么 | 动 ELF？ | 动数据？ | 风险 | 需实机验证？ |
|---|---|---|---|---|---|---|---|
| **L0** | 用满现役图集里剩余的格（行 24 col16..61 = 46 + 行 27 = 62） | **+108 格**；扣掉 0xB2/0xB3 两个单字节字 ⇒ 净 ≈ **+106** | gate `0xB1→0xB3`（4 处 `sltiu`） | ✅ 4 字 | ✅ 重排 + 新字形 | 低 | 是（已有先例） |
| **L1** | **贴图加高 512 → 1024**（PSMT4，TW/TH 幂等） | **+2046 格**（网格行 27..59 × 62） | 重建 `new_font_revised` PAK 记录：`h=1024`、`px_size=0x80310`、16 段 GIF 容器；下半张填空 `0x11` | ❌ **纯数据** | ✅ | **中**：COMMON.PAK 长大 ~0x40300；+256 KB 显存；加载器 `+0x30` 记账公式（见 §9-2）需复核 | **必须** |
| **L1'** | 贴图加高 512 → **768**（折中） | **+1054 格** | 同上，`h=768`、`px_size=0x60310` | ❌ | ✅ | 中（显存只要 +128 KB） | 必须 |
| **L2** | **抬 gate**（每个 lead 字节 +94 槽） | 每字节 **+94**（净 +93，因为要让出 1 个单字节码） | 4 处 `sltiu …,0xB1` → `sltiu …,0xNN`（`0x416EE8` / `0x417160` / `0x41751C` / `0x5656A4`） | ✅ 4 字 | ✅ | 低（但 gate > 0xB1 就会吃掉 `0xB1`△ / `0xB5`✕ 图标码，需把图标码迁到 gate 之外的字节） | 是 |
| **L3** | 图标带跳行 **3 行 → 2 行** | **+62 格** | `0x4170E8` 的 `+3`→`+2`；同时把 △/✕ 的硬编码 UV（原版 `0x219C4C`/`0x219C70`）上移 16 px，并把网格行 12..24 的 **806 个字**整体上移 1 行 | ✅ 2~4 字 | ✅ 806 格像素搬运 | **中高**（大面积像素搬运，虽**不需要重编文本**：slot 不变） | 是 |
| **L4** | **trail 下界 `0xA1` → `0x40`**：stride `94` → `191` | 现役 16 leads：**1504 → 3056**（**+1552**）；无需动 lead 区间，**不吃图标码** | stride 立即数 2 处（`0x417088` 网格 / `0x416F9C` 宽度）+ trail 下界 4 处（`0x416F0C`/`0x417180`/`0x5656C4`/`0x417538`）+ 工具链 `tcslib.PAIR_TRAIL_LO` | ✅ 6 字 | ✅ 全部对偶码格位重排 + 重渲 + 重编文本 | **高**：ASCII/单字节码的字节值（0x40..0xA0）会大量出现在 trail 位置；解码语义安全（trail 被无条件吃掉），但**所有**做字节扫描的既有代码/工具都要复核 | 必须 |
| **L5** | 对偶码改走记录表（`nrec` → 1728+） | 0（只换寻址方式，可解锁 y480..511 等自由区） | 扩 `FONT.RES` 记录数组 | ❌ | ✅ | **高**：`FONT.RES` 属于 MENU.IMG 第 4 槽，扩容会平移其后数据（历史实测卡死） | — |
| **L6** | 12px 带当第二套 | **0** | — | — | — | 只能靠记录表 ⇒ 被 L5 堵死 | — |
| **L7** | 第二张贴图 `pda_counterparts.rsb` | 未知（≥ +1504 量级） | 逆向"谁用 `mgr+0x4C` 画字" | ✅ 多处 | ✅ | **高**，工作量以轮计 | — |

### 7.1 推荐路线（★）

**R1 = L1 + L2 + 一行跳空补丁 ⇒ 净 ≈ +372 对偶码（1504 → 1876），一次覆盖全部 364 个缺字。**

具体：

1. **数据**：把 `COMMON.PAK` 的 `new_font_revised` 重建为 **1024×1024 PSMT4**
   （`w=1024 h=1024 psm=0x14`；`clut_size=0x410` 不变；`px_size` 由 `0x40010` → `0x80310`；
   像素容器换成 **16 段 × 64 行** GIF 封包；**已有 512 行内容逐字节不动**，
   新行 512..1023 全部填 `0x11`（透明））。这一步 **不动 ELF**。
2. **ELF（6 个字）**：
   * `0x416EE8`、`0x417160`、`0x41751C`、`0x5656A4`：`sltiu …,0xB1` → `sltiu …,0xB5`
     ⇒ lead 区间 `0xA1..0xB4`，**20 leads × 94 = 1880 槽（+376）**；
   * cave `0x4170A8` 之后插入（或改写）"网格行 ≥ 25 再跳 2 行"的判定，
     让 lead 0xB1..0xB4 的新槽落到 **y ≥ 482**（避开 ASCII 带 y450..481）。
     现成的空位：`0x4170A4` / `0x4170E4` 是两个 `nop`，`0x41713C..0x417140` 也空着。
3. **图标码**：`0xB1`（△）会落进新 lead 区间 ⇒ 把 △ 的码字节迁到 `0xB5` 之外的单字节码
   （`0xB5`✕ **天然存活**，因为 gate=0xB5 时 `0xB5` 不是 lead）；代价 = 再让出 **1 个**低频单字节汉字。
4. **代价**：`0xB2` / `0xB3` / `0xB4` 三个单字节汉字改成对偶码（占 3 个新槽）。
   ⇒ **净增 = 376 − 3 − 1 = +372** ⇒ 总容量 **1876**，缺字 **364** 全部覆盖，**还剩 8 槽**。
5. **衔接"已占满的 1504"**：现有 1504 个码位的 **slot 不变、格位不变、FT 记录不变**，
   所以**不需要重排、不需要重编现有文本**；只新增 372 条的码位/字形/文本编码。

**R2（若后续还要余量）**：h=1024 下网格行 33..59（27 行 = 1674 格）是**纯余量**。
继续抬 gate（每个 lead +94）即可吃到；或上 L4（trail 扩容）把每 lead 从 94 提到 191。

### 7.2 与"364 个缺字"的对账

`REPORT_expand_font_329.md` §3.3：候选 693 种，入选 329 种，**落选 364 种 / 386 次**。
R1 的 **+372** > 364 ⇒ **一次性补齐**（且 R1 之后仍有 8 槽 + 1024 高贴图里 1674 格余量）。

---

## 8. 实机证据

**本轮未做探针盘。** 原因（如实）：

1. R1 的"数据侧"要重建 `COMMON.PAK` 的像素容器（1024×1024、16 段 GIF、`px_size` 变化），
   这不是现成补丁脚本能覆盖的动作；现有 `patch_zh113_expand_font.py` 的 `Atlas` 类**假定**
   `px_size = 0x40010`、8 段、每段 64 行 —— 直接复用会写出无效容器。
2. 我发现的**加载器记账公式**（§9-2）意味着 `px_size` 变化**可能有**未预期的行为，
   需要先做一次"只加高贴图、不动任何字形/文本"的**单变量**探针才能干净归因。
3. 授权路径只允许写 `work/builds/GR_TEST_FONTCAP_*/`，而重建容器需要一个尚不存在的
   构建脚本；我判断在剩余预算内**做不出一道判据干净的探针**，宁可不做也不做"多变量混合"的
   假阳性实验。

**下一轮可直接执行的最干净探针（单变量：只验证"引擎接不接受 1024 高的贴图"）**：

```powershell
# 1) 写 tools/iso_build/probe_tall_atlas.py  (<src.iso> <dst.iso> 协议, 只改 COMMON.PAK 的
#    new_font_revised 记录: h 512->1024, px_size 0x40010->0x80310, 容器重切成 16 段;
#    已有 512 行像素逐字节复制, 新增行填 0x11; 字形/文本/FONT.RES 一律不动)
# 2) 出盘 (必须 --no-font-compact, 否则字库紧凑重排会抹掉对照)
python tools/iso_build/make_build.py GR_TEST_FONTCAP_TALL --from work/builds/GR_ZH113b `
       --patch tools/iso_build/probe_tall_atlas.py --no-font-compact --no-textdump `
       --no-text-snapshot --no-font-dump
# 3) 实机 (≈6 分钟; nav_hook 默认不抢杀别人的实例, 被占用请排队重试)
python tools/capture/nav_hook.py GR_TEST_FONTCAP_TALL --tag tallatlas
```
**判据**：截图里**任意界面文字与原盘逐像素一致** ⇒ 1024 高贴图被接受
（加载器/显存/GS 都没炸）⇒ L1 成立；若出现花纹/错位/黑块 ⇒ 贴图高被硬约束（回到 §9-2）。

---

## 9. 已知限制 / 我没能确认的部分

1. **没做探针盘**（§8）。所有容量数字都是**盘上数据 + ELF 字节 + 反编译**三路推出来的，
   **没有实机闭环**。
2. ⚠ **加载器里有一段我读不懂语义的记账，是 L1 的主要未知**：
   反编译 `LoadingTexturePak` L113-114：
   ```c
   iVar4 = (uint)*(ushort *)(iVar5 + 0x10) * (0x10000 / *(ushort *)(iVar5 + 0x10)) * 4 + 0x10;
   *(int *)(iVar5 + 0x30) = iStack_82c4 + ((iStack_82c4 + iVar4 + -1) / iVar4) * -0x10;
   ```
   对现役 `w=1024, px_size=0x40010` 恰好给出 `iVar4 = 0x40010`、`+0x30 = 0x40000`
   （= 真像素字节数，完全正确）。但 `h=1024`、`px_size=0x80310` 时
   `+0x30 = 0x802E0 = 525024`，而真实像素字节是 `0x80000 = 524288` ⇒ **差 736 B**。
   `+0x30` 到底被谁用、差 736 B 会不会越界读，**我没查到**（需再逆一层）。
   **这是 L1 唯一可能致命的点，必须在实机前解决或直接探针验证。**
3. **显存预算未核**：`UITextureMgr` 的 VRAM 分配器没逆到。1024×512 PSMT4 = 256 KB，
   1024×1024 = 512 KB（GS 总 4 MB）。若分配器把别的纹理紧贴在字体纹理之后，加大高度会**覆盖**它。
   未证实/未证伪。
4. **"`MENU.IMG` 内部偏移冻结"这条既有结论，我在 ELF 里找不到支持**（§4.3 的 0 命中搜索）。
   但历史确实观察到"平移尾部数据 ⇒ 卡死在记忆卡界面"。**两条证据冲突，本轮判定为未解决**。
   如果它其实成立，L1（COMMON.PAK 长大 ~256 KB）和 L5 都会被堵死，只剩 L0/L3（+108/+62）。
5. **`pda_counterparts.rsb` 第二张贴图**只证明"被 `SetTexture` 绑到 `mgr+0x4C`"，
   **没有**找到任何用 `mgr+0x4C` 画字的代码 ⇒ 不能承诺它能当第二套字形图集。
6. **12px 带的"引擎对记录 UV 有未查明规则"我没能定论**；§5 的 ×2 标度只是**推测**，
   给出了一个可判定实验（改 `u0` ±8 看位移 16 还是 8），本轮未做。
7. **Ghidra 项目的字节不是现役 ELF**（§1 注）。所有**代码级**结论我都用
   `r73_probe_bytes.py` + 自写解码器在**磁盘字节**上复核过；但**反编译 C**（`deep_part.txt`）
   来自新建的 `GRLocEE` 项目，未逐字节复核该项目与磁盘 ELF 的一致性
   （只抽验了字库 cave 区；C 里引用的**加载器**函数在 50 处差分里**不在**改动列表内，故可信度高）。
8. **反编译器超时**：`FontDeep` 用 900 s 才拿到 C；`FontDecomp` 的 120 s 会**静默返回空 C**
   （我在第一版里就被这个坑了一次）。其它大函数（`DrawString`）因为被 `j` 补丁打断，
   函数体只有 2~3 条指令，**反编译无意义** —— 那些地方只能看汇编。
9. **副作用发现（与本任务无关，但建议 Lead 处理）**：`work/builds/` 里 **`GR_ZH117.iso`
   的字库是坏的** —— `dump_font.py` 报「对偶字字形覆盖不全: 有字形 **1175** / 已用 **1504**」，
   317 个对偶码在盘上**一个墨点都没有**（329 个 round67 新字没写进去或错位 -3 行）。
   **最新的完整盘是 `GR_ZH113b.iso`**（`dump_font.py` 报 1504/1504 有字形、自查 OK）。
   若构建/发布流程按"最大版本号"取盘，会取到坏盘。

---

## 10. 附：本轮脚本与中间产物

| 文件 | 说明 |
|---|---|
| `work/tools/ghidra_scripts/FontSites.java` | 符号 + 立即数 + 字面量 xref 全扫 |
| `work/tools/ghidra_scripts/FontRaw.java` | 裸字节模式扫描 + 自带 MIPS 解码器 |
| `work/tools/ghidra_scripts/FontDecomp.java` | 批量反编译（默认 120 s 超时） |
| `work/tools/ghidra_scripts/FontDeep.java` | 单函数深挖（900 s 超时，打印 C 长度） |
| `…/r73/r73_elf_diff.py` → `elf_diff.txt` / `elf_diff_summary.txt` | ★ 原版↔现役全文件差分（50 处 / 567 字） |
| `…/r73/r73_probe_bytes.py` → `probe_bytes.txt` | 关键 VA 字节三方差分（原版 / r72 / Ghidra 项目） |
| `…/r73/r73_capacity.py` → `capacity.json` | PAK/FT 字段 + 各 h 的容量表 |
| `…/r73/r73_band_census.py` → `band_census.txt` | 图集逐 16px 行墨量（12px 带判定） |
| `…/r73/r73_slot_ink.py` → `slot_ink.txt` | 逐 slot 引擎格/legacy 格墨量 |
| `…/r73/r73_hardcoded_offsets.py` → `hardcoded.txt` | ELF 里有没有硬编码 MENU.IMG 偏移（**0 命中**） |
| `…/r73/run2.utf8.log` / `fontraw_part.txt` | FontRaw+FontDecomp 原始输出（默认 MIPS 语言） |
| `…/r73/deep_part.txt` / `ee_decomp_part.txt` | ★ EE 语言（`r5900:LE:32:default`）的反编译 C |
| `…/r73/dump117.log` / `dump113b.log` | 两张盘的 `dump_font.py` 自查输出 |
