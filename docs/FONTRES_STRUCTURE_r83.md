# R83-① FONT.RES **权威结构**（反汇编实证，round83）

> 作者：执行任务（round83）。全部结论都有**ELF 反汇编原文**或**盘上回读**作证据，逐条给出行号/VA。
> 反汇编工具：`work/tools/cave_dis.py`（standalone R5900 反汇编器，输入 `work/builds/GR_ZH98/temp/r72/SLUS_206.13.elf`）
> 原始转储：`work/builds/GR_ZH98/temp/r83/{struct.txt,free.txt,budget.txt,cave_A.txt,cave_B.txt,glyph_uv_fn.txt,addoneword.txt,drawstring.txt,readres.txt}`
> 可复跑：`python work/tools/zx_r83_struct.py`（结构）、`zx_r83_free.py`（占用）、`zx_r83_budget.py`（容量）

---

## 0. 一句话结论（先把 Lead 的两条待确认项结掉）

| Lead 的问题 | 答案 | 证据 |
|---|---|---|
| `b0`/`b1` 是什么？ | **`b1` = 该字形的"步进宽度（像素，整数）"**；`b0` 在现役盘 544 条记录里**恒为 0**，未被任何代码读取 | §2.3 `lbu $v0, 1($v0)` → `(float)` → 乘缩放 |
| 一个新码如何映射到某条记录？ | **单字节码 `c` → `记录索引 = c − face[+0x20]`（`face[+0x20] = 0x20`）**；**对偶码 → `索引 = (lead−0xA1)·94 + (trail−0xA1) + 0xE0`** | §2.2 / §2.3 反汇编 |
| 记录能否指向任意矩形？ | **能**。记录的 4 个 u16 被**原样**当作纹理坐标用（无任何再加偏移） | §2.4 |
| 「记录分支恒假」要不要改代码？ | **不用改代码。** 判据是 `idx < nrec`，`nrec = fld[4]×fld[5]` 是**纯数据**、`__nwa(nrec*10+0x10)` 动态分配、**索引无 8 位掩码**（见 §2.5） | §2.2/§2.5 |
| 图集高度 `h` 上限 | 本轮**未做** h 实验（任务书禁令）。但 §3 指出"h 是唯一变量"这个结论**证据不足** | §3 |

---

## 1. 容器/资源的两层结构

### 1.1 `MENU.IMG` 里的两个条目（盘上回读，`r83/struct.txt` [A]/[C]）

```
#3 COMMON.PAK  off=0x57400   stored=400659  real=400659
#4 FONT.RES    off=0xB9120   stored=4421    real=7222
```

### 1.2 `COMMON.PAK` = 4 条记录链（`<u32 type><u32 nameLen><name><u32 psm><u32 w><u32 h><u32 clut>`
`<clut 字节><u32 px_size><px 字节>`，`type=0x63` 为结束哨兵）

| rec | @PAK 偏移 | 名字 | psm | w×h | clut | px_size | px@ | end |
|---|---|---|---|---|---|---|---|---|
| 0 | 0x0 | `arrow` | 0x00 | 32×32 | 0 | 4,112 | 0x21 | 0x1031 |
| **1** | **0x1031** | **`new_font_revised`** | **0x14 (PSMT4)** | **1024×512** | **1,040** | **0x40010 = 262,160** | **0x146D** | **0x4147D** |
| 2 | 0x4147D | `pda-lcd-02` | 0x13 (PSMT8) | 256×256 | 1,040 | 0x10010 | 0x418B3 | 0x518C3 |
| 3 | 0x518C3 | `pda_counterparts` | 0x13 (PSMT8) | 256×256 | 1,040 | 0x10010 | 0x51CFF | 0x61D0F |

记录链结束 `0x61D0F`，PAK 长 400,659 ⇒ **尾料 4 B**。

### 1.3 像素容器（`new_font_revised`）的实际形状

