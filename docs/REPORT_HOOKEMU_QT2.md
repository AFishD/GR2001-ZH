# 报告：QT2 —— 「像官方一样直接用」的带钩子 PCSX2（幽灵行动 SLUS-206.13 汉化取证版）

- 日期：2026-10-17 23:00 → 2026-10-18 01:xx（本机时区 Asia/Hong_Kong）
- 执行者：QT2 执行者（AI）
- 成品：`work\builds\GR_HOOKEMU_QT2\qt\`（便携版，双击 `pcsx2-qt.exe` 即用，**零命令行参数**）
- 一键重建：`work\builds\GR_HOOKEMU_QT2\build_qt2.ps1`
- 补丁（相对 `third_party\emu\pcsx2_src`）：`work\builds\GR_HOOKEMU_QT2\hooks_qt2.patch`
- 用户手册：`docs\HOOKEMU_QT2_GUIDE.md`

---

## 0. 一句话结论

1. **上一版黑屏+崩溃已定位并复现**：不是渲染器、不是数据根、不是资源缺失，而是**内存监视把客户机代码页接管了**。
   上一版即使**不加 `-hook`**，`hook\hook_config.ini` 里的 `enabled = 1` 也会被自动读取 → `memReset()` 里把
   `0x00500000-0x00581000` 的 129 页重映射成 vtlb 慢路径 handler；这 129 页里**有客户机代码页**
   （实测 0051A000/0051B000/0051C000/0051D000/00537000/0053A000/0053D000/0053E000/00542000/0054C000/0054D000），
   代码一旦走 handler，PCSX2 的**取指**（`PSM()` 直接宿主指针）和**自修改代码保护**
   （`mmap_MarkCountedRamPage()`）都不成立 ⇒ 旧版表现为客户机执行垃圾（`TLB Miss` 风暴 → PC=0 → 永久黑屏），
   新版（延迟武装、只走慢路径 C 钩子）走到帧 154 时在 `recRecompile` 内宿主崩溃（`0xC0000005`）。
2. **QT2 的成品已经跑通**：零参数双击 → 载入 `GR_REBUILD2400.iso` → 8 分钟跑到 **帧 28588**（≈953 个 30 帧快照），
   `TLB Miss 0 / Trap 0 / Unrecognized 0`，24 张窗口截图亮度 19.9–96.4（**从不黑屏**），
   `emulog.txt` 里 **3,810,000 条写监视命中**（精确到指令 PC/宽度/值）。
3. 钩子**默认开**且**默认延迟武装**（BIOS 阶段完全不插桩），全部输出写进 `logs\emulog.txt`，
   F10 热键（真实按键验证）与 `TRIGGER` 文件两种触发都实测落盘成功。

---

## 1. A：黑屏诊断（含对照实验，全部本机实跑）

### 1.1 用户那次失败的直接证据（机器级）

| 证据 | 内容 |
| --- | --- |
| Windows 应用程序错误 | `2026-10-17 22:57:18`，出错应用程序 **`...\work\builds\GR_HOOKEMU\qt\pcsx2-qt.exe`**（版本 0.0.0.0 = 本地构筑，不是官方的 2.8.2.0），异常代码 `0xc0000005`，出错模块 `unknown`，错误偏移 `0x0` |
| WER 事件 1001 | `22:57:21`，事件名 `BEX64`，P1=`pcsx2-qt.exe`，P7=`PCH_84_FROM_unknown+0x0`，P8=`c0000005` |
| 数据根痕迹 | `Documents\PCSX2\inis\PCSX2.ini` mtime `22:56:31`、`Documents\PCSX2\cache\d3d12_pipelines_sm51.bin` mtime `22:57:04` ⇒ 用户是**双击**运行的（没有 `-datapath`，DataRoot 落在 `Documents\PCSX2`），崩溃前 GS 已经在建 D3D12 管线 |
| 同时存在的他人实例 | `pid=396` 官方 `%LOCALAPPDATA%\PCSX2\pcsx2-qt.exe`（22:54:13 启动，CPU 9 秒，闲置窗口）— **只记录，从未操作** |

> 注：上一版 `Documents\PCSX2` 那份 ini 里 `EnableFileLogging = false`，所以那次崩溃**没有留下 emulog**（这也是"看不到日志"的原因之一）；QT2 用自己内置的数据根并强制打开文件日志。

### 1.2 对照实验矩阵（旧 `GR_HOOKEMU\qt\pcsx2-qt.exe`，全部用私有数据根副本，用户目录零写入）

| # | 命令要点 | 结果（截图亮度 / emulog 关键行） | 结论 |
| --- | --- | --- | --- |
| D0 | 旧 exe + Documents 配置副本（BIOS SCPH-70000 JPN）+ `GR_REBUILD2400.iso`，**不加 -hook** | 200 秒全黑（亮度恒定 **23.15**）；emulog `TLB Miss` **46** 行，首行 `[4.7488] TLB Miss, pc=0x1019ec addr=0x8 [store]`（ELF 开始执行后 **48 ms**），末行 `pc=0x0 addr=0x20` | 复现黑屏 |
| D7 | 旧 exe + **官方配置副本**（DX12 / 6× / SCPH-90006）+ 同 ISO | 150 秒全黑（亮度恒定 **13**）；同样 46 行 TLB storm，首行一字不差；emulog 里 `HookWatch: 129 watched page(s) remapped`、`ranges=1` | **不是数据根/BIOS/设置的问题** |
| D6 | **官方 exe**（用户 `%LOCALAPPDATA%\PCSX2` 副本）+ 官方配置 + 同 ISO | 亮度 19.4→52.4 变化；`TLB Miss 0`；日志有 `FMV started/ended`、`Dumping 512x512 texture …`、Pad 配置 | 盘和配置都没问题 ⇒ 差别在我们的构筑 |
| D8 | **旧 exe 去掉 hook 配置**（钩子关）+ 官方配置 + 同 ISO | 亮度 17.4→103.3 变化；`TLB Miss 0` | **是我们的钩子，不是 exe 构建缺陷** |
| E1 | 旧 exe + `watch = none`（钩子开、但没有任何监视区间）+ 官方配置 | 亮度 17.4→72.8 变化；`TLB Miss 0`；`HookWatch: dumping … hook_250_pc_00101D10`（触发 PC 正常落盘） | 块钩子/异常钩子/落盘都没问题 ⇒ 问题**只在"内存监视"** |

### 1.3 历史日志复查（上一轮为什么没发现）

`work\builds\GR_HOOKEMU\val\runs\` 22 个 run 的 `emulog.txt` 逐个统计：

- 凡 `HookWatch: ACTIVE … ranges=1` 的 run（`final1`、`final2`、`hook_val7/8`、`hook11..17`、`hook4/5/6`）→ **全部**在 `… is executing` 之后立刻出现同一个 `TLB Miss` storm（46–50 行，首行 `pc=0x1019ec addr=0x8 [store]`）。
- `hook13`（`watch = none`）、`control_old`（无钩子）→ `TLB Miss 0`。
- 上一轮报告的"Qt 版跑到帧 2095、端到端可用"对应的日志 `GR_HOOKEMU\qt\hookdumps\qt_emulog.txt`：**同样 46 行 TLB storm，首行一字不差**（`[4.8576] TLB Miss, pc=0x1019ec addr=0x8 [store]`）。

⇒ **上一轮"帧 2095 / exit 0"只证明了模拟器进程没崩，游戏画面其实早就黑屏了**（EE 卡在 PC=0 空转，帧号照样涨）。这也是本轮新增"窗口截图亮度"验收项的原因。

### 1.4 确切原因与证明

**原因**：监视区间 `0x00500000-0x00580000` 覆盖了**客户机代码页**；被监视页被映射成 vtlb handler 后，

- 重编译器取指走 `PSM(pc)`（`Memory.h:150` → `vtlb_GetPhyPtr`，即"直接宿主指针"），handler 页拿不到真实指针 ⇒ 编译出垃圾/不存在的代码；
- 自修改代码保护 `memory_protect_recompiled_code()` → `mmap_MarkCountedRamPage()`（`vtlb.cpp:1461`）按 `PSM()` 反推 rampage 并 `MemProtect(&eeMem->Main[rampage<<12])` ⇒ 指针非法 ⇒ 宿主访问违例。

**证明（对照 + 符号解析）**：

1. E1（`watch = none`）正常、D8（钩子关）正常、D0/D7（有监视区间）黑屏 ⇒ 变量唯一。
2. 新构筑（延迟武装 + 只走慢路径 C 钩子 + **不排除代码页**）第一次运行时在帧 154 宿主崩溃：`crash_info.txt` =
   `HOST CRASH code=C0000005 rip_off=3E285D frame=154 ee_pc=0053EBE0 epc=00411AE8`；
   用新加的 `/MAP` + `tools\symlookup.ps1` 解析得 **`?recRecompile@@YAXI@Z +0x17D`**（EE 重编译器内部）。
3. 在 `recRecompile()` 入口加"代码页自动取消监视"后，同一命令立刻恢复正常（`TLB Miss 0`），
   并且日志明确列出被取消监视的代码页（0051A000…0054D000 共 11 页，见 §2.2）。
4. 旧版 `0x00580000-0x00600000` 会崩的旧结论需要修正为：**不是"越过 0x580000"这件事本身**，而是那一带同样是代码页；
   0x580000 以下（0053A000、0053D000、0053E000、00542000）同样是代码页，同样会崩。

### 1.5 用户那次崩溃点为什么"错误偏移 0x0"

用户的 WER 记录是 `出错模块 unknown / 偏移 0x0`（典型的"跳到 0 执行"）。我们本机可复现的崩溃有**两种**表现：
客户机侧（旧版：执行垃圾 → `TLB Miss` → PC=0 → 黑屏，与用户"读盘后直接黑屏"一致，且用户那次的 `ReShade.log`/ini 痕迹说明它确实跑到了 GS 阶段）
与宿主侧（新版未排除代码页时：`recRecompile` 内 `0xC0000005`，与用户"一段时间后崩溃"一致）。
**结论：黑屏与崩溃同源（代码页被 handler 接管），只是崩在哪一层取决于时序。**

---

## 2. B：QT2 成品

### 2.1 目录与「零参数怎么用」

```
work\builds\GR_HOOKEMU_QT2\
├─ qt\                     ← ★ 便携成品（双击 pcsx2-qt.exe 即用）
│   ├─ pcsx2-qt.exe        11,762,688 B（PCSX2 2.8.2 + QT2 钩子）
│   ├─ Qt6*.dll / SDL3.dll / D3D12\ / QtPlugins\ / platforms\ …（Qt 运行库，windeployqt 部署）
│   ├─ resources\          必须（shaders/GameIndex/fonts…）
│   ├─ translations\       PCSX2 与 Qt 的中文界面翻译
│   ├─ hook\hook_config.ini 钩子配置（默认已开；唯一需要改的文件）
│   ├─ portable.txt / portable.ini / qt.conf   ← 让 exe 目录成为数据根（与用户官方便携版同构）
│   ├─ inis\PCSX2.ini      用户官方设置的副本，[Folders] 全部改成相对路径
│   ├─ bios\ (6 files, 8.4 MB) / memcards\ (2×8.65 MB)  用户 BIOS 与记忆卡**副本**
│   ├─ logs\emulog.txt     ★ 钩子全部输出
│   ├─ hookdumps\          取证输出（hook_<帧号>_<原因>\）
│   └─ README_怎么用.txt    面向非开发者
├─ hook\hook_config.ini    配置模板（部署时复制到 qt\hook\）
├─ src\                    打了 QT2 补丁的 PCSX2 源码副本
├─ build\                  Ninja 构建树（含 pcsx2-qt.map，用于把崩溃 RIP 解析成函数）
├─ build_qt2.ps1           一键重建 + 重新部署
├─ hooks_qt2.patch         对 third_party\emu\pcsx2_src 的完整 diff（git apply --check 通过）
├─ tools\{emu_run,c1_long_run,send_key,symlookup,make_portable_data}.ps1
└─ runs\                   本轮全部验证现场（截图/summary/日志副本）
```

**零参数用法**（= 双击）：

1. 进 `work\builds\GR_HOOKEMU_QT2\qt\`，双击 `pcsx2-qt.exe`（或把 `.iso` 拖到 exe 上）；
2. 系统 → 启动光盘 → 选盘（与官方 PCSX2 完全一样）；
3. 卡死时按 **F10**，或在 `hookdumps\` 里放一个名为 `TRIGGER` 的空文件；
4. 去 `logs\emulog.txt` 看 `HookWatch:` 行；要回传的就是 `logs\emulog.txt` + `hookdumps\hook_*\`。

不需要 `-hook`、不需要 `-datapath`、不需要任何环境变量。

### 2.2 钩子默认开 + 延迟武装（实现方式）

| 需求 | 实现 | 位置 |
| --- | --- | --- |
| 默认开 | `InitializeFromEnvironment()`：环境变量 → `<exe>\hook\hook_config.ini` → **内置默认（仍然开）**；`enabled = 0` 或放一个 `hook\OFF` 文件或 `-nohook` 才关 | `pcsx2/HookTools/HookWatch.cpp` |
| 延迟武装 | 新开关 `arm_after = auto`（默认）＝ **游戏 ELF 装载后** 或 **读即时存档后** 武装，兜底 `arm_frame = 900`；`immediate` 保留旧行为 | `HookWatch::OnElfLoaded/OnStateLoaded/OnFrame`，调用点 `VMManager::UpdateELFInfo()`、`VMManager::DoLoadState()` |
| 启动阶段不插桩 | `memReset()` 里的 `InstallMemoryHandlers()` 改为只在 `ShouldArmAtBoot()`（= immediate 模式）时执行；武装前 `IsWatchingMemory()` 为 false ⇒ JIT 一个字节都不生成 | `pcsx2/Memory.cpp` |
| 武装动作 | ① `vtlb_MapHandler` 写物理映射；② 对 kuseg/kseg0/kseg1 三个别名逐页 `vtlb_VMap()` 重建虚拟映射；③ `vtlb_ResetFastmem()` 全量重建 fastmem（避免 4 MB 合并页出现"记账说映射了、实际没映射"的陈旧状态） | `HookWatch::ArmNow()` |
| **代码页自动豁免**（本轮新增，关键修复） | `recRecompile()` 入口调用 `HookWatch::OnCodeFetch(pc)`：该页只要在监视集合里，就**先**恢复成普通 RAM（pmap + 三个别名 + fastmem）再取指；武装时还会把"已经有编译块"的页提前剔除（`mmap_GetRamPageInfo != ProtMode_None`） | `pcsx2/x86/ix86-32/iR5900.cpp` + `HookWatch::OnCodeFetch/RestoreRamPage` |
| 精确 PC | JIT 在慢路径访问前只写一条 `mov [g_current_access_pc], pc`；C 钩子用它当 PC（块级 PC 作兜底） | `recVTLB.cpp` `EmitHookWatchAccessPC()` |
| 记录方式 | `jit_hooks = 1`（默认）：慢路径 C 钩子 + 重编译器调用式钩子（给出精确 PC/宽度/值）；旧的 `0` 只走 C 钩子（EE 的 JIT store 不会记录） | `recVTLB.cpp` / `HookWatch.cpp` |
| 监视默认区间 | `watch = 0x00500000-0x00580000`（含 `0x0055B7A0` 分配器状态、`0x0055BB98` 桶 126 槽），**代码页会被自动剔除** | `HookWatch::FinalizeInit()` |
| 其他 | `force_slowmem` 默认 0；`ring_entries = 262144`；`max_dumps = 8`；`log_every = 2000` | `hook\hook_config.ini` |

### 2.3 输出全部进 emulog.txt

`emulog.txt`（= `<数据根>\logs\emulog.txt`，QT2 里就是 `qt\logs\emulog.txt`）里会出现：

```
HookWatch: ACTIVE (QT2) source=command line config='...\qt\hook\hook_config.ini'
HookWatch: watch=00500000-00580000 arm_after=auto arm_frame=900 ring=262144 entries dumpdir='...\qt\hookdumps'
HookWatch: hook output goes to the emulator log (...\qt\logs\emulog.txt)
HookWatch: waiting to arm (BIOS boot phase is NOT instrumented)
HookWatch: game ELF loaded: 'cdrom0:\SLUS_206.13;1' entry=0x00100008
HookWatch: 129 watched page(s) remapped to the slow RAM handler
HookWatch: ARMED (reason=elf_loaded frame=6): watch=active -> 129 page(s) on the slow RAM handler (kuseg+kseg0+kseg1 aliases), fastmem mapping rebuilt
HookWatch: recording: slow-path C hook + optional JIT hooks (jit_hooks=1); ...
HookWatch: page 0053E000 holds guest code -> un-watched (code must stay on ordinary RAM)
HookWatch: watch hits=2000 frame=243 last: pc=0040DDFC addr=00563A3A size=16 W value=0000000000000720
HookWatch: watch hits=3810000 frame=28588 last: pc=004039A0 addr=00570150 size=64 W value=001FD00000000000
HookWatch: F10 pressed (frame 14272) -> dumping
HookWatch: dumping to ...\hookdumps\hook_14272_hotkey_f10
HookWatch: dump dir (absolute): ...\hookdumps\hook_14272_hotkey_f10
HookWatch:   file: ...\hook_14272_hotkey_f10\ee_ram.bin  33554432 B (32.0 MB)
HookWatch:   file: ...\hook_14272_hotkey_f10\ring.txt  14114010 B (13.5 MB)
HookWatch: top writer PCs (… unique, showing up to 20): 00414DC0x…
HookWatch: ring tail (last 40 of 262144 records, chronological):
HookWatch:        262104 f=14272 pc=00414CEC addr=00570174 size=32 W src=1 value=0000000000003A5B
HookWatch: dump complete in 125 ms
```

- **命中摘要**：每 `log_every` 条写一行（默认 2000 条一行）。
- **触发落盘**：四类触发都打印原因/帧号；落盘后打印**绝对路径**与每个文件的**大小**，再打印"写得最多的 PC 排行"和"最近 40 条记录"。
- **异常/崩溃**：EE 致命异常打印 `EE EXCEPTION code=… (ExcCode=…) pc=…` 后落盘；
  宿主崩溃由链在 PCSX2 崩溃处理器上的 filter 写 `<dumpdir>\crash_info.txt`，**同时追加进 emulog.txt**。
- 大块二进制（`ee_ram.bin` 32 MB / `iop_ram.bin` 2 MB / `ring.bin` 6 MB / `watch_*.bin`）仍落独立目录，只在 emulog 里给路径。

### 2.4 四种触发（都保留，且都在本轮实测过）

| 触发 | 默认 | 本轮验证 |
| --- | --- | --- |
| [a] 触发 PC（12 个分配器 PC） | **默认关**（`dump_on_trigger = 0`；上一版默认开会在开局 5 秒内把 4 次额度用完） | 旧版/中间版本实测触发正常（`hook_250_pc_00101D10` 等 4 次） |
| [b] EE 致命异常 | 开（`exception_codes = 1,2,3,4,5,6,7,10,13`） | 见 §3.3 的 OOMFIX 现场（异常/触发记录） |
| [c] **F10 热键** | 开 | **真实按键**（`tools\send_key.ps1` 发 `VK_F10`）→ `F10 pressed (frame 14272/14300/14325/14351/14376) -> dumping`，5 个 `hook_*_hotkey_f10` 落盘 |
| [d] `TRIGGER` 文件 | 开 | 真建文件 → `TRIGGER file found (frame 17830) -> dumping`，`hook_17830_file_trigger` 落盘，文件改名 `TRIGGER.done_17830` |
| [e] **EE 致命跳转**（本轮新增） | 开 | `recError()`（跳进未映射 recLUT 页 / 未对齐地址）时**在 PCSX2 暂停 VM 之前**自动落盘；C2 实测：帧 13212 `pc=7E7E7E7E` → `hook_13212_fatal_jump_7E7E7E7E` |
| （附加）`auto_input` | 关 | 用于复现"第 30 帧按 L1"：`auto_input = 30 L1 5`，帧号**从武装那一刻起算**（读存档场景必需） |

---

## 3. C：验证（全部本机实跑，数字都在）

### 3.1 C1 端到端（成品，零参数）

命令（等价于双击 exe 后载入光盘）：

```
work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe work\builds\GR_REBUILD\GR_REBUILD2400.iso
```

（脚本 `tools\c1_long_run.ps1`，仅做窗口截图 + 第 240 秒按 F10 + 第 300 秒放 TRIGGER；**没有加任何钩子参数**）

| 指标 | 结果 |
| --- | --- |
| 运行时长 | **483 秒**（另有 223 秒的短跑 C1b：21 张截图、亮度 12.8–112.7） |
| 窗口截图 | **24 张**（每 20 秒一张），亮度 **19.92 – 96.43**，`lum < 3`（黑屏判据）**0 张**；截图里是真实游戏画面（FMV/场景，非黑屏） |
| 帧号 | 末条命中行 `frame=28588` ⇒ **≥6000 帧**（≈953 个 30 帧快照） |
| `TLB Miss` | **0** 行 |
| `Trap exception` | **0** 行 |
| `Unrecognized op` | **0** 行 |
| 钩子生效 | `ARKED reason=elf_loaded frame=6`；**watch hits = 3,810,000**（emulog 里 `watch hits=` 行 1,905 行） |
| 落盘 | F10 触发 5 个 dump（帧 14272/14300/14325/14351/14376）+ TRIGGER 触发 1 个（帧 17830）；每个 dump 7 个文件 ≈ 54 MB |
| 宿主崩溃 | 事件日志查询：**无** |
| 用户目录 | `%LOCALAPPDATA%\PCSX2` 与 `Documents\PCSX2` 在 23:00 之后**零文件被修改**（`LastWriteTime` 全 ≤ 22:57:04，即用户自己那次） |

**收尾复测**（最终成品 + 最终随包配置，仍然零参数）：123 秒、7 张截图（亮度 15.8–106.3、无黑屏）、
`TLB 0 / Trap 0`、**watch hits = 3,080,000**（末条 `frame=7085 pc=001025C4 addr=0055B7A0 size=64 W value=00000000157C80D0`
——正是分配器状态那一格）。

### 3.2 C2 复现能力回归（补丁存档 + L1）

命令（成品，只有“载入存档/载入盘”这两个正常参数；钩子参数为零）：

```
work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe -fastboot ^
  -statefile "work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s" ^
  "work\builds\GR_OOMFIX\OOMFIX_lay1.iso"
