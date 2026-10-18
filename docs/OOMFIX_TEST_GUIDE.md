# OOMFIX 验证指南（给用户，照抄即可）

> 针对：任务中按 **L1**（武器/资源加载）导致的卡死。
> 根因与修复见 `docs\REPORT_OOMFIX.md`。本页只说「怎么验」。

---

## 0. 先看这一条（最重要，不然你会白测）

**不要用旧的即时存档（savestate）来验证这次修复。**

PCSX2 的 `.p2s` 即时存档里存了**整块 32 MB EE 主存**，读档之后 VM 直接从存档的 PC 继续跑，
**BIOS 不会再去光盘里装载 `SLUS_206.13`** ⇒ 光盘里的修复代码会被存档里的旧代码覆盖掉。
本机实测：修好的盘 + 旧存档，运行时内存与**未修盘逐字节相同**，照旧崩。

**正确做法（二选一）**

| 做法 | 说明 |
|---|---|
| **A. 用记忆卡存档（推荐）** | 用游戏内正常存档（`Mcd001.ps2`/`Mcd002.ps2`）继续玩；从关卡/任务开始处重新进入，走到原来崩的地方。 |
| **B. 用我们打好的补丁存档** | `work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s` 已经把修复代码写进存档的 EE 主存，直接放进 `%LOCALAPPDATA%\PCSX2\sstates\` 然后读 **1 号档**即可（它对应 `OOMFIX_lay1.iso`）。 |

> 顺带一提：因为补丁改了 ELF，盘的 CRC 会变
> （`LAY_fix1_bytecount` = `7A761FCA` → `OOMFIX_lay1` = **`CC41DF03`**；`GR_REBUILD2400` = `7A361FCA` → `OOMFIX2400` = **`CC01DF03`**）。
> 所以旧的 `SLUS-20613 (7A761FCA).01.p2s` 在修复盘上**不会出现在读档列表里**——这也是必须改名/换卡的另一个原因。

---

## 1. 用哪张盘

| 盘 | 什么时候用 |
|---|---|
| `work\builds\GR_OOMFIX\OOMFIX2400.iso` | **主力测试盘**（基底 = `GR_REBUILD2400.iso`，主力产品线） |
| `work\builds\GR_OOMFIX\OOMFIX_lay1.iso` | 与那份「按 L1 会崩」的存档**同源基底**（`LAY_fix1_bytecount.iso`）+ 补丁；配补丁存档做同现场复现 |

两张盘都只改了 **4 + 44 字节**（ELF 里一处 `j` + 一段 44 B 的 cave），其余与基底逐字节相同（`meta.json` 有全量 diff 与自检）。

---

## 2. 最小验证步骤（`OOMFIX2400.iso`，约 5 分钟）

1. 打开你平时用的 PCSX2（官方版即可），**独占**运行：
   - 先确认没有另一个 PCSX2 在跑（同一个记忆卡目录不能两个实例同时写）。
2. 引导 `OOMFIX2400.iso`。
3. **从记忆卡存档继续**（不要读旧即时存档，见 §0）：
   - 主菜单 → 选档案 → 载入你原来那个进度 → 进任务。
   - 如果原来那份进度是「任务中」的即时存档，请从任务的最近一个记忆卡存档重进。
4. 进任务后照原来的操作按 **L1**（触发武器/资源加载），可以再按几次 R1/切武器，把原来的复现路径走一遍。
5. 观察 30 秒～2 分钟：

| 你看到的 | 结论 |
|---|---|
| 不再卡死，能继续玩 / 能过原来卡住的那一步 | ✅ 修复有效 |
| 仍然卡死，但日志里**没有** `Trap exception at 0x80000274`、**没有** `EE: Unrecognized op` | ⚠ 与本机结果一致：**旧的内存写坏已经治好**，但这次是另一个原因（本机实测是堆已耗尽后 `Jump to unaligned address (PC: 0x7e7e7e7e)`）。请把日志发给我们 |
| 日志里仍有 `Trap exception at 0x80000274` / `EE: Unrecognized op` | ❌ 修复没生效——请确认你**没有**在读旧即时存档，并把这盘的 sha256 与日志发给我们 |

6. 反馈请附上：
   - 整份 `emulog.txt`（`%LOCALAPPDATA%\PCSX2\logs\emulog.txt`，或你的便携版日志目录）；
   - 用的盘的 sha256（`certutil -hashfile OOMFIX2400.iso SHA256`）；
   - 崩/不崩时的按键与大致时间点。

---

## 3. 想复现「按 L1 必崩」的同一现场（进阶，验证修复到底改了什么）

只有这一条路能在**同一帧**对照「修 vs 不修」：

1. 把补丁存档放进 `%LOCALAPPDATA%\PCSX2\sstates\`：
   ```
   copy "work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s" "%LOCALAPPDATA%\PCSX2\sstates\"
   ```
2. 引导 `OOMFIX_lay1.iso`，读 **1 号档**（F3 或菜单里的读档），立刻按 **L1**。
3. 预期：
   - 不再出现 `Trap exception at 0x80000274` / `EE: Unrecognized op`（未修盘在这份存档下 100% 出现，本机 4,990,386 行）；
   - 但**仍会在同一帧停下**（`Jump to unaligned address (PC: 0x7e7e7e7e)`），因为这份存档的堆已经无法满足那次 64 KB 的分配——这是**另一个**问题（根因未解决，见报告 §5.4/§8）。

> 想自己造补丁存档（例如换成你的槽位 10）：
> ```
> python work\builds\GR_OOMFIX\tools\oomfix_zstd.py patch ^
>   "%LOCALAPPDATA%\PCSX2\sstates\SLUS-20613 (7A761FCA).10.p2s" ^
>   "%LOCALAPPDATA%\PCSX2\sstates\SLUS-20613 (CC41DF03).10.p2s" ^
>   --entry eeMemory.bin --apply work\builds\GR_OOMFIX\tools\state_patch_spec.json
> ```
> （只改存档里 12 个代码字，其余 32 MB 与 16 个 zip 条目逐字节不变，工具带自证）

---

## 4. 本机已经验过什么（你可以直接采信的部分）

- **未修基底**（`LAY_fix1_bytecount.iso`）+ 那份存档 + 第 30 帧按 L1：**100% 复现** `Trap exception at 0x80000274`（4,990,386 行）、`EE: Unrecognized op` 53 行、`0x1300` 第 44 帧被写 63 次、低端 `0x0..0x1000` 被写 3,322 B。
- **修复盘**同一现场：**0 行 Trap / 0 行非法指令**、`0x1300` 第 44 帧被写 **0** 次、低端 `0x0..0x1000` 变化 **0 B**，并且调用者的失败分支确实被执行（资源被跳过）。
- **冷启动 6000 帧冒烟**（两张修复盘各一次）：191 张截图、TLB 0、Trap 0、无非法指令，与各自基底**逐帧逐像素 0 差异**。
- **不按 L1** 的对照：跑满 130 帧干净 ⇒ 补丁只在「按 L1 触发资源加载」这条路径上起作用。

细节数字见 `docs\REPORT_OOMFIX.md` §5 / §6。
