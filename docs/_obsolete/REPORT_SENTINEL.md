# REPORT_SENTINEL.md —— 候选 R（`0xB1/0xB5` 图标哨兵）四张对照盘 + 候选 C（u8 引用计数）静态跟进

> ⚠ **历史错误断言订正（2026-10-18 收尾轮）**：本文含已被实测/实机否证的表述 —— 见 `docs/CORRECTIONS.md` §7。
> 原文保留作过程记录；**结论冲突时以 `docs/CORRECTIONS.md` + `docs/STATUS.md` 为准**。
> 📦 本文档已归档到 `docs/_obsolete/`：被否证路线：候选 R（0xB1/0xB5 图标哨兵）四张对照盘；保留的是 REPORT_SENTINEL_FIX.md；索引见 `docs/README.md`。

> 执行者：汉化执行者（哨兵对照盘子代理）· 2026-10-16
> 仓库根 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> **只读**：`work\builds\GR_CVAR\**`、`work\builds\GR_TXT\**`、`work\builds\GR_HOOK\**`、
> `third_party\orig\**`、`%LOCALAPPDATA%\PCSX2` —— **一字未改**（基底 `CVAR_04_text.iso` 的 sha256
> 与既有 meta 声明逐字一致，见 §7）。
> 写入范围仅：`work\builds\GR_SENT\**`、本文件、`docs\AB_TEST_GUIDE.md`（追加附录 C）。
> **未跑模拟器**（本任务不需要；判据在用户手上）。未 commit / 未切分支 / 未 merge。
> **未使用 `Select-Object -First N`**（需要截断时一律重定向到文件再 `Get-Content`/read）。

---

## 0. 一句话结论（先说会改变你下一步判断的六条）

```
① ★★ 原盘引擎**没有 2 字节解码**：DrawString 的主循环**每条分支都只前进 1 字节**
   （`0x219D90 bnel v1,zero,0x219DB4` + 延迟槽 `0x219D94 addiu s0,s0,1`；
     落空边 `0x219D98..0x219DAC`（x 加 font+0x18）后 `0x219DB0 addiu s0,s0,1`）。
   MIPS「branch likely」在**不跳转时把延迟槽作废** ⇒ 两条边各 +1。
   ⇒ font+0x24 那个标志**只管字距**（固定 font+0x18 vs 累加 CharWidth），**不管步长**。
   ⇒ **CVAR_04 上中文对偶码是被一个字节一个字节画出来的** ⇒ 每个 LANG 容器里
     **全部 314 个 `0xB1/0xB5` 字节都逐个走单字节字符路径**（不只是 286 个 trail）。
   （这同时是 `REPORT_TEXT_OVERFLOW.md` §2.3「+0x33C 原义是 i+=2 else i+=1」的**更正**。）

② ★ `DrawString` 里对 `0xB1/0xB5` 的硬编码立即数有 **8 处**（不是 6 处）：
   0x219C08 · 0x219C10(延迟槽) · 0x219C14 · **0x219C40(分支目标)** · 0x219C94 · 0x219CAC ·
   0x219D24 · 0x219D38。前一批决定**硬编码图标 UV**，后一批决定 **AddOneWord 的 flag=1**
   ⇒ 走 `fontmgr+0x4C` 的**副包**（容量判据 `slti v1,v1,2` @0x21A0D0；主包 `slti v1,v1,1280` @0x219FCC）。

③ ★★ **本轮新发现：`RSFont::CharWidth`（VA 0x21AD10）也硬编码 `0xB1/0xB5`**
   —— `0x21AD38 addiu v0,zero,-75` / `0x21AD4C addiu v0,zero,-79`，命中就**无条件返回 20**
   （0x21AD48/0x21AD58），完全不查字表。⇒ 哨兵字节有**第二个硬编码消费者（字距）**，
   而它 **不在** SENT_02 的补丁范围里。全 ELF 这类立即数共 **10 处** = DrawString 8 + CharWidth 2。

④ ★ **「只改 trail」在数学上不可行**（用数据证明，不是猜）：charset 的 `pair_of` **铺满整个对偶空间**
   （25 lead × 94 trail = 2350，一格一字），而语料（3 容器并集）用了 1651 格，
   **lead 0xA1..0xB0 全部 94/94 饱和**（只有 0xA7 空 0xE3、0xAF 空 0xF1 各 1 格）
   ⇒ 32 个哨兵对偶码里**没有一个能在同 lead 内找到空闲 trail** ⇒ 必须**整对搬移**（每处改 2 字节），
   落到 497 个完全空闲的对偶码里（全在 lead 0xB2/0xB3/0xB4/0xB6/0xB7/0xB8/0xB9）。

⑤ ★ **四张盘已产出并通过独立终检**（`work\builds\GR_SENT\`，§3/§7）：
   `SENT_01_trail_fix`（3 容器 730 处哨兵全清）/ `SENT_02_icon_path_off`（只改 ELF 8 字节，
   文本一字不动 ⇒ **布局中性臂**）/ `SENT_03_xml_only` / `SENT_04_lang_only`（与 01 构成
   {LANG,XML}×{改,不改} 的 **2×2 闭合**）。判定表见 §5。

⑥ ★ 候选 C（u8 引用计数）**静态推进到"未达成"**（§B）：`Substring` 其实是**造新节点、不累加源**，
   "循环里 Substring 把源推到 255"这条**死掉**；批量拷贝的两个 helper
   （`RSArray<RSUIString>::operator=` / `Copy_Array`）都是**先析构旧元素再拷** ⇒ 不泄漏。
   没找到任何能把**同一节点**同时存活副本推到 >255 的静态路径。**需要实机写监视 `RSString+2`。**
```

---

## 1. 本轮新增的静态证据（全部可复跑）

复现命令：

```powershell
$env:PY = "C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

# 哨兵形态普查 + 替代表（→ audit\A_sentinel_scan.txt / .json / A_trail_sites.csv）
& $env:PY work\builds\GR_SENT\tools\sent_scan.py

# 对偶空间占用普查（→ 控制台）
& $env:PY work\builds\GR_SENT\tools\sent_occ.py

# 候选 C：refcount 调用点普查 + 循环归属（→ audit\B_refcount.txt）
& $env:PY work\builds\GR_SENT\tools\sent_refcount.py

# 反汇编（只读原盘 ELF；已存盘）
& $env:PY work\tools\cave_dis.py third_party\orig\ps2\slus_out\SLUS_206.13 diso 0x219A70 0x219E10
& $env:PY work\tools\cave_dis.py third_party\orig\ps2\slus_out\SLUS_206.13 diso 0x21AD10 0x21AE60
```

### 1.1 ★★ 原盘 DrawString 的步进：**两条分支都是 +1**（更正既有报告的读法）

```
0x219BC4  v0 = s6 + s0            ; s6 = 串首, s0 = 索引(字节)
0x219BC8  a1 = lb 0(v0)           ; ★ 取**有符号字节**
0x219BCC  jal 0x0040BFC8 (wctomb) ; a0 = sp+223（1 字节格）
0x219BD4  a1 = lb 223(sp)         ; ★ a1 = 符号扩展后的字节值（0xB1 ⇒ 0xFFFFFFB1 = −79）
0x219BD8  jal CharWidth           ; 先量宽（**哨兵字节在这里就已经被特判，见 §1.2**）
...
0x219D8C  v1 = lbu 36(s3)         ; s3 = RSFont, font+0x24 = 标志
0x219D90  bnel v1, zero, 0x219DB4 ; 标志≠0 ⇒ 跳到循环尾
0x219D94  addiu s0, s0, 1         ; ★ 延迟槽：只在**跳转发生时**执行 ⇒ +1
0x219D98  f1 = lwc1 24(s3)        ; 标志==0 才会走到这里：x += font+0x18（固定字距）
0x219DA0..0x219DA8  x = x + font+0x18
0x219DAC  nop
0x219DB0  addiu s0, s0, 1         ; ★ 落空边自己的 +1
0x219DB4  slt v1, s0, s7
0x219DB8  bnel v1, zero, 0x219BC4 ; 循环回边（同样 likely：+1 在延迟槽里）
0x219DBC  v0 = s6 + s0
```

* `bnel`（opcode `0x15`，branch-likely）的语义：**不跳转时延迟槽被作废**。
  所以「跳转边」靠延迟槽 +1、「落空边」靠 0x219DB0 +1 —— **两边都是 +1**。
* ⇒ `font+0x24` 是**等宽/比例字距标志**，不是 DBCS 步进标志。
  真正的 DBCS 2 字节解码是**汉化自己加的**（`0x416ED0` cave + `sp+222`/`lhu`，
  见 `REPORT_HOOK_BISECT.md` §1.2 G3）；原盘从来没有过。
* ⇒ 在 **CVAR_04（原盘 ELF）** 上，中文文本的**每一个字节**都是一个独立字符，
  `0xB1/0xB5` 就在**每一个字节位置**上撞图标特判。**这是候选 R 的成立前提，现已坐实。**

### 1.2 ★ `0xB1/0xB5` 的**两个**硬编码消费者

**(a) `RSFontMgr::DrawString`（VA 0x219A70）—— 8 处立即数**

| VA | 指令 | 作用 |
|---|---|---|
| `0x219C08` | `addiu v1,zero,0xFFB5` | 0xB5 判定 |
| `0x219C10` | `addiu v1,zero,0xFFB5` | 上一条的**延迟槽副本**（跳转不发生时执行） |
| `0x219C14` | `addiu v1,zero,0xFFB1` | 0xB1 判定 |
| `0x219C40` | `addiu v1,zero,0xFFB5` | **`beq` 的跳转目标**再装一次（0xB1 分支进来后比出"不是 0xB5"） |
| `0x219C94` | `addiu v1,zero,0xFFB5` | **第二次判定**：命中就跳到 `0x219CB8` 的"图标专用字距"块（跳过普通 `f23 += f21` 累加） |
| `0x219CAC` | `addiu v1,zero,0xFFB1` | 同上 |
| `0x219D24` | `addiu v0,zero,0xFFB5` | 决定 `AddOneWord(...,t0=1)` ⇒ **副包** |
| `0x219D38` | `addiu v0,zero,0xFFB1` | 同上 |

命中后果（第一批判定，`0x219C08..0x219C40`）：**跳过 `ComputeCharTextureCoords`**，
改用硬编码 UV（0xB5: `0x3F80/0x4346/0x41A8/0x435A`；0xB1: `0x3F80/0x4346/0x4234/0x435A`，
写入 `sp+176..188`）；命中后果（第二批判定，`0x219C94/0x219CAC`）：字距走图标专用块；
命中后果（第三批判定，`0x219D24/0x219D38`）：`AddOneWord` 的 `t0=1`
⇒ 顶点进 **`fontmgr+0x4C` 的副包**：

```
AddOneWord(0x219F50):  t0 != 0 ⇒ 0x21A078（副包路径）
   0x21A0B8 v1 = lw 104(s0)      ; 副包计数
   0x21A0BC v1 += 1
   0x21A0CC slti v1, v1, 2       ; ★ 副包容量 = 2
   0x21A0D4 bne → 0x21A174 返回（未满不 flush）
   满 ⇒ SetAlpha/SetLinearSampling/AddModel(+0x28 主包 if 非空)/AddModel(+0x4C 副包)/计数清零
主包：0x219FCC slti v1,v1,1280 ；0x219FC8 v1 = lw 68(s0)
```
⇒ **每遇到 2 个哨兵字节就多一整轮 flush（两个 AddModel）**。这是「内容驱动、与长度无关」的
形状：**命中次数只取决于用到了哪些汉字**，与串长无关（中文 payload 只有英文的 48.6%）。

**(b) ★ 本轮新发现：`RSFont::CharWidth`（VA 0x21AD10）**

