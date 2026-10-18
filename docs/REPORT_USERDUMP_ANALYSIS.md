# REPORT_USERDUMP_ANALYSIS — 用户真机双 dump 现场分析（桶 126 是谁写坏的）

* 轮次：GR_USERDUMP（纯离线取证，未运行任何模拟器）
* 输入：用户用带钩子的 Qt 版在真机上抓的两份 dump + 一份 live emulog
* 产出目录：`work\builds\GR_USERDUMP\**`（tools / out / evidence）
* 纪律：只读用户 dump / 既有产物 / ISO / `third_party\**`；写入仅本目录与本文档。未 commit / 未切分支 / 未 merge。
  * 事后核对（`git status --porcelain`）：`?? docs/REPORT_USERDUMP_ANALYSIS.md` 是本次唯一新增的受版本控制文件；`work/**` 被 `.gitignore:61` 忽略，故 `work\builds\GR_USERDUMP\**` 不出现在 git status 里。
  * 工作树里另有 4 个 `M`（`tools/diag/dump_all_text.py`、`tools/font_pipeline/data/charset_compiled_zh16.json`、`tools/text_csv/inject_text_csv.py`、`tools/text_csv/tcslib.py`）**不是本次改动**：它们的 mtime 都是 2026-10-15，早于本会话（2026-10-18 10:54）。本次从未写入这些路径。
* 污染记录：分析期间用户自己的 `pcsx2-qt.exe`（pid 45040，起于 2026-10-18 10:45:30，命令行 = `...\qt\pcsx2-qt.exe ...\GR_LAYOUT\LAY_fix1_bytecount.iso`）一直在运行，`qt\logs\emulog.txt` 被它持有写锁（426 秒时 `VMManager Pausing...`，即用户按了暂停）。**本会话从未对该进程做任何操作**（只读命令行 + 只读文件），所有分析在私有目录内完成。

---

## 0. 结论速览（TL;DR）

| 问题 | 答案 |
|---|---|
| 两份 dump 分别是什么状态 | **旧（frame 19701）= 健康**；**新（frame 23444）= 已退化**（桶 126 槽已被写坏）。判据 = `ee_ram.bin` 的 `0x0055BB98/9C` |
| 桶 126 槽值 | 旧 `0x0055BB88/0x0055BB88`（空桶自指，健康）；新 `0x6ED47823/0x6ED47823`（**越界垃圾，整个 32 MB RAM 只出现在这两个槽**） |
| 那条 store 抓到了吗 | **没有**。损坏发生在帧 **(19701, 22436]**，而两份 ring 分别只覆盖 `18995..19700` 与 `22437..23443`，**没有任何一份覆盖损坏窗口**，两份 ring 里对 `0x55BB98/9C` 的写记录都是 **0 条** |
| 写者身份（反汇编判定） | **分配器自己**，不是外来野写：`free()`（`0x00101D10`）大块路径的**插入 bin 双写** `sw C→bin->fd`（`0x00102010`）+ `sw C→bin->bk`（`0x00102014`）——钩子 ring 报的 PC 是 `0x00102014 / 0x00102018`。判定依据：两份 ring 共 **206,830** 条桶数组写，**写者 PC 无一例外全部落在 `0x00101C00..0x00102700` 分配器镜像内**；且 `fd == bk == 单元素` 这一形态只能由"往空桶插入"产生，摘链无法产生 |
| 卡死机理（已逐条对齐反汇编验证） | `malloc(nb=0x10020)` → `idx = 110+(nb>>12) = 126` → 从 `0x0055BB9C` 取链头 = `0x6ED47823` → `ld 8(C)`=TLB Miss `0x6ED4782B` → `lw 0x14(C)`=TLB Miss `0x6ED47837` → 读到 0 → `v=0` → 之后永远 `ld 8(0)`/`lw 0x14(0)`（日志里 `pc=0x1024d0 addr=0x8` 与 `pc=0x102584 addr=0x14` 无限交替）= **卡死**。**注意：malloc 永不返回，所以 OOMFIX 那种"NULL 返回安全网"救不了这个死循环** |
| 归因（是否汉化数据造成） | **未判定**。已排除"坏值直接来自盘上数据"（`0xA73D37F0` 在 1.6 GB ISO 里 0 命中）；并且**英文原盘同样会出现桶 126 坏**（同一 `fd==bk==非 chunk` 形态）。现有证据不足以归因汉化，也没有证据说"与汉化无关" |

---

## 1. 素材清点（路径 / 大小 / 时间 / sha256）

完整清单见 `work\builds\GR_USERDUMP\evidence\INVENTORY.txt`。摘要：

### 1.1 旧 dump = `hook_19701_hotkey_f10`（2026-10-18 10:51:13）

| 文件 | 字节 | sha256 |
|---|---|---|
| `ee_ram.bin` | 33,554,432 | `A6948E314EBB9FF752B486F9AE8629D0C6644D1AFDB371C4AF8EDFF994989223` |
| `iop_ram.bin` | 2,097,152 | `0B66E42225036B769C7F5BA6A37D2F89FD38BE28A1AAC33E701DBE11A04F6894` |
| `meta.txt` | 1,146 | `3179439B7676F4901A49CB285CE784FB6E8699A27EA347C4CAB5CBACA84C87BA` |
| `regs.txt` | 38,741 | `1E53B9789ABB627CE295F1BA3ED5383E2D30F39155FBCEBDB979B9E759F40D92` |
| `ring.bin` | 6,291,456 | `C21C3A90867B0525A6BB45FE0265F8BF99EF37DDC9E0F07DF1EBA1FE5BD08221` |
| `ring.txt` | 14,306,522 | `1D4ECD668D530B8F5983CA3E9059A4F28ECFC9144A50432B09F2CBA4D997603D` |
| `watch_00500000_00581000.bin` | 528,384 | `48FF5861E7FE42A9C5335D537BE0FF7B837F61489F6A45C02790319B9D38A5FE` |

### 1.2 新 dump = `hook_23444_hotkey_f10`（2026-10-18 10:52:33）

| 文件 | 字节 | sha256 |
|---|---|---|
| `ee_ram.bin` | 33,554,432 | `758A4F646177E2856E60E217C5021498ACA0850C95460999671AF53CF431B965` |
| `iop_ram.bin` | 2,097,152 | `71B2013E35FF3D932F6A820E0F9CB66196A2E87D8F6DB99D680CBDBFE78BAAE9` |
| `meta.txt` | 1,146 | `4FA8608FDEA8482D0E99EC8EA9A2003A07A6FEE1FD0549F83E72961741F2235F` |
| `regs.txt` | 38,742 | `0E959BB108EB090A3AF25EBE03331A16B7FF368081E336C32DA82E5CD625F7DE` |
| `ring.bin` | 6,291,456 | `8599734371FB85338F7BF32317B9F179BBF004AB30E72511BC170A36D7EFB71C` |
| `ring.txt` | 14,306,564 | `EE5E138F08A84F33E1833939BE4B43182D5030C04C5C3DCC6C78FC3D2D15018D` |
| `watch_00500000_00581000.bin` | 528,384 | `83DBBD544085F6154C51E83009C24E55927C80EF5F348170203F4AA00D71DAE7` |

