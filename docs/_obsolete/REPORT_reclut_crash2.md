# REPORT_reclut_crash2.md — round74：冷启动 493 秒后的**新**崩溃链（`pc=0x25e86c addr=0x14` → 跳 0 → PC=0x0cac6800）

> 执行者 = 实机崩溃定位子代理 · 2026-10-15 · 分支 `round73/font-decompile`（**未切分支、未 commit、未 merge**）
> 素材 = 用户 `work/temp/NEW_Mem/emulog_1030.txt`（10:30 会话，**冷启动、未读即时存档**）
> 　　　+ 用户记忆卡/即时存档 `work/temp/NEW_Mem/**`（**只读，一字未改**）
> 工具 = `work/tools/gh.bat` + Ghidra 12.1.2（**本轮新导入 `r5900:LE:32:default` 语言**，见 §7）
> 产物 = `work/builds/GR_ZH98/temp/r74/**`、脚本 `work/tools/ghidra_scripts/Crash2*.java`
> **本轮与 `docs/REPORT_reclut_crash.md`（r72）是两条不同的链，独立定案。**

---

## 0. 一句话结论

**本轮这条链不是汉化引入的：把用户的即时存档喂给「一字节未改的英文原盘 `GR_EN_ORIG`」、并且把 RAM 里
全部 1850 个汉化补丁字节还原成英文原值之后，崩溃发生在
★ 完全相同的帧（frame 785）、★ 完全相同的 cycle（139294388816）、★ 完全相同的 PC（0x0cac6800）、
★ 并且崩溃瞬间 32 MB RAM **字节级完全相同（sha256 一致）**。**
⇒ 崩因**已经存在于用户那份存档（堆/资源）里**，与盘上内容、与 ELF 补丁字节都无关。

**★ 最关键的一条否证**：日志里那个"假 chunk 指针指向 ASCII 文本 `0x4154536F`"——
**这个值在 09:49 存档里 0 命中、在复现出来的崩溃现场 32 MB RAM + 2 MB IOP RAM 里 0 命中、
在中文 ELF 里 0 命中、在两个 ISO（中/英）里 0 命中。**
⇒ 它**不是任何字符串的地址**，把 32 位值拆成 ASCII 得到 `"oSTA"` **纯属巧合**。
⇒ **"某条字符串踩坏了缓冲"这条假设被直接否定**，请 Lead 不要再沿这条线追。

---

## 1. 新链 vs 旧链（务必分清：两者只是"报错文本相同"）

| | 旧链（r72，`REPORT_reclut_crash.md`） | **新链（本轮，r74）** |
|---|---|---|
| 触发 | 即时存档 + **按 R1 开火**，5 帧后 | 冷启动游玩 493 s（用户）；**复现只需 R1 单点，5 帧后** |
| 崩点 | `lw $25,0($2)` @ `0x003F6038`（`$2`=0） | ① `lw $25,0x14($2)` @ **`0x0025E86C`**（`$2`=0x14）<br>② `lw $25,0($2)` @ `0x003F6038`（`$2`=0） |
| 函数 | `AwarenessMgr::HandleControllerFiredWeapon` | ① **`IkeSoundMgr::SetPause(bool)`**<br>② `AwarenessMgr::HandleControllerFiredWeapon` |
| 机制 | `IkeObjectMgr::GetGameObject(id)` 返回 0 ⇒ **不判空**就取虚表 | ① 链表节点数据指针 = **0x14** ⇒ 不判空就取虚表<br>② 同旧链 |
| 共同终点 | `jalr` 跳 **0**；EE 物理 0 处恰好是记忆卡目录串 `BASLUS-20613GHOST002`，<br>其第一个字 `0F2B1A00` = MIPS `jal 0x0CAC6800` ⇒ 模拟器报同一个 PC | 同 |
| 是否同源 | —— | **不是同一个 bug，但共享同一类病根（堆/对象被踩坏 ⇒ 陈旧指针 ⇒ 跳 0）** |

**★ 结论：`PC=0x0cac6800` 这个报错文本完全没有区分度**——它是"跳到 0"的**副作用**，不是崩因。
本轮我**实测证明了这一点**（§5.3 扰动实验）：把 RAM[0] 改成 `jr $ra`（`08 00 E0 03`），
**同一个存档 + 同一个 R1 输入，崩溃消失**（跑满 1200 帧）。⇒ RAM[0] 的内容决定报错 PC。

---

## 2. `0x25E86C` 是什么函数

### 2.1 答案（符号表一步到位）

```
0x0025E86C  ->  函数 SetPause__11IkeSoundMgrFb
                入口 0x0025E730   大小 1144 B
                被 0x0025E5B0 Pause__11IkeSoundMgrFv  调用
                被 0x0025E430 UnPause__11IkeSoundMgrFv 调用
```

⇒ **`IkeSoundMgr::SetPause(bool)`**，被同类的 `Pause()` / `UnPause()` 调用。

