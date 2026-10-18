# REPORT_cave_count_vs_bytes.md — round79：「汉化 cave 代码的计数/字节不匹配」静态审计

> 执行者 = 静态审计子代理 · 分支 `round73/font-decompile`（**未切分支、未 commit、未 merge**）
> 输入（直接采用，不重新论证）= `docs/REPORT_zh_heap_corruption.md` 的零成本判据
> （`TLB Miss` 行数：汉化 50/13，英文原盘 0；异常最早出现在**开机 7.68 s**）
> 与"`$a0 = 0x14` = 汉化 cave 自己的字宽常量"这条现场坐标。
> 产物 = 本报告 + `work/tools/cave_*.py` + `work/builds/GR_ZH98/temp/r79/**` + `work/builds/GR_ZH119/`
> **只读**：所有 ISO（含 `GR_ZH111` / `GR_ZH113b` / `GR_EN_ORIG`）、`%LOCALAPPDATA%\PCSX2\**`、
> `work/temp/NEW_Mem/**`、`tools/text_csv/*`、`font_compact.py`、`make_build.py`、`tools/font_pipeline/data/*`。

---

## 0. 一句话结论

1. **H1 的字面形式（cave 里"按字符数申请缓冲、按字节数写"）在本轮被穷举检查后【不成立】。**
   四个被整体替换的函数（`0x416ED0` 解码器 / `0x416F40` CharWidth / `0x565670` StringWidth 尾 /
   `0x417050` ComputeCharTextureCoords）**没有任何一处分配缓冲**，唯一的写目标是调用方**栈帧内**的
   3 个字节（`sp+221..223`，帧长 224），且只有一个调用点。逐条取证见 §2、§3。
2. **但审计在"计数 vs 字节"的同一个家族里抓到一个具体的字节级缺陷（F1，头号嫌疑）**：
   `0x5657E0  lhu $a1, 2($t0)` 把 `RSUIString::mImpl` 的 **u8 模式字节（+2）** 当成 **u16 长度**读，
   而这个值被当作**长度**交给辅助函数 `0x565760`，其返回值又当作**字符数**交给
   `RSString::Left(count)`。`mImpl+3` 是构造函数**从不写入**的堆残留字节 ⇒ 一旦非 0，
   长度最大到 **65535**，辅助函数会沿字符串指针**向下越界扫描最多 64 KB**，
   并把越界算出来的数当 `Left()` 的拷贝长度。
   ⇒ **它的后果是数据/会话相关的（堆残留决定），不是每次开机必然发生** ——
   与用户现场"两次会话 7.68 s / 434.15 s 起始不同、本机 0 缺页"的特征同型。
   最小修法 = **改 1 条指令**：`0x5657E0: 0x95050002 → 0x95050000`（`lhu a1,0(t0)`）。见 §4、§6。
3. **H2（返回值语义被改）【成立】，共 3 处**，其中 2 处会实际改变布局，1 处（StringWidth 尾部）
   是有意为之（ZH63 的 kern 修复）。最值得注意的是 **F3**：cave 版 CharWidth **删掉了**
   原版 `if (*(u8*)(this+0x24)) return *(int*)(this+0xC);` 这条"等宽模式"短路，
   而**同一个标志仍被未被替换的 `CharHeight`（0x21ACD0）遵守** ⇒ 两个度量函数对同一对象
   的"模式"判断不一致。见 §3.3 F3。
4. ★ **方法学更正（很重要，直接影响后续所有轮次）**：EE（R5900）的 **`MULT` 是三操作数
   `MULT rd, rs, rt`（`rd = rs×rt`）**，PCSX2 的 EE 重编译器就是这么实现的
   （`REC_FUNC_DEL(MULT, _Rd_)`、`iR5900MultDiv.cpp:244`）。因此
   `0x41708C mult $t4,$t6` 写的是 **$t4**、`0x416FA0 mult $t1,$t6` 写的是 **$t0**，
   两条格位公式 `slot=(lead−0xA1)×94+(trail−0xA1)` **都是对的**。
   按普通 MIPS 读成"`mult` 结果没人用 ⇒ 少了 ×94"会得出**错误结论**（`docs/REPORT_font_capacity_decompile.md`
   §3.2 的注释正是照普通 MIPS 写的，结论对、注释错）。本报告 §3.2 给出逐字段证据。
5. ★ **否证一类假说**：cave 落点 `0x416ED0..0x4176E8` 并不是"空白填充"，而是**静态链进来的
   PS2 iomanX 文件系统驱动函数**（符号表：`sceRemove` / `sceMkdir` / `sceRmdir` / `sceFormat` /
   `sceAddDrv` / `sceDelDrv` / `sceDopen` / `sceDclose` / `sceDread` / `sceGetstat`）。
   但**全 .text 扫描证明没有任何 `jal`/`j`/分支/地址合成指向它们**（63 个命中的控制转移**全部**
   来自这些函数自己的内部）⇒ **它们是不可达死代码，覆盖它们不会破坏任何活代码**。
   见 §4 F5。

---

## 1. 基座：两套指令流是怎么钉住的

### 1.1 汉化盘与现役基底共用同一个可执行文件（★ 新事实）

```
work/builds/GR_ZH111/GR_ZH111.iso     → SLUS_206.13  sha256 = 3465580f4ec39098423e2053…
work/builds/GR_ZH113b/GR_ZH113b.iso   → SLUS_206.13  sha256 = 3465580f4ec39098423e2053…
work/builds/GR_ZH98/temp/r72/SLUS_206.13.elf  sha256 = 3465580f4ec39098423e2053…
third_party/orig/ps2/slus_out/SLUS_206.13     sha256 = 5fec662f2a138f9f62f6bc07…   (英文原版)
```

⇒ **用户报障的那张盘（`GR_ZH111`，CRC `7A361FB5`）与现役基底 `GR_ZH113b` 的 ELF 逐字节相同**，
所以本报告对 cave 的每一条结论**同时适用于**用户崩过的盘和将要做的对照盘。

| 角色 | 文件 | 取法 |
|---|---|---|
| 原版 | `third_party/orig/ps2/slus_out/SLUS_206.13`（37,453,732 B） | 已在仓 |
| 汉化 | `work/builds/GR_ZH98/temp/r79/dump/elf_zh113b.bin`（sha256 同上） | `work/tools/cave_extract_elf.py <iso> <out>`（LBA 295，只读） |

ELF 布局（两版完全一致）：**只有 1 个非空 `PT_LOAD`**：`off=0x80 va=0x00100000 filesz=0x4DED00`
（`memsz=0x54BE80`，即 BSS 比文件多 0x6D180）。文件另外 32 MB 是**不加载**的
`.strtab`(0x4DEDE0) / **`.symtab`(0x61CF80，38,722 条符号)** / `.rel`(0x2230480) / MIPS debug 段。
VA→文件偏移 = `0x80 + (VA − 0x100000)`。

### 1.2 ★ 符号表是可用的（本轮新工具 `work/tools/cave_syms.py`）

零售 ELF 里保留了完整 `.symtab`，于是四个函数与所有 cave 落点都有**权威名字**：

| VA | 原版符号 | 大小 | 被汉化怎么用 |
|---|---|---|---|
| `0x21AC00` | `StringWidth__6RSFontCFPCc` | 196 | 内环被 `j 0x417150` 换掉、尾部被 `j 0x565670` 换掉 |
| `0x21ACD0` | `CharHeight__6RSFontCFv` | 64 | **未改** |
| `0x21AD10` | `CharWidth__6RSFontCFc` | 204 | 第 3 条起 `j 0x416F40` |
| `0x21ADE0` | `ComputeCharTextureCoords__6RSFontCFcRfRfRfRf` | 328 | 入口 `j 0x417050` |
| `0x219A70` | `DrawString__9RSFontMgrFPCcffRC7RSColorP6RSFontPCiPCii` | 912 | 入口 +8 处 `j 0x565930` |
| `0x219EB0` | `DrawString__9RSFontMgrFPCciiRC7RSColorP6RSFontPCiPCii` | 72 | 调用点改 `j 0x565900` |
| `0x21CA20` | `ComputeDrawXY__15RSTextComponentFRC10RSUIString` | 488 | 5 处挂点（含尾部填充 `0x21CC08`） |
| `0x21CC10` | `DoWordWrap__15RSTextComponentFRC10RSUIString` | 936 | 入口后 0x160 处 `j 0x417500` |
| `0x53FD50` | `Length__10RSUIStringCFv` | 44 | **未改**（本报告用它定 `mImpl` 布局） |
| `0x5414B0` | `__vc__10RSUIStringFi`（`operator[]`） | 216 | **未改**（定 `mImpl` 布局的关键） |
| `0x53E2B0` | `Left__8RSStringCFUi` | 48 | **未改**（F1 的下游） |
| `0x53EBE0` | `__ct__8RSStringFPCc` | 104 | **未改** |
| `0x118EE0` | `fptosi` | 16 | cave CharWidth 调用它做 float→int |
| `0x519AC0` | `SetLinearSampling__8UIPacketFb` | 356 | 4 个调用点把 `a1` 由 1 改 0 |

cave 落点的**原住户**（这条决定了"覆盖是否安全"，见 §4 F5）：