### 1.3 日志

| 文件 | 字节 | 备注 |
|---|---|---|
| `qt\logs\emulog.txt` | 444,549（快照时） | **被运行中的 `pcsx2-qt.exe` pid 45040 持有写锁，`Get-FileHash` 报 FileReadError（文件正由另一进程使用）**。改用"共享读快照"取证：`evidence\emulog_snapshot_2026-10-18.txt`，sha256 = `4A95B1E9C08594E7758F40CBF8991DABCB9CA17B7A99E7A4D989D37BBF1BF6FA`（444,549 B） |

### 1.4 ring 记录格式（本轮实测确认）

`ring.bin` 每条 **24 B**（小端，按时间升序，`ring.txt` 首行是表头、共 262,145 行 = 1+262,144）：

```
+0x00 u32 frame   +0x04 u32 pc   +0x08 u32 addr   +0x0C u64 value
+0x14 u8 size_bits(32/64/128)  +0x15 u8 pad  +0x16 u8 dir('W'=0x57)  +0x17 u8 src
```

校验：`ring.bin` 前 3 条与 `ring.txt` 前 3 行（`0 22437 00102014 0055BAA8 32 W 0 0000000001991A70` …）逐字段一致（见 `tools\g2_ringfilter.py` 的 `--check` 输出 `out\g2_*_check.txt`）。

---

## 2. A. 两份 dump 的对齐与状态判定

### 2.1 触发记录（`meta.txt` + `emulog.txt`）

| 项 | 旧 dump | 新 dump |
|---|---|---|
| 触发原因 | `reason=hotkey_f10`（用户按 F10 手动抓） | 同 |
| 帧号 | **19701** | **23444** |
| 触发时刻（emulog） | `[343.0386] F10 pressed (frame 19701) -> dumping` | `[423.4241] F10 pressed (frame 23444) -> dumping` |
| `ring_entries_total` / `written` | 5,103,987 / 262,144 | 6,203,287 / 262,144 |
| ring 覆盖帧区间（实测） | **18995 .. 19700** | **22437 .. 23443**（区间内**每帧都有**记录，无空洞） |
| `arm_mode` / watch | `4` / `00500000-00580000` | 同 |
| `trigger_pcs` | 12 个：`00101D10 00101DD8 00101DE4 00101E08 00101E34 00101E6C 00101FE0 00102000 00102008 001024D0 001024E8 00102584` | 同（本次未触发，12 个 PC 触发默认关） |
| 武装时刻 | `[1.5094] HookWatch: ARMED (reason=elf_loaded frame=6): watch=active -> 129 page(s) on the slow RAM handler` | 同一次运行，同一条 |
| 挂载的 ELF / CRC | `cdrom0:\SLUS_206.13;1`，`Initializing Elf: 37453732 bytes`，`CRC: 7A761FCA`，`entry=0x00100008` | 同一次运行 |

**两份 dump 来自同一次运行**（同一份 emulog 里只有这两次 `F10 pressed`），新 dump 之后 4.06 s（帧 ≈ 23645）发生致命卡死。

**top writer PC 排行**（emulog 原文）：

* 旧：`HookWatch: top writer PCs (59 unique, showing up to 20): 0040574Cx141118 00101EECx24859 00101EFCx24859 001020C0x21665 00101F00x9464 001020C8x8190 00102250x2590 0010224Cx2590 004039A0x2112 00101E24x1837 00101E20x1837 0010257Cx1272 004147D0x1092 00414CE8x1092 00414CECx1092 00414CF0x1092 00414CE4x1092 00414DC0x1092 00101DE4x1030 0010227Cx910`
* 新：`HookWatch: top writer PCs (55 unique, showing up to 20): 0040574Cx84115 00101EECx34573 00101EFCx34573 001020C0x28372 00101F00x18078 001020C8x15063 0010224Cx3350 00102250x3350 004039A0x3018 0010257Cx2960 00101E20x2357 00101E24x2357 00101DE4x1621 00102580x1599 004147D0x1544 00414CE8x1544 00414CE4x1544 00414CECx1544 00414CF0x1544 00414DC0x1544`

> `00101EEC/00101EFC/00101F00/001020C0/001020C8` 等就是分配器（见 §4 反汇编）；`0040574C` 是往 `0x00561640` 连续写伪随机 dword 的非分配器代码（新 ring 里 84,115 次），`004039A0/00414CE8/004147D0` 写 `0x00570140-0x00570190` 一带。它们都在桶数组（`0x0055B7A8`）之外，**从不写桶数组**（见 §5.4）。

### 2.2 状态判定：直接读 `ee_ram.bin` 的桶 126 槽

命令（`tools\g1_buckets.py`，输出 `out\g1_buckets.txt` / `.json`）：

```
python work\builds\GR_USERDUMP\tools\g1_buckets.py
```

自指公式**逐字按 `docs\REPORT_HEAP_EXHAUSTION.md` §1.2** 核对：
`桶 i 的伪 chunk = 0x0055B798 + 8*i`，`fd 在 0x0055B7A8+8*i`、`bk 在 0x0055B7AC+8*i`；空桶 ⇔ `fd == bk == 伪 chunk`。
对 `i=126`：伪 chunk = `0x0055B798 + 0x3F0` = **`0x0055BB88`**，fd 槽 = `0x0055BB98`、bk 槽 = `0x0055BB9C`。（用户题面里"`0x55BB84`"是笔误；正确值 `0x0055BB88`，与 `REPORT_HEAP_EXHAUSTION.md` 及其 `EVIDENCE_bin126.txt` 一致。）

| dump | `0x0055BB98` | `0x0055BB9C` | 判定 |
|---|---|---|---|
| 旧（f19701） | `0x0055BB88` | `0x0055BB88` | **健康**（空桶自指） |
| 新（f23444） | `0x6ED47823` | `0x6ED47823` | **坏**（>32 MB 物理 RAM 上界；单元素链） |

原始字节（`out\g1_buckets.txt`）：

```
旧 0x0055BB90: 80 BB 55 00 80 BB 55 00 88 BB 55 00 88 BB 55 00   <- 125 fd/bk, 126 fd/bk
新 0x0055BB90: 80 BB 55 00 80 BB 55 00 23 78 D4 6E 23 78 D4 6E   <- 126 fd/bk = 0x6ED47823
```

**独立第二来源交叉核对**：`watch_00500000_00581000.bin`（同一 dump 目录里的被监视区原始快照）在 `0x55B7A0 / 0x55B7A8 / 0x55BB98 / 0x55BB9C / 0x55BBA4` 五点与 `ee_ram.bin` 逐字节一致，新 dump 该文件里桶 126 fd/bk 同样是 `0x6ED47823`（`out\g4_crosschecks.txt` §[4]）。

**全 RAM 唯一性**：`0x6ED47823` 这个 4 字节值在 32 MB 里**只出现 2 次**，就是 `0x0055BB98` 与 `0x0055BB9C`（`g1_buckets.txt`，重叠加窗扫描）。⇒ 它不是从 RAM 别处拷来的，是"写进去/算出来"的。（上一轮 `0xA73D37F0` 也是同样的唯一性。）