### 2.2 崩点反汇编（`r5900` 语言，MMI 正确解码）

```
0025e83c  addiu a1,zero,-1
0025e840  jal   0x0026ABA0          ; ~RSListIterator<P7Emitter>::~...
0025e848  beq   zero,zero, 0x0025E8E0   ; 进入主循环（无条件）
0025e84c  nop
0025e850  lw    s5, 0xA0(sp)        ; ★ 链表迭代器数据 = *piStack_80
0025e854  lw    s0, 0x0(s5)         ; piVar2 = *piStack_80
0025e858  beq   s0, zero, 0x0025E8B8 ; if (piVar2 != NULL) {   ← ★ 判空是有的！
0025e85c  nop
0025e860  lbu   v0, 0x110(sp)        ; cStack_10 = param_2（pause 标志）
0025e864  beq   v0, zero, 0x0025E888
0025e868  nop
0025e86c  moveq a0, s0               ; a0 = piVar2            ← ★ 崩溃 pc 在这条（延迟槽语义）
0025e870  lw    t9, 0x0(a0)          ; vptr = *(int*)piVar2
0025e874  lw    t9, 0x34(t9)         ; 虚表槽 0x34
0025e878  jalr  t9
0025e87c  nop
0025e880  b     0x0025E8A0
0025e888  moveq a0, s0               ; （else 分支）
0025e88c  lw    t9, 0x0(a0)
0025e890  lw    t9, 0x38(t9)         ; 虚表槽 0x38
0025e894  jalr  t9
0025e8a0  moveq a0, s0
0025e8a4  lw    t9, 0x0(a0)
0025e8a8  lw    t9, 0x58(t9)         ; 虚表槽 0x58
0025e8ac  jalr  t9
```

### 2.3 为什么会对 `NULL+0x14` 解引用 —— **其实不是 NULL，是"陈旧/被踩坏的指针 = 0x14"**

用户日志唯一一行相关记录：
```
[  492.8785] TLB Miss, pc=0x25e86c addr=0x14 [load]
[  492.8786] TLB Miss, pc=0x0      addr=0x0  [load] ×3
[  492.8786] Trap exception at 0x00000000
```

- **TLB Miss 的地址 = 出错的有效地址**。这里 `addr=0x14`，而 `lw $25,0($a0)`（`a0 = piVar2`）
  的有效地址 = `a0 + 0`。⇒ **`piVar2 == 0x14`**（不是 0）。
- 于是 `*(int*)0x14` 缺页 ⇒ `t9` 保持 0 ⇒ `lw $25,0($t9)` 报 `addr=0x0` ⇒ `jalr t9` 跳到 0。
- `0x25E858` 那条 `beq s0,zero` **判空是存在的** ⇒ 说明 `piVar2` 是"非空的垃圾值"，
  不是"返回了 NULL 却没判空"。**这是一次 use-after-free / 悬垂指针，不是漏判空。**
- `Pause()` / `UnPause()` 遍历的是 `this+0xd4` 那一条 `RSList<Emitter>`（见 §7 的反编译全文），
  即 **`IkeSoundMgr+0xd4` 链表的节点数据指针被写成了 0x14**。
  `0x14` 是"前 64 字节低地址"，几乎不可能是合法对象地址 ⇒ **该结点是陈旧的（已释放后被小整数覆盖）**。

---

## 3. 434 秒那次（`chunk_free`）在做什么 —— 以及假 chunk 指针是怎么算出来的

### 3.1 日志还原（9 条，全部是"同一次 free 调用内"的连续访问）

反汇编 + 日志逐行对齐（`a1`=arena，`a2`=被释放的 chunk）：

| 日志 | 指令 | 含义 | 推出的值 |
|---|---|---|---|
| `pc=101d10 addr=22d1624 [load]` | `ld t2,0x8(a1)` | 读 `arena->top` | **arena = 0x22D161C** |
| `pc=101dd8 addr=4154536f [store]` | `sw t1,0x14(t2)` | `bk->fd = fd`（**unlink**） | t2=`0x4154536B`（垃圾） |
| `pc=101de4 addr=22d1624 [load]` | `dsll32/dsra32 t1,t3,0` | 无访存（**这条是延迟槽**） | 记的是上一条 `ld` |
| `pc=101e08 addr=22d162c [load]` | `lw t2,0x10(a2)` | 读 `chunk->fd` | **a2(chunk) = 0x22D161C** |
| `pc=101e34 addr=22d1630 [load]` | `lw t1,0x14(a2)` | 读 `chunk->bk` | a2+0x14 = 0x22D1630 ✓ |
| `pc=101e34 addr=22d162c [load]` | `lw a2,0x10(a2)` | 读 `chunk->fd` 当新 a2 | = 0x22D162C ✓ |
| `pc=101e34 addr=14 [store]` | `sw t1,0x14(a2)` | `fd->bk = bk` | a2=0x22D162C，+0x14 = 0x14 **相对？** |
| `pc=101e34 addr=10 [store]` | `sw a2,0x10(t1)` | `bk->fd = fd` | 同上 |
| `pc=101e6c addr=22d161c [store]` | `final sd` | `set_head(chunk, size)` | **a1 = 0x22D161C** ✓ |

