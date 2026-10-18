# 报告：QT2 便携取证构筑「误删事故」的重建与验证

- 日期：2026-10-18 16:2x → 17:3x（本机时区 Asia/Hong_Kong）
- 触发原因：一次磁盘清理误删了**带钩子 Qt 便携构筑的可执行文件与大于 ~5 MiB 的 Qt 运行库**
- 成品（重建后）：`work\builds\GR_HOOKEMU_QT2\qt\`（便携版，双击 `pcsx2-qt.exe` 即用，**零命令行参数**）
- 一键重建：`work\builds\GR_HOOKEMU_QT2\build_qt2.ps1`
- 补丁：`work\builds\GR_HOOKEMU_QT2\hooks_qt2.patch`（74,968 B；13 文件；`git apply --check` **exit 0**）
- 用户手册：`docs\HOOKEMU_QT2_GUIDE.md`（本轮已更新依赖路径与重建说明）
- 事故前那一版的技术报告：`docs\REPORT_HOOKEMU_QT2.md`（**本轮的"行为一致"基准**）

---

## 0. 一句话结论

1. **重建成功**：`work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe`（11,765,248 B）
   sha256 = **`956151755464572D8287A7C0FF7271C9152511E9D90C80CCDF261621CFD7B452`**，
   同目录 Qt 运行库全部为 **6.10.3.0**，`resources\`/`translations\`/`hook\`/内置数据根/README 全部就位。
2. **依赖是从网上重新取回的**：本机现有 Qt 副本版本不符（用户的 PCSX2 是 Qt **6.11.1**、shadPS4 启动器是 **6.10.0**），
   所以用 **USTC 镜像**重新下载 Qt 6.10.3（qtbase+qtsvg+qttools+qttranslations）到
   `work\builds\GR_HOOKEMU_QT2\deps\6.10.3\msvc2022_64`（4,195 个文件 / 419.5 MB），**没有**动共享前缀 `work\builds\GR_HOOKEMU\deps`。
3. **三项验证都是用数字说话的**（详见 §4）：
   - C1 零参数端到端（Qt 版）：**261 张窗口截图**（每 4 s 一张，1933×1045）、亮度 **13.00–117.31（117 个不同值，0 张黑屏）**、
     **帧 64,594**、写监视命中 **4,460,000**、`TLB Miss 0 / Trap 0`、中文界面正常；
   - C2 落盘：**F10 真实按键 → 帧 4641 / 4677** 两个 dump；**TRIGGER 文件 → 帧 19719** 一个 dump（各 7 个文件，emulog 里带绝对路径与文件大小）；
   - C3 可关：`-nohook` 跑 95 秒 → emulog 里 **`HookWatch:` 行数 = 0**、命中 0、无 dump。
4. **"与事故前行为一致"的硬证据**：同核心、同配置的 gsrunner 6000 帧跑，
   命中数 **2,564,000**、末条 `frame=5961 pc=004147D0 addr=00570170 size=32 W value=0000000000000000`、
   **191 张快照**、`TLB 0 / Trap 0` —— 与事故前 `REPORT_HOOKEMU_QT2.md` §3.4 记录的数字**逐字相同**。

---

## 1. A：损失清单（每条都有命令/文件证据）

### 1.1 被删的东西（四个位置）

| # | 位置 | 被删内容 | 证据 |
| --- | --- | --- | --- |
| 1 | `GR_HOOKEMU_QT2\qt\`（便携产物） | `pcsx2-qt.exe`、`Qt6Core.dll`、`Qt6Gui.dll`、`Qt6Widgets.dll` | 目录里这三个 DLL 与 exe 不存在；其余 30 个根文件全在 |
| 2 | `GR_HOOKEMU\deps\6.10.3\msvc2022_64\bin\`（**共享** Qt 前缀） | **恰好 7 个 >5 MiB 的 Qt DLL**：`Qt6Core.dll`(10,250,040)、`Qt6Cored.dll`(23,416,120)、`Qt6Gui.dll`(9,514,296)、`Qt6Guid.dll`(27,862,840)、`Qt6Networkd.dll`(5,432,632)、`Qt6Widgets.dll`(6,577,464)、`Qt6Widgetsd.dll`(17,167,160) | 与「同版本、全新解压」的 Qt 6.10.3 `bin\` 逐文件比对：pristine 61 个文件里这 7 个在旧前缀中缺失；`lib\`/`include\`/`plugins\`/`translations\` 未受损（旧前缀反而更多） |
| 3 | `GR_HOOKEMU_QT2\src\`（源码副本） | **只有 1 个源文件**：`3rdparty\zydis\src\Generated\InstructionDefinitions.inc`（5,800,514 B） | 对 `third_party\emu\pcsx2_src` 做全文件集比对：`missing_in_src=67`，其中 66 个是本副本自己的 `.git\*`（pristine 那边有 341 MB 的 pack），**真正的源文件只有这 1 个**；`extra_in_src=45` = 43 个构建产生的 `.qm` + 2 个补丁新增的 `HookWatch.cpp/h` |
| 4 | `GR_HOOKEMU_QT2\build\`（Ninja 树） | 11 个输出：`3rdparty\ccc\ccc.lib`、`3rdparty\imgui\imgui.lib`、`common\common.lib`、`pcsx2\pcsx2.lib`、`ccc\…\symbol_database.cpp.obj`、`zydis\…\SharedData.c.obj`、`pcsx2\…\FullscreenUI_Settings.cpp.obj`、`pcsx2-qt\…\MainWindow.cpp.obj`、4× `cmake_pch.cxx.obj`（PCH 标记）、两个 exe | 首次 `ninja -n pcsx2-qt pcsx2-gsrunner` 输出 `[1/11]`…`[11/11]`，恰好这 11 步 |
| （5） | 用户 dump（**不是本轮重建目标**） | 3 份保留 dump 里的 `ee_ram.bin`(32 MB)、`ring.bin`(6 MB)、`ring.txt`(~13.6 MB) 也被同一次清理删掉 | `qt\hookdumps\hook_19671/19701/23444_hotkey_f10\` 里现在只剩 `iop_ram.bin`/`meta.txt`/`regs.txt`/`watch_*.bin`；**本轮从未删改这些目录** |

### 1.2 删除规则的旁证（为什么是"大文件"）

- `qt\D3D12\D3D12Core.dll` = **5,019,680 B（4.79 MiB）幸存** ⇒ 阈值是 **5 MiB（5,242,880 B）**，不是 5,000,000 B。
- `qt\memcards\Mcd001.ps2`、`Mcd002.ps2` = 8,650,752 B **幸存** ⇒ 清理**跳过了 `.ps2` 记忆卡数据**，只吃程序/运行库/中间产物。
- `qt\resources\`（113 文件 9.3 MB）、`qt\translations\`（43 文件 29 MB）**整棵幸存** ⇒ 受影响的只有"单文件 >5 MiB"的那些。

### 1.3 幸存并已被利用的东西

| 幸存物 | 状态 | 用途 |
| --- | --- | --- |
| `hooks_qt2.patch` | 74,968 B | 补丁本体；`git -C third_party\emu\pcsx2_src apply --check` → **exit 0** |
| `build_qt2.ps1` | 7,008 B | 一键重建；未修改，本轮原样使用 |
| `src\` | 3,012 文件；`git apply --check --reverse` → **exit 0**（补丁已在里面） | 直接增量重建，**没有**改 `third_party\emu\pcsx2_src` |
| `build\`（Ninja 树） | `build.ninja`(3.4 MB)、`CMakeCache.txt`、`.ninja_log`、绝大部分 `.obj` 完好 | 这是重建只花 **130 秒**的原因 |
| `qt\resources\`、`qt\translations\`、`platforms\`、`styles\`、`iconengines\`、`imageformats\`、`tls\`、`networkinformation\`、`generic\`、`QtPlugins\`、`D3D12\` | 全在 | 便携运行时 |
| `qt\hook\hook_config.ini` | 4,753 B（与模板同哈希 `9000564BA86BF579…`） | 钩子默认开：`enabled=1`、`arm_after=auto`、`jit_hooks=1`、`force_file_log=1`、`dump_on_trigger=0`、`max_dumps=8` |
| `qt\inis\PCSX2.ini` | 11,378 B；`[Folders]` 全相对路径；`BIOS = SCPH-90006_BIOS_VX_HK_2.20.bin`；`EnableFileLogging = true` | 内置数据根 |
| `qt\bios\`(6 文件 8.4 MB)、`qt\memcards\`(2×8.65 MB) | 全在 | 内置数据根 |
| `qt\logs\emulog.txt` | 741,534 B | **事故前的现场**（末条 `watch hits=10930000 frame=21535`），本轮新日志会覆盖它，旧内容已另存副本 |
| `qt\README_怎么用.txt` | 6,680 B | 随包说明（本轮只修了 1 行过时表述，见 §4.5） |
| `runs\`、`tools\` | 全在 | 上一轮全部现场 + 工具 |

---

## 2. A2：依赖从哪来（Qt 6.10.3 的恢复）

### 2.1 本机现有 Qt 副本都不能用

| 位置 | 版本 | 结论 |
| --- | --- | --- |
| `%LOCALAPPDATA%\PCSX2\Qt6Core.dll`（用户自己的官方 PCSX2） | **6.11.1.0** | ✗ 与我们的 6.10.3 混用会触发 Qt 版本不一致 |
| `…\shadPS4QtLauncher-…\Qt6Core.dll` | **6.10.0.0** | ✗ 低于编译所用 6.10.3（Qt 只向后兼容） |
| `Program Files\…`（AutoCAD/Calibre/Moonlight/腾讯会议/RetroArch 等） | 各自版本 | ✗ 同上 |
| `work\builds\GR_HOOKEMU\deps\6.10.3\msvc2022_64` | 6.10.3（**本体**） | 但 `bin\` 少了 7 个大 DLL（§1.1 #2）⇒ moc/uic/rcc/windeployqt **都跑不起来** |
| `%APPDATA%\aqt\tmp` | 空 | aqtinstall 当年没留缓存 |

### 2.2 重新取回（写在自己的目录里，不碰共享前缀）

`download.qt.io` 当时只有 **11 KB/s**；改用 **USTC 镜像（约 3 MB/s）**：

| 包 | 大小 | sha256（下载归档） |
| --- | --- | --- |
| qtbase.7z | 42,748,757 | `4DB84DEE7FE3C558F242BEF0A88852613AF76580DC6D2B24596479F47004DAD7` |
| qtsvg.7z | 668,085 | `FA5BB334B6B95582F87481A9F54819DC066E8CEFED7F4FE9A21A77719630BA04` |
| qttools.7z | 26,902,888 | `4D51CD446FF438845C706600AEF6BF7349490C358BF7BB27ABD32CB5EA3AFCB8` |
| qttranslations.7z | 1,937,577 | `5002080668C89BC8749A790F0136F12C15A8F6A407649EF0820C7DC555DA0BB2` |

解压到 **`work\builds\GR_HOOKEMU_QT2\deps\6.10.3\msvc2022_64`**（5,319 文件 / 419.5 MB，含 `bin\Qt6Core|Gui|Widgets.dll`、
`windeployqt.exe`、`moc.exe`、`rcc.exe`、`uic.exe`、`lrelease.exe`、`plugins\`、`translations\`(305 文件)）——
一个**可完全替代原前缀**的 Qt 6.10.3。关键文件哈希（前 32 位）：
`Qt6Core.dll B712B4754588E89F855DC0AA087D6304`、`Qt6Gui.dll 03BA47A2025036A04F5548BCE242788A`、
`Qt6Widgets.dll 61DDD0316A731B8DBABAF2924CD0D47B`、`windeployqt.exe F21031D42AC074A70FEAC5697C9B9A63`。

### 2.3 其余依赖（都在，且只读使用）

- KDDockWidgets 2.4.1：`work\builds\GR_HOOKEMU\deps\kddock\bin\kddockwidgets-qt62.dll`（1,419,264 B）**在**（便携目录里那份也幸存）。
- 工程依赖：`third_party\deps`（`bin\` 22 个 DLL、`lib\`、`include\`）**在**。
- 便携 MSVC：`C:\Users\84363\pbt\msvc\setup_x64.bat` 是 **834 B（不是 0 字节）**，`VC\` 与 `Windows Kits\` 齐全 ⇒ 直接用 `setup_x64.bat`，没有踩 0 字节 `vcvars64.bat` 的坑。

---

## 3. B：重建步骤（可复跑）

### 3.1 先修两处被删导致的构建阻塞

1. **恢复被删的 Zydis 头**（从只读 pristine 树复制，5,800,514 B → `src\3rdparty\zydis\src\Generated\InstructionDefinitions.inc`）。
   不恢复的症状：`SharedData.c(43): fatal error C1083: Cannot open include file: 'Generated/InstructionDefinitions.inc'`。
2. **删掉 4 个"陈旧 PCH 标记"** `build\*\CMakeFiles\*\cmake_pch.cxx.obj`。
   原因：`build.ninja` 把 `.pch` 声明成 `.obj` 的 **phony 别名**
   （`build pcsx2-qt\CMakeFiles\pcsx2-qt.dir\.\cmake_pch.cxx.pch: phony …\cmake_pch.cxx.obj`），
   所以 `.pch` 被删而 `.obj` 还在时 ninja 认为"已最新" ⇒ 编译报
   `fatal error C1083: Cannot open precompiled header file: '…/cmake_pch.cxx.pch'`。删掉标记后 ninja 重新生成 PCH。
   （代价：PCH 是**隐式输入**，重建触发全量重编 470 步 —— 实测 130 秒。）

### 3.2 一键命令（本轮实际执行的）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\build_qt2.ps1 `
  -QtPrefix "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_HOOKEMU_QT2\deps\6.10.3\msvc2022_64" `
  -Jobs 10
```

