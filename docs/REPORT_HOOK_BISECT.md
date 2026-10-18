# REPORT_HOOK_BISECT.md — 「钩子二分」：文字链钩子按运行时机分组 + 5 张打靶盘 + CVAR_04 同源性判定

> 执行者 = 汉化执行者（钩子二分打靶子代理）· 2026-10-16
> 仓库根 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> **只读**：`GR_ZH113b.iso`、`GR_CVAR\**`、`GR_AB\**`、`GR_HUGE\**`、`GR_EN_ORIG.iso`、
> `third_party\orig\ps2\**`、PCSX2 配置 —— **一字未改**；未跑模拟器（判据在用户手上）。
> 写入范围仅：`work\builds\GR_HOOK\**`、`docs\REPORT_HOOK_BISECT.md`、`docs\AB_TEST_GUIDE.md`（追加一节）。
> 未 commit / 未切分支 / 未 merge。**未使用 `Select-Object -First N`。**

---

## 0. 一页结论

```
① 任务书的"35 处文字链改动"与本仓库既有报告的归并口径对不上。按 docs\REPORT_NULLDEREF_ZH113b.md §3.5
   的同一张函数表逐条相加，除 13 处 cave 体 + 4 处 strlwr/strupr + 6 处字符串外，
   "每帧都跑的中文文字/字体/UI 渲染链"实际是 **45 处**（不是 35）。
   相对基底 GR_ZH113b（不是 ZH113b_fix）精确重算后，ELF 差异 = **412 run / 1 850 B / 67 站点**：
       G1 更新/重绘 13 处 · G2 测量/排版 10 处 · G3 字形取址/绘制 14 处 · G4 其它 12 处
       = **49 处**（其中 48 处是代码指令，1 处 `kBtnExplanationMapMax` 是数据常量）
       ； CAVE 体 12 处 · ELF 内字符串 6 处。
   ⇒ 本报告的"文字链钩子"= **49 处**，并把它作为 HK_01 的回退集合（宁可多退，也不漏退）。

② ★★ 找到一条**真实的、每次调用都发生的被调用者保存寄存器（$fp/$s8）违例**，就在
   G3 的 DrawString 序言拦截器上：
       0x219A74  EN `sd ra,160(sp)`  →  ZH `j 0x565930`（拦截器）
       0x219A78  EN `sq fp,144(sp)`  →  ZH 上**永不执行**（拦截器 `j 0x219A7C`，跳过这一条）
       0x219DC4  `lq fp,144(sp)`     →  ZH 上**每次都执行**
   ⇒ 每次 `RSFontMgr::DrawString` 返回时，`$fp` 被从"本次调用从未初始化过的栈槽 sp+144"重新载入。
   **形态 = 任务书要的"只恢复不保存"分支**。（`hk_dump.txt`、`hk_fplive.md` 有完整取证链。）
   但**受害面比预期窄**：对全部 66 个 `jal` 调用点（分布在 20 个符号里；另有 2 处内部 `j` 重定向）做线性存活扫描后，全 ELF 只有 **1 个**符号
   在 DrawString 调用后仍读 `$fp` —— `LoadingLoagoThread`（读盘进度循环，把 `$fp` 当计数器：
   `addiu fp,fp,1` / `sltiu at,fp,40`）。**开火 / L1 / 队伍选择三条触发路径上，静态**没有**
   这条 fp 违例的受害者** ⇒ 它**不是**（至少不是全部）卡死的解释。

③ 用户假设的第二条通道（cave 借用调用者帧）里，**最可疑的站点换人了**：
   `GetActorNameAbbreviated` 的 cave（`0x5657C8..`, 站点 #42，G4）把
   `lhu a1,2(t0)`（★ 应为 `0(t0)`）当长度 → 交给 `0x565760` → 返回的长度作为
   `jal 0x53E2B0(dst=sp+56, src=s0+68, n=v0)` 的**拷贝字节数**，而该函数的帧只有 **80 字节**
   （`addiu sp,sp,-80`；缓冲在 sp+56 ⇒ 只有 24 B 余量）。
   **长度取自对象 +2 的 padding ⇒ 一旦该半字非 0，拷贝就会越过调用者帧尾。**
   ⇒ 这才是本盘上"钩子写坏调用者栈"的**头号静态候选**，且它正好落在
   **队伍选择 / 士兵名缩写**这条用户实测触发路径上。
   （旁证：汉化自己发布的 `GR_ZH113b_fix` 把这一条**恰好修了 1 个字节** —— `2(t0)` → `0(t0)`，
     说明作者已经踩到过它。）

④ CVAR_04 与汉化盘**不是同一个 bug**（不同源），依据是 6 项可复核的指纹差异（§2）。
   但"共同上游写坏者"**没有被排除**：两份 ELF 不同 ⇒ 同一个写坏者可以在两份盘上砸到不同受害者。
   ⇒ **HK_01 同时是这两件事的判据**（§4.3）。

⑤ 已交付 5 张盘（HK_01..HK_05，HK_00 按要求只写指路，不占 1.6 GB），全部独立复核通过（§3）。
```

---

## 1. A. 文字链钩子按**运行时机**分组（静态，只读）

### 1.1 口径与自证

| 项 | 值 | 自证 |
|---|---|---|
| ELF | `/SLUS_206.13;1` @ ISO LBA **295**（ISO 0x93800） | `nh_lib` ISO9660 目录记录 |
| `FILE = VA − ` | **`0xFFF80`** | `PH[0] off=0x80 vaddr=0x100000 filesz=0x4DED00` |
| `ISO = VA − ` | **`0x6C780`** | `0x93800 + 0xFFF80` |
| 差异口径 | `GR_EN_ORIG.iso` vs **`GR_ZH113b.iso`**（打靶基底） | `hk_sites.py` |
| 精确差异 | **412 run / 1 850 B** | 逐字节 |
| 归并（间距 ≤ 4 B） | **67 处 / 覆盖 2 398 B** | 与 `GR_AB\evidence\A_suspicious_offsets.md` §1 的"67 处"一致 |

> 既有报告的"68 处"是相对 `GR_ZH113b_fix`；`ZH113b` 与 `_fix` 只差 1 字节
> （`FILE 0x465860 VA 0x5657E0`），该处被并进相邻 run ⇒ 基底上是 67 处。本报告统一用 **67 / 49**。

命令：
```powershell
python work\builds\GR_HOOK\tools\hk_sites.py     # → evidence\hk_sites.md / .json
```

### 1.2 分组表（按**文本生命周期中的位置**，不按地址顺序）