| cave 落点 | 原版符号 | 原版大小 |
|---|---|---|
| `0x416ED0` | `sceRemove` | 28 |
| `0x416EF0`（含 `0x416F40`/`0x417050`/`0x417150`/`0x417200` 落点） | `sceMkdir` | 428 |
| `0x4170A0` | `sceRmdir` | 28 |
| `0x4170C0`（含 `0x417150` 落点） | `sceFormat` | 620 |
| `0x417330` | `sceAddDrv` | 288 |
| `0x417450` | `sceDelDrv` | 28 |
| `0x417470`（含 `0x417500..0x41752C`） | `sceDopen` | 200 |
| `0x417538`（含 `0x417538..0x4175C0`） | `sceDclose` | 360 |
| `0x4176A0`（含 `0x417650/0x417680/0x4176A0/0x4176B0` 落点） | `sceDread` | 344 |
| `0x4177F8` | `sceGetstat` | 416 |
| `0x565600..0x565B00` | **无任何符号**（真正的无名填充区） | — |
| `0x411690`/`0x21CC08`/`0x407078`/`0x408928` | 位于函数**尾部 nop 填充** | — |

### 1.3 挂点全表（`j`/`jal` 改写，共 43 处）

`work/builds/GR_ZH98/temp/r79/dump/jmap.txt` 给出**每一处**挂点的 ±16 B 上下文 +
cave 体。汇总：

| 挂点 VA | 原指令 | 现指令 | cave | 宿主函数 |
|---|---|---|---|---|
| `0x219A74` | `sd ra,160(sp)` | `j 0x565930` | 0x565930 | `RSFontMgr::DrawString` |
| `0x219ADC` | `mtc1 v0,f0` | `j 0x417200` | 0x417200 | 同上 |
| `0x219BCC` | `jal 0x40BFC8` | `jal 0x416ED0` | 0x416ED0 | 同上（**字符解码器**） |
| `0x219BD0/BD4/E4` | `sp+223` / `lb` | `sp+222` / `lhu` | — | 同上（配合 -1 偏移） |
| `0x21AC74` | `jal 0x21AD10` | `j 0x417150` | 0x417150 | `RSFont::StringWidth` 内环 |
| `0x21AC90` | `lw v0,24(s3)` | `j 0x565670` | 0x565670 | `RSFont::StringWidth` 尾 |
| `0x21AD18` | `lbu v0,36(a0)` | `j 0x416F40` | 0x416F40 | `RSFont::CharWidth` |
| `0x21ADE0` | `lw t2,40(a0)` | `j 0x417050` | 0x417050 | `RSFont::ComputeCharTextureCoords` |
| `0x21BD68` | `addiu v0,zero,18` | `j 0x417680` | 0x417680 | `RSHTML::DrawHTML` 内 |
| `0x21C048` | `lw a2,168(s1)` | `j 0x417650` | 0x417650 | `RSTextComponent::DrawTheString` |
| `0x21C624` | `jal 0x219EB0` | `j 0x565900` | 0x565900 | 同上 |
| `0x21CA50` | `sw v1,236(a0)` | `j 0x565730` | 0x565730 | `RSTextComponent::ComputeDrawXY` |
| `0x21CB28/CB30` | `bnel→0x21CB3C` / `jal 0x21ACD0` | `bnel→0x21CC08` / `jal 0x4176A0` | 0x21CC08/0x411690/0x4176A0 | 同上 |
| `0x21CD70/CD74` | `lw v0,152(s5)` / `addiu a0,sp,248` | `j 0x417500` / `lw a0,252(sp)` | 0x417500 | `RSTextComponent::DoWordWrap` |
| `0x21CFD8` | `lbu v1,264(s0)` | `j 0x4176B0` | 0x4176B0 | `RSTextComponent::SetText` |
| `0x21D940` | `subu v0,v1,v0` | `j 0x565A00` | 0x565A00 | `IkeDialog_List::InitText` |
| `0x2ECEC0` | `addiu a0,sp,136` | `j 0x56583C` | 0x56583C | 某 UI 文本设置 |
| `0x3070B4` | `addiu a0,sp,56` | `j 0x5657C8` | 0x5657C8 | 某 UI 文本设置（**F1 现场**） |
| `0x1FF8D0` | `subu v0,v1,v0` | `addiu v0,v1,-21` | — | 单字常量 |
| `0x2071B4` | `subu v0,v1,v0` | `addiu v0,v1,-16` | — | 单字常量 |
| `0x216578` | `addiu a3,s1,3` | `addiu a3,s1,5` | — | 单字常量 |
| `0x219FF4`/`0x21A0F8`/`0x21A1C4`/`0x21A2C4` | `addiu a1,zero,1` | `addiu a1,zero,0` | — | 4 个 `SetLinearSampling(false)` |
| `0x2DE5A4` | `jal 0x21ACD0`+`mtc1` | `lui v0,0x41A8`(=21.0f)+`mtc1` | — | 单字常量 |
| `0x2BEE5C..`/`0x22E218` | 浮点常量 | 微调 | — | 与文本无关 |

---

## 2. 四个函数：原版 vs 汉化，逐条对照

> 反汇编全部来自**盘上字节**（`work/tools/cave_dis.py`，自带 R5900+MMI 解码器）。
> 下文 `→` 左=原版、右=汉化。**`mult` 一律按 EE 三操作数读**（§3.2）。

### 2.1 字符解码器：`jal 0x40BFC8` → `jal 0x416ED0`（`RSFontMgr::DrawString` 内）

**原版 `0x40BFC8`（6 条，叶子，无栈帧）**

```
0040BFC8  54800003  bnel $a0,$zero,0x40BFD8
0040BFCC  A0850000  sb   $a1,0($a0)          ; ← 延时槽：分支成立时才执行
0040BFD0  03E00008  jr   $ra
0040BFD4  0000102D  daddu $v0,$zero,$zero    ; a0==0 → 返回 0
0040BFD8  03E00008  jr   $ra
0040BFDC  24020001  addiu $v0,$zero,1        ; a0!=0 → 返回 1
```
语义（把 BEQL/BNEL 的"延时槽仅在分支成立时执行"按 `iR5900Branch.cpp:299-314` 的
`recBNEL_process`（not-taken ⇒ `SetBranchImm(pc+4)` 跳过延时槽）核对过）：
`int DecodeChar(char *out, u8 c){ if(out){ *out=c; return 1; } return 0; }`
—— **写 1 字节，返回"消耗 1 字节"**。英文原版是纯单字节直通。

调用点（原版）：
```
00219BC4  02D01021  addu $v0,$s6,$s0     ; v0 = str + i
00219BC8  80450000  lb   $a1,0($v0)      ; a1 = (s8)str[i]
00219BCC  0C102FF2  jal  0x0040BFC8      ; DecodeChar(&sp[223], c)
00219BD0  27A400DF  addiu $a0,$sp,223
00219BD4  83A500DF  lb   $a1,223($sp)    ; 取回 1 字节
00219BD8  0C086B44  jal  0x0021AD10      ; CharWidth
```

**汉化 cave `0x416ED0..0x416F3C`（28 条）**

```
00416ED0  30A500FF  andi $a1,$a1,0x00FF  ; c &= 0xFF
00416ED4  A4850000  sh   $a1,0($a0)      ; ★ 先按单字节码写 **2 字节**
00416ED8  24020001  addiu $v0,$zero,1    ; len = 1
00416EDC  2CA900A1  sltiu $t1,$a1,0xA1
00416EE0  15200014  bne  $t1,$zero,0x416F34      ; c<0xA1 ⇒ 单字节
00416EE8  2CA900B1  sltiu $t1,$a1,0xB1
00416EEC  11200011  beq  $t1,$zero,0x416F34      ; c>=0xB1 ⇒ 单字节（★ GATE 之一）
00416EF4  26F8FFFF  addiu $t8,$s7,-1             ; t8 = strlen-1   ← 用调用方的 $s7
00416EF8  0218C02A  slt  $t8,$s0,$t8             ; ← 用调用方的 $s0 = 字节下标
00416EFC  1300000D  beq  $t8,$zero,0x416F34      ; 末尾 ⇒ 单字节
00416F04  02D07821  addu $t7,$s6,$s0             ; ← 用调用方的 $s6 = 串首
00416F08  91EB0001  lbu  $t3,1($t7)              ; trail
00416F0C  2D6900A1  sltiu $t1,$t3,0xA1
00416F10  15200008  bne  $t1,$zero,0x416F34
00416F18  2D6900FF  sltiu $t1,$t3,0xFF
00416F1C  11200005  beq  $t1,$zero,0x416F34      ; trail ∉ [0xA1,0xFE] ⇒ 单字节
00416F24  00056200  sll  $t4,$a1,8
00416F28  018B6025  or   $t4,$t4,$t3
00416F2C  A48C0000  sh   $t4,0($a0)              ; 结果 = u16 码 = lead<<8|trail
00416F30  24020002  addiu $v0,$zero,2            ; len = 2
00416F34  A082FFFF  sb   $v0,-1($a0)             ; ★★ (a0-1) = 该字符占几个输入字节
00416F38  03E00008  jr   $ra
```

**写目标只有三个字节：`a0[-1]`、`a0[0]`、`a0[1]`；且只被一个调用点调用**
（`cave_dis.py callers 0x416ED0` → `from 0x00219BCC`，仅此一处）。
调用点已把 `a0` 由 `sp+223` 改成 `sp+222`，于是命中 `sp+221 / sp+222..223`。
**宿主帧 = `0x219A70 addiu sp,sp,-224`** ⇒ **三字节全在帧内，不越界**。✔

**契约**：`a0` = 输出（**必须 ≥ 3 字节可用**）、`a1` = 当前字节、**`$s0`=字节下标、`$s6`=串首、
`$s7`=串长**（三个都是**调用方的**寄存器，不设不存）、返回 `v0` = 消耗字节数 ∈{1,2}。

