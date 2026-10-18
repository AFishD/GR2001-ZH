# REPORT_reclut_crash.md — round72:「游玩中按 R1 开火 → Jump to unmapped recLUT page (PC: 0x0cac6800)」实机定位

> 执行者 = 实机崩溃定位子代理 · 2026-10-15 · 分支 `main`（未切分支、未 commit）
> 素材 = 用户新即时存档 `work/temp/NEW_Mem/SLUS-20613 (7A361FB5).01.p2s`（10-15 09:49:22）
> 　　　+ 用户记忆卡 `work/temp/NEW_Mem/Mcd001.ps2`（10-15 09:52，sha1 `2a25972ba95251b94f17964aa2ac7cb6f932a35f`）
> 产物 = `work/builds/GR_ZH118/temp/`，脚本 = `tools/iso_build/fix_zh118_*.py`
> **本轮与 `docs/REPORT_save_crash.md`（r70「存档后黑屏」）是两件不同的事，独立定案。**

---

## 0. 一句话结论

**这是原版游戏（未改动的英文盘）自身的空指针虚函数调用 bug，与汉化无关。**

R1 开火 ⇒ 5 帧后进入 `0x003F5FD0` 这个虚函数 ⇒ 内部向一个对象查表（索引 `36`）
⇒ 该表项为空 ⇒ 访问器 `0x00193E90` 规规矩矩返回 **0**（null）
⇒ **调用方 `0x003F6038` 没做判空就 `lw $25,0($2)` 解引用 null**
⇒ 于是把 **EE 物理内存地址 0 处的内容当成"虚表指针"**读走
⇒ `jalr $31,$25` 跳到 **0**
⇒ PCSX2 把物理 0 处的数据当代码编译执行，而那里的第一个字恰好是
`0F2B1A00` = MIPS `jal 0x0CAC6800`
⇒ 跳到无映射代码页 ⇒ 用户看到的 `Jump to unmapped recLUT page (PC: 0x0cac6800)`。

**`0x0cac6800` 不是"被谁写坏的地址"，它是物理 0 处那串数据（记忆卡目录名 `BASLUS-20613GHOST002` 所在的缓冲区）恰好编码出来的 `jal` 目标。真正的问题是"跳到了 0"。**

---

## 1. 复现：确定性 100%，第一次就中

### 1.1 跑法

gsrunner 的 `Console` 输出**不进 stdout**，必须加 `-logfile` 才能看到
`ReportErrorAsync`。本轮新增封装 `tools/iso_build/fix_zh118_run.py`（比
`fix_zh116_run.py` 多 `--timeout` / `--outroot` / 自动 `-logfile` / `--pcring`）：

```powershell
python tools/iso_build/fix_zh118_run.py `
  --iso work/builds/GR_ZH111/GR_ZH111.iso `
  --tag f111_fire1 `
  --state "work/temp/NEW_Mem/SLUS-20613 (7A361FB5).01.p2s" `
  --maxframes 900 --snap 15 --pcsample `
  --input work/builds/GR_ZH118/temp/nav_fire1.txt `
  --memcards work/builds/GR_ZH118/temp/mc --timeout 200
```

输入表：**只在第 240 帧按一次 R1**（`nav_fire1.txt` = `240 R1 tap`，tap = 按下后 12 帧自动松开）。
记忆卡用**用户卡的副本**（`temp/mc/Mcd001.ps2`，只读原件）。

### 1.2 现象（`dump_f111_fire1/emulog.txt`）

```
[ 6.8987] ReportErrorAsync: R5900 Exception: Jump to unmapped recLUT page (PC: 0x0cac6800)
[ 6.8987] (VMManager) Pausing...
=== HW STATISTICS FOR 245 (125) FRAMES ===
GR: input frame 240: bind 12 = 1.0            (bind 12 = PAD_R1)
GR: === run end, frames=245 ===
```

**⇒ 按下 R1 后第 4~5 帧跳飞。** 已跑多次（`fire111_a` / `f111_fire1` / `ring111_fire`），
**每次都是 f245、每次都是 `0x0cac6800`**，逐帧一致 ⇒ 从这份存档出发是**确定性的，不是偶发**。

> ⚠️ 踩坑记录：VM 一 paused，gsrunner 的 `while (GetState()==VMState::Running)` 循环就退出，
> **进程以 exit code 0 正常结束**。只看退出码会把崩溃误判成"跑完了"，必须看 `emulog.txt`。

