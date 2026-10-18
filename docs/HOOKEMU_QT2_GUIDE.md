# 用户手册：QT2 取证版模拟器（幽灵行动 SLUS-206.13 汉化）

> 这一版是**像官方一样直接用**的 PCSX2：双击 exe → 载入游戏 → 卡死时按一下 F10。
> **不需要任何命令行参数**，钩子默认就开着，所有输出都在 `logs\emulog.txt` 里。
>
> 配套：完整技术报告见 `docs\REPORT_HOOKEMU_QT2.md`。

---

## 0. 你拿到的是什么

| 路径 | 说明 |
| --- | --- |
| `work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe` | **便携版模拟器本体**（双击它） |
| `...\qt\hook\hook_config.ini` | 钩子配置（唯一需要改的文件；不改也能用） |
| `...\qt\logs\emulog.txt` | **★ 日志：钩子的全部输出都在这里** |
| `...\qt\hookdumps\` | 取证输出目录；卡死后会出现 `hook_<帧号>_<原因>\` |
| `...\qt\README_怎么用.txt` | 同内容的随包说明 |
| `...\build\pcsx2-gsrunner\pcsx2-gsrunner.exe` | 无界面版（同样的钩子，自动化/批量跑用） |
| `...\build_qt2.ps1` | 一键重新构建（可选） |
| `...\hooks_qt2.patch` | 对 PCSX2 源码的全部改动（可审计） |

`qt\` 里的设置、BIOS、记忆卡都是**你自己那套官方配置的副本**（`qt\inis\PCSX2.ini`、
`qt\bios\`、`qt\memcards\`），并且做成了**便携目录**（`portable.txt`）——
所以它读的是自己目录里的设置，**不会动你的 `%LOCALAPPDATA%\PCSX2`**。

> ⚠ 你在 QT2 里玩出来的记忆卡存档写进 `qt\memcards\`，是你原记忆卡的副本，不是原卡。

---

## 1. 三步开跑

### 第 1 步：载入游戏（和官方一样）

三种都行：

1. 双击 `qt\pcsx2-qt.exe`，然后菜单 **系统 → 启动光盘**，选你的 `.iso`；
2. 把 `.iso` 直接**拖到** `pcsx2-qt.exe` 上；
3. 命令行：`qt\pcsx2-qt.exe "D:\你的盘.iso"`（可选，不是必须）。

**怎么确认钩子在工作**：用记事本打开 `qt\logs\emulog.txt`，找 `HookWatch:` 开头的行：

```
HookWatch: ACTIVE (QT2) source=command line config='...\qt\hook\hook_config.ini'
HookWatch: watch=00500000-00580000 arm_after=auto arm_frame=900 ring=262144 entries dumpdir='...\qt\hookdumps'
HookWatch: waiting to arm (BIOS boot phase is NOT instrumented)     ← 开机阶段不插桩（故意的）
HookWatch: game ELF loaded: 'cdrom0:\SLUS_206.13;1' entry=0x00100008
HookWatch: ARMED (reason=elf_loaded frame=6): ...                  ← ★ 到这一步就开始记录了
HookWatch: page 0053E000 holds guest code -> un-watched ...         ← ★ 代码页自动豁免（正常现象）
HookWatch: watch hits=2000 frame=243 last: pc=0040DDFC addr=00563A3A size=16 W value=0000000000000720
```

看到 **`ARMED`** 和 **`watch hits=`**，就说明一切正常。
（`page ... holds guest code -> un-watched` 是**正常且必要**的：代码页不能被监视，否则模拟器会崩。）

### 第 2 步：卡死/卡顿/画面不动时，抓现场

**推荐：按一下 F10**（模拟器窗口要在前台）。
也可以在 `qt\hookdumps\` 里**新建一个名为 `TRIGGER` 的空文件**（没有扩展名），效果一样。

另外两种是自动的：命中配置里的**触发 PC**、或者 EE 发生**致命异常**（Trap/地址错误）时自动抓。

落盘要几秒（要写 32MB 内存快照）。完成后 `emulog.txt` 里会出现：

```
HookWatch: F10 pressed (frame 14272) -> dumping
HookWatch: dumping to ...\hookdumps\hook_14272_hotkey_f10
HookWatch: dump dir (absolute): ...\hookdumps\hook_14272_hotkey_f10
HookWatch:   file: ...\hook_14272_hotkey_f10\ee_ram.bin  33554432 B (32.0 MB)
HookWatch:   file: ...\hook_14272_hotkey_f10\ring.txt  14114010 B (13.5 MB)
HookWatch: top writer PCs (7 unique, showing up to 20): 00414DC0x...
HookWatch: ring tail (last 40 of 262144 records, chronological):
HookWatch:        262104 f=14272 pc=00414CEC addr=00570174 size=32 W src=1 value=0000000000003A5B
HookWatch: dump complete in 125 ms
```

**不用打开 dump 目录也能看懂**：emulog 里直接给了"写得最多的 PC 排行"和"最后 40 条写记录"。

### 第 3 步：回传哪些文件

| 必须回传 | 说明 |
| --- | --- |
| `qt\logs\emulog.txt` | 整个日志（钩子全部输出） |
| `hookdumps\hook_<帧号>_<原因>\ring.txt` | **核心证据**：谁（PC）什么时候写了哪个地址、写了什么值 |
| `hookdumps\hook_<帧号>_<原因>\meta.txt` | 触发原因、帧号、监视区间、触发 PC、寄存器 |
| `hookdumps\hook_<帧号>_<原因>\regs.txt` | PC / 32 个通用寄存器 / CP0 / 最近执行过的块 PC |

| 建议一起回传（压缩后很小） | 说明 |
| --- | --- |
| `...\ee_ram.bin`（32MB） | 卡死瞬间的整块 EE 主存，用来复核内存 |
| `...\iop_ram.bin`（2MB） | IOP 内存 |
| `...\ring.bin`（6MB） | 同 ring.txt 的二进制版，便于脚本分析 |
| `...\watch_*.bin` | 被监视区间（默认 512KB）的快照 |

**不需要回传**：记忆卡（`memcards\`）、BIOS、ISO。

压缩示例（把 `<帧号>` `<原因>` 换掉）：

```
7z a dump.7z "hookdumps\hook_<帧号>_<原因>\*"
```

---

## 2. 已知前提（很重要，别踩）

> ★ **不要用旧即时存档测试"只改光盘"的补丁。**
>
> PCSX2 的即时存档（`.p2s`）会把**整块 32MB EE 主存**一起恢复；读旧存档时 BIOS **不会**再从光盘装载 ELF，
> 所以"只改 ISO 里的代码"在这种场景下**完全不生效**（本工程实测：读旧存档时，修好的盘与未修的盘在内存上逐字节相同）。
>
> - 要验证"只改盘"的补丁 → 请**从记忆卡存档继续玩**，或者用我们打好补丁的存档；
> - 本工程验证用的补丁存档：`work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s`。

另外两条：

- `-statefile` 载入即时存档后**模拟器是暂停的**（工具栏 Pause 高亮）：先按一下 **P** 或点 Pause 让它继续跑，
  否则 F10 / TRIGGER 都不会被处理（因为不跑帧）。
- 本版默认监视 `0x00500000-0x00580000`（含分配器状态 `0x0055B7A0`、桶 126 槽 `0x0055BB98`）；
  **不要把它扩到含代码页的区间**——含代码的页会（也必须）被自动剔除，剔得越多漏得越多。

---

## 3. 想关掉钩子 / 调速度

**临时关掉钩子**（排查"是不是钩子的问题"）三种方式任选：

1. `hook\hook_config.ini` 里把 `enabled` 改成 `0`；
2. 在 `hook\` 目录里新建一个名为 `OFF` 的空文件；
3. 命令行加 `-nohook`（例：`pcsx2-qt.exe -nohook "D:\盘.iso"`）。

关掉后就是普通 PCSX2，没有任何钩子开销。

**觉得自己机器上变慢了**（被监视的 512KB 走慢路径，属正常）：

```ini
; qt\hook\hook_config.ini
watch = 0x0055B000-0x0055C000     ; 只盯分配器元数据页，流量最小
```

---

## 4. 配置项速查（`qt\hook\hook_config.ini`）

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `enabled` | `1` | 钩子总开关 |
| `watch` | `0x00500000-0x00580000` | 监视的 EE 物理地址区间（可写多行） |
| `arm_after` | `auto` | `auto`＝游戏 ELF 装载后 / 读存档后武装；`immediate`＝开机就武装（旧版行为，**会黑屏**，别用） |
| `arm_frame` | `900` | 上面两种情况都没发生时的兜底帧号 |
| `jit_hooks` | `1` | `1`＝精确到指令的 PC/宽度/值（推荐）；`0`＝只走 C 钩子（更保守，EE 的 JIT store 不记录） |
| `watch_reads` | `0` | 是否连读也记录（更慢） |
| `dump_on_hotkey` | `1` | F10 落盘 |
| `trigger_file` | `1` | `TRIGGER` 文件落盘 |
| `dump_on_exception` | `1` | EE 致命异常自动落盘 |
| `dump_on_trigger` | `0` | 命中触发 PC 自动落盘（**默认关**，免得开局就把额度用完；要开就改 1） |
| `max_dumps` | `8` | 一局最多落盘几次（防爆盘） |
| `full_ram` | `1` | 是否带 32MB EE + 2MB IOP 快照（关掉省 34MB） |
| `auto_input` | 无 | 自动按键（复现用）：`auto_input = 30 L1 5` ＝武装后第 30 帧按 L1 五帧 |
| `log_every` | `2000` | 每记录这么多条命中就往 emulog 写一行摘要 |

---

## 5. 排错

| 症状 | 处理 |
| --- | --- |
| emulog 里没有 `HookWatch:` 行 | 看 `hook\` 里是不是放了 `OFF` 文件；看 ini 里 `enabled` 是不是 0 |
| 只有 `waiting to arm`，没有 `ARMED` | 游戏还没载入 ELF（还在 BIOS 阶段）；等菜单/LOGO 出来就有了 |
| `ARMED` 之后没有 `watch hits=` | 游戏还没写到被监视的区间；把 `watch` 放宽一点，或先玩到有堆活动的地方 |
| 按 F10 没反应 | 窗口要在前台；如果刚读了即时存档，**先按 P 解除暂停**；也可改用 `TRIGGER` 文件 |
| 落盘目录是空的 | 看 emulog 里有没有 `dump limit (...) reached`（额度用完了，改大 `max_dumps`） |
| 模拟器启动就崩 | 用 `-nohook` 启动一次对比；若不再崩，把 `hook\hook_config.ini` 发我（附 emulog） |
| 想要更详细的日志 | `all_logging = 1`（会非常慢，只在排障时用） |

---

## 6. 一键重建（一般不需要）

```powershell
# 完整重建（configure + 编译 + 部署便携目录）——★ 2026-10-18 之后请带上 -QtPrefix
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\build_qt2.ps1 `
  -QtPrefix "$PWD\work\builds\GR_HOOKEMU_QT2\deps\6.10.3\msvc2022_64"

# 只重刷便携目录（不编译）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\build_qt2.ps1 `
  -QtPrefix "$PWD\work\builds\GR_HOOKEMU_QT2\deps\6.10.3\msvc2022_64" -SkipBuild