### 2.2 `RSFont::CharWidth`：`0x21AD10` → `j 0x416F40`

**原版 `0x21AD10..0x21ADDC`（204 B，有 16 字节栈帧）**

```
0021AD10  27BDFFF0  addiu $sp,$sp,-16
0021AD14  FFBF0000  sd   $ra,0($sp)
0021AD18  90820024  lbu  $v0,36($a0)      ; ★★ v0 = *(u8*)(this+0x24)   「等宽模式」标志
0021AD1C  10400003  beq  $v0,$zero,0x21AD2C
0021AD20  00051E3C  dsll32 $v1,$a1,24      ; (延时) 符号扩展 c
0021AD24  1000002A  beq  $zero,$zero,0x21ADD0
0021AD28  8C82000C  lw   $v0,12($a0)       ; ★★ 模式≠0 ⇒ 直接返回 *(u32*)(this+0xC)
0021AD2C  00031E3F  dsra32 $v1,$v1,24
0021AD30  24020020  addiu $v0,$zero,32
0021AD34  14620003  bne  $v1,$v0,0x21AD44
0021AD38  2402FFB5  addiu $v0,$zero,-75     ; 0xB5(✕)
0021AD3C  10000024  beq  $zero,$zero,0x21ADD0
0021AD40  8C820014  lw   $v0,20($a0)        ; ' ' ⇒ return *(u32*)(this+0x14)
0021AD44  10620005  beq  $v1,$v0,0x21AD5C
0021AD48  24020014  addiu $v0,$zero,20      ; ✕ ⇒ 20
0021AD4C  2402FFB1  addiu $v0,$zero,-79     ; 0xB1(△)
0021AD50  14620004  bne  $v1,$v0,0x21AD64
0021AD58  24020014  addiu $v0,$zero,20      ; △ ⇒ 20
0021AD64  8C860028  lw   $a2,40($a0)        ; a2 = this->mFontDef (+0x28)
0021AD68  30A200FF  andi $v0,$a1,0x00FF
0021AD6C  0002163C  dsll32 $v0,$v0,24
0021AD70  0002163F  dsra32 $v0,$v0,24       ; (s8)c
0021AD74  80C30020  lb   $v1,32($a2)        ; v1 = def+0x20 (face 首字符)
0021AD78  00431023  subu $v0,$v0,$v1
0021AD7C  304300FF  andi $v1,$v0,0x00FF
0021AD80  04620006  bltzl $v1,0x21AD9C      ; idx<0 ⇒ 0
0021AD84  70001E28  pcpyld $v1,$zero,$zero
0021AD88  8CC20044  lw   $v0,68($a2)        ; nrec
0021AD8C  0062102A  slt  $v0,$v1,$v0
0021AD90  14400002  bne  $v0,$zero,0x21AD9C
0021AD98  70001E28  pcpyld $v1,$zero,$zero   ; idx>=nrec ⇒ 0
0021AD9C  8CC60038  lw   $a2,56($a2)        ; recs
0021ADA0  306300FF  andi $v1,$v1,0x00FF
0021ADA4  00031080  sll  $v0,$v1,2
0021ADA8  00431021  addu $v0,$v0,$v1
0021ADAC  00021040  sll  $v0,$v0,1          ; ×10 = 记录步长
0021ADB0  C481001C  lwc1 $f1,28($a0)        ; f1 = *(f32*)(this+0x1C) 缩放
0021ADB4  00461021  addu $v0,$v0,$a2
0021ADB8  90420001  lbu  $v0,1($v0)         ; rec[idx].f1
0021ADBC  44820000  mtc1 $v0,$f0
0021ADC4  46800020  cvt.s.w $f0,$f0
0021ADC8  0C0463B8  jal  0x00118EE0         ; fptosi
0021ADCC  46010302  mul.s $f0,$f0,$f1      ; (延时)
0021ADD0  DFBF0000  ld   $ra,0($sp)
0021ADD4  03E00008  jr   $ra
0021ADD8  27BD0010  addiu $sp,$sp,16
```

**汉化**：`0x21AD18` 与 `0x21AD1C` 变成 `j 0x416F40` + `nop`
（**注意：挂点在序言 `addiu sp,sp,-16 / sd ra,0(sp)` 之后**，所以 `ra`/`sp` 契约由原版序言维持），
`0x416F40..0x417038`（62 条）为 cave：

```
00416F40  00054202  srl  $t0,$a1,8          ; t0 = 高字节（=lead，0 表示单字节）
00416F44  15000011  bne  $t0,$zero,0x416F8C ; 走 DBCS
00416F4C  30AB00FF  andi $t3,$a1,0x00FF
00416F50  24090020  addiu $t1,$zero,32
00416F54  11690031  beq  $t3,$t1,0x41701C   ; ' '  ⇒ 0x41701C
00416F5C  240900B5  addiu $t1,$zero,0xB5
00416F60  11690031  beq  $t3,$t1,0x417028   ; ✕   ⇒ 0x417028
00416F68  240900B1  addiu $t1,$zero,0xB1
00416F6C  1169002E  beq  $t3,$t1,0x417028   ; △   ⇒ 0x417028
00416F74  8C860028  lw   $a2,40($a0)
00416F78  80C30020  lb   $v1,32($a2)
00416F7C  01634023  subu $t0,$t3,$v1
00416F80  310800FF  andi $t0,$t0,0x00FF     ; idx = (c-base)&0xFF   ← 与原版 andi 等价
00416F84  1000001E  beq  $zero,$zero,0x417000
00416F8C  310900FF  andi $t1,$t0,0x00FF     ; DBCS: lead
00416F90  2529FF5F  addiu $t1,$t1,-161
00416F94  30AA00FF  andi $t2,$a1,0x00FF     ; trail
00416F98  254AFF5F  addiu $t2,$t2,-161
00416F9C  240E005E  addiu $t6,$zero,94      ; stride
00416FA0  012E4018  mult $t1,$t6            ; ★ EE 三操作数: rd=t0 ⇒ **$t0 = (lead-0xA1)*94**
00416FA4  010A4021  addu $t0,$t0,$t2        ; t0 = slot
00416FA8  250800E0  addiu $t0,$t0,224       ; idx = slot + 0xE0
00416FAC  8C860028  lw   $a2,40($a0)
00416FB0  8CC30044  lw   $v1,68($a2)        ; nrec
00416FB4  0103102B  sltu $v0,$t0,$v1
00416FB8  14400003  bne  $v0,$zero,0x416FC8 ; idx<nrec ⇒ 记录表
00416FBC  24020010  addiu $v0,$zero,16      ; ★★ 否则 **直接返回 16**
00416FC0  1000001A  beq  $zero,$zero,0x41702C
00416FC8  8CC60038  lw   $a2,56($a2)        ; recs
00416FCC  00081080  sll  $v0,$t0,2
00416FD0  00481021  addu $v0,$v0,$t0
00416FD4  00021040  sll  $v0,$v0,1          ; ×10
00416FDC  90420001  lbu  $v0,1($v0)         ; rec[idx].f1
00416FE0  44820000  mtc1 $v0,$f0
00416FE8  C481001C  lwc1 $f1,28($a0)
00416FEC  46010302  mul.s $f0,$f0,$f1
00416FF0  0C0463B8  jal  0x00118EE0         ; fptosi
00416FF8  1000000C  beq  $zero,$zero,0x41702C
00417000  8CC30044  lw   $v1,68($a2)        ; 单字节越界 → idx=0 → 0x416FC8
00417010  24080000  addiu $t0,$zero,0
0041701C  8C820014  lw   $v0,20($a0)        ; ' ' ⇒ *(u32*)(this+0x14)
00417028  24020014  addiu $v0,$zero,20      ; △/✕ ⇒ **20**（= 现场坏值 0x14）
0041702C  DFBF0000  ld   $ra,0($sp)         ; ★ 与 0x21AD10 序言配对的尾声
00417030  03E00008  jr   $ra
00417034  27BD0010  addiu $sp,$sp,16
```

**契约核对**：cave 在 `0x21AD18` 进入 ⇒ 原版序言已执行（`sp-=16`、`ra` 存 `0(sp)`），
cave 的尾声 `ld ra,0(sp); addiu sp,sp,16` 与之一致 ✔。
`0x21AD10` 的 5 个调用者（`0x219BD8`/`0x21CD88`/`0x4171A0`/`0x4171B8`/`0x417570`）都从函数入口进 ⇒ 序言必然执行 ✔。

### 2.3 `RSFont::StringWidth`：内环 `0x21AC74 → j 0x417150`，尾部 `0x21AC90 → j 0x565670`

**原版（`0x21AC00..0x21ACC4`，196 B，帧 96 B）** 关键段：

```
0021AC70  80450000  lb   $a1,0($v0)       ; a1 = str[i]        ($v0 = $s2+$s4)
0021AC74  0C086B44  jal  0x0021AD10       ; CharWidth
0021AC78  72602628  pcpyld $a0,$s3,$zero  ; (延时)
0021AC7C  02228821  addu $s1,$s1,$v0      ; 累计宽度
0021AC80  26940001  addiu $s4,$s4,1       ; ★ i += 1（字节）
0021AC84  0290102A  slt  $v0,$s4,$s0
0021AC88  1440FFF9  bne  $v0,$zero,0x21AC70
0021AC8C  02541021  addu $v0,$s2,$s4
0021AC90  8E620018  lw   $v0,24($s3)       ; ★ 尾部：v0 = *(u32*)(s3+0x18) = 每字符步进「kern」
0021AC94  2603FFFF  addiu $v1,$s0,-1
0021AC98  00621018  mult $v1,$v0          ; rd=0 ⇒ 结果丢弃（原版这里是**死乘法**）
0021AC9C  02228821  addu $s1,$s1,$v0      ; ★ 只加 **1 次** kern
0021ACA0  72201628  pcpyld $v0,$s1,$zero
0021ACA4  DFBF0050  ld   $ra,80($sp)
0021ACBC  03E00008  jr   $ra
0021ACC0  27BD0060  addiu $sp,$sp,96
```

