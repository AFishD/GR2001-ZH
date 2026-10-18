# 幽灵行动（SLUS-206.13）汉化 —— 带「写监视 + 取证」的 PCSX2 Qt 版使用手册

> 目标：在你的官方 PCSX2 复现「游玩中卡死 / 2fps 挂起」时，**在卡死现场把证据落盘**——
> 到底是哪一条 store 指令、以什么值、写到了被写坏的分配器区域。
>
> 本手册面向非开发者，照抄命令即可。

---

## 0. 先看你拿到了什么

| 路径 | 说明 |
| --- | --- |
| `work\builds\GR_HOOKEMU\qt\` | **便携版 Qt 模拟器**（`pcsx2-qt.exe` + Qt DLL + `resources\` + `hook\`） |
| `work\builds\GR_HOOKEMU\qt\hook\hook_config.ini` | 钩子配置（唯一需要改的文件） |
| `work\builds\GR_HOOKEMU\qt\hookdumps\` | 默认的取证输出目录（里面会出现 `hook_*/`） |
| `work\builds\GR_HOOKEMU\build\pcsx2-gsrunner\pcsx2-gsrunner.exe` | 控制台版（同样的钩子，用于自动化/无界面验证） |
| `work\builds\GR_HOOKEMU\hooks.patch` | 对 PCSX2 源码的全部改动（可审计） |
| `work\builds\GR_HOOKEMU\build_hooked_emu.ps1` | 一键重新构建脚本 |

**这个 Qt 版和官方 PCSX2 是同一个模拟器内核**（同一份源码 + 钩子），所以它能复现你的卡死；
它默认**不打开**任何钩子，只有加 `-hook` 才会变慢、才开始记录。

---

## 1. 三步开跑

### 第 1 步：打开钩子启动

在资源管理器里进入 `work\builds\GR_HOOKEMU\qt\`，在地址栏输入 `cmd` 回车，然后：

```bat
pcsx2-qt.exe -hook
```

- 如果你把 `hook\hook_config.ini` 放在别处：`pcsx2-qt.exe -hookconfig D:\某处\hook_config.ini`
- 必须看到窗口标题/日志里出现 `HookWatch: ACTIVE ...` 才算钩子生效（日志在 `hookdumps\hooked_emulog.txt`，或菜单 设置→日志）。

### 第 2 步：BIOS / 记忆卡 / 渲染器

- 默认它使用你**现有的 PCSX2 配置**（BIOS、记忆卡、画面设置都沿用），无需重设。
- 如果它弹出「设置向导」：把 BIOS 选成你平时用的那个（例：`SCPH-90006_BIOS_VX_HK_2.20.bin`）、
  记忆卡用空卡或你自己的卡即可，渲染器建议 **Vulkan**（和官方一致，最容易复现卡死）。
- 如果它提示 **无法写 `Documents\PCSX2\inis\PCSX2.ini`**（权限/被占用），用私有数据目录启动：

```bat
pcsx2-qt.exe -datapath "%~dp0qtdata" -hook
```

  然后把 `qtdata\PCSX2\inis\PCSX2.ini` 里的 `[Folders] Bios=` 指向你的 BIOS 目录。

### 第 3 步：正常玩，直到卡死

- 用你平时的方式引导 `GR_REBUILD2400.iso`（本工程已确认能复现卡死的镜像）。
- 玩到卡死/掉到 2fps 的那一刻，**按一下 F10**（推荐），或者
  在 `hookdumps\` 里新建一个名叫 `TRIGGER` 的空文件（无界面/自动跑时用）。
- 几秒后你会看到新目录：`hookdumps\hook_<帧号>_hotkey_f10\` 或 `..._file_trigger\`。
  日志里会有 `HookWatch: dumping to ...` 和 `dump complete (...)`。

> 什么情况下会自动落盘（不用你按键）：
> 1. 配置里列出的**触发 PC** 被执行（默认是崩溃日志里那 12 个分配器 PC）；
> 2. EE 发生**致命异常**（TLB/地址/总线错误、保留指令、Trap）——中断/系统调用不触发，避免刷屏；
> 3. F10 或 `TRIGGER` 文件。

---

## 2. 卡死之后：要回传哪些文件

进 `hookdumps\hook_<帧号>_<原因>\`，**整个目录打包**回传最省事；至少要有：

| 文件 | 内容 | 大小 |
| --- | --- | --- |
| `ring.txt` | **核心证据**：环形缓冲全量文本，每行 `序号 帧号 PC 地址 宽度 方向 来源 值高:值低` | 1–60 MB |
| `ring.bin` | 同上，二进制（24 字节/条，便于脚本分析） | 24 MB 级 |
| `ee_ram.bin` | 卡死瞬间 EE 主存 32MB 快照 | 32 MB |
| `iop_ram.bin` | IOP 内存 2MB 快照 | 2 MB |
| `watch_*.bin` | 被监视区间（默认 `0x500000-0x580000`）的 512KB 快照 | 0.5 MB |
| `regs.txt` | PC / 32 个 GPR / HI / LO / CP0 状态 + 最近执行过的块 PC 环 | 几 KB |
| `meta.txt` | 本次触发的帧号、原因、监视区间、触发 PC 列表、配置路径 | 几 KB |
| `hooked_emulog.txt` | 模拟器日志（含 `HookWatch:` 行、异常记录） | 几 KB–几 MB |

**压缩建议**：`ee_ram.bin`/`iop_ram.bin`/`ring.bin` 压缩率很高，用 7-Zip 打成 `.7z`（极限压缩）后，
35 MB 的目录通常只剩 **2–6 MB**，可以随便传。

**最省流量的最小集合**（如果只想要结论）：
`ring.txt` + `meta.txt` + `regs.txt` + `hooked_emulog.txt`（约 2–5 MB），
但如果需要我重放/复核内存，就一定要带两个 RAM 快照。

---

## 3. 我们要回答的 3 个问题（你回传的东西正好够）

1. **哪一条 store 最先写坏分配器区？**
   → `ring.txt` 里最后若干条 `W`（写）记录：`pc` 就是那条 store 的客户机 PC，
   `addr` 是被写地址（分配器状态在 `0x0055B7A0`，`least_addr = state-8`），
   `value_hi:value_lo` 是写进去的值，`size` 是宽度。
2. **写它的 PC 属于哪个函数？**
   → 用 `pc` 在反汇编/符号里定位（本工程已有 `GR_DISASM` 工具与 ELF 符号）。
   验证时已抓到的样本：`0x00412A64`、`0x0041226C`、`0x00402EB4`、`0x00402F38`、`0x00402FB8`
   在帧 154 分别往 `0x0056E120 / 0x0056D974 / 0x00561D08 / 0x00561D20 / 0x00561D10` 写入
   `2 / 0x65AEA0 / 0x64BE80 / 0xF180 / 0xF020` —— 这些就是分配器元数据的真实读写者样本。
3. **写坏之前最后执行的文本/渲染相关 PC 是什么？**
   → 在配置里加一行 `trace_pc = 0x00219A70`（或你关心的任一渲染函数入口），
   钩子会把每次执行连同 32 个 GPR 快照写进 `hookdumps\hook_pctrace.txt`；
   再对照 `ring.txt` 的帧号，就能确定「最后一次画字」与「写坏」的先后关系。
   另外 `regs.txt` 末尾的「最近块 PC 环」给出了卡死前执行过的块地址序列。

---

## 4. 钩子开关（`hook\hook_config.ini`）

常用项（改完重启模拟器生效）：

```ini
[hook]
enabled = 1                       ; 1=启用（配合 -hook 使用）
dumpdir = hookdumps               ; 输出目录（相对 exe 所在目录）
ring_entries = 1048576            ; 环形缓冲条数（1M 条 = 24MB）

