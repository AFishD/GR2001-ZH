# A/B 打靶测试指南 — 《PS2 幽灵行动》汉化盘 `GR_ZH113b` 硬卡死最小对照盘

> ⚠ **历史错误断言订正（2026-10-18 收尾轮）**：本文含已被实测/实机否证的表述 —— 见 `docs/CORRECTIONS.md` §4、§6。
> 原文保留作过程记录；**结论冲突时以 `docs/CORRECTIONS.md` + `docs/STATUS.md` 为准**。
> 📦 本文档已归档到 `docs/_obsolete/`：被推翻路线：sp+221 变长步进 / A-B 打靶系列（对照盘已清理）；索引见 `docs/README.md`。

> 执行者：汉化执行者（A/B 打靶子代理）· 2026-10-15
> 仓库根 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> 盘目录：**`work\builds\GR_AB\`**（5 张，每张 1,648,164,864 B = 1.535 GiB）
> 静态验证结论见 `work\builds\GR_AB\evidence\TASK1_STATIC.md`（含 ★ 可疑偏移站点表）
> **未修改任何既有盘**；未 commit / 未切分支 / 未 merge；**未使用 `Select-Object -First N`**。

---

## 0. ★ 先读这三句（它会改变你怎么看 AB_01）

```
① AB_01 与 AB_02 打的是同一个站点（DrawString+0x33C）。静态证据（TASK1_STATIC.md 任务 1-A）显示
   「lbu v0,221(sp)」**不是笔误** —— sp+221 就是同一个 cave 解码器写在缓冲区前一字节的「本字符长度」
   （`0x416F34 sb v0,-1(a0)`，a0 = sp+222）。所以：
     · AB_02（撤销变长步进，回到英文原盘的 +1）= 真正的"撤销汉化改动"对照；
     · AB_01（221→222）= **负向对照**：s0 会按"码位低字节"跳步（0xB1=177、0xBA=186…）
       ⇒ 预期**立刻**出现文字错位/花屏/异常，而不是"修好了"。
   两张盘都要跑，但请按下面的"预期现象"读结果，不要把 AB_01 变坏当成坏消息 —— 那是**模型被证实**。
② 5 张盘都**仍然是完整汉化盘**，只做单点改动。**不存在"英文盘对照臂"**：本轮的"基准"是
   `AB_00_base.iso`（= `GR_ZH113b.iso` 逐字节拷贝，sha256 完全相同）。
③ 五张盘都**继承** `GR_ZH113b` 上仍然存在的一个已知读取偏移错：
   `GetActorNameAbbreviated` cave `VA 0x5657E0 / ISO 0x4F9060` 的 `lhu a1,2(t0)`
   （对象布局 = `{u16 len @+0, …, char* data @+4}` ⇒ 长度应在 `+0`；`GR_ZH113b_fix` 已修成 `0(t0)`，
   但**本任务的基底是 `GR_ZH113b`，所以没修**）。详见 `evidence/A_suspicious_offsets.md` §2.1。
   ⇒ 这是**混淆因素**：若所有 5 张盘都卡，**不能**据此断定候选 1/2 不成立。
```

---

## 1. 五张盘一览（每张"只差什么"）

| 盘 | 改动 | 与基底的逐字节差异 | sha256（前 16） | 目的 |
|---|---|---|---|---|
| `AB_00_base.iso` | **无**（= `GR_ZH113b.iso` 逐字节拷贝） | **0 run / 0 B** | `ff3abd3c50e380f6` | 基准；复现基线卡死 |
| `AB_01_sp222.iso` | `DrawString+0x33C`：`lbu v0,221(sp)` → **`222(sp)`** | **1 run / 1 B** @ISO `0x1AD62C`：`DD` → `DE` | `46571b1b5a40452b` | **负向对照**：把"唯一读 221"改成与另三处一致（预期变坏） |
| `AB_02_sp221_revert.iso` | 同站点**整对**回退英文原盘 `nop ; addiu s0,s0,1` | **1 run / 8 B** @ISO `0x1AD62C`：`DD 00 A2 93 21 80 02 02` → `00 00 00 00 01 00 10 26` | `5b8ac982213c3b1b` | 撤销该变长步进（候选 1 的"反证臂"） |
| `AB_03_fontres_real7k.iso` | `FONT.RES`（MENU + GR 两份）**内部头 `real` 5,942 → 7,222** + LZO 流重压（明文 = 原 5,942 B + 1,280 B 零）；`stored` 仍 4,421；**IMG 条目表不动** | **4 run / 1,355 B**（见 §2.3） | `4275f43cca4cfd35` | 候选 2 方向一：让内部头与条目 `real` 一致，并把明文补到 7,222 |
| `AB_04_fontres_real5942.iso` | `FONT.RES` 的 **IMG 条目表 `real` 7,222 → 5,942**（MENU #4 + GR #906），与内部头一致 | **2 run / 2 B** @ISO `0x0257EA2D` + `0x5EC2F90D`：`1C` → `17` | `331c23519fde4368` | 候选 2 方向二：让条目与内部头一致，明文不补 |

**完整 sha256 / 尺寸 / 构建命令 / 逐 run 差异清单**：每张盘同目录的
`AB_00_base.meta.json` … `AB_04_fontres_real5942.meta.json`。
**重建命令**：`python work\builds\GR_AB\tools\ab_build.py [盘名]`（源盘只读）。

### 1.1 AB_01 / AB_02 的字节级说明

```
VA 0x219DAC  ⇒  FILE 0x119E2C  ⇒  ISO 0x1AD62C   (ISO = VA − 0x6C780)

GR_ZH113b（= 基底）在 ISO 0x1AD62C 起的 8 字节：
   DD 00 A2 93 | 21 80 02 02
   = 0x93A200DD lbu v0,221(sp)   ; 0x02028021 addu s0,s0,v0
   （0x93A200DD 小端 = DD 00 A2 93 ⇒ **imm 低字节在 +0**）

AB_01 只动 +0 这一个字节：DD → DE
   0x93A200DE = lbu v0,222(sp)   ；其余 7 字节不变
AB_02 把这 8 字节整体换成英文原盘 GR_EN_ORIG 的同址字节（构建脚本实测取回并断言）：
   00 00 00 00 | 01 00 10 26
   = 0x00000000 nop              ; 0x26100001 addiu s0,s0,1
```
> 已用反汇编在**成品盘上回读校验**：`AB_01` = `lbu v0,222(sp)`、`AB_02` = `nop ; addiu s0,s0,1`。
> （初版构建曾把 `DE` 误写到 +2 得到 `lbu fp,221(fp)`，已定位并修正；本表与 `AB_01_sp222.meta.json`
> 是修正后的结果，sha256 `46571b1b…`。）

### 1.2 AB_03 的字节级说明

```
MENU.IMG FONT.RES @ISO 0x5ECE8120（条目 #4，off=758,048，stored=4,421）
   头 6 B : d1 05 00 00 36 17  →  e8 05 00 00 36 1c
            comp 0x5D1=1,489 → 0x5E8=1,512 ; real 0x1736=5,942 → 0x1C36=7,222
   流  24 B @0x5ECE86F6 变化（该盘的 LZO 流前缀基本不变，只在尾部多出 1,280 个零的编码）
GR.IMG  FONT.RES @ISO 0x0F04EE40（条目 #906，off=212,710,976，stored=4,421）
   头 6 B : 34 05 00 00 36 17  →  56 05 00 00 36 1c
            comp 0x534=1,332 → 0x556=1,366 ; real 5,942 → 7,222
   流 1,319 B @0x0F04EE75 变化
```
* 明文 = **原 5,942 B 逐字节不变** + **1,280 B `00`**（= 补齐到条目 `real` 的 7,222）。
* 重压后已用**两个独立解码器**自检：`tools/gr_tools/lz77_decode.lzo1x_decompress` 与
  `tools/text_csv/tcslib.lzo1x_decompress`，均还原出 7,222 B 且逐字节相等。
* `stored` 保持 4,421 ⇒ 槽内余量充足（MENU 1,520 ≤ 4,421−8；GR 1,374 ≤ 4,413）。
* **不变式检查**：`stored(4,421)` 与 `real(7,222)` 关系不变（`stored < real`，与英文盘相同）；
  IMG 条目表、名字区、哈希区、ISO9660 **一个字节都没动**。

### 1.3 AB_04 的字节级说明

```
MENU.IMG 条目表 #4   u32[7] @ISO 0x5EC2F90D（表在 IMG+0x830，步长 48，字段 +28）
GR.IMG   条目表 #906 u32[7] @ISO 0x0257EA2D
   7,222 = 0x00001C36  →  5,942 = 0x00001736
   差异只有这 2 个字节（小端的高字节 1C→17）
```
* 明文与 LZO 流**未动**（`stored=4,421` 也不动）⇒ 只让"条目声明"与"内部头 + 实际明文"一致。
* 这是本组里**唯一**会改变"引擎若按条目 `real` 分配/解压时会拿到什么"的盘。

---

## 2. 每张盘：验证什么假设 / 预期现象 / 怎么跑

### 通用前置（每张盘都要做）

```powershell
# 0) 确认模拟器无他人实例（独占资源；发现他人实例只等待、不许杀）
Get-Process -Name '*pcsx2*' -ErrorAction SilentlyContinue |
  Select-Object Id,ProcessName,StartTime

# 1) 用现成 gsrunner 采集器（与本仓库历史轮次同一口径）
python tools\iso_build\fix_zh118_run.py `
  --iso  "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_AB\AB_02_sp221_revert.iso" `
  --tag  "ab_02_sp221_revert" `
  --maxframes 0 --snap 0 --timeout 1800 `
  --memcards "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH98\temp\r76\mc_zh" `
  --outroot  "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_AB\runs"

# 2) 跑完数 TLB / 看停顿 PC（日志在运行中被独占，必须等退出后再读）
(Select-String "work\builds\GR_AB\runs\dump_ab_02_sp221_revert\emulog.txt" -Pattern 'TLB Miss').Count
```