**汉化**：
* `0x21AC74 → j 0x417150`（**进入时 `a1` = 当前字节，`s4` = 字节下标，`s0` = 串长，
  `s1` = 累计宽度，`s3` = 字体对象**；`0x21AC78` 的 `pcpyld a0,s3,zero` 作为 `j` 的延时槽照常执行）：

```
00417150  30A800FF  andi $t0,$a1,0x00FF
00417154  2D0900A1  sltiu $t1,$t0,0xA1
00417158  15200017  bne  $t1,$zero,0x4171B8   ; 单字节
00417160  2D0900B1  sltiu $t1,$t0,0xB1
00417164  11200014  beq  $t1,$zero,0x4171B8   ; ≥0xB1 单字节（GATE）
0041716C  2618FFFF  addiu $t8,$s0,-1
00417170  0298C02A  slt  $t8,$s4,$t8          ; s4 < len-1
00417174  13000010  beq  $t8,$zero,0x4171B8
0041717C  904B0001  lbu  $t3,1($v0)           ; trail（$v0 = $s2+$s4，由内环维持）
00417180  2D6900A1  sltiu $t1,$t3,0xA1
00417184  1520000C  bne  $t1,$zero,0x4171B8
0041718C  2D6900FF  sltiu $t1,$t3,0xFF
00417190  11200009  beq  $t1,$zero,0x4171B8
00417198  00082A00  sll  $a1,$t0,8
0041719C  00AB2825  or   $a1,$a1,$t3           ; a1 = lead<<8|trail（合成对偶码）
004171A0  0C086B44  jal  0x0021AD10           ; CharWidth(对偶码)
004171A8  02228821  addu $s1,$s1,$v0          ; 累计
004171AC  26940002  addiu $s4,$s4,2           ; ★ i += 2（字节）
004171B0  08086B21  j    0x0021AC84           ; 回原版内环判据（跳过 +1）
004171B8  0C086B44  jal  0x0021AD10           ; CharWidth(单字节)
004171C0  08086B1F  j    0x0021AC7C           ; 回原版累计 + s4+=1
```
**单位一致**：`s4` 是**字节**下标、`s0` 是**字节**长度，单字节 +1 / 对偶 +2 ✔，
累计的 `v0` 是**像素宽** ✔。这一处是"计数 vs 字节"的**正确**实现。

* `0x21AC90 → j 0x565670`（`0x565670..0x56571C`，44 条）：

```
00565670  24020000  addiu $v0,$zero,0           ; i = 0（**字节**下标）
00565674  24090000  addiu $t1,$zero,0           ; t1 = 对偶字符计数
00565678  260EFFFF  addiu $t6,$s0,-1            ; t6 = len-1
0056567C  004E502A  slt  $t2,$v0,$t6
00565680  1140001F  beq  $t2,$zero,0x565700     ; 扫完
00565688  02425821  addu $t3,$s2,$v0
0056568C  916B0000  lbu  $t3,0($t3)
00565690  2D6C00A1  sltiu $t4,$t3,0xA1
00565694  11800003  beq  $t4,$zero,0x5656A4
0056569C  081595BC  j    0x5656F0              ; 单字节 i+=1
005656A4  2D6C00B1  sltiu $t4,$t3,0xB1
005656A8  11800011  beq  $t4,$zero,0x5656F0     ; ≥0xB1 单字节（GATE）
005656C0  916D0001  lbu  $t5,1($t3)             ; trail
005656C4  2DAC00A1  sltiu $t4,$t5,0xA1
005656C8  15800009  bne  $t4,$zero,0x5656F0     ; ★ ZH63 把这里的 beq 改成 bne（极性修复）
005656D0  2DAC00FF  sltiu $t4,$t5,0xFF
005656D4  11800006  beq  $t4,$zero,0x5656F0
005656DC  25290001  addiu $t1,$t1,1             ; 对偶数 +1
005656E0  24420002  addiu $v0,$v0,2             ; i += 2（字节）
005656F0  24420001  addiu $v0,$v0,1             ; i += 1（字节）
00565700  01C97023  subu $t6,$t6,$t1            ; ★ t6 = (len-1) - pairs = 字符数 - 1
00565704  8E6F0018  lw   $t7,24($s3)             ; kern = *(u32*)(s3+0x18)
00565708  01CF0018  mult $t7,$t6,$t7             ; ★ 三操作数：**$t7 = (字符数-1) × kern**
0056570C  00007812  mflo $t7                     ; （冗余，值相同）
00565710  022F8821  addu $s1,$s1,$t7             ; 累计
00565714  02201021  addu $v0,$s1,$zero           ; 返回值 = s1
00565718  08086B29  j    0x0021ACA4              ; 回原版尾声
```
**单位推导**：设串字节长 `L = 2P + S`（P 个对偶、S 个单字节）⇒ 字符数 `N = P + S = L − P`，
所以 `(L−1) − P = N − 1` ✔ **`t6` 确实是"字符数−1"，单位是字符**；
再乘 `kern`（像素/字符）⇒ 加到**像素**累计量 `s1` 上 ✔ 单位自洽。
（`0x21AC98` 原版的 `mult v1,v0` rd=0 ⇒ 结果丢弃，原版只加 **1 次** kern；汉化改成
`(N−1)` 次 —— 这是 **H2 的语义改变**，见 §3.3 F4，**是有意为之**，ZH63 报告有记录。）

### 2.4 `RSFont::ComputeCharTextureCoords`：`0x21ADE0` → `j 0x417050`

**原版 `0x21ADE0..0x21AF28`（328 B，叶子，无栈帧）**：

```
0021ADE0  8C8A0028  lw   $t2,40($a0)        ; t2 = this->mFontDef
0021ADE4  30A300FF  andi $v1,$a1,0x00FF
0021ADE8  00031E3C  dsll32 $v1,$v1,24
0021ADEC  00031E3F  dsra32 $v1,$v1,24       ; (s8)c
0021ADF0  81450020  lb   $a1,32($t2)        ; def+0x20
0021ADF4  00651823  subu $v1,$v1,$a1
0021ADF8  306500FF  andi $a1,$v1,0x00FF
0021ADFC  04A20006  bltzl $a1,0x21AE18      ; idx<0 → 0
0021AE00  70002E28  pcpyld $a1,$zero,$zero
0021AE04  8D430044  lw   $v1,68($t2)        ; nrec
0021AE08  00A3102B  sltu $v0,$a1,$v1
0021AE0C  14400002  bne  $v0,$zero,0x21AE18
0021AE14  70002E28  pcpyld $a1,$zero,$zero   ; idx>=nrec → 0
0021AE18  8D4A0038  lw   $t2,56($t2)        ; recs
0021AE20  00051880  sll  $v1,$a1,2          ; ← 汉化 cave 的"记录分支"也回到这里
0021AE24  00651821  addu $v1,$v1,$a1
0021AE28  00031840  sll  $v1,$v1,1          ; ×10
0021AE2C  006A2821  addu $a1,$v1,$t2
0021AE30  94A50002  lhu  $a1,2($a1)         ; rec.u0 (u16)
0021AE34  04A00004  bltz $a1,0x21AE48
0021AE38  00055042  srl  $t2,$a1,1          ; (延时)
0021AE3C  44850000  mtc1 $a1,$f0
0021AE40  10000007  beq  $zero,$zero,0x21AE60
0021AE44  46800020  cvt.s.w $f0,$f0
0021AE48  30A50001  andi $a1,$a1,0x0001
0021AE4C  01455025  or   $t2,$t2,$a1
0021AE50  448A0000  mtc1 $t2,$f0
0021AE58  46800020  cvt.s.w $f0,$f0
0021AE5C  46000000  add.s f0,f0,f0         ; ★★ 记录路径的 UV **×2**（网格路径没有）
0021AE60  E4C00000  swc1 $f0,0($a2)        ; *out_u0
0021AE64..0x21AF1C  同法处理 v0/u1/v1 → *out_v0/*out_u1/*out_v1
0021AF20  03E00008  jr   $ra
```

**汉化**：入口两字 `8C8A0028`/`30A300FF` → `08105C14 j 0x417050` + `nop`，cave `0x417050..0x417138`：

