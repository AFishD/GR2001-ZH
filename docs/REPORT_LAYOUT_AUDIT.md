# GR_LAYOUT · B 线（gate 0xBA / h=644 / 64 列）布局与步进一致性审计

> 生成：2026-10-17 · 执行者：**GR_LAYOUT** 子代理
> 输入（**全部只读**）：`work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf`（= 真 K2 ELF，sha256 `5cb59175…f47d8`）、
> `work\builds\GR_REBUILD\GR_REBUILD2400.iso`（sha256 `d7f83d7e…443ca0`，1,648,164,864 B）、
> `third_party\orig\ps2\slus_out\SLUS_206.13`（原盘 ELF）、`work\tools\*`、`tools\hanliu\tools\*`、
> `work\builds\GR_CSFIX\audit\*`、`work\builds\GR_REBUILD\tools\rb_verify_k2.py`、`work\tools\cap_build_k2.py`
> 写入仅 `work\builds\GR_LAYOUT\**`、`docs\REPORT_LAYOUT_AUDIT.md`、`docs\DISASM_TEST_GUIDE.md`（追加）。
> 本目录工具：`work\builds\GR_LAYOUT\tools\{lay_dis,lay_map,lay_reach,lay_classify,lay_census,lay_sites_diff,lay_fontres,lay_mkiso,smoke_lay}`。
> 原始输出：`work\builds\GR_LAYOUT\audit\*`。

---

## 0. 先给三句话

1. **U1 判定：`×94` 一个字都没丢。** `0x416FA0` / `0x41708C` 上根本不是"MIPS32 两操作数 `mult` 缺 `mflo`"，
   而是 **R5900（PS2 EE 核）的三操作数 `MULT rd, rs, rt`**（SPECIAL `funct=0x18`，低 32 位积**直接写 rd**，
   不存在"要再 `mflo` 一次"这回事）。本工程既有反汇编器 `work\tools\cave_dis.py:94` 把 `funct 0x18`
   打成两操作数并把 `rd` 字段**丢掉**，才产生了"乘积从未被读"的假象。
   ⇒ `dfix_apply.py --set probe-slot` 与 `REPORT_DISASM_ROOTCAUSE.md §4 #3` 的静态推导**是反的**：
   `idx = 0xE0 + (lead−0xA1)×94 + (trail−0xA1)` 与工具登记的 ABI 完全一致，
   **`probe-slot` 绝不能应用**（它会把正确的 `addu t0,t0,t2` 换成读陈旧 `LO` 的 `mflo t0`）。
   证据见 §2。

2. **B 线的图集几何是自洽的**（ncol=64 / SKIP=2 / Y0=3 / V1=+19 ↔ 盘上 1024×644 图集 + 三段 FT 记录带）。
   逐项对得上，**没有**"改了 ELF 常量但数据没跟着改"的错位；`addiu rd,zero,62` 的 20 处残留
   **全部在原盘未改代码里**（逐个给结论见 §3.1），`ncol` 在汉化改写区里**只有一个装载点**（§3.3）。

3. 真正"只有中文数据规模才会撞破"的残留是**两套口径并存**：
   `StringWidth` 的**等宽早退分支**仍用**字节长度**（而同函数的汉化主循环已换算成**字形数**），
   以及**顶点包 flush → GIF 发送**这条路上汉化改过的 5 个字节。
   据此出了 **3 张单变量可测盘**（§5），测试顺序与判定表见 §6。

**⇒ 本轮最重要的一句话给 Lead：请把 `probe-slot` 从"候选修复/探针"里**删除或标注为"基于误读、禁止使用"**，
否则下一位执行者会拿它去"修"一段本来就是对的代码。**

---

## 1. 素材与血统（自证）

| 项 | 值 | 来源 |
|---|---|---|
| 基底盘 | `work\builds\GR_REBUILD\GR_REBUILD2400.iso` | 只读 |
| 基底 sha256 | `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0` | `Get-FileHash` |
| 基底大小 | 1,648,164,864 B | 同上 |
| ELF | `SLUS_206.13` @ **LBA 295**，37,453,732 B | `lay_mkiso.py` 内 ISO9660 解析 |
| ELF sha256 | `5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8` | 与 K2 逐字节相同（`diff_A_vs_B.txt` 之外的 8 字节差） |
| PT_LOAD | `(va=0x100000, off=0x80, filesz=0x4DEC00, flags=7)` | `lay_dis.Elf` |
| A 线 vs B 线 | **8 字节**（`audit/diff_A_vs_B.txt`，与既有文档逐行相同） | 自算 |
| 汉化 vs 原盘 | **567 字**（`audit/classify_k2.txt` 首部逐区间列出） | 自算 |

A→B 的 8 个字节（复算确认，`audit/diff_A_vs_B.txt`）：

| VA | A 字 | B 字 | 语义 |
|---|---|---|---|
| `0x416EE8` | `2CA900B1` | `2CA900BA` | decode cave 前导上界 |
| `0x4170AC` | `240E003E` | `240E0040` | **ncol 62→64** |
| `0x4170E8` | `25AD0003` | `25AD0002` | row≥12 行位移 +3→+2 |
| `0x4170F8` | `25CD0002` | `25CD0003` | V0 偏移 2→3 |
| `0x4170FC` | `25CE0012` | `25CE0013` | V1 偏移 18→19 |
| `0x417160` | `2D0900B1` | `2D0900BA` | StringWidth cave 前导上界 |
| `0x41751C` | `2D4B00B1` | `2D4B00BA` | gate #3 |
| `0x5656A4` | `2D6C00B1` | `2D6C00BA` | gate #4 |

