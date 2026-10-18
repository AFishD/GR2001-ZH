# REPORT_zh_heap_corruption.md — round76：汉化引入的内存/状态损坏定位

> 执行者 = 汉化引入的内存/状态损坏定位子代理 · 2026-10-15 · 分支 `round73/font-decompile`
> （**未切分支、未 commit、未 merge**）
> 前置事实 = 用户实机 A/B：**英文原盘 `GR_EN_ORIG` 同一流程不崩且成功存档；汉化盘崩**
> ⇒ 前两轮 `docs/REPORT_reclut_crash*.md` 的"不是汉化"结论**已被推翻**，本报告**不引用**该结论。
> 产物 = `work/builds/GR_ZH98/temp/r76/**`、`third_party/emu/pcsx2_src/pcsx2-gsrunner/GRResearch.cpp`、
> 　　　`third_party/emu/pcsx2_src/pcsx2/x86/ix86-32/iR5900.cpp`（仅 3 行 hook 位）
> 用户证据 `work/temp/NEW_Mem/**` **一字未改**（所有读取都走只读副本到 `r76/mc/`）。

---

## 0. 一句话结论

**用"TLB Miss 行数"这个零成本指标，用户的两次会话给出了 50 : 0 的硬分离：**

| 会话 | 盘（用户自己的日志坐实） | BIOS | 时长 | `TLB Miss` 行数 | 首次出现 |
|---|---|---|---|---|---|
| `work/temp/NEW_Mem/emulog.txt`（09:49） | **`GR_ZH111.iso`**（CRC `7A361FB5`） | Japan v02.20 | ~600 s | **50（打满上限）** | **7.68 s** |
| `work/temp/NEW_Mem/emulog_1030.txt`（10:30） | `GR_ZH111.iso` | Japan v02.20 | 492 s 后崩 | **13** | **434.15 s** |
| `%LOCALAPPDATA%\PCSX2\logs\emulog.txt`（11:12） | **`GR_EN_ORIG.iso`**（CRC `3E571E95`） | Japan v02.20 | **874 s 正常退出** | **0** | — |

⇒ **汉化盘会话出现"分配器把越界地址当指针用"的缺页；英文原盘会话 874 秒一次都没有。**
⇒ 这**就是**本任务要求的"降级态"判据，而且它**不需要跑崩溃**、**不需要 pcring**、**只要读 emulog**。
⇒ 并且它把时间尺度改成：**异常最早出现在开机后 7.68 秒**（载入 ELF 后 6 秒），**不是"玩 7 分钟才坏"**。

**但没有拿到写入者**：本机 gsrunner（与分析机同一份 v2.8.2 源码）**复现不出这个缺页**（见 §4），
所以 Task A 的"写监控"只完成到**工具已实现、已编译、已封装**，**未抓到写入 PC**。
Task B 的**盘链二分未完成**（原因同：本机上没有可用的降级信号可测）。**如实列在 §7。**

---

## 1. 先把盘钉死：用户的汉化盘 = `GR_ZH111`，对照盘 = `GR_EN_ORIG`

用户日志自己写的，不是我推的：

```
[    0.3740] isoFile open ok: C:\...\work\builds\GR_ZH111\GR_ZH111.iso
[    1.3804] ELF Loading: cdrom0:\SLUS_206.13;1, Game CRC = 7A361FB5, EntryPoint = 0x00100008
```
```
[    0.5281] isoFile open ok: C:\...\work\builds\GR_EN_ORIG\GR_EN_ORIG.iso
[    3.2065] ELF Loading: cdrom0:\SLUS_206.13;1, Game CRC = 3E571E95, EntryPoint = 0x00100008
```