```
px_size = 262,160 = 262,144 (纹理) + 16 (尾部 GIFTAG)
262,144 = 8 段 × 48 B 前缀 + 261,760 B 段数据      ← ★ 逐字节对得上
段: seg0..seg6 各 48 B 前缀 + 32,768 B (64 行)；seg7 48 B 前缀 + 32,384 B (63.25 行)
末尾另有 48 B 前缀落在 0x3FFE0（其最后 16 B 就是尾部 GIFTAG）
每段前缀 = [PT 16B][A+D TRXPOS 16B][IMAGE tag 16B]，TRXPOS 低 u32 里的 SSAY = 段首行
```

---

## 2. ★ 码 → 记录的完整链路（反汇编实证）

### 2.1 三个相关函数

| 函数 | VA | 作用 |
|---|---|---|
| `RSFontMgr::DrawString`（第 3 重载） | 0x219A70 起 | 逐字符循环：解码 → 取宽度 → 取 UV → `AddOneWord` |
| `CharWidth`（原 0x21AD10，汉化后跳 cave） | 入口 0x21AD10 → `j 0x416F40` | 返回该码的步进宽度（float） |
| `GetGlyphUV`（原 0x21ADE0，汉化后跳 cave） | 入口 0x21ADE0 → `j 0x417050` | 输出该码的 (U0,V0,U1,V1) 四个 float |
| `AddOneWord` | 0x219F50 | 把 (x, UV) 交给 sprite 虚函数 |

调用点（`r83/drawstring.txt` L86–L114）：
```
0x219BC4  addu $v0, $s6, $s0        ; v0 = str + i
0x219BC8  lb   $a1, 0($v0)          ; 取 1 字节
0x219BCC  jal  0x00416ED0           ; ★ 解码 cave: 往 sp+0xDE 写 u16 码, 返回长度 1/2
0x219BD0  addiu $a0, $sp, 0xDE
0x219BD4  lhu  $a1, 222($sp)        ; a1 = u16 码
0x219BD8  jal  0x0021AD10           ; CharWidth(码) → v0  (float 步进宽)
...
0x219C30  jal  0x0021ADE0           ; GetGlyphUV(码, &u0,&v0,&u1,&v1)
...
0x219D54  jal  0x00219F50           ; AddOneWord(font, &x, &uv, ...)
```

**解码 cave 0x416ED0（`r83/cave_A.txt` L1–L28）** —— 决定"哪些字节是单字节码、哪些是 lead"：
```
00416ed0  andi  $a1, $a1, 0x00FF
00416ed4  sh    $a1, 0($a0)          ; 先把 byte 当 u16 码写出去
00416ed8  addiu $v0, $zero, 1        ; 默认长度 1 = 单字节
00416edc  sltiu $t1, $a1, 0x00A1
00416ee0  bne   $t1, $zero, 0x416F34 ; < 0xA1 ⇒ 单字节
00416ee8  sltiu $t1, $a1, 0x00B1     ; ★★ 真 gate（现役盘 = 0xB1）
00416eec  beq   $t1, $zero, 0x416F34 ; ≥ 0xB1 ⇒ 单字节
00416ef4..0x416F1C  边界检查 + trail 检查 0xA1 ≤ trail < 0xFF
00416f24  sll   $t4, $a1, 8
00416f28  or    $t4, $t4, $t3        ; t4 = (lead<<8)|trail
00416f2c  sh    $t4, 0($a0)
00416f30  addiu $v0, $zero, 2        ; 长度 2 = 对偶
00416f34  sb    $v0, -1($a0)         ; 长度写到 out[-1]
```
⇒ **判定规则**：`0xA1 ≤ byte < gate` ⇒ 对偶（吃下一字节当 trail，且要求 `0xA1 ≤ trail < 0xFF`）；否则单字节。
⇒ 单字节码的取值范围 = `0x00..0xA0` ∪ `[gate, 0xFF]`。

### 2.2 `CharWidth` 的汉化版 cave（0x416F40 起，`r83/cave_A.txt` L29–L90）