```
00417050  8C8A0028  lw   $t2,40($a0)
00417054  30A300FF  andi $v1,$a1,0x00FF
00417058  00056202  srl  $t4,$a1,8
0041705C  15800006  bne  $t4,$zero,0x417078       ; 高字节≠0 ⇒ DBCS 网格
00417064  81450020  lb   $a1,32($t2)
00417068  00651823  subu $v1,$v1,$a1
0041706C  306500FF  andi $a1,$v1,0x00FF
00417070  10000009  beq  $zero,$zero,0x417098      ; ⇒ 共用判据
00417078  318C00FF  andi $t4,$t4,0x00FF            ; DBCS
0041707C  258CFF5F  addiu $t4,$t4,-161             ; t4 = lead-0xA1
00417080  306D00FF  andi $t5,$v1,0x00FF
00417084  25ADFF5F  addiu $t5,$t5,-161             ; t5 = trail-0xA1
00417088  240E005E  addiu $t6,$zero,94
0041708C  018E6018  mult $t4,$t6                  ; ★ 三操作数 rd=t4 ⇒ **$t4 = (lead-0xA1)×94**
00417090  018D6021  addu $t4,$t4,$t5              ; slot = (lead-0xA1)*94 + (trail-0xA1)
00417094  258500E0  addiu $a1,$t4,224              ; a1 = slot + 0xE0
00417098  8D430044  lw   $v1,68($t2)              ; nrec
0041709C  00A3102B  sltu $v0,$a1,$v1
004170A0  14400024  bne  $v0,$zero,0x417134       ; a1<nrec ⇒ 记录表
004170A8  24ACFF20  addiu $t4,$a1,-224             ; slot
004170AC  240E003E  addiu $t6,$zero,62            ; NCOL
004170B0  018E001A  div  $t4,$t6
004170B4  00006812  mflo $t5                       ; row = slot/62
004170BC  00007012  mflo $t6                       ; (×62)
004170C0  018E6023  subu $t4,$t4,$t6               ; col = slot%62
004170C4  240F0010  addiu $t7,$zero,16             ; CW
004170CC  00007012  mflo $t6                       ; 16*col
004170D0  25C50000  addiu $a1,$t6,0                ; u0
004170D4  25CC0010  addiu $t4,$t6,16               ; u1
004170D8  240F000C  addiu $t7,$zero,12             ; SKIP_ROW
004170DC  01AF782A  slt  $t7,$t5,$t7
004170E0  15E00002  bne  $t7,$zero,0x4170EC
004170E8  25AD0003  addiu $t5,$t5,3                ; row += 3（跳过图标带）
004170EC  240F0010  addiu $t7,$zero,16             ; CH
004170F8  25CD0002  addiu $t5,$t6,2                ; v0 = 16*row + 2
004170FC  25CE0012  addiu $t6,$t6,18               ; v1 = 16*row + 18
00417100..0x417130  mtc1/cvt.s.w/swc1 ×4 → *out_u0,*out_v0,*out_u1,*out_v1
0041712C  03E00008  jr   $ra
00417134  8D4A0038  lw   $t2,56($t2)               ; 记录分支：t2 = recs
00417138  08086B88  j    0x0021AE20                ; 回原版记录矩形代码（a1 = idx）
```

**契约核对**：cave **不使用栈**（无 `sp` 访问），只写 `a2/a3/t0/t1` 四个**调用方给的 out 指针**
（`0x219C24..0x219C34` = `sp+176/180/184/188`，在 `DrawString` 的 224 字节帧内）✔；
`jr ra` 直接返回给调用者 ✔。

---

## 3. 逐函数「计数 vs 字节」审计

### 3.1 审计表

| # | 函数（cave VA） | 输入 | 返回（单位） | 有无分配器 | 写目标 / 边界 | 索引单位一致性 | 数组/表访问 | 步进一致性 | 返回值语义 vs 原版 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 字符解码器 `0x416ED0` | `a0`=out、`a1`=字节；**读调用方 `$s0/$s6/$s7`** | `v0` = **输入字节数** ∈{1,2}；副作用 `out[-1]`=长度、`out[0..1]`=u16 码 | **无** | 仅 `out[-1..1]`；唯一调用点 `0x219BCC` 给 `a0=sp+222`，帧 `sp+0..223` ⇒ **全在帧内** | `out` 语义 = 3 字节结构（len+u16），调用点已按此改 | 无 | `a1` 字节、`$s0` 字节下标、`$s7` 字节长 → 全字节 ✔ | 原版"写 1 字节 / 返回 1" → "写 u16 码 + 长度字节 / 返回 1 或 2"；**调用点已同步改**（`sp+223→222`、`lb→lhu`）✔ | **无越界**（唯一硬要求 = out≥3 B，已满足） |
| 2 | CharWidth `0x416F40` | `a0`=RSFont*、`a1`=码（≤0xFF 单字节 / ≥0x100 对偶） | `v0` = **像素宽**（`fptosi(f1×scale)`）或 16 / 20 / `*(u32*)(this+0x14)` | **无** | **不写任何内存**；只读 `this+0x28`、`def+0x20`、`def+0x44`、`def+0x38`、`this+0x1C` | idx 一律 &0xFF（取值域 0..255）；`slot` 用 `sltu`/`div` 无符号 | `recs + idx*10`，idx 经 `sltu idx<nrec` 检查后才用 | 只有 +0x10 步进（记录 10 字节）✔ | ★**删掉了 `this+0x24` 等宽模式短路**（F3） | **无内存写**；H1 不成立 |
| 3 | StringWidth 内环 `0x417150` | `a1`=当前字节、`$s0/$s2/$s4/$s1/$s3` | 无（改 `s1`/`s4`） | **无** | 无 | `s4` 字节下标、`s0` 字节长；+1/+2 ✔ | 无 | ✔ | 与原版等价（把"每字节一次 CharWidth"改成"每字符一次"） | **正确** |
| 4 | StringWidth 尾 `0x565670` | `$s0`=**字节**长、`$s2`=串首、`$s3`=字体、`$s1`=累计像素 | `v0`=像素总宽 | **无** | 无 | `(len−1)−pairs = 字符数−1`（推导见 §2.3）✔ | 无 | `i+=1`(单) / `i+=2`(对偶) 同在一个 `v0` 上加 ✔ | ★`+1×kern` → `+(字符数−1)×kern`（F4，**有意**） | **单位自洽** |
| 5 | ComputeCharTextureCoords `0x417050` | `a0`=RSFont*、`a1`=码、`a2/a3/t0/t1`=out 指针 | 无（写 4 个 float） | **无** | 4 个调用方指针（`sp+176/180/184/188`，帧内） | `slot` 单位 = 格位；`row=slot/62, col=slot%62` ✔ | `recs` 仅在 `a1<nrec` 分支（此分支直接回原版 0x21AE20，不用 cave 的算术） | `mult` 三操作数 ⇒ **×94 真的发生了**（§3.2）✔ | 记录路径的 `×2` 标度保持原版不动 | **无越界**；H1 不成立 |
| 6 | `0x417500`（DoWordWrap 内） | `$s5`=外层 this、`$s2`=**字节**下标、`$s6`=**字节**长、`$s3`=像素 x、`$s7`=像素上限、`a0`=`*(sp+252)` | 无 | **无** | 无 | `data + s2`、`s2 += 1/2` —— 与 `__vc__` 的 `data + index` **同域**（§4 F1 前的核对）✔ | 无 | ✔ | 用 `mImpl->data` 直取代 `__vc__(obj,s2)`，等价 ✔ | **等价**（`a0` 的取值也核对过，见 §4 F0） |
| 7 | `0x5657C8` | `s0+68` 处 RSString 成员 | 无 | **无** | 无 | ★ `lhu a1,2(t0)` = {mode,pad} 当长度 | — | — | ★**字段宽度错配** | **F1 — 头号嫌疑** |
| 8 | `0x565760`（辅助） | `a0`=char*、`a1`=**长度** | `v0`=去尾空格后长度、`v1`=是否含≥0xA1 | **无** | 无 | 按字节扫 `data[0..a1)` | — | `p+=1` ✔ | — | a1 由调用方给；F1 的受害者 |
| 9 | `0x565730` | `a0`=文本对象 | 无 | 无 | `sw 236(a0)` | 定值/`+4` | — | — | `*(a0+0x3C)+*(a0+0x4C)(+4 if 0x14==0x52)` → `236(a0)` ✔ 与原版 `addu v1,a1,v1` 一致 | 等价 |
| 10 | `0x417200` | `v0`=宽度 | `v0`（26→16） | 无 | 无 | — | — | — | **H2**：把 26 映射成 16 | 有意（配合 F3） |
| 11 | `0x411690`+`0x21CC08` | `a0`=文本宽、`a2` | 无 | 无 | 无 | `a0 -= 10`（像素） | — | — | 居中量微调 | 与内存无关 |
| 12 | `0x565900` | `s1`=组件、`a1/a3` | 无 | 无 | 无 | 差 `+7`（像素） | — | — | 转发到 `RSFontMgr::DrawString`（返回值约定不变） | 与内存无关 |
| 13 | `0x4176A0/0x417680/0x417650/0x4176B0` | — | 常数 16 | 无 | 无 | — | — | — | **H2**：把"度量函数返回值"换成常量 16 | 有意 |

**结论：在"申请/写入"这个字面意义上，H1 无处落地** —— 四个函数**一次都不调用分配器**
（`python work/tools/cave_audit.py writes` 列出 cave 区间内全部 store，见 `r79/dump/writes.txt`：
只有 `sh a1,0(a0)` / `sb v0,-1(a0)` / 4 个 `swc1` 到 out 指针 / `sw 236(a0)` /
`sd ra`、`sw t0..v0` 到**自己帧内**的保存区）。
唯一有"边界"要求的是解码器的 `out[-1..1]`，而调用点已经把指针挪好、帧也有空间。

### 3.2 ★ 方法学更正：`MULT` 是 EE 三操作数指令（否则会误判成"少了 ×94"）

`work/tools/cave_fields.py` 打印原始字段：