---

## 2. ★ U1 判定：`×94` 到底丢没丢（带指令证据）

### 2.1 直接证据（K2 ELF 上的原始字节，`audit/dis_k2_cw_cctc.txt`）

```
# CharWidth cave（0x416F40 起）
00416f8c  310900ff  andi  $t1, $t0, 0x00FF        ; t1 = lead
00416f90  2529ff5f  addiu $t1, $t1, -161          ; t1 = lead - 0xA1
00416f94  30aa00ff  andi  $t2, $a1, 0x00FF        ; t2 = trail
00416f98  254aff5f  addiu $t2, $t2, -161          ; t2 = trail - 0xA1
00416f9c  240e005e  addiu $t6, $zero, 94          ; 94
00416fa0  012e4018  >>> mult $t0, $t1, $t6 <<<    ; ★ R5900 三操作数：$t0 = $t1 * $t6
00416fa4  010a4021  addu  $t0, $t0, $t2           ; t0 += (trail - 0xA1)
00416fa8  250800e0  addiu $t0, $t0, 224           ; t0 += 0xE0

# GetGlyphUV cave（0x417050 起）
00417084  25adff5f  addiu $t5, $t5, -161          ; t5 = trail - 0xA1
00417088  240e005e  addiu $t6, $zero, 94
0041708c  018e6018  >>> mult $t4, $t4, $t6 <<<    ; ★ R5900 三操作数：$t4 = $t4 * 94
00417090  018d6021  addu  $t4, $t4, $t5           ; t4 += (trail - 0xA1)
00417094  258500e0  addiu $a1, $t4, 224           ; a1 = idx
```

**逐字段解码**（`0x012E4018`）：`op=0`，`rs=(w>>21)&31=9= $t1`，`rt=(w>>16)&31=14= $t6`，
**`rd=(w>>11)&31=8= $t0`**，`sa=0`，`funct=0x18`。
R5900 把 SPECIAL `funct 0x18` 定义成 **`MULT rd, rs, rt`**（结果低 32 位直接写 `rd`）。
**"丢了 `rd` 字段的两操作数读法"正是 `cave_dis.py` 第 94 行**：

```python
# work\tools\cave_dis.py:94
if fn == 0x18: return "mult $%s, $%s" % (r[rs], r[rt])     # ← rd 被丢弃
```

### 2.2 三条独立旁证

1. **写出侧就是三操作数**：`tools\hanliu\tools\patch_db2_elf.py`（cave 的原始生成器）
   第 46 行 `def mult3(self, rd, rs, rt): self._r(0,rs,rt,rd,0,0x18)`，第 137 行
   `a.mult3('t0','t0','t2')`，注释写着 `# EE 三操作数`。同一套编码在 `patch_db2b_elf.py` 第 61/141 行复现。
2. **同一代文档里已经写对过**：`docs\FONTRES_STRUCTURE_r83.md` 第 119 行
   `00416fa0 mult $t1, $t6  ; ★ R5900 三操作数 mult rd=t0 ⇒ t0 = (lead−0xA1)·94`。
   后出的 `REPORT_DISASM_ROOTCAUSE.md §2.3/§4#3` 把它读反了。
3. **同形态的"三操作数 + `mflo`"在同一段代码里出现过**，证明作者两种写法都会用：
   `0x4170B0 018e001a div $zero,$t4,$t6`（`rd=$zero` 主动丢弃商）+ `0x4170B4 00006812 mflo $t5`。
   若 `funct 0x18` 真是两操作数，作者不会在隔壁用 `mflo` 取商。

### 2.3 结论与后果

* **`idx = 0xE0 + (lead−0xA1)×94 + (trail−0xA1)`，slot = idx − 0xE0 = (lead−0xA1)×94 + (trail−0xA1)。**
  与 `docs\REPORT_atlas_artifact.md §3`（实机 0 误差命中 `x = 16×col`）**不矛盾** —— 那边本来就用了正确读法。
* `dfix_apply.py --set probe-slot` 的 6 个字**会破坏**这段算法：
  `0x417090` 本来是 `addu $t4,$t4,$t5`，该表要把 `0x41708C` 的 `mult` 当成两操作数、把 `0x417090` 换成 `mflo`、
  把 `0x417094` 与 `0x416FA8` 的 `+0xE0` 挪到 `+0x3F`。换完 `$t4` 会读到**上一次 `DIV` 的陈旧 `LO`**。
* **⇒ 建议 Lead：把 `probe-slot` 从站点表/文档里标注为"基于误读，禁止应用（GR_LAYOUT §2 已判定）"。**
  本任务不动 `GR_DISASM` 任何文件，只在这里登记。

---

## 3. 步进 / 几何一致性审计（A 的逐条结果）

### 3.1 A.1 残存旧几何常量普查（`addiu rd,zero,K`，`audit/classify_k2.txt`）

判据：**M** = 该 VA 落在"汉化相对原盘的改写字"里（用逐字 diff 得到 567 个改写字，再归并成区间）；
**O** = 原盘原码，汉化一字未动。