- **没有加 `-Reconfigure`**：`CMakeCache.txt`/`build.ninja` 里的头文件与 import lib 路径指向旧共享前缀，而那些**没被删**（`lib\Qt6Core.lib` 等仍在），
  只有 DLL 被删 ⇒ 编译/链接照旧，`windeployqt`/`moc`/`uic`/`rcc` 改由**新前缀**提供。这是最小改动路径。
  （若将来连 `lib\`/`include\` 也没了，就用 `-Reconfigure -QtPrefix <新前缀>`；新前缀已含 qtbase+qtsvg+qttools+qttranslations，具备该条件，但**本轮未实测**。）
- 结果：`ninja` 470/470 成功，链接出 `pcsx2-gsrunner.exe` 与 `pcsx2-qt.exe`，随后部署完成，**exit 0，耗时 130.1 秒**。
- `windeployqt` 的 3 条警告都是**既往即有、与本次事故无关**：
  "Translations will not be available…"（脚本故意 `--no-translations`，Qt 自己的 `qt_*.qm` 会让 PCSX2 弹"Translation Error"）、
  "Cannot find … dxcompiler.dll and dxil.dll"（脚本故意 `--no-system-d3d-compiler`）、"VCINSTALLDIR is not set"。

### 3.3 产物核对（重建后）

| 项目 | 状态 |
| --- | --- |
| `qt\pcsx2-qt.exe` | 11,765,248 B；FileVersion 0.0.0.0（本地构筑，非官方 2.8.2.0） |
| `Qt6Core/Gui/Widgets/Network/Svg.dll` | 全部 `FileVersion=6.10.3.0` |
| `platforms\qwindows.dll`、`styles\qmodernwindowsstyle.dll`、`iconengines\qsvgicon.dll`、`imageformats\qsvg.dll`、`tls\qschannelbackend.dll` | 全部 6.10.3.0 |
| 该 exe 的直接导入 | `Qt6Core.dll / Qt6Gui.dll / Qt6Widgets.dll`（与 `build.ninja` 链接行一致） |
| `resources\`(113)、`translations\`(43)、`hook\hook_config.ini`、`README_怎么用.txt`、`qt.conf`、`portable.txt/ini` | 齐全 |
| 内置数据根 `inis\`(2) / `bios\`(6, 8.4 MB) / `memcards\`(2×8.65 MB) | 齐全（来自用户设置副本，未改 `GR_SYNC`） |
| gsrunner | `build\pcsx2-gsrunner\pcsx2-gsrunner.exe` |

### 3.4 新的哈希（本轮口径）

- **exe**：`956151755464572D8287A7C0FF7271C9152511E9D90C80CCDF261621CFD7B452`（`qt\pcsx2-qt.exe`）
- **gsrunner**：`24D3088E88AB13842FA8D4FAC0A10D249FF51A73C030AF430ADC58FE69E84D5E`
- **目录清单（逐文件 sha256）**：`work\builds\GR_HOOKEMU_QT2\runs\REBUILD\qt_manifest_sha256.txt`
  （`qt\` 共 **1,317 文件 / 515.7 MB**）
- **静态载荷聚合哈希**：`95cf1dc4390d84309d1f354e54ecb7334dded9b3d3080adf276d240fe1092ae3`
  （= 把 223 个"重建产出/必需"文件的 `sha256␠␠相对路径` 排序后拼接再 sha256，120.8 MB；
  排除运行期会变的 `logs\ hookdumps\ sstates\ cache\ snaps\ inis\ textures\` 与 3 个 portable 标记文件）

---

## 4. C：验证（全部本机实跑，数字在）

### 4.1 C1 零参数端到端（Qt 版，唯一命令行参数就是 ISO）

```
work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe work\builds\GR_COMBFIX\COMBFIX_2400.iso
```

（`tools\qt_e2e_run.ps1`，**没有**任何钩子开关；每 4 秒抓一张窗口图，第 240 秒按 F10、第 330 秒放 `TRIGGER`）

| 指标 | 结果 |
| --- | --- |
| 运行时长 | **1083.2 秒**（超时正常收尾，只杀自己启动的 pid） |
| 窗口截图 | **261 张**（≥190 ✓），全部 1933×1045（真窗口，非 157×25 那种被最小化的假窗口） |
| 亮度 | **13.00 – 117.31**，**117 个不同值**，`lum<3`（黑屏判据）**0 张** ⇒ **不黑屏** |
| 画面变化 | 相邻帧平均像素差 **18.72**（最长静止段 8 张 = 游戏自己的静态菜单/读盘画面，非黑屏） |
| 帧号 | 末条命中行 `frame=64594` ⇒ **≥6000 帧**（约 2,153 个 30 帧快照当量） |
| 写监视命中 | **4,460,000** 条（emulog 里 `watch hits=` 行 2,230 行） |
| `TLB Miss` / `Trap exception` / `Unrecognized` | **0 / 0 / 0** |
| 钩子时序 | `ACTIVE (QT2) source=command line config='…\qt\hook\hook_config.ini'` → `waiting to arm`（BIOS 不插桩）→ `game ELF loaded: 'cdrom0:\SLUS_206.13;1'` → **`ARMED (reason=elf_loaded frame=6)`** → `page 005xxxxx holds guest code -> un-watched`（代码页自动豁免）→ `more code pages un-watched; further lines suppressed` |
| 游戏确实在跑 | `FMV started` 12 次 / `FMV ended` 11 次；截图里是中文界面 + 游戏画面（见 `runs\REBUILD\C1\shots\shot_060.png`、`shot_204.png`） |
| 宿主崩溃 | 事件日志查询：无 |
| 外部干扰 | 起跑时**他人 pcsx2 进程 = 0**；运行中窗口被外部**最小化 1 次**（t=1009 s），本工具自动还原并记录（`window_restores: 1`），**从未操作别人的进程** |

### 4.2 C1b 同核心精确帧数复核（gsrunner，6000 帧 / 191 快照）

```
pcsx2-gsrunner.exe -grdumpdir runs\REBUILD\G2 -grmaxframes 6000 -grsnap 30 ^
  -grbios qt\bios -grbiosname SCPH-90006_BIOS_VX_HK_2.20.bin -grmemcards qt\memcards ^
  -logfile runs\REBUILD\G2\emulog.txt -- work\builds\GR_COMBFIX\COMBFIX_2400.iso