; ★ 监视的 EE 物理地址区间（可写多行）
watch = 0x00500000-0x00580000     ; 默认值：含分配器状态 0x0055B7A0
; watch = 0x0055B000-0x0055C000   ; 更窄：只看分配器元数据页（流量最小）
watch_reads = 0                   ; 1=连读也记录（很慢，一般不需要）

; ★ 触发 PC（默认 12 个分配器 PC；自己加会覆盖默认，需自行列全）
; trigger = 0x00101D10
; trigger = 0x00101DD8
; trigger = 0x00101DE4
; trigger = 0x00101E08
; trigger = 0x00101E34
; trigger = 0x00101E6C
; trigger = 0x00101FE0
; trigger = 0x00102000
; trigger = 0x00102008
; trigger = 0x001024D0
; trigger = 0x001024E8
; trigger = 0x00102584

trace_pc = 0x00219A70             ; 追踪执行（含寄存器快照），可多行
dump_on_exception = 1             ; 致命异常自动落盘
exception_codes = 1,2,3,4,5,6,7,10,13
dump_on_hotkey = 1                ; F10 落盘
trigger_file = 1                  ; 放一个 TRIGGER 文件即落盘
trigger_once = 1                  ; 每个触发 PC 只落一次盘
max_dumps = 8                     ; 单局最多落盘次数（防爆盘）
full_ram = 1                      ; 是否带 32MB EE / 2MB IOP 快照
max_dump_entries = 0              ; 0=环形缓冲全量写文本（可改成 200000 减小体积）

