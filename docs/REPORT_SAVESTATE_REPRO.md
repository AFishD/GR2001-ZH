# REPORT — 即时存档本地复现（LAY_fix1_bytecount / L1）

- 日期：2026-10-17（本机时区 Asia/Hong_Kong）
- 执行者：SAVESTATE_REPRO 执行者（子 agent）
- 结论一句话：**第一次在本机复现成功** —— 用用户给出的 `.p2s` + `L1`（无头 gsrunner，逐帧注入）稳定复现死机；并抓到现场：**第 44 帧有两条游戏内代码路径（block `0x005391BC` / `0x004039BC`）以字节流方式覆写 EE RAM 低端 `0x1000..0x4000`（BIOS 低端内存 / 异常向量区），第 45 帧 EE 开始执行被写坏的内存（`EE: Unrecognized op`），随即无限 `Trap exception at 0x80000274`（890,286 行/60 帧）**。存档只在"按了 L1"时死；不按 L1 的对照跑 260 帧零异常。

---

## 1. 存档定位（第一步）

| 项 | 值 |
|---|---|
| 路径（工作区，最新） | `work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s` |
| 绝对路径 | `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s` |
| 大小 | 15,253,301 B |
| 修改时间 | 2026-10-17T20:35:40.2487189+08:00 |
| sha256 | `34939ABD07642E77E2615F53B4C1102A7CC8CF206757402A2C70FA8C599675F3` |
| 用户 PCSX2 目录副本 | `%LOCALAPPDATA%\PCSX2\sstates\SLUS-20613 (7A761FCA).01.p2s`（size/mtime/sha256 **完全相同**，即同一份） |

同目录/同源配套文件：

- `work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s.backup`（15,178,103 B，20:35:10）
- `%LOCALAPPDATA%\PCSX2\sstates\` 另有 8 个更旧存档（CRC 后缀 `7A361F8D / 7A361FCA / 7A36E0B1 / 7A361FB5 / 3E571E91 / 3E571E95 / 7A361FB7`）
- `%LOCALAPPDATA%\PCSX2\logs\emulog.txt`（69,168 B，20:35:56）→ 已只读复制为 `work\builds\GR_REPRO\common\user_emulog_2026-10-17_203556.txt`
- 记忆卡 `%LOCALAPPDATA%\PCSX2\memcards\Mcd001.ps2` / `Mcd002.ps2`（各 8,650,752 B，20:35:56）→ 只读复制到各 run 的 `mc\`
- BIOS `SCPH-90006_BIOS_VX_HK_2.20.*`（bin/erom/rom1/rom2/mec/nvm）→ 只读复制到各 run 的 `bios\`（**没有**让模拟器直接写用户 BIOS 目录）

**存档来源可考证**（用户 emulog）：`[224.0268] OSD [SaveStateSlot1]: 已保存即时存档到 位置 1`，0.76 s 后 `[224.7905]` 开始 `TLB Miss, pc=0x1024d0 / 0x102584` 死循环。即该存档正是**卡死前 0.76 秒**那一刻。

**用户日志里的原始故障签名**（只读证据，未改动用户文件）：

```
[207.6867] TLB Miss, pc=0x101d10 addr=0x14e228f7 [load]      ← 本会话第一次
[207.6873] TLB Miss, pc=0x101dd8 addr=0x14 [store]
[207.6875] TLB Miss, pc=0x101dd8 addr=0x10 [store]
[207.6877] TLB Miss, pc=0x101de4 addr=0x14e228f7 [load]
[207.6878] TLB Miss, pc=0x101e08 addr=0x14e228ff [load]
[207.6880] TLB Miss, pc=0x101e34 addr=0x14e22903 [load]
[207.6881] TLB Miss, pc=0x101e34 addr=0x14 [store]
...
[224.7905] TLB Miss, pc=0x1024d0 addr=0x8 [load]  ← 之后成对无限重复
[224.7906] TLB Miss, pc=0x102584 addr=0x14 [load]
```

注意：**用户日志里 `Trap exception` 一次都没有**（已全量 grep 确认），也没有 `EE: Unrecognized op`。

---

## 2. 本机复现（第二步）—— 结果：复现成功 ✓

### 2.1 环境

- 构筑：`third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe`（v2.8.2-1-gcd5e3304c，2026-10-15 11:45）。为不写 `third_party\**`，**整目录复制**到 `work\builds\GR_REPRO\emu\gsrunner\` 后从副本运行（inis/缓存/日志都落在我们自己的目录）。
- 存档版本校验通过：emulog `Savestate version: 0x9a590000`（用户官方 v2.8.2 同为 `0x9a590000`，`g_SaveVersion=(0x9A59<<16)|0` 与 git rev 无关），载入无报错，`eeMemory.bin` 等 15 个模块全部 `found`。
- ISO: `work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso`，sha256 `A69A9CA44049EAED4085239A2B8D10AF58888F54F62A51E40C1ECE22DD2D2808`（与任务书一致）。
- BIOS：`SCPH-90006_BIOS_VX_HK_2.20.bin`（日志 `BIOS Found: Japan v02.20(05/09/2006)`，与用户 emulog 完全一致）。
- 记忆卡：用户同源 `Mcd001/Mcd002` 的**只读副本**（不是空卡）。
- 独占：每次起跑前轮询 `Get-Process pcsx2*`，全程零他人实例；一次只跑一个实例。

### 2.2 逐字命令（以 r11 为例，其它 run 只换 flag/输入表；每 run 的 `cmdline.txt` 已存盘）

```
work\builds\GR_REPRO\emu\gsrunner\pcsx2-gsrunner.exe -grdumpdir work\builds\GR_REPRO\r11_watch_lowram
  -grmaxframes 46 -grpcsample 1 -grwatch 4864 256 -grwatch 5617584 8
  -grinput work\builds\GR_REPRO\r03_l1_memwatch\in_l1_f30.txt
  -grmemcards work\builds\GR_REPRO\r11_watch_lowram\mc
  -grbios work\builds\GR_REPRO\r11_watch_lowram\bios -grbiosname SCPH-90006_BIOS_VX_HK_2.20.bin
  -grstate work\builds\GR_REPRO\common\state_LAY_fix1_bytecount.p2s
  -logfile work\builds\GR_REPRO\r11_watch_lowram\emulog.txt
  -- work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso
```

输入表格式（该构筑源码 `pcsx2-gsrunner/GRResearch.cpp` 确认）：`<帧号> <按键小写> <press|release|hold>`，`press` 在第 +12 帧自动松开。r01/r03/r05/r07/r08/r09/r10/r11 用：

```
# 存档载入后第 30 帧按 L1
30 l1 press
```

日志实测：`[2.8944] GR: input frame 30: bind 10 = 1.0`，`[3.2680] GR: input frame 42: bind 10 = 0.0`（bind 10 = L1）。**帧号以"存档载入完成后的第一帧 = 第 1 帧"计**（`-grstate` 由 `VMManager::Initialize` 在首个 Execute 之前载入，故帧计数不含 BIOS/ELF 启动）。

### 2.3 run 矩阵

| run | 关键 flag | 输入 | 帧数 | 结果 |
|---|---|---|---|---|
| r01_l1 | snap30, memwatch(hex→无效) | L1@30 | 3000(未跑完) | **卡死**；`Trap exception` 洪水，7 分钟 1730 帧写了 **4.18 GB** 日志（已杀，见注） |
| r02_control | grpcsample | **无输入** | 260 | **无任何 TLB/Trap/异常**，10 s 跑完 |
| r03_l1_memwatch | memwatch(十进制) | L1@30 | 60 | 卡死：Trap **890,286** 行 |
| r05_win_triggered | grdumpwin 40 46 | L1@30 | 50 | 卡死：Trap 304,558 行 |
| r06_win_control | grdumpwin 40 46 | 无输入 | 50 | **无异常** |
| r07_pcring_l1 | grpcring 262144 | L1@30 | 48 | 卡死（exectrace 尾部 = 陷阱环） |
| r08_baseiso_l1 | **未修基底 ISO** | L1@30 | 60 | 卡死：Trap **890,286** 行（与 r03 逐位一致） |
| r09_hook_jump | grhook×3 | L1@30 | 46 | 卡死；证明 `0x0042B350` 是**正常热函数**（12,666 次命中，从第 1 帧起） |
| r10_origdisc_l1 | **GB 英文原盘** | L1@30 | 60 | 卡死：Trap **890,286** 行（同上） |
| r11_watch_lowram | grwatch×2 | L1@30 | 46 | 卡死；**抓到覆写现场** |

> 注：r01 的 4.18 GB `emulog.txt` 因磁盘保护已删除，保留 `emulog_head.txt`（崩前 413 行全文）、`emulog_trigger.txt`（崩前 300 行 + 之后 120 行）、`emulog_prefix8mb.gz`（原始前 8 MB 压缩）。

### 2.4 复现判据（任务书给的判据）

- `Trap exception`：**命中**（r01/r03/r05/r07/r08/r09/r10/r11 都是）。
- `TLB Miss`（PC 族 `0x101d10…0x102584`）：**本机未出现**（0 行）。差异原因见 §5。

---

## 3. 现场证据（第三步）

### 3.1 时间线（都是 emulog 原始行，帧号由快照/输入日志钉住）

```
[1.9128] GR: EE/IOP memory available              ← 存档已载入，开始计帧
[2.8944] GR: input frame 30: bind 10 = 1.0        ← 第 30 帧：按下 L1
[3.2680] GR: input frame 42: bind 10 = 0.0        ← 第 42 帧：松开
[3.3604] Unknown R5900 Standard: EFD7080E         ← 第 44~45 帧之间：低端内存已被写坏，EE 开始当代码执行
[3.3605] EE: Unrecognized op 740090d5
[3.3606] Unknown R5900 SPECIAL: 009000FD
[3.3606] EE: Unrecognized op e0809870
[3.3606] EE: Unrecognized op ca36d721
[3.3606] EE: Unrecognized op 9000fd
[3.3606] EE: Unrecognized op f390a100
...（随后）Trap exception at 0x80000274  ×890,286（60 帧内）
```

PC 采样（`pcsample.txt`，每 4 帧一行；r05）：`40 → 00452498`、`44 → 0042B350`、`48 → 80000180`（通用异常向量）、`52 → 800001f8`、`56 → 80000180`。
对照 r06（不按键）：`40 → 004524CC`、`44 → 0046B840`、`48 → 00411FB0` —— 一直在正常游戏代码里。

`0x80000274` = 物理 `0x00000274`，正是**异常向量区** 0x0..0x280 之内（如下）；`Trap` 是 EE 在该处执行到 TRAP 指令，异常入口本身也被写坏，于是永久自陷。

### 3.2 内存取证 A：分配器/live 结构区（`-grmemwatch`，VA `0x0055B000` + 8 KB，逐帧）

（脚本 `tools\analyze_memwatch.py`，输出 `memwatch_diff_control_vs_l1.txt`；对照 = r02，触发 = r03）

- 控制组（259 帧）与触发组（59 帧）共 59 帧可比：**76 个字节不同**，**第一次分歧 = 第 44 帧**（1 帧不差地卡在崩帧上）。
- "哪个字段被写成什么"，直接从第 43/44/45 帧的 EE RAM 快照读出 32 位字（小端，已逐个核对原始字节）：

| VA | 第 43 帧 control / triggered | 第 44 帧 control / triggered | 第 45 帧 control / triggered |
|---|---|---|---|
| `0x0055B7A0` | `0x00F229F9FE` / 同 | `0x00F229F9F2` / `0x00F229F9FE` | `0x00F229F9FE` / `0x00F229FDFE` |
| `0x0055B7B0`（+`B4` 成对同值） | `0x000055B7A0` / 同 | **`0x0000B4F710`** / `0x000055B7A0` | `0x000055B7A0` / **`0x0000010020`** |
| `0x0055B7C8` | `0x00007A3D00` / 同 | `0x012991B0` / `0x007A3D00` | `0x007A3D00` / `0x007A3D00` |
| `0x0055B7D8` | `0x0000686C70` / 同 | `0x000055B7C8` / `0x00B64C00` | `0x0000686C70` / `0x00B64C00` |
| `0x0055B7E8` | `0x00013DA970` / 同 | `0x000055B7D8` / `0x00013DA970` | `0x00013DA970` / 同 |
| `0x0055B818` | `0x0000B712B0` / 同 | `0x000055B808` / `0x0000B712B0` | `0x0000B712B0` / 同 |

  - `0x0055B7B0`/`B4` 是一对**同值的链表头尾指针**（`+0x10/+0x14` 成对出现），维护它的正是 block `0x00101E1C/0x00102220/0x00102274/0x001024E8`（见 §3.4）。
  - 关键异常值：**触发组第 45 帧这对指针变成 `0x0000010020`**（= 64 KB + 0x20 的**低端地址**，与 §3.3-B 里被覆写的 `0x1000..0x4000` 同一"低端内存"类），对照同帧仍是 `0x000055B7A0`。⇒ 指针字段退化成低端地址，与低端内存被字节流覆写是**同一帧、同一类**的现象。
  - 第 43 帧两 run 完全一致（`0x0055B7A0` 起的 8 个字逐位相同），第 44 帧起分叉 ⇒ 分叉点被钉在**第 44 帧**。
- 触发组的字节变动在**第 45 帧后完全停止**（游戏已死），对照继续每 2 帧变动（第 44/56/72/84/86/88/104/105/232…帧）。

### 3.3 内存取证 B：整块 EE RAM 逐字节差分

（`tools\analyze_ramdiff.py`、`tools\diff_two_dumps.py`；输出 `ramdiff_control_vs_l1.txt`、`r05_win_triggered\f44_to_f45_ramdiff.txt`）

**A. 对照 vs 触发（同一帧快照，各 33,554,432 B）**

| 帧 | 不同字节 | 说明 |
|---|---|---|
| 40 | 58 | 只是"按了 L1 之后游戏正常反应"的少量状态位（`0x0064B840`、`0x00001130`、`0x000193C0`、`0x0129BFE8`、`0x012E76C8` 等） |
| 41 | 44 | 同上 |
| 42 | 44 | 同上 |
| 43 | 43 | 同上 |
| **44** | **15,911** | 差异**爆炸**，集中在 `0x014ACC00..0x014AF900`（堆区） |

**B. 触发组内部 第 44 帧 → 第 45 帧（同一 run，无对照偏差）**

- 共 **55,359 B** 被写；其中：
  - `0x00001000..0x00004000`（BIOS 低端内存/异常向量区）：**7,407 B**
  - `0x00000000..0x00000300`：**614 B** —— 原本是 `"BASLUS-20613GHOST002"`（EE 低位启动数据）与 `0x2000` 处的 MIPS 代码（`3C018002 00230821 AC2495E4 03E00008` …），崩后全部变成垃圾字节
- 这就是"**异常向量被写坏 → 执行到垃圾 → 自陷死循环**"的直接因果链。

**C. 垃圾指令落在哪（`tools\find_opcodes.py`，`unrecognized_op_locations.txt`）**

把 emulog 里打印的 `EE: Unrecognized op` 字按小端在各帧 RAM 快照里搜索，结果**只在第 45、46 帧命中，全部落在 `0x0000001C..0x0000027C`**（异常向量区）：

```
EFD7080E @ 0x000001A8    740090D5 @ 0x00000188    EFD36F0A @ 0x000001BC
C19095A1 @ 0x000001B4    4EE51400 @ 0x0000027C    F390A100 @ 0x00000270
009000FD @ 0x00000268    CA36D721 @ 0x00000264    47009051 @ 0x00000234
E0809870 @ 0x00000208
```

对照 run（r06）第 45/46 帧**一个都没有** → 该垃圾是**触发后才写进去的**，不是存档自带。

### 3.4 写监视（`-grwatch`）—— 抓到"第一条写到被毁区域的 store" ✓

r11：`-grwatch 4864 256`（= `0x00001300`，256 B；该块在第 40..44 帧之间完全静止，却在 44→45 帧被改 244 B）与 `-grwatch 5617584 8`（= `0x0055B7B0`）。

`watch.txt` 命中（每条含 frame / cycle / writer_block / old / new）：

```
hit 1  frame=0  cycle=64816608016 addr=00001300 ...（首次播种，属伪命中）
hit 2  frame=44 cycle=65030627374 addr=00001300 size=256 writer_block=005391BC cur_block=005391DC
       old=00801A3C...  new=53801A3C...          ← 0x00001300: 00 -> 53