### 1.3 触发条件矩阵（都是同一存档、同一 `--maxframes 900`）

| # | 盘 | 存档 | 输入 | 结果 |
|---|---|---|---|---|
| 1 | ZH111 | 用户原档 | **无输入** | 干净跑完 900 帧 |
| 2 | ZH111 | 用户原档 | `cross` @240 | 干净跑完 900 帧 |
| 3 | ZH111 | 用户原档 | `R2` @240 | 干净跑完 900 帧 |
| 4 | ZH111 | 用户原档 | **`R1` @240** | **崩 f245, PC=0x0cac6800** |
| 5 | ZH111 | 用户原档 | **`R1` @100** | **崩 f105, PC=0x0cac6800** |
| 6 | **GR_EN_ORIG** | 用户原档 | **`R1` @240** | **崩 f245, PC=0x0cac6800** |
| 7 | **GR_EN_ORIG** | 用户原档 + **1850 个汉化字节全撤** | `R1` @240 | **崩 f245, PC=0x0cac6800** |
| 8 | ZH111 | 同上"补丁全撤"存档 | `R1` @240 | **崩 f245, PC=0x0cac6800** |

**只有 R1（开火）触发；cross / R2 / 不按键都不触发。且按 R1 的帧号不同 ⇒ 崩溃帧号跟着平移（固定延迟 5 帧）。**

---

## 2. `GR_EN_ORIG` 对照 = 一样崩（判据 ①②）

第 6/7/8 行就是答案。第 7/8 行的"补丁全撤"存档由
`tools/iso_build/fix_zh116_mkstate.py` 生成：把存档 `eeMemory.bin` 里**汉化 ELF 与英文
ELF 不同的 1850 个字节全部还原成英文值**（清单 `temp/elf_diff.txt`），
即"游戏状态不变、RAM 里的补丁被撤光"，再配**未改动的英文原盘**。

⇒ **盘是英文原盘、RAM 里的补丁是英文原值，照样在同一帧、同一 PC 崩。**

**补丁地址分布**（`elf_diff.txt`，按 0x1000 页统计）：
`0x417xxx`(733) `0x565xxx`(511) `0x416xxx`(254) `0x577xxx`(77) `0x578xxx`(75)
`0x21Cxxx`(44) `0x219xxx`(32) `0x21Axxx`(25) `0x411xxx`(18) `0x407xxx`(14)
`0x408xxx`(14) `0x2DExxx`(12) `0x21Dxxx`(7) `0x21Bxxx`(7) `0x2BExxx`(6) `0x2ECxxx`(4)。

**崩溃代码路径所在的 `0x003F5xxx/0x003F6xxx`、`0x00193Exx`、`0x00365Exx`、`0x00366Axx`
一个补丁字节都没有**（`Select-String -Path elf_diff.txt -Pattern "^003F6|^00193E|^00366A"` = 空）。

**第 4 条独立证据（本轮新增，很硬）**：`cdvd.log` 记录每次 CDVD 读的帧号，
崩溃跑里 **36585 次读全部发生在 frame 0**（即存档加载阶段），
**加载完存档之后游戏再没有从盘上读过任何东西** ⇒ 汉化盘的内容（除已随存档载入 RAM 的部分外）
在物理上不可能影响这段执行。

**第 5 条独立证据**：见 §4 的扰动实验 —— 崩溃 PC 完全由 EE 物理地址 0 的内容决定。

### 2.1 ★ 用户自己那次 Qt 会话的日志：模拟器直接打印了 `pc=0x0`

证据目录里还有一份 **不是我产生的** 日志：`work/temp/NEW_Mem/emulog.txt`
（2026-10-15 09:58–09:59，`PCSX2 v2.8.2` 中文界面 = **pcsx2-qt 前端**，
启动 78 s，单次 boot：`isoFile open ok: .../GR_ZH111/GR_ZH111.iso`，
`OSD [LoadStateFromSlot]: 已从位置 1 加载即时存档`）。

**这一次会话里同一个报错出现了 5 次，PC 全是 `0x0cac6800`**：