```
0x21AD18  v0 = lbu 36(a0)          ; font+0x24 标志
0x21AD1C  beq v0,zero → 0x21AD2C   ; 标志≠0 ⇒ 0x21AD28 v0 = lw 12(a0)（**固定字宽**）
0x21AD2C  v1 = (符号扩展)a1
0x21AD30  v0 = 32 ; 0x21AD34 beq v1,32 → 0x21ADD0/0x21AD40 v0 = lw 20(a0)   ; 空格宽
0x21AD38  v0 = -75 (0xFFB5)
0x21AD44  beq v1,v0 → 0x21AD5C
0x21AD4C  v0 = -79 (0xFFB1)
0x21AD50  bne v1,v0 → 0x21AD64
0x21AD58  v0 = 20 ; 0x21AD5C → 0x21ADD4 返回    ; ★★ 0xB1/0xB5 ⇒ **硬编码 20**（不查表、不缩放）
0x21AD64  a2 = lw 40(a0)           ; face
0x21AD74  v1 = lb 32(a2)           ; face->firstchar（= 0x20）
0x21AD78  v0 = v0 - v1 ; 0x21AD7C andi 0xFF
0x21AD80  bltzl v1 → 0x21AD9C      ; ★ idx < 0 ⇒ 0
0x21AD88  v0 = lw 68(a2)           ; face->nrec = 224
0x21AD8C  slt v0,v1,v0 ; bne → 0x21AD9C   ; ★ idx ≥ nrec ⇒ 0（**钳位，不是越界读**）
0x21AD9C  a2 = lw 56(a2) ; v0 = idx*10 ;
0x21ADB8  v0 = lbu 1(v0)           ; ★ 宽 = rec[idx].b1
```
* ⇒ 哨兵字节的**字距被硬编码成 20**，而原盘字表里**只有 0xB1/0xB5 是 20**
  （`large` 最大 18、`default` 最大 16；只有 `huge` 面另有 5 个字节 = 20）。
* ⇒ 这是**第二个**必须一起考虑的特判；**SENT_02 没有动它**（见 §6 混淆项 C2）。
* 全 ELF 扫 `addiu rX,zero,0xFFB1|0xFFB5` 共 **10 处**（audit\B_refcount.txt §2 与
  `SENT_02_icon_path_off.meta.json` 的 `elf_icon_imm_sites_all`）。

### 1.3 哨兵形态普查（与 `REPORT_TEXT_OVERFLOW.md` §3.6 逐字一致）

| 容器 | 条目 | payload | `0xB1` | `0xB5` | 含其一的条目 | **当 trail** | 裸单字节 | 语料里出现的对偶码 |
|---|---|---|---|---|---|---|---|---|
| `EN_STRINGS.RES@MENU` | 2232 | 55,751 | 144 | 170 | **207** | **286** | **28** | 1230 |
| `EN_STRINGS.RES@GR` | 2232 | 55,751 | 144 | 170 | **207** | **286** | **28** | 1230 |
| `EN_SPECIAL_FEATURE.XML`（69 个 `<text>`） | 69 | 47,857 | 62 | 96 | 34 | **158** | 0 | 1457 |

* 合计 **786 个哨兵字节 = 730 trail + 56 裸**（三容器；裸的 56 = 两个 LANG 各 28，
  它们是**故意的图标占位**，英文原盘同样有 28 个 ⇒ **本批盘一律保留**，这样"哨兵是不是
  汉字的一部分"才是单变量）。
* ★ **口径更正**：既报告写"含其中之一的条目 = 221"，那是**含裸图标也算**的口径；
  纯按 trail 算是 **207** 条（两个 LANG 各 207）。两个数都对，只是口径不同。
* ★ **XML 另有 8 个哨兵字节在 `<text>` 之外**：都在 `<item name="…">` 的**属性值**里
  （见 `A_sentinel_scan.json` 的 `xml.sentinel_offsets_outside_text` =
  32958 / 33374 / 33759 / 33763 / 34097 / 34099 / 34429 / 34655，全部是 0xB1）。
  本批盘**只改 `<text>` 内容**（= 既有报告的 158/34 口径），这 8 处**原样保留并登记**
  （§6-C4）。这是"最小改动 + 与既有口径可比"的选择，不是遗漏。
* 两个 LANG 容器 **blob 不全等**：长度 128,545 / 128,668（GR 多 123 B），
  **公共前缀内逐字节不同 0 处** ⇒ 差异只在尾部结构；逐条载荷与哨兵位置完全一致。

### 1.4 ★ 「只改 trail」不可行的证明 + 替代表构造

```
charset pair_of: 2350 格全铺满（25 lead × 94 trail，一格一字，无空格）
语料占用（3 容器并集）: 1651 格
lead 占用: 0xA1..0xB0 → 94/94（饱和！只有 0xA7 空 E3、0xAF 空 F1，各 1 格）
           0xB1 → 0 格，0xB5 → 0 格（因为哨兵 trail 的对偶码里没有 lead=0xB1/0xB5 的）
           0xB2/0xB3/0xB4/0xB6/0xB7/0xB8/0xB9 → 15/13/25/29/23/23/21 格
⇒ 32 个哨兵对偶码 (L,0xB1)/(L,0xB5)（L = 0xA1..0xB0）**没有一个能在同 lead 内找到空闲 trail**
（0xA7/0xAF 各只有 1 个空格，只能救 2 个） ⇒ **必须整对搬移**（lead + trail 都变）。
完全空闲的对偶码（并集之外、且两字节都非哨兵）= **497 个**，全部落在 lead 0xB2/0xB3/0xB4/0xB6/0xB7/0xB8/0xB9。
```

**选点规则（确定性、可复算）**：

1. 候选 = 497 个全空闲且两字节都非哨兵的对偶码；
2. 代价 = `Σ_face ( |W(新 lead) − W(原 lead)| + |W(新 trail) − W(原 trail)| )`
   （`W` 取自**原盘** MENU `FONT.RES` 的 3 个面：`W(0xB1)=W(0xB5)=20`（硬编码），
   其余 = `rec[(byte−0x20)].b1`）⇒ **最小化版式扰动**；
3. **贪心匹配**保证替代表**单射**（每轮取当前最小代价的「未分配源 × 未占用目标」）；
4. 并列取字典序最小。

结果替代表（32 条，逐盘写在各自 `*.meta.json` 的 `alias` 段）：

```
A1B1 星→B4DA   A1B5 择→B4C9   A2B1 吗→B2C9   A2B5 文→B2CA   A3B1 墙→A7E3   A3B5 样→B2DC
A4B1 景→B3C9   A4B5 编→B3CA   A5B1 铁→B2D1   A5B5 靠→B2DB   A6B1 章→B9C9   A6B5 表→B9CA
A7B1 励→B3CB   A7B5 厄→B3D0   A8B1 雾→B9CB   A8B5 齿→B9D0   A9B1 损→B6CA   A9B5 太→B6CB
AAB1 今→B2DA   AAB5 欢→B3DA   ABB1 丈→B2D0   ABB5 乘→B2D9   ACB1 概→B3DC   ACB5 殿→B2C8
ADB1 宾→B9D9   ADB5 泛→B9DC   AEB1 酷→B6DA   AEB5 冰→B6C9   AFB1 啤→B2DE   AFB5 坛→B3C8
B0B1 宝→B9C8   B0B5 崇→B9DE
```

（涉及 **32 个不同汉字**（16 lead × 2 哨兵），不是 286 个 —— 既报告"286 个不同字形"是
**把命中次数写成了字数**；286 是**位置数**，去重后是 32 个字。如实登记该口径更正。）

### 1.5 「解码字符序列逐条不变」的证明（口径与边界都写清）

* **替代表口径**：声明 32 条 `新对偶码 → 原字` 的别名（因为新码在 charset 里本来是别的字）。
  在**替代表优先**的解码器下：`decode_alias(产物载荷) == decode_charset(基底载荷)`
  **逐条成立**：两个 LANG 各 **2232/2232** 条、XML **69/69** 个 `<text>` 节点，
  **不符 0 条**（构建时断言 + `sent_verify.py` 从**盘上重读**再断言一次，两次都过）。
* **不用替代表**时：**207 条 LANG 条目 / 34 个 XML 节点**的解码会变
  （被搬移的字会读成新码在 charset 里的主人）。**如实登记**，不掩盖。
* **替代表为什么在 CVAR_04 上站得住**（链条）：
  1. CVAR_04 = **原盘 ELF + 原盘图集/FONT.RES + 三份中文文本** ⇒ 盘上**没有中文字形**，
     中文本来就渲染成"某些英文格子的乱码"（既有报告 §4.3 已写"CVAR_04 也是乱码"）；
  2. 原盘引擎**逐字节**渲染（§1.1 已证）⇒ 对偶码只是**项目侧**的编码约定，
     **引擎侧根本没有"双字节字符"这个概念**；
  3. 原盘 `CharWidth`/`ComputeCharTextureCoords` 对越界 `idx` **钳位到 0**
     （§1.2(b) 的 `bltzl`/`slt` 两条），`firstchar=0x20` 时 `0xA1..0xFE` 落在 `idx 129..222 < 224`
     ⇒ 不触发钳位，但也**只影响画出来的那个（乱码）格子**；
  4. ⇒ 搬移对偶码**改变的只是"画哪个乱码格子"**，不改变任何可读的中文语义（因为不可读）。
     这正是本盘要的单变量：**盘上不再有"汉字第二字节 = 图标哨兵"这一形态**。
* **必须一起报的副作用（不可避免）**：`0xB1/0xB5` 的字距是**硬编码 20**，而任何真实字节的
  字距 ≤ 18（`large`）/ ≤ 16（`default`）⇒ 32 个字各损失约 6~10 单位字距
  （`Σ|ΔW|`：large **329** / default **362** / huge **29**）。**版式会轻微变窄、折行点可能移动。**
  已证明无法避免（除 0xB1/0xB5 外没有宽度 = 20 的字节）。
  ⇒ **SENT_02 是版式中性臂**（文本/图集一个字不动），两张盘一起读可以把"版式"这个变量摘掉。

---

## 2. 候选 C（`RSString` 的 u8 引用计数）静态跟进 —— **未达成**，但把两条路堵死了

完整清单：`work\builds\GR_SENT\audit\B_refcount.txt`（脚本 `tools\sent_refcount.py`）。

### 2.1 布局与 refcount 的每一次 ±1（指令级）

```
RSString  = { u16 len @+0 ; u8 refcount @+2 ; char* data @+4 }   (8 B)
RSUIString= { void* vtable(0x5A72D8) @+0 ; RSString* m_str @+4 } (8 B)
RSUIString 区（0x540EA0..0x542100）里对 +2 的读-改-写共 **52 条**（逐条见 B_refcount.txt §2）
```

| 函数 | VA | 关键指令 | 判定 |
|---|---|---|---|
| 拷贝构造 | `0x541F50` | `541F5C lw v1,4(a1)` / `541F64 sw v1,4(a0)`（**共用同一节点**）<br>`541F6C lbu v1,2(a0)` / `541F70 addiu v1,v1,1` / `541F78 sb v1,2(a0)` | **+1，无上限检查**（u8 直接回卷） |
| 析构 | `0x541E90` | `541EC8 lbu v0,2(v1)` / `541ECC addiu v0,v0,-1` / `541ED0 sb v0,2(v1)`<br>`541ED4 andi v0,0xFF` / `541ED8 bne v0,zero → 跳过 free` | −1；**只有写回恰好为 0 才 free** |
| `operator=` | `0x541CA0` | `541D18/541D20` +1（新节点）；`541D74/541D7C` −1（旧节点） | 与拷贝构造同型 |
| **`Substring`** | `0x540F60` | `540FC0 sb zero,2(s0)` / `540FD0 sb a1,2(s0)`（**新节点**）<br>`541068/541070` +1（结果节点）；`541084/54108C` **−1（源对象节点，减到 0 就 free）** | ★ **造新节点、不与源共享** ⇒ 「循环里 Substring 把源推到 255」**不成立** |

### 2.2 调用点普查（全 .text）