| 组 | 时机 | 站点 | 字节 | 函数 | 做什么 |
|---|---|---|---|---|---|
| **G1** | **更新 / 重绘路径**（每帧、每次文本内容变化都走） | **13** | 70 | `DrawText__10IkeButton3Fv`、`DrawText__15IkeKeyMapButtonFv`、`DrawText__13IkeBaseButtonFv`、`SetText__6RSHTMLF`、`SetText__15RSTextComponent`、`DrawTheString__15RSTextComponent`、`DisplayMessages__11ChatDisplay`、`DrawNN__14NewPS2Shortcut`、`AddOneWord__9RSFontMgr`×2、`Flush__9RSFontMgr`、`Draw__9RSFontMgr`、`ReadResource__15RSTextComponent` | 3 个 `DrawText` 改**行距常量**；2 个 `SetText`、`DrawTheString`、`ReadResource`、`DrawText_IkeBaseButton` 把**原指令换成 `j/jal` 到 cave**；`AddOneWord`/`Flush`/`Draw` 各 1 字节把 `SetLinearSampling(pkt, 1)` 改成 `0`；`DisplayMessages` 改浮点常量 `0x3F80(+1.0f)`→`0xBFC0(-1.5f)`；`DrawNN` 20 B 指令重排 |
| **G2** | **测量 / 排版路径**（决定下一步画在哪、要不要换行） | **10** | 44 | `StringWidth__6RSFontCFPCc`×2、`CharWidth__6RSFontCFc`、`DoWordWrap__15RSTextComponent`×3、`ComputeDrawXY__15RSTextComponent`×4 | `StringWidth+0x74` `jal CharWidth`→`j 0x417150`；`+0x90` `lw v0,24(s3)`→`j 0x565670`；`CharWidth+0x8` 整对换成 `j 0x416F40`；`ComputeDrawXY` 3 处 `j`/`jal` 到 s_Pool 与 sceDread cave、1 处 `j 0x411690`；`DoWordWrap+0x160` `addiu a0,sp,248`→`j 0x417500` + `lw a0,252(sp)` |
| **G3** | **字形取址 / 绘制路径**（含 DrawString 序言拦截器） | **14** | 55 | `DrawString__9RSFontMgr`**×12**、`DrawLetters__12IkeFontTable`、`ComputeCharTextureCoords__6RSFont` | `DrawString+0x4` 序言第 2 条换成 `j 0x565930`（**拦截器**）；`+0x6C` 换成 `j 0x417200`；`+0x15C` DBCS 解码 `jal 0x40BFC8`→`jal 0x416ED0` + 缓冲 sp+223→sp+222 + `lb`→`lhu`；`+0x174`/`+0x230` 读 sp+222；6 处图标码立即数 `-75/-79`→`181/177`；`+0x33C` `nop;addiu s0,s0,1`→`lbu v0,221(sp);addu s0,s0,v0`（变长步进）；`ComputeCharTextureCoords+0x0` 函数入口换成 `j 0x417050`；`DrawLetters+0xB8` `addiu a3,s1,3`→`+5` |
| **G4** | **其它** | **12** | 69 | `GetUISoldierAbbreviateName__Fii`、`GetActorNameAbbreviated__9ActorFileCFv`、`kShortcutDefaultSC__FUii`×4、`SetLinearSampling__8UIPacketFb`、`kBtnExplanationMapMax`、`strlwr`×2、`strupr`×2 | 两个"名字缩写"函数各把 1 条 `addiu a0,sp,N` 换成 `j` 到 s_Pool cave；`kShortcutDefaultSC` 4 处浮点常量；`SetLinearSampling+0x8` 1 条 `beq`→`nop`；`kBtnExplanationMapMax` 数据常量 `0x4352`→`0x4349`；`strlwr`/`strupr` 各把有符号表索引换成 `sltiu …,128` 无符号守卫 |
| **CAVE** | **代码体**（被上面各组的 `j/jal` 调用；不属于"时机"） | 12 | 1 994 | `sceRemove`、`sceMkdir`、`sceDopen`、`sceDclose`、`sceFormat`×2、`sceIpuInit` + `s_Pool`×5 | DBCS 解码器 / `CharWidth` 替换体 / `ComputeCharTextureCoords` 替换体 / `StringWidth` 替换体 / `DrawString` 尾段 / `DoWordWrap` 软换行循环 / `SetText` 替换体 / DrawString 序言拦截器 / `ComputeDrawXY` helper / 名字缩写 helper |
| **STR** | **ELF 内字符串表（数据，非钩子）** | 6 | 166 | `@5689 @5690 @5694 @5695 @5696 @5698` | 法/德/意/西/英 loading 文案 → 中文；**仍有 47 个活引用** |

逐站点全表（VA / ISO / 原指令 / 汉化指令 / 栈-ABI 标记）见 `work\builds\GR_HOOK\evidence\hk_sites.md`。

### 1.3 ★ 逐条判定：这处改动**是否动到调用者的栈帧 / 寄存器保存约定**

判定口径：把站点涉及的 4 字节指令逐条解码，标出
`SPREL`（以 `sp` 为基址的内存访问）、`SPADDR`（`addiu rX,sp,N`）、`SPADJ`（`addiu sp,sp,±N`）、
`SAVE_RESTORE`（`sq/lq/sd/ld/swc1/lwc1` 且对象是 `s0..s7/fp/ra`）、`REDIRECT`（`j/jal`）、`JR`。
**"动到调用者栈"= 该指令访问的 `sp` 不属于本函数自己的帧，或改写了被调用者保存寄存器。**

| 组 | 站点 | 触到栈/ABI？ | 判定与依据 |
|---|---|---|---|
| G1 | 3× `DrawText` 行距常量 | 否 | 纯 `subu v0,v1,v0` → `addiu v0,v1,-N`，只碰 `v0/v1` |
| G1 | `SetText__6RSHTMLF+0x18`、`SetText__15RSTextComponent+0x18`、`ReadResource+0x68`、`DrawText_IkeBaseButton+0x110`、`DrawTheString+0x164` | **是（REDIRECT）** | 把 1~2 条原指令换成 `j/jal` 到 cave。原指令含 `sw v0,248(s0)`、`lbu v1,264(s0)`、`lw a2,168(s1)` —— 都是**对象字段访问**（不是 `sp`）。cave 落点 / 返回点见 §1.4：**自洽**（`SetText`→`j 0x417680`→`j 0x21BD70`；`ReadResource`→`j 0x417650`→`j 0x21C050`；`DrawText_IkeBaseButton`→`j 0x565A00`→`jr at` 回 `0x21D954`） |
| G1 | `AddOneWord`×2、`Flush`、`Draw` 各 1 B | 否 | `addiu a1,zero,1`→`0`，只改传给 `SetLinearSampling` 的实参 |
| G1 | `DisplayMessages+0x518` | 否 | `lui v0,0x3F80`→`0xBFC0`（浮点常量） |
| G1 | `DrawNN+0x8A4` 20 B | 否 | 指令重排：`jal 0x21ACD0` 被 `lui/mtc1` 取代；**不碰 `sp`、不碰 `s*`/`ra`**。注意它**删掉了一次调用**，`ra` 不会被写，控制流不变 |
| G2 | `StringWidth+0x74`、`+0x90`、`CharWidth+0x8`、`ComputeDrawXY+0x30`/`+0x110`/`+0x1E8`、`DoWordWrap+0x160` | **是（REDIRECT / SPADDR/SPREL）** | `CharWidth+0x8` 把 `lbu v0,36(a0); beq` **整对**换成 `j 0x416F40; nop` ⇒ **原函数被整体托管给 cave**；`DoWordWrap+0x160` 把 `addiu a0,sp,248`（取**本帧**地址）换成 `lw a0,252(sp)`（取**本帧**里存的对象指针）—— 这是 67 处里**唯一**"栈地址→栈槽取值"的语义改动（既有报告 S2，判 D）。**两者都不越出本函数自己的帧**（`DoWordWrap` 帧 936 B，sp+248/252 在帧内） |
| G2 | `ComputeDrawXY+0x108` 1 B、`DoWordWrap+0x1C4`/`+0x2BC` | 否 | 立即数 / 寄存器换名（`a3,s6`→`a3,s2`）/ 删 1 条 `addiu v0,v0,1` |
| **G3** | **`DrawString+0x4`（站点 #3）** | **★★ 是 —— 写坏调用者寄存器** | 见 §1.4。**这是全 67 处里唯一一处被证实的"保存/恢复不成对"** |
| G3 | `DrawString+0x15C` / `+0x174` / `+0x230` / `+0x33C` | 否 | 全部在 **DrawString 自己的 224 B 帧**内：sp+221/222/223 三个相邻槽。cave 在 `0x416F34 sb v0,-1(a0)` 写长度到 sp+221，读侧 `lbu v0,221(sp)` 与之一致（既有报告 §3.2 已证） |
| G3 | `DrawString` 6 处图标码立即数 | 否 | `addiu v1,zero,-75`→`181`：低 8 位同为 `0xB5`，是**符号扩展→零扩展的修正** |
| G3 | `ComputeCharTextureCoords+0x0`（站点 #22） | **是（REDIRECT）** | **函数入口**两条指令换成 `j 0x417050; nop`。原指令 `lw t2,40(a0)` 是**对象字段**访问，不碰 `sp`。cave 以 `jr ra` 返回 ⇒ 调用者无感 ⇒ **ABI 自洽** |
| G3 | `DrawLetters+0xB8` | 否 | `addiu a3,s1,3`→`+5`，改传给 `DrawString` 的 Y 偏移 |
| **G4** | **`GetActorNameAbbreviated+0x24`（站点 #42）** | **★★ 是 —— 可能写坏调用者栈帧** | 见 §1.5。cave 用**调用者帧**的 sp+48/56；`lhu a1,2(t0)` 让拷贝长度失控 |
| G4 | `GetUISoldierAbbreviateName+0x120`（站点 #41） | **是（借用调用者帧，但自洽）** | cave 用 sp+112/116/120/136 —— 与 EN 被替换的 `addiu a0,sp,136` **同槽**，且 sp+112 是 EN 就有的输出结构。cave 在 sp+136 上构造 `RSUIString` 并调 `operator=`(`0x541CA0`)/`~RSUIString`(`0x541E90`)，**对象大小未知 ⇒ 是否越过帧尾未达成**（帧 160 B，sp+136 起仅 24 B） |
| G4 | `kShortcutDefaultSC`×4、`SetLinearSampling+0x8`、`kBtnExplanationMapMax` | 否 | 浮点常量 / `beq`→`nop` / 数据字节 |
| G4 | `strlwr`/`strupr`×4 | 否 | 只在 `a1/a3/t0/v1` 上加 `sltiu …,128` 守卫；**不改栈**（既有报告 S6/S7 判"逐指令等价"，本次复核同意） |
| CAVE | 12 处 | **是（覆盖了带栈帧的真函数）** | `sceRemove`(360 B)/`sceMkdir`(236)/`sceFormat`(147)/`sceDopen`(192)/`sceDclose`(232) 的**函数体被整段覆盖**；EN 侧这些函数有自己的 `addiu sp,sp,-N`/`sd ra`/`jr ra`。**但它们的直接调用者在英文原盘上 = 0**（`GR_AB\evidence\C_cave_xref.md` §C.1）⇒ 覆盖真代码**不构成风险**；`sceIpuInit` cave 与 `s_Pool` cave 落在原盘**全零真空**。**结论：cave 选址不是栈风险源** |
| STR | 6 处 | 否 | 纯数据；中文串更短 ⇒ 无溢写 |