### 2.3 A→B 逐 store 差分成不成立（最重要的负面结论）

题面设想的"最有价值情形"= 两份 dump 的时间跨度覆盖损坏窗口 ⇒ 逐 store 差分。**实际不成立**：

```
旧 ring 覆盖帧 18995..19700   （旧 dump 本身在 19701，健康）
新 ring 覆盖帧 22437..23443   （新 dump 本身在 23444，已坏）
⇒ 窗口 (19701, 22436] 共 2735 帧，两份 ring 都没有覆盖
```

窗口上界还能进一步收紧：第一次出现"分配器拿着野指针在跑"的症状在 **帧 ≈ 22094–22098**（emulog `[394.7071..394.7083]`，前后最近的 `frame=` 分别是 22094 与 22098）。所以损坏窗口 = **(19701, 22094]**（约 2394 帧 ≈ 51 s），仍然完全没有 ring 覆盖。

于是：**A→B 的"逐 store 差分"未达成**；能做的差分是"逐桶 + 逐块的状态差分"（见 §5），以及被 ring 覆盖区间内的"写者全集"统计（见 §3.4 / §5.4）。

---

## 3. B. 找出"写坏桶 126 的 store"

### 3.1 B1 — ring 里所有写到整个桶数组的记录

筛法：对每条记录按宽度 `size/8` 展开，取与 `[0x0055B7A8, 0x0055BBA8)` 相交者。命令：

```
python work\builds\GR_USERDUMP\tools\g2_ringfilter.py     # 全量清单 -> out\g2_OLD_f19701.txt / out\g2_NEW_f23444.txt
python work\builds\GR_USERDUMP\tools\g3_bucketwriters.py  # 按 PC/槽位/值类别归类 -> out\g3_*.txt
```

| dump | ring 记录 | 命中 mstate+桶数组区（含 `0x55B7A0..0x55BBA8`） | 命中桶 126 槽 `0x55BB98/9C` | 命中值 `0x6ED47823` | 命中地址 `0x6ED4782B/823` |
|---|---|---|---|---|---|
| 旧 | 262,144 | **108,715** | **0** | 0 | 0 |
| 新 | 262,144 | **160,100** | **0** | 0 | 0 |

**结论：两份 ring 里都没有"写桶 126 槽"这条 store**（含 64/128 位宽跨槽的情况；§3.3 已按宽度展开判定）。这也和"空桶长期自指、无人写它"一致——`out\g3_NEW_f23444.txt` 的桶写直方图里，本窗口有写的桶是 `1,4,6,8,…,118`，**最高只到 118**；旧窗口最高只到 125（写的是 bin125 的 fd，`0x55BB90`，不是 126）。

### 3.2 B2 — "第一条把桶 126 槽写成非自指值的 store"

**未直接在 ring 中取得**（原因见 §2.3）。下面是可给出的最强定位：

* 该 store 一定发生在 **(19701, 22094]** 之间；
* 它把 `0x0055BB98` 与 `0x0055BB9C` **两个槽同时**写成同一个值 `0x6ED47823`（⇒ 桶 126 在写入前是**空**的，写入后是**单元素**链，fd 与 bk 同指这一个 chunk）；
* 症状首次可见帧 ≈ **22094–22098**：emulog 该次 TLB-miss 风暴的地址集合里已经出现 `0x6ED4782B(=C+8)`、`0x6ED47833(=C+0x10)`、`0x6ED47837(=C+0x14)`，即分配器已经在按"chunk 基址 = `0x6ED47823`"访问它；
* 结合 §4 反汇编，这条（对）store 的指令是
  `0x00102010  ace50010  sw $a1, 16($a3)` → **`bin->fd = C`**
  `0x00102014  ad250014  sw $a1, 20($t1)` → **`bin->bk = C`**
  （`t1` = 桶 126 的伪 chunk `0x0055BB88`，`a1` = C = `0x6ED47823`；当桶空时 `a3 == t1`）
  钩子把这两条 store 报成 PC `0x00102014` / `0x00102018`（**钩子的 ring `pc` 字段存在 ±4 的取址偏差**，见 §4.4）。

### 3.3 B3 — 写者身份判定：分配器内部，不是野写

**(a) 值形态判定（与 PC 无关的判据）**

| 形态 | 是否与现场一致 | 说明 |
|---|---|---|
| 往**空桶**插入（`bin->fd = C; bin->bk = C`） | ✅ `fd == bk == C` | 唯一能一步产生"两槽同值"的写法 |
| 摘链最后元素（`FD->bk=BK; BK->fd=FD`，`FD=BK=bin_pseudo`） | ❌ | 只会把两槽写回 `pseudo`（= 变回空桶），旧 ring 里 `0x1021BC/0x1021C0` 对桶 118 就是这个行为 |
| 摘链（`C->fd->bk=C->bk`）单侧落进桶槽 | ❌ | 只能改**一个**槽，且另一个槽保持原值；要两槽都变 `C` 需要巧合 |
| 外来越界野写（把数据盖到桶数组） | ❌ 形态不符 | 野写一般是"一片连续地址被数据样值覆盖、多个桶同时坏"。上一轮记录过这种真野写案例（`zh_7A36E0B1`：`bins_broken=13`，一堆桶被 `0x0098xxxx` 数据样值覆盖，桶 126 是 `fd=0x81EA7113 / bk=0x0096B1FC` **两槽不同值**）；本次新 dump **只有桶 126 一个桶坏，且两槽同值** |

**(b) 写者 PC 全集判定（决定性）**

对两份 ring 里**所有**触及 `0x55B7A0..0x55C000`（mstate + 整个桶数组 + 填充）的记录统计写者 PC：

```
OLD : addr range touched 0x0055B7A0..0x0055BB90 ; 37 distinct PCs
      PCs OUTSIDE the allocator image 0x00101C00..0x00102700 : NONE
NEW : addr range touched 0x0055B7A0..0x0055BB60 ; 33 distinct PCs
      PCs OUTSIDE the allocator image 0x00101C00..0x00102700 : NONE
```

（`out\g4_crosschecks.txt` §[6]）⇒ 在 206,830 条桶数组写样本里，**非分配器代码从不写这片内存**。野写假设没有任何正面证据。

**(c) 反汇编：写者所在函数与寄存器链**

ELF：`work\builds\GR_CULPRIT\elf\LAY_fix1_bytecount_SLUS_206.13.elf`（37,453,732 B）。**与用户这次跑的是同一份代码**：emulog 里 `isoFile open ok: ...\GR_LAYOUT\LAY_fix1_bytecount.iso`、`Initializing Elf: 37453732 bytes`、`CRC: 7A761FCA`，与该 ELF 的文件大小一致，且与 `docs\REPORT_HEAP_EXHAUSTION.md` 用的是同一份。

反汇编命令（本轮自己重跑，不用有 bug 的 `work\tools\cave_dis.py`）：