```
00416f40  srl   $t0, $a1, 8          ; t0 = 码 >> 8（lead 字节）
00416f44  bne   $t0, $zero, 0x416F8C ; lead != 0 ⇒ 对偶分支
--- 单字节分支 ---
00416f4c  andi  $t3, $a1, 0x00FF     ; t3 = 码
00416f50  addiu $t1, $zero, 32       ; ' ' 特判 ⇒ 返回 a0[+0x14]
00416f5c  addiu $t1, $zero, 0xB5     ; ★ 0xB5 特判 ⇒ 返回 20
00416f68  addiu $t1, $zero, 0xB1     ; ★ 0xB1 特判 ⇒ 返回 20
00416f74  lw    $a2, 40($a0)         ; a2 = face   (font+0x28)
00416f78  lb    $v1, 32($a2)         ; v1 = (s8)face[+0x20]  ← ★ 码基址
00416f7c  subu  $t0, $t3, $v1
00416f80  andi  $t0, $t0, 0x00FF     ; t0 = (码 − face[+0x20]) & 0xFF   ← ★★ 记录索引
--- 对偶分支 ---
00416f8c  andi  $t1, $t0, 0x00FF     ; lead
00416f90  addiu $t1, $t1, -161       ; lead − 0xA1
00416f94  andi  $t2, $a1, 0x00FF     ; trail
00416f98  addiu $t2, $t2, -161       ; trail − 0xA1
00416f9c  addiu $t6, $zero, 94
00416fa0  mult  $t1, $t6             ; ★ R5900 三操作数 mult rd=t0 ⇒ t0 = (lead−0xA1)·94
00416fa4  addu  $t0, $t0, $t2        ; t0 = slot = (lead−0xA1)·94 + (trail−0xA1)
00416fa8  addiu $t0, $t0, 224        ; ★★ t0 = 记录索引 = slot + 0xE0
--- 公共 ---
00416fac  lw    $a2, 40($a0)
00416fb0  lw    $v1, 68($a2)         ; v1 = face[+0x44]  ← ★★ nrec
00416fb4  sltu  $v0, $t0, $v1        ; ★★★ 判据: 索引 < nrec ?
00416fb8  bne   $v0, $zero, 0x416FC8 ; 是 ⇒ 走记录
00416fbc  addiu $v0, $zero, 16       ; 否 ⇒ 宽度 = 16（对偶分支）
--- 单字节分支的越界回落 ---
00417000  lw    $v1, 68($a2)
00417004  sltu  $v0, $t0, $v1
00417008  bne   $v0, $zero, 0x416FC8
00417010  addiu $t0, $zero, 0        ; ★ 越界 ⇒ 索引归 0（用 record[0]）
--- 取记录 ---
00416fc8  lw    $a2, 56($a2)         ; a2 = face[+0x38] = 记录数组基址
00416fcc  sll   $v0, $t0, 2
00416fd0  addu  $v0, $v0, $t0
00416fd4  sll   $v0, $v0, 1          ; v0 = 索引 × 10
00416fd8  addu  $v0, $v0, $a2        ; rec = base + 索引×10
00416fdc  lbu   $v0, 1($v0)          ; ★★★ v0 = rec->b1  ⇒ **b1 = 步进宽度**
00416fe0  mtc1/cvt.s.w/mul.s ...     ; × a0[+0x1C] 缩放后返回
```

### 2.3 `GetGlyphUV` 的汉化版 cave（0x417050 起，`r83/cave_B.txt` L7–L66）