* **每张盘的实机时长建议 ≥ 15 分钟**（用户实测"游玩达到一定时间之后才出现"）。
* 本机 gsrunner **历史上复现不出缺页**（`docs\REPORT_zh_heap_corruption.md` §4 已定案：BIOS/记忆卡/ISO/版本
  全对齐后 5 个手臂全 0）⇒ 本轮的验收重点应放在**可判定的数字**：
  `frames / elapsed / TLB Miss 行数 / 停顿 PC 序列 / 最长连续同帧段`，外加**画面**。
* 建议**同一操作序列**跑每一张盘（否则不可比），并记录 `emulog` 里的 `Game CRC`（应为 `7A361FB7` 系）。

### 2.1 `AB_00_base.iso` — 基准

| 项 | 内容 |
|---|---|
| 验证的假设 | **基线可复现性**：汉化盘的硬卡死是否在本机能出现 |
| 预期现象 | 与用户描述一致：游玩到一定时间后画面静止；`emulog` 出现 `pc=0x1024D0 addr=0x8 [load]` / `pc=0x102584 addr=0x14 [load]` 的**同时间戳无限重复**（`chunk_alloc` 的 bin 链走到 NULL）。若本机 0 条 TLB，则**这一轮全部 5 张盘都会是 0**，只能比画面 |
| 复现步骤 | ①正常游玩（任意关卡）→ ②**火箭筒（AT4 / RPG-7）开火** → ③**L1 开小队/地图界面** → ④存读档；循环直到 ≥15 分钟或卡死 |
| 判据 | `TLB Miss` 行数、停顿 PC 序列、最长连续同帧长度、截图去重数 |

### 2.2 `AB_01_sp222.iso` — 负向对照（把"唯一读 221"改成与另三处一致）

| 项 | 内容 |
|---|---|
| 验证的假设 | 「`sp+221` 是笔误」这一假设（报告候选 1 的核心疑点） |
| 静态预测 | **假**：`sp+221` 是解码器 `0x416F34 sb v0,-1(a0)` 写的长度；改成 `222(sp)` 后 `s0 += 码位低字节`（`0xB1`=177、`0xBA`=186、`0x8x`=104…）⇒ 索引会**跳过/越过**字符串 |
| **预期现象（重点）** | **中文文字立刻出现错位/缺字/花屏/行宽异常**（不需要等 15 分钟）；若 `s0` 越过串尾，`slt v1,s0,s7` 会失效、循环可能读到非法地址 ⇒ 也可能立刻异常或退出 |
| 怎么读结果 | ① 若"立刻变坏" ⇒ **证实** §0 的偏移模型，`sp+221` 不是笔误；**候选 1 的"偏移不一致"分支被排除**；<br>② 若"什么都没变" ⇒ 说明这条路径在当前流程里**没被执行到**（例如该分支需要 `lbu v1,36(s3) == 0` 才走）⇒ 记录并转入 AB_02；<br>③ 若"卡死反而变晚/消失" ⇒ **极重要**，说明这条路径确实在写坏堆，把 AB_02 的结果一起报上来 |
| 时长 | ≥ 15 分钟（但预期前 60 秒内就能看出文字是否坏） |

### 2.3 `AB_02_sp221_revert.iso` — 候选 1 的反证臂（撤销变长步进）

| 项 | 内容 |
|---|---|
| 验证的假设 | **候选 1**：文字链的"变长步进"改写导致越界写 ⇒ 堆损坏 ⇒ dlmalloc bin 走到 NULL |
| 静态背景 | 该站点的 EN 原语义 = `nop ; addiu s0,s0,1`（**每轮固定 +1**）。撤销后，中文对偶码（2 字节）会被**当成两个单字节**各画一次 ⇒ 中文本身会显示错乱；但 **`s0` 的推进量与 EN 完全一致** ⇒ 不再有"从栈上读步长"的路径 |
| 预期现象 | ①**中文文字错乱**（预期内，这不代表盘坏了）；②若候选 1 成立 ⇒ **硬卡死消失或显著推迟**；③若仍按原节奏卡死 ⇒ **候选 1 被排除**（同时因为文字已经错乱，也不能排除"其他文字层改动"） |
| 判据 | 与 `AB_00` 用**同一操作序列**同时长对比：`TLB Miss` 行数、首次卡死的时间点、停顿 PC 序列 |
| 注意 | 本盘文字错乱 ⇒ **不能**用"截图是否正常"作判据，只能用**时序/计数** |

### 2.4 `AB_03_fontres_real7k.iso` — 候选 2 方向一

| 项 | 内容 |
|---|---|
| 验证的假设 | **候选 2**：`FONT.RES` 内部头 `real`(5,942) 与 IMG 条目 `real`(7,222) 不一致 ⇒ 引擎按 7,222 分配/解压却只有 5,942 字节的真实内容 ⇒ 字表解释器走过 5,942 后读**未初始化堆**，且 `huge` 面 `idx ≥ 96` 越界 ⇒ 垃圾 UV/宽度 |
| 本盘做了什么 | 把内部头改回 7,222，并把**明文补零到 7,222** ⇒ 两个 `real` 一致，尾部再也不是"未初始化堆"而是**确定的零**；`huge` 面仍然只有 96 条（本盘**不修** `nrec`，保持单变量） |
| 预期现象 | ①若候选 2 成立 ⇒ 卡死**显著推迟/消失**，且中文显示**不应变差**（明文前缀逐字节未变）；②若**仍按原节奏卡死** ⇒ 候选 2 被排除；③若**中文变差或立刻异常** ⇒ 说明引擎实际用的是**内部头**且把 7,222 当真（尾部零被当成记录解释）⇒ 反向证明"内部头 `real` 是权威"，这是一个**独立的重要结论** |
| 判据 | 与 `AB_00` 同时序对比；另外**专门看中文有没有变化**（与 `AB_00` 同帧逐像素比对更佳） |

### 2.5 `AB_04_fontres_real5942.iso` — 候选 2 方向二

| 项 | 内容 |
|---|---|
| 验证的假设 | 同上，但改的是**条目表**：让条目 `real` 与内部头/实际明文一致 |
| 本盘做了什么 | `MENU #4` 与 `GR #906` 的 `u32[7]` 由 7,222 → 5,942（**只 2 个字节**），LZO 流与明文**未动** |
| 预期现象 | ①若"引擎按条目 `real` 分配"⇒ 缓冲区从 7,222 缩到 5,942 ⇒ 不再有尾部垃圾；**同时** `huge` 面 96 条的问题**不受影响**（本盘不动 `nrec`）；②若卡死消失/推迟 ⇒ 候选 2 的"条目 `real` 权威"分支成立；③若**立刻崩/花屏** ⇒ 说明引擎按条目 `real` 做 LZO 解压上界，缩到 5,942 反而截断了某些东西 ⇒ 也是一条可用结论 |
| 判据 | 同 `AB_03`；特别注意**读档/进关卡时**的字库加载（`LoadingTexturePak` / `UITextureMgr`）是否报错 |

---

## 3. 判定表（跑完怎么下结论）

| 观察 | 结论 | 下一步 |
|---|---|---|
| **只有 `AB_02` 不卡** | ★ **候选 1 成立**（文字链变长步进是元凶） | 保留 `nop;addiu s0,s0,1` 语义的前提下重做 DBCS 步进（把长度放到**另一个不冲突的槽**或直接在**寄存器**里回传，不再借用 `sp+221`）；同时把 `DrawLetters+0xB8` 的 `+3→+5` 一起 A/B |
| **只有 `AB_03` 不卡** | ★ **候选 2 方向一成立**（内部头 `real` 是权威，尾部补零修好了） | 正式版：内部头 `real` 与明文长度**必须等于** IMG 条目 `real`；并把 `huge` 面的 `nrec` 从 96 恢复到 224（或让 `idx ≥ nrec` 掉进网格时**钳位到 0** 而不是负 `slot`） |
| **只有 `AB_04` 不卡** | ★ **候选 2 方向二成立**（条目 `real` 是权威） | 正式版：条目 `real` 与内部头/明文长度三者一致 |
| **`AB_03` 与 `AB_04` 都不卡** | ★ 候选 2 成立且**两个口径都要一致** | 直接做"三者对齐 + `nrec` 恢复 224"的正式版 |
| **`AB_03` 与 `AB_04` 都仍卡** | **候选 2 被排除** | 转到：`huge` 面 `nrec` 96→224 单变量盘（本组未出，需要新一轮）；以及 TASK1_STATIC 的 S1（`2(t0)`，用 `GR_ZH113b_fix` 的 1 字节修）与 S2（`DoWordWrap` `sp+252`） |
| **`AB_01` 立刻变坏** | ✅ **偏移模型被证实**（`sp+221` 是解码器写的长度，不是笔误） | 候选 1 的"偏移不一致"分支**排除**；把注意力放在 AB_02 与候选 2 |
| **`AB_01` 与 `AB_00` 无差别** | 该分支在测试流程里**没被执行** | 换触发路径（例如进"字体表/教程"页），或先把 `lbu v1,36(s3)` 的分支条件查清（静态未达成项） |
| **5 张盘全部同型卡死（含 `AB_00`）** | 本轮**无区分度** | 见 §4 混淆因素；需要先把 S1 修掉（`GR_ZH113b_fix` 的 1 字节）+ 出 `nrec` 单变量盘 |