```
python work\builds\GR_CULPRIT\tools\dis2.py work\builds\GR_CULPRIT\elf\LAY_fix1_bytecount_SLUS_206.13.elf diso 0x101D10 0x102050
python work\builds\GR_CULPRIT\tools\dis2.py work\builds\GR_CULPRIT\elf\LAY_fix1_bytecount_SLUS_206.13.elf diso 0x102050 0x1026C0
```

产物：`out\dis_101D10_102050.txt`、`out\dis_102050_1026C0.txt`、`out\dis_101C00_101D10.txt`。

`0x00101D10` = **`free(mstate, chunk)`**（调用点 `0x00102034`: `jal 0x00101D10`，`a0=0x0055B7A0`(mstate)，`a1=user_ptr-16`；与 `REPORT_HEAP_EXHAUSTION` 的 `chunk = prev_foot(8)+head(8)+fd@0x10+bk@0x14` 布局一致）。关键片段（原字 + 指令）：

```
00101d10  dcaa0008  ld $t2, 8($a1)        ; C->head -> size
00101d24  8c870008  lw $a3, 8($a0)        ; a3 = mstate->top
00101d34  00a63021  addu $a2, $a1, $a2    ; a2 = C + size (next)
00101d38  dcc90008  ld $t1, 8($a2)        ; next->head
00101d40  14c70017  bne $a2, $a3, +23     ; next != top ? -> 合并/插链
...
00101da0  31490001  andi $t1, $t2, 0x1    ; PREV_INUSE
00101da4  1520000f  bne $t1, $zero, +15 -> 0x00101DE4
00101dac  dcac0000  ld $t4, 0($a1)        ; C->prev_foot  (未做合法性校验!)
00101db8  000c503c  dsll32 $t2, $t4, 0
00101dbc  000a503f  dsra32 $t2, $t2, 0    ; 取低 32 位并符号扩展
00101dc0  00aa2823  subu $a1, $a1, $t2    ; P = C - prev_size   <-- 野指针在这里产生
00101dc4  8caa0010  lw $t2, 16($a1)       ; P->fd
00101dc8  15490003  bne $t2, $t1, +3 -> 0x00101DD8   ; P->fd != 常量($t1=0x0055B7A0, 由 0x101DB0/DB4 得到)
                                                     ;   => 认为 P 是个真正挂在链上的空闲块，去摘链
                                                     ;   （不相等时才摘链；相等则只累加 prev_size）
00101dd8  8ca90014  lw $t1, 20($a1)       ; P->bk
00101ddc  ad490014  sw $t1, 20($t2)       ; P->fd->bk = P->bk    <- 野写（NULL 时落到 0x14）
00101de0  ad2a0010  sw $t2, 16($t1)       ; P->bk->fd = P->fd    <- 野写（NULL 时落到 0x10）
...
00101e94  2c610200  sltiu $at, $v1, 512   ; 小块/大块路径分叉
00101f40..00101f6c                        ; 由 size 算桶号 t2（含 addiu $t2,$zero,126）
00101fcc  8d290010  lw $t1, 16($t1)       ; 大块桶内按 fd 走，找插入点
00101fe0  dd260008  ld $a2, 8($t1)
00101ff4  1480fff5  bne $a0, $zero, -11   ; 继续走
00102000  8d270014  lw $a3, 20($t1)       ; a3 = t1->bk
00102008  aca70014  sw $a3, 20($a1)       ; C->bk = a3
0010200c  aca90010  sw $t1, 16($a1)       ; C->fd = t1
00102010  ace50010  sw $a1, 16($a3)       ; a3->fd = C   >>> 桶空时 a3==bin_pseudo -> bin->fd = C
00102014  ad250014  sw $a1, 20($t1)       ; t1->bk = C   >>> bin->bk = C
00102018  03e00008  jr $ra
```

大块桶号推导（`0x001020E4..0x00102154`，逐条对上 `REPORT_HEAP_EXHAUSTION` §1.3）：
`v1 = nb>>9`；`v1<5 → idx=(nb>>6)+56`；`<21 → (nb>>9)+91`；`<85 → (nb>>12)+110`；`<341 → (nb>>15)+119`；`<1365 → idx=126`；否则 `(nb>>18)+124`。
`nb = 0x10020` ⇒ `nb>>9 = 128 < 341` ⇒ **`idx = (0x10020>>12)+110 = 16+110 = 126`**。

**(d) C 是从哪来的**：`0x00101DC0` 的 `P = C - (int32)C->prev_foot`。这条链上的 chunk 基址不是调用者直接传进来的"合法空闲块"，而是**由 C 自己头部里的 `prev_foot` 字段算出来的**——所以一旦某个块的 `prev_foot`/`head` 被踩坏（被游戏数据覆盖、或前一次错误合并写坏），分配器就会自己"造"出一个越界基址，再把它当空闲块**摘链 + 插链**。帧 ≈22094 的 TLB-miss 记录正好是这个式子：`C1 = 0x6E6A338`，`C2 = 0x6ED47823`，`C2 − C1 = 0x6FD4EB`（= 从 `C1->prev_foot` 低 32 位符号扩展出来的 `prev_size` 的相反数）——**`C2` 与 `C1` 的差正是那个"尺寸"**。这就是题面提到的"把尺寸当成指针"那一类错误的同族：**"尺寸/前块尺寸"参与了 chunk 基址运算，而该字段已不可信**。

### 3.4 关于"不是外来野写"的补充证据

* 若真是"某处越界写把数据盖到桶数组"，通常会**同时**破坏相邻字节/相邻桶。实测：新 dump 里 `0x0055BB88` 之前（`0x0055BB80-0x0055BB87` = 桶 125 fd/bk）与之后（`0x0055BBA0-0x0055BBA7` = 桶 127 fd/bk）**都是完好的自指值**；`0x55B7A0/0x55B7A4/0x55B7A8/0x55B7AC`（mstate 头）也正常。
* 唯一性扫描：`0x6ED47823` 全 RAM 只在这两个槽。
* 写者全集：206,830 条桶数组写全部来自 `0x00101C00..0x00102700`。

---

## 4. 卡死链条：逐条对齐反汇编（本轮新证据）

这条链在 `REPORT_HEAP_EXHAUSTION` 里被记过症状（"`pc=0x1024d0/0x102584` 死循环"），本轮把它与**桶 126 的坏值**逐指令接上了：

```
001024a8  2459fff0  addiu $t9, $v0, -16   ; t9 = 桶 126 伪 chunk = 0x0055BB88
001024c0  8f220014  lw $v0, 20($t9)       ; v0 = *(0x0055BB9C) = 桶 126 bk = 0x6ED47823  <<<
001024c4  50590033  beql $v0, $t9, ...    ; 桶空则跳过（这次不空）
001024d0  dc4b0008  ld $t3, 8($v0)        ; 读 C->head  = 0x6ED4782B  -> TLB Miss
001024d4  016dc024  and $t8, $t3, $t5     ; size = head & 0x1FFFFFFE
001024d8  03055823  subu $t3, $t8, $a1    ; size - nb
001024e0  1580001b  bne $t4, $zero, +27 -> 0x00102550
00102550  0560000c  bltz $t3, +12 -> 0x00102584   ; size < nb -> 取下一个
00102584  8c420014  lw $v0, 20($v0)       ; v0 = C->bk = 0x6ED47837 -> TLB Miss, 读到 0
00102588  1459ffd1  bne $v0, $t9, -47 -> 0x001024D0   ; v0(0) != 桶哨兵 -> 回到 0x1024D0
```