```
[ 7.6820] TLB Miss, pc=0x0 addr=0x0 [load]      <-- ★★★ 模拟器自己打印 PC = 0
[ 7.6820] TLB Miss, pc=0x0 addr=0x0 [load]
[ 7.6820] TLB Miss, pc=0x0 addr=0x0 [load]
[ 7.6820] Trap exception at 0x00000000
[ 7.6820] ReportErrorAsync: R5900 Exception: Jump to unmapped recLUT page (PC: 0x0cac6800)
[ 7.6820] (VMManager) Pausing...
...
[23.0156] (VMManager) Resuming...
[23.0159] ReportErrorAsync: ... (PC: 0x0cac6800)      <- 点掉对话框立刻再触发
[38.5449] Trap exception at 0x00000000
[38.5449] ReportErrorAsync: ... (PC: 0x0cac6800)
[54.2186] RSGameStateMgr::SaveGame( ofstream ) IN
[54.2229] TLB Miss, pc=0x0 addr=0x0 [load] x3 ...
[69.0013] RSGameStateMgr::LoadGame( filename ) IN
[73.3517] TLB Miss, pc=0x102220 addr=0x10b2bef8 [store] / pc=0x101de4 / pc=0x101e6c
[73.4678] Trap exception at 0x00000000
[73.4678] ReportErrorAsync: ... (PC: 0x0cac6800)
```

这条日志的价值：

1. **它是 Qt 前端、用户侧环境、用户自己的操作**（中间还夹着游戏自己的存档/读档），
   不是我 gsrunner 的脚本 ⇒ 排除"我们工具链的伪影"。
2. **`TLB Miss, pc=0x0` 是模拟器核心自己打印的** ⇒ "PC 跑到 0" 不是我反汇编推出来的，
   是模拟器直接看到的，与 §3 的 `ra=8` 推断互相独立地吻合。
3. 报错**每次 PC 都一模一样**（`0x0cac6800`），与用户"有的时候"并不矛盾：
   `有的时候` 指的是"**在别的游戏状态下开火不会走到这个空指针分支**"，
   而一旦走进来，落点就是确定的。
4. 用户点掉对话框后 VM 从暂停点恢复 ⇒ 立刻再次触发（`23.0156 Resuming` → `23.0159` 同一报错），
   所以这个报错会让**这一段彻底卡住**，不是"偶发一下就过去了"。

---

## 3. 崩溃点定位（工具改造 + 现场）

### 3.1 本轮新增的模拟器诊断（默认关闭）

| 文件 | 改动 |
|---|---|
| `pcsx2/x86/ix86-32/iR5900.cpp` | 新增 `bool g_eeTraceAllBlocks = false;`，让已有的逐块入口 trampoline `grIsDrawHookPC()` 在开关打开时对**每个**块返回 true（与已有 `g_eeDrawHook` 同风格，默认零开销） |
| `pcsx2-gsrunner/GRResearch.cpp/.h` | 新增 `-grpcring <n>`：块起始 PC 环形缓冲；`OnHostErrorReport()`：识别 `recLUT` 报文时**同步**（gsrunner 的 `ReportErrorAsync` 是同步的，跑在 CPU 线程上，`cpuRegs` 就是崩溃瞬间的值）落盘 `reclut_crash.txt`（PC/cycle/hi/lo/全部 32 个 GPR/ra・sp・gp 指向的字/最后 256 条执行块轨迹）+ EE/IOP RAM dump；运行结束再写 `exectrace_tail.txt` |
| `pcsx2-gsrunner/Main.cpp` | `Host::ReportErrorAsync` 末尾调用 `GRResearch::OnHostErrorReport(title, message)` |

构建：`bash tools/emu_build/build_pcsx2.sh`（`MVC_ROOT=C:\Users\84363\pbt\msvc`），
增量 4 个编译单元 + 链接 ≈ 40 s。

> 用法：`fix_zh118_run.py ... --pcring 1048576`

### 3.2 崩溃瞬间（`dump_ring111_fire/reclut_crash.txt`）

```
frame: 245
pc: 0CAC6800      cycle: 136637906632
hi: 76            lo: 4
r31 ra  00000008      <-- ★ ra = 8，不是正常返回地址
r2  v0  00000000      r4  a0  00000000      r5  a1  00000001
r16 s0  007365E0      r19 s3  013C17F0      r20 s4  0082FBA0
r28 gp  005E6CF0      r29 sp  01FFE610
```