> **判定纪律**：一次只改一个变量、同一操作序列、同一时长；`TLB Miss` 计数与**首次异常的时间点**
> 要一起给（只看计数会被"跑得久"骗）。

---

## 4. 混淆因素（必须一起报）

| # | 因素 | 说明 |
|---|---|---|
| C1 | **五张盘都是汉化盘** | 没有英文对照臂。`AB_00` 是"汉化基准"，不是"原盘"。若 `AB_00` 不卡，本轮无法判定任何事 |
| C2 | **S1 未修**：`VA 0x5657E0 / ISO 0x4F9060` 的 `lhu a1,2(t0)` 仍在 | 这是**已知的读取偏移错**（对象布局 `{u16 len @+0; char* data @+4}`），`GR_ZH113b_fix` 已修成 `0(t0)`。它在 `GetActorNameAbbreviated`（**小队/名字显示路径**）上，与 L1 界面相关 ⇒ 若 5 张全卡，不能排除是它 |
| C3 | `AB_02` 的文字一定错乱 | 撤销变长步进后中文必然显示错乱 ⇒ 本盘**不能**用画面判据 |
| C4 | `AB_01` 预期会立刻变坏 | 见 §0/§2.2；这是**负向对照**，不是修复臂 |
| C5 | `huge` 面 `nrec=96` 在本组 5 张盘里**始终未修** | `AB_03`/`AB_04` 只动 `real`，不动 `nrec` ⇒ 若"越界 UV"是主因，本组测不出来 |
| C6 | `AB_03` 重压了 LZO 流 | 虽然明文前缀逐字节未变、两个解码器都自检通过，但**压缩流的字节序列与原盘不同** ⇒ 若引擎对流的长度/边界有隐藏假设，这是一条新变量。要排除它，可另出一版"只改内部头 `real`、不动流"的盘（**不安全**，未构建，见 §5） |
| C7 | 本机复现能力有限 | `docs\REPORT_zh_heap_corruption.md` §4 已定案：gsrunner 在 BIOS/记忆卡/ISO/版本全对齐后**仍复现不出缺页** ⇒ 本机 A/B 大概率是"全 0"，验收重点应放在可判定数字 |
| C8 | `Frame rate: 59.94` 那类行**不是实测帧率** | 是 PCSX2 的 CRTC 配置输出，**不得当性能证据**（`LEAD_CAPACITY_2400.md` §18.2） |
| C9 | 模拟器是**独占资源** | 并发会把两边 fps 都压到 ~30，直接毁掉读数。见 §6 |

---

## 5. 未构建的盘与原因（如实登记）

任务书允许最多 5 张，已用满。以下两条**想测但没出**，原因是**无法在"只改 1~2 字节/单变量"的前提下安全构建**：

1. **`huge` 面 `nrec` 96 → 224（或 224→96 反向）单变量盘** —— 需要重排 `FONT.RES` 明文与整张图集的记录表
   （`fld[4]×fld[5]` 与 224 条记录矩形必须一起给），**不是 1~2 字节**，且与 `AB_03`/`AB_04`
   的"`real` 对齐"混在一起会破坏单变量 ⇒ 留给下一轮。
2. **"只改内部头 `real`、不动 LZO 流"盘** —— 内部头 `real` 是解压输出尺寸；
   把它从 5,942 改成 7,222 而流只产出 5,942 字节，会让解码器**读越输入流末尾**（垃圾/异常）。
   这属于"故意制造不确定行为"，**按纪律停手、不硬撑**。要做等效对照请用 `AB_03`（已补齐明文到 7,222）。

另外 `S2`（`DoWordWrap+0x160`：`addiu a0,sp,248` → `lw a0,252(sp)`）与 `S3`
（`ComputeDrawXY` cave 的 `82 / 20(a0) / +4`）**也没有出盘**：它们的"正确值"静态未判定
（见 `TASK1_STATIC.md` 未达成项 2/3），做盘只能靠猜，违反"每个结论要有证据"。

---

## 6. 环境与污染登记（2026-10-15 本次构建时）

| 项 | 状态 |
|---|---|
| 本次构建是否用了模拟器 | **否**（任务 1/2/3 均为纯静态；按任务书"不需要跑模拟器，勿为它阻塞交付"） |
| 起跑前 pcsx2 进程检查 | **发现 2 个他人实例**：`pcsx2-gsrunner` PID **11636**（起于 21:00:27）、`pcsx2-qt` PID **32020**（起于 21:05:01） |
| 处置 | **只记录，不杀**（纪律：发现他人实例只等待、不许杀）。⇒ **任何人现在起跑都处于并发污染状态**，fps/时序读数不可信 |
| gsrunner 路径 | `third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe` |
| 采集器 | `python tools\iso_build\fix_zh118_run.py`（`--iso/--tag/--maxframes/--snap/--timeout/--memcards/--outroot/--grswitch`） |
| BIOS / 记忆卡 | 沿用 `work\builds\GR_ZH98\temp\r76\mc_zh` 与 JP BIOS（`-grbios` / `-grbiosname`），与 `REPORT_zh_heap_corruption.md` §4.3 同一口径 |
| 日志 | `emulog.txt` 在运行中被独占，**必须等实例退出后**再读 |

---

## 7. 复现构建 / 复核静态结论

```powershell
# 重建 5 张盘（源盘只读；只写 work\builds\GR_AB\**）
python work\builds\GR_AB\tools\ab_build.py
python work\builds\GR_AB\tools\ab_build.py AB_03_fontres_real7k     # 单张重建

# 逐字节差异清单 / sha256 / 尺寸 —— 每张盘的 meta.json
Get-Content work\builds\GR_AB\AB_01_sp222.meta.json

# ★ 可疑偏移站点表 + 三项静态验证
Get-Content work\builds\GR_AB\evidence\TASK1_STATIC.md
Get-Content work\builds\GR_AB\evidence\A_suspicious_offsets.md
```

**产物索引**

| 路径 | 内容 |
|---|---|
| `work\builds\GR_AB\AB_00_base.iso` … `AB_04_fontres_real5942.iso` | 5 张打靶盘 |
| `work\builds\GR_AB\AB_*.meta.json` | 逐字节差异清单 / sha256 / 尺寸 / 构建命令 |
| `work\builds\GR_AB\evidence\TASK1_STATIC.md` | 三项静态验证汇总（数字 + 结论 + 未达成） |
| `work\builds\GR_AB\evidence\A_suspicious_offsets.md` | ★ 可疑偏移站点表 S1…S15 |
| `work\builds\GR_AB\evidence\A_offset_table.md` / `.json` | 67 处 ELF 差异逐条（含 ISO 偏移） |
| `work\builds\GR_AB\evidence\B_huge_face.md` / `.json` | `huge` 面 nrec + `idx ≥ 96` 字符清单 |
| `work\builds\GR_AB\evidence\C_cave_xref.md` / `.json` | cave 落点三类 xref 扫描 |
| `work\builds\GR_AB\evidence\_deep.txt` / `_spframe.txt` | 32 函数 EN|ZH 全文反汇编 / 20 函数栈访问逐条差异 |
| `work\builds\GR_AB\tools\ab_*.py` | 构建与静态分析脚本（全部只读源盘） |
| `work\builds\GR_AB\evidence\VERIFY_BUILDS.md` | ★ 成品盘自检（sha256 / 反汇编回读 / FONT.RES 回读 / 前缀一致性）—— **全部 ✅** |
| `work\builds\GR_AB\README.md` | 目录索引 + 5 张盘 sha256 一览 |

### 交付前自检结果（`python work\builds\GR_AB\tools\ab_verify.py`）

```
AB_00_base            sha ff3abd3c…  diff 0 B      AB_00 == 基底 sha256 : ✅
AB_01_sp222           sha 46571b1b…  diff 1 B      ISO 0x1AD62C: DD→DE ⇒ lbu v0,222(sp)  ✅ 反汇编回读
AB_02_sp221_revert    sha 5b8ac982…  diff 8 B      ⇒ nop ; addiu s0,s0,1               ✅ 反汇编回读
AB_03_fontres_real7k  sha 4275f43c…  diff 1,355 B  MENU/GR 内部 real=7222 / 明文 7222 B /
                                                   前 5,942 B == 基底 ✅ / 尾部 1,280 B 全零 ✅
AB_04_fontres_real5942 sha 331c2351… diff 2 B      MENU#4 + GR#906 real=5942 ✅ 明文与基底逐字节相同 ✅
总判定: ✅ 全部通过
```

---
---

# 附录 A（2026-10-15 追加）— `huge` 面 `nrec` 恢复盘 `GR_HUGE`（**建议插到最前跑**）

> 执行者：汉化执行者（GR_HUGE 打靶子代理）· 2026-10-15
> 盘目录：**`work\builds\GR_HUGE\`**（2 张，各 1,648,164,864 B）
> 详情：`work\builds\GR_HUGE\evidence\HUGE_BUILD_REPORT.md`（构建/字节级）、
> `work\builds\GR_HUGE\evidence\A_HUGE_FACE_TRACE.md`（★ 静态判定：huge 面**会**被选中，含反汇编）、
> `work\builds\GR_HUGE\evidence\VERIFY_HUGE.md`（V1..V9 自检，全部 ✅）
> **只读**了所有既有盘与 PCSX2 配置；未 commit / 未切分支 / 未 merge；**未跑模拟器**。

## A.0 先说三句（它会改变你怎么排测试顺序）

```
① 本节这两张盘打的**不是**"偏移错"，而是**候选 2 的 `nrec` 那一支**：
   `FONT.RES` 的 `huge` 面记录数 96 → 224（= 英文原盘的 224），记录矩形**逐条取自英文原盘**。
   ⇒ `idx < nrec` 对单字节码 0x20..0xFF **恒真** ⇒ 不再进 `slot = idx − 224` 的网格分支
     ⇒ 不再产生负 U0/U1。这是 5 张 AB 盘里**唯一没出、也最该先打**的那一张
     （原指南 §5 第 1 条已把它列为"留给下一轮"）。