| 目标 | 调用点 | 备注 |
|---|---|---|
| `Substring(int,int)` | **31** | 含 `DoWordWrap` 2 处（`0x21CDD0`/`0x21CE04`，同一循环 `[0x21CC18..0x21CEC4]`） |
| `Substring(int)` | 2 | — |
| 拷贝构造 `__ct__…FRC10RSUIString` | **207** | 「存活副本」的唯一来源 |
| `operator=` | **229** | 同上 |
| `operator+=`（3 个重载） | 1+45+88 | — |
| `__pl__`（3 个重载） | 35+7+28 | — |
| `operator[]` | 32 | — |
| 析构 | **2104** | 与拷贝/赋值配对的 −1 |
| **在循环内的 Substring/拷贝/赋值** | **577** | 每个都给了最内层回跳分支与"返回值是否被 `sw $v0` 存起来" |

**关键结构判定**：`DoWordWrap` 的 Substring → `operator=` → **同一次迭代内 `jal ~RSUIString`**
（`0x21CDDC`→`0x21CDE8`、`0x21CE10`→`0x21CE1C`）⇒ **副本是循环局部的**，
每轮 +1 后立刻 −1，计数不会累积。`DoWordWrap` 里唯一的动态数组是
`IncreaseToSize_Array<i>`（`0x21D2A0`，`RSArray<int>` 行位置），**不是 RSUIString 数组**。

### 2.3 批量拷贝的两个 helper：**先析构旧元素，不泄漏**

```
RSArray<RSUIString>::operator=  0x2FC910:
   若 this==src 直接返回；
   a0 = lw 0(this)（旧数据指针）；非空 ⇒ jal 0x149D20(a0, ~RSUIString=0x541E90)  ← ★ 先析构旧元素
   然后 jal Copy_Array
RSArray<RSUIString>::Copy_Array 0x2FC970:
   count = src->count；__nwa__(8*count+16) 造新数组；
   循环 i<count: jal 0x541CA0(this->data+i, src->data+i)   ← 逐元素赋值（每元素 +1，与源共享节点）
```
⇒ **数组整体赋值不会每调用 +1 泄漏**（旧内容先被释放），
所以「反复导航同一个列表 ⇒ 计数单调爬升到 255」这条也**不成立**。

`RSArray<RSUIString>` 的使用者（14/17 个站点）：`RSHTML::CreateStrings/DrawHTML`、
`ChatBar::ProcessMessage`、`Console::ProcessMessage`（含 `ChangeSize_Array` = 历史增长）、
`IkeMapList`/`IkeSaveList`/`SavedGames::CreateList`、`SPQuickMission::BuildMissionList`、
`PS2ChooseCampaign`/`PS2SP*::BuildGameTypeList`、`ShellMenu::FillKickList`、`RSButtonList`、
`RSStringTable::ReadResource`、`NavigateBetweenItems`。**没有一处能同时存活 >255 个共享同一节点的副本。**

### 2.4 结论与"回卷到底会怎样"的算术

```
· 回卷方向一（+1 从 0xFF → 0x00）：计数读成 0，但仍有 256 个活引用。
  下一次析构读到 0 ⇒ 0−1 = 0xFF（≠0）⇒ **不 free** ⇒ 表现为**泄漏**，不是立刻双 free。
· 回卷方向二（回卷后计数再降回 0）：只有当"活引用数 mod 256 == 0 且计数恰被减到 0"时
  才会 **在有副本存活时 free** ⇒ 悬垂/双 free ⇒ 与 `~RSUIString` 野指针链 + `mmalloc_free`
  收到堆外指针（既有报告 §3.3/§3.4）**形态一致**。
⇒ 机制**可能**，但需要"同一节点同时存活 ≥255 个副本"这个前提。
· **静态未找到这条路径**（§2.1–2.3 把两条最像的路都堵死了）⇒ 判定 **未达成**。
```

**需要的实机证据（明确写清）**：
1. 在 `RSString+2`（对象偏移 +2，1 字节）上设**写监视**（PCSX2 调试器 memory write breakpoint，
   或用 `-debugger` 的 Memory Watch），复现三条触发路径，记录**同一个节点的计数是否跑到 0xFF/0x00**；
2. 更省事的一条：在 `RSUIString` 拷贝构造（`VA 0x541F78`，即 `sb v1,2(a0)` 那一条）
   与析构（`VA 0x541ED0`）上各下断点，**只统计同一个 `a0` 被 +1 的净次数**；
3. 若计数确实只在小范围（0..3）波动 ⇒ **候选 C 可以彻底划掉**，把注意力全部留给候选 R。

---

## 3. 四张对照盘（`work\builds\GR_SENT\`）

### 3.1 基底与设计

基底一律 **`work\builds\GR_CVAR\CVAR_04_text.iso`**（已实证会崩的最小复现盘；
sha256 `554d3d8b9968aaaa2aca3525ab313155dcf4ae55dffe10e7a8bab02520a15179`，本轮**只读**，
与既有 meta 声明逐字一致）。四张盘每张**只动一个变量**：

| 盘 | 改了什么 | 为什么是单变量 |
|---|---|---|
| **`SENT_01_trail_fix`** | 3 个容器里**全部 730 处哨兵 trail**（LANG 286+286、XML 158）整对搬到安全空闲对偶码 | 盘上不再有"汉字第二字节 = 0xB1/0xB5"；**文本一个字没换**（替代表口径下逐条解码不变） |
| **`SENT_02_icon_path_off`** | 只改原盘 ELF 的 **8 处** `addiu rX,zero,0xFFB1/0xFFB5` → `…,0xFF00`（= −256，任何符号扩展字节都不可能等于它） | **文本/图集/结构一个字不动**；等价于"关掉 DrawString 的图标路径"。**版式中性** |
| `SENT_03_xml_only` | 只搬 XML 的 158 处（LANG 原样） | 与 SENT_04 构成 2×2 |
| `SENT_04_lang_only` | 只搬两个 LANG 的 286+286 处（XML 原样） | 与 SENT_03 构成 2×2 |

### 3.2 四张盘的读数（全部来自独立终检 `audit\C_verify.txt`）

| 盘 | sha256 | 尺寸 | 差异 | 允许区外 | 哨兵 trail 残留 |
|---|---|---|---|---|---|
| `SENT_01_trail_fix.iso` | `9e0ae5ee3c66944ed28c17393c088ee87268d7ec653937b1d127c9e4edf863a5` | 1,648,164,864 | **1106 run / 82,403 B** | **0 run** ✅ | MENU 0 / GR 0 / XML 0 |
| `SENT_02_icon_path_off.iso` | `7935b5fff78963960a275198a793ca5b5ecb0e94ebc31b1fbccb468a233817f7` | 1,648,164,864 | **8 run / 8 B** | **0 run** ✅ | MENU 286 / GR 286 / XML 158（**按设计不动**） |
| `SENT_03_xml_only.iso` | `71bab00375f668cbe75cbb8cebaddc12c7d56582dda99b79413eca54129c2274` | 1,648,164,864 | **370 run / 31,634 B** | **0 run** ✅ | MENU 286 / GR 286 / XML **0** |
| `SENT_04_lang_only.iso` | `4f078fc80e3232e546f7c551d0ae66735c5f81a37806e0cad20936653b19af59` | 1,648,164,864 | **736 run / 50,769 B** | **0 run** ✅ | MENU **0** / GR **0** / XML 158 |

（"哨兵 trail 残留"= 按同一形态口径在**产物盘**上重扫的 trail 数；裸图标占位 28/28/0 全部保留。）

### 3.3 每张盘的硬自检（`*.meta.json` 的 `selfcheck` / `containers`，全部通过）

1. `size_eq_base = true`（1,648,164,864 = 基底），`allowed_region_only = true`（**允许区外 0 run**；
   允许区 = 被改的容器槽 ∪ ELF 补丁 4 字节窗口）。
2. **容器长度不变**：3 个容器的解压 blob 长度与基底**逐字节长度相同**
   （128,545 / 128,668 / 116,486），`repack` 断言"解压总长不变"+ 每个重压子流 `lzo1x_decompress` 回环自检。
3. **条目 1:1**：LANG 2232/2232（`(g,i,length)` 逐条相同）、XML 69 个 `<text>` 节点长度全同。
4. **IMG 条目字段**（`stored/real/off/name`）与基底一致；**两份 IMG 整表 sha256**（686×48 B、
   4070×48 B）与基底一致 ⇒ 条目表一个字未动；ISO9660/LBA 未动。
5. **解码等价**：替代表口径下 `decode(产物) == decode(基底)` **逐条**（LANG 2232×2 + XML 69），
   构建时与终检时各验一次，**均 0 条不符**。
6. **回读**：`SENT_02` 的 8 处补丁从盘上逐字回读 == 声明；且**在盘上重扫 DrawString 整段**
   （0x219A70..0x219E00，232 条指令）确认 **0xFFB1/0xFFB5 立即数残留 = 0**。
7. 帧长 ≤ 槽长 `stored`；槽内帧后余量按既有约定补 0（与基底一致）。
8. 基底盘与英文原盘**未改**：基底 sha256 与 `CVAR_04_text.meta.json` 声明一致（§7）。

### 3.4 构建与复核命令

```powershell
$env:PY = "C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $env:PY work\builds\GR_SENT\tools\sent_build.py                    # 四张全建
& $env:PY work\builds\GR_SENT\tools\sent_build.py SENT_02_icon_path_off   # 单张重建
$env:SENT_DRY='1'; & $env:PY work\builds\GR_SENT\tools\sent_build.py     # 只算不写
& $env:PY work\builds\GR_SENT\tools\sent_verify.py                   # → audit\C_verify.txt（独立终检）
```

### 3.5 每张盘的**预期现象**（哪些"看着坏了"是设计内）

* 四张盘**都仍然是"原盘图集 + 中文文本"** ⇒ **中文一定是乱码**（既有报告 §4.3 已定）：
  CVAR_04 本来就查不到中文字形。**判据只有一条：卡死 / 不卡死。**
* `SENT_01/03/04` 的**乱码图案会与 CVAR_04 略有不同**（被搬移的 32 个字的两个字节都换了格子），
  且这些位置的字距会变窄（§1.5）；**这是设计内，不是坏盘**。
* `SENT_02` 的**画面应当与 CVAR_04 几乎逐像素相同**（文本/图集/字距全未动；
  只是那 314×N 个哨兵字节不再走硬编码图标 UV 与副包 flush）—— **唯一可控的可见差别**是
  原本画成 △/✕ 图标的位置会改画普通（乱码）字形。

---

## 4. 触发与复现（沿用用户已确立的口径）

三条触发点（**只有这三条被用户实测证实**）：**火箭筒开火**（只有火箭筒，文本只差子弹数）→
**L1 小队/地图** → **选择关卡→队伍选择界面**。表现 = **画面完全静止、必须重启**。

建议每张盘的跑法（与 `docs\CVAR_TEST_GUIDE.md` §3 同一口径）：

```powershell
# 0) 先确认没有别人的模拟器实例（独占资源；发现他人实例只等、不许杀）
Get-Process -Name '*pcsx2*' -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime

# 1) 用现成采集器
python tools\iso_build\fix_zh118_run.py `
  --iso  "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_SENT\SENT_02_icon_path_off.iso" `
  --tag  "sent_02_icon_off" `
  --maxframes 0 --snap 0 --timeout 1800 `
  --memcards "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH98\temp\r76\mc_zh" `
  --outroot  "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_SENT\runs"
