# REPORT_SPINFIX —— 分配器内部自旋：本机复现、四处修复、四张盘与验证

> ⚠ **历史错误断言订正（2026-10-18 收尾轮）**：本文含已被实测/实机否证的表述 —— 见 `docs/CORRECTIONS.md` §7。
> 原文保留作过程记录；**结论冲突时以 `docs/CORRECTIONS.md` + `docs/STATUS.md` 为准**。

* 轮次：GR_SPINFIX（2026-10-18，Asia/Hong_Kong）
* 输入（**直接采用，不重查**）：`docs\REPORT_USERDUMP_ANALYSIS.md`（用户双 dump 定案：桶 126 是分配器自己写坏的；卡死 = malloc 在桶链里自旋）、
  `docs\REPORT_HEAP_EXHAUSTION.md`（堆结构 / 桶自指公式）、`docs\REPORT_OOMFIX.md`（"只改 ISO 在读旧存档时不生效"）
* 产物：`work\builds\GR_SPINFIX\**`（**4 张修复盘** + 3 个坏桶存档变体 + 4 个补丁存档 + 全部 run/日志/工具 + `hook_config_next.ini`）、本报告、`docs\HOOKEMU_QT2_GUIDE.md` §8 追加
* 只读：所有既有 ISO / 产物 / `third_party\**` / 用户 PCSX2 目录（只 `open(...,'rb')` 与 `Copy-Item` 出去）
* 未 commit / 未切分支 / 未 merge；**全程未使用 `Select-Object -First N`**

---

## 0. 结论速览（TL;DR）

| 问题 | 答案 |
|---|---|
| 坏桶存档造出来了吗 | **造出来了**。最小注入 = 只改 8 字节（`0x0055BB98/9C = 0x6ED47823`，用户真机新 dump 的原值），见 §2.3 |
| 复现了用户的自旋吗 | **部分复现（如实）**：用户链条的**前两条 TLB Miss 逐条对上**（`pc=0x1024CC addr=0x6ED4782B` / `pc=0x102584 addr=0x6ED47837`），但**没有**变成"无限自旋"——本机环境里紧接着的 `ld 8(0)` **不再 TLB Miss**（低端页在该会话里是被映射的），循环于是退出、退化成与未注入时**完全相同**的那条老链（解压器写低端 → `Trap at 0x80000274`，Trap 行数 2,647,472 分毫不差）。见 §2.4/§7 未达成项 1 |
| 为什么同一份"坏桶存档"以前不自旋 | **本轮新发现**：存档自带的坏值 `0xA73D37F0` 落在 EE **KSEG1**（`0xA0000000-0xBFFFFFFF`）⇒ 访存按 `addr & 0x1FFFFFFF` 折算进 RAM，**不 TLB Miss**；用户的 `0x6ED47823` 是**未映射 KUSEG** ⇒ TLB Miss ⇒ 读回 0 ⇒ 自旋。hook 实测证明桶 126 **确实被走到**（帧 44 在 `0x1024CC` 读到的就是 `A73D37F0`） |
| 出的盘 | `SPINFIX_F4.iso`（首选，最小）、`SPINFIX_F1F2.iso`（治因）、`SPINFIX_F4_2400.iso`（产品线）、`SPINFIX_F1F2_F4.iso`（组合）——4 张，全部 8 项自证 OK，见 §3 |
| 修好了吗 | **F4：修好了（本机能给出的最强证据）**。坏桶现场：Trap 2,647,472 → **0**，TLB Miss **2 → 2**（F4 在两条读之后，所以那两条仍在），帧数 90 → **300 继续跑**，解压器调用 2 → **14 次**，F4 cave 命中 1 次。见 §4.1 |
| F1F2 呢 | **消不掉已存在的坏桶**（Trap 2,647,471，与未修一致）——它只管"别再写坏"，不管"已经坏了"；而且 6000 帧冒烟里 F1F2 有 **6 帧**与基底不同（像素级确有差异，最大 38/255，仅帧 660..810）。见 §4.1/§4.2 |
| 要不要组合 | **要**：`SPINFIX_F1F2_F4.iso` = 消卡死 + 防再写坏；本期优先给用户的是 `SPINFIX_F4.iso`（干净、0 差异帧） |
| 给用户的下一步 | 见 §6：**先跑 `SPINFIX_F4.iso`**（把状态文件按新 CRC 改名，否则读档读不到），玩到原来卡死处按 L1 |

---

## 1. 纪律 / 素材 / 污染记录

* **模拟器独占**：全程轮询 `Get-Process pcsx2*`。期间**用户自己的 `pcsx2-qt.exe`（pid 45040，起于 2026-10-18 10:45:30）一直在跑**（11:21 时 CPU 280 s、11:35 时 283 s ⇒ 处于暂停/空闲）。按纪律**只等不杀**，每个 run 目录里落 `OTHERS_RUNNING.txt` 记录污染。
  * 该污染只影响**运行墙钟**，不影响结果：本机模拟器**逐帧确定**——同盘两跑 191/191 帧 sha256 完全相同（§4.2 的决定性对照），基底两跑 191/191 完全相同。
* 写入只落在 `work\builds\GR_SPINFIX\**`、`docs\REPORT_SPINFIX.md`、`docs\HOOKEMU_QT2_GUIDE.md`（追加）。
* 中间物清理：污染现场的 `emulog.txt`（未修盘跑 90 帧 = **111 MB**）在统计后即裁剪成 `emulog_sample.txt`（前 3000 + 后 200 行）并删原日志；`d1/d2` 诊断 run 已删。
* 磁盘：开工前 `Get-PSDrive C` 余 **19.3 GB**；4 张盘 6.15 GB（`GR_SPINFIX` 整个目录 7.43 GB）；中间物清理回收 2.63 GB；**结束时余 11.7 GB**（明细见 §9）。
* **模拟器副本**：`work\builds\GR_SPINFIX\emu\gsrunner\pcsx2-gsrunner.exe`，sha256 = `E58253069BEE248FA46ACF56873540D096BB3B816F0A3B40783BFA3074813EE6`（与 `REPORT_OOMFIX.md` 记录一致）。
* **`git status --porcelain` 事后核对**：本轮新增的受版本控制文件只有 `?? docs/REPORT_SPINFIX.md`；`docs\HOOKEMU_QT2_GUIDE.md` 本身是未跟踪文件（已在其 §8 追加）。
  工作树里另有 4 个 `M`（`tools/diag/dump_all_text.py`、`tools/font_pipeline/data/charset_compiled_zh16.json`、`tools/text_csv/inject_text_csv.py`、`tools/text_csv/tcslib.py`，mtime 2026-10-15）与 **270 条 `D work/builds/**`（GR_TEST_FONT* / GR_ZH9x / GR_TEST_PROBE_LEAD 下的 temp 快照与 csv）**——**都不是本轮改动**：
  本轮删除的 791 个文件**全部**在 `work\builds\GR_SPINFIX\runs\**` 之下（实测：270 条 `D` 里属于 `work/builds/GR_SPINFIX/` 的有 **0** 条）。

---

## 2. A. 坏桶存档 + 自旋复现

### 2.1 输入核对（`tools\probe_inputs.py` → `out\probe_inputs.txt/.json`）