**汇总：67 处里只有 1 处被证实"改坏了被调用者保存约定"（G3 站点 #3），
另有 2 处"借用调用者帧"（G4 站点 #41/#42）与 1 处"栈地址→栈槽取值"（G2 站点 #30）。**

### 1.4 ★★ 站点 #3：`DrawString` 序言拦截器 —— "只恢复不保存"

取证链（`evidence\hk_dump.txt`，EN/ZH 逐条对照；`evidence\hk_fp.txt` 复核指令原码）：

```
0x219A70  addiu sp,sp,-224       EN=ZH  ；帧分配，两盘都执行
0x219A74  EN  FFBF00A0  sd ra,160(sp)
          ZH  0815964C  j 0x565930          ← 站点 #3，序言第 2 条被换成拦截器
0x219A78  EN  7FBE0090  sq fp,144(sp)       ← ★ ZH 上**永不执行**
0x219A7C  7FB70080      sq s7,128(sp)       ← 拦截器 `j 0x219A7C` 的落点（跳过了 0x219A78）
   ...
0x219DC0  DFBF00A0      ld ra,160(sp)       ← 尾声
0x219DC4  7BBE0090      lq fp,144(sp)       ← ★ ZH 上**每次调用都执行**
0x219DC8..              lq s7/s6/s5/s4/s3/s2/s1/s0, ...
0x219DF8  03E00008      jr ra
0x219DFC  27BD00E0      addiu sp,sp,224
```

拦截器 `0x565930..0x5659A4`（`s_Pool` 真空内新增，44 条）：

```
0x565930  sw t0,16(sp) / sw t1,20(sp) / sw t2,24(sp) / sw v0,28(sp)   ; 保存 scratch 到**新帧**
0x565940  lui t0,0x2C ; addiu t0,t0,-32000 ; subu t0,ra,t0
0x56594C  sltiu v0,t0,12736 ; beq v0,zero,0x565990                   ; 只看"调用者是否在预期区间"
0x565958  addu t1,a1,zero ; <扫描 a1 指向的串找 >= 0xA1 的字节>       ; 结果 t1 **未被使用**
0x56597C  swc1 f0,32(sp) ; ... ; lwc1 f0,32(sp)                       ; f0 存了又原样取回
0x565990  lw t0,16(sp) / lw t1,20(sp) / lw t2,24(sp) / lw v0,28(sp)   ; 读回 scratch
0x5659A0  sd ra,160(sp)                                              ; ★ 补做被替换掉的 sd ra
0x5659A4  j 0x219A7C                                                 ; ★ 落到 0x219A7C ⇒ 跳过 0x219A78
```

**判定：**

| 问题 | 结论 | 依据 |
|---|---|---|
| 保存了哪些寄存器？ | 只保存 `t0/t1/t2/v0`（全是**调用者保存**的临时寄存器）+ 临时用一下 `f0` | 指令表 |
| 恢复路径唯一吗？ | 唯一：`0x565990..0x56599C` 读回，之后无条件 `j 0x219A7C` | 拦截器内无分支绕过读回 |
| 是否存在"只保存不恢复 / 只恢复不保存"？ | **★ 存在，形态是"恢复保留、保存被跳过"**：`sq fp,144(sp)` 被 `j 0x219A7C` 跳过，而 `lq fp,144(sp)` 在尾声无条件执行 | `hk_dump.txt` 的 ZH 栈帧表：`DrawString` 全函数（size 912）内 `sp+144` 只有 **写 1 条 @0x219A78 / 读 1 条 @0x219DC4**；而 `0x219A78` 不可达 |
| 后果 | 每次 `RSFontMgr::DrawString` 返回，`$fp`(=$s8，被调用者保存寄存器) ← `*(u128*)(sp+144)` = `sp_调用者 − 80` 处的陈旧栈数据 | 同上 |
| 拦截器写 `sp+16..31` / `sp+32` 会踩到什么？ | **不会**：`sp` 已由 `0x219A70` 减 224，写的是**自己的**新帧；且 `lw` 读回发生在 `0x219A7C` 的 `sq s7,128`/`sq s0,16` 之前 ⇒ 顺序正确 | 帧表 |
| 拦截器的串扫描 | 用 `t1` 副本扫 `a1`，**不改 `a1`**；但**没有长度上界**（只到 `\0`）⇒ 若 `a1` 不是 NUL 结尾就是**读越界**（读，不是写） | 指令表 |
| 这段扫描有用吗？ | **看起来是死代码**：`t1` 结果从未被使用，`f0` 存了又原样取回 ⇒ 该分支只消耗时间 | 指令表 |

**受害者面（`evidence\hk_fplive.md`）**：对 **66 个** `jal` 调用点
（分布在 **20 个**符号里；另有 2 处内部 `j` 重定向 —— `0x219A74`→`0x565930`、`0x21C624`→`0x565900`），
按"自最近一次写 `$fp` 以来调用过 `0x219A70`/`0x219EB0`"为污染条件做线性存活扫描，
**全 ELF 只有 1 个符号**在污染后仍读 `$fp`：

```
LoadingLoagoThread  0x20C0E0..0x20CA04
   0x20C7DC  addiu fp,fp,1     ← 读-改-写，$fp 当循环计数器
   0x20C870  addiu fp,fp,1
   （0x20C740 sltiu at,fp,40 —— 循环上界比较）
```

⇒ **`$fp` 违例是真的，但它的静态受害者是"读盘进度循环"，不是开火 / L1 / 队伍选择。**
（局限见 §5-未达成 1：`jalr` 虚调用目标不可知、未做 CFG 数据流、未覆盖"把 `$fp` 当值经 `jalr` 传参"的情形。）

### 1.5 ★★ 站点 #42：`GetActorNameAbbreviated` cave —— 长度读错偏移 ⇒ 可能写越调用者帧

```
调用点  0x3070B4  EN  88 00 A4 27   addiu a0,sp,56      ← 被替换的原指令
                 ZH  F2 95 15 08   j 0x5657C8

cave    0x5657C8  lw   t0,72(s0)          ; t0 = s0->[72]      (s0 = ActorFile this)
        0x5657CC  beq  t0,zero,0x565828
        0x5657D4  lw   a0,4(t0)           ; a0 = t0->[4]  = 字符数据指针
        0x5657D8  beq  a0,zero,0x565828
        0x5657E0  lhu  a1,2(t0)           ; ★★ 长度字段读在 +2（ZH113b_fix 改成 0(t0)）
        0x5657E4  jal  0x565760           ; (a0=char*, a1=len) → v0 = 去尾空格后的长度, v1 = 是否见 lead
        0x5657EC  beq  v1,zero,0x565828
        0x5657F4  addiu a0,sp,56          ; ★ 目标 = 调用者帧 sp+56
        0x5657F8  addiu a1,s0,68          ; 源
        0x5657FC  jal  0x53E2B0           ; 拷贝
        0x565800  addu a2,v0,zero         ; ← 延迟槽：n = v0 = 上面那个"长度"
        ...
        0x565828  addiu a0,sp,56 / addiu a1,s0,68 / addiu a2,zero,1 / j 0x3070BC
```

