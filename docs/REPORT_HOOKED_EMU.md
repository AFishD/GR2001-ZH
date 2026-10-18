# 报告：带「写监视 + 现场取证」的 PCSX2 Qt 版（HookWatch）

日期：2026-10-17 21:0x（本地）
执行者：汉化工程执行者（AI）
工作根：`C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`

---

## 0. 结论速览

| 项目 | 结果 |
| --- | --- |
| **Qt 版是否编成** | ✅ 编成并**端到端跑通**（跑到游戏帧 2095 并在故障取证点落盘） |
| 便携目录 | `work\builds\GR_HOOKEMU\qt\`（exe + Qt 运行库 + `resources\` + `translations\` + `hook\`，208 个文件 / 130.7 MB） |
| Qt 可执行 | `work\builds\GR_HOOKEMU\qt\pcsx2-qt.exe`，11,740,160 B，SHA256 `C684D736BB4E9686FF51FC041D3D2CD435A7EF01B89AE5F9EF90B84B083AAC11` |
| 控制台降级版 | `work\builds\GR_HOOKEMU\build\pcsx2-gsrunner\pcsx2-gsrunner.exe`，SHA256 `95E9466D30C8A2D8A222FC1D220D204B3ACD6412F00EB83921894EF5908D1B08` |
| 一键构建脚本 | `work\builds\GR_HOOKEMU\build_hooked_emu.ps1`（可复跑：`pwsh -File ...`） |
| 源码改动补丁 | `work\builds\GR_HOOKEMU\hooks.patch`（47,536 B，SHA256 `D607782FC43025F6BFC7C623F40E1262B9B740ED12F55D948A291BEAEAC91479`，12 个文件；已用 `git apply --check` 对原始 `pcsx2_src` 校验通过，LF + 无 BOM） |
| 用户手册 | `docs\HOOKED_EMU_GUIDE.md` |
| 核心验证数字 | 写监视记录 **32,776 条**；PC 触发落盘 `hook_153_pc_00100008`；文件触发落盘 `hook_2095_file_trigger`；抓到的真实写样本 PC = `0x00412A64 / 0x0041226C / 0x00402EB4 / 0x00402F38 / 0x00402FB8` |
| 关键限制 | `watch` 不能越过 `0x00580000`；`force_slowmem=1` 不可用（都会 `0xFEFEFEFE` 崩，见 §4） |

---

## 1. 第 1 步：Qt 版构建

### 1.1 环境与依赖获取（都留下了证据）

| 依赖 | 来源 | 结果 |
| --- | --- | --- |
| MSVC 14.51.36231 | 便携工具链 `C:\Users\84363\pbt\msvc` | ⚠️ 该目录下 `VC\Auxiliary\Build\vcvars64.bat` 是 **0 字节空文件**，不能按 AGENTS.md 用 vcvars；必须 `call setup_x64.bat`（脚本内直接设 PATH/INCLUDE/LIB）。一键脚本已按此写。 |
| CMake 4.0.3 / Ninja | `C:\Program Files\CMake\bin\cmake.exe`、scoop ninja | ✅ 与既有 gsrunner 构建树一致 |
| Qt 6.10.3 MSVC x64 | `uv tool run --from aqtinstall aqt install-qt windows desktop 6.10.3 win64_msvc2022_64 --archives qtbase qttools qttranslations qtsvg opengl32sw d3dcompiler_47` | ✅ 装到 `work\builds\GR_HOOKEMU\deps\6.10.3\msvc2022_64`（含 Qt6CorePrivate/GuiPrivate/WidgetsPrivate 与 LinguistTools）。**注意**：PCSX2 要求 Qt ≥ 6.10.1；aqt 的元数据里 **6.11.x 返回 404**（`download.qt.io/.../qt6_6111/...Updates.xml` 不存在），所以选 6.10.3（CI 用的是 6.11.1，仅补丁版本差异）。 |
| KDDockWidgets 2.4.1 | GitHub tag `v2.4.1` 源码，源码构建 | ✅ 安装到 `work\builds\GR_HOOKEMU\deps\kddock`（`KDDockWidgets-qt6` ≥2.3.0 满足 `find_package`） |
| 其余依赖（SDL3/freetype/ffmpeg/plutosvg/ryml/…） | 复用工程既有 `third_party\deps` | ✅ |

### 1.2 配置与构建（在源码副本内，未动 `third_party\emu\pcsx2_src` 与既有 gsrunner 构建树）

```bat
call C:\Users\84363\pbt\msvc\setup_x64.bat
cmake -S work\builds\GR_HOOKEMU\src -B work\builds\GR_HOOKEMU\build -G Ninja ^
  -DCMAKE_BUILD_TYPE=Release ^
  "-DCMAKE_PREFIX_PATH=<qt>;<kddock>;third_party\deps" ^
  -DENABLE_QT_UI=ON -DENABLE_GSRUNNER=ON -DENABLE_TESTS=OFF ^
  -DUSE_VULKAN=OFF -DUSE_OPENGL=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF
ninja -C work\builds\GR_HOOKEMU\build pcsx2-qt pcsx2-gsrunner -j 10
```

- 首次配置/编译一次通过（879 个目标）；后续增量 2–12 个目标。
- 修掉两个“工地坑”（都写进了补丁，可审计）：
  1. `USE_VULKAN=OFF` 时 `pcsx2/GS/Renderers/DX11/D3D.cpp` 仍按 `ARCH_X86` include `GSDeviceVK.h`，而 vendored Vulkan 头只在 `USE_VULKAN=ON` 时进 include path → 在 `pcsx2/CMakeLists.txt` 无条件加入 `3rdparty/vulkan/include`。
  2. 便携 MSVC 的 `vcvars64.bat` 为空（见上），构建脚本统一走 `setup_x64.bat`。
- 便携化：`windeployqt --release --no-opengl-sw --no-system-d3d-compiler --no-translations` + 拷贝 `kddockwidgets-qt62.dll`、`third_party\deps\bin\*.dll`、`D3D12\`、`src\bin\resources`、`src\bin\translations`、`hook\`。
- `resources\` 是硬要求：gsrunner 与 Qt 都会因 `EmuFolders::SetResourcesDirectory()` 找不到 `<exe>\resources` 而静默退出（已踩、已写进手册）。

### 1.3 产物

```
work\builds\GR_HOOKEMU\
├─ build\                       # CMake/Ninja 构建树（含 PDB、map）
│  ├─ pcsx2-qt\pcsx2-qt.exe
│  └─ pcsx2-gsrunner\pcsx2-gsrunner.exe  (+ resources\ 供其启动)
├─ qt\                          # ✅ 便携 Qt 版（可直接双击/命令行跑）
│  ├─ pcsx2-qt.exe  resources\  translations\  platforms\ …  kddockwidgets-qt62.dll
│  └─ hook\hook_config.ini      # 钩子配置（默认 range 0x500000-0x580000）
├─ hook\                        # 配置模板（hook_config.ini + hooked_qt_example.ini）
├─ src\                         # 打了钩子的源码副本（12 个文件被改/新增）
├─ hooks.patch                  # 对 pcsx2_src 的 diff
├─ build_hooked_emu.ps1         # 一键构建
├─ deps\ (Qt 6.10.3, kddock 源码+构建)
├─ tools\symlookup.exe          # 崩溃地址→符号（本次排障用）
└─ val\                         # 本次全部验证 run 的日志/快照/配置
```

---

## 2. 第 2 步：钩子清单（HookWatch）

新增 `pcsx2/HookTools/HookWatch.{h,cpp}`；改动 `pcsx2/{CMakeLists.txt,Memory.cpp,vtlb.cpp,R5900.cpp,Counters.cpp,VMManager.cpp}`、
`pcsx2/x86/ix86-32/{iR5900.cpp,recVTLB.cpp}`、`pcsx2-qt/QtHost.cpp`、`pcsx2-gsrunner/CMakeLists.txt`。
**所有开关默认关闭**；只在 `pcsx2-qt.exe -hook` / `-hookconfig <ini>` / 环境变量 `PCSX2_HOOK_CONFIG` 时生效。

| # | 功能 | 实现要点 | 开关 | 证据 |
| --- | --- | --- | --- | --- |
| 1 | **全量日志** | `all_logging=1` 时置 `EmuConfig.Trace.{EE,IOP,MISC}` 全 1 并把文件级别提为 TRACE；另给 `[Logging]`+`[EmuCore/TraceLog]` 全开片段（手册 §4） | `all_logging`、`logfile` | 代码路径 + 配置片段已交付；**未实测**（日志量过大，见 §4） |
| 2 | **写监视（页面保护式）** | 把 `watch` 区间的**物理页**在 `memReset()` 中重映射为自定义 vtlb RAM handler（`HookWatch::InstallMemoryHandlers()`）。fastmem 映射由 pmap 生成，因此这些页**不进 fastmem**：首次访问触发 PCSX2 的 fastmem 回填，之后走慢路径，JIT 侧钩子拿到**精确 PC**+值 | `watch`（可多行）、`watch_reads` | `HookWatch: 129 watched page(s) remapped to the slow RAM handler`；dump 内 `ring.txt` 32,776 条；真实样本见 §3.3 |
| 3 | **触发式取证** | (a) 触发 PC：`recRecompile` 汇编期判定 `IsBlockHookPC(pc)` 后 `xFastCall(OnBlockEntry, pc)`；(b) EE 致命异常：`cpuException()` 头部按 ExcCode 过滤后 dump；(c) F10（`GetAsyncKeyState` 边沿）或 `<dumpdir>\TRIGGER` 文件（每帧轮询） | `trigger*`、`dump_on_trigger/exception/hotkey`、`trigger_file`、`exception_codes`、`exception_any/repeat`、`max_dumps`、`trigger_once` | `hook_153_pc_00100008`（PC 触发）、`hook_2095_file_trigger`（Qt，文件触发）、`TRIGGER.done_379`（重命名成功）；BIOS 引导期 syscall/中断**未**刷屏（过滤生效） |
| 4 | **PC 追踪** | `trace_pc`（可多行）命中时写 `hook_pctrace.txt`：帧号+PC+32 个 GPR 快照；`regs.txt` 另含最近 4096 个执行块的 PC 环 | `trace_pc`、`trace_all_blocks`、`trace_limit` | 文件已生成（46 B 表头）；菜单场景该 PC 未执行 → 命中路径**未验证** |
| 5 | **落盘内容** | `ring.txt`/`ring.bin`（全量、时间顺序）、`ee_ram.bin`(32MB)、`iop_ram.bin`(2MB)、`watch_*.bin`(被监视窗口)、`regs.txt`、`meta.txt`、可选 `hook_live.txt`、崩溃诊断 `crash_info.txt` | `full_ram`、`max_dump_entries`、`live_text` | 每个 dump 目录 6–7 个文件，见 §3 |
| 6 | **崩溃地址诊断** | 在 PCSX2 崩溃处理器之上链一个 filter，把 `ExceptionCode/RIP/RSP/RIP-base` 追加进 `<dumpdir>\crash_info.txt`（本次就是用 `tools\symlookup.exe` + linker map 把 RIP 解析到 `recRecompile` 定位问题） | 自动 | `crash_info.txt` 实例见 §4 |

### 尺寸/性能（实测）

- 环形缓冲 262,144 条（本次验证用）→ `ring.txt` ≈ 1.66 MB、`ring.bin` ≈ 786 KB；默认 1,048,576 条时约为 4 倍。
- 一个完整 dump ≈ 39 MB（含 32MB EE + 2MB IOP 快照）；7z 极限压缩后实测同级目录可压到个位数 MB。
- 开钩子后游戏明显变慢（被监视页走 C 层 handler + 每次记录）；`watch` 越窄越快。

---

## 3. 第 3 步：验证（全部为本地实跑）

### 3.1 对照组与失败实验（都记录在案）

| 实验 | 配置 | 结果 |
| --- | --- | --- |
| 对照：原 gsrunner（无钩子） | `-grmaxframes 2400` | ✅ 2400 帧、exit 0 |
| 钩子开 + **fastmem 关**（`force_slowmem=1`） | watch 任意 | ❌ ELF 入口处崩，退出码 `0xFEFEFEFE`（= `-16843010`） |
| 钩子开 + 保留 fastmem，但**未做 handler 映射** | watch `0x500000-0x600000` | ❌ 同上（慢路径整体关闭不可用） |
| handler 映射 + **区间越界** | `watch=0x00580000-0x00600000` | ❌ 同上（该段含代码页，SMC 保护冲突） |
| handler 映射 + 上半段 | `watch=0x00500000-0x00580000` | ✅ 900/2400 帧均 exit 0 |
| handler 映射 + 窄区间 | `watch=0x0055B000-0x0055C000` | ✅ 可跑（250 帧后正常收尾） |

### 3.2 通过项（工作配置：`watch = 0x00500000-0x00580000`）

- **gsrunner**（无头）：`-grmaxframes 900`，exit 0；日志出现
  `HookWatch: ACTIVE dumpdir=… ring=262144 entries` → `129 watched page(s) remapped to the slow RAM handler`
  → `hook_153_pc_00100008`（**PC 触发**，32,769 条）→ `hook_379_file_trigger`（**TRIGGER 文件触发**，32,776 条，`TRIGGER` 被改名为 `TRIGGER.done_379`）。
- **Qt 版**（本次重点，`-nogui -batch -datapath <私有目录>`）：窗口标题 `Tom Clancy's Ghost Recon`，
  日志 `ELF Loading: … EntryPoint = 0x00100008` → 跑到**帧 2095**，在 `hookdumps\` 放 `TRIGGER` 后生成
  `hook_2095_file_trigger`（32,776 条 + 32MB/2MB 快照 + `regs.txt` + `meta.txt`），随后由我主动结束进程。
  → **Qt 版端到端可用**（构建、启动、钩子生效、落盘全链路）。
- 异常触发过滤：BIOS/ELF 引导期大量 syscall/中断**没有**产生 dump（`exception_codes` 默认只留致命码），
  避免了首版“8 次 dump 额度在 2 秒内被用完”的问题（该问题已修复并有前后对比日志）。

### 3.3 真实抓到的“谁在写分配器区”（两套前端结果一致）

帧 154（ELF 入口后第一波堆初始化），`ring.txt` 末尾：

```
32769 154 00412A64 0056E120 32 W 0 0000000000000002
32770 154 0041226C 0056D974 32 W 0 000000000065AEA0
32771 154 00402EB4 00561D08 32 W 0 000000000064BE80
32772 154 0041226C 0056D974 32 W 0 000000000064BFE0
32773 154 00402F38 00561D20 32 W 0 000000000000F180
32774 154 00402FB8 00561D10 64 W 0 000000000000F020
32775 154 0041226C 0056D974 32 W 0 0000000001F89020
```

这正是我们要的“**哪条 store、以什么值、写到哪个地址**”，且 PC 已精确到指令（分配器状态 `0x0055B7A0` 落在该区间内）。
gsrunner 与 Qt 两次独立运行的这 7 条记录**完全一致**（可重复性证据）。

---

## 4. 未达成 / 已知限制（必须如实告知）

1. **默认监视区间不能覆盖到 `0x00600000`**：`0x00580000-0x00600000` 含**代码页**，被映射为监视 handler 后无法参与
   PCSX2 的自修改代码页保护（`mmap_MarkCountedRamPage`/fastmem 回填路径冲突），游戏在 ELF 入口即崩（`0xFEFEFEFE`）。
   已验证折中：默认 `0x00500000-0x00580000`（含分配器状态 `0x0055B7A0`）。要覆盖整段 1MB，需要后续实现
   “代码页自动剔除 / SMC 感知的 handler 回收”（见 §6 建议）。
2. **`force_slowmem=1`（全模拟器关 fastmem）不可用**：本游戏在该模式下 ELF 入口必崩；已默认 0，并在配置里注明。
   最初的“强制慢路径”设计因此改为“**只让被监视页走慢路径**”（handler 映射），功能等价且不破坏游戏。
3. **F10 热键未用真实按键验证**：实现为每帧 `GetAsyncKeyState(VK_F10)` 边沿触发，但本地无头验证环境无法可靠按键；
   已验证的是 **PC 触发**、**致命异常触发**、**TRIGGER 文件触发**三条路径。请用户在实机按一次 F10 确认（若不生效就用 TRIGGER 文件，二者等价）。
4. **`watch_reads=1` 未实测**（读监视很慢，默认关）。
5. **`all_logging=1` 未实测**（只实现开关 + 交付 ini 片段；全量日志会拖慢游戏到不可玩）。
6. **`trace_pc` 命中路径未实测**：菜单场景 `0x00219A70` 未执行，`hook_pctrace.txt` 只有表头。
7. **DMA/VIF/VU1 直写不覆盖**：只记录经过 vtlb 的 EE 访存（含 COP2/VU0 macro）；DMA 直接写宿主内存的路径不经 vtlb。
   当前卡死指纹是 EE 侧写坏分配器，够用；若要覆盖 DMA 需要另加钩子。
8. **未在用户实机上复现卡死**：本次只跑到菜单/帧 2095（约 37 秒 guest 时间），没有玩到“卡死/2fps”现场。
   “能复现卡死”沿用工程既有结论（`GR_REBUILD2400.iso` 实机确认），Qt 版本身的**故障现场取证**仍需要用户按手册跑一次。
9. **污染记录（未杀任何他人实例）**：验证窗口内检测到他人实例——20:31:55 起的官方 `pcsx2-qt`（跑 `GR_LAYOUT\LAY_fix1_bytecount.iso`）、
   21:00:02 起的他人 `pcsx2-gsrunner`。我的所有结论都有独立重复（同一 7 条记录在 gsrunner 与 Qt 两次运行中一致），
   且每次跑自己的实例前都轮询过进程；未对他人实例做任何操作。

---

## 5. 用户交接清单

**给用户的最小操作集（详见 `docs\HOOKED_EMU_GUIDE.md`）**

1. 进 `work\builds\GR_HOOKEMU\qt\`，执行 `pcsx2-qt.exe -hook`（必要时加 `-datapath <私有目录>`）。
2. 用 `GR_REBUILD2400.iso` 正常玩到卡死；卡死瞬间按 **F10**（或在 `hookdumps\` 放 `TRIGGER` 文件）。
3. 把 `hookdumps\hook_<帧号>_<原因>\` 整个目录（至少 `ring.txt`+`meta.txt`+`regs.txt`+`hooked_emulog.txt`，
   最好连 `ee_ram.bin`/`iop_ram.bin`）用 7z 压缩后回传。

**要回答的 3 个问题**（数据都在回传文件里）：
① 哪条 store 最先写坏分配器区（`ring.txt` 的 `pc/addr/value`）；② 该 PC 属于哪个函数；
③ 写坏前最后执行的文本/渲染 PC（`trace_pc` + `hook_pctrace.txt` + `regs.txt` 的块 PC 环）。

---

## 6. 建议的下一步（按性价比排序）

1. **实机复现一次**：用户按手册跑 Qt 版到卡死点并回传 dump —— 这是把工具变成结论的唯一缺口。
2. **扩展监视范围到 `0x00580000-0x00600000`（代码页安全）**：在 `HookWatch::InstallMemoryHandlers()` 里做
   “按页惰性剔除”——当 `memory_protect_recompiled_code()` 首次保护某页时，把该页从 handler 映射改回直连 RAM 映射
   （并保留该页的写监视通过 fastmem 回填/`vtlb_UpdateFastmemProtection` 路径），即可覆盖整段 1MB 而不触发 SMC 冲突。
3. **DMA 侧补钩**（若 dump 显示分配器区被 DMA 改写）：在 `Dmac.cpp` / `Vif_Unpack` 的写内存路径加同样的记录点。