| 素材 | sha256 | 桶 126（`0x0055BB98/9C`） | 判定 |
|---|---|---|---|
| 用户新 dump `hook_23444_hotkey_f10\ee_ram.bin` | `758a4f64…b965` | `0x6ED47823 / 0x6ED47823` | 坏（用户真机现场） |
| 用户旧 dump `hook_19701_hotkey_f10\ee_ram.bin` | `a6948e31…9223` | `0x0055BB88 / 0x0055BB88` | 健康（空桶自指） |
| 可用存档 `GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s` | `34939abd…75f3` | **`0xA73D37F0 / 0xA73D37F0`** | **★ 存档自带坏桶**（与 `GR_OOMFIX\common\state_LAY_fix1_bytecount.p2s` 逐字节相同） |
| 基底 `GR_LAYOUT\LAY_fix1_bytecount.iso` | `a69a9ca4…2808` | — | ELF sha256 `0a986bb3…87b9`，CRC **7A761FCA** |
| 基底 `GR_REBUILD\GR_REBUILD2400.iso` | `d7f83d7e…3ca0` | — | ELF sha256 `5cb59175…f47d8`，CRC 7A361FCA |

9 个站点字（F1/F1b/F2a/F2b/F4/F5a/F5b/F6a/F6b）在两个基底上**逐个核对相符**（ISO 偏移 = VA−0x6C780、ELF 偏移 = VA−0xFFF80）。

### 2.2 ★ 关键发现：同一个坏桶，为什么只有用户真机会自旋

* 存档/上一轮现场里的坏值 **`0xA73D37F0` 落在 EE KSEG1**（`0xA0000000-0xBFFFFFFF`）：EE 对 KSEG1 的访存不做 TLB 查表，而是把地址 `& 0x1FFFFFFF` 直接当物理地址 ⇒ `0xA73D37F8 → RAM 0x073D37F8`，**不 TLB Miss**，只是读到一块无关的 RAM 垃圾 ⇒ malloc 一路走下去最后**返回 0（NULL）**，于是踩上 `REPORT_OOMFIX.md` 那条老链（解压器把输出写到地址 0 → 覆盖异常向量 → `Trap 0x80000274`）。
* 用户真机的坏值 **`0x6ED47823` 落在未映射 KUSEG** ⇒ **TLB Miss**，PCSX2 的 miss 处理让目标寄存器读到 0 ⇒ `v0=0` ⇒ `0x1024D0 ld 8(0)` / `0x102584 lw 0x14(0)` 无限交替 = **卡死**。
* **直接证据**（`runs\d4_scan`，未修盘 + 原存档 + L1@30，hook `0x102050/0x102420/0x102498/0x1024CC`）：
  ```
  hook pc=00102050 f44 c=65029607104  a1=00010020                 <- malloc(nb=0x10020)
  hook pc=001021E4 f44 c=65029607131  a3=0055BB60 v0=0055BB60      <- 请求自己的桶 121 是空的
  hook pc=0010229C f44 c=65029607152  v0=00B722D0                  <- unsorted 桶 1 里有一块，且放不下
  hook pc=00102420 f44 c=65029607184  v0=00B722D0                  <- 进 binmap 扫描
  hook pc=00102498 f44 c=65029607257  v0=80000000                  <- 从桶 124 起扫
  hook pc=001024CC f44 c=65029607286  v0=A73D37F0                  <- ★ 走到了桶 126，读到的就是坏值
  hook pc=0010269C f44 c=65029607343  v0=00000000                  <- 因为 KSEG1 折算成有效 RAM，走完返回 NULL
  ```
  ⇒ **桶 126 一定会被这条 malloc 走到**；区别只在"那个坏值读起来是 TLB Miss 还是别名到 RAM"。

### 2.3 三个存档变体（`tools\spinfix_state.py` → `states\states.meta.json`）

| 变体 | 做法 | 与基底差异 | sha256 | 用途 |
|---|---|---|---|---|
| `S3_base.p2s` | 原样复制 | 0 B | `9e5a8369…4697a` | 健康对照 |
| **`S1_bin126_user.p2s`** | **只改 8 字节**：`0x0055BB98/9C = 0x6ED47823` | **8 B**（`0x0055BB98..0x0055BBA0`） | `b0cc0cda…1f94b` | ★ 复现用（"分配器相关内存的最小注入"） |
| `S2_win500_580.p2s` | 把用户新 dump 的 `0x00500000..0x00580000`（512 KB）整段覆盖（任务书字面要求） | 457 B / 93 段 | `ed834ca7…1a87` | 字面变体（结果见 §2.4） |

做过的自证：`oomfix_zstd.rewrite` 的 16 个 zip 条目回读逐字节一致；每个注入点独立回读；32 MB 尺寸；与基底逐字节 diff 统计。

> 为什么**不**整块 32 MB 覆盖：`eeMemory.bin` 里除了分配器还有 PC/栈/GPU 状态，整块换掉等于换了一个游戏进度，不叫"同现场"。而 512 KB 窗口里装的是**另一场景**的 `top=0x01A47BB0` 与整套桶指针（基底是 `top=0x01B0ED20`），注入进去会破坏自洽。

### 2.4 A 现场实验（未修盘 `LAY_fix1_bytecount.iso`，输入 = `-grinput` 第 30 帧按 L1，90 帧）

| run | 存档 | TLB Miss | Trap | 帧数 | 备注 |
|---|---|---|---|---|---|
| `a1_base_stock_state` | `S3_base` | **0** | 2,647,472 | 90 | 基线：malloc 返回 NULL → 解压器写低端 → Trap |
| **`a2_bad_bin126`** | `S1_bin126_user` | **2** | 2,647,472 | 90 | ★ 两条 miss 与用户日志**逐条同址同 PC**；但**未自旋** |
| `a3_win500_580` | `S2_win500_580` | 0 | **0** | 90 | 整段注入破坏自洽：L1 触发的那次解压分配**根本没发生**（hook `0x539110` 0 次、`0x102050` 只有 6 次）⇒ 这条路不能用来复现 |

`a2` 的日志摘录（`runs\a2_bad_bin126\emulog_sample.txt`）：

```
[    2.7177] GR: needle 'newfontrevisedrs' hit #22 in ee at offset 0x005A7630 (frame 44)
[    2.7180] GR: needle 'WPNRPK74' hit #22 in ee at offset 0x0057F1C8 (frame 44)
[    2.7266] TLB Miss, pc=0x1024cc addr=0x6ed4782b [load]     <- ★ 用户链条第 1 条（桶 126 坏值 +8）
[    2.7267] TLB Miss, pc=0x102584 addr=0x6ed47837 [load]     <- ★ 用户链条第 2 条（坏值 +0x14）
[    2.7283] Unknown R5900 Standard: EFD7080E                  <- 之后是"解压器写低端"那条老链
[    2.7284] Trap exception at 0x80000274
```
用户真机（`REPORT_USERDUMP_ANALYSIS` §4）：
```
[  427.4814] TLB Miss, pc=0x1024d0 addr=0x6ed4782b [load]
[  427.4816] TLB Miss, pc=0x102584 addr=0x6ed47837 [load]
[  427.4816] TLB Miss, pc=0x1024d0 addr=0x8 [load]      <- 本机没有第 3 条
[  427.4817] TLB Miss, pc=0x102584 addr=0x14 [load]
```