```

* 每张盘 **≥ 15~20 分钟**、**同一操作序列**（火箭筒 → L1 → 队伍选择 → 存读档循环）、
  **每张盘之间重启模拟器**；跑之前轮询到零 pcsx2 进程。
* 卡死后立刻记 `emulog.txt` 尾部 60 行 + 是否出现
  **`pc=0x541038` / `pc=0x541eb0` / `pc=0x541ca0`**（同一条 RSUIString 链）
  或 `0x102764/0x102a30/0x102aa4`（分配器）。
  （`pc=` 是 PCSX2 的**重编译块入口**，不是出错指令 —— 判"同一条链"可以，判"哪条指令"不行。）

---

## 5. ★ 判定表（跑完怎么下结论）

先跑 **`SENT_02_icon_path_off`**（改 8 字节、版式中性、最干净），再跑 **`SENT_01_trail_fix`**
（数据侧），然后 `SENT_03`/`SENT_04` 二选一或都跑。

| # | 观察（`SENT_02`） | 结论 |
|---|---|---|
| 1 | **不卡**（而 CVAR_04 卡） | ★★ **候选 R 成立，且元凶就是 DrawString 的 `0xB1/0xB5` 图标特判路径**（硬编码 UV + `AddOneWord(flag=1)` 副包）。**与文本长度完全无关**（文本一字未动）⇒ 后续修复走 §8 的"代码侧"或"编码侧"任一条 |
| 2 | **仍卡** | 图标特判**不是**充分原因。**立刻转 `SENT_01`**： |

| # | 观察（`SENT_01`，在 #2 之后读，或与 #1 并列读） | 结论 |
|---|---|---|
| 3 | **`SENT_02` 仍卡、`SENT_01` 不卡** | ★ **哨兵字节作为"数据"是元凶，但走的不是 DrawString 的图标路径** ⇒ 下一个怀疑对象就是**同两个字节的另一个硬编码消费者：`CharWidth` 的硬编码 20**（§1.2(b)，本轮新发现，**SENT_02 没关它**）⇒ 需要第 5 张盘"再关 CharWidth 的 2 处"（一条命令可出，见 §6-C2） |
| 4 | **两张都不卡** | ★ 两条独立路径都能修好同一个症状 ⇒ **"引擎对 `0xB1/0xB5` 的特判"这条线整体成立**（代码侧关掉、数据侧避开，都能修）⇒ 修复可直接选**最便宜的一条**（代码侧 8 字节），不必改 charset/图集 |
| 5 | **`SENT_02` 仍卡、`SENT_01` 也仍卡** | ★★ **候选 R 被排除**（两个方向都堵住）：既不是图标特判，也不是"盘上存在哨兵字节" ⇒ **长度与哨兵都被排除** ⇒ 回到 `REPORT_TEXT_OVERFLOW.md` §5 判定表第 4/7 行（转 `TXT_01/TXT_03/TXT_02` 的读数）与本文 §B（候选 C，需要实机写监视） |
| 6 | 任何一张**卡得比 CVAR_04 更早/更晚/换指纹** | ⚠ 非单调：把两张的 emulog 与 `GR_CVAR\CVAR_04_emulog.txt` **逐项对照指纹**（PC 集合、首次故障形态、终端形态），别只看"卡/不卡" |

| # | 观察（2×2 容器二分） | 结论 |
|---|---|---|
| 7 | `SENT_03`（只修 XML）**不卡** | 贡献者是 **XML（`EN_SPECIAL_FEATURE.XML`）** ⇒ 特殊功能界面的文本 |
| 8 | `SENT_04`（只修 LANG）**不卡** | 贡献者是 **两个 LANG 容器**（菜单/HUD/选项；286×2 处） |
| 9 | `SENT_03` 与 `SENT_04` **都仍卡**，而 `SENT_01` **不卡** | ★ **两份容器各自都能独立触发**（或需要同时清理）⇒ 修复必须覆盖全部 3 个容器（§8） |
| 10 | 三张全卡、只有 `SENT_02` 不卡 | 数据侧清哨兵**不足以**修（说明还有非哨兵形状在起作用），但代码侧关特判**足够** ⇒ **修复取代码侧**，并把数据侧继续往"其它 `0x9x` 特判/编码形状"上查 |

> **判定纪律**：一次只跑一张、同一操作序列、每张 ≥15 分钟、每张之间重启；
> 卡死立刻记 emulog 尾部 60 行 + 停顿 PC 集合。**先跑 `SENT_02`。**

---

## 6. 混淆因素（必须一起读）

| # | 因素 | 说明 |
|---|---|---|
| **C1** | **SENT_01/03/04 会改变版式（轻微）** | `0xB1/0xB5` 的字距硬编码 20，任何替代码都 ≤18/≤16 ⇒ 32 个字的字距各降约 6~10 单位（`Σ|ΔW|` large 329 / default 362 / huge 29）。折行点可能移动 ⇒ "文字排版"这个变量在数据侧盘上**动了**。**`SENT_02` 没有这个问题**（版式中性臂） |
| **C2** | ★ **`SENT_02` 只关了 DrawString 的 8 处，没关 `CharWidth` 的 2 处** | `CharWidth`（0x21AD38/0x21AD4C）对 0xB1/0xB5 **硬编码返回 20**。若判定表 #2/#3 出现，第 5 张盘 = 再加这 2 处（补丁与 `SENT_02` 同型：立即数 → `0xFF00`，ISO 偏移 `0x1AE5B8` / `0x1AE5CC`）。**按任务上限本批只出 4 张**，如实登记 |
| **C3** | `SENT_01/03/04` 的替代表是**项目侧声明** | 它保证"解码字符序列不变"，其合法性建立在"CVAR_04 上没有中文字形 + 原盘逐字节渲染"（§1.5）。在**汉化盘（ZH113b）**上这个替代表**不成立**（那里的图集真有中文字形，换格子就是换字形）⇒ **本批盘的正确用途是判"哨兵是不是元凶"，不是当成最终修复** |
| **C4** | XML 里 8 个哨兵字节**没清** | 它们在 `<item name="…">` 的**属性值**里（偏移见 §1.3），不在 `<text>` 内容里。本批只清 `<text>`（= 既有报告 158/34 的口径）⇒ "XML 已全清"这句话**只对 `<text>` 成立** |
| **C5** | **28 个裸图标字节一律保留** | 两个 LANG 各 28 个，英文原盘同样有 28 个 ⇒ 它们是**故意的图标占位**。四张盘上它们**照旧命中图标路径** ⇒ 判定表 #1/#3 是"**汉字里的哨兵**"这件事成立，不是"任何图标都不许画" |
| **C6** | `SENT_02` 是**代码补丁**（改了 ELF） | 它把 `addiu rX,zero,-75/-79` 改成 `-256`。**语义边界**：`a1` 恒为 `lb` 出来的符号扩展字节（∈ {0x00000000..0x7F} ∪ {0xFFFFFF80..0xFFFFFFFF}），`−256` 两集合都不在 ⇒ **永不命中**，且这 8 条立即数寄存器随即被覆盖/只用于比较（已逐条核对，不影响后续 UV/flag 逻辑）。改动 **8 run / 8 B**，逐字回读已验 |
| **C7** | 本机复现能力有限 | 既有报告已定案：gsrunner 在 BIOS/记忆卡/ISO/版本全对齐后**复现不出缺页** ⇒ 验收**只能靠用户实机**。**本轮未跑模拟器**（无并发污染） |
| **C8** | `pc=` 是**块入口**不是出错指令 | 见 `REPORT_TEXT_OVERFLOW.md` §3.4；判"同一条链"可以 |

---

## 7. 纪律与污染登记

| 项 | 状态 |
|---|---|
| 既有 ISO / PCSX2 配置 | **全程只读**（`T.Iso` 只读打开；无任何写入既有盘的路径）。基底 `CVAR_04_text.iso` 的 sha256 本轮复算 = `554d3d8b…a15179`，与 `CVAR_04_text.meta.json` 声明**逐字一致** |
| 写入范围 | 仅 `work\builds\GR_SENT\**`、`docs\REPORT_SENTINEL.md`、`docs\AB_TEST_GUIDE.md`（追加） ✅ |
| commit / 分支 / merge | **未做** ✅ |
| 模拟器 | **未跑**（**起跑前** `Get-Process -Name '*pcsx2*'` 计数 = **0**；全程未启动任何实例）。**交付时复查发现 1 个他人实例**：`pcsx2-gsrunner` PID **36876** ⇒ **只记录、不杀**（用户可能正在用自己的官方 PCSX2 测盘，那是最高优先）⇒ **任何人现在起跑都处于并发污染状态**，fps/时序读数不可信 |
| 磁盘 | 构建前 `Get-PSDrive C` = **14.55 GB** 可用 ⇒ 4 × 1.648 GB 可容纳；构建后（本报告写作时）**10.91 GB**；**交付时复查 = 27.63 GB**（其间有其它进程回收了空间，非本任务所为）⇒ 四张盘已落盘，不受影响 |
| **纪律偏差** | **无**。未使用 `Select-Object -First N`（截断一律重定向到文件 + `Get-Content`/read）。构建过程中修过 3 个**本轮自己的脚本 bug**（`decode_with_alias` 返回值未取 `[0]`、XML 分支误判 kind、ELF 补丁把十六进制字符串喂给 `struct.pack`），修好后**重跑全流程**，四张盘与全部读数都是修好之后的产物 |
| **并发工作区（非本任务所为，登记以免误判）** | 交付时 `git status` 显示：`tools/diag/dump_all_text.py`、`tools/font_pipeline/data/charset_compiled_zh16.json`、`tools/text_csv/inject_text_csv.py`、`tools/text_csv/tcslib.py` 为 `M`，若干 `work/builds/GR_TEST_*` 产物为 `D`，磁盘可用量 10.91 → **27.63 GB** ⇒ **工作区里有其它执行者/用户在并发改动**。本任务**只写** `work\builds\GR_SENT\**` 与本文件 + `docs\AB_TEST_GUIDE.md`（追加），上述改动**不是本任务做的**，且本任务全程以 `mmap`/只读方式访问既有盘，**不依赖**这些文件的当前内容（本轮的读写口径全部落在 `work\builds\GR_SENT\tools\*.py` 与 `tools\text_csv\tcslib.py` 的既有 API 上） |

---

## 8. 修复路径预案（候选 R 成立时）

三条路，按**代价从低到高**：

### 8.1 代码侧（最便宜，且项目**已经做过一次**）
把 ELF 里对 `0xB1/0xB5` 的硬编码特判改掉 —— 这正是汉化盘 `GR_ZH113b` 已有的做法
（`REPORT_HOOK_BISECT.md` §1.2 G3：「6 处图标码立即数 `-75/-79` → `181/177`」）。
* 本批 `SENT_02` 证明了**补丁形态可安全构建**（8 字节、`0xFF00`、逐字回读、0 越界）。
* **代价**：8 字节（DrawString）+ 2 字节（CharWidth，本轮新发现，**建议一起改**）。
* **风险**：`SENT_02` 的 `0xFF00` 写法是"永不命中"；若要用 `181/177`（汉化盘口径），
  必须确认引擎送进来的 `c` 是**符号扩展**（`lb`）还是**无符号**（`lhu`）—— 原盘是 `lb`（§1.1），
  汉化 cave 改成了 `lhu`，两者口径不同，**不要照抄**。
* **这是推荐路径**：单变量盘已验证、代价最小、不碰文本/图集。

### 8.2 编码侧（"重排 charset 对偶分配"）—— 可行，但要动图集
目标：让**任何字**的对偶码两字节都不落 `0xB1/0xB5`（不只是 trail）。
* **必要性**：`pair_of` 铺满 2350 格，且高频字（前 16 个 lead）**94/94 饱和**
  （本文 §1.4 实测）⇒ 不能只挪 trail，**必须整对重新分配**，并保证新对偶码不与任何
  现存字的码冲突（否则文本会串字）。
* **代价评估**（在 `GR_ZH113b` 那类**有中文字形**的盘上）：
  1. 选 32 个（或更多）**空闲对偶码**：本盘语料并集外有 497 个空格，但**汉化盘的 charset
     有 2350 个字**（不是本项目 1651 格占用），可用空格要以**汉化盘自己的 charset** 重新普查；
     若不足，就要扩图集格子（`LEAD_CAPACITY_2400.md` §11 的容量阶梯：保守 2,240 / 乐观 2,368 格，
     **已经很紧**）。
  2. **把字形搬到新格**：每个被搬的字要在 `COMMON.PAK` 图集里把 16×16 4bpp 的格子
     （128 B）**复制到新格**，并更新 `FONT.RES` 对应记录（`rec[idx]` 10 B：`u0/v0/u1/v1/b1`），
     **同时**保证 `u0 = x−20 ≥ 1`（0xA1 码位诅咒）与记录带不重叠（`LEAD_CAPACITY_2400.md` §11 的扣行问题）。
     32 个字 ⇒ ≈ 32×128 B 像素 + 32×10 B 记录 + 图集重压（容器尺寸不变）。
  3. 重新生成全部文本（charset → CSV → 容器），并**逐条**验证解码不变（本轮的替代表口径可用）。
* **代价结论**：不是"改几个字节"，是**一次 charset + 图集的再分配**，且**容量已经很紧**
  （需要先做一次"空闲格 + 记录带冲突"的普查）；但它**一次修好所有容器与所有界面**，
  且不依赖任何引擎补丁。
* **最小可行变体**：只搬**32 个**哨兵字（不是全部字），把它们的格子复制到 32 个空格 —— 
  这是 8.2 里最省的一档，代价 ≈ 32 格。

### 8.3 混合（推荐的实际做法）
**先上 8.1**（8+2 字节，立刻可用、可验证）；把 8.2 作为"正式版洁癖修复"，
在容量普查通过后再做。若 8.1 在实机上把卡死修掉，8.2 的优先级可以降到最低
（它只解决"引擎特判"，而特判已被补丁关掉）。

---

## 9. 未达成项（如实列出）

1. **没有实机数据**：四张盘**没有跑过**（任务书明示本任务不需要模拟器）。§3.5 的"预期现象"只是预期。
2. **`SENT_02` 没关 `CharWidth` 的 2 处硬编码**（本轮新发现）—— 受"最多 4 张"限制，
   如实登记为第 5 张盘的内容（§6-C2 给了 ISO 偏移，一条命令可出）。
3. **XML 里 8 个属性值内的哨兵没清**（§1.3 / §6-C4）：它们是 `<item name="…">` 的标签，
   是否**显示**未核实（若显示，则"XML 全清"需要把口径从 `<text>` 扩到**整个 blob**）。
4. **候选 C 未达成**（§2.4）：没有静态路径能证明"同一节点 ≥255 个存活副本"；
   需要实机在 `RSString+2` 上设写监视（或统计 `0x541F78` / `0x541ED0` 对同一 `a0` 的净次数）。
5. **替代表在汉化盘（`GR_ZH113b`）上不成立**：本轮只证明"在 CVAR_04 上换对偶码不改变可读语义"
   （因为那里没有中文字形）。**在真盘上搬对偶码必须连图集格子一起搬**（§8.2）。
6. **`SENT_01/03/04` 改了版式**（字距 −6~10 / 32 字，§6-C1）：无法避免（除 0xB1/0xB5 外没有宽度 20 的字节）；
   若要"零版式变化"的对照，只能用 `SENT_02` 这条代码侧臂。
7. **`0xB1/0xB5` 之外是否还有别的"非常规字节"**：本轮只做了这两个字节的**全 ELF 立即数普查**
   （10 处）与**字表宽度普查**；`DrawString` 另有 `0x20`（空格）特判（`0x219BEC`），
   其它字节**未再穷举**（沿用既有报告的结论）。
8. **`0x149D20`（`RSArray<RSUIString>::operator=` 里析构旧元素的 helper）的完整语义未逐条读**：
   只确认它被以 `a1 = ~RSUIString(0x541E90)` 调用、且发生在 `Copy_Array` 之前（§2.3）。

---

## 10. 产物索引

| 路径 | 内容 |
|---|---|
| `work\builds\GR_SENT\SENT_01_trail_fix.iso` / `.meta.json` | 3 容器 730 处哨兵全清（逐处清单在 meta 的 `site_list`） |
| `work\builds\GR_SENT\SENT_02_icon_path_off.iso` / `.meta.json` | ELF 8 字节补丁（含 10 处全 ELF 立即数站点表） |
| `work\builds\GR_SENT\SENT_03_xml_only.iso` / `.meta.json` | 只清 XML |
| `work\builds\GR_SENT\SENT_04_lang_only.iso` / `.meta.json` | 只清 LANG |
| `work\builds\GR_SENT\summary.json` | 四张盘 sha256 / 尺寸 / 差异 / 剩余哨兵 |
| `work\builds\GR_SENT\audit\C_verify.txt` | ★ **独立终检**（从盘上重读；四张全 ✅） |
| `work\builds\GR_SENT\audit\A_sentinel_scan.txt` / `.json` / `A_trail_sites.csv` | 哨兵形态普查 + 逐处清单 + 替代表 |
| `work\builds\GR_SENT\audit\B_refcount.txt` | 候选 C：52 条 refcount 指令 + 调用点普查 + 577 个循环内站点 + 重点函数全文 |
| `work\builds\GR_SENT\audit\B_uiarray.txt` | `RSArray<RSUIString>` 全部使用者与调用点 |
| `work\builds\GR_SENT\audit\_drawstring_orig.txt` / `_charwidth_orig.txt` / `_addoneword_orig.txt` / `_uiarray_copy.txt` 等 | 原盘 ELF 反汇编取证（只读产出） |
| `work\builds\GR_SENT\tools\sent_lib.py` / `sent_scan.py` / `sent_occ.py` / `sent_build.py` / `sent_verify.py` / `sent_refcount.py` | 全部脚本（既有 ISO 只读） |
| `docs\REPORT_SENTINEL.md` | 本文件 |
| `docs\AB_TEST_GUIDE.md` 附录 C | 本批盘的速查 + **全局测试优先级** |

---

# ★ 附录 S5 —— 第 5/6 张盘：代码侧**全关**（`SENT_05_icon_all_off` / `SENT_06_icon_all_off_zh113b`）+ 全 ELF 消费者普查收口

> 执行者：汉化执行者（`SENT_05/06` 子代理）· 2026-10-16
> **只读**：`work\builds\GR_CVAR\**`、`work\builds\GR_SENT\SENT_0{1..4}*`、`work\builds\GR_ZH113b\**`、
> `third_party\orig\**`、`work\builds\GR_HASHR\**`（只读其产出）、PCSX2 配置。
> **写入仅**：`work\builds\GR_SENT\**`、本文件（追加）。**未 commit / 未切分支 / 未 merge**。
> **未跑模拟器**（起跑前与交付前 `Get-Process -Name '*pcsx2*'` 计数 = **0**，全程未启动任何实例）。
> **未使用 `Select-Object -First N`**（截断一律重定向到文件再 `Get-Content`/read）。

## S5.0 一句话结论（先说会改变你下一步判断的六条）

```
① ★★ 全 ELF 穷举普查（180/186 处立即数，逐条判定）的结论：
   **对「文本字节 0xB1/0xB5」做硬编码相等比较的，全盘只有那 10 处**
   （原盘 = DrawString 8 + CharWidth 2）。**没有第 11 处。**
   · 0 处 `slti/sltiu`（原盘）；ZH113b 的 4 处 `sltiu …,0xB1` 是 **DBCS lead 区间边界**
     （`lead < 0xB1` ⇒ 对偶码），**不是相等比较**，动了就是改解码区间 ⇒ **本批一律不碰**。
   · 0 处 `lui+ori` 拼出的 32 位 0x…B1/B5 常量。
   · 1 处 `ori rX,zero,0xFFB5`（VA 0x105488）= 16 位常量 **0x0000FFB5**，
     任何 `lb`/`lbu` 出来的字节（≤0xFF 或 ≥0xFFFFFF80）**都不可能等于它** ⇒ 结构上不可能是字节消费者。
   · 14 处其它 `addiu rX,zero,177/181` 已在 §S5.2 逐条判死（对象尺寸 / 事件码 / 颜色 / 行号 / 指针偏移）。
   · 38 处 `word == 0x000000B1/0xB5` 是**数据表**里的 4 字节项（反汇编误读成 SPECIAL），见 §S5.3。