| 用途 | 路径 | 时间 |
|---|---|---|
| 汉化盘（用户报障那一版） | `work/builds/GR_ZH111/GR_ZH111.iso` | — |
| 英文对照盘 | `work/builds/GR_EN_ORIG/GR_EN_ORIG.iso` | — |
| 汉化会话 log（**有缺页**） | `work/temp/NEW_Mem/emulog_1030.txt`、`emulog.txt` | 10:30 / 09:49 |
| 英文会话 log（**零缺页**，874 s 正常退出 + 记忆卡存档成功） | `%LOCALAPPDATA%\PCSX2\logs\emulog.txt` | 11:12 |
| 英文会话的即时存档（**干净参考态**） | `%LOCALAPPDATA%\PCSX2\sstates\SLUS-20613 (3E571E95).{10,01,01.backup}.p2s` | 11:01 / 11:09 |
| 汉化会话的即时存档（已带潜在损坏） | `work/temp/NEW_Mem/SLUS-20613 (7A361FB5).01.p2s{,.backup}` | 09:49 |
| 两张记忆卡 | `work/temp/NEW_Mem/Mcd001.ps2`（9:52，汉化会话写的）<br>`%LOCALAPPDATA%\PCSX2\memcards\Mcd001.ps2`（11:12，**英文会话写的**） | — |

> ★ 本轮**新发现**的资源（前两轮都没用上）：`%LOCALAPPDATA%\PCSX2\sstates\` 里有一整套
> **CRC `3E571E95`（英文盘）的即时存档**，以及**英文会话自己写的记忆卡**。
> 这是"干净基线"，也是后面做盘链对照时唯一可信的起点。

---

## 2. 降级态判据（Task B 要的"统一判据"，已定案）

### 2.1 为什么用 `TLB Miss` 行数

`pcsx2/vtlb.cpp:537-549`：

```cpp
const std::string message(fmt::format("TLB Miss, pc=0x{:x} addr=0x{:x} [{}]", ...));
if (EmuConfig.Cpu.Recompiler.PauseOnTLBMiss) { ... }
static int spamStop = 0;
if (spamStop++ < 50 || IsDevBuild)
    Console.Error(message);