helper `0x565760` 的语义（`hk_dump.txt` 0x565760 段，逐条读出）：
`t0 = a0 + a1`（尾指针）；循环只置 `v1 = 1`（见到 `>= 0xA1` 的字节）；
`0x565794 addu v0,a1,zero` ⇒ **`v0` 就是把传入的 `a1` 原样返回**（再去掉尾空格）。**没有长度校验、没有上界。**

帧大小证据（`hk_fp.txt`）：
```
0x307090  addiu sp,sp,-80        ← GetActorNameAbbreviated 的帧只有 80 B
0x307094  sd ra,32(sp)
0x307098  sq s1,16(sp)
0x30709C  sq s0,0(sp)
```
⇒ `sp+56` 起的缓冲只有 **24 字节**余量（sp+80 就是帧尾，再往上是被调者的调用者帧）。

**判定：**
* 若 `t0+2`（`{u16 len@+0; …}` 的 padding）为 **0** ⇒ `a1=0` ⇒ helper 返回值 `v0=0`、`v1=0`
  ⇒ 走 `0x565828` 分支，`a2=1`，**只拷 1 字节，安全**（但**名字显示为空 / 1 字符**，是显示缺陷）。
* 若 `t0+2` 为**任何非 0 值**（heap 对象的 padding **不保证为 0**）⇒ `v0 = 该值`
  ⇒ `jal 0x53E2B0(dst=sp+56, src=s0+68, n=该值)`：**`n > 24` 即越过调用者帧尾**，
  写进 `sq s0,0(sp)`/`sq s1,16(sp)`/`sd ra,32(sp)` 之外、以及**调用者自己的帧**。
  ⇒ **这就是"钩子写坏调用者栈"的形态**，而且它正好在**队伍选择 / 士兵名缩写**这条用户实测触发路径上。
* **旁证（很强）**：汉化自己发布的 `GR_ZH113b_fix` 与 `GR_ZH113b` **全盘只差 1 个字节**，
  就是这一条 `95 05 00 02 lhu a1,2(t0)` → `95 05 00 00 lhu a1,0(t0)`。
  **作者已经踩到并修过它** ⇒ 这不是"理论上的风险"，是已发生的缺陷。**而本打靶基底 `GR_ZH113b` 上它仍是错的。**

> 这一条**不在任务书给的任何一组**里被点名；它属于既有报告的 **S1**（`GR_AB\evidence\A_suspicious_offsets.md` §2.1），
> 并按任务书的分组归入 **G4（其它 → 名字缩写）**，因此被 **HK_01 与 HK_05** 覆盖（HK_02/03/04 不覆盖它）。

### 1.6 其余"钩子借用调用者帧"的两处复核

| 站点 | 借用哪些调用者帧槽 | 与 EN 是否同槽 | 判定 |
|---|---|---|---|
| #41 `GetUISoldierAbbreviateName+0x120`（G4） | `sp+112`（读 `116(sp)` = 其 `+4` 字段）、`sp+120`、`sp+136`、`sp+144` | EN 被替换的正是 `addiu a0,sp,136`；EN 另有 `sp+112/120/128/144/156` | **同槽，自洽**。cave 在 sp+136 上建 `RSUIString` 并调 `operator=`/`~RSUIString`（`0x541CA0`/`0x541E90`）。帧 160 B，sp+136 起余 24 B ⇒ **`RSUIString` 是否 ≤ 24 B 未达成**（`hk_fp.txt` 帧表可复核） |
| #30 `DoWordWrap+0x160`（G2） | `sp+248`→`lw a0,252(sp)` | EN 也读 `252(sp)`（`0x21CD10 lw v0,252(sp)`） | **本帧内**，语义从"取地址"变"取值"，既有报告判 D；**不越帧** |
| #42 `GetActorNameAbbreviated+0x24`（G4） | `sp+48`、`sp+56` | EN 被替换的正是 `addiu a0,sp,56`；EN 另有 `sp+48/56/64/76` | 槽位**同槽**；风险来自 §1.5 的**拷贝长度**，不是槽位 |

---

## 2. ★ CVAR_04 与汉化盘崩溃**是否同源** —— 独立核对：**不同源**

方法：把两份 emulog 解析成事件序列，对 **PC 集合 / 故障地址形态 / 触发点 / 错误类型 / 终端形态**
逐项对比。命令与产物：
```powershell
python work\builds\GR_HOOK\tools\hk_syms.py    # → evidence\hk_pc_symbols.txt / hk_pc_events.json
```

### 2.1 六项指纹逐项对比

| 维度 | `GR_ZH113b\emulog.txt`（汉化盘） | `GR_CVAR\CVAR_04_emulog.txt`（原盘 ELF + 中文文本） | 同/异 |
|---|---|---|---|
| 规模 | TLB Miss **40** / Trap **2** / unmapped **2** / 唯一故障 PC **12** | TLB Miss **50**（打满 PCSX2 打印上限）/ Trap **0** / unmapped **0** / 唯一故障 PC **6** | 异 |
| 首次故障 | `[246.1611] pc=0x101D10 addr=0x11d46cc9 [load]` —— **很大、非 NULL、低位不齐的垃圾指针** | `[56.6988] pc=0x541038 addr=0x0 [store]` —— **字面 NULL** | 异 |
| 故障 PC 集合 | `0x0, 0x101D10, 0x101DE4, 0x101E08, 0x101E34, 0x101E6C, 0x102220, 0x1024E8, 0x114490, 0x17C57C, 0x39A3C0, 0x3CF414` | `0x102764, 0x102A30, 0x102AA4, 0x541038, 0x541CA0, 0x541EB0` | **交集 = 空集 ∅** |
| 归属函数族 | dlmalloc **`chunk_alloc`/`chunk_free`**（大块/mmapped 分支）+ **玩法/模拟对象**：`IkeRulesMgr::GetFireTeam`、`IkeSimulationMgr::GetBestAwareness`、`SimHuman::HumanDynamicCollision`、`RSVector3::operator-` | dlmalloc **`mmalloc_free`/`small_free`**（小块分支）+ **`RSUIString`（引擎 UI 字符串类）**：`Substring`、`operator=`、**`~RSUIString`**（34/50 次都是析构函数） | 异 |
| 地址形态 | 首次 `0x11d46cc1/c9/d1/d5` = 同一垃圾基址 + 小偏移的**结构/数组遍历**；随后 `addr=0x10 / 0x14`（NULL+0x10/+0x14 的 **unlink 写**，`chunk_free` 0x101DD8/0x101E34） | `addr=0x4,0x5,0x6,0x7`（**对 NULL+4 的未对齐 4 字节访问**，`mmalloc_free`/`small_free`）⇒ **`free()` 收到不在堆里的指针**；再从 `0x541EB0` 出发沿 `0xcf3f1098 → … → 0xc997e318` **等步长 0x5A72D8 的野指针链**（34 次） | 异 |
| 终端形态 | `[259.4759] Trap exception at 0x00000000` + `Jump to unmapped recLUT page (PC: 0x0cac6800)`；`[271.5423]` 同样再来一次 ⇒ **CPU 跳到 PC=0** | **没有 Trap、没有 PC 跳飞**；TLB 打印打满 50 条上限即止；用户实机看到的是 **GS 侧 `ReadFIFO_VIF1: FQC = 0` 断言** ⇒ **EE 在野指针链里空转 vs GS FIFO 停摆** | 异 |
| 时间 | 246.16 s / 259.47 s / 271.51 s（深入游戏后） | 56.70 s（很早） | 异 |

`0x102764 / 0x102A30 / 0x102AA4` 的反汇编（`hk_dump.txt`）显示它们是
`lbu v1,-4(a0)` / `lbu t0,-4(a0)` / `sll a0,t1,23` —— 即
**`mmalloc_free`/`small_free` 在检查"这个指针是不是在堆里"，而传进来的 `a0` 落在堆基址之下**（`sltu v1,a0,a1` 分支）。
**形态 = `free()` 收到了栈指针 / 静态指针 / NULL 附近的伪指针。**

### 2.2 判定