**判定（如实）**：
1. **"坏桶 + 用户坏值"确实让分配器踩到越界链 —— 已复现**（两条 miss 的地址、PC、顺序完全一致；hook 另证桶 126 被走到）。
2. **"无限自旋"未复现**：本机该会话里低端页（`0x0/0x8/0x14`）是**被映射的**，`ld 8(0)` 不 miss，循环于是退出；`v0` 归 0 之后 malloc 走完返回（0 或垃圾），退化成与 `a1` **Trap 行数完全相同**的老链。
   * 差的这一个条件是"**低端页未映射**"（用户 Qt 版当次会话如此），它由客户机自己的 TLB 装载决定，我没有可用的开关去强制。
   * 因此：**修复的验证强度 = 静态证明 + "坏值被读到的现场" + 失败形态对照（Trap 2.6 M → 0）+ 冒烟不回归**，见 §4；而不是"把无限自旋按下去"。缺什么写在 §7。

---

## 3. B. 四张修复盘（`work\builds\GR_SPINFIX\`）

### 3.1 修复设计

| 站 | VA | 原字（反汇编） | 新字 | 语义 |
|---|---|---|---|---|
| **F1** | `0x00101DC0` | `00AA2823 subu $a1,$a1,$t2` | `08156DCC j 0x0055B730` | cave 内重算 `P = C − (int32)C->prev_foot`，校验 **`mstate < P < C` 且 `P%8==0`**；不合法 → `j 0x101DE4`（= **原有的"前块在用、不合并"出口**，语义自洽：只是少合并一块，不会野写） |
| **F2** | `0x00101D38` | `DCC90008 ld $t1,8($a2)` | `08177B31 j 0x005DECC4` | cave 内校验 `a2 = C+size` 满足 **`C < a2 < 32MB`**；不合法 → `j 0x102018`（= **free() 直接返回**：放弃这次 free 只会泄漏一块；next 块的 PREV_INUSE 保持 1 仍然为真，堆账目自洽） |
| **F4** | `0x00102588` | `1459FFD1 bne $v0,$t9,-47` | `081068D7 j 0x0041A35C` | cave 内校验链头 **`t9 < v0 < 0x1FFFFFFE`**（严格大于桶哨兵 ⇒ 排除 `v0==t9` 与 `v0==0`）；不合法 → `j 0x102590`（= **既有的"本桶没有可用块、继续找下一个桶"出口**） |

**F1 的关键点**：校验用 `mstate < P < C` 两条 `sltu` 就同时覆盖了"下界（堆基址之上）"和"上界（32 MB 之内）"（因为 `C < heap_end`），再叠一条 8 字节对齐检查。合法时 `a1 = P` 然后 `j 0x101DC4` **回到原指令流**（含原延迟槽），逐条等价；hook 实测（§4.1）显示它在正常路径上"只进不出"。

**F2 的关键点**：站点 `0x101D38` 的**延迟槽 `0x101D3C addiu $t4,$t0,16` 照常执行**（cave 不需要重做它）；合法时 cave 补做 `ld $t1,8($a2)` 再 `j 0x101D40`，与原来逐条等价。

**F4 的关键点**：`0x102588` 那条 `bne` 的原延迟槽是 `nop`，所以站点可以直接换成 `j`；cave 的合法出口 `j 0x1024D0` 就是原 `bne` 的回头路，非法出口 `j 0x102590` 就是原"桶走空"的落点 —— **两个出口都是既有路径**，没有新语义。

> ⚠ **任务书给的 F4 指令 `sltiu $at,$v0,0x02000000` 无法编码**：SLTIU 的立即数只有 16 位（最大 0xFFFF），0x02000000 放不进去。本工程改用
> `sltu $at,$t9,$v0` + `sltu $t3,$v0,$t5`（`t5 = 0x1FFFFFFE` 是 malloc 自己在 `0x1024BC` 设好的 size 掩码，本 cave 只读不改）：
> 上界放宽到 512 MB，但**任何 ≥32 MB 的坏值（含用户的 `0x6ED47823`、上一轮的 `0xA73D37F0`）都被当场拦下**；万一坏值落在 `[32MB,512MB)`，
> 下一轮循环 TLB Miss 后 `v0` 归 0，也会被 `t9 < v0` 拦下 ⇒ **仍然不会自旋**（最多多一次坏迭代）。

### 3.2 cave 落点（三处，均经审计 + 现场核对）

| cave | VA | 长度 | 来源（ELF 里是零） | 为什么安全 |
|---|---|---|---|---|
| `CAVE_F1` | `0x0055B730` | 68 B | 零区 `0x0055B730..0x0055B780` | `spinfix_cave.py` 审计：**无控制转移目标、无 32 位字面量、无 lui 合成地址、无 `.relmain` 落点、无符号覆盖**；另在**8 份现场 RAM 快照**（用户两份 dump + u1 帧 43/44/45/46 + 帧 2 + 存档原像）上**逐字节全零**。⚠ 但它紧邻活跃数据（前后文见 §4.2 的回归分析） |
| `CAVE_F2` | `0x005DECC4` | 44 B | 零区 `0x005DECC4..0x005DED00`（段尾填充） | 同上 8 份快照全零；审计全 0；邻接符号是 `@EX@__sinit_…` 表尾与 `@552` |
| `CAVE_F4` | `0x0041A35C` | 36 B | 零区**正好** 36 B | 同上；位于 iomanX **死代码区**（DBCS cave 0x416E00..0x417800 同一模块），离活跃数据最远 |

**明确避开**：DBCS cave 全区 `0x416E00..0x417800`、4 个闸门 `0x416EE8/0x417160/0x41751C/0x5656A4`、ZH cave block B `0x565600..0x565B00`、
**GR_OOMFIX 已落地 cave `0x00550048..0x00550080`**、分配器镜像 `0x00101C00..0x00102700`、解压器 `0x00539110`、RSFont 区 `0x0021AC00..0x0021AE00`。
（`meta.json` 的 `ref_regions` 对这些区逐字节断言"与基底相同"。）

### 3.3 四张盘

| 盘 | 基底 | 站/cave | ISO sha256 | 尺寸 | CRC(PCSX2) | ELF sha256 | 自证 |
|---|---|---|---|---|---|---|---|
| **`SPINFIX_F4.iso`** | `LAY_fix1_bytecount` | F4 + cave(36 B) | `9704600e5118c2b3bf217b8414fcd8682a2f5b72d875c80029dbdcaee1af34e2` | 1,648,164,864 | **755BD0BA** | `fb60afc4…a6a5` | 8/8 OK |
| `SPINFIX_F1F2.iso` | 同上 | F1+F2 + 2 cave(112 B) | `d22fd26b987bce88e480d60247bbf10eedcfb6847233498524a6abbaafb7eb65` | 同 | **BED57022** | `8e34f26a…d4e9` | 8/8 OK |
| `SPINFIX_F1F2_F4.iso` | 同上 | F1+F2+F4 + 3 cave(148 B) | `46d8a00ca77bc6e1a218c0bb3fc66bbc50380b01bb08f17cd6a92fff668136fc` | 同 | **B1F8BF52** | `3f079171…6b9f` | 8/8 OK |
| `SPINFIX_F4_2400.iso` | `GR_REBUILD2400` | F4 + cave(36 B) | `56302bd6281d2fa0a72b8f92512586644ca5766778858a4f4501b9c1445b8c0f` | 同 | **751BD0BA** | `30558259…48e2` | 8/8 OK |