```
0041708C  018E6018  op=00 rs=12(t4) rt=14(t6) rd=12(t4) sa=0 fn=18   ; MULT t4,t4,t6 → t4
00416FA0  012E4018  op=00 rs= 9(t1) rt=14(t6) rd= 8(t0) sa=0 fn=18   ; MULT t0,t1,t6 → t0
00565708  01CF0018  op=00 rs=14(t6) rt=15(t7) rd= 0(zero) sa=0 fn=18 ; MULT (2 操作数形式)
0056570C  00007812  op=00 ... fn=12                                   ; MFLO t7
```

`rd` 字段**非 0**，而且 PCSX2 的 EE 重编译器就是这么实现的：

```cpp
// third_party/emu/pcsx2_src/pcsx2/x86/ix86-32/iR5900MultDiv.cpp
REC_FUNC_DEL(MULT, _Rd_);                                   // L21
EERECOMPILE_CODERC0(MULT, XMMINFO_READS|XMMINFO_READT|(_Rd_ ? XMMINFO_WRITED : 0));   // L244
if (writed && _Rd_ && ...) xMOV(ptr64[&cpuRegs.GPR.r[_Rd_].UD[0]], rax);              // L102-117
```

⇒ `MULT rd,rs,rt` 把 `rs×rt`（低 64 位）写进 **GPR[rd]**，同时也写 HI/LO。
所以 `0x41708C` 之后 `$t4` 已经是 `(lead−0xA1)×94`，`0x417090 addu t4,t4,t5` 是**正确**的
`+ (trail−0xA1)`；`0x416FA0` 之后 `$t0` 已经是 `(lead−0xA1)×94`，`0x416FA4 addu t0,t0,t2` 同样正确。
**两条格位公式都成立**，`slot = (lead−0xA1)*94 + (trail−0xA1)`，与工具链
（`tcslib.PAIR_STRIDE=94`、`gen_font16.py:139`、`patch_zh113_expand_font.py:27`）**完全一致**。
（`docs/REPORT_font_capacity_decompile.md` §3.2 的 `addu t4,t4,t5  ; t4 = slot = (lead-0xA1)*94+...`
注释按普通 MIPS 写会读不出乘法的来源，结论虽对但注释应订正为"`mult` 三操作数"。）

### 3.3 H2 的三处：返回值语义被改

**F3（会影响布局）｜CharWidth 删掉了 `this+0x24` 等宽模式**
* 原版：`0x21AD18 lbu v0,36(a0)` / `0x21AD1C beq v0,zero,0x21AD2C` /
  `0x21AD24 beq zero,zero,0x21ADD0` / `0x21AD28 lw v0,12(a0)` ⇒ **标志≠0 时返回 `*(u32*)(this+0xC)`**（单一等宽值），
  完全不做逐字宽计算。
* 汉化：`0x21AD18` = `j 0x416F40`、`0x21AD1C` = `nop` ⇒ **短路被删除**，一律走逐字宽。
* **同一个标志在未被替换的 `CharHeight`（`0x21ACD0`）里仍然生效**
  （`0x21ACD8 lbu v0,36(a0)` / `0x21AD04 … lw v0,16(a0)`），
  ⇒ 对 `this+0x24 != 0` 的对象，**`CharWidth` 与 `CharHeight` 现在对"模式"的判断不一致**。
* 补偿痕迹：cave `0x417200`（由 `0x219ADC` 挂入）把宽度 **26 → 16**；
  `0x1FF8D0` 把 `subu v0,v1,v0` 换成 `addiu v0,v1,-21`；`0x2071B4` 换成 `-16`。
  ⇒ 说明作者知道某些对象的"等宽值"是 26/21/16 并逐个打补丁。
* **判定：H2 成立**（返回语义确实变了），但它是**静态可枚举**的语义改变，不是随机损坏源。

**F4（有意）｜StringWidth 尾部 kern 的乘数**
`+1×kern` → `+(字符数−1)×kern`。`tools/iso_build/patch_zh63.py` 头部有完整记录
（"该 cave 自 ZH57 起对真实字符集等效于 EN 原公式（no-op），修复后 x +8/+10/+11/+17 精确吻合"，
修复方式是把 `0x5656C8` 的 `beq` 改成 `bne` —— 本轮在 §2.3 的 cave 体里核对到
`0x5656C8 15800009 bne` 确实已是修好的形态）。
**判定：H2 成立但是设计意图**，单位自洽（§2.3）。

**F5｜`0x417200` / `0x417650` / `0x417680` / `0x4176A0` / `0x4176B0` 把度量函数返回值换成常量**
`0x4176A0` 就是 `addiu v0,zero,16; jr ra`（3 条桩），而 `0x21CB30` 原来调的是
`CharHeight`（`0x21ACD0`）。⇒ **`ComputeDrawXY` 的居中量不再由字体度量决定，而是硬编码 16。**
**判定：H2 成立、有意**（居中补丁），但它意味着"文本宽度"这条数据流已经**部分脱离**真实度量。

---

## 4. 审计扩展到全部 43 个挂点后的发现

### F0（先排除一个可疑点）｜`0x21CD74 lw a0,252(sp)` 是**正确的**

`DoWordWrap` 里 `sp+248` 是一个 **RSUIString 对象**、`sp+252` 是它的 `+4` 字段。
由**未改动**的库函数定布局：

```
Length__10RSUIStringCFv  0x53FD58  lw v0,4(a0)   ; v0 = this->mImpl
                         0x53FD5C  lw a0,4(v0)   ; a0 = mImpl->data
                         0x53FD68  jal 0x406F28  ; strlen(data)     ← Length() = strlen
__vc__10RSUIStringFi     0x5414C8  lw v0,4(a0)   ; v0 = this->mImpl
                         0x5414C9  ...
                         0x5414D0  addiu v1,v0,2
                         0x5414D4  lbu  v0,2(v0) ; ← mImpl+2 按 **u8** 读
                         0x5414D8  slti at,v0,2
                         0x5414E4  addiu v0,v0,-1
                         0x5414E8  sb   v0,0(v1) ; ← 又按 **u8** 写回
                         0x54151C  sh   v0,0(s2) ; ← mImpl+0 (u16) = strlen+1   ★长度字段
                         0x54152C  sw   v0,4(s2) ; ← mImpl+4 = data
                         0x541560  lw   v0,4(s1)
                         0x541570  lw   v0,4(v0)
                         0x541578  addu v0,v0,s0 ; ★ operator[](i) = data + i  （**纯字节偏移**）
```
⇒ `mImpl` = `{ u16 len_plus1 @0 ; u8 mode @2 ; u8 pad @3(构造函数从不写) ; char *data @4 }`，
`operator[]` 是**字节**索引 ⇒ `DoWordWrap` 的 `s2` 是**字节**下标，cave 的 `data+s2`、`s2 += 2` **同域且正确**。
**⇒ 之前怀疑的"字符下标当字节用"在这一处不成立，排除。**

### ★ F1（头号嫌疑）｜`0x5657E0 lhu a1,2(t0)`：把 u8 模式字节当 u16 长度

**现场**（cave `0x5657C8`，由 `j 0x5657C8` 从 `0x3070B4` 挂入）：

```
003070B4  27A40038  addiu $a0,$sp,56     ; 原版第一条（被换掉）
003070B8  26050044  addiu $a1,$s0,68     ; (j 的延时槽，保留)
003070BC  0C14F8AC  jal  0x0053E2B0      ; Left__8RSStringCFUi(ret=a0, this=a1, count=a2)
003070C0  24060001  addiu $a2,$zero,1    ; 原版：取 **第 1 个字符**
```
```
005657C8  8E080048  lw   $t0,72($s0)     ; t0 = RSString::p = RSUIString::mImpl
005657CC  11000016  beq  $t0,$zero,0x565828
005657D4  8D040004  lw   $a0,4($t0)      ; a0 = mImpl->data      ✔ 正确字段
005657D8  10800013  beq  $a0,$zero,0x565828
005657E0  95050002  lhu  $a1,2($t0)      ; ★★★ 错：mImpl+2 是 u8 mode，长度在 mImpl+0(u16)
005657E4  0C1595D8  jal  0x00565760      ; helper(data, a1)  ⇒ a1 被当 **长度** 用
005657EC  1060000E  beq  $v1,$zero,0x565828     ; 无 DBCS ⇒ 走原版（count=1）
005657F4  27A40038  addiu $a0,$sp,56
005657F8  26050044  addiu $a1,$s0,68
005657FC  0C14F8AC  jal  0x0053E2B0      ; Left(ret, this, count = v0 = helper 的去空格长度)
```

`0x565760`（辅助）语义：`p = data; end = data + a1; while (p != end) { if (*p >= 0xA1) has_dbcs = 1; p++; }`
然后从尾部去掉 0x20，返回 `v0 = 去尾空格后的长度`。

**后果链**：
* `mImpl+3`（`pad`）**从不被写**（`__vc__` 的构造路径只写 `+0`(sh)、`+2`(sb)、`+4`(sw)）⇒ 它是**堆残留字节**。
* `pad == 0` ⇒ `a1 = mode = 1` ⇒ helper 只看第 1 个字节 ⇒ 返回 1 ⇒ `Left(1)` = **与原版等价（无害）**。
* `pad != 0` ⇒ `a1 = 1 + (pad<<8)`，最大 **0xFF01 = 65281** ⇒
  helper 沿 `data` **越界扫描最多 ~64 KB**（可能跨出 32 MB EE RAM ⇒ **TLB Miss**），
  并把一个**远大于真实串长**的数当 `Left()` 的**字符数**交给 `RSString::Left` ⇒
  超大子串 / 超长拷贝 ⇒ **堆破坏**（正好能解释"分配器 free 链被写坏"这类崩溃）。