```
00417050  lw    $t2, 40($a0)         ; face
00417054  andi  $v1, $a1, 0x00FF     ; trail
00417058  srl   $t4, $a1, 8          ; lead
0041705c  bne   $t4, $zero, 0x417078
00417064  lb    $a1, 32($t2)         ; face[+0x20]
00417068  subu  $v1, $v1, $a1
0041706c  andi  $a1, $v1, 0x00FF     ; a1 = 索引 = 码 − face[+0x20]
00417078..0x417094  对偶: a1 = ((lead−0xA1)·94 + (trail−0xA1)) + 0xE0
00417098  lw    $v1, 68($t2)         ; nrec
0041709c  sltu  $v0, $a1, $v1
004170a0  bne   $v0, $zero, 0x417134 ; ★ 索引 < nrec ⇒ 记录分支
--- 网格公式分支 ---
004170a8  addiu $t4, $a1, -224       ; slot = 索引 − 224
004170ac  addiu $t6, $zero, 62
004170b0  div   $t4, $t6   ; mflo $t5 = row = slot/62 ; subu = col = slot%62
004170c4  addiu $t7, $zero, 16
004170c8  mult  $t4, $t7   ; mflo = col*16
004170d0  addiu $a1, $t6, 0           ; U0 = 16·col
004170d4  addiu $t4, $t6, 16          ; U1 = 16·col + 16
004170d8  addiu $t7, $zero, 12
004170dc  slt   $t7, $t5, $t7
004170e0  bne   $t7, $zero, 0x4170EC
004170e8  addiu $t5, $t5, 3           ; ★ row ≥ 12 ⇒ row += 3（空出 3 行放记录带）
004170ec  addiu $t7, $zero, 16
004170f0  mult  $t5, $t7     ; mflo = row*16
004170f8  addiu $t5, $t6, 2           ; V0 = 16·row + 2
004170fc  addiu $t6, $t6, 18          ; V1 = 16·row + 18
00417100..0x41712C  四个 (int→float) 存到 a2/a3/t0/t1
--- 记录分支 ---
00417134  lw    $t2, 56($t2)          ; 记录数组基址
00417138  j     0x0021AE20            ; ★ 跳回原函数体（注意：跳过 0x21AE1C 的 andi）
```

**记录分支的消费者 0x21AE18–0x21AF24（`r83/…side_0021ADD0_0021AF30.txt` 与 ELF 实读）**：
```
0021AE20  sll   $v1, $a1, 2
0021AE24  addu  $v1, $v1, $a1
0021AE28  sll   $v1, $v1, 1          ; v1 = 索引×10   ← ★ 索引**没有** &0xFF
0021AE2C  addu  $a1, $v1, $t2        ; rec = base + 索引×10
0021AE30  lhu   $a1, 2($a1)          ; rec+2 = u0
0021AE70  lhu   $a1, 4($a1)          ; rec+4 = v0
0021AEB0  lhu   $a1, 6($a1)          ; rec+6 = u1
0021AEF0  lhu   $v1, 8($v1)          ; rec+8 = v1
         （每个值经 u16→float 惯用法, 因为 lhu 零扩展 ⇒ bltz 分支永不触发 ⇒ **原样使用**）
0021AF20  jr    $ra / swc1 $f0, 0($t1)
```

### 2.4 ⇒ 权威结论

```
① 记录 = **10 字节** `<BB4H>` = {u8 b0, u8 b1, u16 u0, u16 v0, u16 u1, u16 v1}
   单位 = 图集 texel，**绝对坐标**，被引擎**原样**当 UV 用。
   · b1 = 步进宽度（像素，整数）
   · b0 = 现役 544 条记录里恒 0；两个消费点（0x416FDC / 0x21AE20 路径）都**不读 b0**
   · 头部 0x21AF2C 的两条 `jr $ra`+`swc1` 之外无其它字段

② 码 → 记录索引
   · 单字节码 c  :  idx = (c & 0xFF) − face[+0x20]        （face[+0x20] = 0x20 ⇒ idx = c − 0x20）
   · 对偶码 (L,T):  idx = (L−0xA1)·94 + (T−0xA1) + 0xE0   （= slot + 224）
   · 判据        :  idx < face[+0x44]（= nrec = fld[4]×fld[5]）⇒ 用记录；否则用网格公式
   · 网格分支的 slot = idx − 224 ⇒ **对偶码的网格槽号恒等于自然槽号 slot**
   · 单字节码分支越界（idx ≥ nrec，只可能发生在 c < 0x20 时回绕）⇒ idx 归 0，用 record[0]

③ 现役盘 nrec = 224/224/96
   ⇒ 单字节码 c ∈ 0x20..0xFF ⇒ idx = 0..223 **恒 < 224 ⇒ 单字节码永远走记录表** ✓
   ⇒ 对偶码 idx = slot + 224 ≥ 224 **恒 ≥ 224 ⇒ 对偶码永远走网格公式** ✓
   （Lead 说的"恒假谓词"就是这一条；**它只是 nrec=224 的数值后果，不是代码缺陷**）

④ ★ 把 nrec 抬到 224+K 即可让"自然槽号 < K"的对偶码改走记录表
   —— 而 idx 无 8 位掩码（cave 的 `j 0x21AE20` 跳过了 0x21AE1C 的 `andi $a1,$a1,0xFF`），
      `__nwa(nrec*10+0x10)` 动态分配 ⇒ **ELF 侧零常量、纯数据驱动** ✓
```