② ★ **静态已经判定 `huge` 面会被运行期选中**（原 §5 的"未达成"项结案）：
   `SimHuman::TriggleForBlackCamera`（VA 0x3DEB70）在 `0x3DEFA4` / `0x3DF09C` 两次
   `jal 0x3A17D0`(RSFontMgr::GetFont)，**延迟槽 = `addiu a1,zero,6`** ⇒ `fonts[6]`
   ⇒ 字体名 `huge` ⇒ face = `huge` 面。它画的是 "Player1. : <名>" / "Player2 …" 标签。
   完整链路（"face 指针由**字体名**决定"）见 `A_HUGE_FACE_TRACE.md` §2/§5。
③ ⚠ 但**中文是否流经 huge 面仍未达成**（那两个标签的字面量在汉化盘上仍是纯 ASCII）。
   ⇒ 本盘若**无变化**，先看 §A.4 判定表最后一行，不要直接判"nrec 假设被证伪"。
```

## A.1 两张盘

| 盘 | 改动 | 与基底 `GR_ZH113b.iso` 的逐字节差异 | sha256 | 目的 |
|---|---|---|---|---|
| `HUGE_nrec224.iso` | `FONT.RES`（MENU #4 + GR #906）`huge` 面 **nrec 96→224** + 补齐 224 条记录（rec[96..223] **逐条取自英文原盘**） | **5 run / 2,983 B** | `23ccd11a0e60bcd777e2a89bb863cae4b5eb9c80c5837653aa297855ebcf56f2` | ★ **隔离最强候选**：越界 UV 是否就是元凶 |
| `HUGE_nrec224_plus_s1fix.iso` | 同上 + **S1**：`VA 0x5657E0 / ISO 0x4F9060` `lhu a1,2(t0)` → `lhu a1,0(t0)` | **6 run / 2,984 B** | `b206090240fffc69e625c2a25fab9a00213d244202cbd5dbf49b8a9205c9fb3f` | 一次把 S1 从变量表里划掉 |

逐字节差异清单（相对基底；`*.meta.json` 有全量 hex）：
```
HUGE_nrec224.iso
  ISO 0x0F04EE40     6 B    GR.IMG  #906 FONT.RES 槽头 : 34 05 00 00 36 17 → 60 08 00 00 36 1c
                                                          comp 1,332 → 2,144 ; real 5,942 → 7,222
  ISO 0x0F04EE75  2097 B    GR.IMG  #906 FONT.RES 的 LZO 流（重压涟漪，见 A.5-C3）
  ISO 0x5ECE8120     6 B    MENU.IMG #4  FONT.RES 槽头 : d1 05 00 00 36 17 → f3 08 00 00 36 1c
                                                          comp 1,489 → 2,291 ; real 5,942 → 7,222
  ISO 0x5ECE869A     1 B    MENU.IMG #4  流与补零交界
  ISO 0x5ECE86B0   873 B    MENU.IMG #4  FONT.RES 的 LZO 流（重压涟漪）
HUGE_nrec224_plus_s1fix.iso  = 上面 5 run + ISO 0x004F9060 1 B（02 → 00）
```
> **重建**：`python work\builds\GR_HUGE\tools\hg_build.py`（源盘只读）。
> **自检**：`python work\builds\GR_HUGE\tools\hg_verify.py`（V1..V9，全部 ✅）。
> sha256 已用**两个独立工具**互证（本仓库 `hg_verify.py` 与系统 `Get-FileHash`）。

## A.2 本盘验证什么假设 / 它到底改了什么

| 项 | 内容 |
|---|---|
| **验证的假设** | **候选 2 的 `nrec` 分支**：汉化把 `huge` 面的 nrec 乘数由 **14 改成 6** ⇒ `nrec` 224→96 ⇒ 所有 `idx ≥ 96` 的**单字节码**（= 全部非 ASCII 单字节码，全语料 20,632 个码位 100%）掉进网格公式分支，`slot = idx − 224 < 0` ⇒ 负 U0/U1 ⇒ 逐次踩坏内存 / 布局异常 ⇒ 最终 `dlmalloc` 分配失败 ⇒ NULL ⇒ 死循环 |
| **改了什么（1 个逻辑变量）** | `huge` 面的**记录表恢复成英文原盘形态**：`nrec` 96→224（展开态 `0x123C` 的 u32：6→14），并补上 128 条真记录（1,280 B，逐条取自英文原盘） || **不可避免的连锁** | 明文 5,942→**7,222 B**；内部头 `real` 5,942→**7,222**；`comp` 因重压而变（1,489→2,291 / 1,332→2,144）。这三项**不可分离**（`nrec` 变了就必须有 224 条记录，有记录就必须声明真实长度） |
| **没动什么** | IMG 条目表（`stored` 4,421 / `real` 7,222）、名字区、哈希区、ISO9660、ELF（第一张）、图集 `new_font_revised`（COMMON.PAK）—— **全部逐字节未动**（V6/V8/V9 ✅） |
| 顺带修好的 | 内部头 `real`(5,942) 与 IMG 条目 `real`(7,222) 的**不一致被消掉**（现在三方一致：7,222 = 7,222 = 实际明文长度）⇒ 与 `AB_03` 的混淆见 §A.5-C2 |

★ **与 `AB_03` 构成一次干净的两臂对照**（这是本轮能拿到的最强单变量对照）：
```
AB_03_fontres_real7k : 内部 real 5,942→7,222 + 明文补 1,280 B **零**      （nrec 仍 96）
HUGE_nrec224         : 内部 real 5,942→7,222 + 那 1,280 B 换成**真记录** + ser[5] 6→14
⇒ 两者之差 ≈ `nrec` 这一个变量 ⇒ 先跑 HUGE_nrec224，再跑 AB_03，直接读差值。
```

## A.3 怎么跑（与既有盘同一口径）

```powershell
# 0) 确认模拟器无他人实例（独占资源；发现他人实例只等待、不许杀）
Get-Process -Name '*pcsx2*' -ErrorAction SilentlyContinue |
  Select-Object Id,ProcessName,StartTime

# 1) 用现成 gsrunner 采集器（与本仓库历史轮次同一口径）
python tools\iso_build\fix_zh118_run.py `
  --iso  "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_HUGE\HUGE_nrec224.iso" `
  --tag  "huge_nrec224" `
  --maxframes 0 --snap 0 --timeout 1800 `
  --memcards "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH98\temp\r76\mc_zh" `
  --outroot  "C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_HUGE\runs"

# 2) 跑完数 TLB / 看停顿 PC（日志在运行中被独占，必须等退出后再读）
(Select-String "work\builds\GR_HUGE\runs\dump_huge_nrec224\emulog.txt" -Pattern 'TLB Miss').Count
```
* 时长 ≥ 15 分钟、**与 `AB_00_base` 同一操作序列**（原指南 §2.1 的 ①..④ 循环）。
* ★ **专门要看的触发点**：`TriggleForBlackCamera` 是"黑屏/分屏玩家名"路径 ⇒
  尽量走到 **2P / 分屏 / 玩家名显示 / 进入关卡的黑屏过场**；
  并把**玩家名设成含中文的名字**（若前端允许）——那是把中文塞进 `huge` 面的唯一可控手段。

## A.4 判定表

| 观察 | 结论 | 下一步 |
|---|---|---|
| **本盘不卡，`AB_00` 卡** | ★★ **`huge` 面 `nrec` 假设成立**（越界 UV 就是元凶链的一环） | 正式版直接把 `huge` 面恢复 224 条（本盘做法）；再把 `AB_01`/`AB_02`/S1 逐条排除掉以收尾 |
| **本盘不卡，`AB_03` 也卡** | ★★ **排除"尾部补零/长度声明"的解释**，把功劳归给 `nrec`+真记录 | 同上，且说明 `AB_03` 的零填充不是修复 |
| **本盘不卡，`AB_03` 也不卡** | 两个变量（`nrec` / `real` 对齐）在本地都无法分开 | 再出 §A.6 的 **planB** 盘做第三臂；或直接做"三者对齐 + `nrec` 恢复"的正式版 |
| **本盘仍卡，`AB_00` 也卡** | `nrec` 这一支在本机**无区分度**；若本机本来就复现不出（原 §4-C7），**不能**据此排除 | 转 `AB_01`/`AB_02`（文字链）/ S1 / S2；并把 §A.5 的混淆项一起报 |
| **本盘仍卡，而且卡得比 `AB_00` 更早** | ⚠ 新增记录本身引入新变量（见 §A.5-C4：英文图集布局 vs 汉化图集几何不同） | 先出 **planB** 盘（§A.6）排除记录来源，再下结论 |
| ★ **本盘把 "Player1./Player2" 或某些 UI 字画得更糟/更怪** | 预期内（§A.5-C4）：取回的记录指向**英文图集的布局**，在汉化图集上是"任意字形片段"，且 128 条里 77 条步进宽 = 1 px | **不算坏消息**；改用 planB 盘看外观 |
| **本盘毫无变化（连文字外观都一样）** | 说明 `huge` 面在测试流程里**根本没被用来画任何东西**（很可能是：只有 ASCII 走 huge） | 这本身是结论：`nrec` 分支**不是**本流程的成因 ⇒ 转 `AB_02` 与 S1/S2，并把 `A_HUGE_FACE_TRACE.md` §7.1 的"未达成"一起报 |

> **判定纪律**（沿用原 §3）：一次只改一个变量、同一操作序列、同一时长；
> `TLB Miss` 计数与**首次异常的时间点**要一起给。