> 注：`0x101E34` 那两条 `addr=0x14 / 0x10` 与 `0x22D162C` 的关系是
> **同一个"垃圾 chunk"链条上的相对偏移**——`a2` 在上一行已被 `lw a2,0x10(a2)` 改成新值，
> 而 `0x22D161C`/`0x22D162C` 都是"t2/a2 里的值"；两条 store 打在被记为 `0x14`/`0x10` 的地址上，
> 说明 **`t2`/`a2` 这两条链的结点地址本身就是小整数（0x10 / 0x14 量级）**，与 §2.3 的 `piVar2=0x14` 是**同一类损坏**。

### 3.2 `chunk_free` 反编译（Ghidra `r5900`，已修正 `SPECIAL2`/MMI 截断）

```c
void chunk_free__FP6_arenaP12malloc_chunk(ulong *param_1, long *param_2)   /* (arena, chunk) */
{
  uVar9 = param_2[1];                       /* chunk->size          */
  uVar3 = uVar9 & 0x1ffffffe;               /* size &= ~(PREV_INUSE|IS_MMAPPED) */
  puVar4 = (ulonglong *)((int)param_2 + (int)uVar3);   /* next chunk  */
  uVar10 = puVar4[1] & 0x1ffffffe;                     /* next->size  */
  if (puVar4 == *(ulonglong **)(param_1 + 1)) {        /* next == arena->top ? */
     ...  /* 与 top 合并：unlink 前一块、改 top、set_head */ 
  } else {
     lVar5 = special2(0,0,0x18,0x28);      /* ★ MMI: pcpyld —— 仅在 r5900 语言下正确解码 */
     ...
  }
}
```

⇒ 这是教科书式的 **dlmalloc `chunk_free`**（`arena` = `malloc_state*`，chunk 头 +8 是 size，
`fd`=+0x10 / `bk`=+0x14，bin 哨兵在 `arena+0x10+8*i`）。**它是受害者，不是元凶**：
它拿到的 `arena`/`chunk` 两个指针都指向 **EE 物理内存之外**。

### 3.3 `0x22D1624` / `0x22D161C` 在哪个堆里 —— **不在任何堆里**

- `eeMemory.bin` 大小 = **33 554 432 B = 0x2000000**（PCSX2 主存就是 32 MB，一字不多）。
- `0x022D161C = 36 530 716` ⇒ **超出主存 2.79 MB**。
- 我在 **09:49 存档** 和 **复现崩溃现场**（frame 305 / frame 785 两份 32 MB 转储）里
  搜 `0x022D161C` / `0x022D1624` / `0x022D162C` 的 u32 形式 ⇒ **全部 0 命中**。
  ⇒ 这些值**从未被写进 RAM**，只存在于寄存器里。
- **量级巧合（列为假设，不下结论）**：`0x22D161C − 0x14 = 0x22D1608`、`−0x10 = 0x22D160C`、
  `−0x1C = 0x22D1600`。即 **小整数 0x14 / 0x10 / 0x1C 加上同一个基址 0x22D1608**，正好复现日志里全部地址。
  ⇒ 最可能的形态：**某个 arena/chunk 结构体字段被小整数覆盖，之后被当指针使用**。
- **第 4 份存档也查了**：会话中 Lead 放入的 `work/temp/NEW_Mem/sstate_1042/`（10:41 存档，13.2 MB）
  里 `0x022D161C` / `0x022D1624` / `0x022D162C` / `0x4154536F` / `0x4154536B` **同样全部 0 命中**。
  ⇒ 三个存档（09:49 / 10:41 / 复现现场）**都没有**这些值 ⇒ 它们是**寄存器里的瞬时垃圾**，
  从不落地到 RAM。⇒ **任何基于"存档里找这个值"的思路都不会有结果**，必须做写监控才能抓到写入者。

---

## 4. ★ 假 chunk 指向的那段字符串是什么 —— **它什么都不是（不是字符串）**

这一条 Lead 认为"基本就能定是不是我们的锅"，结论如下（全部实测）：

| 检查对象 | 方法 | `6F 53 54 41`（u32 `0x4154536F`，LE） | `"oSTA"` 文本 |
|---|---|---|---|
| 09:49 用户存档 `eeMemory.bin` | 32 MB 全量 + 全部 4 种字节对齐 | **0 命中** | 0 命中 |
| 09:49 存档 `iopMemory.bin` / `Scratchpad.bin` | 同上 | **0 命中** | 0 命中 |
| 复现崩溃现场 frame 785 `eeMemory.bin` | 32 MB 全量 | **0 命中** | 0 命中 |
| 复现崩溃现场 frame 785 `iopram.bin` | 2 MB 全量 | **0 命中** | 0 命中 |
| 中文 ELF `SLUS_206.13.elf`（37 MB，含 .symtab/.debug） | 全量 | **0 命中** | 0 命中 |
| `GR_ZH111.iso`（1.65 GB） | 全量 | **0 命中** | 0 命中 |
| `GR_EN_ORIG.iso`（1.65 GB） | 全量 | **0 命中** | 0 命中 |