② ★★ 新证据一：`beq $a2, 0xB1/0xB5`（VA **0x5117CC / 0x5117DC**）**不是文本字节消费者**。
   它是「事件/资源码」分发器 `0x511730`，键值来自 `lhu $a2, 8($a1)`，而 +8 那个 16 位字段
   正是 `0x126A20(code)` 造的（`0x126A4C sh $s1, 8($s0)`）。
   **650 个 `jal 0x126A20` 调用点里，a0 = 编译期小整数常量 345 个 / lw 20 个 / 未知 284 个 /
   `lb` 出来的字节只有 1 个（且是结构体字段 51($v1)）** ⇒ 这些 0xB1/0xB5 是**码**，不是文本字节。
   ⇒ **本批不改它**（改了会把事件 0xB5 变成 no-op，给诊断盘引入与主题无关的行为差），
   一行命令可加（见 §S5.8-①）。

③ ★★ 新证据二（**更正既有口径**）：在**汉化盘 `GR_ZH113b`** 上，
   · `0x21AD10` 是 **trampoline**：`addiu sp,sp,-16; sd ra,0(sp); j 0x416F40; nop`
     ⇒ **活的 `CharWidth` 在 cave `0x416F40`**，源码体 `0x21AD20..0x21ADD8`（含
     `0x21AD38`/`0x21AD4C` 的 `0xFFB5/0xFFB1`）**没有任何外部入口 ⇒ 死代码**
     （`sent_reach.py` 实测：进入该区间的 8 条控制流全部来自区间内部）。
   · cave 版 `CharWidth` **先按高字节分流**：`0x416F44 bne $t0,$zero → 0x416F8C`（`$t0 = a1>>8`）
     ⇒ **汉字对偶码（高字节≠0）根本不进 0xB1/0xB5 特判**；`0x416F5C/0x416F68` 只对**单字节**生效。
   · DrawString 的「第 8 处」`0x219C40`（`addiu v1,zero,0xFFB5`）**本来就是惰性**：它只从
     `0x219C18 beq a1,0x00B1` 进入 ⇒ 执行到 `0x219C44 bne a1,0xFFFFFFB5` 时 `a1 ≡ 0x00B1`
     ⇒ **恒不相等**（`lb` 口径与 `lhu` 口径下都恒不相等）。
   ⇒ **`docs\PATCH_INVENTORY.md` 只列 7 处是「对的」**；本文 §1.2(a) / §6-C2 把 `0x219C40` 算成
     「漏掉的第 8 处」是**口径错误，在此更正**（它不需要改，也改不出差别）。
   ⇒ 在真实汉化盘上，「代码侧特判」这条线**已经被汉化自己基本修平**——这本身就是一条重要判定输入。

④ ★ 两张盘已产出并通过**独立终检**（从盘上重读，`audit\I_verify56.txt`，全 ✅）：
   | 盘 | 改了什么 | 差异 | sha256 |
   |---|---|---|---|
   | **`SENT_05_icon_all_off`** | 原盘 ELF 的 **10 处** `0xFFB5/0xFFB1` → `0xFF00`（= SENT_02 的 8 处 **+ CharWidth 的 2 处**） | **10 run / 10 B** | `e5d822313128bbc3e9216318cd9962f8b9a0f8954cca0501fd5ef8c2b19cab0d` |
   | **`SENT_06_icon_all_off_zh113b`** | ZH113b ELF 的 **12 处**（DrawString 8 + CharWidth 残留体 2 + **CharWidth cave 2**）全部 → `0xFF00` | **12 run / 21 B** | `ab56ce69cc648cd097b288012d0d63e3774d71aafe77500e60a21cc59c58f79a` |
   `SENT_05` **vs `SENT_02` 只差 2 个字节**（ISO `0x1AE5B8` / `0x1AE5CC`，即 CharWidth 的 2 处）
   ⇒ 它是 SENT_02 的**单变量递进**（"再关 CharWidth"这一步值不值），不是新盘。