```
★ 判定：CVAR_04 与汉化盘 **不是同一个 bug（不同源）**。
   6 项指纹（PC 集合、归属函数族、首次故障形态、故障地址形态、终端形态、时间）**全部不同**，
   其中 **PC 集合交集为空集** 是最硬的一条：
   汉化盘死在"大块分配器的 bin 链 + 玩法/模拟对象"，CVAR_04 死在"UI 字符串类 + 小块分配器"。
   两盘唯一的**共同点**是"最终都在 dlmalloc 里缺页" —— 这是**受害者症状类相同**，
   不是**同一元凶**。

★ 但有一条替代假设**未被排除**，必须写清：
   两份盘的 ELF 不同（CVAR_04 = 原盘 ELF，汉化盘 = 打了 67 处补丁的 ELF）。
   若**同一个上游写坏者**（例如中文文本数据本身、或某个只依赖文本内容的越界写）在两份盘上
   都存在，它完全可能砸到**不同的受害者**（受害者取决于哪段代码先拿到被污染的内存）。
   ⇒ "不同源"从这里得到的是"**故障现场不同源**"，
     "**上游写坏者是否共同**"需要 HK_01 来判（§4.3）。
```

---

## 3. B. 5 张「钩子二分」打靶盘

### 3.1 磁盘预算（先确认）

```
PS> Get-PSDrive C | Format-List Name,Used,Free
Name : C   Used : 972803567616   Free : 26378207232     ← 26.3 GB 可用
```
5 张 × 1.6 GB ≈ 8.2 GB ⇒ 够。**HK_00 按要求不复制**（写 `HK_00_base.meta.json` 指路），
省下的额度用于 **HK_05_g4_off**，使二分**闭合**（HK_01 = HK_02∪HK_03∪HK_04∪HK_05 的补集）。

### 3.2 五张盘

| 盘 | 只回退什么 | 站点 | 回退字节 | 与基底差异 | sha256 |
|---|---|---|---|---|---|
| `HK_00_base` | **不占盘** —— 直接用 `work\builds\GR_ZH113b\GR_ZH113b.iso` | — | — | — | `ff3abd3c50e380f666955ccb6226b67198e181589c0db9b4d52e4643208f6445` |
| `HK_01_all_text_off.iso` | **G1+G2+G3+G4 = 全部 49 处指令级钩子** | 49 | 238 B | 182 B | `9d724ab0ca76ccc452c47e03e37e511b45c7372e147f93ef11302debb56aa5f9` |
| `HK_02_g1_off.iso` | G1 更新/重绘 | 13 | 70 B | 57 B | `2df6910deba3d3a78092f12c2622ca660d703284af2d3588b21877a1fc26840a` |
| `HK_03_g2_off.iso` | G2 测量/排版 | 10 | 44 B | 40 B | `08935ee05b870c72e51f17c98c5f6927991e62218a14576b93d0e7122e30f528` |
| `HK_04_g3_off.iso` | G3 字形取址/绘制（**含 DrawString 序言拦截器**） | 14 | 55 B | 39 B | `0002e3e4c8cb4efea458940733632ec3d5e8008779bb7ab84e7e3696a2bc161d` |
| `HK_05_g4_off.iso` | G4 其它（**含 `GetActorNameAbbreviated` / `GetUISoldierAbbreviateName` 两个名字缩写 cave**） | 12 | 69 B | 46 B | `a63a3827893c531de88c8675cbd1d1b3e4b5a4171c8094a57daf6648ef4ea46f` |

**每张盘都保留**：中文文本（`EN_STRINGS.RES/TXT`、`LANG`）、中文图集
（`COMMON.PAK new_font_revised` PSMT4 1024×512、`FONT.RES`）、CAVE 代码体（12 处）、
ELF 内 loading 中文串（6 处）。**没有任何一张盘动过这些。**

### 3.3 "回退"的字节级定义（可复核）

* 站点 = `EN_ORIG` vs `GR_ZH113b` 的**逐字节差异 run 按间距 ≤ 4 B 归并**后的区间。
  每个 run 本身是"**全部字节都不相同的极大连通段**"。
* 回退 = 把该区间内的字节**逐字节写成英文原盘对应字节**
  （`ISO = FILE + 0x93800`，`FILE = VA − 0xFFF80`）。
* 因为区间外两盘本来就相同，**写 EN 字节 = 精确还原原盘指令流，且不多动一个字节**。
* 区间是"字节级"而不是"指令级"：有几处站点（如 `DrawString+0x199`）只差**指令的立即数字节**，
  区间起点落在指令中间。**这不影响正确性** —— 逐字节写回后该指令与英文原盘逐字节相同。

### 3.4 自检（`hk_build.py` 内置 + `hk_verify.py` 独立复核，两次都过）

`evidence\hk_verify.md` 的每张盘都验了 6 项：

| 检查 | 结果 |
|---|---|
| 尺寸与基底相同（1 648 164 864） | ✅ 5/5 |
| 盘上 sha256 == meta 声明 | ✅ 5/5 |
| 差异字节**全部落在**声明的回退区间内（越界 = 0） | ✅ 5/5（**0 字节越界**） |
| 每个**新**字节 == 英文原盘同址字节 | ✅ 5/5（**0 个不符**） |
| 每个回退区间与英文原盘逐字节相同 | ✅ 5/5（**0 个站点不符**） |
| ELF 头（0..0x80，含 `e_phoff`/`e_phnum`）+ 2 个 PH 条目未动 | ✅ 5/5（`e_type=2 e_machine=8 e_phnum=2`） |

> 复核命令：`python work\builds\GR_HOOK\tools\hk_verify.py`
> 逐站点清单：`work\builds\GR_HOOK\evidence\hk_disc_tables.md`
> 逐字节清单：`work\builds\GR_HOOK\HK_xx*.meta.json` 的 `patch_list` / `byte_diff_runs`

### 3.5 自洽性风险（任务书要求"若判断会破坏自洽就停手"）

**本执行者判定：5 张盘都安全可跑，没有一张需要停手。** 理由：

1. **每一处回退都是把一条完整指令还原成原盘出货版本。** 不存在"半条指令"或"回退后悬空的分支"
   —— 逐字节还原后，该函数在那些地址上与出货版**逐字节相同**（§3.4 第 5 项已验）。
2. **回退后变成死代码的 cave 不会执行。** 交叉验证（`GR_AB\evidence\C_cave_xref.md` §C.2/§C.5）：
   每个 cave 入口的 `jal/j` 调用点**全部**落在被回退的 49 处之内
   （`0x416ED0←0x219BCC`、`0x416F40←0x21AD18`、`0x417050←0x21ADE0`、`0x417150←0x21AC74`、
   `0x417200←0x219ADC`、`0x417500←0x21CD70`、`0x417600←0x41765C/0x41768C/0x4176BC`、
   `0x417650←0x21C048`、`0x417680←0x21BD68`、`0x4176A0←0x21CB30`、`0x4176B0←0x21CFD8`、
   `0x565670←0x21AC90`、`0x565730←0x21CA50`、`0x565760←0x5657E4/0x56586C`、
   `0x56583C←0x2ECEC0`、`0x565900←0x21C624`、`0x565930←0x219A74`、`0x565A00←0x21D940`、
   `0x411690←0x21CC08`）。⇒ `HK_01` 上**所有 cave 都不可达**。
3. **必须接受、且必须提前告诉测试者的一件事：这些盘的中文渲染会退化。**
   回退掉 `DrawString` 的 DBCS 解码后，GBK 双字节会被当单字节走英文路径
   ⇒ **花屏 / 乱码 / 文字错位 / 行距怪异是预期现象，不是"盘坏了"。**
   判据**只有一条：卡死 / 不卡死**。
4. **一个额外好处**：回退 G3（`HK_04`）会把 `0x219A74` 的 `j 0x565930` 一并撤掉
   ⇒ **`sq fp,144(sp)` 恢复执行 ⇒ §1.4 的 `$fp` ABI 违例在 `HK_04`（和 `HK_01`）上被消除**。
   所以 `HK_04` 同时是"G3 组"和"`$fp` 违例"两张假设的判据。

---

## 4. D. 给用户的测试判定表

### 4.1 建议顺序与判据

> **前置（沿用 `docs\AB_TEST_GUIDE.md` §2 的通用前置）**：跑之前确认没有别人的模拟器实例（只等不杀）；
> 日志在运行中被独占，**必须等进程退出后再读**；每张盘至少复现到"上次卡死的那一步"。
> 复现脚本（把触发点跑一遍）：**火箭筒开火** → **按 L1 开小队/地图** → **选关后进队伍选择界面**。