* **堆残留字节 ⇒ 结果依赖会话的分配历史**：与用户现场"09:49 会话 7.68 s 就脏、
  10:30 会话开机干净到 434.15 s"以及"本机 0 缺页"完全同型。
* 作者本人在**同一个 helper 的另一个调用点**用的是正确办法 —— `0x56583C` 里先
  `jal 0x53FD50 (Length__10RSUIStringCFv)` 拿到长度（strlen）再传给 `0x565760`：
  ```
  00565854  27A40070  addiu $a0,$sp,112
  00565858  0C14FF54  jal  0x0053FD50      ; Length()
  00565868  00402821  addu $a1,$v0,$zero    ; a1 = 长度
  0056586C  0C1595D8  jal  0x00565760      ; helper(data, 长度)
  ```
  ⇒ **两处口径不一致**，`0x5657C8` 这处是"就地读字段"，且读错了偏移/宽度。

**最小修法（1 条指令，4 字节窗口）**
```
ISO 文件偏移 = 295*2048 + 0x80 + (VA − 0x100000) = 0x93880 + 0x4657E0 = 0x4F9060
VA 0x5657E0   95050002  lhu $a1, 2($t0)     →     95050000  lhu $a1, 0($t0)
（0x95050000: op=0x25(lhu), rs=8(t0), rt=5(a1), imm=0；只有最低字节 0x02→0x00 变化）
```
`0x95050000` = `lhu a1,0(t0)`（`op=0x25, rs=8(t0), rt=5(a1), imm=0`）。
`mImpl+0` 存的是 `strlen+1`（见 `0x54151C sh v0,0(s2)`），所以修后 `a1 = 串长+1` ⇒
helper 会多看一个 NUL 字节（`0x00 < 0xA1`，不改变 `v1`），返回 `len+1`，`Left(len+1)` 有界 ✔。

**备选的最小"中和"修法（若验证发现 `mImpl+0` 也不是长度）**
```
0x5657C8   081595F2  j 0x5657C8  →  081595E0  j 0x565828
```
即无条件走原版 `Left(1)` 路径，等于关掉这一段汉化逻辑（行为回到原版，无越界）。

### F2｜同一个字符循环的两条出口步进不一致（`0x219D90` vs `0x219DAC`）

```
00219D8C  92630024  lbu  $v1,36($s3)         ; v1 = *(u8*)(font+0x24)   ← 与 F3 同一个模式标志
00219D90  54600008  bnel $v1,$zero,0x219DB4  ; ★ 成立 ⇒ 执行延时槽后直接跳 0x219DB4
00219D94  26100001  addiu $s0,$s0,1          ; ★ 延时槽：只 +1（**字节**）
00219D98  C6610018  lwc1 $f1,24($s3)         ; 且只在"模式==0"时额外加一段 advance
00219DAC  93A200DD  lbu  $v0,221($sp)        ; ← 汉化：取解码器写的"消耗字节数"
00219DB0  02028021  addu $s0,$s0,$v0         ; ← 汉化：+1 或 +2
```
原版两条出口**都是 +1**（`s0` 是**字节**下标），所以一致；
汉化只改了 `0x219DB0`（`+1`→`+v0`），**没有改延时槽 `0x219D94`**。
⇒ **当 `font+0x24 != 0` 时，一个 2 字节字符只让字节下标前进 1**，
后续字节被当成新字符解析（字形错位、串尾可能多读 1 字节）。
**单位本身没错（都是字节），错在两条出口用了不同的"每字符消耗量"。**
最小修法**不能**简单地把延时槽改成 `addu s0,s0,v0`：`0x219D94` 处 `$v0` 早已被
`jal 0x21AD10`（CharWidth）的**宽度返回值**覆盖（`0x219BE0 mtc1 v0,f0`），不是长度。
因此要保行为需要 **3 条**指令（在 cave 里另开一小段：`lbu v0,221(sp)` + `addu s0,s0,v0` + 跳回），
或者接受行为变化用 **2 条 nop**：
```
0x219D90  54600008 bnel v1,zero,0x219DB4  ->  00000000 nop
0x219D94  26100001 addiu s0,s0,1          ->  00000000 nop
```
（后者让控制流恒常落入 DBCS 判定块、恒常经 `0x219DAC/DB0` 的 `+v0`；代价是原版
"模式≠0 时不执行 `0x219D98..0x219DA8` 那段额外 advance"的行为被取消。）
**本轮没有出这一版盘**（F2 只造成文本错位、不造成越界写，优先级低于 F1）。

### F5｜cave 落点安全性的**否证**（有价值，因为它排掉一整类解释）

`work/tools/cave_refs.py` + `work/tools/cave_addrs.py`：
* `0x416E00..0x417800` 内共有 **10 个带完整序言的真函数**（符号表见 §1.2），
  但 **全 .text 里没有任何 `jal`/`j`/条件分支/lui+imm 地址合成指向这个区间**
  （63 个"命中"全部来自这些函数**自己的内部**分支）；
  ELF 里也没有任何**字面 32 位指针**指向它们（唯一的字节命中在 `.symtab` 自身）。
* `0x565600..0x565B00` **一个符号都没有**，全 .text 只有 **1 条**异常分支
  （`0x559718 beq $zero,$a2,+12291 → 0x565728`，落点在 cave 起点**之前 8 字节**，
  且该区间没有任何函数序言 ⇒ 线性反汇编的假命中）。
⇒ **两处 cave 落点都是不可达代码/无名填充，覆盖它们没有破坏任何活代码。**
（这一条同时解释了为什么汉化能正常跑到 7 秒以后。）

### F6｜潜伏（当前数据下不可达，但改了数据就会爆）
cave CharWidth 的 DBCS 分支算出的 `idx = slot + 0xE0 ≥ 0xE0 = 224`，
而现役三个 face 的 `nrec = 224 / 224 / 96`（`docs/REPORT_font_capacity_decompile.md` §4.2）
⇒ `sltu idx,nrec` **恒假** ⇒ **对偶码永远走"返回 16"**，记录分支不可达。
⇒ 一旦按 L2/L5 路线把 `nrec` 抬到 ≥1728，这个分支**立刻活过来**，
而此时 `idx` 的语义必须真的是"记录下标"——**在做 L5 之前必须重跑本审计**。

---

## 5. H1 / H2 结论

| 命题 | 判定 | 证据 |
|---|---|---|
| **H1**（cave 里"按字符数申请缓冲 / 按字节数写"，逐字符越界写 u16 码位/字宽） | **不成立（字面形式）** | §3.1 表：四个函数**零分配器调用、零堆写**；唯一写目标是调用方栈内 3 字节且只有一个调用点（§2.1）；`cave_writes` 全表见 `r79/dump/writes.txt` |
| **H1′**（同一家族：**字段/单位错配**把"模式字节"当"长度"，导致越界读 + 超长子串 ⇒ 堆破坏） | **成立（高危候选，1 处）** | F1，§4：`0x5657E0 lhu a1,2(t0)`；布局证据来自未改动的 `Length`/`__vc__`（`0x53FD58`/`0x5414D4`/`0x5414E8`/`0x54151C`）；同 helper 的另一调用点用的是 `Length()`（`0x565858`） |
| **H2**（返回值语义被改） | **成立（3 处）** | F3（CharWidth 删等宽短路，与 CharHeight 不一致）、F4（kern 乘数，有意）、F5′（度量换常量 16，有意）；§3.3 |
| **H2′**（步进不一致） | **成立（1 处）** | F2，§4：`0x219D94` 仍是 `+1`，`0x219DB0` 已改 `+v0` |
| **"0x14 进指针槽"是否由文本 cave 直接产生** | **本轮【未能证实】** | cave 代码没有把字宽/码位写进任何指针槽的路径；cave 的写目标已逐条穷举（§3.1 表 + `r79/dump/writes.txt`） |

---

## 6. 对照盘 `GR_ZH119` 与验证步骤

### 6.1 盘
* 基底 `work/builds/GR_ZH113b`（其 ELF 与用户崩过的 `GR_ZH111` 逐字节相同，§1.1）
* 唯一改动：**ELF 4 字节（实际变 1 字节）** `0x5657E0: 0x95050002 → 0x95050000`
* 脚本：`work/tools/cave_mk119.py`（自带全盘 diff 断言：窗口外差异必须为 0）
* 产物：`work/builds/GR_ZH119/GR_ZH119.iso`（**已构建完成并复核**）

**构建实测结果（本轮已完成，不是待办）**
```
[base]  work/builds/GR_ZH113b/GR_ZH113b.iso (sha ff3abd3c50e380f6…)
[ELF]   0x005657E0: 0x95050002 -> 0x95050000  (lhu a1,2(t0) -> lhu a1,0(t0)) OK
[diff]  全盘差异 1 字节, 全部位于 ELF 0x4F9060..0x4F9064 窗口内 OK
[iso]   work/builds/GR_ZH119/GR_ZH119.iso  (1.65 GB)
```
独立复核（从**成品 ISO** 重新抽出 ELF，`r79/dump/elf_zh119.bin`）：
```
0x5657E0  00000595  lhu $a1, 0($t0)          ← 与 GR_ZH113b 的 0x95050002 只差最低字节
逐字节 diff(elf_zh113b, elf_zh119) = 1 字节, 文件偏移 0x465860 (= ISO 0x4F9060) ✔
```

> 若用户环境验证后认为该字段其实是长度（即 `lhu a1,0` 不是正解），
> 用 F1 的"备选修法"（`0x5657C8: 081595F2 → 081595E0`）再出一版即可 ——
> 两者都只动 ELF，不动文本/字库/容器。