**`ra = 8` 是整条链的钥匙**：MIPS 的 `jal` 把 `ra` 置为 `PC+8`；`ra=8` 说明
**有一条 `jal` 指令是在 PC=0 处执行的**。

### 3.3 执行块轨迹（环形缓冲最后 9 项）

```
003F6018 -> 00193E90 -> 00193EA4 -> 00193EBC -> 00193ECC -> 003F602C -> 003F6038 -> 00000000
                                                                                      ^^^^^^^^
                                        <== 派出坏 PC 的那个块，起始地址 = 0
```

对 EE RAM dump（VA=物理地址，实测 `RAM[VA]==ELF[VA-0x100000+0x80]`）反汇编：

```
00193E90  addiu $2,$0,-1              ; 访问器：查表
00193E94  bne   $5,$2,00193EA4        ;   a1 != -1 才查
00193EA4  lw    $2,192($4)            ;   v0 = *(this + 0xC0)   <- 表基址
00193EA8  sll   $3,$5,2               ;   a1*4
00193EAC  addu  $2,$2,$3
00193EB0  lw    $2,0($2)              ;   v0 = table[a1]
00193EB4  bne   $2,$0,00193EC4
00193EBC  beq   $0,$0,00193ECC        ;   ★ 表项为空 ⇒ 返回 0（规范的空返回）
00193ECC  jr    $31

003F602C  beq   $2,$0,003F6038        ; ★ v0==0 成立（轨迹证明走了这条）
003F6030  nop
003F6034  addiu $2,$2,-256            ; （编译器给多继承 this 调整加的判空）
003F6038  lw    $25,0($2)             ; ★ 没判空就解引用：$2==0 ⇒ $25 = RAM[0x00000000]
003F603C  (MMI)
003F6040  lb    $5,95($29)
003F6044  lw    $25,792($25)          ; 虚表槽 0x318
003F6048  jalr  $31,$25               ; ★ 跳到 $25
```

**EE 物理地址 0 处的内容**（存档里与崩溃时逐字节相同 ⇒ 不是自改代码）：

```
00000000  00 1A 2B 0F   ->  0x0F2B1A00  =  MIPS `jal 0x0CAC6800`   ★★ 与崩溃 PC 逐位吻合
00000004  06 09 EA 07   ->  0x07EA0906
00000008  00 1F 2B 0F   ->  0x0F2B1F00  =  `jal 0x0CAC7C00`
0000000C  0E 09 EA 07
00000010..1F  全 0
00000020  42 41 53 4C 55 53 2D 32 30 36 31 33 47 48 4F 53 54 30 30 32
          "BASLUS-20613GHOST002"          <-- 记忆卡存档目录名
```

`jal` 的 target = `(word & 0x3FFFFFF) << 2`；`0x0F2B1A00 → 0x0CAC6800`，**逐位相等**。
PC=0 处第一条指令就是这条 `jal` ⇒ `ra = 0+8 = 8`，与 §3.2 的 GPR dump **完全吻合**。

### 3.4 为什么"表项为空"

- 对象：`0x00728C20`（RAM 里 `0x0059EAC0` 这个 vptr 只出现 1 次）。
  `jal 0x193E90` 的编码在 32MB RAM 里 **0 处**，`0x00193E90` 这个字只出现 1 次，在
  `0x0059EAD0` = **虚表 `0x0059EAC0` 的槽 4**（正好对应 `lw $25,16($25)`）。
- 表：`*(0x728C20 + 0xC0) = *(0x728CE0) = 0x00B0C130`（堆，稀疏表）。
- `table[36]` = `RAM[0x00B0C1C0]` = **0**（表里只有 index 0..3 / 16 / 33 有值，其余全 0）。
- 传给访问器的索引来自栈：`sp=0x01FFE610` ⇒ `lw $5,88($29)` = `RAM[0x01FFE668]` = **`0x24` = 36**。

⇒ **访问器没有错，它如实返回"没有 36 号条目"；错的是调用方没判空。**

---

## 4. ★ 扰动实验：把"跳到 0"这一步坐实

改存档 `eeMemory.bin` 的 `RAM[0]`（`tools/iso_build/fix_zh118_patchstate.py`），
输入/盘/其余全部不变：