| K | 处数 | 其中 M | M 的 VA（全部） | 结论 |
|---|---|---|---|---|
| **62** | **20** | **0** | —（`0x3AA92C` 已不在：它就是 `0x4170AC`，ISO 偏移 `0x3AA92C`，A 线值 62、B 线 64） | ★ **20 处全部与原盘原码有关，与字库/图集/文本布局无关**；逐条见下 |
| 63 | 27 | 0 | — | 全部原码（含 `0x411AD0`，与 `0x411AC0`=62 / `0x411AE0`=64 组成同一段原码的常量簇） |
| **64** | **166** | **1** | `0x4170AC` | ★ `ncol` 在汉化改写区**只有一个装载点** |
| 12 | 335 | 1 | `0x4170D8` | UV cave 的 `row≥12` 阈值 |
| 16 | 444 | 6 | `0x416FBC`(CharWidth 越界返回宽)、`0x4170C4`/`0x4170EC`(格宽)、`0x41720C`、`0x417620`/`0x4176A0`(容量钳位 cave) | 全部是"格宽=16"，与盘上 `CW=CH=16` 一致 |
| 18 | 89 | 1 | `0x417688`（`0x417600(obj,18)` 的实参） | 与 `0x417600` 的 `min(a1,16)` 钳位配对 |
| 19 | 101 | 0 | — | 无 |
| 94 | 14 | 2 | `0x416F9C`、`0x417088` | ★ 两处都**只**喂给 R5900 三操作数 `mult`（§2） |
| 104 | 29 | 0 | — | `DrawLetters` 表行数，全部原码 |
| 224 | 27 | 0 | — | 单字节码位基数 0xE0；`0x416FA8`/`0x417094` 由 `addiu …,224` 实现（不在本普查的"零基址装载"口径内，另见 §3.2） |
| 512 / 640 | 19 / 28 | 0 | — | 历史图集高，全部原码 |
| **644** | **0** | 0 | — | ★ **ELF 里没有任何 `addiu rd,zero,644`**：h=644 只存在于 `COMMON.PAK` 头（数据侧），与预期一致 |
| 1024 / 1280 | 65 / 28 | 0 | — | 图集宽 / 顶点包容量，全部原码 |
| 1736 / 1872 / 2344 / 2350 / 2368 / 2432 / 329744 | 0 / 0 / 0 / 0 / 0 / 0 / 0 | 0 | — | ELF 里**不存在**这些"容量/几何登记值"的立即数 ⇒ 汉化确实把它们放在**数据侧**（图集/容器头），ELF 只认 4 个常量 |

**`addiu rd,zero,62` 的 20 处逐个结论**（`audit/classify_k2.txt` 的 `## K = 62` 段）：

| # | VA | 判定 |
|---|---|---|
| 1–2 | `0x129F2C`、`0x12A378` | O，原盘原码；不在任何文本/字库函数里（`0x12xxxx` = 场景/资源区） |
| 3–4 | `0x17E9E4`、`0x17EA40` | O，原码 |
| 5–10 | `0x2EF144/168/170/194/19C/1C0`、`0x2EFDB0`、`0x2EFE18`、`0x2F07D8` | O，原码；与 `0x2EF…` 段里的 3/12/16/63/64 是同一批"通用尺寸/枚举"常量 |
| 11 | `0x314A84` | O，原码 |
| 12 | `0x35ECA8` | O，原码 |
| 13 | `0x385C08` | O，原码 |
| 14 | `0x3E59B4` | O，原码 |
| 15 | `0x411AC0` | O，原码；★ 紧邻 `0x411AD0`(=63) / `0x411AE0`(=64)——这是一段**通用常量簇**，不是图集列数 |
| 16–20 | `0x542380`、`0x543B9C`、`0x543E88`、`0x544240`、`0x5443DC`、`0x544C10` | O，原码（`0x54xxxx` = 文本/字符串库区，但都是原盘的布局常量） |

⇒ **"gate 0xB1 时代有 27 处 62，只有 0x3AA92C 是网格"这条历史结论，方向是对的**：
本轮用逐字 diff 独立复算，得到 **20 处**（口径更严：只数"`addiu rd,zero,62`"且要求 `rs=$zero`；
历史 27 处很可能把 `ori/slti/andi` 或非零基址形态也计入），**没有一处落在汉化改写区**。
⇒ **改成 64 时"那 26 处是否都无关"的答案是：是，全部无关**（不是"看起来无关"，而是**它们的字节在汉化前后完全没变**，
而原盘靠这些字节 + 英文文本运行正常 ⇒ 它们不可能因为中文字库扩容而改变语义）。

### 3.2 A.2 槽 → 地址公式（逐条实读，`audit/sites_k2_readback.txt`）

| VA | 字 | R5900 语义 |
|---|---|---|
| `0x416F90` | `2529FF5F` | `t1 = lead − 0xA1` |
| `0x416F98` | `254AFF5F` | `t2 = trail − 0xA1` |
| `0x416F9C` | `240E005E` | `t6 = 94` = **PAIR_STRIDE（trail 空间 `0xA1..0xFE` 共 94 个）** |
| `0x416FA0` | `012E4018` | ★ `MULT rd=t0, rs=t1, rt=t6` ⇒ `t0 = (lead−0xA1)×94` |
| `0x416FA4` | `010A4021` | `t0 += (trail−0xA1)` |
| `0x416FA8` | `250800E0` | `t0 += 0xE0`（单字节码位基数 = 224） |
| `0x416FB0` | `8CC30044` | `v1 = count = [FD+0x44]` |
| `0x416FB4/B8/BC/C0` | `0103102B` / `14400003` / `24020010` / `1000001A` | `if (idx < count)` 读记录，否则**返回硬编码宽 16** |
| `0x416FC8..DC` | `8CC60038` … `90420001` | 记录基址 `[FD+0x38]`，**步长 10 字节**（`sll2 / addu / sll1`），`+1` = 字宽字节 |
| `0x41708C` | `018E6018` | ★ `MULT rd=t4, rs=t4, rt=t6` ⇒ `t4 = (lead−0xA1)×94`（同型，第二处） |
| `0x417094` | `258500E0` | `a1 = idx = t4 + 0xE0` |
| `0x4170A8` | `24ACFF20` | `t4 = idx − 224` = **slot**（网格回退路径） |