all_logging = 0                   ; 1=打开全部 PCSX2 日志源（很慢，见下）
logfile = hookdumps\hooked_emulog.txt
```

### 全量日志（CPU/MMU/DMA/GS/SIF/CDVD/IOP…）

两种等价做法：

1. **一键开关**：把 `all_logging = 1`（钩子会把所有 trace 源打开并把日志级别提到 TRACE，
   日志写到 `logfile`）；命令行再加 `-logfile <路径>` 可覆盖输出位置。
2. **纯 PCSX2.ini 片段**（不想用钩子时）——把下面整段贴进 `inis\PCSX2.ini`：

```ini
[Logging]
EnableSystemConsole = false
EnableFileLogging = true
EnableTimestamps = true
EnableVerbose = true
EnableEEConsole = true
EnableIOPConsole = true

[EmuCore/TraceLog]
Enabled = true
EE.bios = true
EE.memory = true
EE.giftag = true
EE.vifcode = true
EE.mskpath3 = true
EE.r5900 = true
EE.cop0 = true
EE.cop1 = true
EE.cop2 = true
EE.cache = true
EE.knownhw = true
EE.unknownhw = true
EE.dmahw = true
EE.ipu = true
EE.dmac = true
EE.counters = true
EE.spr = true
EE.vif = true
EE.gif = true
IOP.bios = true
IOP.memcards = true
IOP.pad = true
IOP.r3000a = true
IOP.cop2 = true
IOP.memory = true
IOP.knownhw = true
IOP.unknownhw = true
IOP.dmahw = true
IOP.dmac = true
IOP.counters = true
IOP.cdvd = true
IOP.mdec = true
MISC.sif = true
```

⚠️ **不要**同时开 `all_logging=1` 和全量 trace + 高负载游戏：日志会到 GB/分钟级，游戏会掉到个位数 fps。

---

## 5. 性能与已知限制（实测结论，务必先看）

| 现象 | 说明 |
| --- | --- |
| 开钩子后游戏明显变慢 | 被监视的页要走 C 层慢路径 + 每条访问都记录。属预期。若只想尽快跑到卡死点，把 `watch` 缩到 `0x0055B000-0x0055C000`。 |
| **不要把 `watch` 越过 `0x00580000`** | 实测（2026-10-17）：`0x00580000-0x00600000` 这段含**代码页**，被映射成监视 handler 后无法参与 PCSX2 的自修改代码保护，游戏会在 ELF 入口处直接崩（退出码 `0xFEFEFEFE`）。默认区间 `0x00500000-0x00580000` 已验证可跑满 2400 帧。 |
| **不要设 `force_slowmem = 1`** | 实测：关掉 EE fastmem 后本游戏在 ELF 入口必崩（同样 `0xFEFEFEFE`）。默认 `0`，用 handler 映射达到「只让被监视页走慢路径」的效果。 |
| 读监视默认关闭 | `watch_reads=1` 会记录读，流量和耗时都翻倍；分配器被写坏只需要看写。 |
| 覆盖范围 | 能抓到 **EE CPU 的 load/store**（含 COP2/VU0 macro 的访存）与经 vtlb 的访问；**DMA/VIF/VU1 微代码直接写内存的路径不经过 vtlb**，不会被记录（当前卡死指纹是 EE 侧写坏，够用；如需覆盖 DMA 请告知，需要另加钩子）。 |
| 全量日志 | 会让游戏更慢；`GS` 相关日志量最大，建议只在你需要时勾。 |
| `-hook` 与官方实例共存 | 不要把本构建和官方 PCSX2 同时开同一个存档/记忆卡目录；本构建默认沿用官方配置目录，建议独占运行。 |

---

## 6. 排错

| 症状 | 处理 |
| --- | --- |
| 日志里没有 `HookWatch: ACTIVE` | 确认加了 `-hook` 或 `-hookconfig <ini>`；确认 ini 里 `enabled = 1`；确认 `hook\hook_config.ini` 在 exe 同级目录。 |
| 启动就退出、退出码 `-16843010`（= `0xFEFEFEFE`） | 模拟器崩溃。检查 `watch` 是否超过 `0x00580000`、`force_slowmem` 是否为 1；`hookdumps\crash_info.txt` 会记录崩溃地址（若有）。 |
| 没有生成 `hook_*` 目录 | 没触发。按 F10（窗口需在前台）、或在 `hookdumps\` 放 `TRIGGER` 文件、或让触发 PC/致命异常发生；也检查是否已达到 `max_dumps`。 |
| 文本太大 | 把 `max_dump_entries` 设为 `200000`（约 11MB 文本），或只回传 `ring.bin` + `meta.txt`。 |
| 想改监视范围 | 一次只改一端，并从小范围（`0x0055B000-0x0055C000`）开始验证能跑，再逐步扩大；**上限 0x00580000**。 |

---

## 7. 复跑一键构建（可选）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU\build_hooked_emu.ps1
# 只刷新便携目录、不重新编译：
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU\build_hooked_emu.ps1 -SkipBuild
# 重新 configure：
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU\build_hooked_emu.ps1 -Reconfigure
```