`v0` 变 0 之后：`0x1024D0` 读 `addr=0x8`、`0x102584` 读 `addr=0x14`，两者都 TLB Miss，返回值使 `v0` 保持 0，`bne` 永远成立 ⇒ **无限循环**。live emulog 原文：

```
[  427.4814] TLB Miss, pc=0x1024d0 addr=0x6ed4782b [load]     <- 第一次踩到坏链
[  427.4816] TLB Miss, pc=0x102584 addr=0x6ed47837 [load]     <- 读到 0
[  427.4816] TLB Miss, pc=0x1024d0 addr=0x8 [load]            <- 之后永远这两条
[  427.4817] TLB Miss, pc=0x102584 addr=0x14 [load]
...（无休止，直到 434.72 s 用户暂停）
```

**这就是"按 L1 即卡死"的现场**：L1 触发了某个 64 KB 量级的资源分配（`nb = 0x10020`，对应 `REPORT_HEAP_EXHAUSTION` 里记录的 65,552 B 资源），分配器走到唯一的 64 KB 桶（126）→ 踩上早已埋好的坏链 → 死循环。时间对得上：F10 dump 在 `[423.4241]`（帧 23444），卡死在 `[427.4814]`（帧 ≈23645），相隔 4.06 s。（emulog 不记录按键事件，所以"用户按了 L1"是**时间推断**，未直接取证。）

### 4.1 与 `REPORT_CULPRIT_STORE.md` 的差异（本轮修正）

`REPORT_CULPRIT_STORE.md` 的致命链是"`malloc` 拿 NULL → 写地址 0 → 砸异常向量 → Trap/自陷"。**本次现场的最后一跳不是这个**：

* 两份 dump 的低 4 KB（`0x0000..0x0400`，EE 异常向量页）**逐字节完全相同**（`g4_crosschecks.txt` §[1]：`00 1A 2B 0F 0E 09 EA 07 00 1F 2B 0F 0E 09 EA 07` …），两态非零字节数都是 411/1024；`0x20` 起还是 `BASLUS-20613GHOST002` 存档头模板。⇒ 没有任何东西写进去过。
* 分配器在 `0x101DDC/0x101DE0` 经 NULL 指针写 `0x14/0x10` 时，那两次 store **本身就是 TLB Miss**（`[394.7074] ... addr=0x14 [store]` / `addr=0x10 [store]`）——**这些写没有落地**。
* 所以本次的致命一跳是**"malloc 内部的桶链遍历永不返回"**，不是"返回 NULL 后调用者写 0"。

**这一点对修法影响很大**：`OOMFIX`（见 `docs\REPORT_OOMFIX.md`）是"`malloc` 返回 NULL 时的安全网"，**它救不了本次这种死在 `malloc` 里面的死循环**。见 §6.3。

---

## 5. B4 — 交叉核对（`ee_ram.bin` 全堆遍历）

命令：`python work\builds\GR_USERDUMP\tools\g4_crosschecks.py` → `out\g4_crosschecks.txt`

### 5.1 堆账目（按 `REPORT_HEAP_EXHAUSTION` 的 `base=0x0065AEA0` 起走）

| 项 | 旧 f19701 | 新 f23444 |
|---|---|---|
| heap_base | `0x0065AEA0` | `0x0065AEA0` |
| top（`0x55B7A8`） | `0x01A47BB0` | `0x01A47BB0`（**没动**） |
| heap_end | `0x01F98020` | `0x01F98020` |
| heap_total | 26,464,640 | 26,464,640 |
| chunks_total | 42,732 | 42,744 |
| 已用（used%） | 20,544,576（**77.63 %**） | 20,539,200（**77.61 %**） |
| 空闲块数 | 51 | 58 |
| 桶数组越界/未对齐项 | **0** | **2**（都是桶 126） |
| 桶项不指向任何 chunk 起点 | **0** | **2**（都是桶 126） |

⇒ 两态之间堆顶、堆界、总容量**完全没变**，甚至"已用"还略降；变化的只有 12 个 chunk 的正常增删 + **桶 126 的两个槽**。

### 5.2 因果核对：桶 126 坏值 ↔ 那条 store

* 坏值 `0x6ED47823` 是 4 字节整值，全 RAM 唯一命中就是这两个槽（重叠扫描，`g1_buckets.txt`）⇒ 与"某条 store 直接写入"一致，**不是**从别处 memcpy 来的。
* 该值满足 `fd == bk`（单元素链）；且在 `0x0055BB98..0x0055BB9F` 之外没有任何其他被破坏的桶数组字节 ⇒ 写者是"精确写这两个 4 字节槽"的代码，而不是溢出。

### 5.3 其它桶/其它结构有没有被同一写者破坏

* 桶数组：只有 126 坏；`0x55B7A0-0x55B7AC`（mstate 头）正常；桶 0 的别名（`0x55B7A8`=top、`0x55B7AC=0x0055B798`）正常。
* 除桶 126 外，**254 个桶项（127 桶 × fd/bk）在两份 dump 里全部指向真实 chunk 起点**（`[3b] entries NOT equal to any chunk start: 0 / 2`）⇒ 野写常见的"成片坏"没有出现。
* 被监视区其余部分（`0x500000-0x581000`）：`0x00561640`（`0040574C` 在写的伪随机 dword 序列）与 `0x00570120-0x00570190`（`004039A0/00414CE8/004147D0/00414DC0` 等）在两份 dump 里都存在且地址固定，**不是**本次损坏的来源。
* 由同一"坏尺寸/坏 prev_foot"引起的**第二个**受害点确实存在：帧 ≈22959（`[413.2266]`）分配器又在处理另一个野指针 `0x14E228EF`，同一次还碰到 `0x6ED4782B/0x6ED47837`（= 桶 126 那个坏块）。⇒ 坏状态是**持续存在并会反复被踩**的，不是一次性事件。

### 5.4 ring 覆盖区间内"谁写桶数组"的完整名单（两 dump）

