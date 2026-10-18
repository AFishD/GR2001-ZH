# REPORT — 模拟器设置与用户官方 PCSX2 全面同步（SLUS-20613 / GR 汉化工程）

- 日期：2026-10-17（本机时区 Asia/Hong_Kong）
- 执行者：EMU_SETTINGS_SYNC 执行者（子 agent）
- 用户数据根（**全程只读**）：`C:\Users\84363\AppData\Local\PCSX2`（portable 安装：安装目录 = 数据根，`portable.txt` 空文件 + `portable.ini: RunWizard=0` + `qt.conf: Plugins=./QtPlugins`）
- 产出：差异矩阵 `work\builds\GR_SYNC\A_key_matrix.md|csv`、私有数据根 `work\builds\GR_SYNC\data\PCSX2\`、一键脚本 `work\builds\GR_SYNC\run_synced.ps1`、9 个 run 的现场证据 `work\builds\GR_SYNC\runs\*\evidence.txt`
- **用户数据根未被写入的证明**：`work\builds\GR_SYNC\USER_ROOT_VERIFY.txt` → `VERDICT: UNTOUCHED (byte-identical to the pre-run baseline)`（4803/4803 文件，len+mtime+sha256 全部与跑前基线一致）

## 0. 一句话结论

1. **差异表要点**：用户 ini 330 个键里 **95 个在他们自己的官方 2.8.2 里也是死键**（键名不存在于其 exe 字符串表 → 被静默忽略）；真正"行为面"的差异只有少数几条，最要紧的是 **`EmuCore/Speedhacks/vuThread`：用户 `false`（MTVU 关）、我们 **`true`**（MTVU 开，源码 `VMManager.cpp:3597` 按 ≥3 核的硬件默认强开，日志实证 `MTVU speedhack is enabled`）**。
2. **私有数据根 + 一键脚本已建成并自证**：`-datapath work\builds\GR_SYNC\data` ⇒ 真实 DataRoot 为 `…\data\PCSX2`（源码 `Pcsx2Config.cpp:2252` 会拼 `PCSX2`）；启动日志逐目录回读全部落在私有根，且 ini 被**回写到私有根**；跑前跑后用户目录 hash 不变。
3. **★ 同步后复现形态没有改变**：仍是我们原有的 `Trap at 0x80000274`（890,287 行），`TLB Miss` **0 行**；单键二分 5 组（`fastmem` / `vuThread` / `VsyncEnable` / GS 后端 DX11-vs-DX12 / 整份用户配置）**全部不变**，其中 4 组连第 40–46 帧的 EE RAM 都**逐字节相同**。
4. ⇒ **没有哪个设置键决定形态差异**；设置不是用户 `TLB Miss` 与我们的 `Trap` 之间差异的原因。我们的现场读数（第 44 帧爆发改写、写者块 `0x005391BC`/`0x004039BC`、第 45 帧执行垃圾）**可以外推到用户机器**（同一份存档 + 同一张盘 + 同一 BIOS，且该改写是客户机代码的确定性行为）。
5. 操作层发现（会影响以后的实验）：**`-grsetting` 只能设布尔键**——它先 `SetIntValue` 再 `SetBoolValue`（`GRResearch.cpp:1013-1018`），整型键会被覆盖成字符串 `"true"` 从而解析失败退回默认值（校准证据见 §3.4）；整型键**必须走 `-ini`**，而 `-ini` 已被 SW 探针证明有效。
6. 地址口径澄清：任务书给的三对 hex/decimal 互相矛盾；实测 **`0x005391BC` / `0x004039BC` 是第 44 帧爆发改写的"写者代码块 PC"**（watch 日志的 `writer_block` 字段），不是被监视的数据地址（见 §3.5）。

---

# A. 清点与逐键对比

## A.1 用户数据根清点（只读）

| 项 | 内容 |
|---|---|
| `inis\PCSX2.ini` | 9956 B，2026-10-17 20:35:57（**故障会话结束后 1 秒**）。330 个键 |
| `inis\PCSX2.ini.bak_grtest` | 8758 B，2026-09-05（旧备份；`Renderer = 3`=DX11、`CdvdDumpBlocks=false`、旧手柄绑定） |
| `inis\playtime.dat` / `inis\debuggerlayouts\` / `debuggersettings\` | 非配置 |
| `PCSX2-ui.ini` | **不存在**（那是 Dolphin 的文件；本版 UI 键在 `PCSX2.ini` 的 `[UI]`） |
| `patches\` | **空目录**（无任何 pnach；全机 workspace 也搜不到 SLUS-20613 的 pnach） |
| `cheats\` | 3 个 pnach：`774DE8E2 / 93E998CA / A4DF1A15`，**均非本作**（`EnableCheats=true` 对本作无效果） |
| `gamesettings\` | 2 个：`SLPM-65266_A4DF1A15.ini`、`SLPM-65999_B7ADB13A.ini`，**非本作** |
| `bios\` | 40 个文件；ini 选中 `SCPH-90006_BIOS_VX_HK_2.20.bin`（+`.erom/.rom1/.rom2/.mec/.nvm`） |
| `memcards\` | `Mcd001.ps2` / `Mcd002.ps2`（各 8,650,752 B，2026-10-17 20:35:56，即故障会话） |
| `logs\emulog.txt` | 69,168 B，2026-10-17 20:35:56 → 用户侧故障签名（`TLB Miss, pc=0x1024d0 addr=0x8` 成对无限循环，**全程无 `Trap exception`**） |
| `cdvd-dump\` | 24 个 block dump；`LAY_fix1_bytecount (2026-10-17 20-31-56).dump`（70 MB）⇒ **用户故障会话跑的就是我们这张 `LAY_fix1_bytecount.iso`**（`CdvdDumpBlocks = true`） |

### sstates 清单（CRC 后缀 ↔ 盘，依据「同一会话的 cdvd-dump 起止时间」配对）

| 存档（CRC 后缀） | 大小 / 时间 | 同会话 cdvd-dump（起→止） | 归属 |
|---|---|---|---|
| `3E571E95`.01 / `.10` | 15,056,895 / 14,182,076（10-15 22:59 / 11:01） | 无对应 dump | 早期（疑英文原盘）血统 |
| `3E571E91`.01(+backup) | 15,296,669（10-15 23:11） | `SENT_02_icon_path_off`（22:54:16→23:11:06） | SENT 血统 |
| `7A361FB7`.01(+backup) | 15,729,262（10-15 20:19） | `GR_ZH113b_fix`（20:16:26→20:20:19） | **ZH113b_fix**（与任务书一致 ✓） |
| `7A361F8D`.01 | 14,646,514（10-17 19:57） | `DFIX_pkt`（19:52:57→19:57:14） | DFIX 血统 |
| `7A361FCA`.01 | 14,559,341（10-17 19:51） | `GR_REBUILD2400`（19:47:15→19:52:17） | REBUILD 血统 |
| `7A36E0B1`.01(+backup) | 14,783,402（10-17 15:16） | `SENT_06_icon_all_off_zh113b`（15:13:38→15:18:19） | SENT_06 血统 |
| `7A361FB5`.01/`.02` | 15,065,437（10-17 15:03）/15,148,220（10-15 10:56） | `GR_FA2400_K2`（15:08:20→15:13:09）时间相邻但档在 dump 之前，**归属未定** | GR_FA2400 血统（存疑） |
| **`7A761FCA`.01**(+backup) | **15,253,301（10-17 20:35:40）** | **`LAY_fix1_bytecount`（20:31:56→20:35:56）** | **本次复现用的 LAY_fix1 血统 ✓** |

> `7A761FCA` 与 workspace 的 `work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s` size/mtime/sha256 完全相同（前一轮已核对）。

## A.2 我们这边的配置（关键：gsrunner 根本不读 ini）

| 位置 | 角色 | 证据 |
|---|---|---|
| `Documents\PCSX2\inis\PCSX2.ini`（13,338 B，485 键） | **Qt 前端**的配置；`pcsx2-qt.exe`（含 `GR_HOOKEMU\qt` 那份）在无 `-datapath` 时用它 | 该 exe 目录下无 `portable.txt/portable.ini` ⇒ DataRoot = `Documents\PCSX2` |
| `work\builds\GR_REPRO\emu\gsrunner\pcsx2-gsrunner.exe` | 我们复现用的无头构筑 | 同目录无 portable 标记 ⇒ DataRoot 也是 `Documents\PCSX2`（仅用于 textures/cache/patches 等目录） |
| **gsrunner 的设置来源** | **不读任何 ini**：`Main.cpp:170-176` 用 `MemorySettingsInterface` + `VMManager::SetDefaultSettings(si,true,true,true,true,true)` + `LoadStartupSettings()` ⇒ **编译默认值 + 硬件默认值**，再叠加 `GSRunner::SettingsOverride()` 的研究模式强制项 | 这就是"两边键可能全不一样"的真正来源：**旧复现跑的是我们构筑的默认值，不是 `Documents\PCSX2\inis\PCSX2.ini`** |
| gsrunner 可用的设置入口 | `-ini <file>`（**只读 `[EmuCore/GS]` 一节**，`Main.cpp:760-781`）、`-grsetting <section> <key> <int>`（`GRResearch.cpp:798`，实际只对布尔键可靠，见 §3.4）、`-renderer/-upscale/-swthreads/-noshadercache` 等 | `-datapath` 在 gsrunner 中**不存在**（exe 字符串表无此串；`pcsx2-qt.exe` 有） |
| 无 `pwsh` | 本机只有 Windows PowerShell 5.1；且 .ps1 默认被 ExecutionPolicy 拦 | 所有脚本必须 `powershell -NoProfile -ExecutionPolicy Bypass -File …` |

## A.3 差异矩阵（完整表见 `work\builds\GR_SYNC\A_key_matrix.md` / `.csv`）

统计：并集 574 键；用户 330 / 我们 485；内容不同 408；用户独有 89、我们独有 244；**用户 ini 中 95 个键在用户自己的 exe 里不存在（死键）**、235 个有效。

### A.3.1 会影响行为/性能的键（逐键）

| section/key | 用户值 | 我们（gsrunner 实际生效值） | 影响面 | 备注 / 证据 |
|---|---|---|---|---|
| `EmuCore/Speedhacks/vuThread` | **false** | **true** | **行为/时序（唯一确凿项）** | 我们：`VMManager.cpp:3584-3611` 按核数写默认（本机 6 核 → true），日志实证 `MTVU speedhack is enabled, saved states may not be stable`；用户显式 false ⇒ 其 MTVU 关 |
| `EmuCore/CPU/Recompiler/EnableFastmem` | 未写 → 默认 true | true | 宿主代码生成（不改客户机语义） | `Pcsx2Config.cpp:455`；两边实际相同 |
| `EmuCore/CPU/Recompiler/PauseOnTLBMiss` | 未写 → false | false | 故障表现（暂停/继续） | `vtlb.cpp:538`；两边相同 ⇒ 不是 TLB Miss 的成因 |
| `EmuCore/CPU/FPU.Roundmode` | 3 | 3（默认 ChopZero） | 浮点行为 | `Pcsx2Config.cpp:33-41`；同步臂 3 相同 |
| `EmuCore/CPU/FPU.DenormalsAreZero` / `FPU.FlushToZero` | true / true | 默认 true（DAZ 键同时驱动 FTZ，源码 `Pcsx2Config.cpp:620`） | 浮点行为 | `FPU.FlushToZero` 在本版**不存在**（死键） |
| `EmuCore/CPU/VU.DenormalsAreZero` / `VU.FlushToZero` / `VU.Roundmode` | true / true / 3 | — **死键**（本版键名是 `VU0.*`/`VU1.*`，运行时拼名） | 浮点行为 | 用户这三行**未生效**，实际=默认（DAZ/FTZ on、ChopZero）⇒ 与我们相同 |
| `EmuCore/CPU/Recompiler/vuOverflow`(+Extra/Sign/Underflow) | true/false/… | — **死键**（本版 `vu0Overflow`/`vu1Overflow`） | VU 钳位 | 用户值无效 ⇒ 默认 true ⇒ 与我们相同 |
| `EmuCore/GS/Renderer` | **15 = DX12**（`Config.h` 枚举） | Auto(-1) → 本机自动解析为 DX12 | 渲染后端 | 实测两边都是 DX12（日志 `D3D12: Creating a 620x437 windowed swap chain`） |
| `EmuCore/GS/VsyncEnable` | 1 = true | false（默认） | 帧节奏 | 单键开关不变形态（§3.3） |
| `EmuCore/GS/upscale_multiplier` | **6（6× 原生）** | 1（默认） | 渲染负载 → 宿主性能 | 同步臂生效证据：Draw Calls 11551 vs 9217、**Uploads 2074 vs 69** |
| `EmuCore/GS/accurate_blending_unit` / `texture_preloading` / `filter` / `dithering_ps2` / `MaxAnisotropy` | 4(High) / 0 / 2 / 2 / 16 | 默认 1 / 2 / 2 / 2 / 16 | 渲染负载 | 差异（渲染面） |
| `EmuCore/GS/HWSpinGPUForReadbacks` / `HWSpinCPUForReadbacks` | true / true | false / false | 宿主线程同步 | 差异（渲染面） |
| `EmuCore/GS/extrathreads` | 2 | 3（硬件默认 `VMManager.cpp:3608`） | 仅 SW 渲染器 | 用 DX12，无实际影响 |
| `EmuCore/GS/FrameLimitEnable`、`FrameSkipEnable`、`FramesToDraw`、`FramesToSkip` | true/false/2/2 | — **死键** | 帧率 | 本版没有这些键（`Framerate/NominalScalar` 取而代之） |
| `EmuCore/GS/mipmap_hw` | 0 | — **死键**（本版 `hw_mipmap`，默认 true） | 渲染 | 用户以为关了 mipmap，实际仍是开 |
| `EmuCore/GS/interlace` | 7 | — **死键**（本版 `deinterlace_mode`，默认 0=Automatic） | 去隔行 | 用户值无效 |
| `EmuCore/GS/aa1` | true | — **死键**（本版 `HWAA1`，默认 false） | GS 边缘抗锯齿 | **用户以为开了 AA1，实际没开** |
| `EmuCore/GS/crc_hack_level` / `accurate_date` / `HWDisableReadbacks` / `linear_present` / `wrap_gs_mem` | 死键 | — | — | 均不在本版键表内 |
| `EmuCore/CdvdDumpBlocks` | **true**（`BlockDumpSaveDirectory=%LOCALAPPDATA%\PCSX2\cdvd-dump`） | false | 宿主 IO；会话留痕 | 用户每局都在写 block dump（我们据此把他们的盘对上号） |
| `EmuCore/CdvdVerboseReads` | false | false | 日志 | 相同 |
| `EmuCore/EnablePatches` / `EnableCheats` / `EnableWideScreenPatches` / `EnableNoInterlacingPatches` | true/true/false/true | 默认 true/true/true/false | 补丁 | **无 SLUS-20613 的 pnach / gamesettings ⇒ 对本故障无效果** |
| `EmuCore/HostFs` | false | false | 宿主文件系统 | 相同 |
| `Framerate/NominalScalar` / `TurboScalar` | 1 / 0 | 1 / 2 | 帧率 | 仅 Turbo 时不同，本次不触发 |
| `Logging/EnableVerbose` / `EnableFileLogging` / `EnableEEConsole` / `EnableSystemConsole` | true/true/true/false | gsrunner 研究模式强制 Verbose+FileLogging+Timestamps，EEConsole 默认 false | 日志 | 同步臂已把 EEConsole 置 true |
| `EmuCore/TraceLog/Enabled` | false | false | 指令级 trace | `EE.bitset`/`IOP.bitset` 是死键（本版是逐源布尔） |
| `Folders/*` | 相对路径（相对数据根） | 我们 run 目录；gsrunner 的 DataRoot=`Documents\PCSX2` | 路径 | 私有根已全部改写为私有根内绝对路径 |
| `Filenames/BIOS` | `SCPH-90006_BIOS_VX_HK_2.20.bin` | 同步臂同（旧 repro 也用同一个，`-grbiosname`） | 启动路径 | 一致；日志 `BIOS Found: Japan v02.20(05/09/2006)` 与用户 emulog 相同 |
| `MemoryCards/Slot1|2_Filename` + Enable | `Mcd001/Mcd002` + true | 同（`-grmemcards`） | 存档介质 | 一致 |
| `DEV9/Eth/*`、`DEV9/Hdd/*` | 全关（`AutoDNS1/2`、`HddSizeSectors` 是死键） | 全关 | 网络/硬盘 | 无影响 |
| `SPU2/Output/*` | cubeb / wasapi / Latency=100 / `OutputModule`(死) | gsrunner 设 `OutputModule=nullout`（**死键**）⇒ 实测仍开 Cubeb WASAPI（日志 `Creating Cubeb audio stream`） | 音频 | 不影响 EE 语义 |

### A.3.2 用户 ini 里的死键（他们自己的官方 exe 也不认）——95 个，摘录要紧的

`EmuCore/CPU/{VU.DenormalsAreZero,VU.FlushToZero,VU.Roundmode,FPU.FlushToZero}`、
`EmuCore/CPU/Recompiler/{vuOverflow,vuExtraOverflow,vuSignOverflow,vuUnderflow,PreBlockCheckEE,PreBlockCheckIOP,StackFrameChecks}`、
`EmuCore/GS/{mipmap_hw,interlace,aa1,FrameLimitEnable,FrameSkipEnable,FramesToDraw,FramesToSkip,crc_hack_level,accurate_date,linear_present,HWDisableReadbacks,conservative_framebuffer,wrap_gs_mem,ThreadedPresentation,disable_shader_cache,UserHacks_TriFilter,UserHacks_SkipDraw,UserHacks_SkipDraw_Offset,UserHacks_AutoFlush,UserHacks_Half_Bottom_Override,UserHacks_WildHack,OsdShowMessages,save*,shaderfx*}`、
`EmuCore/{EnablePerGameSettings,CdvdShareWrite,ConsoleToStdio,McdCompressNTFS,McdEnableEjection,MultitapPort*_Enabled}`、
`Framerate/{SkipOnLimit,SkipOnTurbo}`、`Folders/CheatsWS`、`MemoryCards/Multitap*`、
`SPU2/Mixing/*`、`SPU2/Output/{OutputModule,BackendName,SynchMode,SpeakerConfiguration}`、`DEV9/*` 若干、`Hotkeys/CycleMipmapMode`。

> 判定方法：把每个键名当作 NUL 结尾的 C 字符串在**用户自己的 `%LOCALAPPDATA%\PCSX2\pcsx2-qt.exe`** 里查找（脚本 `work\builds\GR_SYNC\tools\key_matrix.ps1`）。用户官方 exe（fileVersion **2.8.2.0**，见其 `crash-2026-10-15-*.txt`）与我们构筑（`v2.8.2-1-gcd5e3304c`）的**键表完全一致**，因此"死键"对两边同样成立。少数复合键名（`Slot{}_Enable`、`{}.Roundmode` 等）是按模板拼接，已人工复核（见 CSV 备注列）。

---

# B. 同步后的私有数据根（不动用户目录）

## B.1 布局与内容（49.1 MB）

```
work\builds\GR_SYNC\
├─ run_synced.ps1                 # 一键运行（两引擎 / 同步·基准 / 单键探测 / 回读校验）
├─ A_key_matrix.md|csv            # A 的差异矩阵
├─ USER_DATA_ROOT_BASELINE.csv    # 跑前用户目录全量基线（4803 文件 len+mtime+sha256）
├─ USER_ROOT_VERIFY.txt           # 跑后复核 → VERDICT: UNTOUCHED
├─ data\                          # ← -datapath 参数就是这一层
│   └─ PCSX2\                     # ← 真实 DataRoot（-datapath X ⇒ X\PCSX2）
│       ├─ inis\PCSX2.ini         # 用户 ini 的忠实副本（仅 3 类改写，见 B.2）
│       ├─ bios\SCPH-90006_BIOS_VX_HK_2.20.{bin,erom,rom1,rom2,mec,nvm}   # 8.4 MB，sha256 与用户原件相同
│       ├─ memcards\Mcd001.ps2, Mcd002.ps2                                # 17.3 MB，sha256 与用户原件相同
│       ├─ patches\               # 空（用户也是空）
│       ├─ cheats\                # 用户 3 个 pnach 原样
│       ├─ {logs,sstates,cache,snaps,textures,covers,inputprofiles,videos,cdvd-dump,cheats_ws,gamesettings,resources}\  # 空目录（模拟器只写这里）
│       └─ _sync\{ini_rewrites.diff, grsetting_sync.tsv, grsetting_skipped.txt, manifest.tsv}
└─ runs\<RunName>\{cmdline.txt, evidence.txt, watch.txt, pcsample.txt, grlog.txt, emulog.txt?}
```

`tools\`：`make_synced_root.ps1`（建根）、`key_matrix.ps1`（差异矩阵+二进制键识别）、`verify_user_root.ps1`（用户目录只读复核）、`compare_arms.py` / `collect_evidence.py`（对比与证据留存）。

## B.2 对 ini 的全部改写（`data\PCSX2\_sync\ini_rewrites.diff`）

1. `[Folders]` 全部键 → 私有根内**绝对路径**（原值多为 `bios\`、`sstates` 这类**相对数据根**的路径）；
2. `[EmuCore] BlockDumpSaveDirectory` → `<私有根>\cdvd-dump`（原值指向**用户自己的** `%LOCALAPPDATA%\PCSX2\cdvd-dump`）；
3. `[EmuCore/GS] Adapter` → **删除**（原值是他们那块 `NVIDIA GeForce RTX 5060 Ti`，本机是 RTX 4070 Ti SUPER / 另一台 3080，强行同步会导致选择适配器失败）；
4. 文件头加 8 行 `;` 注释说明来源与改写项。其余**逐字节保持**用户的键与值（含所有死键）。

## B.3 `-datapath` vs `portable.txt`：选 `-datapath`，理由

- `portable.txt` 的判定位置是**exe 所在目录**（`Pcsx2Config.cpp:2268`）。我们的 exe 在 `work\builds\GR_REPRO\emu\gsrunner\` / `work\builds\GR_HOOKEMU\qt\`，在那里放 `portable.txt` 会**改变既有实验环境**（那目录不在本任务的写入白名单内），且 `-portable` 与 `-datapath` 只存在于 Qt 前端，gsrunner 两者都没有。
- `-datapath` 显式、可回读、可写进 `cmdline.txt` 存档；实测语义：`-datapath X` ⇒ `DataRoot = X\PCSX2`（`Pcsx2Config.cpp:2252`）。**第一次探测时我把根放在了 `X` 本身，日志显示它去读 `X\PCSX2\inis\PCSX2.ini`（不存在）并打印 `Enabling MTVU.`（走了首次运行默认流程）**——这个反例正好证明了 datapath 的拼接语义与"没读到用户配置就会退回默认"的风险，修正后布局为 `data\PCSX2\`。

## B.4 回读证据（"确实用了私有根的配置、没写用户目录"）

`runs\qt_readback\`（`-Engine qt -QtMode testconfig`，exe = `GR_HOOKEMU\qt\pcsx2-qt.exe`）：

```
[    0.0415] DataRoot Directory: …\work\builds\GR_SYNC\data\PCSX2
[    0.0416] Loading config from …\work\builds\GR_SYNC\data\PCSX2\inis\PCSX2.ini.
[    0.0436] BIOS Directory:        …\data\PCSX2\bios
[    0.0436] MemoryCards Directory: …\data\PCSX2\memcards
[    0.0436] Patches Directory:     …\data\PCSX2\patches
[    0.0436] Cheats Directory:      …\data\PCSX2\cheats
[    0.0436] Logs/Savestates/Textures/Cache/… 全部在私有根内
```

- **没有** `Enabling MTVU.` 这行（对比 B.3 的反例）⇒ 读到的是用户 ini 的 `vuThread=false` 且 `SettingsVersion=1` 匹配，未套用硬件默认。
- 私有根的 `inis\PCSX2.ini` **mtime 被模拟器改写（21:27:38 → 21:27:44，11813→11907 B）**⇒ ini 回写位置确实是私有根；同时用户 ini 的 sha256 `E0C8FE7B…` 前后不变。
- 每个 run 的脚本输出都有：`USER TREE : files 4803 -> 4803 ; tree-hash 176B8C8A… -> 176B8C8A…`、`USER INI : sha256 E0C8FE7B… -> E0C8FE7B…`、`OK: user data root untouched`。
- 收尾全量复核（`USER_ROOT_VERIFY.txt`）：`CHANGED 0 / ADDED 0 / DELETED 0`，**VERDICT: UNTOUCHED**；私有根的 BIOS 6 件与两张记忆卡 sha256 与用户原件逐一 `IDENTICAL`。
- 诚实注记：最初基线里 3 个 `covers\…[Disc1of3].jpg` 因文件名含 `[]` 被 PowerShell 通配符吃掉、`sha` 为空；本次改用 `-LiteralPath` 补算并与基线 len+mtime 一致后回填，复核结论不受影响（详见 `USER_ROOT_VERIFY.txt`）。

## B.5 一键脚本用法

```powershell
# ① 与用户官方设置一致的运行（gsrunner；用私有根 bios/memcards/patches/cheats + 用户全部活键）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_SYNC\run_synced.ps1 -RunName s01_synced_l1
# ② 我们的旧默认（对照臂）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_SYNC\run_synced.ps1 -RunName b01_baseline_l1 -Settings baseline
# ③ 数据根模式（真读用户 ini 原文；无输入注入，用于路径回读/形态对照）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_SYNC\run_synced.ps1 -RunName qt_readback -Engine qt -QtMode testconfig
# ④ 单键布尔探测（整型键见规范，不能用 -grsetting）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_SYNC\run_synced.ps1 -RunName t_x -Settings baseline -SingleSetting 'EmuCore/Speedhacks;vuThread;0'
# ⑤ 整型/字符串键探测：做一份探针 ini（只改要测的键），用 -IniOnly
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_SYNC\run_synced.ps1 -RunName t_y -IniOnly -IniPath <probe.ini>
```

脚本内置纪律：起跑前轮询 `pcsx2*`（有他人实例就**抛错拒跑**，绝不 kill）；跑前跑后指纹比对用户目录；每个 run 从私有根**复制** BIOS/记忆卡到 run 目录（保证两臂输入字节相同、私有根不被写花）；`cmdline.txt` 存档完整命令行。

---

# C. 用同步设置重跑复现，与旧读数对比

共同条件（两臂完全相同，只有设置不同）：存档 `work\builds\GR_REPRO\common\state_LAY_fix1_bytecount.p2s`（= 用户 `7A761FCA` 存档）、盘 `work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso`、BIOS `SCPH-90006_BIOS_VX_HK_2.20.bin`、输入表 `in_l1_f30.txt`（`30 l1 press`）、`-grpcsample 1`、8 个 `-grwatch`（含十进制 `5480892/4213180/5613472` 与 hex 口径 `5476796/4209084/5617568`、r11 的 `5617584`、以及爆发区 `4864:256`）、`-grdumpwin 40 46`、`-grmaxframes 60`。

## C.1 运行矩阵

| run | 引擎/设置 | 关键差异 | 结果形态 | `Trap` 行数 | `TLB Miss` | `Unrec` |
|---|---|---|---|---|---|---|
| `s01_synced_l1` | gsrunner / **用户设置** | `-ini`(整节 `[EmuCore/GS]`) + 48 个 `-grsetting` 布尔（含 `vuThread=0`、`VsyncEnable=1`） | **Trap @0x80000274** | 890,287 | **0** | 53 |
| `b01_baseline_l1` | gsrunner / 我们的默认 | 无 `-ini`、无 `-grsetting`（= 旧 r07/r11 同款） | **Trap @0x80000274** | 890,286 | **0** | 53 |
| `t_key_vuthread0` | baseline + 单键 `vuThread=0` | MTVU 关 | Trap | 890,286 | 0 | 53 |
| `t_key_fastmem0` | baseline + 单键 `EnableFastmem=0` | fastmem 关 | Trap | 890,286 | 0 | 53 |
| `t_key_vsync1` | baseline + 单键 `VsyncEnable=1` | 垂直同步开 | Trap | 890,286 | 0 | 53 |
| `t_ini_dx11` | 探针 ini：`Renderer=3`(DX11) | GS 后端换 DX11 | Trap | 890,286 | 0 | 53 |
| `t_ini_probe` | 探针 ini：`Renderer=13`(SW) | **校准**：证明 `-ini` 生效 | 运行 20 帧无异常（对照用） | — | — | — |
| `t_probe_sw_grsetting` | baseline + `-grsetting …Renderer 13` | **校准**：证明 `-grsetting` 不能设整型 | — | — | — | — |
| （历史）`r07_pcring_l1` | 上一轮、46 帧 | — | Trap | 187,412 | 0 | 53 |

`pcsample.txt`（每 4 帧采样的当前块 PC，帧号→PC）：

| run | 40 | 44 | 48 | 52 | 56 |
|---|---|---|---|---|---|
| s01_synced_l1 | 004524b4 | 0042b364 | **800001f8** | 80000180 | 800001ac |
| b01_baseline_l1 / 4 个单键 | 00452498 | 0042b350 | **80000180** | 800001f8 | 80000180 |

⇒ 两条臂都在第 44→48 帧之间离开游戏代码区（`0x004…`）跳进 BIOS 低端异常向量区（`0x8000 01xx`），随后进入 `Trap` 死循环。

## C.2 写监视命中（`watch.txt`，块粒度写监视）

两臂**完全同构**：总命中 197、帧 ≥38 的命中 63、命中序列逐条同字节：

```
hit 2 frame=44 cycle=65030627342 addr=00001300 size=256 writer_block=005391BC cur_block=005391DC
      old=00801A3C0011427F… new=53801A3C0011427F…
hit 4 frame=44 … writer_block=004039BC cur_block=004039D8
hit 9 frame=44 … writer_block=005391BC
hit 11/13/16/18/21 frame=44 … writer_block=004039BC / 005391BC …
```

⇒ **用户机器上必然也发生同一次爆发改写**（写者块 `0x005391BC`、`0x004039BC` 的写指令序列在两臂逐字节一致），这就是"我们的读数可外推"的直接依据。`0x00001300..0x1400` 被逐字节覆写（BIOS 低端/异常向量区在 EE RAM 的映射）。

## C.3 EE RAM 差分规模

- **臂内**每帧差分（`-grdumpwin` 的 `win_f000004X_eeram.bin`，32 MB）：`40→41` 58 KB、`41→42` 89 KB、`42→43` 107 B、`43→44` 31 KB、`44→45` 55 KB、`45→46` 2 B（两臂同量级；爆发帧就是 43→44）。
- **跨臂**：4 个单键探测（`vuThread`/`fastmem`/`VsyncEnable`/DX11）与 baseline 在第 40–46 帧**逐字节相同（sha256 相同）**⇒ 这些键对我们所复现的客户机状态**零影响**。
- 只有"整份用户设置"臂（s01）与 baseline 有 ~45 KB/32 MB（0.14%）差异，且 watch 里的 cycle 只差 32 个周期 ⇒ 是**宿主侧渲染负载（6× 上采样 + 关纹理预载）带来的时序抖动**传导到客户机计时器，不是语义差异；形态与爆发序列不变。

## C.4 校准：两个设置注入通道的有效性（这是 A/B 之外最有用的一条）

| 探针 | 做了什么 | 判据 | 结果 |
|---|---|---|---|
| `t_ini_probe` | `-ini` 指向把 `Renderer` 改成 13(SW) 的探针 ini | gsrunner 只在硬件渲染时累计 GS 统计（`Main.cpp:302` `if (GSIsHardwareRenderer())`）⇒ `@HWSTAT@ Draw Calls` 应≈0 | **Draw Calls = 0**（baseline 是 4148/9217/11551）⇒ **`-ini` 确实生效** ✓ |
| `t_probe_sw_grsetting` | `-grsetting EmuCore/GS Renderer 13` | 同上 | **Draw Calls = 4148**（仍是硬件）⇒ **`-grsetting` 对整型键无效**：`ApplyFolderSettings` 先 `SetIntValue(13)` 再 `SetBoolValue(true)`，后者把值覆盖成字符串 `"true"`，`GetIntValue` 解析失败退回默认（`GRResearch.cpp:1013-1018`） |

⇒ 因此同步方案定为：**整型/字符串键走 `-ini`（整节 `[EmuCore/GS]`，68 个键），布尔键走 `-grsetting`（48 个键）**；脚本已按此实现（`grsetting_sync.tsv` 里 GS 节被自动排除）。`vuThread=0` 生效有独立日志证据：synced 臂日志里**没有** `MTVU speedhack is enabled`（baseline 有）。

## C.5 ★ 形态是否改变 / 哪个键决定形态

**没有改变，也没有任何一个键决定形态。** 覆盖到的键：

- 全量：用户 330 键里**全部 235 个活键**（68 个 GS 键经 `-ini`、48 个非 GS 键经 `-grsetting`、其余字符串/路径类经 `-grbios/-grmemcards/-grbiosname` 或本身是默认值）。诚实注记：那 48 个 `-grsetting` 里有 4 个是整型/浮点键（`EECycleRate=0`、`EECycleSkip=0`、`FPU.Roundmode=3`、`Framerate/NominalScalar=1`），受 §C.4 的 clobber 影响**未真正生效**，但它们的用户值恰等于我们构筑的默认值（`EECycleRate` 默认 0、`NominalScalar` 默认 1、`FPU.Roundmode` 默认 `ChopZero`=`Pcsx2Config.cpp:33-41`），故不构成未同步项；
- 单键：`EmuCore/Speedhacks/vuThread`（任务点名的 MTVU）、`EmuCore/CPU/Recompiler/EnableFastmem`（任务点名的 fastmem）、`EmuCore/GS/VsyncEnable`、GS 后端 DX11/DX12/（Auto 实测=DX12）；
- 渲染面：6× 上采样 + `accurate_blending_unit=4` + `texture_preloading=0` + `HWSpin*Readbacks=1` + `fxaa` + `AspectRatio=16:9`（整节 `-ini` 带入）；
- 补丁/秘籍：`EnablePatches/EnableCheats=true`（**无 pnach 命中本作**，等于无影响）。

⇒ **结论：`TLB Miss` 循环 vs `Trap` 的形态差异不是设置造成的**；我们的复现读数可以外推到用户机器（同一存档、同一张 `LAY_fix1_bytecount` 盘、同一 BIOS；第 44 帧爆发改写的写者与字节序列在两臂逐字节一致）。

### 形态差异的候选解释（**假设，未做实验证实**，供下一步）

1. **JIT 块缓存（宿主态，存档不含）**：`Trap exception` 来自 `R5900OpcodeImpl.cpp:1240`（执行到 `TRAP` 类指令），`EE: Unrecognized op` 来自 `iR5900Misc.cpp:173`（重编译器现场解码到非法指令）；`TLB Miss` 来自 `vtlb.cpp:537`（**非致命**，记日志后按 0 继续）。EE 侧写内存**不会**清 EE 重编译缓存（全树只有 IOP 写、COP0 TLB 写、CDVD/SIF DMA 等路径调用 `psxCpu->Clear/recClear`，见 `IopMem.cpp:288/331/404`、`CDVD.cpp:1195`、`Sif1.cpp:62`、`COP0.cpp:260…`）。用户是**连续游玩 224 秒**的会话，游戏代码块早已编译进缓存 ⇒ 被覆写后仍执行**旧的已编译代码**，于是继续用坏指针做 load ⇒ 表现为 `TLB Miss` 循环；我们是**新进程 + 载入存档**，被覆写的块（异常向量）从未执行过 ⇒ 现场解码到垃圾 ⇒ `Unrecognized op` + `Trap`。
2. **会话更早的分叉**：用户 emulog 在存档前 **17 秒**（207.68 s）就已出现 `TLB Miss, pc=0x101d10 addr=0x14e228f7` 一类坏指针访问，而我们拿到的存档是 224.03 s 那一刻；他们的状态在存档前可能已经走上与我们不同的分支。
3. **二进制不同（未验证）**：用户官方 `pcsx2-qt.exe`（fileVersion 2.8.2.0，15.2 MB）与我们本地构筑（`v2.8.2-1-gcd5e3304c`，Qt 版 11.7 MB、带 GR 插桩）键表一致但**代码/编译配置不同**。官方 exe 的 CLI 没有输入注入能力（`-grinput` 只存在于我们的 gsrunner），因此"用他们的二进制复现"本轮**未达成**（见 §E）。

## C.6 地址口径澄清（任务书三对 hex/decimal 互相矛盾）

| 任务书 hex | 任务书 decimal | decimal 实际等于 | 实测该地址的角色 |
|---|---|---|---|
| `0x005391BC` | 5480892 | `0x0053A1BC` | 两者**都已监视**；`0x005391BC` 是**第 44 帧爆发的写者代码块 PC**（`writer_block=005391BC`），不是被改写的存储单元 |
| `0x004039BC` | 4213180 | `0x004049BC` | 同上：`0x004039BC` 是另一个写者块 PC |
| `0x0055B7A0` | 5613472 | `0x0055A7A0` | 该页在帧 1 起被游戏正常改写（`writer_block=001025AC…`），与本次故障无关 |

被真正覆写的数据区是 **`0x00001300`（256 B，第 44 帧，写者 `0x005391BC`/`0x004039BC`）**，与前一轮 `REPORT_SAVESTATE_REPRO.md` 的「第 44 帧覆写 `0x1000..0x4000`」一致。脚本因此把 8 个地址全部纳入监视。

---

# D. 以后跑任何实验的规范（命令模板）

> 目的：任何"复现/对比/取证"run 默认都应**与用户官方设置一致**，只有显式声明才退回我们的默认。

1) **默认同步运行（gsrunner，推荐）**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  work\builds\GR_SYNC\run_synced.ps1 -RunName <name> `
  [-InputFile <in.txt>] [-State <p2s>] [-Iso <iso>] [-MaxFrames 60] `
  [-WatchPairs '4864:256','5480892:4',...] [-DumpWin 40,46]
```
- 设置来源：`work\builds\GR_SYNC\data\PCSX2\inis\PCSX2.ini`（用户 ini 副本）→ 68 个 `[EmuCore/GS]` 键走 `-ini`，48 个非 GS 键（其中 44 个布尔可靠生效）走 `-grsetting`；
- BIOS/记忆卡/patches/cheats 全部来自私有根；每个 run 复制一份到 run 目录（私有根保持可复现）。

2) **对照臂（我们的旧默认）**：同一命令行加 `-Settings baseline`（这是唯一允许"不同步"的用法，且必须在报告里标注）。

3) **数据根模式（只有它真读用户 ini 原文）**：
```powershell
… -Engine qt -QtMode testconfig     # 秒级：验证 DataRoot/各目录/ini 回读
… -Engine qt -QtMode run            # 有界 GUI run：-nogui -batch -fastboot -statefile <p2s> -- <iso>
```
- `-datapath` 传**父目录**（脚本内部已处理 `data` vs `data\PCSX2`）；该模式**不能注入手柄输入**（Qt exe 没有 `-grinput`）。

4) **单键二分**：
- 布尔键：`-Settings baseline -SingleSetting '<section>;<key>;0|1'`（可 `|` 串联多组）；
- 整型/字符串键：**必须**做探针 ini（改一个键）+ `-IniOnly -IniPath <probe.ini>`；`-grsetting` 设整型会静默失效（§C.4）。

5) **纪律清单（每次都要做）**
- 跑前：`Get-PSDrive C` 看余量；轮询 `Get-Process pcsx2*`，**有他人实例只等不杀**（脚本会拒跑）；
- 跑前跑后各做一次用户目录指纹（脚本自动；收尾再跑 `verify_user_root.ps1` 全量 sha256 复核）；
- 地址一律**十进制**（该构筑 `-grwatch`/`-grmemwatch` 的 `0x` 前缀会被解析成 0）；
- 大日志/大 RAM dump：先用 `collect_evidence.py` 落 `evidence.txt`（含 dump 的 sha256），再删原始文件（本轮清掉 2.3 GB）；`-grmaxframes` 别超过需要的窗口；
- 本机没有 `pwsh`：脚本一律用 `powershell -NoProfile -ExecutionPolicy Bypass -File` 调用；
- 任何 run 的 `cmdline.txt` 必须留档（脚本自动写）。

---

# E. 未达成 / 限制（如实）

1. **"哪个键决定形态"无法给出——因为没有键决定**。12 次运行（9 次本轮 + r07 等历史）里 `TLB Miss` 出现 **0 次**；同步臂与 5 组单键探测全部维持 `Trap at 0x80000274`。故本条按任务书的"形态不变"分支结案：**设置不影响该故障，我们的读数可外推**。
2. **未能用用户自己的官方 `pcsx2-qt.exe` 做带输入注入的复现**：官方 exe 没有 `-grinput`/`-grstate`（只有 `-statefile`），无法在第 30 帧注入 L1；因此"二进制差异"这一假设本轮**未验证**（只做到"用私有数据根以官方 ini 启动 + `-testconfig` 回读"）。建议下一步：把《用户 exe 副本 + 私有根 + `-statefile`》跑起来，用**改过 Pad1 绑定**的私有 ini（把 L1 绑到键盘键）+ 窗口按键注入，或在我们的 gsrunner 上做"预热异常向量块"的实验来验证 §C.5 的 JIT 假设。
3. **JIT 块缓存假设未做实验证实**（只给了源码路径与推理）。
4. **逐帧 PC 环**：只用了 `-grpcsample`（4 帧采样）；`-grpcring` 未使用，因此"首个异常帧的精确 PC 轨迹"止于 4 帧粒度（帧 44→48 之间跳变）。
5. **`PCSX2-ui.ini` 不存在**（用户/我们都没有该文件），UI 类差异只能在 `PCSX2.ini` 的 `[UI]` 内比较。
6. 用户 `sstates\…(7A361FB5)` 的盘归属存疑（时间上 ß 与两个 dump 会话都不严格对齐）。
7. 私有根规模 49.1 MB（未复制 `sstates`/`cdvd-dump`/`covers` 等大件；任务只要求 inis/bios/memcards/patches/cheats）。

---

## 附：本轮产物与命令证据索引

| 文件 | 内容 |
|---|---|
| `work\builds\GR_SYNC\A_key_matrix.md` / `.csv` | 574 键逐键差异 + 是否存在于用户 exe / 我们 gsrunner exe |
| `work\builds\GR_SYNC\USER_DATA_ROOT_BASELINE.csv` | 跑前用户目录 4803 文件 len+mtime+sha256 |
| `work\builds\GR_SYNC\USER_ROOT_VERIFY.txt` | 跑后复核：0 changed / 0 added / 0 deleted，UNTOUCHED；私有根 BIOS/记忆卡与用户原件 IDENTICAL |
| `work\builds\GR_SYNC\data\PCSX2\_sync\ini_rewrites.diff` | 对用户 ini 的 3 类改写 + 头注释 |
| `work\builds\GR_SYNC\data\PCSX2\_sync\grsetting_sync.tsv` / `grsetting_skipped.txt` | 116 行同步键（68 行 GS → `-ini`、48 行非 GS → `-grsetting`）/ 65 行被跳过（其中 50 行为死键） |
| `work\builds\GR_SYNC\runs\<run>\cmdline.txt` | 每 run 的完整命令行（s01 为 3237 B，48 组 `-grsetting`） |
| `work\builds\GR_SYNC\runs\<run>\evidence.txt` | 该 run 的异常普查、首异常行、渲染器/MTVU/BIOS 回读、watch.txt、pcsample.txt、RAM dump 的 sha256 |
| `work\builds\GR_SYNC\tools\{make_synced_root,key_matrix,verify_user_root}.ps1`、`{compare_arms,collect_evidence}.py` | 全部可重跑 |
| `docs\REPORT_SAVESTATE_REPRO.md` | 上一轮的现场报告（本轮的对照基准） |