```

⇒ **Release 构建下每个进程最多打 50 行**，全部进 `-logfile`/emulog。
⇒ **"打满 50"本身就是"反复缺页"的硬证据**；行的时间戳给出**起始时刻**。
⇒ 这是**零成本**的：不需要 `--pcring`（前一轮的 pcring 会让 6600 万块全部记录，代价极高）。

### 2.2 用户两次汉化会话的缺页时间线（原文照抄）

**09:49 会话**（前 9 行，`work/temp/NEW_Mem/emulog.txt`）：

```
[    7.6807] TLB Miss, pc=0x1024e8 addr=0x10b2bef8 [store]
[    7.6810] TLB Miss, pc=0x102220 addr=0x10b2bef8 [store]     × 5
[    7.6820] TLB Miss, pc=0x3f6038 addr=0x0 [load]
[    7.6820] TLB Miss, pc=0x3f6038 addr=0x318 [load]
[    7.6820] TLB Miss, pc=0x0 addr=0x0 [load]                  × 3
```
然后同样的"三连"在 **54.22 s**、**73.32 s** … 反复出现，直到打满 50 行。

**10:30 会话**（`emulog_1030.txt`，共 13 行）：

```
[  434.1495] pc=0x101d10 addr=0x22d1624 [load]        ← 分配器 chunk_free
[  434.1497] pc=0x101dd8 addr=0x4154536f [store]
[  434.1500] pc=0x101de4 addr=0x22d1624 [load]
[  434.1501] pc=0x101e08 addr=0x22d162c [load]
[  434.1503] pc=0x101e34 addr=0x22d1630 [load]
[  434.1503] pc=0x101e34 addr=0x22d162c [load]
[  434.1506] pc=0x101e34 addr=0x14 [store]
[  434.1507] pc=0x101e34 addr=0x10 [store]
[  434.1510] pc=0x101e6c addr=0x22d161c [store]
[  492.8785] pc=0x25e86c addr=0x14 [load]             ← 58 s 后
[  492.8786] pc=0x0 addr=0x0 [load] × 3
[  492.8786] Trap exception at 0x00000000
```

### 2.3 判据给 Lead 的三条增量信息

1. **异常是"突发"而不是"持续降级"**：434.15 s 那 9 行全在 **1.5 ms** 之内（一次 `free()` 走坏链），
   之后 58 秒**再无缺页**，然后直接崩。
   ⇒ **前一轮 §6.2"从 434 s 起进入'每次 free 都缺页'的降级态、2fps 是它造成的"这个推断不成立**：
   用户日志里没有任何"持续缺页"。~2fps 与 HUD/天空盒损坏**另有原因**（§3.3）。
2. **10:30 会话开机是干净的**（首次缺页 434 s）；**09:49 会话开机就脏**（7.68 s）。
   ⇒ 损坏**不是**每次开机必然发生；它是**会话相关**的（同一张盘、同一 BIOS）。
3. **同一个"三连"签名在 09:49 会话里精确重复**（相同 `pc`、相同 `addr=0x10b2bef8`）
   ⇒ 不是随机噪声，而是**确定性的代码路径**在每次"状态切换"处走到坏数据。

---

## 3. 现场坐标复核（修正前两轮的两处误读）

### 3.1 `0x25E86C` 到底是什么指令 —— **它是 MMI，且 0x14 确实是"非空垃圾值"**

用 `work/builds/GR_ZH98/temp/r74/r74_mips.py dis 0x25E850 0x25E890` 逐条解码**现役 ELF 字节**：

```
0025e858  12000017  beq $s0, $zero, +96 -> 0x0025E8B8   ← 判空是有的
0025e86c  72002628  pcpyld $a0, $s0, $zero              ← ★ 这是 MMI 64 位搬移，不是取数
0025e870  8c990000  lw   $t9, 0($a0)                    ← ★ 真正缺页的是这条
0025e874  8f390034  lw   $t9, 52($t9)
0025e878  0320f809  jalr $t9
```

- PCSX2 报的是 `pc=0x25e86c addr=0x14 [load]`，而块内唯一的取数在 `0x25e870`（= 报出 PC + 4）。
  ⇒ **报出的 pc 比出错指令小 4**（与 MIPS "pc 指向延迟槽"的约定一致）。
- ⇒ 出错访问 = `lw $t9, 0($a0)`，**`$a0 = 0x14`**。
  ⇒ **`piVar2`（`RSList<Emitter>` 结点数据指针）确实是非空的小整数 `0x14`**，
  前一轮的这条结论**成立**（虽然推导路径不同）。**"加判空"治不了它。**
- ★ **新增**：`0x14` = 20 = **汉化自己 cave 里的一个常量**：`0x417028: addiu v0,zero,20`
  是图标字符（△/✕）的**字宽**；`0x41701C: lw v0,20(a0)` 是空格宽度。
  ⇒ **"0x14 出现在指针槽里"与"汉化文本层产出的布局整数"在数值上吻合**（见 §6 的修复方向）。

### 3.2 `chunk_free` 那两条 `addr=0x14 / addr=0x10` —— **不能当作"小整数进链表"的证据**

同法解码 `0x101E20..0x101E50`：

```
00101e34  8cc90014  lw  $t1, 20($a2)
00101e38  8cc60010  lw  $a2, 16($a2)
00101e3c  acc90014  sw  $t1, 20($a2)     ← unlink: fd->bk = bk
00101e40  ad260010  sw  $a2, 16($t1)     ← unlink: bk->fd = fd
```

若 `$a2 = $t1 = 0`，则两条 store 的**有效地址正好是 0x14 与 0x10** —— 与日志**逐字吻合**。
⇒ **`addr=0x14 / 0x10` 既可能是"小整数 0x14 进了指针槽"，也可能只是 NULL + 结构体偏移**；
前一轮 §3.1 把它当成"同一类小整数损坏"**证据不足**，本报告不再沿用。
（`0x4154536f` 那一条的"不是字符串"结论仍然有效，因为它是 `addr` 不是值。）

### 3.3 `0x3f6038`（"跳 0"那条链）在**开机 7.68 秒**就出现过

`pc=0x3f6038 addr=0x0 [load]` + `pc=0x0 addr=0x0 ×3` 正是前一轮那个确定性复现链
（`AwarenessMgr::HandleControllerFiredWeapon` → `GetGameObject` 返回 0 → 不判空 → 跳 0）。
⇒ 它在用户的汉化会话里**反复出现**（7.68 / 54.22 / 73.32 s…），而**在英文会话里 874 秒一次都没有**。
⇒ 这条链**不是**"玩了很久才累积出来的"，而是**汉化会话从早期就带着的对象/注册表不一致**。

---

## 4. ★ 本机复现失败：这是本轮最大的限制（如实记录）

### 4.1 做了什么

| # | 盘 | BIOS | 输入 | 帧数 | `TLB Miss` |
|---|---|---|---|---|---|
| 1 | `GR_ZH111` | Europe v01.60（gsrunner 默认） | 无 | 300 | 0 |
| 2 | `GR_ZH111` | Europe v01.60 | 开机→读记忆卡→载入存档→主菜单→战役→任务 7→游玩 | 4600 | 0 |
| 3 | `GR_ZH111` | Europe v01.60 | 同上 + 菜单深探 | 7600 | 0 |
| 4 | `GR_ZH111` | **Japan v02.20（用户同款，Console 20060905-125923）** | 无 | 4000 | **0** |
| 5 | `GR_ZH111` | Japan v02.20 + `vuThread=0`（MTVU 关，用户配置） | 无 | 4000 | **0** |

- **BIOS 已对齐**（新增 `-grbios` / `-grbiosname`，见 §5.2；日志实测
  `BIOS Found: Japan v02.20(05/09/2006) Console 20060905-125923`，与用户完全一致）。
- **记忆卡已对齐**（用用户卡的只读副本 `r76/mc_zh/Mcd001.ps2`）。
- **ISO 就是用户那一个文件**（`work/builds/GR_ZH111/GR_ZH111.iso`，CRC 一致）。
- **模拟器版本已对齐**：gsrunner `PCSX2 v2.8.2-1-gcd5e3304c`，用户 `PCSX2 v2.8.2`，
  `Savestate version: 0x9a590000` 两者相同；两者都启用 Fastmem。
- ⇒ **仍然一次缺页都没有。**

### 4.2 因此可以确定的结论

> **用户那两次缺页不是"汉化盘在干净环境下必然复现"的行为**，
> 它需要用户环境里**额外的某个条件**。已排除：BIOS、模拟器版本、记忆卡、ISO 文件本身、汉化/英文之别。

### 4.3 还没排除的差异（下一轮的第一件事）

gsrunner 读的是**过期配置**：日志显示它把 data root 定在 `Documents\PCSX2`
（`BIOS Found: ... Searching for a BIOS image in 'C:\Users\84363\Documents\PCSX2\bios'`），
于是它用的是 **`Documents\PCSX2\inis\PCSX2.ini`（2024-10-30 的旧文件）**，
而用户实际跑的是 **`%LOCALAPPDATA%\PCSX2\inis\PCSX2.ini`（2026-10-15 10:57）**：

| 键 | 用户（生效） | gsrunner 读到 | 影响 |
|---|---|---|---|
| `EmuCore/Speedhacks` `vuThread` | **false** | **true** | MTVU：VU1 上另一线程 ⇒ 时序完全不同 |
| `EmuCore` `EnableFastBoot` | 缺省 | **true** | 跳过 BIOS 引导段 |
| `EmuCore` `EnableWideScreenPatches` | false | **true** | 会加载 pnach（本游戏无匹配文件，应无影响） |
| `EmuCore` `EnablePatches` / `EnableCheats` | true / true | true / true | 同上 |

我加了 `-grsetting` 并把 `vuThread` 强设为 0（第 5 行），**仍未复现**；
⇒ **要么该 override 没有真正生效到 VM（需要复核），要么真正起作用的是别的键**。
**下一轮必须做的第一步**：把 gsrunner 的 data root / ini 直接指向用户的
`%LOCALAPPDATA%\PCSX2`（一行 `EmuFolders::DataRoot` override，属于已授权文件），
把配置差异一次性消掉，再重跑第 4 行那个 4000 帧的短测试。

---

## 5. Task A：写监控（工具已落地并编译通过，但未抓到写入者）

### 5.1 为什么不用 `-grmemwatch`

现成的 `-grmemwatch <addr> <size> <interval>` 是**按帧轮询**（`FrameTick` 里采样），
只告诉你"第几帧变了"，**给不出写入者 PC**。而本任务的问句是"谁把 0x14 写进那个指针槽"。

### 5.2 本轮新增的四个开关（全部**默认关闭、零开销**）

| 开关 | 语义 | 实现位置 |
|---|---|---|
| **`-grwatch <addr> <size>`**（可重复） | **块粒度 EE RAM 写监控**：借 zh16b/r72 已有的"每个基本块入口回调"蹦床，在每个块入口比对被监控区间；一变就写 `watch.txt`：`hit/frame/cycle/addr/size/writer_block/cur_block/old/new`，并附**最近 64 个块起始 PC**。**`writer_block` = 值改变时正在执行的块 ⇒ 写指令就在该块体内**，离线用 MIPS 解码器即可定位到具体 store。<br>⚠ 只归因 **EE 代码**的写；若变化来自 IOP/DMA/GS 侧，会记到"当时恰好在跑的块"，属强提示而非证明。 | `GRResearch.cpp`（`Watch`/`DrawHookTrampoline`） |
| **`-grhook <pc>`**（可重复） | 在这些块入口打印 `a0..a3/v0/s0/s1/ra/sp` 到 `hooklog.txt`（上限 20 万行）。用来盯分配器入口 / 文本层函数。 | 同上 |
| **`-grbios <dir>` / `-grbiosname <file>`** | 覆盖 BIOS 搜索目录与文件名（本机 gsrunner 默认抓 Europe v01.60，用户跑 Japan v02.20）。 | `GRResearch.cpp`（`ApplyFolderSettings`） |
| **`-grsetting <section> <key> <int>`**（可重复） | 启动前强行覆盖任意模拟器设置（用来对齐用户配置）。 | 同上 |

配套的**唯一** hook 点改动（`pcsx2/x86/ix86-32/iR5900.cpp`，**3 行**）：

```cpp
bool (*g_eeExtraHookPC)(u32 pc) = nullptr;      // 默认 null ⇒ 行为与改动前完全相同
static bool grIsDrawHookPC(u32 pc)
{
    return g_eeDrawHook &&
        (g_eeTraceAllBlocks || (g_eeExtraHookPC && g_eeExtraHookPC(pc)) || ... );
}
```

### 5.3 编译与构建（已验证）

- 那两个被改的 .cpp **单独编译通过**（`ninja .../iR5900.cpp.obj .../GRResearch.cpp.obj`）。
- **整机链接也已通过**：用仓内官方脚本
  `$env:MVC_ROOT='C:\Users\84363\pbt\msvc'; bash tools/emu_build/build_pcsx2.sh`
  （该脚本的关键点：`INCLUDE` 里必须带 `...\3rdparty\vulkan\include`，
  否则 `GS/Renderers/DX11/D3D.cpp` 会因缺 `vulkan/vulkan.h` 而**整体链接失败**——这是**既有坑，与本轮改动无关**）。
  ⇒ 增量 2 个 .cpp + 链接 ≈ 90 s；产物 `third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe`
  已更新到 2026-10-15 11:45（9801216 B）。
- ⚠ **注意**：链接要求 `pcsx2-gsrunner.exe` 不被占用；卸载前必须先停掉自己起的实例。

### 5.4 没抓到写入者的原因

写监控必须挂在**某个具体地址**上，而"哪个地址会被写坏"取决于复现（§4 未复现）。
唯一确定的受害者地址（§3.1 的 `RSList<Emitter>` 结点、§3.3 的对象表）都只在**用户已损坏存档**里成立，
而那份存档在任何盘上都会崩（前一轮四臂实验），**动不了损坏的产生时刻**。
⇒ **工具就位，缺的是"能复现的环境"。**

---

## 6. 最小可信修复/规避方向（分"已定案"与"推测"）

### 6.1 已定案（有日志/字节级证据）

1. **降级态可零成本判定**：数 emulog 里的 `TLB Miss` 行（上限 50）+ 看首行时间戳。汉化 50、英文 0。
2. **异常最早出现在开机后 7.68 s**，并且"跳 0"链（`pc=0x3f6038`）在早期就反复出现。
3. **`0x14` 是汉化 cave 自己的常量（字宽 20）**，且它出现在指针槽里 ⇒ 方向是
   **"UI/字形布局产出的整数写到了指针位置"**，不是"字符串太长踩坏缓冲"。
4. **本机 gsrunner 复现不出**（BIOS/版本/记忆卡/ISO 全部对齐后仍是 0 缺页）⇒
   复现依赖用户环境的某个配置项，**不能再用本机"跑不崩"当反证**。

### 6.2 推测（未验证，但可判定）

- **H1｜文本层把布局整数写进指针槽**（最高优先）：
  汉化把 `CharWidth`（`0x21AD10` → cave `0x416F40`）、`StringWidth`（`0x21AC90` → cave `0x565670`）、
  `ComputeCharTextureCoords`（`0x21ADE0` → cave `0x417050`）、字符解码（`0x219BCC` → cave `0x416ED0`）
  全部换成了按 **u16 码位 + 2 字节步进** 的新实现。
  只要**任何一处"按字符数开缓冲、按字节数写"（或反之）**，就会逐字符地写越界，
  写入的内容正好是 **u16 码位 / 字宽（0x10、0x14、0x1C 量级）** —— 与现场坏值同型。
  **判定实验**：`-grwatch` 盯住文本 mesh 缓冲与相邻对象头，在复现环境里跑几分钟，看 `writer_block` 是否落在 `0x219xxx`/`0x416Exxx`/`0x4170xx`。
- **H2｜布局相关的流式读取竞态**：汉化重排了 `MENU.IMG`/`GR.IMG`（条目搬迁）与 `COMMON.PAK`，
  改变了 CDVD 读取的长度/时序；游戏的流式装载代码若有时序假设，就可能留下**未初始化/陈旧指针**，
  之后被 `pc=0x1024e8 addr=0x10b2bef8 [store]` 这类写打出来。
  **支持它的证据**：同一个模拟器版本 + 同一张盘 + 同一 BIOS 在本机不复现 ⇒ 触发条件是"时序/配置敏感"的；
  而用户环境里盘 A/B 分离得很干净。
  **判定实验**：把 gsrunner 的配置与用户完全对齐（§4.3）后重跑；若复现，则逐个关闭 speedhack 定位到具体键。

### 6.3 规避（给用户，立即可用）

1. **判据**：一旦看到"天空盒坏 / HUD 消失 / 掉到 2fps"，**立刻别按键**（按键=投递消息=跑 handler=崩），
   摇杆不崩；直接重启读记忆卡存档。
2. **别再用带损坏的即时存档**（`work/temp/NEW_Mem/SLUS-20613 (7A361FB5).01.p2s`）。
3. **崩溃报错 PC 永远是 `0x0cac6800`**（EE 物理 0 处记忆卡目录串 `BASLUS-20613GHOST002`
   的首字恰好编码成 `jal`）——**零诊断价值**，不要据此判断"同一个 bug"。

### 6.4 关键回归判据（给 Lead 的验收口径）

**任何"修复盘"都必须在用户的复现环境里把 `TLB Miss` 行数从 50 降到 0**
（或至少降到与英文盘同级的 0）。**不要再用"跑 10 分钟没崩"当验收。**

---

## 7. Task B：盘链二分 —— **未完成**（如实）

要求链：`GR_EN_ORIG → GR_ZH98 → GR_ZH109 → GR_ZH111 → GR_ZH113 → GR_ZH113b`
（六张盘都在 `work/builds/`，均已只读确认存在，未改动）。

**为什么没做**：二分的前提是"每一版都能测出一个可比的降级信号"。
本轮把判据（§2.1）定下来了，但**本机复现不出降级**（§4）：
六张盘在本机都会读出 `TLB Miss = 0`，**没有任何区分度**，跑完也只是六行 0。
硬跑六次并不能得到"第一次出现损坏的那一版"，只会得到六份无法解释的空结果。

**已经为下一轮准备好的东西**（一旦 §4.3 的配置对齐做完，二分就是机械劳动）：

```powershell
# 每张盘各跑一次（≈70 s/张），只数 TLB 行数
foreach ($v in 'GR_EN_ORIG','GR_ZH98','GR_ZH109','GR_ZH111','GR_ZH113','GR_ZH113b') {
  python tools\iso_build\fix_zh118_run.py `
    --iso   "C:\...\work\builds\$v\$v.iso" `
    --tag   "r76_bisect_$v" --maxframes 4000 --snap 0 --timeout 400 `
    --memcards "C:\...\work\builds\GR_ZH98\temp\r76\mc_zh" `
    --outroot  "C:\...\work\builds\GR_ZH98\temp\r76" `
    --grswitch "-grbios <r76\bios_jp>" `
    --grswitch "-grbiosname SCPH-90006_BIOS_VX_HK_2.20.bin"
  (Select-String "$out\dump_r76_bisect_$v\emulog.txt" -Pattern 'TLB Miss').Count
}
```

**另外一个被本轮否掉的老判据**：`-grpcsample` **不能**用来测降级率 ——
它每 4 帧在 vsync 处采一次 `cpuRegs.pc`，采到的永远是同一处
（`work/builds/GR_ZH98/temp/r74/dump_r74_r1only/pcsample.txt` 76 行全是 `00411fb0`）。

---

## 8. 已定案 vs 推测（一览）

| # | 命题 | 状态 | 证据 |
|---|---|---|---|
| 1 | 用户汉化盘 = `GR_ZH111`（CRC `7A361FB5`）；对照 = `GR_EN_ORIG`（`3E571E95`） | **已定案** | 用户两份 emulog 的 `isoFile open ok` / `Game CRC` |
| 2 | 汉化会话出现分配器越界缺页（09:49 打满 50；10:30 共 13 行）；英文会话 874 s **0 行** | **已定案** | 三份 emulog 计数（§0/§2） |
| 3 | 异常最早出现在开机后 **7.68 s**；"跳 0"链早期反复出现 | **已定案** | §2.2、§3.3 |
| 4 | 434 s 那次是**一次突发**（1.5 ms 内 9 行），不是持续降级；"2fps=持续缺页"不成立 | **已定案** | `emulog_1030.txt` 时间戳 |
| 5 | `0x25E86C` 是 `pcpyld`，真正缺页的是 `0x25E870` 的 `lw $t9,0($a0)`，`$a0 = 0x14` | **已定案** | 逐条字节解码（§3.1） |
| 6 | `0x14` = 20 = 汉化 cave 的图标字宽常量 | **已定案** | `0x417028 addiu v0,zero,20`（§3.1） |
| 7 | `chunk_free` 的 `addr=0x14/0x10` **不能**单独证明"小整数进链表"（NULL+偏移同样成立） | **已定案（否证前一轮的一条）** | §3.2 |
| 8 | 本机 gsrunner 在 BIOS/版本/记忆卡/ISO 全对齐后**仍复现不出缺页** | **已定案** | §4.1 五行实验 |
| 9 | 复现依赖用户环境的某个配置项（首疑 MTVU / FastBoot / data-root 不一致） | **推测** | §4.3 的设置表 |
| 10 | H1：文本层把"每字符布局整数/码位"写进了指针槽（缓冲按字符数开、按字节数写之类） | **推测** | §6.2；数值同型 + 补丁面全在文本层 |
| 11 | H2：条目搬迁改变了 CDVD 流式读取时序，暴露游戏自身竞态 | **推测** | §6.2；本机不复现 ⇒ 时序敏感 |
| 12 | 谁把 `0x14` 写进去的（写入者 PC） | **未定案** | §5.4：工具就位，缺可复现环境 |
| 13 | 盘链二分：第一次出现损坏的版本 | **未定案** | §7：本机无区分度信号 |

---

## 9. 未定案部分与下一步需要什么

1. **需要用户环境的一份"可比配置"**（最高优先，成本最低）：
   - 要么把 `%LOCALAPPDATA%\PCSX2\inis\PCSX2.ini` 原样交给我们（只读），
     以便把 gsrunner 的 data root 指过去（一行 override，属已授权文件）；
   - 要么请用户按**固定配置**（`vuThread=false`、`fastCDVD=false`、`EECycleRate=0`、
     `EnableFastBoot=false`、clamp/rounding = 默认）重跑一次汉化盘 + 一次英文盘，各 3 分钟，
     并把两份 emulog 给我们。**只要复现，二分 + 写监控都能立刻做。**
2. **需要一份"早期"的即时存档**：用户下一次复现时，请在**第一次看到天空盒/HUD 异常的那一帧**
   立刻存即时存档（slot 2，别覆盖 slot 1）。这一份能把"损坏窗口"夹到几秒内，
   `-grwatch` 挂上去基本一定抓到写入者。
3. **本轮无法交付的东西**（不要当已解决）：
   写入者身份、二分版本、2fps/天空盒/HUD 的直接成因。
4. **给 Lead 的一句话**：
   "汉化引入"这条**已经被用户日志以 50:0 的缺页计数坐实**；
   但**本机复现不出**，所以**下一步不是继续在模拟器里猜，而是先把用户的配置对齐**——
   对齐之后，`-grwatch`（已实现、已编译）就能给出写入者 PC。

---

## 10. 纪律自查

- ✅ 未切分支（全程 `round73/font-decompile`）、未 commit、未 merge
- ✅ 用户证据 `work/temp/NEW_Mem/**` **只读**（两个 p2s、两张卡、三份 emulog 都只读；
  记忆卡副本落在 `work/builds/GR_ZH98/temp/r76/mc/`）
- ✅ 历史 ISO **只读**（未写入任何 build 目录；未新建 `GR_ZH119`）
- ✅ **未改** `tools/text_csv/*`、`font_compact.py`、`make_build.py`、`tools/font_pipeline/data/*`
- ✅ 模拟器源码只改了 **`GRResearch.cpp`**、**`iR5900.cpp`（3 行 hook 位）**，
  改动**全部默认关闭**；未改 `Main.cpp`（不需要）
- ✅ **未杀任何别人的进程**（起跑前后各查一次 `*pcsx2*`，全程 0 个外部实例；
  自己起的 gsrunner 全部跑完自行退出；长跑那次是我自己主动 kill 的）
- ✅ 写盘范围仅：`docs/REPORT_zh_heap_corruption.md`、`work/builds/GR_ZH98/temp/r76/**`
  （外加上述两处已授权的模拟器源码）
- ✅ 未用 `Select-Object -First N`

---

## 11. 附：本轮产物索引（`work/builds/GR_ZH98/temp/r76/`）

| 文件 | 说明 |
|---|---|
| `r76_probe.py` | p2s 条目列表 / CRC32（只读） |
| `r76_shot.py` → `shots/*.png` | 从 8 份即时存档里抽出内嵌截图（判断会话场景） |
| `r76_mcdiff.py` | 汉化卡 vs 英文卡的战役存档逐字节对照（结论：两份存档进度不同，83% 字节不同，**无法据此判定损坏**） |
| `r76_mknav.py` → `nav_boot_play.txt` / `nav_long_zh.txt` / `nav_menu_probe.txt` | 冷启动→读记忆卡→载入存档→主菜单→战役→任务 7→游玩的输入表（**实测可达 in-level**，见下） |
| `dump_r76_boot2_zh111/`、`dump_r76_navprobe/` | 上述流程的实跑证据（截图 + emulog） |
| `dump_r76_zh111_jpbios/`、`dump_r76_zh111_mtvu0/` | 用户 BIOS / MTVU=0 的对照跑（**均 0 缺页**） |
| `bios_jp/` | 用户同款 BIOS 的只读副本（`SCPH-90006_BIOS_VX_HK_2.20.*`） |
| `mc/`、`mc_zh/` | 两张记忆卡的只读副本（`user_before_zh.ps2` = 汉化会话卡；`host_after_en.ps2` = 英文会话卡） |

**可达 in-level 的输入表实测帧号**（供后续轮直接复用）：

```
800..2602    start ×10           跳过 logo / Press START
2720, 2840   up ×2               「选择文件」初亮在「新建」，up×2 → 槽 1
3150         cross               载入 BASLUS-20613GHOST001
3600, 3900   down ×2             主菜单：训练 → 战役
4200         cross               进入「战役」
4700         cross               接受 → 任务 7 载入
≈7400                            in-level（截图确认，HUD/天空盒正常）
```

> ★ 启发式修正：`work/builds/GR_ZH99/temp/verify/nav_menu.txt` 里"up×3 到槽 1"在本卡上**不成立**
> ——本卡有 2 个存档，up×3 会绕回「新建」并进入「输入名字」屏（本轮实测截图
> `dump_r76_boot_zh111/snap_f00003300.png`）。**up×2 才对。**