⇒ **没有任何一条路径丢掉 `×94`**；"哪条路径丢了"这一问的答案是"**一条都没有**，前提本身不成立"。

### 3.3 A.3 行/列换算：`ncol=64` 只改了一个立即数，其余换算跟着一致

`0x4170A8..0x417130` 全文（`audit/dis_k2_cw_cctc.txt`）：

```
004170a8  24acff20  addiu $t4, $a1, -224        ; t4 = slot
004170ac  240e0040  addiu $t6, $zero, 64        ; ★★ NCOL（唯一装载点）
004170b0  018e001a  div   $zero, $t4, $t6       ; R5900 三操作数，rd=$zero ⇒ 商进 LO
004170b4  00006812  mflo  $t5                   ; t5 = row = slot / NCOL
004170b8  01ae7018  mult  $t6, $t5, $t6         ; t6 = row * NCOL
004170bc  00007012  mflo  $t6
004170c0  018e6023  subu  $t4, $t4, $t6         ; t4 = col = slot - row*NCOL
004170c4  240f0010  addiu $t7, $zero, 16
004170c8  018f7018  mult  $t6, $t4, $t7         ; t6 = col * 16
004170cc  00007012  mflo  $t6
004170d0  25c50000  addiu $a1, $t6, 0           ; U0 = 16*col
004170d4  25cc0010  addiu $t4, $t6, 16          ; U1 = U0 + 16
004170d8  240f000c  addiu $t7, $zero, 12        ; 阈值
004170dc  01af782a  slt   $t7, $t5, $t7         ; row < 12 ?
004170e0  15e00002  bne   $t7, $zero, +2 -> 0x4170EC
004170e8  25ad0002  addiu $t5, $t5, 2           ; ★★ SKIP_ROWS（row>=12）
004170ec  240f0010  addiu $t7, $zero, 16
004170f0  01af7018  mult  $t6, $t5, $t7         ; t6 = row' * 16
004170f4  00007012  mflo  $t6
004170f8  25cd0003  addiu $t5, $t6, 3           ; ★★ V0
004170fc  25ce0013  addiu $t6, $t6, 19          ; ★★ V1
00417100..0x417130  4 个 (U0,V0,U1,V1) 转 float 写调用者给的 4 个栈格；jr $ra
00417134  8d4a0038  lw   $t2, 56($t2)           ; 记录路径基址 [FD+0x38]
00417138  08086b88  j    0x0021AE20            ; 回引擎原有记录读取（步长同为 10）
```

* **`div`/`mflo` 只有一个消费者**：`LO` 只被 `0x4170B4` 的 `mflo $t5` 取用；`0x4170B8` 处的三操作数 `mult`
  再算 `row×NCOL` 供取模，`0x4170C0` 得 `col`。**没有第二条 `div`/`mod` 站点**。
* `ncol` 的**第二个消费者不存在**：普查显示 `64` 在汉化改写区只出现 1 次（`0x4170AC`，§3.1）。
* 边界：`slot ∈ [0,2349]` ⇒ `row ∈ [0,36]`、`col ∈ [0,63]` ⇒ `U0 ≤ 1008`、`U1 ≤ 1024 = w` ✓；
  `row=36 ≥ 12` ⇒ 图集行 38 ⇒ `V0 = 16×38+3 = 611`、`V1 = 627 ≤ 644 = h` ✓。
* `0x417134` 的记录路径与 `0x21AE20` 的记录读取**共用同一套 `(u0,v0,u1,v1)` 字段与 10 字节步长**
  （cave 内 `sll2/addu/sll1` ↔ 引擎原文同构）⇒ **两条路共用同一 V1/rowShift 口径**（记录路径直接用记录里的值，
  网格路径用 `16×row' + Y0`；两条路的**采样窗高都是 16**）。

### 3.4 A.4 字形记录 / 矩形带（盘上回读，`audit/fontres_rebuild2400.txt`）

```
COMMON.PAK 记录: ('new_font_revised', psm=20(0x14 PSMT4), w=1024, h=644, clut=1040, px_size=329744, px@5229)
FONT.RES: 槽内 4421 B → 展开 5942 B（尾部指针 5664）

## face 'large'    fld[2]=0x20 fld[3]=0x20 fld[4]=32 fld[5]=7  ⇒ nrec = 224
   记录 224 条；非空 224；矩形并集 u∈[0,1024) v∈[0,643]
   前 6 个不同矩形 = (0,195,16,211) (0,211,16,227) (0,627,8,643) (8,627,16,643) (16,195,32,211) (16,211,32,227)
## face 'default'  同 large（nrec = 224）
## face 'huge'     fld[2]=0x34 fld[3]=0x2A fld[4]=16 fld[5]=6  ⇒ nrec = 96
   前 6 个不同矩形 = (0,627,8,643) (8,627,16,643) (16,627,24,643) …
```