> 本机 PowerShell 默认禁止运行未签名脚本（`UnauthorizedAccess`），所以上面的 `-ExecutionPolicy Bypass` 是必须的；
> 该脚本已实测可在 `-SkipBuild` 模式跑通并刷新 `qt\` 便携目录。

脚本会：调用便携 MSVC 环境（`C:\Users\84363\pbt\msvc\setup_x64.bat`）→ `cmake -G Ninja`
（Qt 6.10.3 + KDDockWidgets 2.4.1 + `third_party\deps`）→ 构建 `pcsx2-qt` 和 `pcsx2-gsrunner`
→ 用 `windeployqt` 刷新 `qt\` 便携目录。

---

## 8. 相关：解压器 NULL 检查修复（OOMFIX）的验证入口

2026-10-17 的 **OOMFIX** 轮（修 `0x00539110` 解压器不检查 `malloc` 返回值导致的低端内存写坏 / `Trap at 0x80000274`）
给出了两张修复盘与一份**补丁存档**，并新增了一条**对测试方式有决定性影响**的注意事项：

> ★ **PCSX2 的 `.p2s` 即时存档会整块恢复 32 MB EE 主存**；读旧即时存档时 **BIOS 不会再从光盘装载 ELF**，
> 所以「只改 ISO」的补丁在读旧存档的场景里**完全不生效**（本机实测：修好的盘 + 旧存档，运行时 RAM 与未修盘逐字节相同）。
> 验证这类**代码补丁**必须用**记忆卡存档**继续玩，或使用我们打好补丁的存档。

- 用户向的最小步骤：**`docs\OOMFIX_TEST_GUIDE.md`**
- 完整读数与证据：**`docs\REPORT_OOMFIX.md`**
- 产物：`work\builds\GR_OOMFIX\OOMFIX2400.iso` / `OOMFIX_lay1.iso`（各只改 ELF 的 4 + 44 字节）、
  `work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s`（补丁存档）
- 本手册 §1–§4 的钩子玩法**依然适用**（本轮的 hook/watch 用法与上一轮一致）；只有「读档」这一步要按上面的注意事项改。