| 顺序 | 盘 | 只回退了什么 | **不卡** 意味着 | **仍卡** 意味着 | 下一步二分到哪 |
|---|---|---|---|---|---|
| 0 | `HK_00_base`（= `GR_ZH113b`） | 无 | 本机复现不出 ⇒ 后面全部无区分度，先解决复现 | 复现成立（预期） | 往下走 |
| 1 | **`HK_01_all_text_off`** | 全部 49 处指令级钩子 | ★ **钩子成立**：元凶在这 49 处里（且不在 CAVE 体与 loading 串里）。**同时说明 CVAR_04 与汉化盘的上游写坏者不同源** | ★ **钩子被排除**：49 处钩子全退掉仍卡 ⇒ 元凶是**文本内容/图集/容器**（与钩子无关）。**此时请把它的指纹（TLB Miss 数、停顿 PC、终端形态）与 `CVAR_04_emulog.txt` 对照** —— 若与 CVAR_04 一致，则两盘**同源**，问题回到"中文文本数据本身" | 不卡 → 2；仍卡 → 转 `CVAR` 线的文本/图集方向（并回报指纹） |
| 2 | `HK_02_g1_off` | G1 更新/重绘 13 处 | 元凶在 G1（`DrawText`/`SetText`/`Flush`/`Draw`/`AddOneWord`/`DisplayMessages`/`DrawNN`/`ReadResource`/`DrawTheString`） | G1 无关 | 3 |
| 3 | `HK_03_g2_off` | G2 测量/排版 10 处 | 元凶在 G2（度量/换行/坐标） | G2 无关 | 4 |
| 4 | `HK_04_g3_off` | G3 字形取址/绘制 14 处（**含 `DrawString` 序言拦截器 ⇒ 同时消除 `$fp` ABI 违例**） | ★ 元凶在 G3 —— **且因为这一组唯一包含 §1.4 的 `$fp` 违例，若只有它不卡，`$fp` 违例就是最可能的原因** | G3 无关（`$fp` 违例也一并被排除） | 5 |
| 5 | `HK_05_g4_off` | G4 其它 12 处（**含 `GetActorNameAbbreviated` 的 `lhu a1,2(t0)`**） | ★ 元凶在 G4 —— **优先怀疑 `GetActorNameAbbreviated` cave 的长度错位导致越写调用者帧（§1.5）** | G4 无关 | 见 §4.2 |

### 4.2 结果组合 → 结论表（二分闭合，无遗漏）

因为 `HK_01 = G1∪G2∪G3∪G4`：

| `HK_01` | `HK_02` (G1) | `HK_03` (G2) | `HK_04` (G3) | `HK_05` (G4) | 结论 |
|---|---|---|---|---|---|
| 不卡 | 不卡 | 卡 | 卡 | 卡 | 元凶在 **G1** |
| 不卡 | 卡 | 不卡 | 卡 | 卡 | 元凶在 **G2** |
| 不卡 | 卡 | 卡 | 不卡 | 卡 | 元凶在 **G3**（**首选怀疑 `DrawString` 序言拦截器的 `$fp` 违例**） |
| 不卡 | 卡 | 卡 | 卡 | 不卡 | 元凶在 **G4**（**首选怀疑 `GetActorNameAbbreviated` cave**） |
| 不卡 | 卡 | 卡 | 卡 | 卡 | **两个以上组各自能独立触发**（或存在耦合）。按"最小改动"原则先修 G3，再修 G4；此时需要再做"只回退单站点"的细盘 |
| 不卡 | 不卡 | 不卡 | 不卡 | 不卡 | 任一组单独回退都够 ⇒ **多组各自能触发**；优先修 §1.4（G3）与 §1.5（G4）这两处已证缺陷 |
| 不卡 | 任一组不卡 | | | | 见上两行 |
| **仍卡** | 任意 | 任意 | 任意 | 任意 | **钩子不是元凶**：49 处全退（`HK_01`）仍卡 ⇒ 元凶在文本内容 / 图集 / 容器，或在 CAVE 体与 loading 串这些**没被回退**的东西里。此时**关键动作**：把 `HK_01` 的 emulog 与 `CVAR_04_emulog.txt` **逐项对照指纹**（§2.1 那张表），回报"与 CVAR_04 一致 / 不一致" |

> **注意非单调性**：回退不是"越少越安全"。若 `HK_01` 不卡而 `HK_02..HK_05` 全卡，说明
> **多组协同**才触发；若 `HK_01` 卡而某张组盘不卡，说明**回退某一组反而引入了新问题** ——
> 这两种情况都必须连 emulog 一起报。

### 4.3 `HK_01` 的第二个用途：直接判定 §2.2 遗留的"共同上游"

`HK_01` 的 ELF 在**所有代码路径上与英文原盘等价**（49 处钩子全退 + 12 处 cave 全不可达），
只保留了 6 处 loading 中文串（数据）。因此：

```
HK_01 ≈ CVAR_04 + (strlwr/strupr 的 DBCS 守卫已回退 ⇒ 也等价) + 中文 loading 串 + 中文图集
```

* 若 **`HK_01` 仍卡，且指纹与 `CVAR_04` 一致** ⇒ **"中文文本/图集"就是共同的上游写坏者**，
  汉化盘的卡死与 CVAR_04 是**同一元凶的两个受害者**（此时 §2.2 的"现场不同源"仍成立，
  但"上游同源"成立）。**这是本次二分最有价值的一个结果。**
* 若 **`HK_01` 仍卡，但指纹与 `CVAR_04` 不一致** ⇒ 还有第三个写坏者，且在 CAVE 体或 loading 串之外。

### 4.4 与既有盘的**测试优先级**（明确排序）

| 优先级 | 盘 | 理由 |
|---|---|---|
| **P0** | **`HK_01_all_text_off`** | 唯一能一刀切回答"钩子是不是元凶"的盘；同时是 §4.3 的判据。**先跑这一张。** |
| **P1** | `HK_02` / `HK_03` / `HK_04` / `HK_05` | 只在 `HK_01` 不卡时才需要；四分定位 |
| **P2** | `CVAR` 系列（`CVAR_04_text` / `CVAR_05_elf_atlas`） | 已被两轮实机跑过，结论已确立（05 不崩 / 04 崩且崩法不同）。**只在 §4.3 需要指纹对照时重跑** |
| **P3** | `AB` 系列（`AB_00..AB_04`） | `AB_01`/`AB_02` 验证的是**已被推翻**的"`sp+221` 变长步进"假设（"串长/步进"框架已不成立）；`AB_03`/`AB_04` 验证的是 FONT.RES `real` 不一致（已被 `GR_HUGE` 与 `CAPACITY_2400 §19/20/21` 否掉）。**降级为背景对照** |
| **P4（已逻辑排除，不再跑）** | **`HUGE` 系列（`HUGE_nrec224` / `HUGE_nrec224_plus_s1fix`）** | 任务书明示"HUGE 系列已被逻辑排除"。补充理由：`huge` 面 `nrec` 改动**只影响字形索引读**（读越界 ⇒ UV 错误），**不产生写**，无法解释"堆元数据被写坏 + 调用者栈被写坏"这一类**写**型损坏。**降级/关闭** |

> **注**：`HUGE_nrec224_plus_s1fix` 与本次 G4 的 §1.5 有交集（它顺手修了 S1 那 1 个字节）。
> 若用户手上只有 `HUGE` 盘可跑，`HUGE_nrec224_plus_s1fix` 的"不卡/仍卡"可以**旁证 §1.5**
> —— 但它同时改了 `nrec`，是**混淆变量**，不能单独下结论。**首选仍是 `HK_05`。**

---

## 5. C. 用户假设的静态支持 / 反驳 —— 汇总

### 5.1 "所有会写调用者栈或把 `sp` 当临时寄存器的钩子" 清单