**判读（逐条与 ELF 常量对齐）**

| 项 | 盘上读数 | ELF 常量 | 是否一致 |
|---|---|---|---|
| 图集 w×h | 1024×644 | `ncol=64` ⇒ `64×16 = 1024` ✓ | ✓ |
| 最高的采样窗 | `v1 = 643` | `V1_max = 16×(36+2)+19 = 627`（网格） | ✓（记录带可到 643，网格到 627，都在 h=644 内） |
| SKIP 让出的带 | ASCII 记录带 `y=195..211`、`211..227` | `row<12` ⇒ atlas 行 0..11 = y 3..195；`row≥12` ⇒ 从 atlas 行 14 = y 227 起 | ✓ **ASCII 带正好落在被跳过的 atlas 行 12/13** |
| 货架 | `y=611`(A) / `y=627`(B) | atlas 行 38 = `3+16×38 = 611`；行 39 = 627 | ✓ 与 `cap_build_k2.py` 的 `SHELF_A=(736,1024,611)` / `SHELF_B=(0,1024,627)` 逐字吻合 |
| 记录步长 | cave `sll2/addu/sll1` = **10 B**；`0x21AE20` 同构 | — | ✓ ★ **注意：`REPORT_DISASM_ROOTCAUSE.md §2.4` 写的"20 字节/条"是笔误** —— 同段引用的 `sll/addu/sll` 明明等于 ×10；`DrawLetters` 的表步长才是 20（不同表） |
| DBCS 记录分支 | `nrec = 224/224/96`，而 DBCS `idx = 224+slot ≥ 224` | `0x416FB4 sltu idx,count` | ✓ 恒走网格路径；**CharWidth 对 DBCS 恒返回硬编码 16**（= 格宽，自洽） |

---

## 4. ★ 不一致清单（按可能性排序）

| # | 不一致点 | VA / ISO | 现值 → 应为 | 为什么"只有中文数据规模才会撞破" | 如何验证 |
|---|---|---|---|---|---|
| **I1** | **`probe-slot` 的整套推导基于反汇编器丢失 `rd` 字段**（§2） | `0x416FA0`/`0x41708C` 等 6 处 | **无需改动**（现值即正确）；须把工具/文档里的 `probe-slot` 标为禁用 | 不撞破；但**一旦有人应用它**，所有对偶汉字的槽位会变成"上一次除法的陈旧 `LO`"，字形全乱 | `lay_census.py sites`（§3.2 表）+ `cave_dis.py:94` 一行即可复现假象 |
| **I2** | `StringWidth`(0x21AC00) 的**等宽字体早退分支**仍用**字节长度**，同函数的汉化主循环已改成**字形数** | `0x21AC3C lbu $v0,36($s3)` / `0x21AC48 lw $v0,12($s3)` / `0x21AC4C beq⇒0x21ACA4` / **`0x21AC50 mult $v0,$s0,$v0`** | 保留原字；用"字形数"口径（见盘 1） | `s0` = **字节长度**。中文串字节数 ≈ 2× 字形数 ⇒ 只要 `[font+0x24]!=0`（等宽标志），测宽 ≈ 2× 真值。作者显然撞过它：把 `0x1FF8D0`/`0x2071B4`/`0x21CB30` 的**实测宽度**硬换成 21/16/16（绕开而没修） | 盘 `LAY_fix1_bytecount`：本机 6000 帧与未修基底**逐帧 sha256 对照**。若完全相同 ⇒ `[font+0x24]` 在导航序列里恒 0 ⇒ 该路径当前不可达（也是结论） |
| **I3** | `AddOneWord` 的 4 条 flush 路径把 `jal 0x519AC0` 的发送参数 `a1` 由原盘 **1 改成 0** | `0x219FF4`/`0x21A0F8`/`0x21A1C4`/`0x21A2C4`（ISO `0x1AD874/978/A44/B44`） | `24050000` → `24050001` | 这三处直接坐在"顶点包 → GIF 发送"上；中文文本每帧顶点/包数远高于英文（同屏 glyph 数、图标码 `0xB1/0xB5` 迁移），更容易踩到 flush 的边界语义 ⇒ 与"写坏堆"同一现场 | 盘 `LAY_fix2_sendmode`：与基底逐帧对照 + 实机跑关卡 |
| **I3b** | 同一发送函数里的模式比较被 NOP | `0x519AC8`（ISO `0x4AD348`） | `00000000` → `10C30054`（`beq $a2,$v1,+84`） | 同 I3，成对改动之一；单独一盘便于二分 | 盘 `LAY_fix3_gifbranch` |
| **I4** | 排版里 `GetStringWidth()+1` 的 `+1` 被删 | `0x21CECC` | `00000000` → `24420001` | 与 I2 同族（"测量 vs 绘制"口径漂移）；中文串更长 ⇒ 累积差 1 px/串 | `LAY_fix4_layoutplus1.iso`（`--set layout_plus1`，本轮未跑冒烟的备选） |
| **I5** | 被 cave 夹在中间的**原有代码残片**：`0x417140 slti v0,a1,1024` / `0x417144 beq v0,zero,+10 → 0x417170`（**跳进 sw cave 中段**） | `0x417140..0x41714C`、`0x4171C8..0x4171FC` | 保持原样（当前**不可达**） | 现在没有入边（`audit/reach_4170.txt`：区间内入口点只有 `0x417050`/`0x417150`，`0x417140` **0 条**）；但只要将来往这个原始函数再加一个入口，就会以错误寄存器状态进入 cave 中段 | `lay_reach.py <elf> 0x417030 0x417200` |
| **I6** | （已澄清）20 处 `addiu rd,zero,62` 全部无关；`ncol` 只有 1 个装载点 | §3.1 / §3.3 | 无需改动 | — | `lay_classify.py` |
| **I7** | （已澄清）图集几何与盘上数据逐项自洽 | §3.4 | 无需改动 | — | `lay_fontres.py` |