hit 3  frame=44 cycle=65030627697 writer_block=005391BC  0x00001301: 80 -> FB
hit 4  frame=44 cycle=65030627880 writer_block=004039BC  0x00001302: 1A -> 00
hit 5  frame=44 cycle=65030628083 writer_block=004039BC  0x00001303: 3C -> 90
hit 6  frame=44 cycle=65030628354 writer_block=004039BC  0x00001304: 00 -> A1
...（hit 7 … hit 64 全部 frame=44）
```

- **64/64 次命中全部在第 44 帧**，cycle 区间 `65030627374..65030638384`（**11,010 个 EE cycle ≈ 5.5 µs**），即一次紧凑的字节流覆写。
- 写者只有两个 block：**`0x005391BC`**（cur `0x005391DC`）与 **`0x004039BC`**（cur `0x004039D8`），交替出现 —— 典型"逐字节写目标缓冲区"的循环。
- 第一个被写坏的字节：**frame 44 / cycle 65030627374 / writer block `0x005391BC` / `0x00001300: 00 → 53`**。
- `0x0055B7B0`（分配器/链表字段）的维护者被同一工具点名：block **`0x00101E1C`、`0x00102220`、`0x00102274`、`0x001024E8`**（另有 `0x00101D10/0x00101DA0/0x00101DE4/0x00101E00/0x00101E08` 出现在上下文环里）。

### 3.5 对照实验（第四步）

| 实验 | 结果 | 说明 |
|---|---|---|
| 同存档 **不按任何键**（r02/r06） | **不复现**（260 帧 / 50 帧全干净） | ⇒ L1 是**必要条件**，不是时间驱动的自发崩 |
| 同存档 + L1，**未修基底** `GR_REBUILD2400.iso`（sha256 `D7F83D7E…443CA0`） | **完全一样地复现**（Trap 890,286 行，PC 序列 `40→00452498 44→0042B350 48→80000180` 逐项一致） | 原因见下 |
| 同存档 + L1，**GB 英文原盘** `third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso`（sha256 `2B42EA7CE9BD0A85972A07CA59B1B9D79422ED318B85737DB3CFD17DAA788531`） | **完全一样地复现**（同上，逐项一致） | 同上 |
| 同存档同输入重复跑（r03/r05/r08/r10） | 逐位一致（Trap 行数 890,286 完全相同） | 该构筑在此配置下**完全确定性**，可用作后续 A/B |

**为什么换 ISO 没区别（重要，勿误读）**：我们把存档里的 `eeMemory.bin` 解出来核对过补丁点 —— 恢复后的 EE RAM 在 `VA 0x0021AC40` 处是 `10 00 00 04`（小端 `0x10000004` = 补丁后的 `beq $zero,$zero,+4`），而不是原始 `0x10400004`。**存档自带补丁后的代码与全部运行时数据**，所以"载入存档后的执行"与从哪张盘启动无关。⇒ 想验证"汉化数据相关"，不能靠换盘 + 同一存档；需要从**未修盘新启动**走到同一现场（见 §6）。

---

## 4. 结论与根因假设

已被证据钉住的部分：

1. 该存档 + 第 30 帧按 L1 ⇒ 第 44 帧起，游戏自身代码（block `0x005391BC`、`0x004039BC`）以字节流方式把垃圾写进 **EE RAM `0x1000..0x4000`**（含 `0x0..0x300` 的异常向量/引导数据），共 7,407 B（低端 614 B）。
2. 第 45 帧 EE 取指进入被写坏的 `0x1C..0x27C`，打印 `Unknown R5900 Standard` / `EE: Unrecognized op`，异常入口 `0x80000180` 同样是垃圾，最终在 `0x80000274` 反复 `Trap exception` ⇒ **死机**。
3. 同一帧（44），由 `0x00101xxx–0x001026xx` 模块维护的链表指针表（`0x0055B7A0` 起，`0x0055B7B0`/`B4` 是一对同值头尾指针）与对照分叉；第 45 帧这对指针退化成低端地址 `0x0000010020`（对照为 `0x000055B7A0`）。
4. 用户现场是**同一个模块**在报错：他们的 `TLB Miss` PC 族 `0x101d10 / 0x101dd8 / 0x101de4 / 0x101e08 / 0x101e34 / 0x101e6c / 0x101fe0 / 0x102000 / 0x102008 / 0x1024d0 / 0x1024e8 / 0x102584` 与我们写监视点名的 `0x00101D10…0x001024E8` 是**同一段代码**；且他们的失败动作是 **store 到 `0x14` / `0x10`** —— 恰好是本次被抓到被覆写的**同一条低端内存**（`0x0..0x300`）。

⇒ **根因假设（高置信）**：汉化补丁改变了 `StringWidth` 的字节长度早退路径后，在"按 L1（切换/使用武器，触发 UI/字符串渲染）"这条路径上，`0x00101xxx` 这段字符串/列表管理代码拿着一个**错误的指针**去做写操作；该指针指向 EE RAM 低端（`0x0..0x4000`，即"NULL + 小偏移"形态）。在本机（低页可写）它**成功写坏异常向量 → 自陷死循环**；在用户机上同一写动作**打在未映射页上 → TLB Miss 死循环**。两者是同一处错误写、两种表现。

**尚未证明**（不要当成已确认）：上游"错误指针从哪来"没有定位；没有反汇编 `0x005391BC / 0x004039BC` 找到那条 store 指令；不能排除"低端覆写"是 DMA 而非 EE store（`-grwatch` 的归属是"强提示"，工具源码自己这么写）。

---

## 5. 未达成项 / 与任务的差异（如实）

1. **未复现 `TLB Miss` 形态**：本机 8 个 run 里 `TLB Miss` 命中 0 次；复现出来的形态是 `EE: Unrecognized op` + `Trap exception`（任务书判据里"或 `Trap exception`"成立）。差异的候选原因：本构筑/本机把 `0x0..0x4000` 视为可写（无 TLB 缺失），于是同一错误写"成功"落地 → 走的是另一条死亡路径。
2. **未做"不按 L1 的 TLB Miss 对照"**（无从做：用户那份日志是唯一来源）。
3. **`-grwatch` 只保住 64 条命中/区域**，`0x0055B7B0` 的 64 条在第 8 帧就用完，**没能抓到第 44 帧改写它的 block**；抓到的是低端 `0x1300` 的 64 条（恰好在第 44 帧，等于"抓到了第一条写坏低端内存的 store"）。
4. **没定位到"第一条写到分配器元数据的 store"**（任务书第 3.3 条原文）：抓到的是**第一条写到被毁内存区的 store**（低端）；分配器字段那条被命中上限挡掉。
5. `-grmemwatch` **在本构筑必须用十进制地址**（`0x...` 会被解析成 0 后静默丢弃，错误信息在日志文件打开前就丢了）—— r01 因此白跑一次 memwatch；已在本文与脚本里写死。
6. `-grpcring` 尾部 512 条全是陷阱环（`0x80000180/0x800001AC/0x800001F8`），没能保留到"跳转前"的游戏 block（`WriteExecTrace` 只写 512 条且 `reclut_crash.txt` 只在 `recLUT` 类错误时生成；本次不是该类）。
7. 未使用 `work\builds\GR_HOOKEMU` 的钩子 Qt 版（本次既有无头构筑已能载入用户存档，备选方案未启用；那套构建仍在被别人使用，全程零干扰）。
8. 未确认用户机上 `0x14/0x10` 的 `TLB Miss` 与"低端可写性"配置差异的确切机理（PCSX2 VTLB 行为），只给出"同一目标地址区"的事实关联。

---

## 6. 建议下一步（按性价比）

1. **反汇编 block `0x005391BC`、`0x004039BC` 与调用链**（ISO 的 ELF 在手，`base_elf_lba=295`）：找 `sb/sw` 那条指令与它用的目标寄存器 ⇒ 目的指针从哪来。顺带反汇编 `0x00101E1C / 0x00102274 / 0x001024E8`（维护 `0x0055B7B0` 的那段）。
2. **`-grhook 0x005391BC`（十进制 `5480892`）+ `-grhook 0x004039BC`（`4213180`）**：hooklog 会给每次进入时的 `a0..a3/v0/s0/s1/ra/sp` ⇒ 直接拿到源/目的指针与调用者。R11 已证明 hook 机制可用。
3. 用 `-grdumpwin 43 45`（更窄）+ `-grwatch` 小区域（例如 `0x55B7A0` 只 4 字节、或 `0x55B7B0` 的**单个字的一半**）把"分配器字段第一条写"的 block 抓全。
4. 走"**X 切火箭弹 → R1 发射**"那条用户给的复现路径（本报告只跑了 L1 路径）：`30 cross press` + `90 r1 press`（cross/R1 名字取自 DS2 bind 表，bind 名 `Cross`/`R1`）。用于确认是否同一处错误写。
5. 让用户按同一份存档、**不按 L1 但等待 >1.2 s** 再确认一次"不按键不死"，用来交叉验证本机的"L1 必要条件"结论。
6. 若需复现 `TLB Miss` 形态：尝试 `-grsetting EmuCore ...` 或换 BIOS/关闭 fastmem 的构筑，使低页写触发 TLB 缺失路径；或用钩子 Qt 版在真实配置下跑同一存档。

---

## 7. 证据清单（全部落在 `work\builds\GR_REPRO\**`）

| 路径 | 内容 |
|---|---|
| `common\state_LAY_fix1_bytecount.p2s` | 用户存档只读副本（sha256 见 §1） |
| `common\user_emulog_2026-10-17_203556.txt` | 用户 emulog 只读副本（含 `TLB Miss` 原始签名） |
| `common\LAY_fix1_bytecount.meta.json` | 构筑元数据（补丁点/elf 偏移） |
| `r01_l1\emulog_head.txt` / `emulog_trigger.txt` / `emulog_prefix8mb.gz` | 首次复现的崩前全文 + 崩点上下文（原始 4.18 GB 日志因磁盘保护删除） |
| `r01_l1\cmdline.txt`、`in_l1_f30.txt`、`snap_f*.png` | 命令、输入表、逐 30 帧截图 |
| `r02_control\` / `r06_win_control\` | 对照（不按键）：无异常、`pcsample.txt`、`memwatch.bin`、`win_f*_eeram.bin` |
| `r03_l1_memwatch\` | 触发 + 分配器区 memwatch（890,286 Trap 行） |
| `r05_win_triggered\` | 触发 + 第 40..46 帧逐帧 EE RAM（`win_f*_eeram.bin`）+ `f44_to_f45_ramdiff.txt` |
| `r07_pcring_l1\exectrace_tail.txt` | 执行块环尾部（= 陷阱环） |
| `r08_baseiso_l1\` / `r10_origdisc_l1\` | 未修基底 / GB 原盘 对照（同样复现） |
| `r09_hook_jump\hooklog.txt` | `0x0042B350` 等 PC 的进入现场（证明它是正常热函数） |
| `r11_watch_lowram\watch.txt` | **写监视原始命中（frame 44, writer `0x005391BC`/`0x004039BC`）** |
| `memwatch_diff_control_vs_l1.txt`、`unrecognized_op_locations.txt`、`ramdiff_control_vs_l1.txt` | 三份差分/定位报告 |
| `docs\REPORT_SAVESTATE_REPRO.md` | 本报告（`docs\` 下，唯一的文档产出） |
| `tools\*.py`、`tools\extract_head.ps1` | 全部分析脚本（可重跑） |
| `emu\gsrunner\` | 无头构筑的工作副本（避免写 `third_party\**`） |

用户文件（`%LOCALAPPDATA%\PCSX2\**`、`Documents\PCSX2\**`、`third_party\**`、所有 ISO）**全程只读**：本次只做 `Copy-Item` 出去，未写入、未改动、未删除任何用户/仓库既有文件。