| # | 钩子 | 保存了什么 | 恢复路径唯一？ | "只保存不恢复 / 只恢复不保存"？ | 判定 |
|---|---|---|---|---|---|
| 1 | **`DrawString` 序言拦截器** `0x565930`（G3 站点 #3） | `t0,t1,t2,v0` → **自己的新帧** sp+16..31；`f0` → sp+32（存了又原样取回） | 唯一（`0x565990..0x56599C` 读回后无条件 `j 0x219A7C`） | ★★ **有：`sq fp,144(sp)` 被 `j 0x219A7C` 永久跳过，而 `lq fp,144(sp)` 每次都执行** | **真实 ABI 违例**；受害者扫描只找到 `LoadingLoagoThread` |
| 2 | `DrawString` DBCS 解码 cave `0x416ED0`（CAVE 站点 #48） | 不保存任何寄存器；只写调用者缓冲 `sp+222..223` 与 `sp+221`（长度） | 4 条边路 + 主路**都**汇到 `0x416F34`，`jr ra` 唯一 | 无 | **自洽**（既有报告 §3.2） |
| 3 | `GetActorNameAbbreviated` cave `0x5657C8`（G4 站点 #42） | 不保存寄存器；**借调用者帧 sp+48/56** | `jr` 路径为 `j 0x307140`（原函数后续），两条分支都回到原函数 | 无（但**不检查长度上界**） | ★★ **高危**：`lhu a1,2(t0)` 长度错位 ⇒ 拷贝长度失控 ⇒ 可越写调用者帧（§1.5） |
| 4 | `GetUISoldierAbbreviateName` cave `0x56583C`（G4 站点 #41） | 不保存寄存器；借调用者帧 sp+112/116/120/136/144 | 三条 `j` 分别回 `0x2ECF4C`/`0x2ECEC8`，与原指令处的后继一致 | 无 | **同槽自洽**；`RSUIString` 对象大小未达成 |
| 5 | `DoWordWrap` cave `0x417500`（CAVE 站点 #52） | **覆盖了原 `sceDopen` 的函数体**（其中有 `addiu sp,sp,-160`/`sd ra,144(sp)`/`jr ra`）—— 但 `sceDopen` 的调用者 = **0** | cave 内部 `j 0x21CD70`/`0x21CDB8`/`0x21CDBC` 按原逻辑回到 `DoWordWrap` 对应位置 | 无（原函数不可达） | **不是风险**（死宿主） |
| 6 | `SetText`/`ReadResource`/`ComputeDrawXY` 用的 `sceDclose`/`sceDread` cave `0x417600..`（CAVE 站点 #53） | 新增了小函数序言 `addiu sp,sp,-24 / sd ra,0(sp) / sd a0,8(sp) / sd a1,16(sp)` 与 `addiu sp,sp,-8 / sd ra,0(sp)` 两个 helper | 每个 helper 都是 `jr ra` + `addiu sp,sp,N` **成对** | 无 | **自洽**。注意：**这是全 67 处里唯一"新增了完整序言/尾声对"的 cave**，逐条核对过配对 |
| 7 | `SetLinearSampling` 实参改动（G1 ×4） | 无 | — | 无 | 只改 `a1` 的值 |
| 8 | `strlwr`/`strupr`（G4） | 无 | — | 无 | 只在临时寄存器上加守卫 |

### 5.2 结合触发点：**哪一条钩子最可能在这些路径上被执行**