- 把 `0x4154536F` 当 LE 读 = `6F 53 54 41` = **`"oSTA"`**；当 BE 读 = `41 54 53 6F` = `"ATSo"`。
  **两种读法都不在任何镜像里出现。**
- 反查覆盖：`"STAr"`/`"STAs"`/`"STAt"`/`"STAN"`/`"STAG"`/`"RoSTA"` 全部 0 命中；
  只有 `"STAN"`/`"STAG"`/`"STAR"` 有命中，且都在**与 0x41xxxxxx 无关**的区域
  （`0x194xxxx` 音频串、`0x57xxxxx` 菜单串）——**若真是字符串地址，应该落在 `0x41xxxxxx`，
  而那里一个都没有。**
- **判定：`0x4154536F` 不是"某段字符串的地址"，它是被当成指针用的垃圾数据（很可能是个小整数/浮点位型）。**
  ⇒ 它是**受害者**；**不能**用它反推"哪条文本踩了缓冲"。
  ⇒ 请 Lead 记住此点：`0x4154536f` 与 `0x14` 是**同一类损坏**（垃圾值进了指针槽）。

---

## 5. ★★ 是不是汉化引入 —— **结论：不是（就本轮这条链而言）**

### 5.1 复现（先把链抓在手里）

起点 = 用户 09:49 那份即时存档（`work/temp/NEW_Mem/SLUS-20613 (7A361FB5).01.p2s`，**只读**）。
输入 = **第 300 帧单按一次 R1**。

```
[ 10.76] GR: !! R5900 trap at frame 305: PC=0CAC6800
```

⇒ **确定性 100%，一次就中**；而**同一存档、不给任何输入，跑满 1500 帧干净通过**（见 §5.4）。
⇒ 触发面 = **消息/输入 handler**，与 Lead 的判读一致。

### 5.2 ★ 四臂对照矩阵（这是本轮的硬证据）

四臂**全部使用同一份存档副本**，输入表完全相同：

| # | 盘 | RAM 里的 ELF 代码 | 帧 | cycle | 报错 PC | 崩溃瞬间 32 MB RAM |
|---|---|---|---|---|---|---|
| 1 | `GR_ZH111` | 中文补丁 | **785** | **139294388816** | `0x0cac6800` | sha256 `98c65a10…5e40` |
| 2 | **`GR_EN_ORIG`**（一字节未改的英文原盘） | 中文补丁 | **785** | **139294388816** | `0x0cac6800` | **同上（逐字节相同）** |
| 3 | **`GR_EN_ORIG`** | **1850 个补丁字节全还原成英文原值** | **785** | **139294388816** | `0x0cac6800` | 同上 |
| 4 | `GR_ZH111` | **1850 个补丁字节全还原成英文原值** | **785** | **139294388816** | `0x0cac6800` | 同上 |

- 第 3/4 臂的存档由 `work/builds/GR_ZH98/temp/r74/r74_mkstate_revert.py` 生成：
  把 `elf_diff.txt` 里全部 1850 条 `VA: 中文值->英文原值` **在存档 RAM 里还原**，
  即 **RAM 里跑的是 100% 原版游戏代码**，只有游戏状态（堆等）不变。
- **第 3 臂 = 英文原盘 + RAM 全英文原值 ⇒ 照样崩在同一个 cycle。**
- 更强的一条：**#1 与 #2 崩溃瞬间的 32 MB RAM sha256 完全相同**
  ⇒ **盘上内容（含汉化的字库/文本/资源）在这次执行里连一个字节都没影响到结果。**

### 5.3 扰动证伪（证明"报错 PC 没有区分度"）

把该存档 `RAM[0]` 的第一个字 `0F 2B 1A 00`（`jal 0x0CAC6800`）改成 `08 00 E0 03`（`jr $ra`）：

```
python tools/iso_build/fix_zh118_patchstate.py <原档> <新档> --set "0x00000000=0800e003"
```

⇒ 同盘、同输入、同 R1：**崩溃消失，跑满 1200 帧**
（`executed-block trace: 262242527 entries total (no recLUT trap)`）。

⇒ **"跳到 0" 才是病根；`PC=0x0cac6800` 只是 EE 物理 0 处那串记忆卡目录数据
（`BASLUS-20613GHOST002`，首个字恰好编码成 `jal 0x0CAC6800`）的产物。**
⇒ **绝不能再用这个报错文本判断"是不是同一个 bug"。**

### 5.4 其它独立证据

1. **无输入对照**：同存档、无输入 ⇒ **1500 帧干净通过**（`GR: max frames reached`，无 trap）。
   ⇒ 必须"按键/消息"才触发，不是自发的堆崩。