**排序依据**：I1 是"错误结论会主动造成新破坏"（最高）；I2 是唯一**可静态证明的口径不一致残留**且已被作者用硬编码常量绕开；
I3/I3b 是唯一坐在"写坏堆"现场上的汉化字节；I5 是地雷（当前不响）。

---

## 5. 本批可测盘（3 张，全部单变量；`work\builds\GR_LAYOUT\`）

基底 = `GR_REBUILD2400.iso` **的副本**（`lay_mkiso.py` 内 `copyfile` 整盘复制后再改字节），
基底 sha256 = `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0`（1,648,164,864 B）。

| 盘 | 站点（VA / ISO / 现字→新字） | sha256 | 尺寸 |
|---|---|---|---|
| **`LAY_fix1_bytecount.iso`**<br>（I2：关掉"字节长度 × 固定宽"早退，改走已换算成字形数的循环） | `0x0021AC40` / `0x001AE4C0` / `10400004 → 10000004`（`beq $v0,$zero,+4` → `beq $zero,$zero,+4`）**共 1 处 1 字节** | `a69a9ca44049eaed4085239a2b8d10af58888f54f62a51e40c1ece22dd2d2808` | 1,648,164,864 B |
| **`LAY_fix2_sendmode.iso`**<br>（I3：恢复 4 条 flush 的 GIF 发送参数） | `0x00219FF4` / `0x001AD874`；`0x0021A0F8` / `0x001AD978`；`0x0021A1C4` / `0x001ADA44`；`0x0021A2C4` / `0x001ADB44` —— 全部 `24050000 → 24050001`（`addiu $a1,$zero,0 → …,1`）**共 4 处 4 字节** | `d51dd5a79c6993411ea8ef5691261faf8e045328d756042d6ef6cfdd02ace6fe` | 1,648,164,864 B |
| **`LAY_fix3_gifbranch.iso`**<br>（I3b：恢复发送函数里的模式比较） | `0x00519AC8` / `0x004AD348` / `00000000 → 10C30054`（`beq $a2,$v1,+84`）**共 1 处 3 字节** | `8bdf5007163d11f10b7aa5405eb50eae3b0622acef7e5367a6a0c905a82a0c97` | 1,648,164,864 B |

每张盘同目录有 `<盘名>.meta.json`（逐站点 VA/ISO/原字/新字/diff_runs/sha256/尺寸/自证）。
**三张盘的自证全部通过**（`lay_mkiso.py` 输出）：

```
size_unchanged        OK (1648164864 B)
diff_only_in_windows  OK
every_window_touched  OK
readback_all_ok       OK
gates/geom/core 未动   OK（16 处：4 闸门 + 4 图集几何 + 4×94/×94/+0xE0 核心站点）
产物 ELF sha256       fix1 0a986bb3… / fix2 25e839a1… / fix3 2d4bd562…
```

* **没有动** `GR_REBUILD` / `GR_DFIX` / `GR_DISASM` / `third_party` 里任何文件；也没有删任何既有产物。
* 第 4 张盘（I4 `layout_plus1`）**已实现但未出盘**：`--set layout_plus1` 可随时补一张，避免与 I2 混成一个变量。

---

## 6. 本机冒烟（6000 帧 / 模拟器独占 / 逐帧 sha256 对照）

口径与 `DFIX_REPORT.md` 完全一致（同一 `cap_run.py` + 同一 `nav_menu_only.txt` + 同一判据）；
脚本 `work\builds\GR_LAYOUT\tools\smoke_lay.ps1`（**轮询零 pcsx2、只等不杀、记录污染**），
日志 `work\builds\GR_LAYOUT\audit\smoke_serial.log`，逐盘读数 `audit/results_*.txt`，对照 `audit/results_cmp_vs_base.txt`。

**实际读数（2026-10-17 20:19:27 → 20:26:28，全程独占，起跑前 `pcsx2` 进程 = 0，跑后残留 = 0）**

| 盘 | 截图 | 去重画面 | `TLB Miss` | `Trap exception` | cdvd 事件 | maxLBA | 耗时 | 跑后残留进程 |
|---|---|---|---|---|---|---|---|---|
| `base`（未修对照） | **191** | 163 | **0** | **0** | 60420 | 804765 | 103 s | 无 ✓ |
| `LAY_fix1_bytecount` | **191** | 163 | **0** | **0** | 60420 | 804765 | 103 s | 无 ✓ |
| `LAY_fix2_sendmode` | **191** | 163 | **0** | **0** | 60420 | 804765 | 106 s | 无 ✓ |
| `LAY_fix3_gifbranch` | **191** | 163 | **0** | **0** | 60420 | 804765 | 106 s | 无 ✓ |