**8 项自证**（每盘 `meta.json` 内，全部 True）：`size_unchanged` / `diff_only_in_declared_windows` / `every_window_touched` / `readback_all_ok` /
`gates_untouched_4` / `dbcs_zh_oomfix_caves_untouched` / `elf_header_untouched` / `elf_lba_size_unchanged`。
差异统计：F4 = 7 段/25 B，F1F2 = 25 段/74 B，F1F2_F4 = 32 段/99 B（**只统计"非零差异字节"**；cave 里的 `nop` 与基底同为 0，不计）。

出盘命令（逐字）：
```powershell
python work\builds\GR_SPINFIX\tools\spinfix_apply.py --flavor F4      --base-flavor lay1 --out work\builds\GR_SPINFIX\SPINFIX_F4.iso
python work\builds\GR_SPINFIX\tools\spinfix_apply.py --flavor F1F2    --base-flavor lay1 --out work\builds\GR_SPINFIX\SPINFIX_F1F2.iso
python work\builds\GR_SPINFIX\tools\spinfix_apply.py --flavor F1F2_F4 --base-flavor lay1 --out work\builds\GR_SPINFIX\SPINFIX_F1F2_F4.iso
python work\builds\GR_SPINFIX\tools\spinfix_apply.py --flavor F4      --base-flavor 2400 --out work\builds\GR_SPINFIX\SPINFIX_F4_2400.iso
```

### 3.4 ★ 只改 ISO 在读旧存档时不生效（沿用并再次实测）

PCSX2 的 `.p2s` 里 `eeMemory.bin` 是**整块 32 MB EE 主存**。本轮的对照 `b4_iso_only_ctl`（`SPINFIX_F4_2400.iso` + **未打补丁**的存档）：
Trap 仍 2,647,472、hook `0x0041A35C`（F4 cave）**0 次命中** ⇒ 补丁在存档场景里**完全不可见**。
⇒ 所以本轮所有"同现场"验证都把补丁**同时写进存档**（`tools\spinfix_state_fix.py`，从 ISO 的 ELF 里按 `meta.json` 声明窗口逐字节抄进 RAM）：

| 补丁存档 | 注入窗口 | 差异字节 | sha256 |
|---|---|---|---|
| `states\S1_bad_F4.p2s` | F4 站 + cave | 25 B | `68e04a96…c9ea0` |
| `states\S1_bad_F1F2.p2s` | F1/F2 站 + 2 cave | 74 B | `cb0e39ba…58671` |
| `states\S1_bad_F1F2_F4.p2s` | 3 站 + 3 cave | 99 B | `47f5879a…8f1a9` |
| `states\S3_base_F4.p2s` | F4（健康基底） | 25 B | `34e5d79b…78b5d0f` |

---

## 4. C. 验证

### 4.1 失败形态对照（同一坏桶现场 `S1_bin126_user`，L1@30）

| run | 盘 | 存档 | 帧 | **TLB Miss** | **Trap** | 解压器调用 | F4 cave 命中 | 结果 |
|---|---|---|---|---|---|---|---|---|
| `a1` | 未修 | `S3_base`（健康） | 90 | 0 | **2,647,472** | 2 | — | 老链（NULL→写低端→Trap） |
| `a2` | 未修 | `S1`（坏桶） | 90 | **2** | **2,647,472** | 2 | — | 用户链条前两条 miss + 老链 |
| **`b1`** | **F4** | `S1_bad_F4` | 90 | 2 | **0** | **14** | **1** | ★ 卡死链被截断 |
| `b2` | F1F2 | `S1_bad_F1F2` | 90 | 2 | **2,647,471** | 2 | —（F1 cave 90 / F2 cave 1529 次，均合法通过） | **没救**（F1/F2 只防"写坏"，不修"已坏"） |
| **`b3`** | **F1F2_F4** | `S1_bad_F1F2_F4` | 90 | 2 | **0** | 14 | 1 | ★ 组合 |
| `b4` | F4_2400 | `S1`（**未打补丁**） | 90 | 2 | 2,647,472 | 2 | **0** | 只改 ISO 不可见（§3.4） |
| **`b5`** | **F4** | `S1_bad_F4` | **300** | 2 | **0** | — | 1 | ★ **能继续跑**（≥300 帧） |
| **`b6`** | **F4** | `S3_base_F4`（健康） | **300** | **0** | **0** | — | 1 | ★ F4 对"存档自带坏桶 `0xA73D37F0`"这条路也一样救活（对照 `a1` 的 2,647,472） |

关键读数：
* **Trap 行数从 2,647,472 → 0**（`b1/b3/b5`，与未修同配方同帧数）。
* 用户链条的两条 miss 在 F4 盘上**仍然出现**（F4 站在它们之后），但**不再有第 3 条**（不会打转）。
* 解压器调用 **2 → 14 次**：说明 L1 触发的那次 64 KB 分配**成功拿到了真正的块**（malloc 不再消费坏链，回退到 top 切分），资源加载继续。
* `b5` 跑到 **300 帧**正常结束（`=== run end, frames=300 ===`）：**不再"永不返回"**。
* `b6` 说明 F4 对 `0xA73D37F0` 这种"别名型坏值"同样有效（`a1` 会 Trap 2.6 M 行，`b6` 干净）。

### 4.2 6000 帧冷启动冒烟（`tools\capture\nav_menu_only.txt`）+ 逐帧 sha256

| run | 盘 | 截图 | 帧区间 | TLB | Trap | op | 与基底逐帧 sha256 |
|---|---|---|---|---|---|---|---|
| `smoke_SPINFIX_F4` | `SPINFIX_F4.iso` | **191** | 270..5970 | **0** | **0** | 0 | vs `LAY_fix1_bytecount`：共同 191 / **相同 191 / 不同 0** |
| `smoke_LAY_fix1_bytecount` | 基底 | 191 | 270..5970 | 0 | 0 | 0 | — |
| `smoke_SPINFIX_F1F2` | `SPINFIX_F1F2.iso` | **191** | 270..5970 | **0** | **0** | 0 | vs 基底：共同 191 / **相同 185 / 不同 6** ⚠ |
| `smoke_SPINFIX_F1F2_F4` | `SPINFIX_F1F2_F4.iso` | **191** | 270..5970 | **0** | **0** | 0 | vs 基底：共同 191 / **相同 185 / 不同 6** ⚠ |
| `smoke_SPINFIX_F4_2400` | `SPINFIX_F4_2400.iso` | **191** | 270..5970 | **0** | **0** | 0 | vs `GR_REBUILD2400`：共同 191 / **相同 191 / 不同 0** |
| `smoke_GR_REBUILD2400` | 基底 | 191 | 270..5970 | 0 | 0 | 0 | — |

四次 F4 相关跑都到 `=== run end, frames=6000 ===`（单次 102~103 s）；5000 帧判据（≥190 截图 / TLB 0 / Trap 0）**全部满足**。
补丁存活自证（第 5970 帧整块 RAM，`tools\spinfix_ramcheck.py`）：`SPINFIX_F4` / `SPINFIX_F1F2` / `SPINFIX_F1F2_F4` / `SPINFIX_F4_2400`
的**每一个站字与 cave 字都与 ISO 里逐字相同**（冷启动跑到 6000 帧没有被任何东西改写）。