| PC | 角色（对照反汇编） | 旧计数 | 新计数 |
|---|---|---|---|
| `00101EEC` | `0x101EE8 sd`：mstate+0 桶位图（`0x55B7A0`） | 24,859 | 34,573 |
| `00101EFC` | `0x101EF8 sw`：**小块插入** `bin->fd = C` | 24,859 | 34,573 |
| `00101F00` | `0x101F00 sw`：小块插入 `bin->bk = C`（空桶时） | 9,464 | 18,078 |
| `001020C0` | `0x1020BC sw`：小块摘链 `FD->bk` | 21,665 | 28,372 |
| `001020C8` | `0x1020C4 sw`：小块摘链 `BK->fd` | 8,190 | 15,063 |
| `0010224C/00102250` | 桶 1 的一对插入写 | 2,590 / 2,590 | 3,350 / 3,350 |
| `00101E20/00101E24` | 空桶插入的一对写 | 1,837 / 1,837 | 2,357 / 2,357 |
| `00101DE0/00101DE4` | `0x101DDC/DE0` 与 `0x101DF0..` 摘链/复位 | 396 / 1,030 | 622 / 1,621 |
| **`00102014/00102018`** | **大块（≥512 B）插入 `bin->fd = C` / `bin->bk = C`** | **173 / 157** | **47 / 48** |
| `00102530/00102534` | 大块摘链/切分相关一对 | 910 / 494 | 1,505 / 772 |
| `0010253C/00102538` | 同上 | 910 / 910 | 1,505 / 1,505 |
| `0010257C/00102580` | 空闲块合并复位一对 | 1,272 / 432 | 2,960 / 1,599 |
| `001021BC/001021C0` | malloc 大块摘链 `FD->bk / BK->fd` | 5 / 5 | 2 / 2 |
| `00101D74/00101D78` | 与 top 合并时摘前块的链 | 2 / 2 | 0 / 0 |
| 其它 20 余个 | — | 见 `g4_crosschecks.txt` | — |

大块插入对 `00102014/00102018` 的实测样本（旧 ring，`out\g5_ring_excerpts.txt`）——正好演示它平时写的是**合法 chunk 指针**：

```
f=19021 pc=00102014 addr=0055BAC0 val=0x00A3FC70  -> bin 99 fd
f=19021 pc=00102018 addr=0055BAC4 val=0x00A3FC70  -> bin 99 bk
f=19021 pc=00102014 addr=0055BAE8 val=0x00A3FC70  -> bin 104 fd
f=19506 pc=00102014 addr=0055BB70 val=0x01A47BB0  -> bin 121 fd
f=19506 pc=00102014 addr=0055BB88 val=0x01A6AE70  -> bin 124 fd   (注意 0x55BB88 同时是桶126伪chunk=桶124fd槽)
```

新 ring 里同一对写到的最高桶是 **118**（帧 23244 / 23365）。旧 ring 最高到 **124**。**两份 ring 都没有写到 125/126/127**——这既解释了"为什么这条 store 没被抓到"，也说明 64 KB 级分配确实罕见（`REPORT_HEAP_EXHAUSTION` 也记过：425 帧内 0 次）。

---

## 6. C. 完整因果链 + 修法建议 + 归因

### 6.1 完整因果链

```
[起点] free() 的合并路径用不可信的"前块尺寸/块头"字段算 chunk 基址
       0x00101DC0  P = C - (int32)C->prev_foot        <- 没有范围校验
       （帧 ≈22094 实测：C1=0x6E6A338，prev_foot 低32位符号扩展 = -0x6FD4EB
         ⇒ P = C2 = 0x6ED47823，越界 1.8 GB）
   ↓
[写坏] 分配器把这个越界指针当空闲块插进它"自称"的尺寸类桶
       同一帧 free() 走到大块插入尾 0x00102008..0x00102014：
       0x00102010  bin->fd = C2   (0x0055BB98 = 0x6ED47823)
       0x00102014  bin->bk = C2   (0x0055BB9C = 0x6ED47823)
       ⇒ 桶 126（唯一的 ≥64 KB 桶）从此挂着一条指向 RAM 外的链
   ↓
[潜伏] 帧 22094→23443 之间，桶 126 两个槽再无写入（ring 实测 0 条）
       期间分配器至少两次踩到它（帧≈22094、帧≈22959），每次都在
       0x101DDC/0x101DE0 经 NULL 写 0x14/0x10（TLB Miss，未落地）
   ↓
[幻觉分配] 用户按 L1 → 请求 nb=0x10020 → idx = 110+(nb>>12) = 126
       malloc 大块搜索 0x1024C0: v = *(0x0055BB9C) = 0x6ED47823
       0x1024D0  ld 8(v)  -> TLB Miss 0x6ED4782B
       0x102584  lw 0x14(v) -> TLB Miss 0x6ED47837，读到 0
   ↓
[卡死] v = 0 且循环无 NULL 检查：0x1024D0 ld 8(0) / 0x102584 lw 0x14(0) 无限交替
       （emu 里就是 TLB-miss 风暴 + 画面不动 = 用户看到的"卡死"）
```

与既有结论的接法：`REPORT_HEAP_EXHAUSTION.md` 的"桶 126 坏 + 幻觉分配"在本轮得到**用户真机现场**的确认，并补上了两处新东西：① 坏值 `0x6ED47823`（不是上一轮的 `0xA73D37F0`，说明坏值是**每次会话各自产生的垃圾**，不是固定常量）；② **本次没有走 `REPORT_CULPRIT_STORE.md` 的"malloc 返回 NULL → 写 0 → 砸向量"分支**，而是死在 malloc 内部（低 4 KB 两态逐字节相同可证）。

### 6.2 修法站点表

ELF 文件偏移换算：单一 `PT_LOAD va=0x00100000 off=0x00000080` ⇒ `off = VA − 0x00100000 + 0x80`。（ISO 内 LBA/扇区偏移**未达成**，因为 `SLUS_206.13` 在 ISO 里的 extent 需要走 `GR_LAYOUT` 的 iso 布局工具；本轮只给 ELF 内偏移。原字均取自本轮反汇编，可直接 `verify_sites.py` 核对。）