## A.5 混淆因素（必须一起报）

| # | 因素 | 说明 |
|---|---|---|
| **C1** | 两张盘**都是汉化盘** | 没有英文对照臂；`AB_00_base` 仍是"汉化基准" |
| **C2** | 本盘**顺带修好了"内部 `real` 与条目 `real` 不一致"**（5,942→7,222） | 这是不可分离的连锁（§A.2）；要分开请用 `AB_03` 做对照臂 |
| **C3** | **LZO 流被重压** | 明文前缀逐字节未变，但压缩流字节序列与原盘不同（2,097 B / 873 B 的"涟漪"）。要排除"引擎对流的隐藏假设"，请与 `AB_03`（也重压过）并列比较 |
| **C4** | ★ **英文原盘与汉化盘的图集几何不同** | `new_font_revised`：EN = **psm 0x13 / 512×512 / 8bpp**，ZH = **psm 0x14 / 1024×512 / 4bpp**（像素字节预算同为 262,144）。取回的记录坐标**落界**（u<512<1024、v<512，成品盘实测 0 条越界）但指向英文布局 ⇒ **外观上是任意字形片段**；128 条里 **77 条步进宽 b1 = 1**（文字会挤） |
| **C5** | 基底上 FONT.RES 的**内部尺寸与 IMG 条目的不一致** | 本盘把它**消掉**了（见 C2）；但 `AB_00`/`AB_01`/`AB_02` **仍带着**这个不一致，跨盘比较时要记住 |
| **C6** | 所有既有盘（含本组）**都继承 S1** | `VA 0x5657E0 / ISO 0x4F9060` 的 `lhu a1,2(t0)`（真偏移错）。`HUGE_nrec224_plus_s1fix.iso` 把它修了；`HUGE_nrec224.iso` **没修** |
| **C7** | 本机复现能力有限 | `docs\REPORT_zh_heap_corruption.md` §4 已定案：gsrunner 复现不出缺页 ⇒ 大概率"本地全 0"，验收重点放在可判定数字 |
| **C8** | `Frame rate: 59.94` 那类行**不是实测帧率** | 是 PCSX2 的 CRTC 配置输出，不得当性能证据 |
| **C9** | 模拟器是**独占资源** | 见原 §6 与 §A.7；并发会把两边 fps 都压到 ~30 |
| **C10** | ★ **中文是否流经 `huge` 面仍未达成** | 已证 `TriggleForBlackCamera` 用 `GetFont(6)` = `huge`，但它画的两个字面量是纯 ASCII；只有拼上的**玩家名**可能带非 ASCII。⇒ "本盘无变化"≠"假设被证伪"（见 §A.4 末行） |

## A.6 建议测试顺序（把新盘插到**最前**）

```
① HUGE_nrec224.iso               ← 本节新盘（最强候选、唯一未打过的变量）
② AB_00_base.iso                 ← 基准（确认本机是否复现；不复现则后面全是 0）
③ AB_03_fontres_real7k.iso       ← 与 ① 的"两臂对照"（只差 nrec + 那 1,280 B 的内容）
④ AB_02_sp221_revert.iso         ← 候选 1 的反证臂
⑤ AB_04_fontres_real5942.iso     ← 候选 2 方向二
⑥ AB_01_sp222.iso                ← 负向对照（预期立刻变坏，用来证实偏移模型）
⑦ HUGE_nrec224_plus_s1fix.iso    ← 只在"①③④ 都卡"时用来划掉 S1
（可选第八臂）HUGE_nrec224_planB.iso —— 见下
```
**理由**：① 隔离的是**唯一没被测过、且静态判定"确实会被选中"**的变量；
它一跑完就能决定后 6 张盘的必要性（若 ① 不卡而 ② 卡，③④⑤⑥ 只剩收尾价值）。
② 必须在 ① 之后立刻跑一次，否则"① 不卡"无法区分"修好了"和"本机没复现"。

**可选第三臂（本轮**未**占盘位，一条命令可出）**：
```powershell
python work\builds\GR_HUGE\tools\hg_build.py --planB      # ⇒ HUGE_nrec224_planB.iso (+ _plus_s1fix_planB)
```
planB 用**基底自己的 `default` 面** rec[96..223] 补全 ⇒ `huge ≡ default`
（因为汉化盘的 `huge` rec[0..95] 与 `default` rec[0..95] **逐字节相同**，即 `huge` 本来就是
`default` 记录表的前 96 条）。它排除 C4（记录来源）与"1 px 步进"这两个副作用，
备料与 sha256 见 `work\builds\GR_HUGE\evidence\planB_meta.json`。

## A.7 本次构建的环境与污染登记（2026-10-15）

| 项 | 状态 |
|---|---|
| 本次是否用了模拟器 | **否**（纯静态 + 只读回读） |
| 期间 pcsx2 进程检查（21:44） | **发现 2 个他人实例**：`pcsx2-gsrunner` PID **18356**（起于 21:44:11）、`pcsx2-qt` PID **19248**（起于 21:44:39） |
| 交付前复查（22:0x） | 剩 **1 个**：`pcsx2-gsrunner` PID **43028**（起于 21:56:50）⇒ 起跑前**必须**再轮询一次到零 |
| 处置 | **只记录，不杀**（纪律：发现他人实例只等待、不许杀） ⇒ **任何人现在起跑都处于并发污染状态**，fps/时序读数不可信 |
| 磁盘 | 新增 2 × 1.6 GB；C: 剩余 **25.29 GB** |
| 写入范围 | 仅 `work\builds\GR_HUGE\**` 与本文档（追加）；既有盘一字未改 |

## A.8 产物索引

| 路径 | 内容 |
|---|---|
| `work\builds\GR_HUGE\HUGE_nrec224.iso` | ★ 主盘（`huge` nrec 96→224，记录取自英文原盘） |
| `work\builds\GR_HUGE\HUGE_nrec224_plus_s1fix.iso` | 主盘 + S1 单字节修复 |
| `work\builds\GR_HUGE\HUGE_nrec224*.meta.json` | 逐字节差异清单 / sha256 / 构建命令 / 取回来源与取回字节 sha256 |
| `work\builds\GR_HUGE\evidence\HUGE_BUILD_REPORT.md` | ★ 构建报告（为什么不是"1~2 字节"、`comp`/`real` 怎么定、连锁项） |
| `work\builds\GR_HUGE\evidence\A_HUGE_FACE_TRACE.md` | ★★ **huge 面是否被选中 = 是**（face 由字体名决定的完整链路 + 9 个 `GetFont` 实参表 + 未达成项） |
| `work\builds\GR_HUGE\evidence\VERIFY_HUGE.md` / `.json` | 成品盘独立自检 V1..V9（全部 ✅） |
| `work\builds\GR_HUGE\evidence\hg1_faces.txt` / `.json` | EN/ZH × MENU/GR 三面记录表全量（224/224/224 vs 224/224/96） |
| `work\builds\GR_HUGE\evidence\hgA5_rsfonts.txt` | FONT.RES 里的 8 个字体（名字/缩放）⇒ index 6/7 = `huge` |
| `work\builds\GR_HUGE\evidence\hgA9_triggle.txt` | ★ `SimHuman::TriggleForBlackCamera` 全文 + `GetFont(6)` 两处 |
| `work\builds\GR_HUGE\evidence\hg2_altplan.txt` / `planB_*.bin` | 替代方案 B 的取证与 1,280 B 备料 |
| `work\builds\GR_HUGE\tools\hg_*.py` | 构建 / 自检 / 静态分析脚本（全部只读源盘） |

## A.9 口径说明（避免和既有文档的"`fld[5]`"打架）

```
`FontDefinition` 在展开态里的 14 个 u32 有**两套编号**，两套都对，只是基准不同：
  文件序 ser[0..13]  = 盘上/内存里 FONT.RES 明文中的先后（= hg1_faces.txt / B_huge_face.md 用的）
  结构序 fld[0..13]  = ReadResourceFile 读进 FontDefinition 之后的字段序
  换算：fld[2]=ser0 fld[3]=ser1 fld[4]=ser2 fld[5]=ser3 fld[0]=ser4 fld[1]=ser5
        fld[12]=ser6 fld[13]=ser7 fld[10]=ser8 fld[11]=ser9 fld[6]=ser10 fld[7]=ser11
        fld[8]=ser12 fld[9]=ser13
  nrec = fld[0]×fld[1] = ser[4]×ser[5]      （自证：0x219590 `mult s6,v1,v0`）
  face[+0x20] = fld[8] = ser[12] = 32 = 0x20（自证：cave `0x417064 lb a1,32(t2)`）
⇒ 既有文档说的"`fld[4]×fld[5]` = nrec"是**文件序**口径（ser[4]×ser[5]），数值一致，不冲突。
```

**`--planB` 分支已用 `--check`（只跑断言、不写盘）验证通过**：
```
[check] HUGE_nrec224_planB             planB=True  s1=False 全部断言通过；未写盘
        MENU comp 1489→1507 ; real 5942→7222 ; 前缀+后缀逐字节未变 ; 取回块 sha256=ac128eb2…065f
        GR   comp 1332→1361 ; real 5942→7222 ; 前缀+后缀逐字节未变 ; 取回块 sha256=d02fae0b…a5af
[check] HUGE_nrec224_plus_s1fix_planB  planB=True  s1=True  全部断言通过；未写盘
[check] HUGE_nrec224                   planB=False s1=False 全部断言通过；未写盘
        MENU comp 1489→2291 ; GR comp 1332→2144 ; 取回块 sha256=8a1db6a3…a7a6（与成品盘一致）
```
（`python work\builds\GR_HUGE\tools\hg_build.py --check` / `--planB --check`；
本轮两个分支都跑过，**没有新增盘**。）