```

配置：`runs\cfg\C2_oomfix.ini`（`watch = 0x00500000-0x00580000` + `0x00001000-0x00002400`、`jit_hooks = 1`、
**`auto_input = 30 L1 5`** = 武装后第 30 帧按 L1 五帧）。选择该 config 用的是官方的 `PCSX2_HOOK_CONFIG` 环境变量
（只是为了让 L1 注入和落盘目录可控；成品默认配置本身也是钩子全开）。

| 指标 | 结果 |
| --- | --- |
| 武装 | `ARMED (reason=elf_loaded frame=0)`（存档帧基 13,169；`auto_input armed: L1 from frame 30 to 35`） |
| L1 复现 | `HookWatch: auto_input: L1 press at frame 30` / `release at frame 35` |
| 写监视命中 | **10,210 条**（`ring_total=10210`）；其中落到分配器所在页 `0x0055Bxxx` 的 **6,332 条** |
| 命中样本（精确 PC/宽度/值） | `00101EEC 0055B7A0 64 W value 00000000F209C9FE`（**分配器状态 0x0055B7A0**）、`00101F00 0055B83C 32 W value 0000000000B4F6E0`、`001020C8 0055B7C8 32 W value 000000000055B7B8` |
| 失败现场 | 帧 **13212**：`HookWatch: EE FATAL: jump to unaligned address pc=7E7E7E7E (frame=13212) -> taking a dump before the VM is paused`（这就是本工程的"堆元数据被写坏 → 跳进垃圾地址"故障；PCSX2 随即把 VM 暂停） |
| 落盘 | `runs\C2\hookdumps\hook_13212_fatal_jump_7E7E7E7E\`：`ee_ram.bin` 32 MB、`iop_ram.bin` 2 MB、`regs.txt` 38,750 B、`ring.txt` 539,947 B、`ring.bin` 245,040 B、`watch_00500000_00581000.bin` 528,384 B、`watch_00001000_00003000.bin` 8,192 B、`meta.txt` 1,175 B |
| emulog 记录 | 触发原因、帧号、**绝对路径**、每个文件大小、top writer PCs、最近 40 条记录（全在 `qt\logs\emulog.txt`） |

★ 本轮为此新增了**第 5 类触发**：EE 重编译器的致命跳转（`recError()`：跳进未映射 recLUT 页 / 未对齐地址）。
这类崩溃正是用户说的"卡死"现场，而 PCSX2 在 `recError()` 里会立刻 `SetPaused(true)`——
如果等用户手按 F10，帧已经不再推进，什么也抓不到。现在它会**在暂停之前自动落盘**（上面这条 dump 就是这么来的）。

诚实注记：
- 该场景用的是 `-statefile`（读即时存档）。**读即时存档后 PCSX2 处于暂停状态**，需要按一次 `P` 让它继续；
  本轮的 C1（零参数、从光盘启动）不需要这一步。
- F10 与 `TRIGGER` 两条触发路径在 C2 场景里**没有**机会验证（游戏在 2.1 秒、用户按 F10 之前就已经崩了），
  它们的验证在 §3.1 的 C1 里完成（真实按键 + 真实文件）。

### 3.3 C3 黑屏回归（老版本黑 / 新版本不黑）

| 对照 | 版本 | 结果 |
| --- | --- | --- |
| 老版本（旧 `GR_HOOKEMU\qt`） | 2026-10-17 21:06 构筑 | D0/D7：**黑屏**（亮度恒定 13/23.15），46 行 `TLB Miss`，首行 `pc=0x1019ec addr=0x8 [store]` |
| 老版本 + 关钩子（D8） | 同上 | 正常（亮度 17–103，`TLB Miss 0`） |
| **新版本 QT2（零参数）** | 2026-10-18 00:xx 构筑 | **不黑**（24 张截图亮度 19.9–96.4，`TLB Miss 0`，帧 28588） |
| 新版本但 `jit_hooks=0`（C1b） | — | 也不黑（亮度 12.8–112.7），但 EE 的 JIT store 不记录（`ring_total=0`）⇒ 因此默认用 `jit_hooks=1` |

### 3.4 C1 复核：同核心的无界面跑（gsrunner，6000 帧 / 191 张快照）

用**同一份源码/同一份钩子配置**构建的 `pcsx2-gsrunner.exe` 做一次精确帧数的复核（这是唯一能精确指定帧数的前端）：

```
pcsx2-gsrunner.exe -grdumpdir runs\G1 -grmaxframes 6000 -grsnap 30 ^
  -grbios qt\bios -grbiosname SCPH-90006_BIOS_VX_HK_2.20.bin -grmemcards qt\memcards ^
  -logfile runs\G1\emulog.txt -- work\builds\GR_REBUILD\GR_REBUILD2400.iso