| # | 站点 VA | ELF off | 原字 | 新字（建议） | 理由 | 风险 |
|---|---|---|---|---|---|---|
| **F1（首选：堵住野指针来源）** | `0x00101DC0` | `0x20C0` | `00aa2823  subu $a1,$a1,$t2` | 把这 4 字节改成 `j <cave>`（cave 内：先 `subu $a1,$a1,$t2`，再校验 `heap_base ≤ $a1 < heap_end && $a1%8==0`；合法则 `j 0x00101DC4` 继续，不合法则 `j 0x00101DE4` 跳过前块合并，可选落一条日志） | 病灶是"用不可信的 `prev_foot` 造出越界 chunk 基址"。这一处堵住后，越界指针**不会**再被插进桶 | 需要 cave（本工程已有 cave 机制）+ 保存/恢复 `$at`（或改用 `$t3` 等本路径未用寄存器）；改变了"前块合并"行为，理论上有内存碎片增加的副作用，需回归 `OOMFIX_TEST_GUIDE` 的场景 |
| **F2（配套：堵住 next 方向）** | `0x00101D38` / `0x00101D40` | `0x2038` / `0x2040` | `dcc90008  ld $t1,8($a2)`<br>`14c70017  bne $a2,$a3,+23` | 在 `a2 = C + size`（`0x00101D34`）之后加同样的范围校验；`a2` 越界则按"next 已到堆顶"处理 | 同一函数里 `C + size` 也是用不可信 `size` 算的 | 同上 |
| **F3（喂坏指针的调用点，若有）** | 未知 | — | — | **未达成**：真正让 `prev_foot/head` 变脏的写（或第一次 `free(野指针)`）落在 ring 未覆盖的 `(19701,22094]`，本轮没有抓到 | 这是"更好的修法"（修调用点），但需要下一轮把 ring 拉长或改成"只记录 `0x55B7A0..0x55BBA8` + `0x00101D00..0x00102700` 的写" | — |
| **F4（安全网 A：桶链自检）** | `0x00102588` | `0x2588` | `1459ffd1  bne $v0,$t9,-47` | 改成三指令（进 cave）：`sltiu $at,$v0,0x02000000` / `beq $at,$zero,<bail>` / `bne $v0,$t9,-47`；`bail` 走"这个桶没有可用块"的既有出口（继续找下一个桶或返回 0） | **直接杀掉本次的死循环**：链头掉出 RAM 就不再自旋。这是最小、最保险的一处 | 只治症不治因：坏值仍在桶里，其它路径（`0x101FCC` 的插入点搜索、`0x1021B0` 的摘链）仍会踩；且 `bail` 后返回 0 需要 `OOMFIX` 之类的调用侧兜底 |
| **F5（安全网 B：摘链前置校验）** | `0x00101DC4`/`0x00101DC8` | `0x20C4`/`0x20C8` | `8caa0010  lw $t2,16($a1)`<br>`15490003  bne $t2,$t1,+3` | 在 `0x00101DC8` 的判定里追加 `P` 与 `P->fd/P->bk` 的范围检查 | 防止"经 NULL/野指针写 0x14/0x10"（虽然本次没落地，但换台机器/TLB 配置不同就可能落地砸向量） | 同 F4，属兜底 |
| **F6（可选：插链前校验）** | `0x00102010`/`0x00102014` | `0x2010`/`0x2014` | `ace50010  sw $a1,16($a3)`<br>`ad250014  sw $a1,20($t1)` | 写入前检查 `a1` 在 RAM 内且 8 对齐，否则不插链（丢弃该块 + 打日志） | 这是**真正写坏桶 126 的那两条 store**；在这里拦最直接 | 会掩盖 F1/F2 的病灶，只能当观测/计时炸弹保险，不宜单独作为修复 |

**优先级建议**：F1+F2（治因，需 cave）> F4+F5（治症，最小改动，能立刻消掉"卡死"）> F6（观测用）。

### 6.3 与既有 `OOMFIX` 的关系

* `OOMFIX`（`docs\REPORT_OOMFIX.md`）是"**`malloc` 返回 NULL** 之后的调用侧安全网"（防止解压器把 NULL 当缓冲区写地址 0）。
* 本次现场的失败模式是"**`malloc` 在桶链里自旋，永不返回**"（§4），`OOMFIX` 的钩子点根本执行不到 ⇒ **互补，不替代，且对本病灶无效**。
* F4/F5 属于"`malloc`/`free` **内部**的指针合法性安全网"，与 `OOMFIX` 形成两层：内层保证分配器不会自旋/不会经野指针写；外层保证即使分配失败，调用侧也不会把 NULL 当缓冲区。两者叠加才覆盖"坏桶"与"真 OOM"两类失败。
* 补充：如果只上 F4（桶链自检）而不上 F1/F2，则坏桶仍在，`malloc` 会在该桶"找不到块"→ 继续找更大桶 → 走 top 切分路径；那时**才会**出现 `malloc` 返回 NULL，**这才是 `OOMFIX` 生效的场景**。所以 F4 + OOMFIX 是一个自洽的最小组合。

### 6.4 归因问题：这次损坏是否与"汉化数据（更大的图集/文本、gate 0xBA 布局）"有关？

**答：未判定。** 下面是据以判断的全部证据（正的、负的都在）。