---

# 附录 B（2026-10-16 追加）— 「钩子二分」盘 `GR_HOOK` 与**测试优先级重排**

> 本节**只追加**，不改动本文件 §0–§A.9 的任何既有结论与判定。
> 完整报告：**`docs\REPORT_HOOK_BISECT.md`**；产物：`work\builds\GR_HOOK\**`。

## B.0 三句话（它会改变你怎么排测试顺序）

```
① 框架换了：用户实机测试把方向从"中文字节串太长 / 变长步进"改成
   **"卡死由『文本的更新动作』触发，与串长无关；形态像某个钩子写坏了调用者的栈/局部指针"**。
   ⇒ 本文件 §2.3 的 AB_02（撤销变长步进）与 §A 的 HUGE（huge 面 nrec）**验证的都不是这个框架**。
② 口径修正：任务书说的"35 处文字链改动"与本仓库既有报告的归并口径对不上。
   按 docs\REPORT_NULLDEREF_ZH113b.md §3.5 的同一张函数表逐条相加，
   "每帧都跑的中文文字/字体/UI 渲染链"实际是 **45 处**；
   相对基底 GR_ZH113b 精确重算 = 412 run / 1 850 B / 67 站点，其中
   **49 处钩子**（G1 更新/重绘 13 · G2 测量/排版 10 · G3 字形取址/绘制 14 · G4 其它 12；
   其中 48 处是代码指令，1 处 `kBtnExplanationMapMax` 是数据常量）
   + CAVE 代码体 12 处 + ELF 内 loading 字符串 6 处。
③ 新盘 `HK_01..HK_05` 直接判"钩子是不是元凶"，且二分**闭合**
   （HK_01 = HK_02∪HK_03∪HK_04∪HK_05 的补集）。**先跑 HK_01。**
```

## B.1 五张盘

基底一律 `work\builds\GR_ZH113b\GR_ZH113b.iso`
（sha256 `ff3abd3c50e380f666955ccb6226b67198e181589c0db9b4d52e4643208f6445`）。
**中文文本与中文图集全部保留**，只把 ELF 里的钩子**逐字节写回英文原盘**。

| 盘 | 回退的组 | 站点 | 回退字节 | 差异 | sha256 |
|---|---|---|---|---|---|
| `HK_00_base` | —（**不占盘**，直接用 `GR_ZH113b.iso`） | — | — | — | `ff3abd3c…f6445` |
| **`HK_01_all_text_off.iso`** | G1+G2+G3+G4 | 49 | 238 | 182 B | `9d724ab0ca76ccc452c47e03e37e511b45c7372e147f93ef11302debb56aa5f9` |
| `HK_02_g1_off.iso` | G1 更新/重绘 | 13 | 70 | 57 B | `2df6910deba3d3a78092f12c2622ca660d703284af2d3588b21877a1fc26840a` |
| `HK_03_g2_off.iso` | G2 测量/排版 | 10 | 44 | 40 B | `08935ee05b870c72e51f17c98c5f6927991e62218a14576b93d0e7122e30f528` |
| `HK_04_g3_off.iso` | G3 字形取址/绘制（含 DrawString 序言拦截器） | 14 | 55 | 39 B | `0002e3e4c8cb4efea458940733632ec3d5e8008779bb7ab84e7e3696a2bc161d` |
| `HK_05_g4_off.iso` | G4 其它（含两个名字缩写 cave） | 12 | 69 | 46 B | `a63a3827893c531de88c8675cbd1d1b3e4b5a4171c8094a57daf6648ef4ea46f` |

**跑法与 §2 通用前置完全一致**（确认无他人模拟器实例 → 只等不杀 → 退出后再读日志）。
触发点按用户实测：**火箭筒开火 → 按 L1 开小队/地图 → 选关后进队伍选择界面**。

## B.2 ★ 判定表（每张盘"卡/不卡"分别意味着什么）

| 盘 | **不卡** | **仍卡** |
|---|---|---|
| `HK_01_all_text_off`（49 处钩子全退） | **钩子成立**：元凶在这 49 处里（且不在 CAVE 体与 loading 串里）；**同时说明 CVAR_04 与汉化盘的上游写坏者不同源** → 跑 HK_02..HK_05 四分 | **钩子被排除**：元凶是**文本内容/图集/容器**。**关键动作**：把它的 emulog 与 `work\builds\GR_CVAR\CVAR_04_emulog.txt` 逐项对照指纹 —— 若一致，则两盘**上游同源**，问题回到中文文本数据本身 |
| `HK_02_g1_off` | 元凶在 G1（DrawText/SetText/Flush/Draw/AddOneWord/DisplayMessages/DrawNN/ReadResource/DrawTheString） | G1 无关 |
| `HK_03_g2_off` | 元凶在 G2（度量/换行/坐标） | G2 无关 |
| `HK_04_g3_off` | 元凶在 G3；**因为这一组是唯一包含 `DrawString` 序言拦截器的，若只有它不卡，则该拦截器就是最可能的原因** | G3 无关（连带排除该拦截器） |
| `HK_05_g4_off` | 元凶在 G4；**首选怀疑 `GetActorNameAbbreviated` cave（长度字段读错偏移 ⇒ 拷越过调用者 80 B 帧尾）** | G4 无关 |

组合判定（二分闭合）见 `docs\REPORT_HOOK_BISECT.md` §4.2。

## B.3 ★ 测试优先级（明确重排）

| 优先级 | 盘 | 理由 |
|---|---|---|
| **P0** | **`HK_01_all_text_off`** | 唯一能一刀切回答"钩子是不是元凶"的盘，且同时是"CVAR_04 上游是否同源"的判据。**先跑这一张。** |
| **P1** | `HK_02` / `HK_03` / `HK_04` / `HK_05` | 仅当 `HK_01` **不卡**时才需要，用于四分定位 |
| **P2** | `CVAR` 系列（`CVAR_04_text` / `CVAR_05_elf_atlas`） | 结论已由两轮实机确立（05 不崩 / 04 崩但崩法不同）。只在需要指纹对照时重跑 |
| **P3（降级为背景对照）** | `AB` 系列（`AB_00..AB_04`） | `AB_01`/`AB_02` 验证的是**已被推翻**的 "`sp+221` 变长步进" 假设；`AB_03`/`AB_04` 验证的 FONT.RES `real` 不一致已被 `GR_HUGE` 与 `CAPACITY_2400 §19/20/21` 否掉 |
| **P4（已逻辑排除，不再跑）** | **`HUGE` 系列（`HUGE_nrec224` / `HUGE_nrec224_plus_s1fix`）** | ① 任务书明示已逻辑排除；② `huge` 面 `nrec` 改动**只影响字形索引读**（读越界 ⇒ UV 错误），**只产生读、不产生写**，无法解释"堆元数据 + 调用者栈被**写**坏"这一类写型损坏。**关闭。** |

> 唯一例外：若用户手上只有 `HUGE` 盘可跑，`HUGE_nrec224_plus_s1fix`（它顺手修了
> `GetActorNameAbbreviated` cave 的那 1 个字节）可以**旁证** `REPORT_HOOK_BISECT.md` §1.5 的假设
> —— 但它同时改了 `nrec`，是**混淆变量**，不能单独下结论。**首选仍是 `HK_05`。**

## B.4 本轮新增的两条静态硬结论（详见 `REPORT_HOOK_BISECT.md` §1.4 / §1.5）

1. **★ 真实 ABI 违例（"只恢复不保存"）**：`DrawString` 序言拦截器（`0x219A74 j 0x565930`）
   回到 `0x219A7C`，**永久跳过 `0x219A78 sq fp,144(sp)`**，而尾声 `0x219DC4 lq fp,144(sp)`
   **每次都执行** ⇒ 每次 `RSFontMgr::DrawString` 返回时 `$fp`(=$s8，被调用者保存寄存器)
   被从"本次调用从未初始化过的栈槽 sp+144"重新载入。
   **受害面**：全 ELF 只找到 1 个符号在调用后仍读 `$fp` —— `LoadingLoagoThread`（读盘进度循环当计数器用）。
   **⇒ 与用户的三个触发点对不上**，所以它不是（至少不是全部）卡死的解释。
2. **★★ 头号可疑钩子换人**：`GetActorNameAbbreviated` 的 cave（`0x5657C8`，站点 #42，G4）
   把 `lhu a1,2(t0)`（**应为 `0(t0)`**）当长度交给 `0x565760`，返回的长度直接作为
   `jal 0x53E2B0(dst=sp+56, src=s0+68, n=v0)` 的**拷贝字节数**；而该函数帧只有 **80 字节**
   （缓冲在 sp+56 ⇒ 只剩 24 B 余量）⇒ **长度一旦非 0 且 > 24，就会写越过调用者帧尾**。
   它落在**队伍选择界面**这条用户实测触发路径上，而且**汉化自己发布的 `GR_ZH113b_fix`
   全盘只差 1 个字节 —— 修的就是这一条**（`2(t0)` → `0(t0)`）⇒ 这是**已发生的缺陷**，不是理论风险。
   **本打靶基底 `GR_ZH113b` 上它仍是错的**；该站点被 **HK_01 与 HK_05** 覆盖。

## B.5 与既有盘的混淆项关系（新增登记）

| 混淆项 | 影响哪些盘 | 说明 |
|---|---|---|
| **S1**（`GetActorNameAbbreviated` cave 的 `lhu a1,2(t0)`） | `AB_*`、`HUGE_*`、`HK_02`/`HK_03`/`HK_04` **全部继承**；`HK_01`/`HK_05` **已回退** | 既有 `AB_TEST_GUIDE.md` §4 已登记 S1；本附录补上"`HK_01`/`HK_05` 覆盖它"这一事实 |
| **中文渲染退化** | `HK_01`..`HK_05` **全部** | 钩子回退后中文走英文单字节路径 ⇒ **花屏/乱码/错位是预期现象，不是盘坏了**。判据只有"卡死/不卡死" |
| **未跑模拟器** | 本轮全部 | 按任务书要求，本轮**没有启动任何 PCSX2 进程** ⇒ 未新增污染 |