#### ⚠ F1F2 的 6 帧差异（如实报告 + 已做的定性）

* 不同帧：`660, 690, 720, 750, 780, 810`（连续 6 个 30 帧采样点，帧 840 起又完全相同）。
* **不是噪声**：
  * 基底同盘两跑：191/191 相同（0 不同）；
  * F1F2 同盘两跑：191/191 相同（0 不同）；
  * F1F2 第二跑 vs 基底第二跑：**同样是那 6 帧**不同 ⇒ **确定性、由 F1F2 补丁引起**。
* **是真实像素差异**：逐通道比对 `snap_f00000660`：R/G/B 的最大差 38/39/34（0..255），差异像素 ~20k~26k，集中在 `x∈[87,504] y∈[156,297]` 的一块；alpha 相同。（用 `ImageChops.difference` + `getbbox` 会**误报 0 差异**，必须逐通道/比字节，脚本见 `out\pixel_bands.txt`。）
* **不是校验误判**：把 F1 的 `.skip`（`0x0055B76C`）与 F2 的 `.bad`（`0x005DECE8`）当块入口挂钩子，900 帧里 **`hooklog: 0 lines`** ⇒ 两条 cave 在所有被走到的路径上**都判为合法**，走的都是"逐条等价"的那一支。
* **最可能的原因 = cave 落点与活跃数据相邻**：`0x0055B730` 的前 0x50 字节是一段**结构化数据流**（`3C 03 00 80 FF 02 00 00` 反复出现的顶点/GIF 包样式），其后紧跟符号 `s_bCDMode(0x0055B780,+4)`、`act_align(0x0055B788,+6)`、`act_data(0x0055B790,+12)`、`main_arena(0x0055B7A0,+1044)` ⇒ 这块 80 B 零区是**数据缓冲区与数据对象之间的填充**，不是死代码。`0x005DECC4` 的邻居是 `@EX@__sinit_…`（.ctors 表项，+12）与 `@552`。
  * 帧 700 全 RAM 差分：与基底差 **8,016 B / 0.024%**，其中堆内指针相差 `0x708`（例如 `0x01809450` vs `0x01809B58`）⇒ **堆布局确实被推偏了**，属于"合法但不同"的分配序列。
  * 本轮**未做**的隔离实验（缺磁盘额度）：F1-only / F2-only 两张诊断盘，用来判定是哪一个 cave 落点引起。见 §7 未达成项 3。
* **结论**：`SPINFIX_F4.iso` / `SPINFIX_F4_2400.iso` **零差异帧，可直接用**；`SPINFIX_F1F2(.+F4)` 带这条 6 帧的已知瑕疵，**下一轮应把 F1/F2 的 cave 换到真正的死区**（F4 cave 所在的 `0x41A3xx` 那种 iomanX 死代码区；`spinfix_cave.py --min 0x10` 的复扫见 §7 未达成项 3）。

### 4.3 静态论证：新字反汇编回读 + 为什么能截断链

三个 cave 都从**产物再反汇编回读**（`spinfix_apply.py` 输出，与设计逐字相符）：

**F4 — `0x0041A35C`（36 B，9 字）**
```
0041A35C  0322082B  sltu $at, $t9, $v0     ; at = (v0 > 桶哨兵 t9)，严格：v0 == t9（桶走空）也判不合法
0041A360  004D582B  sltu $t3, $v0, $t5     ; t3 = (v0 < 0x1FFFFFFE)，t5 由 malloc 在 0x1024BC 设为 0x1FFFFFFE
0041A364  002B0824  and  $at, $at, $t3
0041A368  10200002  beq  $at, $zero, +2 -> 0x0041A374   ; 不像 RAM 内的块 -> bail
0041A36C  00000000  nop
0041A370  08040934  j    0x001024D0         ; 合法 -> 回原循环体（= 原 bne 的回头路）
0041A374  00000000  nop
0041A378  08040964  j    0x00102590         ; bail -> 既有的「本桶无可用块」出口
0041A37C  00000000  nop
```
**为什么能截断链**：卡死的唯一成因是 `0x102588` 那条"`v0 != t9` 就回头"的无条件回边——回边反复带着一个**不在 RAM 里的链头**回到 `0x1024D0`，而 TLB Miss 把 `v0` 读成 0，于是永远满足回边条件。F4 在**每次回边之前**插入一条"链头必须落在 (桶哨兵, 512MB) 内"的判定：
用户的 `0x6ED47823` 在第一轮就被判不合法 → 直接走 `0x102590`（桶走空）→ **回边不再发生**，malloc 继续找下一个桶 / 回退 top 切分，最终**正常返回**（`b1` 实测：解压器 14 次调用全部拿到块）。即使第一轮侥幸放行（例如值落在 `[32MB,512MB)`），第二轮 `v0` 会被 TLB Miss 读成 0，而 `v0 > t9` 不成立 → 同样 bail ⇒ **自旋最多多一轮**。

**F1 — `0x0055B730`（68 B，17 字）**
```
0055B730  DCA10000  ld     $at, 0($a1)          ; C->prev_foot（64 位）
0055B734  0001503C  dsll32 $t2, $at, 0
0055B738  000A503F  dsra32 $t2, $t2, 0          ; t2 = (int32)prev_foot（与原 0x101DB8/BC 一致）
0055B73C  00AA0823  subu   $at, $a1, $t2        ; at = P（原 0x101DC0 的 subu 搬进来）
0055B740  0081102B  sltu   $v0, $a0, $at        ; v0 = (mstate < P)
0055B744  0025682B  sltu   $t5, $at, $a1        ; t5 = (P < C)
0055B748  004D1024  and    $v0, $v0, $t5        ; 两条合起来 ⇒ P 必然落在 (mstate, C) ⊂ RAM
0055B74C  10400007  beq    $v0, $zero, +7 -> 0x0055B76C   ; 不合法 -> .skip
0055B750  00000000  nop
0055B754  30220007  andi   $v0, $at, 0x0007     ; P % 8 == 0 ?
0055B758  14400004  bne    $v0, $zero, +4 -> 0x0055B76C  ; 未对齐 -> .skip
0055B75C  00000000  nop
0055B760  00202821  addu   $a1, $at, $zero      ; a1 = P
0055B764  08040771  j      0x00101DC4           ; 回原指令流（lw t2,16(P) / 摘链 / 合并）
0055B768  00000000  nop
0055B76C  08040779  j      0x00101DE4           ; .skip = 原有「PREV_INUSE 置位」出口
0055B770  00000000  nop
```
**为什么能截断链**：坏桶的**唯一来源**就是这条 `P = C − (int32)prev_foot`：`prev_foot` 一旦被踩坏，`P` 就会落在 RAM 之外（用户的现场是 `0x6ED47823`，越界 1.8 GB），随后被当作空闲块**插进 128 个桶里某一个**（`0x102010/0x102014`）。F1 在**算完 P 的第一时间**做范围+对齐校验，不合法就跳到 `0x101DE4`——那是**原代码本来就有的"前块在用、不合并"出口**，因此：不合并只是少了碎片整理，**不会产生任何野指针、不会写任何内存**。合法时（正常路径）`a1 = P` 后 `j 0x101DC4` 回到原指令流，逐条等价（hook 实测 90~95583 次进入全部走这一支）。