**逐帧 sha256 对照（与同一基底未修盘 `base`，同帧号 PNG 逐字节比较）**

```
[cmp] fix1_bytecount vs 对照 base : 同名可比 191 张 ; 逐字节相同 191 (100.0%) ; 不同 0 张 []
[cmp] fix2_sendmode  vs 对照 base : 同名可比 191 张 ; 逐字节相同 191 (100.0%) ; 不同 0 张 []
[cmp] fix3_gifbranch vs 对照 base : 同名可比 191 张 ; 逐字节相同 191 (100.0%) ; 不同 0 张 []
```

* **不同帧数 = 0（三张盘全部）** —— 这是**预期读数**（本机导航脚本走不到根因：无火箭筒 / L1 / 队列选择 / 长文本，
  见 `DFIX_REPORT.md §B.7`），**不是**"补丁无效"的证据。**没有任何一张盘出现"不同帧数 ≠ 0"**，
  所以不存在"补丁在本机就改变了渲染"的意外（若有，那本身就是线索）。
* 交叉验证：`base` 这一轮与 `GR_DFIX` 的 `base` 轮、以及重建执行者验收过的 `dump_final`
  都是 **191 张 / 163 画面 / TLB 0 / Trap 0**，口径完全一致。
* 三张盘的 `emulog.txt` 行数同为 12046；`TLB Miss` = 0、`Trap exception` = 0；
  文件字节数的微小差异（1,113,553 / 1,117,113 / 1,117,511 B）全部落在 host 路径与时间戳上，
  与 `DFIX_REPORT.md §B.5` 的"日志侧无游戏侧新料"结论一致。
* ⇒ **本机 6000 帧这条路无法区分三张盘**；决定权在用户的实机按 §7 的顺序测。

---

## 7. ★ 给用户的测试顺序与判定表

> **前提**：先跑 **`LAY_fix1_bytecount.iso`**，再跑 `LAY_fix2_sendmode.iso`，最后 `LAY_fix3_gifbranch.iso`。
> 每张都**单独**测（不要一次只换一张以外的任何东西）；每张至少走到出现卡死的那一步（火箭筒 / L1 / 队列选择 / 长文本）。

| 盘 | **不卡了**意味着什么 | **仍卡**意味着什么 | 下一步 |
|---|---|---|---|
| **`LAY_fix1_bytecount.iso`** | `StringWidth` 的"字节 vs 字形"口径不一致**就是**触发物（或它与别的因素串联）⇒ 把"字形数口径"正式补进 `StringWidth`（含 `0x21ACD0` 的等宽早退），再验一次 | 该路径在这条流程里没被走到（很可能 `[font+0x24]` 恒 0）⇒ **I2 降级为"未触发"**，重点转到 I3/I3b | 跑盘 2 |
| **`LAY_fix2_sendmode.iso`** | 顶点包 flush 的**发送参数**是触发物（I3 成立）⇒ 下一步做"只恢复 `a1` 与只恢复分支"的 2×2 二分，并复查 `0x519AC0` 的三个调用者 | 发送参数不是触发物 ⇒ I3 降级；**若出现撕裂/丢字/闪烁，立刻回滚本盘**（说明 `a1=1` 是刻意禁用的） | 跑盘 3 |
| **`LAY_fix3_gifbranch.iso`** | 发送函数里的**模式比较**是触发物（I3b 成立）⇒ 与盘 2 结果合并判定 | I3 整族都不是触发物 ⇒ **§4 的四条候选全部落空**，转 §8 的兜底方案 | 见 §8 |

**读盘口径（每张都一样）**：
1. **崩溃/挂起**：是否出现 `TLB Miss`（PCSX2 日志）/ 画面冻结 / `Trap exception`；
2. **画面**：HUD/菜单汉字是否**新出现乱字、缺字、撕裂、错位**（任何一项出现 ⇒ **立即回滚该盘**并回报截图）；
3. **帧率**：爆炸瞬间是否仍有 2fps 塌方；
4. **存档**：进关卡后存一次档再读回（`CVAR_04` 那条链上的存档也是已知易崩点）。

---

## 8. 若全部仍卡 ⇒ 我建议的下一步（含需要用户提供什么）

**§4 的候选都不成立时，"布局/步进"这条线在本机静态层面就走到头了**，因为：
* U1 已闭环（`×94` 没丢）；
* 图集几何 ↔ 盘上数据逐项自洽（§3.3/§3.4）；
* 唯一"两套口径并存"的点（I2）已经出盘可测。

⇒ 下一步我建议**把"静态猜"换成"抓现场"**，需要用户提供三样东西（按价值排序）：

1. **★ 卡死前 30 秒的即时存档（`.p2s`）** —— 这是最高价值的一项：
   有了它，模拟器可以**跳过 7 分钟的导航**直接复现，且可以用「读档→逐帧单步」把崩溃前最后几百帧的
   `fontmgr+0x44`（主包计数）/`fontmgr+0x48`（复位闸门）/`fontmgr+0x68`（副包计数）与堆头**逐帧打表**，
   直接看到"写入下标越界"的那一帧。**最好同时给"英文盘跑到同一位置的存档"作对照**。
   取法：`PCSX2 → 系统 → 即时存档 → 存到槽 1`，然后把
   `%LOCALAPPDATA%\PCSX2\sstates\SLUS-20613 (7A361FB5).01.p2s`（或当前 CRC 对应的文件）复制出来给我。