### 2.5 三处"曾以为是坑"的澄清

| 说法 | 实情 |
|---|---|
| "记录数必须改 ELF" | ✗ 纯数据：`RSFontMgr::ReadResourceFile` 里 `iVar6 = fld[4]*fld[5]`、`__nwa(iVar6*10+0x10)`（`docs/REPORT_font_content_logic_split.md` L26–L28 已证，本轮复核一致） |
| "索引被 `&0xFF` 截断 ⇒ 记录上限 256" | ✗ **不成立**。`andi $a1,$a1,0xFF` 在 0x21AE1C，而 cave 用 `j 0x21AE20` 跳过它 |
| "记录矩形到采样窗有 +4/+2 偏置（`GLYPH_DU/DV`）" | ⚠ **对记录分支不成立**：记录分支把 (u0,v0,u1,v1) 原样输出。**网格分支**自己是 `U0=16·col, V0=16·row+2`（`+2` 写在公式里）。`tools/text_csv/tcslib.py` 的 `GLYPH_DU/DV=4/2` 是**字形覆盖体检用的容差窗**，不是采样几何。盘上像素与它一致只是因为历史补丁按同一张配方单写过 |

### 2.6 面描述块（face descriptor）字段

展开态布局（`r83/struct.txt` [C]，逐字节回读）：
```
[u32 20][20 B "new_font_revised.rsb"][u32 nfaces=3]
for each face: [u32 nameLen][name][14 × u32 fld][nrec × 10 B 记录]
其后 278 B = 「风格块」序列
```

| face | @fld | 记录 @ | nrec | fld[0] | fld[1] | fld[2] | fld[3] | fld[4] | fld[5] | fld[7] | fld[8] | fld[9] | fld[12] | fld[13] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `large` | 0x0025 | 0x005D..0x091D | 32×7=224 | 10 | 26 | 32 | 32 | 32 | 7 | 0 | 512 | 512 | 32 | 26 |
| `default` | 0x0928 | 0x0960..0x1220 | 32×7=224 | 10 | 26 | 32 | 32 | 32 | 7 | 208 | 512 | 512 | 32 | 26 |
| `huge` | 0x1228 | 0x1260..0x1620 | 16×6=96 | 10 | 16 | 52 | 42 | 16 | 6 | 416 | 512 | 512 | 32 | 42 |

**实证到的语义**（来自反汇编，未实证的一律标"未定"）：
- `fld[4] × fld[5]` = **nrec**（唯一定义式，`ReadResourceFile`）
- 面结构体（堆对象，非文件布局）实测偏移：`face+0x20` = 码基址（`lb`，=0x20）；`face+0x38` = 记录数组指针；`face+0x44` = nrec；`face+0x28` 被 `DrawString` 当"当前 face"指针用
- `DrawString` 0x219D1C–0x219D34 读 `face[+0x08]`（`lwc1` + `cvt.s.w`，即**当整数**用），乘到步进宽上 ⇒ 疑为**字号/缩放**
- `fld[7]` 的三个值 0 / 208 / 416 与 `fld[1]`(26/26/16) 一起，疑为**基线/行距**类度量；**本轮未反汇编到消费者 ⇒ 未定，不要凭它推导**
- `fld[0]=10`、`fld[12]=32`、`fld[13]=26/26/42` **未定**