**F2 — `0x005DECC4`（44 B，11 字）**
```
005DECC4  00A6102B  sltu $v0, $a1, $a2     ; v0 = (C < a2)
005DECC8  00060E42  srl  $at, $a2, 25      ; at = a2 >> 25（非 0 ⇔ a2 >= 32MB）
005DECCC  38420001  xori $v0, $v0, 0x0001  ; v0 = 1 ⇔ a2 <= C
005DECD0  00220825  or   $at, $at, $v0     ; at != 0 ⇔ a2 不合法
005DECD4  14200004  bne  $at, $zero, +4 -> 0x005DECE8
005DECD8  00000000  nop
005DECDC  DCC90008  ld   $t1, 8($a2)       ; ← 原 0x101D38，合法时照做
005DECE0  08040750  j    0x00101D40
005DECE4  00000000  nop
005DECE8  08040806  j    0x00102018        ; .bad：放弃本次 free（只泄漏，不野写）
005DECEC  00000000  nop
```
**为什么能截断链**：`a2 = C + size` 是同一个"用不可信尺寸算指针"的同族错误（`size` 来自 `C->head`）。若 `C->head` 被踩坏，`a2` 会跳出堆，紧接着的 `ld $t1,8($a2)`（原 `0x101D38`）就是一次野读，后续 `bne $a2,$a3` 之后的合并/插链也会用这个野基址。F2 在**用 a2 之前**把它框进 `(C, 32MB)`；不合法就 `j 0x102018`（`jr $ra`）**整场放弃这次 free**——只泄漏一块，堆账目仍然自洽（next 块的 PREV_INUSE 位保持 1，与"C 仍在用"一致）。

**F5（安全网 B）—— 已设计、已编码、未出盘**
站点 `0x00101DC4`（`8CAA0010 lw $t2,16($a1)`）→ `j CAVE_F5`（cave 44 B）：
```
lw   $t2,16($a1)      ; P->fd（原指令）
lw   $t1,20($a1)      ; P->bk
sltu $at,$a0,$t2      ; mstate < fd ?
sltu $v0,$a0,$t1      ; mstate < bk ?
and  $at,$at,$v0
beq  $at,$zero,.skip  ; fd/bk 不像 RAM 内指针 -> 不摘链
nop
j    0x00101DD8       ; 原摘链（0x101DD8 会重新载入 t1 = P->bk）
nop
.skip:
daddu $v1,$v1,$t4     ; 复刻原「P->fd == mstate」分支的延迟槽
j    0x00101DD0       ; -> 0x101DE4
nop
```
**为什么本期不出 F5 盘**：① 站点 `0x101DC4/DC8` **只在 F1 的路径上**，而 F1 已经把 `P` 校验过一遍，F5 的增量只剩"`P->fd/P->bk` 是否也像指针"；
② F5 必须**精确复刻**原 `0x101DC8` 分支的延迟槽（`daddu $v1,$v1,$t4`）与 `a3=1` 的副作用，改错会静默改变 free 的合并账目；
③ 本期四张盘已耗尽预算（任务书 ≤4 张）。**编码与反汇编见上，可直接用于下一轮。**

#### 残余风险（逐条）

| 修 | 残余风险 | 后果 | 建议 |
|---|---|---|---|
| **F1** | ①**只覆盖 `next != top` 这一支**：同一个"用不可信 prev_foot 造基址"的写法在 `0x00101D60`（`subu $a1,$a1,$a0`，`next == top` 路径，反汇编 `00101d54…00101d74` 一模一样）**还有一份**，F1 不改它 | 若损坏从那一路来，桶仍会被写坏 | 下一轮加 **F1b**（同一个 cave 体，第二个站点 `0x00101D60`） |
| | ②治因不治已坏：桶里已有的坏值不会被清掉 | 已坏的存档照样踩（`b2` 实测） | **必须与 F4 组合**（或用 F4 盘） |
| | ③`prev_foot` 合法但"语义上不该合并"时 F1 照样放行（它只做范围校验） | 与原行为一致 | — |
| | ④依赖 `a0 == mstate`、`$v0/$t5` 在 free() 内未被使用（本基底逐条核过、反汇编可查；基底 sha256 锁死） | 换基底需重核 | 换基底时重跑 `probe_inputs.py` |
| | ⑤**cave 落点 `0x0055B730` 紧邻活跃数据**（§4.2） | 6 帧像素差异（确定性） | 下一轮换落点；**在意这 6 帧就用 F4** |
| **F2** | ①`.bad` = 放弃 free ⇒ **泄漏**（重复命中则单调泄漏；本机 900 帧 0 次命中） | 长时间运行可能多占内存 | 与 F4 同盘时若真 OOM，交给 OOMFIX 的 NULL 检查兜底 |
| | ②只校验 `a2` 这一次；`size` 后面还会被用（`0x101DEC`/`0x101E44`） | `a2` 侥幸在范围内时仍可能算错 | 属"不完整校验"，非"错误校验" |
| | ③只保护 `free()`，不保护 `malloc()` 侧 | — | 由 F4 补 |
| **F4** | ①只治症：坏值仍在桶里；每次扫到桶 126 都要再进一次 cave（4 条指令，可忽略） | 桶永久带毒 | 与 F1F2 组合（`SPINFIX_F1F2_F4.iso`） |
| | ②上界是 **512 MB**（`t5` 掩码）而不是 32 MB（`sltiu` 编不出来） | 落在 `[32MB,512MB)` 的坏值会多跑一轮（多 2 行 TLB Miss 日志），第二轮必被 `t9 < v0` 拦下 | 若要严格 32 MB：把 `sltu $t3,$v0,$t5` 换成 `lui $t3,0x0200` + `sltu`（cave 从 36 B 涨到 40 B，需换落点） |
| | ③**只护住 malloc 的"大块桶链扫描"这一条路**：`0x10216C`（请求自己的桶）与 `0x102200`（unsorted 桶）两条快路径没有校验 | 若损坏落在别的桶/别的路径，仍可能踩 | 下一轮可把同一 cave 挂到 `0x10216C`/`0x102200`（需各自留 cave 洞） |
| | ④bail 之后 malloc 可能返回 NULL ⇒ **调用侧必须能接 NULL** | 这正是 **OOMFIX（解压器 NULL 检查）** 覆盖的场景 | F4 与 OOMFIX **互补**：地址上不冲突（F4 站 `0x102588`+cave `0x41A35C`；OOMFIX 站 `0x539174`+cave `0x550048`），下一轮可直接出**组合盘** |

**组合结论（明确回答"要不要组合"）**：要。
* 用户手上那份存档**已经带坏桶**（`0xA73D37F0`），所以 **F4 是"立刻不卡"的那一张**（`b1/b5/b6` 实测 Trap 2.6 M→0、能跑到 300 帧）；
* **F1F2 单独不能救**（`b2`）；
* **F1F2+F4** = 既救当前又防再写坏 ⇒ 长期方案是 `SPINFIX_F1F2_F4.iso`（本期因 §4.2 的 6 帧瑕疵，先把 `SPINFIX_F4.iso` 给用户）。

---

## 5. D. 钩子配置调整（下一次取证用）