2. **卡死时的 PCSX2 完整日志 `emulog.txt`**（用户自己那次会话的，不是本机冒烟的）——
   我要的是 `TLB Miss` 的**行数与首次时刻**、以及它前后 200 行。现有 `DFIX_pkt` 日志只有本机口径。
3. **一句话的复现步骤**：从"读档/开机"到"卡住"按了什么键、在哪个界面。
   本机的 `nav_menu_only.txt` **走不到中文主菜单**（`DFIX_REPORT.md §B.7`），
   所以实机那一步只能靠用户描述。

**我这边（不需要用户）还能做的静态工作**（若 Lead 要我继续）：
* 定位写 `[FD+0x44]`（FONT.RES 记录条数）的加载器，把"`count = nrec = 224`"从强推断变成闭环（**未达成 U-L2**）；
* 用 Ghidra（`work\tools\ghidra`，项目 `GRLocEE.gpr` 已在）恢复 `RSFontMgr` 类，查 `+0x44/+0x48/+0x68/+0x28/+0x4C` 的真实容量与 `[font+0x24]/[font+0x10]/[font+0xC]` 的语义（用于判定 I2 是否可达）。

---

## 9. 未达成项（如实列出）

| # | 未达成 | 已做到哪一步 | 缺什么 |
|---|---|---|---|
| **U-L1** | 没有实机验证任何一张盘 | 三张盘全部做出、自证通过、本机 6000 帧冒烟（§6） | 用户按 §7 的表格测 |
| **U-L2** | 没定位写 `[FD+0x44]`（FONT.RES `count`）的加载器 | 从盘上回读确认三个面的 `nrec = 224/224/96`、记录步长 10 B | 需要在 ELF 里找到读 `FONT.RES` 的函数（可搜 `nrec*10+0x10` 的分配模式），或用 Ghidra |
| **U-L3** | 不知道 `[font+0x24]`（等宽标志）在实机何时非 0 | 找到三个消费者：`0x21AC3C`（StringWidth 早退）、`0x21ACD8`（`0x21ACD0` 单字宽早退）、`0x21CA54 lbu $v1,264($a0)` 家族 | 需要运行时打表（有了 §8 的存档就能做） |
| **U-L4** | `0x519AC0` 的 `a1` 语义没追到底 | 定位：`lbu $a2,33($a0)` 与 `andi $v1,$a1,0xFF` 相等则跳 `0x519C1C`；汉化把 `a1` 改 0 并把该比较 NOP | 需要反汇编 `0x519AC0..0x519D00` 并追 `+84` 目标的语义（本任务范围外） |
| **U-L5** | `0x417140` 残片"若被进入会怎样"没有实证 | 静态证明**当前 0 条入边**（`audit/reach_4170.txt`） | 无需（登记为地雷即可） |
| **U-L6** | 本机冒烟**不触发根因** | 与 `DFIX_REPORT.md §B.3` 同口径：191 张截图 / 163 去重画面 / TLB 0 / Trap 0 | 需要一条能走到"卡死那一步"的导航脚本（§8 第 1、3 项） |

---

## 10. 复现命令（每条结论都能重跑）

```powershell
cd <repo root>

# 0) 磁盘（当前余量不大，本批 3 张盘）
Get-PSDrive C

# 1) U1：正确的 R5900 反汇编（三操作数 mult/div 会带 ★ 标注）
python work\builds\GR_LAYOUT\tools\lay_dis.py work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf `
  dis 0x416f40 0x417038 0x417050 0x417140        # CharWidth cave + GetGlyphUV cave

# 2) A.1 常量普查 + 逐站点"汉化改写(M)/原盘原码(O)"分类
python work\builds\GR_LAYOUT\tools\lay_census.py census work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf -o $env:TEMP\census.txt
python work\builds\GR_LAYOUT\tools\lay_classify.py `
  third_party\orig\ps2\slus_out\SLUS_206.13 work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf -o $env:TEMP\classify.txt

# 3) 站点逐条实读（§3.2/§3.3 的表就是它的输出）
python work\builds\GR_LAYOUT\tools\lay_census.py sites work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf

# 4) A.4 盘上 FONT.RES / COMMON.PAK 回读
python work\builds\GR_LAYOUT\tools\lay_fontres.py work\builds\GR_REBUILD\GR_REBUILD2400.iso

# 5) cave 的入边/地雷（I5）
python work\builds\GR_LAYOUT\tools\lay_reach.py work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf 0x417030 0x417200

# 6) 出盘（基底只读；自证不合格会返回 1）
python work\builds\GR_LAYOUT\tools\lay_mkiso.py --base work\builds\GR_REBUILD\GR_REBUILD2400.iso `
  --out work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso --set strwidth_mono --tag LAY_fix1_bytecount
#   其它：--set sendmode / --set gifbranch / --set layout_plus1

# 7) 串行冒烟（轮询零 pcsx2、只等不杀）+ 逐帧 sha256 对照（base 放最后＝对照基准）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_LAYOUT\tools\smoke_lay.ps1
```

**偏移换算**（由 PT_LOAD `off=0x80 / va=0x100000`、ELF @LBA 295 推出，工具内自检）：
`ELF 文件偏移 = VA − 0xFFF80`；`ISO 偏移 = 0x93800 + ELF 文件偏移 = VA − 0x6C780`
（例：`0x21A040 → ISO 0x1AD8C0`；`0x21AC40 → ISO 0x1AE4C0`）。