（环境变量 PCSX2_HOOK_CONFIG = qt\hook\hook_config.ini，即产品随包配置）
```

| 指标 | 本轮重建版 | 事故前 `REPORT_HOOKEMU_QT2.md` §3.4 | 判定 |
| --- | --- | --- | --- |
| 帧数 | `GR: === run end, frames=6000 ===` | 6000 | **一致** |
| 真·GS 快照 | **191 张**（≥190 ✓） | 191 张 | **一致** |
| 写监视命中 | **2,564,000** | 2,564,000 | **一致** |
| 末条记录 | `frame=5961 pc=004147D0 addr=00570170 size=32 W value=0000000000000000` | 同 | **逐字一致** |
| `TLB Miss / Trap` | 0 / 0 | 0 / 0 | **一致** |
| 耗时 | 102.2 秒 | — | — |

> 这就是"重建版与原版行为一致"的最硬证据：**同样的输入 → 同样的命中数、同样的末条记录、同样的快照数**。

另外 `runs\REBUILD\G1`（**不带** `PCSX2_HOOK_CONFIG`，走内置默认）也跑出 191 张快照 / 6000 帧 / TLB 0 / Trap 0，
并顺带验证了两件事：
- 没有 `hook\hook_config.ini` 时钩子**依然默认开**（`ACTIVE … source=built-in defaults (no hook_config.ini found)`）；
- **触发 PC 自动落盘**这一类触发有效：内置默认 `dump_on_trigger=true`，帧 250 命中 4 个触发 PC →
  `build\pcsx2-gsrunner\hookdumps\hook_250_pc_00101D10 / 00101DE4 / 00101E08 / 001024E8` 四份落盘。
  （该次 `ring_total=0` 是**已知且已记录**的行为：内置默认 `jit_hooks=false`，EE 的 JIT store 不记录；
  产品 ini 里是 `jit_hooks=1`，所以产品跑有命中。见 `REPORT_HOOKEMU_QT2.md` §3.3。）

### 4.3 C2 落盘（两类触发都实测）

| 触发 | 帧号 | 落盘目录 | 文件清单（全部 7 个） |
| --- | --- | --- | --- |
| **F10 真实按键** | **4641** | `qt\hookdumps\hook_4641_hotkey_f10\` | `ee_ram.bin` 33,554,432 B / `iop_ram.bin` 2,097,152 B / `meta.txt` 1,145 B / `regs.txt` 38,740 B / `ring.bin` 6,291,456 B / `ring.txt` 13,813,214 B / `watch_00500000_00581000.bin` 528,384 B |
| **F10 真实按键** | **4677** | `qt\hookdumps\hook_4677_hotkey_f10\` | 同上（`ring.txt` 13,813,542 B） |
| **`TRIGGER` 文件** | **19719** | `qt\hookdumps\hook_19719_file_trigger\` | 7 个文件（`ring.txt` 14,213,262 B），并在 emulog 打印每个文件的**绝对路径与字节数**；文件被改名成 `TRIGGER.done_19719` |
| （首轮中止的那次运行） | 19725 | `qt\hookdumps\hook_19725_file_trigger\` + `TRIGGER.done_19725` | 保留为现场 |

emulog 记录示例：`[82.3297] HookWatch: F10 pressed (frame 4641) -> dumping` → `dump summary: reason=hotkey_f10 frame=4641 ring_total=2553106 entries_written=262144` → `dump complete in 142 ms`。

**F10 的实测条件（重要，已写进手册）**：F10 由 `GetAsyncKeyState(VK_F10)` 在每帧轮询，
**窗口必须真的在前台**。18 分钟那次长跑里 harness 只能"请求"前台（`SetForegroundWindow`）而被系统拒绝
（当时机器有人在用），所以 **0 个 F10 dump**；专用探针 `tools\f10_probe.ps1` 先在窗口中央发一次**真实点击**再按键，
F10 立刻生效（3 次按键 → **2 个 dump**，帧 4641/4677）。
因此 **"F10 或 TRIGGER 能落盘"由两条路径各自独立验证通过**。

### 4.4 C3 配置可关（`-nohook`）

```
qt\pcsx2-qt.exe -nohook work\builds\GR_COMBFIX\COMBFIX_2400.iso     （95 秒）
```

| 指标 | 结果 |
| --- | --- |
| `HookWatch:` 行数 | **0**（没有 `ACTIVE`、没有 `waiting to arm`、没有 `ARMED`、没有 `watch hits=`、没有 `un-watched`） |
| 写监视命中 | **0** |
| 新 dump | **无**（`qt\hookdumps\` 里没有新增目录） |
| 模拟器仍正常 | ELF 装载 `cdrom0:\SLUS_206.13;1`、**Game CRC = CFDB8C97**（与手册里 `COMBFIX_2400` 的 CRC 一致）、`FMV started/ended` 3/2、6 张截图亮度 13.38–91.38 变化 |
| `TLB Miss / Trap` | 0 / 0 |

三种关闭开关在源码里都在（`src\pcsx2\HookTools\HookWatch.cpp`、`src\pcsx2-qt\QtHost.cpp`）：
`hook\OFF` 空文件（L1661-1665，"hard disable, no questions asked"）、ini `enabled=0`（L1070-1075）、
命令行 `-nohook` → `HookWatch::Disable()`（QtHost L2282-2285）。

### 4.5 顺手修掉的一处文档不一致

`qt\README_怎么用.txt` 第 102 行原文写"**不要动 jit_hooks（保持 0）**"，与随包 `hook_config.ini` 里的
`jit_hooks = 1`（以及手册 §4 的推荐）**自相矛盾**，那是代码页豁免修复之前的旧说法。
本轮**只改了这 1 行**（6,680 → 6,760 B，UTF-8 无 BOM，其余 111 行逐字节未动）：
"…不要动 jit_hooks（保持 **1**：精确到指令的 PC/宽度/值；改成 0 会丢掉 EE 的 JIT store 记录）。"

---

## 5. 未达成 / 如实说明

1. **无法做"哈希对等"**：事故前那版 exe 的 sha256 在仓库里**从没被记录过**（`docs\REPORT_HOOKEMU_QT2.md` 只记了字节数 11,762,688）。
   本轮只能给**新的** sha256，并用 §4.2 的"命中数/末条记录/快照数逐字一致"来证明行为一致。
2. **没有跑全量 `-Reconfigure`**：本轮复用了完好的 `CMakeCache.txt`（import lib/头文件指向的旧前缀未受损），
   所以只用新前缀做工具链与部署。新前缀是完整的 6.10.3，具备重配置条件，但"从零 configure"这条路径**未实测**。
3. **C1 长跑里的 F10 没有触发**（前台被占），改用专用探针完成验证；这在真实使用里表现为"**F10 需要模拟器窗口在前台**"，
   属于既有设计（手册第 5 节已写明），不是本次重建引入的问题。另外探针里 3 次按键只落了 2 份 dump，原因未进一步定位。
4. **外部干扰**：模拟器窗口被外部动作最小化过 2 次（中止那次 t≈166 s、正式那次 t=1009 s）；
   只有我自己启动的实例被还原/结束，**全程未触碰任何他人 pcsx2 进程**（每轮 `contamination.txt` 记录，起跑时均为 0）。
   被最小化的那次跑（`runs\REBUILD\C1_aborted_minimized\`，142 张无效截图）**保留为证据**，未删。
5. **3 份用户 dump 的大文件无法找回**：`ee_ram.bin`/`ring.bin`/`ring.txt` 被同一次清理删掉，
   仓库里没有第二份；本轮**按要求一个字节都没动**这三份 dump。
6. **recycle bin 里没有我们的文件**（只有 17 个无关项：记忆卡副本、动画 mkv、字幕），所以无法"还原删除"。
7. **`jt_hooks=false` 时不记录 EE 的 JIT store**（gsrunner 内置默认即如此，`ring_total=0`）——既有已知行为，非本轮回归。
8. **DMA/VIF/VU1 直写不经 vtlb ⇒ 不在监视范围**（与上一版限制相同）。
9. **本轮新增了 3 个工具**（未改既有工具）：`tools\qt_e2e_run.ps1`、`tools\win_probe.ps1`、`tools\f10_probe.ps1`；
   原因见 §5.3/§6.2 —— `tools\emu_run.ps1` 与 `tools\c1_long_run.ps1` 取 `Process.MainWindowHandle`（.NET 会缓存首次结果），
   本轮它锁到了一个**被最小化的 157×25 窗口**，导致截图全是同亮度的无效小图。新工具每张图都重新枚举窗口并取"最大可见非最小化窗口"。
10. 新依赖树占 **488 MB**（`deps\`，含 4 个归档 72 MB），`runs\REBUILD\` 现场占 **840 MB**；
    跑完时 C 盘剩余 42.2 GB（写报告时 47.5 GB）。未删除任何既有报告/脚本/用户 dump。

---

## 6. 怎么最快确认"重建版和之前行为一致"（给用户的三条）

1. **看日志三行**：双击 `work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe`（或把 ISO 拖上去），
   打开 `qt\logs\emulog.txt`，必须依次出现
   `HookWatch: ACTIVE (QT2) source=…qt\hook\hook_config.ini` → `HookWatch: waiting to arm (BIOS boot phase is NOT instrumented)`
   → `HookWatch: game ELF loaded: 'cdrom0:\SLUS_206.13;1'` → **`HookWatch: ARMED (reason=elf_loaded frame=6)`**
   → `HookWatch: watch hits=2000 frame=243 last: pc=0040DDFC addr=00563A3A size=16 W value=0000000000000720`。
   （最后那一行是**逐字可对照的指纹**：重建版与事故前那一版帧 243 的第一条摘要完全相同。）
   同时全程搜 `TLB Miss` 与 `Trap exception` 应该都是 **0**。
2. **按一次 F10**（窗口点一下让它在前台）或在 `qt\hookdumps\` 里新建空文件 `TRIGGER`：
   几秒后 `qt\hookdumps\` 出现 `hook_<帧号>_hotkey_f10\`（或 `hook_<帧号>_file_trigger\`），
   里面 7 个文件（`ee_ram.bin` 32 MB / `ring.txt` ~13 MB / `ring.bin` 6 MB / `regs.txt` / `meta.txt` / `iop_ram.bin` / `watch_*.bin`），
   emulog 里带**绝对路径和每个文件的字节数**。
3. **再跑一次可关性**：在 `qt\hook\` 里放一个名为 `OFF` 的空文件（或加 `-nohook`）重启，
   `qt\logs\emulog.txt` 里应该**一行 `HookWatch:` 都没有**（命中 0）；删掉 `OFF` 再启动又恢复第 1 条的表现。

> 想更严格：跑 §4.2 那条 gsrunner 命令，出现 **191 张快照 / `frames=6000` / 命中 2,564,000 / 末条 `frame=5961 pc=004147D0 addr=00570170 size=32 W value=0000000000000000`**
> 就是与事故前**逐字一致**；exe 的 sha256 应为 `956151755464572D8287A7C0FF7271C9152511E9D90C80CCDF261621CFD7B452`。

---

## 7. 复跑命令（可审计）

```powershell
# 1) 重建 + 重新部署便携目录（本轮实际用过的那条；QtPrefix 指向本轮恢复的 6.10.3）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\build_qt2.ps1 `
  -QtPrefix "$PWD\work\builds\GR_HOOKEMU_QT2\deps\6.10.3\msvc2022_64" -Jobs 10