产物：`work\builds\GR_SPINFIX\hook_config_next.ini`（可直接覆盖 `<便携模拟器>\qt\hook\hook_config.ini`；**只写配置文件，没动别人的成品目录**）。
数字来源：用户两份 dump 的 `ring.bin` 逐条统计（`tools\ring_cover.py` → `out\ring_cover.txt`，每条 24 B，帧率按两次 dump 实测 ≈57 fps）。

### 5.1 改动前后

| 项 | 旧值 | 新值 | 理由 |
|---|---|---|---|
| `watch` | `0x00500000-0x00580000`（512 KB） | `0x0055B7A0-0x0055C000` | 按页取并集后 = **pages 0x55B..0x55C**（与 `0x0055B000-0x0055C000` 同一组页），覆盖 mstate `0x55B7A0` + 128 个桶槽 `0x55B7A8..0x55BBA8` + 其后填充 |
| `ring_entries` | `262144`（6 MB） | **`2097152`**（48 MB） | 见下表；取 2 的幂让实现的 `idx % size` 走位与 |
| `log_every` | `2000` | **`500`** | 收窄后 ≈155 条/帧 ⇒ 摘要约每 3 帧一行（旧值在旧 watch 下被大流量稀释） |
| `max_dumps` | `8` | **`3`** | 每次落盘 ≈190 MB（ring.bin 48 + ring.txt ~110 + ee 32 + iop 2） |
| `dump_on_trigger` | `0` | **`1`**，`trigger` 收窄成 4 个 PC | `0x00102010/0x00102014`（**真正写坏桶 126 的那对 store**）+ `0x001024D0/0x00102584`（卡死现场的 load）；`trigger_once=1` ⇒ 第一次大块插链就自动抓下来 |

### 5.2 预计覆盖时长（实测采样率换算）

| watch / ring | 采样率 | `ring=262144`（旧） | `ring=2097152`（新） |
|---|---|---|---|
| 旧 `0x00500000-0x00580000` | **260.3 条/帧**（新 dump）/ **371.3**（旧 dump） | 706~1007 帧 ≈ **12.4~17.7 s** | 4028~5648 帧 ≈ **70.7~99.1 s** |
| 新 `0x0055B7A0-0x0055C000` | **159.0 条/帧**（新）/ **154.0**（旧） | 1649~1702 帧 ≈ **28.9~29.9 s** | **9893~13619 帧 ≈ 173.6~238.9 s**（≈2.9~4.0 min） |

> 收窄 watch 只把流量降到约 43~61%（**桶数组本身就是高频写区**：41~61% 的命中都在那 2 KB 里），所以真正管用的是**两件事一起做**：收窄 watch + ring 加 8 倍 ⇒ 覆盖从 ~15 s 提到 **~174 s（约 11.7 倍）**。

### 5.3 「覆盖损坏窗口 (19701, 22094] 需要多大 ring」

* 窗口 = **2393 帧 ≈ 42 s**（按 57 fps）。
* 用**现默认 watch（512 KB）**：需要 **≈ 88.9 万条**（ring.bin **20 MB**）——这正是旧配置（26 万条 ≈ 12~18 s）**永远抓不到损坏写者**的原因。
* 用**收窄 watch**：需要 **≈ 36.8~38.0 万条**（ring.bin **8.4~8.7 MB**）。
* 新配置（`ring=2097152` + 收窄 watch）= 覆盖 9893~13619 帧 ⇒ **对损坏窗口有 4.1~5.7 倍余量**；即便用户忘了改 watch、仍用 512 KB，也有 4028~5648 帧（1.7~2.4 倍余量）。

---

## 6. E. 给用户的最小验证步骤

1. **先确定你原来卡死的位置**：读你**卡死前那一次**的正常存档（记忆卡存档最好），或者从任务/关卡开头进。
2. **用哪张盘**：**`work\builds\GR_SPINFIX\SPINFIX_F4.iso`**（首选；最小改动、6000 帧零差异）。
   想连"别再写坏"一起上，用 `SPINFIX_F1F2_F4.iso`（注意 §4.2 的 6 帧已知瑕疵）。
   `SPINFIX_F1F2.iso` **单独用救不了现在已经卡死的存档**（它只管别再写坏）。