| RAM[0] | 预言 | 实测 |
|---|---|---|
| `0x0F2B1A00`（原值 = `jal 0x0CAC6800`） | 崩 PC = 0x0CAC6800 | **崩 f245, PC=0x0CAC6800** ✓ |
| `0x03E00008`（`jr $ra`，ra 此时 = 0x3F6050，正好跳回调用点的下一条） | **不再崩**，继续跑 | **`no recLUT trap`，干净跑完 600 帧** ✓✓ |
| `0x00000000`（`nop`） | 崩 PC 改由 RAM[4..] 决定 | **崩 f245, PC=0x401A6000** ✓ |

第三条还能对上账：`nop` 后 `lw $25,0($2)` 得到 0 ⇒ `lw $25,792($25)` = `RAM[0x318]`
= `00 60 1A 40` = **`0x401A6000`** —— 与实测崩溃 PC **逐位相等**。
（此时轨迹末项是 `003F6038`，块 0 **没有**被进入，因为 `jalr` 直接跳到了 0x401A6000。）

⇒ **崩溃 PC 完全由"EE 物理地址 0 处的内容"决定**，链条锁死，没有任何别的解释空间。

---

## 5. 结论：不是汉化引入

| 证据 | 内容 |
|---|---|
| ① | **未改动的英文原盘** + 同一存档 + 同一 R1 ⇒ 同帧同 PC 崩（§2 第 6 行） |
| ② | 把存档 RAM 里**汉化 ELF 与英文 ELF 不同的 1850 个字节全部还原**，再配英文原盘 ⇒ 照样崩（§2 第 7/8 行） |
| ③ | 崩溃代码路径（`0x3F5xxx/0x3F6xxx`、`0x193Exx`、`0x365Exx`、`0x366Axx`）**0 个补丁字节**；补丁只落在 `0x407xxx-0x417xxx`、`0x565xxx-0x578xxx`、`0x219xxx-0x21Dxxx` 等区 |
| ④ | 加载存档后 **CDVD 一次都没读过盘**（36585 次读全在 frame 0）⇒ 汉化盘内容不可能影响这段执行 |
| ⑤ | 崩溃 PC 由 **EE 物理地址 0 的内容**决定（§4 扰动实验，三条预言全中）——那是记忆卡目录缓冲区，与汉化无关 |
| ⑥ | **用户侧 pcsx2-qt 自己的会话日志**（§2.1，非本轮产物）：5 次同一报错、每次 `PC=0x0cac6800`，且模拟器核心自己打印 `TLB Miss, pc=0x0` ⇒ 同一现场在用户环境里独立重现 |

根因是**原版游戏的空指针虚调用**：
`0x003F6038` 处的代码在 `$2 == 0` 时仍然 `lw $25,0($2)` 解引用，把物理地址 0 当虚表用。

**残留的（尚未闭合的）缺口，如实列出**：存档 RAM 里还有**存档生成前从汉化盘载入的模块/字库数据**
（不是 ELF 代码，撤不掉，因为我们没有"英文盘在同一进度点的 RAM"做对照）。
但按 ③④⑤ + ① 的独立性，这一缺口不足以推翻结论；若要彻底闭合，需要
**冷启动 EN_ORIG → 读用户记忆卡战役存档 → 打到同一位置**（约 30~60 min 脚本化游玩，
上一轮 `REPORT_save_crash.md` §6 也把这个列为 TODO）。

---

## 6. 用户侧怎么办（规避 / 说明）

1. **这不是汉化造成的**，换英文原盘、把汉化补丁全撤都一样崩 ⇒ 不必回退版本、不必重下盘。
2. 触发点是"**在那一瞬间开火**"。可从这份存档出发的实测：不按 R1 / 按 cross / 按 R2
   都能正常跑；按 R1 必崩。所以**能绕开的具体动作**：
   - 换个时机开火（先移动/换姿势/等一两秒再开火）——空指针来自"查 36 号条目查不到"，
     这是**游戏运行时状态相关**的，也正是用户说"有的时候"才出现的原因；
   - 换武器 / 换个位置再开火（索引 36 是运行时算出来的一个 id）；
   - **⚠ 从用户这份即时存档出发是绕不开的**：`§2.1` 的 Qt 日志显示点掉对话框后
     立刻再触发（`Resuming` → 3 ms 后同一报错）⇒ **必须从更早的存档重来这一段**
     （读用户记忆卡里的战役存档，或游戏内更早的手动存档）。