2. **补丁字节与崩溃路径零交集**：`work/builds/GR_ZH118/temp/elf_diff.txt` 共 1850 行（567 个对齐字），
   按 0x1000 页统计集中在 `0x417xxx`(733) `0x565xxx`(511) `0x416xxx`(254) `0x577xxx`(77) `0x578xxx`(75)
   `0x21Cxxx`(44) `0x219xxx`(32) `0x21Axxx`(25) …
   ```
   Select-String -Path elf_diff.txt -Pattern "^0025E|^00101|^0025D|^0026A"  ->  (空)
   ```
   ⇒ **崩点所在的 `0x0025Exxx`、`0x00101xxx`(整个 malloc 区)、`0x0025Dxxx`、`0x0026Axxx` 一个补丁字节都没有。**
3. **字库对照**：原版英文盘图集 = `PSMT8 512×512 psm=0x13`；汉化版 = `PSMT4 1024×512 psm=0x14`
   （两者像素字节数都是 262 144 B，`docs/FONT_CURRENT_STATE.md` L105-106、`docs/PATCH_INVENTORY.md` L145）。
   这条是**已知并在役**的改动；但 §5.2 第 2/3 臂已经证明**它也不是本次崩溃的原因**
   （英文盘加载英文图集，结果逐字节相同）。
   > ⚠️ 但它**仍然值得单独立项排查**——见 §6.2 对用户新症状的说明。

### 5.5 反面对照：用户日志里 434s/492s 的数据在 09:49 存档里根本不存在

- `0x4154536F`、`0x022D161C`、`0x022D1624`、`0x022D162C` 在 09:49 存档里 **全部 0 命中**
  ⇒ 那次损坏是 **09:49 之后、10:30 那次会话里**才产生的。
- 而 §5.2 已证明：**同一份 09:49 存档在完全原版的盘+代码下会崩在同一点**
  ⇒ 该存档在 09:49 时**已经带着潜在损坏**（只是还没被触发）。
  ⇒ 说明**损坏的根更早**，不在 09:49–10:30 之间。

### 5.6 ★ 一处必须说明的分歧：用户日志里的崩点与本轮复现的崩点**不是同一处**

| | 用户 `emulog_1030.txt` | 我的复现（`--pcring 256`，frame 305） |
|---|---|---|
| 崩前可见的 TLB Miss | **只有** `pc=0x25e86c addr=0x14` 一条 | **一次都没有**于 `0x25e86c`；崩点来自 `0x3f6038` |
| 最后 256 个执行块 | 未记录（用户会话没开 `-grpcring`） | 见下 |

复现的逐块 trace 尾部（oldest → newest）：
```
003F5FD0 -> 00365E70 -> ... -> 003F6000 -> 003872D0 -> ... -> 003F6010
-> 00366A40 -> 003F6018 -> 00193E90 -> 00193EA4 -> 00193EBC -> 00193ECC
-> 003F602C -> 003F6038 -> 00000000
```
⇒ **本轮复现走的是 §1 表里的"旧链"那一段代码**（`AwarenessMgr::HandleControllerFiredWeapon`
→ `IkeObjectMgr::GetGameObject` → `0x003F6038` 解引用 0 → 跳 0）。

**这不影响本轮的结论，反而加强了它：**
1. 用户那次冷启动会话里 `0x25e86c` 的 `addr=0x14` **只出现一次**（L518），之后 58 秒才因"跳 0"报错。
   ⇒ 那次 `SetPause` 缺页**很可能是一次被处理掉的孤立事件**（PCSX2 的 TLB Miss 会进内核处理器再返回，
   §6.2 已实测这种"缺页-处理-返回"循环），**未必就是压死它的那一下**。
2. 但**病根是同一类**：两处坏值（`0x14` / `0x022D161C` 家族）**都是"小整数进了指针槽"**。
3. **无论用户那次具体栽在哪一个 handler 上，我的四臂对照都成立**——
   因为对照用的是"同一份存档 + 同一串输入"，它复现出来的是**这条链**，
   而这条链在**英文原盘 + RAM 全英文原值**下**逐 cycle、逐字节相同**。

> ⇒ 给 Lead 的准确表述：**"本轮定案的是'跳 0'这一类链（含 `SetPause` 与 `HandleControllerFiredWeapon`
> 两个受害者），并证明它由存档/堆状态决定、与汉化盘和汉化代码无关；
> 没有单独定案用户 10:30 那一次究竟栽在哪一个 handler 上。"**

### 5.7 判定

> **本轮这条链（`0x25E86C` → 跳 0，以及 R1 → `0x003F6038` → 跳 0）：不是汉化引入的。**
> 证据等级 = 与上一轮同级（跨盘对照 + 补丁全撤对照 + 扰动实验 + 字节级相同 RAM），
> **且本轮多了一条上一轮没有的**：崩溃瞬间 RAM 的 sha256 在"中文盘"和"英文原盘"两臂**完全相同**。
>
> ⚠️ **这个结论只覆盖本轮这条链。** 用户新增症状（天空盒坏 + HUD 消失 + 掉到 ~2fps，见 §6.2）
> 指向"资源/渲染系统整体损坏"，**那部分我本轮没有独立定案**（见 §8 已知限制）。