# 1b) 只重刷便携目录（不编译）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\build_qt2.ps1 `
  -QtPrefix "$PWD\work\builds\GR_HOOKEMU_QT2\deps\6.10.3\msvc2022_64" -SkipBuild

# 2) C1：零参数端到端（每 4 s 截图；t=240 s 按 F10；t=330 s 放 TRIGGER）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\qt_e2e_run.ps1 `
  -Exe "$PWD\work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe" `
  -EmuArgs "$PWD\work\builds\GR_COMBFIX\COMBFIX_2400.iso" `
  -RunDir "$PWD\work\builds\GR_HOOKEMU_QT2\runs\REBUILD\C1" `
  -DumpDir "$PWD\work\builds\GR_HOOKEMU_QT2\qt\hookdumps" `
  -EmuLog  "$PWD\work\builds\GR_HOOKEMU_QT2\qt\logs\emulog.txt" `
  -TimeoutSec 1080 -ShotEverySec 4 -F10AtSec 240 -TriggerAtSec 330

# 3) C3：可关性（应得到 0 条 HookWatch 行）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\qt_e2e_run.ps1 `
  -Exe "$PWD\work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe" `
  -EmuArgLine ('-nohook "' + "$PWD\work\builds\GR_COMBFIX\COMBFIX_2400.iso" + '"') `
  -RunDir "$PWD\work\builds\GR_HOOKEMU_QT2\runs\REBUILD\C3_nohook" `
  -DumpDir "$PWD\work\builds\GR_HOOKEMU_QT2\qt\hookdumps" `
  -EmuLog  "$PWD\work\builds\GR_HOOKEMU_QT2\qt\logs\emulog.txt" `
  -TimeoutSec 95 -ShotEverySec 15 -NoF10 -NoTrigger

# 4) C1b：gsrunner 6000 帧 / 每 30 帧一张 GS 快照（用产品配置）
$env:PCSX2_HOOK_CONFIG = "$PWD\work\builds\GR_HOOKEMU_QT2\qt\hook\hook_config.ini"
& "$PWD\work\builds\GR_HOOKEMU_QT2\build\pcsx2-gsrunner\pcsx2-gsrunner.exe" `
  -grdumpdir "$PWD\work\builds\GR_HOOKEMU_QT2\runs\REBUILD\G2" -grmaxframes 6000 -grsnap 30 `
  -grbios "$PWD\work\builds\GR_HOOKEMU_QT2\qt\bios" -grbiosname SCPH-90006_BIOS_VX_HK_2.20.bin `
  -grmemcards "$PWD\work\builds\GR_HOOKEMU_QT2\qt\memcards" `
  -logfile "$PWD\work\builds\GR_HOOKEMU_QT2\runs\REBUILD\G2\emulog.txt" -- `
  "$PWD\work\builds\GR_COMBFIX\COMBFIX_2400.iso"