```

| 指标 | 结果 |
| --- | --- |
| 帧数 | **6000**（日志 `GR: === run end, frames=6000 ===`） |
| 真·GS 快照（PNG，`snap_f%08u.png`） | **191 张**（≥190 ✓，另有若干 needle 触发的 RAM dump，已清理） |
| `TLB Miss` / `Trap exception` | **0 / 0** |
| 写监视命中 | **2,564,000 条**（末条 `frame=5961 pc=004147D0 addr=00570170 size=32 W value=0`） |
| 记录宽度 | 32 / 64 / 128 位都正确记录（`size=` 字段） |

---

## 3.5 交付清单（本轮新增/改动）

| 路径 | 内容 |
| --- | --- |
| `work\builds\GR_HOOKEMU_QT2\qt\` | ★ 便携成品（exe + Qt 运行库 + `resources\` + `translations\` + `hook\` + 内置数据根 + `README_怎么用.txt`） |
| `...\qt\hook\hook_config.ini` | 钩子配置（钩子默认开、`arm_after=auto`、`jit_hooks=1`、`dump_on_trigger=0`、`max_dumps=8`） |
| `...\qt\inis\PCSX2.ini`、`bios\`、`memcards\` | 用户官方设置的副本；`[Folders]` 全部相对路径（`tools\make_portable_data.ps1` 生成） |
| `...\hooks_qt2.patch` | 75 KB；13 个文件；`git apply --check` **通过**（对 `third_party\emu\pcsx2_src`） |
| `...\build_qt2.ps1` | 一键重建 + 部署（含 `/MAP`、`portable.txt/ini`、`qt.conf`、translations） |
| `...\tools\emu_run.ps1` | 有界跑 + 窗口截图（黑屏判据）+ 崩溃事件采集 |
| `...\tools\c1_long_run.ps1` | 长跑 + 真按键 F10 + `TRIGGER` 文件 + 需要时的解除暂停 |
| `...\tools\send_key.ps1` | 真实按键注入（`keybd_event`） |
| `...\tools\symlookup.ps1` | 用 `pcsx2-qt.map` 把 `crash_info.txt` 的 `rip_off` 解析成函数名 |
| `...\tools\make_patch.ps1` | 逐文件生成补丁并自动 `git apply --check` |
| `...\tools\make_portable_data.ps1` | 从用户设置只读副本生成便携数据根 |
| `...\runs\` | 本轮全部现场：`C1_long`（24 张截图 + summary）、`C2`（fatal dump）、`G1`（191 张快照）、`J1`（jit_hooks=1 验证）、`diag`（A 的对照实验） |

---

## 4. D：未达成 / 如实说明

1. **用户那次的宿主崩溃 RIP 无法解析**：WER 只给了"模块 unknown / 偏移 0x0"，没有可用的 dump（`ReportArchive` 里那份 `AppCrash_pcsx2-qt.exe_404b…` 目录**访问被拒绝**）。我们给出的是**同源机理**（代码页被 handler 接管）与可复现的 `recRecompile+0x17D` 崩溃。
2. **经典 `cpuException` 路径（TLB/地址错误等 ExcCode）的自动落盘未在真实故障里触发**：本轮真实抓到的现场走的是**重编译器致命跳转**（`recError` → 新增的第 5 类触发，已验证），而不是 `cpuException()`。两条路径的代码都在，但 `exception_codes` 那条只有历史日志（BIOS 期异常被过滤）作为间接证据。
3. **`watch_reads = 1`（读监视）未实测**（默认关，代价翻倍且本故障只需看写）。
4. **`all_logging = 1`（全 trace）未实测**（会拖慢到不可玩，只在排障时开）。
5. **DMA/VIF/VU1 直写不覆盖**：只记录经 EE 访存的写（JIT 慢路径 + C 钩子）；DMA 直接写宿主内存的路径不经 vtlb（与上一版限制相同）。
6. **`0x00000000-0x00200000` 等低端区间的"代码页豁免"是动态的**：只有真正被编译过的代码页才会被剔除；若某页先被当数据监视、随后才被当代码执行，剔除发生在**编译该块之前**（`recRecompile` 入口），已实测有效。
7. **污染记录**：全程存在用户自己的官方实例 `pid=396`（22:54:13 起，闲置窗口，CPU 累计 ~15 秒）。所有跑动都记录了它（`runs\*\contamination.txt`），**从未对它做任何操作**；所有实验都在私有数据根/成品目录内完成。

---

## 5. 复跑命令（可审计）

```powershell
# 一键重建成品（configure + build + windeployqt + 部署 hook/portable/translations）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\build_qt2.ps1

# 只重刷便携目录（不编译）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\build_qt2.ps1 -SkipBuild

# 重建内置数据根（从用户设置的只读副本生成相对路径版本）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\make_portable_data.ps1

# C1：零参数端到端（截图 + F10 + TRIGGER）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\c1_long_run.ps1 `
  -Exe work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe `
  -EmuArgs work\builds\GR_REBUILD\GR_REBUILD2400.iso `
  -RunDir work\builds\GR_HOOKEMU_QT2\runs\C1_long `
  -DumpDir work\builds\GR_HOOKEMU_QT2\qt\hookdumps -TimeoutSec 480 -F10AtSec 240 -TriggerAtSec 300

# 崩溃地址 → 函数
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\symlookup.ps1 `
  -Map work\builds\GR_HOOKEMU_QT2\build\pcsx2-qt\pcsx2-qt.map -Offset 3E285D
```