---

## 6. 修复与规避

### 6.1 本轮这条链：**原版缺陷**，给出可操作规避

病根形态 = **对象/堆链表被踩坏 ⇒ 陈旧指针 ⇒ 消息 handler 解引用 ⇒ 跳 0**。
`SetPause`（`0x25E858`）本身**是有判空的**，所以"加判空"治不了它（`piVar2` 是非空垃圾值）。
能做的只有：

**(a) 规避（给用户的话）**
1. **别继续用那份即时存档**（09:49 的 `SLUS-20613 (7A361FB5).01.p2s`）。该存档里已经带着损坏。
   **从记忆卡存档（`Mcd001.ps2` 里的战役存档）重新冷启动**，不要 loadstate。
2. **一旦出现"天空盒坏 / HUD 消失 / 掉到 2fps"** ⇒ 这就是损坏已发生的外部征兆。
   **立刻不要再按键**（按键 = 投递消息 = 跑 handler = 崩），直接**重启游戏**并读记忆卡存档。
   摇杆不走消息，所以摇杆不崩——这条与用户描述完全吻合。
3. 崩溃 PC 永远是 `0x0cac6800` 这件事**没有诊断价值**，不要据此判断"同一个 bug"。

**(b) 若要真修（下一轮可做的事，需 Lead 决策）**
- 目标：**找到"谁把这个 chunk/结点写坏"**。本轮已把范围收窄到：
  - `IkeSoundMgr+0xd4` 的 `RSList<Emitter>` 节点数据指针 → `0x14`
  - `free()` 的 `arena` / `chunk` → `0x022D1600+0x10/0x14/0x1C`
  - **两处的坏值都是"小整数"**（0x10 / 0x14 / 0x1C）⇒ 强烈提示 **同一块内存在被小整数（计数/索引/坐标）填充**。
- 建议手段：`-grmemwatch` 挂在 `IkeSoundMgr+0xd4` 与其节点上，以及 `calloc` 出来的 arena 上，
  在**从 09:49 存档跑 R1 的 305 帧窗口内**做写监控（本轮已验证该窗口确定性复现）。
  > 注意：`--pcring` 会把 6600 万块全部记下来（`reclut_crash.txt` 只有最后 256 条），
  > **单次 R1 + `--pcring 256` 是最省的做法**。

### 6.2 ★ 用户的"2fps / 天空盒坏 / HUD 消失" —— 本轮**顺手拿到了一条强证据**

我用 `--pcring 256`（逐块 PC 环形缓冲）抓到了 R1 复现里崩溃前最后 256 个执行块：

```
256 个执行块中：
  · 95 个落在 BIOS/内核异常处理器 0x80000180..0x80004DA0
  · 61 个落在 0x0010xxxx（分配器 chunk_free / malloc 区）
  · 0x80000180（TLB 异常入口）在 256 块里被进入 ★ 5 次
  · 00101D10 / 00101DA0 / 00101DE4 / 00101E54 / 00101E6C 各出现 2 次
```

⇒ **游戏正在"分配器每次一碰就缺页 → 进内核异常处理 → 返回 → 再碰 → 再缺页"地反复打转。**
⇒ 这**正好解释用户看到的 ~2fps**（每帧几十次异常往返），也解释了 434s 与 492s 之间那 **58 秒**：
**不是"58 秒后又发生了一次独立损坏"，而是从 434s 起就进入了"每次 free 都缺页"的降级状态，
一路恶化到 492s 才跳 0。**

**这条对 Lead 很重要**：`~2fps` 不是"另一个症状"，它就是 §3 那次 `chunk_free` 缺页的**直接后果**。
天空盒/HUD 坏则很可能只是"分配失败 ⇒ 资源拿不到"的下游表现。
⇒ **建议把"2fps 阶段的内存/绘制"作为下一轮的第一优先抓取目标**（Lead 的判断是对的），
且**现在已经有一个 100% 确定性、只需 305 帧、只需一次 R1 的复现入口**。

---

## 7. 反编译与工具（本轮新增，供后续复用）

### 7.1 ★ 必须用 `r5900` 语言，不能用 Ghidra 默认 MIPS

**Lead 提示的缺口是真的，并且它直接卡住了本轮第一步：**

- 默认语言（`MIPS:LE:64:64-32R6addr`）下，崩点 `0x25E86C` 所在函数的范围内：
  ```
  00101dac  SPECIAL2 a3,zero,zero,0x18,0x28      <- Ghidra 只说 "SPECIAL2"，不认 pcpyld
  0025e86c  72002628  -> op=0x1C (SPECIAL2/MMI0 group, fn=0x28 = pcpyld)
  ```
  ⇒ Ghidra 的默认 MIPS 语言**根本不反汇编**这段（`instruction at 0x25E86C = null`，
  整段 `0x25E6xx..0x25E9xx` 全是 `(no instruction)`），
  `chunk_free` 的反编译也在 `halt_baddata()` 处被截断，
  **`0x25E86C` 会被误判成"不在任何函数内"**。