⑤ ★ 全 ELF 复扫（产物 vs 基底逐站点集合对比）：`SENT_05` 消失 **10/10**、新增 **0**；
   `SENT_06` 消失 **12/12**、新增 **0**；两者尺寸不变、允许区外 **0 run**、
   补丁区间内 0xB1/0xB5 立即数残留 **= 0**、`SENT_06` 的 4 个 gate **原样未动**。

⑥ ★ 与 `GR_HASHR`（`98db5f8b` 那条线）的关系：见 §S5.7。**一句话**：
   代价差 ~3 个数量级（代码侧 10~21 字节 vs 编码侧 42 字搬家 + 738 处文本 + 图集）。
   **判定规则照你定的走**：`SENT_05` 不卡 ⇒ 代码侧足够，`GR_HASHR2400` 降为"洁癖修复"；
   `SENT_05` 仍卡 ⇒ **代码侧在 CVAR_04 上即被排除**，而 `SENT_06` 才是"真盘上代码侧还有没有救"
   的那一票；`SENT_06` 仍卡 ⇒ **以 `GR_HASHR2400`（编码侧重排）为准**。
```

## S5.1 复现命令（全部可重跑；既有 ISO 全程只读）

```powershell
$env:PY = "C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

# ① 全 ELF「0xB1/0xB5 硬编码消费者」穷举普查（180/186 处 + 逐条分类）
& $env:PY work\builds\GR_SENT\tools\sent_imm_census.py third_party\orig\ps2\slus_out\SLUS_206.13 `
        --tag "ORIG" --out work\builds\GR_SENT\audit\D_imm_census_orig.txt
& $env:PY work\builds\GR_SENT\tools\sent_imm_census.py SLUS_206.13 --iso work\builds\GR_ZH113b\GR_ZH113b.iso `
        --tag "ZH113b" --out work\builds\GR_SENT\audit\D_imm_census_zh113b.txt
& $env:PY work\builds\GR_SENT\tools\sent_imm_stats.py          # → audit\J_imm_stats.txt（分类汇总）

# ② ISO 内就地读 ELF（VA→ISO 由 PT_LOAD 推出，自检 −0x6C780）
& $env:PY work\builds\GR_SENT\tools\sent_isoelf.py work\builds\GR_ZH113b\GR_ZH113b.iso hdr
& $env:PY work\builds\GR_SENT\tools\sent_isoelf.py work\builds\GR_ZH113b\GR_ZH113b.iso dis 0x416ED0 0x417030

# ③ 可达性探针（判「死代码 / 惰性」）
& $env:PY work\builds\GR_SENT\tools\sent_reach.py "--iso=work\builds\GR_ZH113b\GR_ZH113b.iso" 0x21AD20 0x21ADD8

# ④ 「0x5117xx 是不是文本消费者」：650 个 0x126A20 调用点的实参来源直方图
& $env:PY work\builds\GR_SENT\tools\sent_tokprobe.py > work\builds\GR_SENT\audit\F_tokprobe.txt

# ⑤ 建盘 + 独立终检
& $env:PY work\builds\GR_SENT\tools\sent_build56.py
& $env:PY work\builds\GR_SENT\tools\sent_verify56.py    # → audit\I_verify56.txt
```

## S5.2 ★ 全 ELF 普查：所有 `imm16 ∈ {00B1,00B5,FFB1,FFB5}` 的逐类判定

原始读数：`audit\D_imm_census_orig.txt` / `D_imm_census_zh113b.txt`（逐条 VA/ISO/opcode/反汇编）
与 `audit\J_imm_stats.txt`（分类汇总）。**原盘 180 处 / ZH113b 186 处**。

| 类别 | 原盘 | ZH113b | 能不能是「文本字节的硬编码比较」 | 本批处理 |
|---|---|---|---|---|
| `addiu/addi rX,zero,imm` | 24 | 26 | ★ **只有 DrawString 8 + CharWidth 2 这 10 处是**（见 §S5.4 判定） | **改这 10 处** |
| ├ DrawString 段内 | 8 | 8 | 是（图标 UV 路径 / 图标字距 / `AddOneWord(flag=1)` 副包） | 改 |
| ├ CharWidth 段内 | 2 | 2 | 是（硬编码字距 20）——但 ZH113b 这 2 处是**死代码**（§S5.5） | 改（原盘有效） |
| ├ CharWidth cave（ZH113b 独有） | — | 2 | 是，但**只对单字节**（高字节已分流） | 改 |
| └ 其它 | 14 | 14 | **否**，逐条见下 §S5.2.1 | 不改 |
| `slti/sltiu`（区间边界） | **0** | 4 | **否**（`lead < 0xB1` 的 DBCS gate，非相等比较） | **不碰**（动了就改解码区间） |
| `ori rX,zero,0xFFB5` | 1 | 1 | **否**（0x0000FFB5，字节不可能等于它） | 不改 |
| `lui`+`ori/addiu` 拼 32 位 0x…B1/B5 | **0** | **0** | — | — |
| 分支位移恰为 +177/+181（`beq/bne/beql/bc1f`…） | 118 | 118 | **否**（那是 **branch offset**，不是常量） | 不改 |
| `lbu/sb/lw/sw` 的 **offset** 恰为 177/181 | 34 | 34 | **否**（结构体偏移，如 `lbu $v1,177($s0)`） | 不改 |
| `word` 恰为 `0x000000B1/B5`（数据表） | 38 | 38 | **否**（事件码表 / 资源描述表，§S5.3） | 不改 |

### S5.2.1 14 处「其它 `addiu rX,zero,177/181`」逐条判定（原盘；ZH113b 同址同值）

| VA | 指令 | 判据（上下文）+ 结论 |
|---|---|---|
| `0x170AAC` / `0x170D74` | `addiu $a2,$zero,177` | 相邻调用是 `a1=0x38,a2=0xAF,a3=0x820,t0=0xB0` 与 `a1=0x39,a2=0xB1,0x820,t0=0xB2` ⇒ **连续整数阶梯（调色/渐变表实参）**，非比较 |
| `0x271450` | `addiu $a0,$zero,181` | 紧接 `jal 0x126A20`，与 `0x2ACAFC` 的 `177` 同型 ⇒ **事件/资源码构造实参**（见 §S5.6） |
| `0x2ACAFC` | `addiu $a0,$zero,177` | 同上 |
| `0x2AEC4C`/`0x2AEC54` | `a1=181, a3=181`（+`a2=250,t0=255`） | 4 个相邻实参 = **RGBA 颜色 (181,250,181,255)**，随后 `jal 0x472230`（颜色设置） |
| `0x2B2734`/`0x2B2750` | `addiu $a1,$zero,177/181` | 同一段里 a1 依次 = `0xB0,0xB1,0xB5,0xFB,0xE6` ⇒ **码表遍历**（实参），非比较 |
| `0x35DE34` | `addiu $a1,$zero,181`（分支里） | 同分支另两支给 `0xB8` / `0xBC` ⇒ **三选一的行号/页号** |
| `0x3602CC` | `addiu $s0,$zero,177`（分支里） | 同分支另两支给 `0xB0` / `0xB3` ⇒ **行号** |
| `0x5117C8`/`0x5117D8` | `addiu $v1,$zero,177/181` + **紧接 `beq $a2,$v1`** | ★ **是相等比较，但比的是 16 位「事件码」**（`lhu 8(a1)`；值由 `0x126A20(code)` 写入）⇒ 非文本字节（§S5.6） |
| `0x5121EC`/`0x512264` | `addiu $a1,$zero,177/181` | 同一循环 a1 依次 = `0xAF,0xB1,0xB3,0xB0,0xB2,0xB4,0xB5,0xCE,…` ⇒ **码表遍历实参** |
| （`addiu $a1,$s1,181` 型：`0x21C0BC`/`0x360D3C`/`0x361158`） | `addiu rX,rY,181` | `rs≠0` ⇒ 是**指针偏移**（`s1+181`），结构上不可能是常量比较 |

### S5.2.2 4 个 `sltiu …,0xB1`（**只在 ZH113b 存在**）

```
0x416EE8  sltiu $t1,$a1,0xB1   ← DBCS 解码器 cave 0x416ED0 内的 lead 区间上界
0x417160  sltiu $t1,$t0,0xB1
0x41751C  sltu  $t3,$t2,0xB1（同族）
0x5656A4  sltiu $t4,$t3,0xB1
```
**语义**：`lead < 0xB1` ⇒ 落在 `[0xA1,0xB0]` 就是对偶码 lead。这是**区间边界**，
不是"字节 == 0xB1"。**改它 = 改 lead 区间**（会把 0xB1/0xB5 变成 lead，直接崩文本）。
⇒ 本批**一处未动**，并在 `SENT_06` 里做了「gate 原样」自检（`0x2CA900B1 / 0x2D0900B1 / 0x2D4B00B1 / 0x2D6C00B1`）。

## S5.3 ★ 38 处 `word == 0x000000B1/0xB5` 是**数据表**，不是代码

原始字节取证：`audit\E5_data_region.txt`。

```
VA 0x57C3E8 起（8 字节一项的**码表**）：
  2a000000… / 21000000 / 22000000 / 13000000 / 14000000 / af000000 / b0000000 /
  b1000000 / b5000000 / fb000000 / e6000000 / e5000000 …
  ⇒ 正是 0x2B2734 / 0x5121EC 那两个循环遍历的码表（码值 0xAF,0xB0,0xB1,0xB5,0xFB,0xE6…）

VA 0x5D35C0 起（16 字节一项的**资源描述表**）：
  b5 00 00 00 | 02 60 00 00 | 10 7c 10 00 | 64 08 00 00
  = { u32 code=0xB5 ; u32 flags ; u32 VA=0x107C10 ; u32 size }  ⇒ 资源码，非文本字节