## B.6 产物索引

| 路径 | 内容 |
|---|---|
| `work\builds\GR_HOOK\HK_01_all_text_off.iso` … `HK_05_g4_off.iso` | 5 张打靶盘 |
| `work\builds\GR_HOOK\HK_00_base.meta.json` | `HK_00` 指路（不占盘） |
| `work\builds\GR_HOOK\HK_xx*.meta.json` | 逐字节差异清单 / sha256 / 尺寸 / 构建命令 / 自检 |
| `work\builds\GR_HOOK\README.md` | 打靶盘速查 |
| `work\builds\GR_HOOK\evidence\hk_sites.md` | 67 站点全表 + 运行时机分组 + 逐条栈/ABI 判定 |
| `work\builds\GR_HOOK\evidence\hk_dump.txt` / `hk_fp.txt` / `hk_fplive.md` | 钩子反汇编 + `$fp` 取证 + 受害者扫描 |
| `work\builds\GR_HOOK\evidence\hk_pc_symbols.txt` | 两份 emulog 的故障 PC 归属与集合对比 |
| `work\builds\GR_HOOK\evidence\hk_verify.md` / `hk_disc_tables.md` | 5 张盘独立复核 / 逐站点清单 |
| `work\builds\GR_HOOK\tools\hk_*.py` | 全部脚本（既有 ISO 只读） |
| `docs\REPORT_HOOK_BISECT.md` | ★ 完整报告 |

---

# 附录 C（2026-10-16 追加）— 「哨兵」对照盘 `GR_SENT` + **全局测试优先级终版**

> 本节**只追加**，不改动本文件 §0–§B.6 的任何既有结论与判定。
> 完整报告：**`docs\REPORT_SENTINEL.md`**；产物：`work\builds\GR_SENT\**`。
> 基底一律 `work\builds\GR_CVAR\CVAR_04_text.iso`（sha256 `554d3d8b…a15179`，只读未改）。

## C.0 三句话（它会改变你怎么排测试顺序）

```
① 框架再收窄：用户已论证「内容驱动、与长度无关」，前一位留下两个高权重候选但没有盘位。
   本批把它们做成**可实测的盘**——候选 R（0xB1/0xB5 图标哨兵）**两个方向各一张**：
     · SENT_02（代码侧：关掉 ELF 里 8 处硬编码特判，文本一字不动）★ 先跑这张
     · SENT_01（数据侧：把 3 个容器里 730 处哨兵 trail 整对搬到安全对偶码）
   外加 {LANG,XML}×{改,不改} 的 2×2 闭合（SENT_03 / SENT_04）。
② ★ 本轮新证据（决定了这两张盘为什么值得跑）：
   · 原盘 DrawString **每条分支都只前进 1 字节**（bnel 的两条边各 +1）⇒ 原盘**没有 2 字节解码**，
     中文对偶码是**逐字节**画的 ⇒ 每个 LANG 容器的**全部 314 个 0xB1/0xB5 字节**都撞特判
     （不只 286 个 trail）。这同时更正了 `REPORT_TEXT_OVERFLOW.md` §2.3 的 `i+=2 else i+=1` 读法。
   · DrawString 里的硬编码立即数有 **8 处**（不是 6 处），且 **`RSFont::CharWidth` 也硬编码
     这两个字节（命中无条件返回 20）** —— 后者 **SENT_02 没关**（受"最多 4 张"限制）。
③ 四张盘全部通过独立终检（sha256 / 允许区外 0 run / 容器长度不变 / 条目 1:1 /
   **替代表口径下逐条解码不变**）；判定表见 `REPORT_SENTINEL.md` §5。
```

## C.1 四张盘

基底 `work\builds\GR_CVAR\CVAR_04_text.iso`；尺寸一律 1,648,164,864 B。

| 盘 | 改了什么 | 差异 | sha256 | 目的 |
|---|---|---|---|---|
| **`SENT_02_icon_path_off.iso`** | 只改原盘 ELF：DrawString 里 **8 处** `addiu rX,zero,0xFFB5/0xFFB1` → `…,0xFF00`（−256，符号扩展字节永不可能等于） | **8 run / 8 B** | `7935b5fff78963960a275198a793ca5b5ecb0e94ebc31b1fbccb468a233817f7` | ★ **单变量、版式中性**：关掉图标特判路径 |
| `SENT_01_trail_fix.iso` | 3 容器 **730 处**哨兵 trail 整对搬移（LANG 286+286 / XML 158）；文本一字未换 | 1106 run / 82,403 B | `9e0ae5ee3c66944ed28c17393c088ee87268d7ec653937b1d127c9e4edf863a5` | 数据侧：盘上不再有哨兵形态 |
| `SENT_03_xml_only.iso` | 只搬 XML 158 处（LANG 原样） | 370 run / 31,634 B | `71bab00375f668cbe75cbb8cebaddc12c7d56582dda99b79413eca54129c2274` | 2×2：哪份容器贡献 |
| `SENT_04_lang_only.iso` | 只搬两个 LANG 286+286 处（XML 原样） | 736 run / 50,769 B | `4f078fc80e3232e546f7c551d0ae66735c5f81a37806e0cad20936653b19af59` | 2×2：同上 |

**跑法与 §2 通用前置完全一致**（确认无他人模拟器实例 → 只等不杀 → 退出后再读日志）。
触发点按用户实测：**火箭筒开火 → 按 L1 开小队/地图 → 选关后进队伍选择界面**。

**预期现象（设计内，不是坏盘）**：四张盘**都仍是"原盘图集 + 中文文本" ⇒ 中文一定是乱码**
（CVAR_04 本来就查不到中文字形）；`SENT_01/03/04` 的乱码图案与 CVAR_04 略有不同
（被搬移的 32 个字的两个字节都换了格子，字距变窄约 6~10 单位）；
`SENT_02` 画面应与 CVAR_04 几乎逐像素相同，唯一可见差别是原本画成 △/✕ 图标的位置改画普通乱码字形。
**判据只有一条：卡死 / 不卡死。**

## C.2 ★ 判定表（`REPORT_SENTINEL.md` §5 的浓缩版）

| 观察 | 结论 |
|---|---|
| **`SENT_02` 不卡**（CVAR_04 卡） | ★★ **候选 R 成立**：元凶是 DrawString 对 `0xB1/0xB5` 的硬编码特判（硬编码 UV + `AddOneWord(flag=1)` 副包）；**与文本长度完全无关**（文本一字未动） |
| `SENT_02` 仍卡、**`SENT_01` 不卡** | 哨兵**作为数据**是元凶，但**不是**走 DrawString 图标路径 ⇒ 下一个怀疑对象 = **`CharWidth` 对这两个字节的硬编码 20**（本轮新发现，`SENT_02` 没关；第 5 张盘 = 再加 2 字节，ISO `0x1AE5B8`/`0x1AE5CC`） |
| **两张都不卡** | "引擎对 `0xB1/0xB5` 的特判"整体成立，修复取**最便宜的一条**（代码侧 8 字节） |
| **两张都仍卡** | ★★ **候选 R 被排除**（两个方向都堵住）⇒ 长度与哨兵都被排除 ⇒ 转 `TXT_01/TXT_03/TXT_02` 与 `REPORT_SENTINEL.md` §B（候选 C，需实机写监视 `RSString+2`） |
| `SENT_03`（只修 XML）不卡 | 贡献者是 **XML**（特殊功能界面文本） |
| `SENT_04`（只修 LANG）不卡 | 贡献者是 **两个 LANG 容器**（菜单/HUD/选项） |
| `SENT_03`/`SENT_04` 都仍卡而 `SENT_01` 不卡 | 两份容器**各自都能独立触发** ⇒ 修复必须覆盖全部 3 个容器 |

## C.3 ★ 全局测试优先级（把前几轮产物一起排）

| 优先级 | 盘 | 为什么在这个位置 |
|---|---|---|
| **P0** | **`HK_01_all_text_off`**（`GR_HOOK`） | 唯一能一刀切回答"**49 处钩子是不是元凶**"的盘，且同时是"CVAR_04 与汉化盘上游是否同源"的判据。**仍未跑过 ⇒ 仍是第一优先** |
| **P1** | **`SENT_02_icon_path_off`**（本批，8 字节） | 改 8 字节、**版式中性**、直接判候选 R 的**代码侧**；跑完立刻决定 `SENT_01/03/04` 还有没有必要 |
| **P1** | `SENT_01_trail_fix`（本批） | 数据侧对照臂；与 `SENT_02` **两臂互证**（一个关代码、一个清数据，指向同一个机制） |
| **P2** | `SENT_03_xml_only` / `SENT_04_lang_only` | 2×2 容器二分；只在 P1 出现"卡/不卡不一致"或需要定位到容器时才需要 |
| **P2** | `TXT_01_short` / `TXT_03_len_eq_en` / `TXT_02_orig_text`（`GR_TXT`） | 「长度」这条线的两侧夹逼盘。**若 `SENT_*` 有明确结论，这三张降为交叉验证**；若 `SENT_*` 全卡，它们重新升为 P1（`REPORT_TEXT_OVERFLOW.md` §5 判定表第 4/7 行） |
| **P3** | `HK_02` / `HK_03` / `HK_04` / `HK_05` | 仅当 `HK_01` **不卡**时才需要（四分定位） |
| **P3** | `CVAR_04_text` / `CVAR_05_elf_atlas` | 结论已由两轮实机确立（05 不崩 / 04 崩）；只在需要**指纹对照**时重跑。`CVAR_04` 同时是本批四张盘的**共同基底** |
| **P4（降级为背景对照，不必跑）** | `AB_00..AB_04`（`GR_AB`） | `AB_01`/`AB_02` 验证的是**已被推翻**的 "`sp+221` 变长步进"框架；`AB_03`/`AB_04` 的 FONT.RES `real` 不一致已被 `GR_HUGE` 与 `CAPACITY_2400 §19/20/21` 否掉 |
| **P5（关闭，不再跑）** | `HUGE_nrec224` / `HUGE_nrec224_plus_s1fix`（`GR_HUGE`） | ① 任务书明示已逻辑排除；② `huge` 面 `nrec` 改动**只影响字形索引读**（读越界 ⇒ UV 错误），**只读不写**，无法解释"堆元数据 + 调用者栈被**写**坏"；③ 用户 `CVAR_04`（原盘 FONT.RES，huge nrec=224 完整）照样崩 ⇒ 独立排除。**关闭** |