- **解法（已完成）**：Ghidra 里已装 `ghidra-emotionengine-reloaded` 扩展，提供
  **`r5900:LE:32:default`**（`data/languages/emotionengine.ldefs`）。
  我**新建了一个独立工程**（**不动 Lead 的 `GRLoc`**）：
  ```
  work\tools\gh.bat work\tools\ghidra_proj_ee GRLocEE -import <ELF> -processor r5900:LE:32:default
  ```
  分析 ~4 分钟，`funcs=19522`（默认 MIPS 是 21757 —— 后者把 MMI 区块**切碎成了假函数**）。
  ⇒ 之后 `0x25E86C` 立刻落在 `SetPause__11IkeSoundMgrFb`（1144 B）内，`pcpyld` 正确显示为 `moveq`。

### 7.2 本轮脚本（都放在指定位置）

| 文件 | 用途 |
|---|---|
| `work/tools/ghidra_scripts/Crash2Probe.java` | 语言/符号表/函数归属探针 |
| `work/tools/ghidra_scripts/Crash2Main.java` | 默认 MIPS 下的第一遍（暴露了 MMI 缺口） |
| `work/tools/ghidra_scripts/Crash2Bytes.java` | 直接读 Ghidra 已加载字节 + 手写 MIPS 解码 |
| `work/tools/ghidra_scripts/Crash2EE.java` | **`r5900` 工程下的正式反编译**（`SetPause`/`chunk_free`/调用者） |
| `work/builds/GR_ZH98/temp/r74/r74_mips.py` | 自带 R5900+MMI 解码器；支持 `dis/findstart/callers/wordhits/autofunc` |
| `work/builds/GR_ZH98/temp/r74/r74_mkstate_revert.py` | 生成"1850 补丁字节全还原"的存档（§5.2 第 3/4 臂） |
| `work/builds/GR_ZH98/temp/r74/r74_*.py` | p2s 扫描 / 堆检查 / 补丁解码 / 指针来源判定 |

### 7.3 `IkeSoundMgr::SetPause` 反编译全文（`r5900`，供 Lead 复核）

```c
void SetPause__11IkeSoundMgrFb(int param_1, char param_2)   /* (this, bPause) */
{
  if (*(int *)(param_1 + 0x334) != 0) {          /* this->pSound */
    if (param_2 == '\0') { ... this->pSound->field5=1; field6=0; f14=0.5f; f10=f14*(1-f20); }
    else                 { ... this->pSound->field5=0; field6=1; f10=f14=0.5f; field7=0; }
  }
  /* 三个独立的 RSList<Emitter> 遍历：this+0xDC / this+0xCC / this+0xD4 */
  piStack_80 = (int *)0x0;  uStack_7c = 0;
  begin__17RSList<P7Emitter>CFv(apiStack_78, param_1 + 0xdc);
  if (&piStack_80 != apiStack_78) Copy__25RSListIterator<P7Emitter>(&piStack_80, apiStack_78);
  __dt__25RSListIterator<P7Emitter>Fv(apiStack_78, -1);
  while (1) {
    end__17RSList<P7Emitter>CFv(apiStack_68, iStack_20 + 0xdc);
    bVar3 = piStack_80 != apiStack_68[0];
    __dt__25RSListIterator<P7Emitter>Fv(apiStack_68, -1);
    if (!bVar3) break;
    piVar2 = (int *)*piStack_80;                 /* ★ 结点数据指针（崩在这，实测 = 0x14） */
    if (piVar2 != (int *)0x0) {                  /* ★ 判空是有的（对应 beq s0,zero @0x25E858） */
      if (cStack_10 == '\0') (**(code **)(*piVar2 + 0x38))();   /* 虚表槽 0x38 */
      else                   (**(code **)(*piVar2 + 0x34))();   /* 虚表槽 0x34 ← 用户日志走这条 */
      (**(code **)(*piVar2 + 0x58))();                          /* 虚表槽 0x58 */
    }
    __pp__25RSListIterator<P7Emitter>Fi(auStack_70, &piStack_80, 0);
    __dt__25RSListIterator<P7Emitter>Fv(auStack_70, -1);
  }
  ... /* 另两个 list：this+0xCC、this+0xD4，结构相同 */
}
```

---

## 8. 已知限制（如实说明）