```
按 4 KB 页聚类（原盘与 ZH113b 完全一致）：`0x57C000`×2、`0x58C000`×2、`0x5D3xxx`×2、
`0x5D6xxx`×**11**、`0x5D8000..0x5DE000`×20。
⇒ **这 38 处全部落在 0x57C000/0x58C000/0x5D3000-0x5DF000 三个数据区**，是「表项 / 资源码」，
不参与任何"读文本字节再比较"的语义。**本批一字未动。**

## S5.4 ★ 两张盘的逐字节清单（VA / ISO / 原 / 新）

### S5.4.1 `SENT_05_icon_all_off.iso`（基底 `work\builds\GR_CVAR\CVAR_04_text.iso`，文本一字不动）

基底 sha256 = `554d3d8b9968aaaa2aca3525ab313155dcf4ae55dffe10e7a8bab02520a15179`（**复算一致**）。

| # | VA | ISO 偏移 | 原字 | 新字 | 原立即数 | 新立即数 | 形式 | 作用 |
|---|---|---|---|---|---|---|---|---|
| 1 | `0x219C08` | `0x1AD488` | `0x2403FFB5` | `0x2403FF00` | `0xFFB5` (−75) | `0xFF00` (−256) | 符号扩展 | DrawString 第一次判定（0xB5）⇒ 硬编码图标 UV |
| 2 | `0x219C10` | `0x1AD490` | `0x2403FFB5` | `0x2403FF00` | `0xFFB5` | `0xFF00` | 符号扩展 | 上一条的**延迟槽副本** |
| 3 | `0x219C14` | `0x1AD494` | `0x2403FFB1` | `0x2403FF00` | `0xFFB1` (−79) | `0xFF00` | 符号扩展 | DrawString 第一次判定（0xB1） |
| 4 | `0x219C40` | `0x1AD4C0` | `0x2403FFB5` | `0x2403FF00` | `0xFFB5` | `0xFF00` | 符号扩展 | `beq` 跳转目标再装一次（0xB5 块 / 0xB1 块分流） |
| 5 | `0x219C94` | `0x1AD514` | `0x2403FFB5` | `0x2403FF00` | `0xFFB5` | `0xFF00` | 符号扩展 | 第二次判定：字距走图标专用块 |
| 6 | `0x219CAC` | `0x1AD52C` | `0x2403FFB1` | `0x2403FF00` | `0xFFB1` | `0xFF00` | 符号扩展 | 第二次判定（0xB1） |
| 7 | `0x219D24` | `0x1AD5A4` | `0x2402FFB5` | `0x2402FF00` | `0xFFB5` | `0xFF00` | 符号扩展 | 第三次判定 ⇒ `AddOneWord(t0=1)` **副包**（容量 2） |
| 8 | `0x219D38` | `0x1AD5B8` | `0x2402FFB1` | `0x2402FF00` | `0xFFB1` | `0xFF00` | 符号扩展 | 第三次判定（0xB1） |
| **9** | **`0x21AD38`** | **`0x1AE5B8`** | `0x2402FFB5` | `0x2402FF00` | `0xFFB5` | `0xFF00` | 符号扩展 | ★ **`RSFont::CharWidth` 硬编码字距 20（0xB5）** |
| **10** | **`0x21AD4C`** | **`0x1AE5CC`** | `0x2402FFB1` | `0x2402FF00` | `0xFFB1` | `0xFF00` | 符号扩展 | ★ **`CharWidth` 硬编码字距 20（0xB1）** |

**语义安全性（逐条核对，不是照抄）**：`0x21AD38`/`0x21AD4C` 写的是 **`v0`**，
但查表路径在 `0x21AD68 andi $v0,$a1,0x00FF` / `0x21AD6C dsll32` / `0x21AD70 dsra32`
**用 `a1` 重新算出 `v0`** ⇒ 这 2 条立即数是**纯比较用刮擦寄存器**，改值不影响后续索引/宽度。
（`audit\G_zh113b_disasm.txt` 的 0x21AD64..0x21AD78 与原盘逐字相同，可对照。）

### S5.4.2 `SENT_06_icon_all_off_zh113b.iso`（基底 `work\builds\GR_ZH113b\GR_ZH113b.iso`）

基底 sha256 = `ff3abd3c50e380f666955ccb6226b67198e181589c0db9b4d52e4643208f6445`（与既有文档逐字一致）。

| # | VA | ISO 偏移 | 原字 | 新字 | 原形式 | 可达性 | 作用 / 备注 |
|---|---|---|---|---|---|---|---|
| 1 | `0x219C08` | `0x1AD488` | `0x240300B5` | `0x2403FF00` | **零扩展**（汉化已改） | 活 | DrawString 第一次判定（0xB5） |
| 2 | `0x219C10` | `0x1AD490` | `0x240300B5` | `0x2403FF00` | 零扩展 | 活 | 延迟槽副本 |
| 3 | `0x219C14` | `0x1AD494` | `0x240300B1` | `0x2403FF00` | 零扩展 | 活 | 第一次判定（0xB1） |
| 4 | `0x219C40` | `0x1AD4C0` | `0x2403FFB5` | `0x2403FF00` | 符号扩展 | **惰性** | 只从 `beq a1,0x00B1` 进入 ⇒ `bne a1,0xFFFFFFB5` **恒真**（改前改后等价） |
| 5 | `0x219C94` | `0x1AD514` | `0x240300B5` | `0x2403FF00` | 零扩展 | 活 | 第二次判定（0xB5） |
| 6 | `0x219CAC` | `0x1AD52C` | `0x240300B1` | `0x2403FF00` | 零扩展 | 活 | 第二次判定（0xB1） |
| 7 | `0x219D24` | `0x1AD5A4` | `0x240200B5` | `0x2402FF00` | 零扩展 | 活 | 第三次判定 ⇒ 副包 flag |
| 8 | `0x219D38` | `0x1AD5B8` | `0x240200B1` | `0x2402FF00` | 零扩展 | 活 | 第三次判定（0xB1） |
| 9 | `0x21AD38` | `0x1AE5B8` | `0x2402FFB5` | `0x2402FF00` | 符号扩展 | ★ **死代码** | `0x21AD10` 已 `j 0x416F40`，本体无入口 |
| 10 | `0x21AD4C` | `0x1AE5CC` | `0x2402FFB1` | `0x2402FF00` | 符号扩展 | ★ **死代码** | 同上 |
| **11** | **`0x416F5C`** | **`0x3AA7DC`** | `0x240900B5` | `0x2409FF00` | 零扩展 | ★ **活** | **CharWidth cave（0x416F40）自己的图标特判（0xB5）** |
| **12** | **`0x416F68`** | **`0x3AA7E8`** | `0x240900B1` | `0x2409FF00` | 零扩展 | ★ **活** | **cave 自己的图标特判（0xB1）** |

**唯一会改变行为的 9 处** = 第 1/2/3/5/6/7/8（DrawString 单字节图标路径）+ 11/12（cave 字距 20）。
**行为不变**的 3 处 = 4（惰性）+ 9/10（死代码）——一并改掉是为了「全 ELF 无 0xB1/0xB5 立即数残留」
这一条可机检的判据，逐处登记在案。

### S5.4.3 `0xFF00` 为什么两种语义下都「永不命中」（§6-C6 的展开）

```
原盘（lb 语义）：a1 = 符号扩展字节 ∈ {0x00000000..0x0000007F} ∪ {0xFFFFFF80..0xFFFFFFFF}
汉化（lhu 语义）：a1 = 零扩展 16 位  ∈ {0x00000000..0x0000FFFF}
addiu rX,zero,0xFF00 ⇒ rX = 0xFFFFFF00
  · 0xFFFFFF00 ∉ lb 集合（那个集合只含 0xFFFFFF80 及以上、以及 0x00..0x7F）
  · 0xFFFFFF00 ∉ lhu 集合（那个集合最大 0x0000FFFF）
⇒ 两种口径下都不相等 ⇒ 「永不命中」。**没有照抄汉化 cave 里的 181/177**
（那两个值在 `lhu` 口径下是"恰好命中单字节 0xB1/0xB5"，正好相反）。
```

## S5.5 ★ 汉化盘（ZH113b）上 CharWidth 的真实结构（本轮新证据，含对既有口径的更正）

```
0x21AD10  addiu sp,sp,-16        ← 只 16 字节的 trampoline
0x21AD14  sd ra,0(sp)
0x21AD18  j 0x416F40             ← ★ 真实现被搬到 cave
0x21AD1C  nop
0x21AD20  dsll32 $v1,$a1,24      ┐ 原 CharWidth 本体，仍逐字留在原地，
   ...                            │ 但【没有任何入口】⇒ 死代码
0x21AD38  addiu $v0,zero,0xFFB5  │ ← 本批第 9 处（死）
0x21AD4C  addiu $v0,zero,0xFFB1  │ ← 本批第 10 处（死）
0x21ADD4  jr ra                  ┘
0x21AD90  addiu sp,sp,-16 / sd ra / j 0x416F40   ← 另一个同型 trampoline

0x416F40  srl  $t0,$a1,8          ← ★ cave 版 CharWidth 入口
0x416F44  bne  $t0,$zero → 0x416F8C   ★★ 高字节≠0 ⇒ 对偶码 ⇒ 跳过一切图标特判
0x416F4C  andi $t3,$a1,0xFF
0x416F50  t1 = 0x20 ; 0x416F54 beq $t3,$t1 → 0x41701C   （空格宽 = font+0x14）
0x416F5C  t1 = 0x00B5 ; 0x416F60 beq $t3,$t1 → 0x417028  ← 本批第 11 处（活，仅单字节）
0x416F68  t1 = 0x00B1 ; 0x416F6C beq $t3,$t1 → 0x417028  ← 本批第 12 处（活，仅单字节）
0x416F74.. 查表：face=40(a0) ; firstchar=lb 32 ; idx=(t3−firstchar)&0xFF ; rec[idx].b1 × font+0x1C
```

**可达性实测**（`audit\` + `sent_reach.py`）：
* 进入 `[0x21AD20,0x21ADD8)` 的控制流 **8 条，全部来自区间内部** ⇒ **0 条外部入口 ⇒ 死代码**；
* 进入 `[0x21AD10,0x21AD20)` 的 **5 条 `jal`**（DrawString `0x219BD8`、`0x21CD88`、cave `0x4171A0`/`0x4171B8`/`0x417570`）全部走 trampoline；
* 进入 `[0x219C40,0x219C48)` 的只有 `0x219C18 beq $a1,0x00B1` ⇒ 第 4 处**惰性**。

**⇒ 三条对既有文档的更正/收口：**
1. 本文 §1.2(a)「DrawString 里对 0xB1/0xB5 的硬编码立即数有 **8** 处…`0x219C40`」——**地址对，定性错**：
   `0x219C40` 的 `0xFFB5` 是「0xB1 分支进入后必不成立」的**分流假条件**，不是漏改的比较。
   `docs\PATCH_INVENTORY.md` 只列 7 处**是对的**；§6-C2「SENT_02 只关了 8 处，第 5 张盘再加 CharWidth 2 处」
   里「8 处」这个数字应改为「7 处有效 + 1 处惰性」。
2. 本文 §6-C2「`CharWidth`（0x21AD38/0x21AD4C）对 0xB1/0xB5 硬编码返回 20…SENT_02 没有动它」
   ——**在原盘（CVAR_04）上完全成立**（这 2 处是活代码，已由 `SENT_05` 补上）；
   但在 **ZH113b 上这 2 处是死代码**，真正活着的是 cave `0x416F5C/0x416F68`，且**已被高字节分流保护**。
3. **⇒ 在真实汉化盘上，「汉字 trail 撞 0xB1/0xB5 特判」这条链在代码侧基本不通**
   （对偶码高字节≠0 ⇒ 分流）。这与"ZH113b 仍卡死"合起来读，说明：
   **要么元凶不是代码侧特判（那 SENT_06 也无救），要么元凶在汉化自己新加的代码路径里**
   （cave 版 CharWidth / 解码器 / 拦截器），而不是原盘那 10 个立即数。

## S5.6 ★ 为什么 `0x5117CC/0x5117DC` 不是「文本字节」消费者（本轮新增的排除性证据）

```
0x511730  函数入口
0x51174C  lhu  $a2, 8($a1)        ← ★ 键值 = 结构体 +8 的 **16 位** 字段
0x511758..0x5117DC  一长串 `addiu $v1,zero,CODE` + `beq $a2,$v1,→`
          CODE ∈ {0x2A,0xC5,0xC7,0xC4,0xC3,0xC2,0xB4,0xB2,0xD1,0xCA,0xC9,0xB0,
                  0xCE,0xB3,0xB1,0xAF,0xB5}
                    ↑ 其中 0xB1/0xB5 就是那两个"可疑"的比较