**尾部 278 B（0x1620..0x1736）= 风格块序列**（不是记录表，也不是面描述块起点）：
```
@0x1620  8,7,"default\0", 0, 0, 3, 1, 1.0f, 1.0f     (40 B)
@0x1648  7,"default\0",   0, 0, 3, 1, 1.0f, 1.0f
@0x1670  5,"large\0",     0, 0, 3, 2, 1.0f, 1.0f
…（共 7 块，末块 @0x1710 "huge" 的 scale = 1.6f/1.6f）
```
⇒ `0x1620` 是**记录区结束后的风格区**。Lead 在 round106 读到的 `{n=8,m=7,"default"}` 就是这一块，
**不是面描述块起点、更不是记录表起点** —— 记录表起点分别是 0x005D / 0x0960 / 0x1260。

---

## 3. 对 Lead 「唯一变量 = h」的**证据复核**（★ 重要更正）

`work/tools/diff_font_record_fields.py` 比的是**记录起点 +0x000..+0x05F**。而记录的真实字段偏移是：

```
+0x000 type(0)   +0x004 nameLen(16)   +0x008..0x017 name(16 B)
+0x018 psm(0x14) +0x01C w(1024)       +0x020 h(512)      +0x024 clut_size(1040)
+0x028..       = **调色板数据**（不是字段！）
+0x438         = **px_size**（0x40010）—— 落在 96 B 窗口之外, 该工具**没比**
```

⇒ 该工具报的"+0x028/+0x02C 未变"其实是**调色板前 8 字节没变**，
**不能**用来证明"块读派生字段没变"；同时 **`px_size` 根本没被比较**。

实验矩阵复核（`docs/REPORT_zero_missing_glyph_build2.md` §5.1）：

| 盘 | PAK 长大 | off 平移 | 声明长度对齐 | **px_size/容器** | **h** | 结果 |
|---|---|---|---|---|---|---|
| 基线 | ✗ | ✗ | ✗ | 0x40010 / 8 段 | 512 | ✓ 191 截图 |
| GROW | ✓ | ✓ | ✓ | **0x40010 / 8 段** | **512** | ✓ 191 截图 |
| H640 | ✓ | ✓ | ✗ | **0x501F0 / 10 段** | **640** | ✗ 黑屏 |
| H640B | ✓ | ✓ | ✓ | **0x501F0 / 10 段** | **640** | ✗ 黑屏 |
| H1024 | ✓ | ✓ | ✓ | **0x501F0 / 10 段** | **1024** | ✗ 黑屏 |
| GR_ZH121 | ✓ | ✓ | ✓ | **0x501F0 / 10 段** | **640** | ✗ 黑屏 |

```
★ **没有任何一张盘做到"只改 h、容器不动"。** h 与"容器变大"在全部失败盘上**同时变化**。
⇒ 「h ≤ 512 硬上限」是**推论**，不是被单变量实验证明的事实（任务书把它当成四条实验否证，
   实际是否证了"h 变大 + 容器变大"这一组合，以及"H1024"）。
⇒ 唯一能分开这两者的实验 = **h=640 + px_size 保持 0x40010（只声明、不供数据）**；
   或 **px_size=0x40011（仍 1 块）**（上一轮报告 §5.2 已建议，未做）。
   本轮按任务书禁令**没有**做 h 实验。
```

---

## 4. ★★ 像素容器**没有 196 KB 别的纹理**（更正 Lead 的算术）

`LEAD_RECORD_FORMAT_CONFIRMED.md` §二写：「图集只占 65,536 B（1024×512@4bpp），而容器 = 262,160 B
⇒ 约 196 KB 是别的纹理」。**这是把 4bpp 当成 8bpp 算错了 4 倍**：

```
1024 × 512 @ **4bpp** = 1024 × 512 / 2 = 262,144 B     ← 不是 65,536 B (= /8)
容器 262,160 B = 262,144 (纹理) + 16 (尾部 tag)
实测: 8 段 × 48 B 前缀 + 261,760 B 段数据 = 262,144  ✓ 分毫不差
引擎口径图覆盖率 = **99.80%**（512 行里只有末尾约 1 行未铺满）
```

⇒ **容器里没有任何"别的纹理"可压缩/搬移/冻结**。
「从容器内部腾空间」这条路**在算术上不存在**；能动的只有纹理内部**没被任何采样窗覆盖的像素**（见容量文档）。