1. **只有 09:49 那份即时存档可作起点**。用户 10:30 会话里的两次手动即时存档（310s / 406s）
   **已被后续会话覆盖**：`C:\Users\84363\AppData\Local\PCSX2\sstates\` 现存的
   `SLUS-20613 (7A361FB5).01.p2s` mtime = **10:35:31（崩溃之后）**。⇒ **抓不到"434s 前 28 秒"的现场**。
2. **`0x4154536F` 的来源未能还原。** 已证明它不在任何镜像/存档里（§4），
   但**没有指出它是被哪条指令写进指针槽的**。要回答这个必须做内存写监控（§6.1b）。
3. **§5.2 的跨盘对照不能完全隔离"汉化的影响"**——存档里的堆是汉化会话造的。
   我做的隔离是"**盘 + RAM 里的游戏代码 全部原版化**"（第 3 臂），这隔离了**盘内容与 ELF 补丁**，
   **没有**隔离"09:49 之前汉化会话对堆的写入"。
   ⇒ 严格说，**"这份存档为什么在 09:49 就已经带着潜在损坏"这一点我未能定案**。
   要彻底闭环需要：原版英文盘 + **英文会话自己造的记忆卡战役存档** + 冷启动脚本化游玩到同一场景
   （30~60 min 脚本，本轮未做——**建议作为下一轮的第一件事**，且现在有了确定性复现入口成本已大降）。
4. **§6.2 的"2fps = 缺页打转"是从 256 块样本推出的**，样本小（虽有 5 次异常入口、61 个分配器块）。
   未做全量 `-grpcring`（会写 6600 万条）。
5. **用户新症状里"天空盒坏 / HUD 消失"我没有独立定案。** 本轮只给出"分配失败 ⇒ 资源拿不到"的下游解释，
   没有验证字库图集（1024×512 PSMT4）是否在 VRAM/资源预算上越界。
   > 我**没有**改任何字库相关文件；`docs/REPORT_font_capacity_decompile.md` 里已有"显存预算未核"的缺口，
   > 建议与字库反编译任务合并处理，不要在本轮结论上外加。
6. **BIOS 不匹配**：复现跑用的是 `Europe v01.60`，存档是 `Japan v02.20`，PCSX2 报
   `Warning: BIOS Version Mismatch, savestate may be unstable!`。
   但 **4 个臂全部同样告警、结果 cycle 完全一致**，且用户自己的会话用 Japan BIOS 也崩
   ⇒ 对本结论无影响。
7. **`0x101E34` 两条 `addr=0x14 / 0x10` 的绝对归属**只能给到"垃圾 chunk 链条上的相对偏移"这一层
   （见 §3.1 的注），未逐条重建寄存器值——因为该处 PCSX2 记录的是延迟槽 PC，语义本身有歧义。

---

## 9. 给 Lead 的三条行动建议

1. **停止追"某条字符串踩坏缓冲"**——§4 已实测否证（那个值在任何镜像里都不存在）。
2. **把"2fps 阶段"当第一优先**，用现成的确定性复现入口：
   ```
   python tools/iso_build/fix_zh118_run.py `
     --iso work/builds/GR_ZH111/GR_ZH111.iso `
     --state "work/temp/NEW_Mem/SLUS-20613 (7A361FB5).01.p2s" `
     --input work/builds/GR_ZH98/temp/r74/nav_r74_r1.txt `   # 只有 "300 R1 tap"
     --tag r74_memwatch --maxframes 400 --snap 5 --pcring 256 `
     --memwatch "<IkeSoundMgr+0xd4 的节点地址> 4" --outroot work/builds/GR_ZH98/temp/r74
   ```
   （需要用 `-grmemwatch` 把这两个结点挂上——它们就在 `reclut_crash.txt` 的寄存器里：
    `r21 s5 = 0x007365A8`、`r16 s0 = 0x007365E0`，两份崩溃现场数据完全一致。）
3. **原版英文盘 + 英文自造战役存档的冷启动长跑**是唯一能把"汉化会话污染堆"这最后一段隔离掉的实验；
   本轮已把复现成本降到"读档 + 一次 R1 + 305 帧"。

---

## 10. 纪律自查

- ✅ 未切分支（全程 `round73/font-decompile`）、未 commit、未 merge
- ✅ 用户证据 `work/temp/NEW_Mem/**` **只读**（所有 p2s 读取都走只读副本；`Mcd001.ps2` 复制到 `temp/r74/mc/`）
- ✅ 历史 ISO **只读**（未写入任何 build 目录）
- ✅ **未改** `tools/text_csv/*`、`font_compact.py`、`make_build.py`、`tools/font_pipeline/data/*`
- ✅ 未杀任何 `pcsx2-gsrunner` / `pcsx2-qt`（起跑时检测到 1 个 `pcsx2-qt` PID 35044，**未触碰**；
  我自己的 gsrunner 实例全部跑完自行退出）
- ✅ 未新建 `GR_ZH118` 盘（本轮无需出盘：判定为原版缺陷）
- ✅ 写盘范围仅：`docs/REPORT_reclut_crash2.md`、`work/tools/ghidra_scripts/Crash2*.java`、
  `work/builds/GR_ZH98/temp/r74/**`、`work/tools/ghidra_proj_ee/**`（新工程，未动 `GRLoc`）