| 触发点 | 会经过的文字链钩子 | 组 | 最可疑的一条 |
|---|---|---|---|
| **火箭筒开火**（"唯一的 text 区别只有子弹数"） | `IkeButton::DrawText`（G1）→ `RSTextComponent::SetText`(G1) → 度量（G2：`StringWidth`/`CharWidth`）→ `DrawString`（G3，**含拦截器**）→ `AddOneWord`/`Flush`/`Draw`（G1） | G1/G2/G3 | **`DrawString` 序言拦截器（G3 #3）** —— 它是"每次文本更新都必然执行"的唯一一处已证缺陷（§1.4）。**但静态受害者里没有 HUD 路径（§5.3）** |
| **按 L1 开小队 / 地图** | `IkeKeyMapButton::DrawText`(G1) + `NewPS2Shortcut::DrawNN`(G1) + `ChatDisplay::DisplayMessages`(G1) 建议 `kShortcutDefaultSC`(G4) + 全套 G2/G3 | G1/G3/G4 | 同上；**外加 `DrawNN`（G1）删掉了一次 `jal 0x21ACD0`**（指令重排） |
| **选关后进队伍选择界面** | 除上述外，**额外**走 `GetUISoldierAbbreviateName`(G4 #41) 与 **`GetActorNameAbbreviated`(G4 #42)** | G1/G2/G3/**G4** | ★★ **`GetActorNameAbbreviated` cave（G4 #42）** —— 这是**三条触发点里唯一"队伍选择独有"**的钩子，且它正是汉化自己修过 1 字节的那一处（§1.5） |
| 读盘 / 载入 | `LoadingLoagoThread` → `DrawString`（**`$fp` 违例的真实受害者**）+ 6 处 loading 中文串 | G3 / STR | `$fp` 违例 —— **但用户没报读盘卡死**，这反过来说明 `$fp` 违例的危害可能被"计数器被改小/改大"的巧合掩盖了 |

**排序（最可疑 → 较可疑）：**

1. ★★ **`GetActorNameAbbreviated` cave 的 `lhu a1,2(t0)`（G4 站点 #42）** ——
   唯一同时满足"**是用户触发路径独有**" + "**已证有缺陷（作者自己修过）**" + "**能写越调用者栈帧**" 的一条。
2. ★ **`DrawString` 序言拦截器（G3 站点 #3）** ——
   唯一被证实的**被调用者保存寄存器违例**，每次调用都发生，与串长无关（**完全符合用户描述的"与串长无关"**）；
   但静态受害者只找到 `LoadingLoagoThread`，**与三条触发点对不上**。
3. **`DoWordWrap+0x160` 的 `lw a0,252(sp)`（G2 站点 #30）** ——
   全 67 处里**唯一**"栈地址 → 栈槽取值"的语义改动，`a0` 随即被当对象指针用（`lw t1,4(a0)`）；
   语义正确与否**静态无法判定**（既有报告判 D）。
4. `GetUISoldierAbbreviateName` cave（G4 #41）—— 同槽自洽，但 `RSUIString` 对象大小未达成。
5. 其余 45 处 —— 只改常量/实参/寄存器名，或与配套写入自洽。

### 5.3 从 `GR_ZH113b` 卡死日志的**野指针地址**反推"被写坏的是哪一类指针"

**证据（`hk_pc_symbols.txt`）：**

```
第一段 [246.1611] pc=0x101D10 addr=0x11d46cc9 [load]     chunk_free+0x0   `ld t2,8(a1)`
        [246.1612] pc=0x101DE4 addr=0x11d46cc9 [load]     chunk_free+0xD4
        [246.1614] pc=0x101E08 addr=0x11d46cd1 [load]     chunk_free+0xF8  `lw t2,16(a2)`
        [246.1615] pc=0x101E34 addr=0x10 [store]          chunk_free+0x124 `lw t1,20(a2)` → `sw t1,20(a2)`
        [246.1619] pc=0x101E34 addr=0x14 [store]          同上
        [246.1622] pc=0x101E6C addr=0x11d46cc1 [store]     chunk_free+0x15C
第二段 [259.4748] pc=0x1024E8 addr=0x11d46cc1 [store]     chunk_alloc+0x498
        [259.4750] pc=0x102220 addr=0x11d46cc1 [store] ×6  chunk_alloc+0x1D0（bin 索引）
        [259.4756] pc=0x114490 addr=0x2C/0x30/0x34 [load]  RSVector3::operator- +0x0
        [259.4758] pc=0x3CF414 addr=0x25C [load]           SimHuman::HumanDynamicCollision+0x154
        [259.4759] pc=0x0 addr=0x0 ×3 → Trap → Jump to unmapped recLUT page
第三段 [271.5228] pc=0x17C57C addr=0x3030313 [load] ×7    IkeRulesMgr::GetFireTeam+0x2C `lw v1,16(v0)`
        [271.5422] pc=0x39A3C0 addr=0x340 [load]           IkeSimulationMgr::GetBestAwareness+0x60 `lw t9,0(s6)`
        [271.5423] pc=0x0 addr=0x0 ×3 → Trap
```

**反推：**

| 观察 | 反推 |
|---|---|
| `0x11d46cc1 / c9 / d1 / d5` —— **同一个基址 + 小偏移（8/8/4）**，且基址**低位是奇数**（`…cc1`） | 不是"链路走飞"，而是**在一个"基址 + 字段偏移"的结构/数组上遍历**，而**基址本身是垃圾且未对齐**。"未对齐"是关键：**真实指针几乎总是 4 或 16 对齐**，奇地址说明这个值**不是被当作指针存进去的**，而是**被错误地"从别处搬来"或按错误宽度/偏移读出来的** —— 与 §1.5 / 既有报告 S1 的"**偏移差 1~2**"错误同型 |
| 紧接着 `addr=0x10 / 0x14`（NULL+0x10 / NULL+0x14 的 **store**） | 这是 `chunk_free` 的 **unlink**：`lw t1,20(a2); lw a2,16(a2); sw t1,20(a2); sw a2,16(t1)` —— `a2 == NULL` ⇒ **链表的 `prev`/`next` 字段已经是 NULL**。⇒ **堆块头（chunk header）的 `prev/next` 被写成 0/NULL** |
| `0x3030313` = `0x03030313`，`0x340`、`0x25C`、`0x2C/0x30/0x34` | 这些是**小整数偏移量**（不是地址），说明 `v0`/`s6`/`s4`/`a1` 这些**对象指针**是 **NULL 或极小值**。`0x03030313` 尤其可疑：`0x03/0x03/0x03/0x13` 是**非指针的字节模式**（很像从文本/表里读来的字节被当成 32 位指针） |
| `pc=0x114490 RSVector3::operator-`、`0x3CF414 SimHuman::HumanDynamicCollision`、`0x17C57C IkeRulesMgr::GetFireTeam`、`0x39A3C0 IkeSimulationMgr::GetBestAwareness` | 后面这些是**玩法/模拟对象**在读自己的字段时吃到 NULL —— **同一个"对象指针变 NULL/垃圾"的病症扩散到了不同的对象** |

```
★ 反推结论：
  被写坏的是 **两类指针**：
  ① **堆块头（dlmalloc chunk header）的 prev/next**（`+0x10`/`+0x14`）——被写成 NULL 或垃圾
     ⇒ `chunk_free` 的 unlink 直接对 NULL 写 ⇒ bin 链表断裂 ⇒ `chunk_alloc` 遍历到 NULL ⇒ 画面静止。
  ② **一批 UI/玩法对象的对象指针（很可能是栈上的局部指针，或对象内部的成员指针）** ——
     它们的值变成了 **NULL 或 `0x030303xx` 这类"非指针字节模式"**。
  ⇒ **不是单一的"堆块头被踩"，而是"指针值本身被替换成了垃圾"**。
     形态与"某处按错误的宽度/偏移读写，把数据当指针搬来搬去"一致，
     也与"栈上局部指针被覆盖"一致。**本报告 §1.4（$fp 被换成栈上的陈旧数据）与 §1.5
     （拷贝长度失控，越过 80 字节帧尾）都能产生 ② 这种"指针值被替换"的结果。**
  ★ 未达成：无法从日志唯一确定是"堆块头先坏再传染"还是"指针先坏再砸到堆"。
     两种顺序在中段日志里都能解释（`0x1024E8` 的 store 到 `0x11d46cc1` 出现在 `0x102220`
     之前，暗示**堆外那个垃圾基址先被写**）—— 这一点需要实机 dump 才能定。
```

---

## 6. 未达成项（如实登记）

1. **`$fp` 违例的完整受害者集未达成。** 我只做了"直接 `jal` 到 `0x219A70`/`0x219EB0`"的 66 个调用点的
   线性存活扫描，**没有做 CFG/数据流**，也**没有覆盖 `jalr` 虚调用**（目标不可知）
   以及"把 `$fp` 当值经 `jalr` 传参"的情形。因此"只有 `LoadingLoagoThread` 受害"是**下界**，不是等价结论。
2. **§1.5 的"`t0+2` 到底是不是 0"未达成。** `lhu a1,2(t0)` 的后果是"安全但显示为空"还是"越写帧尾"，
   取决于 `s0->[72]` 那个对象的 `+2` 半字内容（heap padding 是否恒为 0）。**静态无法判定**，需要实机 dump。
3. **`GetUISoldierAbbreviateName` cave 里 `RSUIString` 对象大小未达成**（帧 160 B，sp+136 起只剩 24 B）。
   需要 `RSUIString` 的类布局（可从 `0x541CA0`/`0x541E90`/`0x540F30` 反推，本轮未做）。
4. **`ComputeDrawXY` cave 的魔法常量 `82`（0x52）与结构偏移 `20(a0)` 语义未达成**（沿用既有报告的 S3 未达成）。
5. **CVAR_04 与汉化盘的"上游写坏者是否同一"未达成** —— 这正是 `HK_01` 要回答的（§4.3）。
   本报告只能给出"**故障现场不同源**"（6 项指纹全不同，PC 交集为空）。
6. **未跑模拟器。** 按任务书"不需要跑模拟器"，本轮**没有启动任何 PCSX2 进程**，
   因此**没有新增污染**（既有日志的采集环境见各自 README/指南的污染登记）。
7. **`docs\AB_TEST_GUIDE.md` 的"35 处"表述未回改** —— 该文件是既有交付物，
   本轮只**追加**一节（附录 B）说明口径差异（45/49 vs 35）并指向本报告，**没有改动它的既有结论**。

---

## 7. 复现命令（全部只读既有盘）

```powershell
$env:PY = "C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

# A. 站点表 + 分组 + 栈/ABI 标记  → evidence\hk_sites.md / .json
& $env:PY work\builds\GR_HOOK\tools\hk_sites.py

# A/C. 关键钩子与函数的 EN|ZH 全文反汇编 + 栈帧读写表  → evidence\hk_dump.txt
& $env:PY work\builds\GR_HOOK\tools\hk_dump.py

# C. fp 写点/读点的真实指令 + 两个名字缩写函数的全帧 sp 访问  → evidence\hk_fp.txt
& $env:PY work\builds\GR_HOOK\tools\hk_fp.py

# C. 「DrawString 调用后仍读 $fp」受害者扫描  → evidence\hk_fplive.md
& $env:PY work\builds\GR_HOOK\tools\hk_fplive.py

# C. 两份 emulog 的故障 PC → 符号 + 终端形态 + 集合对比  → evidence\hk_pc_symbols.txt
& $env:PY work\builds\GR_HOOK\tools\hk_syms.py

# B. 构建 5 张盘（源盘只读；只写 work\builds\GR_HOOK\**）
& $env:PY work\builds\GR_HOOK\tools\hk_build.py

# B. 独立复核 5 张盘  → evidence\hk_verify.md
& $env:PY work\builds\GR_HOOK\tools\hk_verify.py

# B. 逐站点回退清单  → evidence\hk_disc_tables.md
& $env:PY work\builds\GR_HOOK\tools\hk_disc_tables.py

# 磁盘余量（构建前应确认）
Get-PSDrive C | Format-List Name,Used,Free
```

## 8. 产物索引

| 路径 | 内容 |
|---|---|
| `work\builds\GR_HOOK\HK_01_all_text_off.iso` … `HK_05_g4_off.iso` | 5 张打靶盘 |
| `work\builds\GR_HOOK\HK_00_base.meta.json` | `HK_00` 指路（不占盘） |
| `work\builds\GR_HOOK\HK_xx*.meta.json` | 每张盘：逐字节差异清单、sha256、尺寸、构建命令、自检 |
| `work\builds\GR_HOOK\README.md` | 打靶盘速查 |
| `work\builds\GR_HOOK\tools\hk_lib.py` | 共享库（ELF/ISO/反汇编/栈访问） |
| `work\builds\GR_HOOK\tools\hk_sites.py` | A 站点表与分组 |
| `work\builds\GR_HOOK\tools\hk_dump.py` | 反汇编与栈帧表 |
| `work\builds\GR_HOOK\tools\hk_fp.py` / `hk_fplive.py` | `$fp` 取证与受害者扫描 |
| `work\builds\GR_HOOK\tools\hk_syms.py` | 两份 emulog 指纹对比 |
| `work\builds\GR_HOOK\tools\hk_build.py` / `hk_verify.py` / `hk_disc_tables.py` | 构建 / 复核 / 清单 |
| `work\builds\GR_HOOK\evidence\*` | 上述全部证据文件 |
| `docs\AB_TEST_GUIDE.md` 附录 B | 口径差异说明 + 与既有盘的优先级排序 |