$env:PCSX2_HOOK_CONFIG = $null

# 5) 窗口几何探针（截图拍到"假窗口"时先跑这个）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\win_probe.ps1 `
  -Exe "$PWD\work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe" `
  -EmuArgs "$PWD\work\builds\GR_COMBFIX\COMBFIX_2400.iso" `
  -OutDir "$PWD\work\builds\GR_HOOKEMU_QT2\runs\REBUILD\PROBE" -WaitSec 30 -DesktopShot

# 6) F10 专用探针（先真实点击激活窗口，再发 F10）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\f10_probe.ps1 `
  -Exe "$PWD\work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe" `
  -EmuArgs "$PWD\work\builds\GR_COMBFIX\COMBFIX_2400.iso" `
  -OutDir "$PWD\work\builds\GR_HOOKEMU_QT2\runs\REBUILD\F10" -ArmWaitSec 80 -Taps 3 -SettleSec 20
```

### 现场文件索引

| 路径 | 内容 |
| --- | --- |
| `runs\REBUILD\build.log` | 本轮 `build_qt2.ps1` 完整输出（470 步 + 部署） |
| `runs\REBUILD\qt_manifest_sha256.txt` | `qt\` 全目录逐文件 sha256（1,317 行） |
| `runs\REBUILD\C1\` | C1 现场：`summary.txt`、261 张 `shots\shot_*.png`、`emulog_copy.txt`、`contamination.txt` |
| `runs\REBUILD\C1_aborted_minimized\` | 被外部最小化而作废的那次跑（142 张无效截图）——**保留为证据** |
| `runs\REBUILD\C3_nohook\` | 可关性现场（0 条 HookWatch 行） |
| `runs\REBUILD\F10\` | F10 探针现场（`summary.txt` + `emulog_copy.txt`） |
| `runs\REBUILD\G1\` `G2\` | gsrunner 现场（各 191 张快照；G1=内置默认，G2=产品配置） |
| `runs\REBUILD\PROBE\` | 窗口几何探针（`windows.txt` 列出全部顶层窗口、`largest.png`、`desktop.png`） |