### 6.2 ★ 验收口径（沿用上一轮定案，不用"跑十分钟没崩"）
**在能复现的环境里把 `TLB Miss` 行数从 50 降到 0。**

```powershell
# 1) 冷启动跑 GR_ZH119,只数缺页
python tools\iso_build\fix_zh118_run.py --iso <...>\work\builds\GR_ZH119\GR_ZH119.iso `
       --tag r79_zh119 --maxframes 4000 --snap 0 --timeout 400 `
       --memcards <用户卡只读副本> --outroot <...>\work\builds\GR_ZH98\temp\r79
(Select-String <out>\dump_r79_zh119\emulog.txt -Pattern 'TLB Miss').Count   # 期望 0
# 2) 同样跑一次 GR_ZH111 / GR_ZH113b 作对照（期望 50 或 >0）
```
⚠ **VM paused 时退出码仍为 0，必须看 emulog。**

### 6.3 若本机仍复现不出（很可能）
**不要伪造结论。** 请用户按下面的最小步骤做一次**单变量**验证：

1. 用 `GR_ZH119.iso` 冷启动，照上次复现的流程玩到"天空盒/HUD 异常"出现的同一位置；
2. 出现后立刻看 `emulog.txt` 里 `TLB Miss` 的**行数**与**首行时间戳**，和 `GR_ZH111` 对比：
   * 若 **50 → 0（或 13 → 0）且首现时刻 >600 s** ⇒ **F1 被证实**；
   * 若行数不变 ⇒ F1 不是成因（回到 §7 的未定案清单）；
3. 无论结果如何，**请把两份 emulog 原文给我们**（这是唯一能判定"50→0"的东西）。

### 6.4 构建命令（本轮实际用的）
```powershell
python tools\iso_build\make_build.py GR_ZH119 --from work/builds/GR_ZH113b `
       --patch work/tools/cave_mk119.py `
       --no-font-compact --no-font-repack --no-font-dump --no-textdump --no-text-snapshot
```

### 6.5 若要做 F1 的**直接**确认（比出盘更省，1 次 3 分钟跑）
`gsrunner` 已有 `-grhook <pc>`：**在每个基本块入口**打印 `a0..a3/v0/s0/s1/ra/sp`（上限 20 万行）。
所以不要钩 `0x5657E4`（它是 fall-through，未必是块入口），而应钩**函数入口 `0x565760`**
—— 它被两处 `jal` 调用，必然是块入口，而且打印的 **`ra` 能区分是哪一处调进来的**：

```
-grhook 0x565760        # helper(data=a0, len=a1)
```
| `ra` | 调用点 | 期望 |
|---|---|---|
| `0x5657E8` | cave `0x5657E0` 之后（**F1 现场**） | 若 `a1` 的高字节恒为 0 且等于串长 ⇒ **F1 不成立**；若 `a1` 恒 = `0x??01`（低字节 1、高字节 = `mImpl+3` 堆残留）而 `a0` 指向的串明显更长 ⇒ **F1 成立** |
| `0x565870` | `0x56583C` cave 里 `Length()` 之后（**正确口径**） | `a1` 应等于串长（strlen）—— 用它当"正确答案"的参照 |

**判据**：把同一次运行里两组 `(a0, a1)` 并排看。**两组 `a0` 指向的字符串长度差不多、
但 `ra=0x5657E8` 那组的 `a1` 与另一组不一致（尤其出现 `0x??01`/巨大值）⇒ F1 成立。**
（`-grhook` 不打印 `t0`，所以钩函数入口而不是 `0x5657E0`。）

---

## 7. 已知限制（如实）

1. **本机没有复现**（沿用 `docs/REPORT_zh_heap_corruption.md` §4 的五行实验结论：
   BIOS/版本/记忆卡/ISO 全对齐后 0 缺页）。**本轮没有实机验证任何东西**，
   所有结论都是"盘上字节 + 符号表 + 静态数据流"。
2. **F1 有一环未闭环**：`mImpl+2` 是 u8 标志（由 `__vc__` 的读/写宽度与"减一写回"证明）
   这一点很强，但**没有任何**原始代码**读取** `mImpl+0` 作为长度（`Length()` 用的是 `strlen`）。
   所以"长度存在 +0"是由 `__vc__` 的构造路径（`sh strlen+1,0(s2)` → `lhu 0(s2)` 当分配大小）
   **间接**推出的。这一环由 §6.5 的 `-grhook` 一条命令即可闭环。
3. **`mImpl+3` 是否真的非 0**（F1 危害的开关）**未实测**。若堆分配总是把 8 字节块清零/复用，
   则 F1 可能长期表现为无害（这也与"多数会话正常"相容）。
4. **`0x219D90` 那条 `bnel` 的语义**是按 PCSX2 `recBNEL_process`
   （`iR5900Branch.cpp:299-314`：not-taken ⇒ `SetBranchImm(pc+4)`，延时槽被跳过）判定的；
   我没有在真机上单步确认。若该延时槽在 not-taken 时也执行，F2 就不成立（两条路都 +1 再 +v0）。
5. **F3/F5′ 的"影响面"未量化**：哪些文本对象 `this+0x24 != 0`、结构化数据在哪，
   本轮没有定位（需要 hook `0x21AD18` 的调用者或扫对象）。
6. **未做盘链二分**（`GR_EN_ORIG → … → GR_ZH113b`）：证据不足（本机无区分度信号），
   而且 §1.1 已经证明 `GR_ZH111` 与 `GR_ZH113b` 的 ELF **完全相同** ⇒
   对"崩过的盘"和"现役盘"二分 ELF 没有意义（要分的是**数据**，不是代码）。
7. **未跑模拟器**（本轮零模拟器占用；§6.5 的 hook 方案是留给下一轮的）。

## 8. 未定案

| # | 未定案项 | 最省的下一步 |
|---|---|---|
| 1 | `mImpl+2` vs `mImpl+0`（F1 的正反） | `-grhook 0x5657E4` 一次（§6.5） |
| 2 | `mImpl+3` 堆残留是否常非 0 | 同上跑里加 `-grwatch <mImpl> 8`，或读 hook 时的 `a0-2` 内存 |
| 3 | F1 是否是**用户现场坏值 0x14 进指针槽**的成因 | 复现环境 + `-grwatch <受害指针槽> 4`（工具 r76 已就绪） |
| 4 | F2 的实际触发面（哪些字体对象 `+0x24 != 0`） | hook `0x219D8C`，统计 `v1` |
| 5 | 2fps / 天空盒 / HUD 的直接成因 | 不在本轮范围 |

---

## 9. 产物索引与纪律自查

| 产物 | 说明 |
|---|---|
| `work/tools/cave_dis.py` | R5900/MMI 反汇编器 + ELF 载入（`dis`/`diso`/`callers`/`jtargets`/`segs`） |
| `work/tools/cave_extract_elf.py` | 从 ISO 只读抽出 `SLUS_206.13`（LBA 295） |
| `work/tools/cave_audit.py` | 全量差分 + side-by-side + jmap + cave 内 store 清单 |
| `work/tools/cave_fields.py` | 打印原始 `rs/rt/rd/sa/fn`（用于证明 `MULT` 三操作数） |
| `work/tools/cave_refs.py` | cave 区间内的原版函数序言 + 全 .text 引用扫描 |
| `work/tools/cave_addrs.py` | `jal/j/branch/lui+imm` 地址合成扫描（证明不可达） |
| `work/tools/cave_probe.py` | 三处定点探查（栈槽写者 / 字面指针 / 长度字段现场） |
| `work/tools/cave_syms.py` | 读 ELF 内 `.symtab`（38,722 符号）解析审计用 VA |
| `work/tools/cave_mk119.py` | `GR_ZH119` 的单指令补丁脚本（带全盘 diff 断言） |
| `work/builds/GR_ZH98/temp/r79/dump/` | `diff_ranges.txt`（全量差分）`jmap.txt`（43 个挂点 + cave 体）`side_0021AC80_0021AD20.txt` / `side_0021ADD0_0021AF30.txt` / `side_00219B80_00219DC0.txt` / `side_0021CD40_0021CE20.txt` / `side_003070A0_003070D0.txt`（四个函数 + F1 现场的逐条 side-by-side）`writes.txt`（cave 内全部 store）`cave_refs.txt`（落点原住户 + 引用扫描）`elf_zh113b.bin` `elf_zh119.bin` `elf_en_orig.bin` `elf_zh111.bin` |
| `work/builds/GR_ZH119/GR_ZH119.iso` | 对照盘（**已构建**，1.65 GB；构造与复核见 §6.1） |

* ✅ 未切分支（全程 `round73/font-decompile`）、未 commit、未 merge
* ✅ 历史 ISO **只读**（`cave_extract_elf.py` 只读；未改 `GR_ZH111`/`GR_ZH113b`/`GR_EN_ORIG`）
* ✅ 用户证据 `work/temp/NEW_Mem/**`、`%LOCALAPPDATA%\PCSX2\**` **只读**（本轮未打开写入句柄）
* ✅ **未改** `tools/text_csv/*`、`font_compact.py`、`make_build.py`、`tools/font_pipeline/data/*`
* ✅ **未改任何模拟器源码**（本轮零模拟器占用，未启任何实例，未杀任何进程）
* ✅ 写盘范围仅：`docs/REPORT_cave_count_vs_bytes.md`、`work/tools/cave_*.py`、
  `work/builds/GR_ZH98/temp/r79/**`、`work/builds/GR_ZH119/**`
* ✅ 未用 `Select-Object -First N`