3. ⚠ **即时存档要改名**：补丁改了 ELF，PCSX2 看到的 CRC 也变了：
   | 盘 | CRC | 你要把状态文件改成 |
   |---|---|---|
   | `SPINFIX_F4.iso` | `755BD0BA` | `SLUS-20613 (755BD0BA).01.p2s` |
   | `SPINFIX_F1F2.iso` | `BED57022` | `SLUS-20613 (BED57022).01.p2s` |
   | `SPINFIX_F1F2_F4.iso` | `B1F8BF52` | `SLUS-20613 (B1F8BF52).01.p2s` |
   | `SPINFIX_F4_2400.iso` | `751BD0BA` | `SLUS-20613 (751BD0BA).01.p2s` |
   放进 `%LOCALAPPDATA%\PCSX2\sstates\` 再读档；**否则读档会读不到（旧 CRC 的档不会被列出来）**。
   （更稳的办法：**别用即时存档**，从记忆卡存档/关卡开头进——这样盘上的补丁一定生效。）
4. **玩什么**：按原来的路线走到卡死前一步，然后**按 L1**（就是原来按下去就卡死的那个动作）。
5. **看什么**：
   * **卡不死** = 修好了（本机：帧数从 90 断在 Trap → 300 帧正常跑完）；
   * 日志里**可能仍会出现 1~2 行** `TLB Miss … addr=0x6ed4782b / 0x6ed47837`——**这是正常的**（F4 的检查在那两条读之后），关键是**不会出现第 3 行、不会无限重复**；
   * 如果还是卡死：把 `emulog.txt` + 盘 sha256 + 当时的按键/帧号发回来。
6. **下一次取证**（想让我们抓到"谁写坏的"）：用 §5 的 `hook_config_next.ini` 覆盖 `qt\hook\hook_config.ini`，照旧玩，卡死/异常时按 **F10**；
   新配置下 ring 能存 **~174 s**（旧的 ~15 s），并且第一次"大块插链"会自动落一次盘。

---

## 7. 未达成项（如实列）

1. **"无限自旋"未在本机复现**（只复现到用户链条的**前两条 TLB Miss**）。缺的条件是"**低端页未映射**"：用户 Qt 版当次会话里 `ld 8(0)` / `lw 0x14(0)` TLB Miss，而本机 gsrunner + 这份存档里它们被映射 ⇒ 循环退出、退化成与未注入**完全相同**的老链（Trap 2,647,472 行，分毫不差）。这不是"没复现现场"，而是"**同一条链在本机的收敛方式不同**"。
2. **`0x00101D60`（`next == top` 路径的同族病灶）未修**（F1 只覆盖 `0x00101DC0`）。反汇编证据在 §4.3。
3. **F1F2 的 6 帧差异未定位到"是哪一个 cave 落点"**：需要 F1-only / F2-only 两张诊断盘做隔离（本轮磁盘额度 ≤4 张，且要留出余量）。已排除的原因：校验误判（900 帧 invalid 路径 0 次命中）、偶发/噪声（同盘两跑 0 差异）、像素级无关（RGB 确有差异）。已定位到"堆布局被推偏 0x708"这一层。
4. **`SPINFIX_F1F2.iso` 与 `SPINFIX_F1F2_F4.iso` 的 cave 落点未改到死区**（`0x0055B730` / `0x005DECC4`）。`spinfix_cave.py --min 0x10` 的复扫（找 `0x41A000..0x430000` 死代码区里更多可用零区）已启动但**未在本轮完成**（工具对每个零 run 都要做全 .text 线性扫描，`--min 0x10` 下耗时超过本轮预算）；命令留在 §8，下一轮直接跑。
5. **F5 未出盘、未动态验证**（只有静态编码 + 反汇编；理由见 §4.3）。
6. **OOMFIX 组合盘未出**（本期 4 张已满）。地址上不冲突（见 §4.3 风险表），机制上互补（F4 让 malloc 可能返回 NULL ⇒ 正需要 OOMFIX 的调用侧 NULL 检查）。
7. **归因（是否汉化数据造成）仍未判定**：沿用 `REPORT_USERDUMP_ANALYSIS` §6.4。本轮没有做"同场景汉化 vs 英文"的定量对照。
8. **`eeMemory.bin` 整块 32 MB 覆盖**未做（理由见 §2.3），只做了 8 字节最小注入与 512 KB 字面注入两种。

---

## 8. 产物清单 + 复跑命令

| 路径 | 内容 |
|---|---|
| `SPINFIX_F4.iso` / `.meta.json` | ★ 首选盘（F4，LAY 基底） |
| `SPINFIX_F1F2.iso` / `.meta.json` | 治因盘（F1+F2） |
| `SPINFIX_F1F2_F4.iso` / `.meta.json` | 组合盘 |
| `SPINFIX_F4_2400.iso` / `.meta.json` | 产品线盘（2400 基底） |
| `hook_config_next.ini` | 下一次取证用的钩子配置（§5） |
| `states\S1_bin126_user.p2s` | ★ 坏桶存档（只改 8 字节，用户真机坏值） |
| `states\S2_win500_580.p2s` / `S3_base.p2s` | 512 KB 字面注入 / 健康对照 |
| `states\S1_bad_F4.p2s` / `S1_bad_F1F2.p2s` / `S1_bad_F1F2_F4.p2s` / `S3_base_F4.p2s` | 打了补丁的存档（同现场验证用） |
| `states\states.meta.json` + `out\state_build.txt` | 存档注入的逐点回读与 diff 统计 |
| `tools\spinfix_apply.py` | 出盘工具（基底指纹 + 站点断言 + cave 反汇编回读 + 8 项自证 + meta） |
| `tools\spinfix_state.py` / `spinfix_state_fix.py` | 造坏桶存档 / 把补丁打进存档 |
| `tools\spinfix_cave.py` / `probe_caves.py` | cave 审计（复用 GR_OOMFIX 的审计器）+ 8 份现场快照逐字节核对 |
| `tools\spinfix_run.ps1` / `spinfix_batch.ps1` / `smoke_spinfix.ps1` | 单跑 / 批量 / 6 盘冒烟（都带"独占检查、只记录不杀"） |
| `tools\spinfix_analyze.py` / `spinfix_ramcheck.py` / `ring_cover.py` | 日志读数 / 补丁存活回读 / ring 覆盖率 |
| `tools\probe_inputs.py` / `probe_binmap.py` / `probe_f44.py` | 输入核对 / mstate+桶数组 / 运行时 RAM 现场 |
| `runs\a1..a3`, `runs\b1..b6`, `runs\smoke_*`, `runs\d3_trace`, `runs\d4_scan`, `runs\e1/e2_*`, `runs\r1/r2_*` | 全部现场（每个目录有 `cmdline.txt` + `analysis.json`，大日志已裁剪） |
| `out\*.txt` / `out\*.json` | 上述全部数字的原始输出 |

复跑（都在仓库根执行；`$py` = `C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`）：

```powershell
# 出盘（4 张，逐字节自证）
& $py work\builds\GR_SPINFIX\tools\spinfix_apply.py --flavor F4      --base-flavor lay1 --out work\builds\GR_SPINFIX\SPINFIX_F4.iso
# 造坏桶存档 + 补丁存档
& $py work\builds\GR_SPINFIX\tools\spinfix_state.py
& $py work\builds\GR_SPINFIX\tools\spinfix_state_fix.py --state work\builds\GR_SPINFIX\states\S1_bin126_user.p2s --meta work\builds\GR_SPINFIX\SPINFIX_F4.meta.json --iso work\builds\GR_SPINFIX\SPINFIX_F4.iso --out work\builds\GR_SPINFIX\states\S1_bad_F4.p2s
# 现场：未修 vs 各修复盘（90/300 帧）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_SPINFIX\tools\spinfix_batch.ps1 -Phase A
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_SPINFIX\tools\spinfix_batch.ps1 -Phase B
# 6000 帧冒烟（6 张盘）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_SPINFIX\tools\smoke_spinfix.ps1
# 逐帧对照 / 补丁存活 / ring 覆盖
& $py work\builds\GR_OOMFIX\tools\oomfix_frames.py work\builds\GR_SPINFIX\runs\smoke_SPINFIX_F4 work\builds\GR_SPINFIX\runs\smoke_LAY_fix1_bytecount
& $py work\builds\GR_SPINFIX\tools\spinfix_ramcheck.py --ram work\builds\GR_SPINFIX\runs\smoke_SPINFIX_F4\win_f00005970_eeram.bin --meta work\builds\GR_SPINFIX\SPINFIX_F4.meta.json
& $py work\builds\GR_SPINFIX\tools\ring_cover.py
# 下一轮：在 iomanX 死代码区找更多可用零区（本轮未跑完）
& $py work\builds\GR_SPINFIX\tools\spinfix_cave.py --iso work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso --min 0x10 --top 5 --json work\builds\GR_SPINFIX\out\cave_min16.json
```

---

## 9. 磁盘（如实）

| 时点 | C 盘可用 |
|---|---|
| 开工前 | 19.3 GB |
| 4 张盘写完后 | 12.3 GB |
| 清理前 | 9.0 GB |
| **本轮结束** | **11.7 GB**（`GR_SPINFIX` 合计 **7.43 GB**，其中 4 张盘 6.59 GB） |

大日志与中间物控制（都在 `work\builds\GR_SPINFIX\**` 内，未动别人的东西）：
* 未修盘 90 帧的 `emulog.txt` = **111 MB**（Trap 刷屏），统计后即裁成 `emulog_sample.txt` 并删原日志（每个 run 目录都有 `analysis.json` 存数字）。
* `e1` 的 `hooklog.txt` 撞到实现的 200,000 行上限（只覆盖到帧 436——这就是我改用"只挂无效路径标签"的 `e2` 的原因，`e2` 的 `hooklog` 为 **0 行**，见 §4.2）；超过 20 MB 的 hooklog 只留 `hooklog_sample.txt`。
* 删掉 791 个**非证据**大文件（needle 机制的 32 MB RAM 快照 `*_eeram.bin`/`*_iopram.bin`、`gsup_*.bin`、`cdvd.log`），回收 **2.63 GB**；**所有被本报告引用的文件都保留**（`win_*_eeram.bin` 7 份、各 `analysis.json`、`emulog_sample.txt`、`hooklog_sample.txt`、191×6 张冒烟截图、4 张盘与 13 个存档）。