3. **PCSX2 的这个报错本身**：`Jump to unmapped recLUT page` 是 PCSX2 的 JIT 诊断
   （EE 跳到一个没有重编译代码页的地址）。真机上不会是这条信息，但同样会跑飞 ——
   所以**真机大概率也会出问题**，只是症状不同。
4. 我试过一条**最小防御补丁**（把 `0x3F602C` 的 `beq $2,$0,0x3F6038` 改成直接跳过这次空调用
   `0x10400008`），实测**不能解决**：绕开空调用后流程转进内核异常/idle（`0x00081FE0`），
   最后仍然走到"跳到 0"⇒ 同一报错（`dump_nullguard`）。**⇒ 不建议打这个补丁**，记录在此免得再试。

---

## 7. 本轮新增 / 改动的文件

| 文件 | 作用 |
|---|---|
| `third_party/.../iR5900.cpp` | `g_eeTraceAllBlocks`（默认 false；逐块入口 trampoline 全开开关） |
| `third_party/.../pcsx2-gsrunner/GRResearch.cpp` `.h` | `-grpcring <n>` + `OnHostErrorReport()`（recLUT trap 现场快照）+ `WriteExecTrace()` |
| `third_party/.../pcsx2-gsrunner/Main.cpp` | `Host::ReportErrorAsync` 里调用 `GRResearch::OnHostErrorReport` |
| `tools/iso_build/fix_zh118_run.py` | gsrunner 封装（`--timeout` / `--outroot` / 自动 `-logfile` / `--pcring`） |
| `tools/iso_build/fix_zh118_probe.py` | 存档 eeMemory 提取 + 盘代指纹 + 「崩溃值是否在 RAM 里」搜索 |
| `tools/iso_build/fix_zh118_patchstate.py` | 对存档 `eeMemory.bin` 打任意字节补丁（扰动实验用） |
| `tools/iso_build/fix_zh118_regions.py` | 两个 EE RAM 镜像 + 任意区间的逐字节对照/dump |
| `tools/iso_build/fix_zh118_xref.py` | `jal` 调用点 / 数据字 / ASCII 的交叉引用搜索 |
| `work/builds/GR_ZH118/temp/` | 全部实机产物（见下表） |

主要产物目录：

| 目录 | 内容 |
|---|---|
| `dump_f111_fire1` / `dump_ring111_fire` | **复现 + 崩溃现场**（`reclut_crash.txt`、`reclut_f00000245_eeram.bin`） |
| `dump_f111_noinput` / `dump_f111_cross` / `dump_f111_r2` | 不触发对照 |
| `dump_en_fire1` / `dump_en_revert_fire` / `dump_zh_revert_fire` | **英文原盘 / 补丁全撤 对照** |
| `dump_pert_jrra` / `dump_pert_nop` | 扰动实验（`jr $ra` 不崩 / `nop` 换 PC） |
| `dump_nullguard` | 最小防御补丁尝试（失败，见 §6.4） |
| `probe/` | 存档 eeMemory 提取 + 指纹 + 值搜索 |

---

## 8. 未做 / 诚实清单

- **没有**做"冷启动 EN_ORIG + 用户记忆卡 + 打到同一位置"的完整对照（30~60 min 脚本化游玩），
  见 §5 残留缺口。
- **没有**穷举"哪些动作能绕开"（只测了 R1/R2/cross/不按）；用户报的是"有的时候"，
  间歇性来自运行时状态，本轮只给出机制与排查方向。
- 用户 Qt 前端用的是 `SCPH-90006_BIOS_VX_HK_2.20.bin`，本轮 gsrunner 仍是
  `SCPH-70012_BIOS_V12_USA_200.bin`（与 r70 同样的未排除混淆项）。但本轮的崩溃链
  完全在游戏代码里、且逐位可复算，BIOS 差异不影响结论。
- `0x728C20` 那个对象、`0xB0C130` 那张表**属于哪个子系统**（武器/小队/AI）没有最终定名：
  只查到它是虚表 `0x0059EAC0` 的槽 4 方法（`0x003F5FD0` 本身是另一张虚表的槽 2），
  索引 `36` 由 `0x00365E70 → 0x00365EA0 → jal 0x0015C8A0` 这条链算出。若有需要，
  可加 `-grpchook <pc>`（动态 hook 点列表）去抓 `0x3F6018`/`0x193E90` 入口的 `a0/a1`。