| # | 证据 | 指向 |
|---|---|---|
| E1 | **坏值不是固定常量，而是每次会话各自产生的垃圾**。既有 audit 里至少 5 个不同值：`0xA73D37F0`（`c05_*`/`r06_*`/`u223_state`/`zh_7A361F8D`）、`0x00AFB670`（`zh_7A361FB5_s02`）、`0xAED3902D`（`zh_7A361FB7`）、`0x6ED47823`（`zh_7A361FCA` 与**用户本次**）、`0x81EA7113/0x0096B1FC`（`zh_7A36E0B1`，另一类野写）。 | 说明坏值来自运行期状态，不是盘上某个字段被直接读出来当指针 |
| E2 | **`0xA73D37F0` 在 1.6 GB 的 `LAY_fix1_bytecount.iso` 里 0 命中**；`0x6ED47823` 命中 2 次（文件偏移 `0x4A046530`、`0x5875AC34`），`0x6E6A338` 命中 1 次（`0x50870294`）。在 1.6 GB 里随机命中某 4 字节模式的期望 ≈0.38 次，故 2 次属于**背景噪声量级**，且未定位于任何汉化数据文件。 | **不支持**"坏值直接来自汉化后的盘上数据" |
| E3 | **英文原盘同样会出现同一个坏桶**：`work\builds\GR_HEAP\evidence\audits\ENG_3E571E91.json` → `bin 126 fd=0x00ACEA20 bk=0x00ACEA20`，`problems=["0x00ACEA20 is not a chunk start"]`（同一"单元素 + 两槽同值 + 非 chunk 起点"形态）。同一批 audit 里英/汉两版都既有"坏"也有"干净"的态（`ENG_3E571E95`、`zh_7A361FB5` 干净）。 | **不支持**"这是汉化独有缺陷"；机制在原生数据上就能触发 |
| E4 | **堆账目汉化/英文没有系统差异**：`heap_total` 全部 = 26,464,640；同场景 `used_pct` = 用户旧 77.63 / 用户新 77.61 / `ENG_3E571E91` 77.61 / `ENG_3E571E95` 77.79 / 汉化各态 77.51–77.92（不同场景的两份是 70.5/70.6，与版本无关）。 | **不支持**"汉化让堆更紧张、更早退化"（至少本场景本时点看不出） |
| E5 | 两份 dump 的 `heap_base / top / heap_end` 逐字节相同（`0x0065AEA0 / 0x01A47BB0 / 0x01F98020`），两态之间"已用"只差 5,376 B，`chunks_total` 只差 12。 | 桶 126 变坏**没有**伴随堆布局/容量的变化 ⇒ 不是"汉化把堆撑爆" |
| E6 | 坏值在**相邻构建的不同会话**里出现过同一个值（`zh_7A361FCA`（CRC `7A361FCA`）与用户本次（CRC `7A761FCA`）都是 `0x6ED47823`），但同一批里其它构建/会话又各不相同。 | 说明它**可能是确定性的**（同一场景同一流程产生同一个垃圾），但也可能只是同源构建的巧合；**仅凭这一点既不能证明也不能排除汉化参与** |
| E7 | 上一轮的对照（`docs\REPORT_HEAP_EXHAUSTION.md` §2.2 明确写"要归因必须做同场景两版对照，未达成"）在本轮**仍未达成**；且 `%LOCALAPPDATA%\PCSX2\sstates\` 里**没有**用户这次构建（CRC `7A761FCA`）的旧存档可比。 | 归因所需的"同场景汉化 vs 英文"定量对照缺失 |

跨会话/跨构建的完整对照表（26 个既有 audit）见 `work\builds\GR_USERDUMP\out\g5_prior_audits.txt`。

⇒ 结论：**未判定**。要做归因，下一轮需要的最小实验是：**同场景、同输入脚本、同一帧号**下分别跑汉化盘与英文原盘，比较 ① 桶 126 是否变坏及坏值 ② `used_pct` 曲线 ③ 首次踩到坏链的帧号。本轮的 E4 已经给出"用 `used_pct` 做对照"的可行口径（两者都在 77.6 % 附近）。

---

## 7. 产物清单

| 路径 | 内容 |
|---|---|
| `docs\REPORT_USERDUMP_ANALYSIS.md` | 本文档 |
| `work\builds\GR_USERDUMP\evidence\INVENTORY.txt` | 全部素材的路径/大小/时间/sha256（含 emulog 被锁说明） |
| `work\builds\GR_USERDUMP\evidence\emulog_snapshot_2026-10-18.txt` | live emulog 的共享读快照（444,549 B） |
| `work\builds\GR_USERDUMP\evidence\emulog_snapshot_sha256.txt` | 快照哈希与说明 |
| `work\builds\GR_USERDUMP\tools\g1_buckets.py` | mstate/桶数组取证（自指核对、桶 126、全 RAM 唯一性、堆走查） |
| `work\builds\GR_USERDUMP\tools\g2_ringfilter.py` | ring 筛选（桶数组、桶 126 槽、特定值/地址） |
| `work\builds\GR_USERDUMP\tools\g3_bucketwriters.py` | 按 PC ×（槽位 × 值类别）归类桶数组写者 |
| `work\builds\GR_USERDUMP\tools\g4_crosschecks.py` | 低 RAM / 全堆走查 / 桶项指针合法性 / watch.bin 交叉核对 / 写者全集 |
| `work\builds\GR_USERDUMP\tools\g5_excerpts.py` | ring 摘录 + emulog 快照 + 既有 audit 交叉引用 |
| `work\builds\GR_USERDUMP\tools\g6_tlbbursts.py` | TLB-miss 风暴按帧归并、野指针清单 |
| `work\builds\GR_USERDUMP\out\g1_buckets.{txt,json}` | 桶数组/桶 126/堆走查全量输出 |
| `work\builds\GR_USERDUMP\out\g2_{OLD, NEW}*.txt` | ring 全量桶数组写清单（108,715 / 160,100 条） |
| `work\builds\GR_USERDUMP\out\g3_{OLD,NEW}*.txt` | 写者归类表（含 PC → 桶 → 值类别 → 样本） |
| `work\builds\GR_USERDUMP\out\g4_crosschecks.txt` | §5 全部数字 |
| `work\builds\GR_USERDUMP\out\g5_ring_excerpts.txt` | 关键 ring 摘录（不是整份） |
| `work\builds\GR_USERDUMP\out\g5_prior_audits.txt` | 既有 audit 交叉引用 |
| `work\builds\GR_USERDUMP\out\g6_tlb_bursts.txt` | 四次 TLB 风暴 + 全部越界地址 |
| `work\builds\GR_USERDUMP\out\dis_101C00_101D10.txt` / `dis_101D10_102050.txt` / `dis_102050_1026C0.txt` | 分配器区反汇编（VA/原字/指令/字节） |

复现命令（全部只读，均在仓库根执行）：

```powershell
$py = 'C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
& $py work\builds\GR_USERDUMP\tools\g1_buckets.py
& $py work\builds\GR_USERDUMP\tools\g2_ringfilter.py
& $py work\builds\GR_USERDUMP\tools\g3_bucketwriters.py
& $py work\builds\GR_USERDUMP\tools\g4_crosschecks.py
& $py work\builds\GR_USERDUMP\tools\g5_excerpts.py
& $py work\builds\GR_USERDUMP\tools\g6_tlbbursts.py
& $py work\builds\GR_CULPRIT\tools\dis2.py work\builds\GR_CULPRIT\elf\LAY_fix1_bytecount_SLUS_206.13.elf diso 0x101D10 0x102050
```

（`dis2.py` 是本工程为 GR_CULPRIT 写的独立反汇编器；**未使用** `work\tools\cave_dis.py`。）

---

## 8. 未达成项（如实列出）

1. **没有抓到"写坏桶 126 的那条 store"本体**。损坏窗口 `(19701, 22094]` 与两份 ring 的覆盖区间 `18995..19700` / `22437..23443` **不重叠**，两份 ring 对 `0x0055BB98/9C` 的写记录都是 0 条。本轮给出的是"由反汇编 + 值形态 + 写者全集 + 现场 TLB 记录"构成的**重建**，不是逐字节 store 记录。
2. **A→B 逐 store 差分未达成**（同上）。已完成的是"逐桶（128 桶）+ 逐块（42,732 / 42,744 块）的状态差分"。
3. **真正的病灶写（把 `prev_foot`/`head` 弄脏的那次写，或第一次 `free(野指针)` 的调用点）未定位** —— 需求下一轮把 ring 覆盖窗口覆盖到 `(19701,22094]`（建议缩短 `log_every`、或把 ring 扩到 ≥1.5M 条、或把 watch 收窄到 `0x0055B7A0-0x0055C000` + `0x00101C00-0x00102700` 的写以便提高有效采样率）。
4. **ISO 内偏移未给出**（只给 ELF 文件偏移 `VA-0x100000+0x80`）；`SLUS_206.13` 在 ISO 里的 LBA/extent 需要 `GR_LAYOUT` 的 iso 布局工具，本轮未跑。
5. **F1/F2/F4/F5 的具体新字编码未完成/未验证**（只给站点、原字与策略）。cave 空间、跳转距离、以及 `bail` 目标需要按本工程既有 cave 工具落地后再核。
6. **PCSX2 对"TLB-miss 的 load"返回什么值未核实**（日志只记 PC/地址/方向/宽度，不记返回值）。这影响 `size`/`prev_size` 的**精确**复算；本轮关于 `C2 − C1 = 0x6FD4EB` 的推导依赖"符号扩展的低 32 位 `prev_foot`"，已在正文标注为推导而非直读。
7. **钩子 ring 的 `pc` 字段存在 ±4 的取址偏差**（多个样本上验证：`0x101EEC↔0x101EE8`、`0x101EFC↔0x101EF8`、`0x102014↔0x102010`、`0x102018↔0x102014`；但对延迟槽里的 store 又是 ±0）。本报告因此**以"地址+偏移+值类别"为主要判据**，PC 只作定位线索。建议下一轮在 `HookWatch.cpp` 里核对这个字段的语义。
8. **L1 按键事件未直接取证**：emulog 不记录输入；"L1 触发卡死"是"dump@帧23444(423.42 s) → 卡死@帧≈23645(427.48 s)，相隔 4.06 s"的**时间推断**。
9. **归因（§6.4）未判定** —— 缺"同场景汉化 vs 英文"的定量对照。
10. **`qt\logs\emulog.txt` 的 sha256 未取**（被运行中的模拟器写锁占用）；已用共享读快照代替并给出快照哈希。另：用户进程仍在运行，**该文件与两份 dump 之后可能继续变化**，本轮所有结论都基于上面的快照哈希与会话内的 dump 哈希。