> **唯一例外**：`HUGE_nrec224_plus_s1fix` 顺手修了 `GetActorNameAbbreviated` cave 的那 1 个字节，
> 可作 `REPORT_HOOK_BISECT.md` §1.5 的**旁证**；但它同时改了 `nrec`，是混淆变量，不能单独下结论。

## C.4 本轮新增的混淆项（登记，必须与结果一起报）

| # | 因素 | 影响哪些盘 |
|---|---|---|
| **D1** | `SENT_01/03/04` 会**轻微改变版式**（`0xB1/0xB5` 字距硬编码 20，任何替代码 ≤18/≤16 ⇒ 32 个字各降 6~10 单位；`Σ|ΔW|` large 329 / default 362 / huge 29） | 数据侧三张盘；**`SENT_02` 不受影响**（版式中性臂） |
| **D2** | `SENT_02` **只关了 DrawString 的 8 处**，没关 `CharWidth` 的 2 处硬编码 | `SENT_02`（若它仍卡，先怀疑这条，见 C.2） |
| **D3** | XML 里另有 **8 个哨兵字节**在 `<item name="…">` 属性值里，本批**没清**（只清 `<text>`，与既有 158/34 口径一致） | `SENT_01` / `SENT_03` |
| **D4** | 两个 LANG 容器各 28 个**裸图标字节**一律保留（英文原盘同样 28 个，是故意的图标占位） | 四张盘**全部** |
| **D5** | `SENT_01/03/04` 的"解码不变"依赖**项目侧替代表**（32 条 `新对偶码→原字`）；它在 **CVAR_04 成立**（那里没有中文字形），在**汉化盘 `GR_ZH113b` 上不成立** | 数据侧三张盘：**只能用来判因，不能当最终修复** |

## C.5 产物索引

| 路径 | 内容 |
|---|---|
| `work\builds\GR_SENT\SENT_01..04*.iso` / `.meta.json` | 四张盘 + 逐字节差异清单 / sha256 / 构建命令 / 自检 / 逐处哨兵清单 / 替代表 |
| `work\builds\GR_SENT\summary.json` | 四张盘一览 |
| `work\builds\GR_SENT\audit\C_verify.txt` | ★ 独立终检（从盘上重读；四张全 ✅） |
| `work\builds\GR_SENT\audit\A_sentinel_scan.*` / `B_refcount.txt` / `_*_orig.txt` | 哨兵普查 / 候选 C 调查 / 原盘反汇编取证 |
| `work\builds\GR_SENT\tools\sent_*.py` | 全部脚本（既有 ISO 只读） |
| `docs\REPORT_SENTINEL.md` | ★ 完整报告（机制 / 盘 / 判定表 / 修复路径预案 / 未达成项） |

---

## D. ★ 哨兵 trail **修复盘**（`GR_HASHR2400`）—— 数据侧修复 + 「未修盘」对照

> 完整报告：`docs\REPORT_SENTINEL_FIX.md`；速查另见 `docs\CVAR_TEST_GUIDE.md` §9。
> 本节是 C 章的**收口**：C 章那四张是"判因盘"（改的是 CVAR_04 原盘引擎族），
> D 章这两张是"**修复盘 + 未修对照**"（都是 2,400 字汉化盘，单变量只差哨兵 trail）。

### D.0 三句话

1. 用户已定案根因：汉化把汉字对偶码的 **trail** 做成了 `0xB1/0xB5`，撞上引擎的硬编码图标特判
   （`AddOneWord(...,flag=1)` 容量 2 副包）⇒ 逐字符写坏内存。本章的盘就是**把 trail 全部避开**。
2. 修复盘只改三样（charset 码位 / 42 个字形搬家 / 3 容器 738 处 2 字节替换），
   **几何·闸门·图集尺寸·FONT.RES·IMG 条目表·字符序列全部不动** ⇒ **版式零影响**。
3. 交付 B（`GR_ZH113b` 的同一修复）**在"不改闸门"下无解**（鸽笼：安全槽 1,472 < 需编码 1,502），
   已停手上报；三条备选见报告 §6.3。

### D.1 两张盘

| 盘 | 路径 | sha256 | 与谁单变量 |
|---|---|---|---|
| **修复盘** `GR_HASHR2400` | `work\builds\GR_HASHR\GR_HASHR2400.iso` | `c9986ad294a2aa94a95b47b0f294b5303d13642c8f53adfa619f6a22f9ba5582` | 只比 K2 多"哨兵 trail 重排" |
| **未修对照** `GR_FA2400_K2` | `work\builds\GR_FA2400_K2\GR_FA2400_K2.iso` | `c3851c1d7eb361e3aa8ab8cea36b0ac6d3915c291e695ec77adf4b6316265e94` | 天然基线 |

### D.2 静态读数（判据已全绿，不需要实机就能核）

| 判据 | 读数（从盘上重读，`work\builds\GR_HASHR\audit\verify.txt`）|
|---|---|
| 3 容器「作为对偶 trail 的 0xB1/0xB5」| **738 → 0** |
| charset「trail ∈ {B1,B5} 的登记」| **50 → 0** |
| 3 容器**逐条**解码字符序列 | 5,019 条**全部一致**（不符 0）|
| 逐字节差异 | 全部是登记在案的"旧哨兵码 → 新码"2 字节替换（越界 0）|
| 有字形槽（dump_font）| **1,877 → 1,877**；缺字形 473 → 423（保留槽单列）|
| 被搬 42 字字形 | 新格 == 基底旧格 **逐 texel 42/42** |
| 图集三闸门 + 两条不变式 | 全过（px_size 329,744、w·h/2 % 2048 = 0、格位互不重复）|
| 全盘差异 | 83,067 B，**窗口外 0 B**；ISO 尺寸不变 1,648,164,864 |

### D.3 怎么跑

```powershell
$env:PY = "C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $env:PY work\tools\cap_run.py --iso work\builds\GR_HASHR\GR_HASHR2400.iso `
      --dump work\builds\GR_HASHR\runs\hashr2400 --nav tools\capture\nav_menu_only.txt `
      --maxframes 6000 --snap 30 --wait-first
```
手动验收清单（**≥20 分钟**，见 `REPORT_SENTINEL_FIX.md` §7.3）：同一关反复进 / 火箭筒开火 /
L1 / 队伍选择 / 存读档 ≥5 轮 / 特别收录长正文 / △✕ 图标 / 拉丁文可读。

### D.4 ★ 判定表

| # | 修复盘 | 未修 K2 | 结论 |
|---|---|---|---|
| 1 | 不卡 | 卡 | ★★ trail 修复有效 ⇒ 推广；（B 的容量问题另议）|
| 2 | 卡 | 卡 | trail 不是（唯一）病因 ⇒ 转**代码侧** 8 字节臂（`DrawString` 立即数 → 永不命中）|
| 3 | 卡得更早 | — | 非单调 ⇒ 停测回报，先回滚 charset 备份 |
| 4 | 不卡 | 不卡 | 环境/时序敏感 ⇒ 看可判定数字（同帧最长段 / TLB 簇 / 停顿 PC），不看卡不卡 |

### D.5 新增混淆项

| # | 因素 | 说明 |
|---|---|---|
| **D6** | 修复盘的 42 个字**换了槽位**（字形逐 texel 相同）| 若某汉字显示异常 ⇒ 报出具体字 + 截图（属"搬家搬错"）|
| **D7** | 钩子开启时 trail **不进入**图标特判（反汇编补证 `REPORT_SENTINEL_FIX.md` §1.3）| 判定表 #2 出现时的解释；代码侧臂是下一步 |
| **D8** | charset/登记表已更新为**新盘口径** | 处理旧盘要加 `--charset work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr` |
| **D9** | 交付 B 未出盘 | 需要 B 的对照请先裁决报告 §6.3 的 B-1/B-2/B-3 |

### D.6 产物索引

| 路径 | 内容 |
|---|---|
| `work\builds\GR_HASHR\GR_HASHR2400.iso` | ★ 修复版 2,400 字成品盘 |
| `work\builds\GR_HASHR\audit\verify.txt` | 独立终检（判据 1/2/3/4/6）|
| `work\builds\GR_HASHR\audit\moves_table.txt` | 逐字符新旧码对照表 + 槽位账 |
| `work\builds\GR_HASHR\temp\GR_HASHR2400_build.json` | 构建报告（差异窗口 / 逐容器命中 / 断言日志）|
| `work\builds\GR_HASHR\backup\*.before_hashr` | charset / gate_pairs 改前备份 |
| `docs\REPORT_SENTINEL_FIX.md` | ★ 完整报告 |