# 重建内置数据根（从你官方设置的只读副本生成相对路径版本）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\make_portable_data.ps1

# 生成/校验源码补丁
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_HOOKEMU_QT2\tools\make_patch.ps1
```

构建需要（本机已有）：便携 MSVC（`C:\Users\84363\pbt\msvc\setup_x64.bat`，834 B，**不是** 0 字节那个）、
**Qt 6.10.3**、KDDockWidgets 2.4.1（`work\builds\GR_HOOKEMU\deps\kddock`）、工程依赖（`third_party\deps`）。

> ⚠ **Qt 6.10.3 的位置在 2026-10-18 变了**：原来用的 `work\builds\GR_HOOKEMU\deps\6.10.3\msvc2022_64`
> 在那次磁盘清理里被删掉了 7 个大于 5 MiB 的 Qt DLL（`Qt6Core/Qt6Gui/Qt6Widgets` 及其 debug 变体等），
> `moc/uic/rcc/windeployqt/lrelease` 因此都跑不起来。现在用的是**重新下载、完好的**那一份：
> `work\builds\GR_HOOKEMU_QT2\deps\6.10.3\msvc2022_64`（qtbase+qtsvg+qttools+qttranslations，4,195 文件 / 419.5 MB）。
> 所以**请给 `build_qt2.ps1` 加 `-QtPrefix` 指到新路径**；不加会退回旧的（已损坏的）前缀而失败。
> 细节与全部数字见 `docs\REPORT_HOOKEMU_QT2_REBUILD.md`。

---

## 7. 这一版和上一版（带钩子的旧 Qt 版）的区别

| | 旧版（`GR_HOOKEMU\qt`） | **QT2（本版）** |
| --- | --- | --- |
| 启动方式 | 要 `-hook`（而且不加参数时也会自动开钩子，导致黑屏） | **双击即用**，钩子默认开 |
| 武装时机 | `memReset()` 开机就接管监视页 | **延迟武装**：BIOS 阶段完全不插桩，ELF/读档后才武装 |
| 代码页 | 代码页也被 handler 接管 → 游戏执行垃圾 → **黑屏** | 代码页**自动豁免**（编译该块前恢复成普通 RAM） |
| 日志 | 只在 `-logfile` 指定时写，ini 里文件日志还是关的 | 全部写进 **`logs\emulog.txt`**，含命中摘要/落盘路径/异常/崩溃 |
| 记录内容 | 需要 JIT 调用式钩子 | 慢路径 C 钩子 + 精确 PC（`g_current_access_pc`）+ JIT 钩子 |
| 本机实测 | 黑屏（46 行 TLB Miss，PC=0），或帧 154 崩溃 | 帧 **28588**、`TLB Miss 0 / Trap 0`、**3,810,000 条命中**、F10/TRIGGER 落盘正常 |

---

## 8. 分配器自旋修复（2026-10-18 追加，轮次 GR_SPINFIX）

> 完整技术报告：`docs\REPORT_SPINFIX.md`。这一节只讲**你要做的三步**。

### 8.1 你拿到的四张修复盘

在 `work\builds\GR_SPINFIX\`：

| 盘 | 用什么 | 说明 |
| --- | --- | --- |
| **`SPINFIX_F4.iso`** | ★ **先用这张** | 最小改动（站点 1 处 + 36 B cave）。本机实测：原来卡死的那次 `malloc(0x10020)` 不再打转，Trap 2,647,472 行 → **0**，300 帧正常跑完；6000 帧冒烟 **191 张截图 / TLB 0 / Trap 0 / 与基底逐帧 0 差异** |
| `SPINFIX_F1F2_F4.iso` | 长期用 | 在上面的基础上再"防写坏"（F1+F2）。⚠ 已知瑕疵：6000 帧冒烟里有 **6 帧**与基底不同（帧 660~810，像素级小差异，最大 38/255），见报告 §4.2 |
| `SPINFIX_F1F2.iso` | 只做研究 | **单独用救不了已经卡死的存档**（它只管"别再写坏"，不管"已经坏了"） |
| `SPINFIX_F4_2400.iso` | 产品线（2400 基底） | 与 `GR_REBUILD2400` 逐帧 **0 差异** |

### 8.2 ⚠ 用即时存档必须改名（否则读不到档）

补丁改动了 ELF，PCSX2 看到的 **CRC 也变了**。你的旧档名是 `SLUS-20613 (7A761FCA).01.p2s`，换盘后要改成：

| 盘 | 新 CRC | 状态文件应叫 |
| --- | --- | --- |
| `SPINFIX_F4.iso` | `755BD0BA` | `SLUS-20613 (755BD0BA).01.p2s` |
| `SPINFIX_F1F2.iso` | `BED57022` | `SLUS-20613 (BED57022).01.p2s` |
| `SPINFIX_F1F2_F4.iso` | `B1F8BF52` | `SLUS-20613 (B1F8BF52).01.p2s` |
| `SPINFIX_F4_2400.iso` | `751BD0BA` | `SLUS-20613 (751BD0BA).01.p2s` |

更稳的做法：**别用即时存档**，从记忆卡存档或关卡开头进——这样盘上的补丁一定生效（即时存档会把整块 32 MB 内存恢复，等于把补丁"盖回去"）。

### 8.3 怎么确认修好了

1. 载入 `SPINFIX_F4.iso`，走到原来卡死前一步；
2. **按 L1**（原来一按就卡死的那个动作）；
3. 看：
   * **不卡了** = 修好了（本机：帧数从"卡在 44 帧"变成"一路跑完 300 帧"）；
   * 日志里**可能仍会出现 1~2 行** `TLB Miss … addr=0x6ed4782b / 0x6ed47837` —— **正常**（检查在那两条读之后），关键是**不会出现第 3 行、不会无限刷屏**；
   * 若还卡死：把 `logs\emulog.txt` + 盘名 + 当时按的键发回来。

### 8.4 下一次抓"谁写坏的"：换一份钩子配置

把 `work\builds\GR_SPINFIX\hook_config_next.ini` 覆盖到 `qt\hook\hook_config.ini`（**只覆盖这一个文件**），照旧双击开玩、卡死/异常时按 **F10**。
改了三件事（数字来自你自己两份 dump 的 ring 实测）：

* `watch` 收窄到 `0x0055B7A0-0x0055C000`（只盯分配器状态 + 128 个桶槽）；
* `ring_entries` 262144 → **2097152**：可回看的时长从 **~15 秒** 提到 **~174 秒**（覆盖你上次没抓到的那个 42 秒损坏窗口，还有 4~6 倍余量）；
* `log_every` 2000 → 500，并且把自动落盘触发 PC 收窄成 **真正写坏桶 126 的那一对 store**（`0x00102010/0x00102014`）+ 卡死现场的两条 load（`0x001024D0/0x00102584`）——第一次"大块插链"就会被自动抓下来。

> 提醒：新配置每次落盘 ≈190 MB（ring.bin 48 MB + ring.txt ~110 MB + ee_ram 32 MB + iop 2 MB），`max_dumps` 已设成 3。

## 9. 「任务完成处卡死」的组合修复盘（2026-10-18 追加，轮次 GR_COMBFIX）

> 完整技术报告：`docs\REPORT_COMBFIX.md`。这一节只讲**你要做的三步**。

### 9.1 你拿到的四张盘（`work\builds\GR_COMBFIX\`）

| 盘 | 补丁 | **CRC（改名用）** | 说明 |
| --- | --- | --- | --- |
| **`COMBFIX_C.iso`** | F4 + OOMFIX + **F7** | `CF9B8C97` | ★ **先用这张**。在你的 `SPINFIX_F4.iso` 基础上补了一处：malloc 的「请自己的桶」快路径回边（`0x001021D4`）也做链头校验。本机实测：不修/F4/A/B 四张盘遇到这种坏桶时都会死在 `0x102180→0x1021A0→0x1021D0` 的三块死循环，只有这张能出来（F7 cave 命中 3 次 → malloc 正常返回 2,031 次 → 解压器 14 次 → 300/600 帧无 Trap）；6000 帧冒烟 **191 张截图 / TLB 0 / Trap 0 / 与基底逐帧 0 差异** |
| `COMBFIX_2400.iso` | F4 + OOMFIX + F7 | `CFDB8C97` | 产品线（2400 基底），补丁集合与 C 相同；6000 帧冒烟与 `GR_REBUILD2400` **逐帧 0 差异** |
| `COMBFIX_A.iso` | F4 + OOMFIX | `C36C1073` | 对照盘：**治不了这次的新卡死**（F4 覆盖不到那条回边） |
| `COMBFIX_B.iso` | A + F1 + F1b | `3AA01EA7` | 研究盘：**也治不了这次的新卡死**；6000 帧里有 **6 帧**（660~810，引导阶段）与基底有像素差异，见报告 §4.3 |

### 9.2 怎么测「任务完成 → 结算」

1. **优先别用旧的即时存档**：从**记忆卡存档**或**关卡开头**进（旧 `.p2s` 会把整块 32 MB 主存恢复，盘上的补丁会被"盖回去"）。
   * 一定要用即时存档的话，**必须改名**：例如 `COMBFIX_C.iso` → `SLUS-20613 (CF9B8C97).01.p2s`，放进 `%LOCALAPPDATA%\PCSX2\sstates\`。
   * 你那份"已经中毒"的存档（桶 126 = `0xF968B859`）**不用重建**：`COMBFIX_C`/`COMBFIX_2400` 也能救（F7 会把坏链头拦下）；但 `COMBFIX_A`/`B` 救不了。
2. 打到**完成全部目标** → 出现「任务完成」提示 → 继续按确认/等它切**结算**（就是原来卡住的那一步）。
3. 看：
   * **能进结算 / 能继续玩** = 修好了；
   * 日志里**可能仍会有 1~2 行** `TLB Miss … addr=0x6ed4782b / 0x6ed47837 / 0xf968b861 / 0xf968b86d` —— **正常**（检查在那两次读之后），关键是**不会出现第 3 行、不会无限刷屏**；
   * 还卡的话：把 `logs\emulog.txt` + 当时在做什么 + 盘名发回来，**顺手按 F10**（会落一份 32 MB RAM 现场）。

### 9.3 为什么这轮不带 F1/F1b（怕你看到 B 盘发懵）

* 这次卡死的直接原因是**桶里已经有坏指针**（很早以前被写进去的），F1/F1b 只能"防止以后再写坏"，**救不了已经坏的桶**；本机实测 B 盘遇到同一现场**照样死循环**。
* 而且 F1 的 cave（`0x0055B730`）旁边是活跃数据，实测会带来 **6 帧**（引导阶段 660~810）像素差异 —— 收益没证明、代价已测到，所以**推荐盘里不带它**。B 盘留着给"以后想查是谁写坏桶"用。

### 9.4 下一次取证：TLB Miss 日志为什么会"卡在 50 行"

模拟器源码里写死了 TLB Miss 的打印上限（`vtlb.cpp`：`if (spamStop++ < 50)`），**只有前 50 条会进 emulog**；你这次卡死在 388 s，那之后的 miss 就再也看不到了。
想让日志更有用：把 `hook_config_next.ini` 里的 `watch` 收窄到 `0x0055B7A0-0x0055C000`（只盯分配器状态 + 128 个桶槽），并保留 `ring_entries = 2097152`；这样"哪些桶在被写"会看得很清楚（TLB 那 50 行改不了，只能靠 RAM 现场 + ring 反推）。

---

## 10. 2026-10-18：误删事故后的重建版（你手上这一份）

> 完整报告：`docs\REPORT_HOOKEMU_QT2_REBUILD.md`。**行为没变**，只是 exe 是重新编译出来的。

### 10.1 一句话

一次磁盘清理误删了便携目录里的 `pcsx2-qt.exe` 和几个大于 5 MiB 的 Qt 运行库（连带源码副本里 1 个头文件、构建树里 11 个中间产物）。
现已从**重新下载的 Qt 6.10.3** 重建并验证完毕，用法与之前**完全一样**（双击即用、钩子默认开、F10/`TRIGGER` 落盘、`-nohook` 可关）。

- 新的 `pcsx2-qt.exe`（11,765,248 B）
  sha256 = **`956151755464572D8287A7C0FF7271C9152511E9D90C80CCDF261621CFD7B452`**
- Qt 运行库全部为 **6.10.3.0**；`resources\`、`translations\`、`hook\`、`inis\`/`bios\`/`memcards\`、`README_怎么用.txt` 都在
- 你放在 `qt\hookdumps\` 里的**那 3 份** `hook_19671/19701/23444_hotkey_f10` **一个字节都没动**（注意它们的大文件 `ee_ram.bin`/`ring.bin`/`ring.txt` 是被同一次清理删掉的，找不回来了）

### 10.2 怎么最快确认"和之前一样"（三条）

1. **日志三行**：双击 `qt\pcsx2-qt.exe` 载入游戏，看 `qt\logs\emulog.txt`：
   `HookWatch: ACTIVE (QT2) source=…qt\hook\hook_config.ini` → `waiting to arm (BIOS boot phase is NOT instrumented)`
   → `game ELF loaded: 'cdrom0:\SLUS_206.13;1'` → **`ARMED (reason=elf_loaded frame=6)`**
   → `watch hits=2000 frame=243 last: pc=0040DDFC addr=00563A3A size=16 W value=0000000000000720`
   （最后这行是**逐字指纹**，重建版与事故前那一版一模一样）；全程 `TLB Miss` 与 `Trap exception` 都应该是 **0**。
2. **F10 或 `TRIGGER`**：窗口点一下让它到前台再按 **F10**（或往 `qt\hookdumps\` 放一个名为 `TRIGGER` 的空文件）→
   出现 `hook_<帧号>_hotkey_f10\`（或 `hook_<帧号>_file_trigger\`），7 个文件；emulog 里有绝对路径和每个文件大小。
   ⚠ **F10 必须让模拟器窗口真的在前台**（它是用 `GetAsyncKeyState` 轮询的）：如果窗口在后台，按 F10 不会落盘，改用 `TRIGGER` 文件即可。
3. **可关性**：在 `qt\hook\` 里放一个空的 `OFF` 文件（或加 `-nohook`）再启动 → `emulog.txt` 里**一行 `HookWatch:` 都没有**；删掉 `OFF` 就恢复。 

### 10.3 本轮实测数字（想复跑就用 §6 的命令）

| 验证 | 结果 |
| --- | --- |
| C1 零参数端到端（Qt，`COMBFIX_2400.iso`） | 1083 秒、**261 张窗口截图**（1933×1045，每 4 s）、亮度 **13.0–117.3**（117 个不同值，**0 张黑屏**）、**帧 64,594**、**命中 4,460,000**、`TLB 0 / Trap 0`、中文界面正常 |
| C1b 同核心 6000 帧（gsrunner） | **191 张快照** / `frames=6000` / **命中 2,564,000** / 末条 `frame=5961 pc=004147D0 addr=00570170 size=32 W value=0000000000000000` / `TLB 0 Trap 0` —— **与事故前记录逐字一致** |
| C2 落盘 | F10 真实按键 → 帧 **4641**、**4677** 两份；`TRIGGER` 文件 → 帧 **19719** 一份（各 7 个文件） |
| C3 `-nohook` | 95 秒：`HookWatch:` 行 **0**、命中 **0**、无 dump；游戏照常跑（CRC `CFDB8C97`） |