0x126A20(x):                      ← 谁写这个 +8 字段？
0x126A30  pcpyld $s1,$a0,$zero
0x126A38  jal 0x127340            （取管理器）
0x126A44  jal 0x126620            （构造）
0x126A4C  sh $s1, 8($s0)          ← ★ 把 16 位实参存进 +8
```
**650 个 `jal 0x126A20` 调用点的实参来源直方图**（`audit\F_tokprobe.txt`）：

| a0 来源 | 个数 |
|---|---|
| `addiu a0,zero,imm`（编译期常量；取值遍布 4,7,0x13,0x1B,0x28,0x52,0x64,0x65,0x7F,0x82,0x85,0x88,0x8A,0xAA,0xAF,0xB1…0x238） | **345** |
| 未在本窗口内识别出定义（多为 `pcpyld`/跨块） | 284 |
| `lw` 出来的指针/对象 | 20 |
| **`lb` 出来的字节** | **1**（`0x19B398 lb $a0,51($v1)`，且紧跟 `bne $a0,zero` 的"非空"判断——**来自结构体，不是文本**） |

⇒ 这些 0xB1/0xB5 是**事件/资源码**，不是从文本里读出来的字节。
**旁证**：`VA 0x57C3E8` 那张 8 字节码表（§S5.3）里就列着 `0x13,0x14,0x21,0x22,0x2A,0xAF,0xB0,0xB1,0xB5,0xFB,0xE6,0xE5`
——正是这套"码"的**全集**，与 0x511730 的 case 表、0x5121EC 的遍历表 **三处互证**。
⇒ 结论：**它不是文本字节的消费者**；本批**不改**。
> `work\builds\GR_HASHR\audit\impl_5117.txt` 也单独反汇编过这段（说明另一条线也在看它）；
> 本附录给出的是**判定它是"码而非字节"的实参分布证据**。

## S5.7 ★ 与 `GR_HASHR*`（`98db5f8b` 那条线）的关系：谁更便宜、谁作主

`work\builds\GR_HASHR\`（**只读其产出**）在做的是**编码侧/数据侧重排**：
`hashr_build.py --mode k2` ⇒ `GR_HASHR2400.iso`（sha256 `c9986ad294a2aa94a95b47b0f294b5303d13642c8f53adfa619f6a22f9ba5582`，
基底 `GR_FA2400_K2.iso`）：把 charset 里 **trail ∈ {0xB1,0xB5} 的 50 个对偶槽**注销
（**42 个真字搬家** + 8 个占位字注销），字形**逐 texel** 搬到新槽，3 个中文容器 **738 处**文本就地 2 换 2；
独立终检 `[V1]/[V2]/[V2b]/[V3]` + `[A1..A9]` 全过（`audit\verify.txt`）。

| 维度 | **代码侧**（本附录 `SENT_05/06`） | **编码侧**（`GR_HASHR2400`） |
|---|---|---|
| 改多少字节 | `SENT_05` **10 B** / `SENT_06` **21 B** | 42 个 16×16 4bpp 格（≈5.4 KB 像素）+ charset 50 条 + 文本 738 处（454 个区间）+ 图集重压 |
| 碰不碰数据 | **不碰**（文本/图集/容器一字不动） | 碰 charset + 图集 + 3 个容器 |
| 容量代价 | **0**（不占任何码位/格位） | 需要 42 个空闲槽（本轮用"保留段自低位压缩让出"，已过闸；`gate 0xBA ⇒ 2350 槽`） |
| 风险面 | 改的是**引擎代码**（汉化已在这片区域有 trampoline/cave，补丁空间要小心） | 改的是**数据**（有 `[V2] 逐条解码不变` 与 `[A6] 逐 texel` 兜底） |
| 覆盖面 | 关掉图标特判 ⇒ 所有容器/所有界面一起生效 | 同理（数据层一次改完） |
| 实测状态 | **未跑**（判据在用户手上） | 已建成 + 独立终检通过，**同样未跑实机** |
| 原盘上已验证的前置 | `SENT_01`（数据侧）**不卡** ✓ / `SENT_02`（代码侧 8 B）**仍卡** ✗ | — |

**判定规则（照你定的口径，本附录只把"读哪张盘"钉死）：**

| 观测 | 结论 | 修复取谁 |
|---|---|---|
| **`SENT_05` 不卡**（而 `SENT_02` 卡） | ★★ 元凶 = **`CharWidth` 的硬编码字距 20**；代码侧 **10 字节**即可修 | **代码侧作主**；`GR_HASHR2400` 降为「洁癖修复」（可选、优先级最低） |
| **`SENT_05` 仍卡** | ★★ **原盘代码侧的 10 个字节全部不是元凶** ⇒ 代码侧在 CVAR_04 上**被排除** | 转 **`SENT_06`** 判"真盘上还有没有活的可关特判" |
| **`SENT_06` 不卡**（而 `GR_ZH113b` 卡） | ★★ 真盘上"活着的 9 处"里有元凶 ⇒ **代码侧修法在真盘上可行**，且**不需重排 charset、不占容量** | **代码侧作主**（比 `GR_HASHR2400` 便宜约 3 个数量级） |
| **`SENT_06` 仍卡** | ★★ **代码侧无解**（真盘上 12 处全关仍卡） | **以 `GR_HASHR2400`（编码侧重排）为准**；并把注意力转向汉化自己新加的 cave/拦截器（§S5.5 更正 3） |

> **两句话版**：**便宜的是代码侧**（10~21 字节、零容量代价）；**已经做完且不依赖引擎补丁的是编码侧**
> （`GR_HASHR2400`）。**谁作主完全由 `SENT_05`/`SENT_06` 的实机读数决定**，本附录不替实机下结论。

## S5.8 未达成项 / 已知边界（如实列出）

1. **两张盘没有跑过实机**（任务书明示不需要模拟器）⇒ §S5.7 的判定表全部是**待读**。
2. **`0x5117CC/0x5117DC` 未改**（§S5.6 判为"事件码比较"）。若你要求"连它也一起关"，
   一行命令可加（写法与其余处一致，`0x240300B1→0x2403FF00` / `0x240300B5→0x2403FF00`，
   ISO `0x4A5048` / `0x4A5058`）；**代价**：事件 0xB5 的 handler 变成 no-op
   （0xB1 那一支本来就是 `→0x5120EC` 直接返回，改与不改等价）
   ⇒ **会给诊断盘引入与主题无关的行为差，故本批不改、单列登记**。
3. **`SENT_06` 里 3 处改动是"惰性/死代码"**（第 4/9/10 处）：为了「全 ELF 0xB1/0xB5 立即数残留 = 0」
   这条机检判据而一并改掉；**它们不可能改变任何行为**，解读 `SENT_06` 时按"**实际生效 9 处**"计。
4. **XML 里 8 个属性值内的哨兵**（本文 §6-C4）本轮**仍未清**：本批是代码侧盘，不涉及数据。
5. **`0xB1/0xB5` 之外是否还有别的"非常规字节"**：本轮只做了这两个字节的**全 ELF 立即数穷举**
   （`imm16 ∈ {00B1,00B5,FFB1,FFB5}`，含 `addiu/ori/andi/slti/sltiu/lui` 与分支位移/访存偏移的分类）
   与**数据表 4 字节项**普查；**没有**做"任意 16 位值 × 任意指令"的更大范围穷举。
6. **`0x21AD10` 的 5 个 `jal` 调用点里，3 个来自 cave（`0x4171A0`/`0x4171B8`/`0x417570`）**：
   这 3 处分别属于哪个汉化 cave 的哪个功能，本轮**没有逐条逆向**（只确认它们都经 trampoline）。
7. **`0x417050`（`ComputeCharTextureCoords` 的 cave）未做 0xB1/0xB5 专项检查**：
   它的单字节路径用的是 `firstchar` 减法 + `nrec` 钳位（`0x417098 sltu $v0,$a1,$v1`），
   从形态上看**不含 0xB1/0xB5 立即数**（全 ELF 普查已覆盖 ⇒ 确实没有），故未再展开。
8. **没做**"改完后在模拟器里确认图标不再出现"的静态/动态验证：本轮只保证
   "立即数永不命中"这一条可机检的判据 + 逐字回读。

## S5.9 纪律与污染登记

| 项 | 状态 |
|---|---|
| 既有 ISO | **全程只读**（`open('rb')`；无任何写入既有盘的代码路径）。基底 `CVAR_04_text.iso` 复算 sha256 = `554d3d8b…a15179` ✓、`GR_ZH113b.iso` 复算 = `ff3abd3c…8f6445` ✓，均与既有 meta/报告**逐字一致** |
| `GR_HASHR\**` | **只读**（用 Python 读 `imm_scan.txt`/`verify.txt`/`hashr_build.py`/`build.log`/`moves_table.txt`；未写入、未改动其任何文件） |
| 写入范围 | 仅 `work\builds\GR_SENT\**`（新增 `SENT_05/06.iso` + `.meta.json` + `audit\D..J` + `tools\sent_imm_census.py`/`sent_isoelf.py`/`sent_reach.py`/`sent_tokprobe.py`/`sent_build56.py`/`sent_verify56.py`/`sent_imm_stats.py`）与本文件（追加） ✅ |
| commit / 分支 / merge | **未做** ✅ |
| 模拟器 | **未跑**（起跑前与交付前各查一次 `Get-Process -Name '*pcsx2*'` = **0**；全程未启动任何实例、未读写 PCSX2 配置） |
| 磁盘 | 构建前 `Get-PSDrive C` = **26.76 GB** 可用 ⇒ 2 × 1.648 GB 可容纳；构建后仍在 20 GB 以上 |
| **纪律偏差** | **无**。未使用 `Select-Object -First N`（截断一律重定向到文件 + `Get-Content`/read）。构建过程中修过 **2 个本轮自己的脚本 bug**：① `sent_imm_census.py` 把 ISO 里 ELF 头的偏移当成了 VA 基址（正确关系是 `ISO(VA) = ELF头偏移 + PT_LOAD.off + (VA − PT_LOAD.va)`，两者差 **0x80**）；② `sent_isoelf.py` 同源 bug 曾让一份反汇编整体错位 0x80。**两处都改成「由 PT_LOAD 推出映射 + 自检 = −0x6C780」，并把受影响的读法全部重跑**（`audit\D_*`、`G_*`、`I_*` 都是修好之后的产物；错位那份已覆盖不留档）。**教训已写进脚本注释**，防后来者复踩 |
| 并发工作区（非本任务所为，登记以免误判） | 交付时 `work\builds\GR_HASHR\GR_HASHR2400.iso`（23:29）与 `font_*` 目录仍在增长 ⇒ 工作区里有其它执行者在并发工作。本任务**只写** `work\builds\GR_SENT\**` 与本文件，并以**只读**方式引用 `GR_HASHR` 的产出（§S5.7 的读数取的是 23:32 前后的快照） |

## S5.10 本附录产物索引

| 路径 | 内容 |
|---|---|
| `work\builds\GR_SENT\SENT_05_icon_all_off.iso` / `.meta.json` | ★ 10 处逐字节清单（VA/ISO/原/新/角色/可达性）+ sha256 + 自检 |
| `work\builds\GR_SENT\SENT_06_icon_all_off_zh113b.iso` / `.meta.json` | ★ 12 处逐字节清单 + gate 未动自检 + trampoline 结构自检 |
| `work\builds\GR_SENT\summary_sent56.json` | 两张盘一览 |
| `work\builds\GR_SENT\audit\I_verify56.txt` | ★ **独立终检**（全 ELF 再普查集合对比 + 跨盘 diff + gate 回读；全 ✅） |
| `work\builds\GR_SENT\audit\D_imm_census_orig.txt/.json` | 原盘全 ELF 立即数普查（180 处逐条） |
| `work\builds\GR_SENT\audit\D_imm_census_zh113b.txt/.json` | ZH113b 全 ELF 立即数普查（186 处逐条） |
| `work\builds\GR_SENT\audit\J_imm_stats.txt` | 分类汇总（opcode/kind/14 处其它/1 处 ori/4 处 gate） |
| `work\builds\GR_SENT\audit\E_other_sites_ctx_orig.txt` | 14 处「其它常量」+ 3 处指针偏移的上下文反汇编 |
| `work\builds\GR_SENT\audit\E5_data_region.txt` | 38 处 `word == 0x000000B1/B5` 的原始字节取证（码表 / 资源描述表） |
| `work\builds\GR_SENT\audit\F_tokprobe.txt` | 650 个 `jal 0x126A20` 的实参来源直方图（判定 0x5117xx 的关键证据） |
| `work\builds\GR_SENT\audit\G_zh113b_disasm.txt` | ZH113b：DrawString 序言/主体、CharWidth trampoline + 本体、解码器 cave、CharWidth cave 全文 |
| `work\builds\GR_SENT\audit\H_build56.log` | 建盘日志 |
| `work\builds\GR_SENT\tools\sent_imm_census.py` / `sent_isoelf.py` / `sent_reach.py` / `sent_tokprobe.py` / `sent_build56.py` / `sent_verify56.py` / `sent_imm_stats.py` | 本轮全部脚本（既有 ISO 只读） |
