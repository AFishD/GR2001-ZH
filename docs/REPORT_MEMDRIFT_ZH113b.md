# REPORT_MEMDRIFT_ZH113b — 「随时间累积的损坏」专项取证

> 执行者：汉化工程执行任务（内存漂移专项）。仓库根 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`。
> 纪律：**所有既有 ISO / `third_party\orig\**` / PCSX2 配置全程只读**，未写任何 ISO；
> 写入仅限 `work\builds\GR_MEMDRIFT\**` 与本文件。模拟器全程单实例。日志一律等进程退出后才读。
> 证据目录：`work\builds\GR_MEMDRIFT\**`（含 `audit/`、各回放目录的 `RESULT.json` / `RUN.txt`）。

---

## 0. 结论摘要（先看这张表）

| 任务项 | 结论 | 证据 |
|---|---|---|
| **1. 实机卡死是否复现** | **未复现** | §2；汉化盘 30,600 帧 + 英文原盘 **80,000 帧 / 26.2 分钟**，两盘 **TLB Miss = 0、Trap = 0、Bus Error = 0**；用户日志里的两个 PC 在我们的样本里**一次都没执行过** |
| **2. 内存漂移取证** | **已产出帧对齐的可比对序列；结论是"没有汉化特有的累积"**（阴性）：两盘漂移曲线逐段几乎相同（82/9/23/12/18/15/13/44/14/14/15 vs 103/9/23/10/18/14/13/40/14/14/15），分配器状态同帧同向演化 | §4；`work\builds\GR_MEMDRIFT\drift_compare_aligned.json`、`drift_en_full.json` |
| **3. face 越界核查** | **有，且穷尽**：`huge` face 的 nrec 被从 **224 砍到 96** ⇒ 该 face 上 `idx ≥ 96` 的全部单字节码走"网格公式"分支 ⇒ `slot = idx−224 < 0` ⇒ **负 UV**。汉化盘实际会用的 **103 个**高位单字节码**全部命中**；`large`/`default` **零越界** | `work\builds\GR_MEMDRIFT\audit\font_face_audit.md` |
| **4. 最可能成因** | ① **FONT.RES 的 `huge` face 被截断 224→96 条，而 ISO 条目的 `real` 仍写 7222** ⇒ 引擎驻留缓冲尾部 **1280 B 是上一次堆分配的残留**（实测 1280/1280 非零），解析器可能踩进去； ② `huge` face 越界码产出负 UV（103/103）。①②**同一个根**：`huge` 的 224→96 | §5、§6 |
| **5. 未达成项** | ① 未复现卡死 ⇒ **没有"卡死瞬间"的直接内存证据**，成因④⑤仍是推断；② **"关卡内持续游玩"这个触发条件没被覆盖**（两盘回放都以过场/菜单为主；帧数口径上英文盘跑满 80,000 帧 = 26.2 分钟）；③ 用户存档在本地模拟器上不可用；④ `real` A/B 与 `huge` 恢复实验因纪律（禁写 ISO）未做；⑤ 解析器定位试过一次没打中 | §9 |

---

## 1. 本轮新增的**最硬**两条证据

### 1.1 用户日志里那个死循环 = 游戏自带的堆分配器 bin 扫描（**代码与英文原盘逐字节相同**）

Lead 给的日志尾部（`work\builds\GR_ZH113b_fix\emulog.txt`）：

```
[  224.4736] TLB Miss, pc=0x1024d0 addr=0x8  [load]      ← 同一个时间戳上无限重复
[  224.4736] TLB Miss, pc=0x102584 addr=0x14 [load]
```

`0x1024d0` 落在**游戏 ELF 的头 10 KB 内**（ELF 基址 0x00100000，PT_LOAD#1 = va 0x00100000 / off 0x80）。
用 `work\tools\cave_dis.py` 反汇编 `third_party\orig\ps2\slus_out\SLUS_206.13`（**未改动的原盘 ELF**）：

```
001024C0  8f220014  lw   $v0, 20($t9)        ; v0 = bin->next
001024C4  50590033  beql $v0, $t9, 0x102594  ; 空 bin 则跳过
001024C8  254a0001  addiu $t2, $t2, 1        ; (beql 延迟槽: 仅分支命中时执行)
001024D0  dc4b0008  ld   $t3, 8($v0)         ; ★★ TLB Miss addr=0x8  ⇒ v0 == NULL
001024D4  016dc024  and  $t8, $t3, $t5       ; t5 = 0x1FFFFFFE (大小掩码)
001024D8  03055823  subu $t3, $t8, $a1       ; 剩余 = 块大小 − 请求
001024DC  296c0020  slti $t4, $t3, 32        ; 剩余 < 32 ⇒ 不切分
...
0010251C  000b283c  dsll32 $a1, $t3, 0
00102528  014b1821  addu $v1, $t2, $t3
0010252C  ad280014  sw   $t0, 20($t1)        ; ← 经典 dlmalloc unlink:
00102530  ad090010  sw   $t1, 16($t0)        ;   chunk{+0x10=fd, +0x14=bk, +0x08=size|flags}
0010253C  ad460014  sw   $a2, 20($t2)
00102540  ad460010  sw   $a2, 16($t2)
00102544  fd440008  sd   $a0, 8($t2)
...
00102550  0560000c  bltz $t3, 0x102584
00102584  8c420014  lw   $v0, 20($v0)        ; ★★ TLB Miss addr=0x14 ⇒ 同一个 NULL
00102588  1459ffd1  bne  $v0, $t9, 0x1024D0  ; 继续扫同一个 bin
```

⇒ **崩溃点 = 某个 bin 的 `next` 读成了 0，分配器于是反复解引用 `NULL+0x8` / `NULL+0x14`。**

同一份反汇编还给出了**分配器状态全局的地址**：

```
00101C58  3C020056  lui   $v0, 0x0056
00101C5C  2442B7A0  addiu $v0, $v0, -18528   ; ⇒ $v0 = 0x0055B7A0
00101C70  0C040814  jal   0x00102050         ; → 分配器主体
```

**运行期实测确认**（`work\builds\GR_MEMDRIFT\peek_arena.py`，ZH 回放快照）：

```
frame  0055B7A0 0055B7A4 0055B7A8 0055B7AC 0055B7B0 0055B7B4 0055B7B8 0055B7BC
2500   F7177FFA 00000000 0183E110 0055B798 0146FE70 0146FE70 0055B7A8 0055B7A8
5000   FB5F7FFE 00000000 01602850 0055B798 0055B7A0 0055B7A0 0055B7A8 0055B7A8
```

`+0x00` 是 bin 位图（smallmap）、`+0x0C = 0x0055B798 = 状态地址−8`（与反汇编里
`t9 = a4 + 8·bin − 8` 的 bin 数组基址**完全吻合**）、`+0x18/+0x1C` 是自指的空 bin 哨兵。
⇒ **反汇编与运行期数据互相印证，分配器状态就在 VA 0x0055B7A0 起的 ~0x600 字节内。**

★ **这条证据把"分配失败 ⇒ NULL 句柄 ⇒ 死循环"从猜测变成了机制**：不是某个返回 NULL 的 API，
而是**堆的空闲链表（bin）被写坏了 / 被清零了**。

★★ **而这段代码我们一个字节都没改**：把 `GR_ZH113b.iso` 里的 ELF 原样抽出与英文原盘对比
（`work\builds\GR_MEMDRIFT\audit\ZH113b_SLUS_206.13.elf`，34,745,372 B，抽自 ISO 偏移 0x93800）：

```
4 字节字差异 = 567 处，全部落在 VA 0x1FF8D0 .. 0x578070
分配器所在 VA 0x102xxx  ——  0 处差异
```

⇒ **卡死是"喂进去的数据把堆写坏了"，不是补丁代码本身有 bug。**

### 1.2 引擎**实际驻留**的 FONT.RES 缓冲尾部有 1280 B 残留数据

详见 §5.2。一句话：`real` 声明 7222、实际解出 5942，而引擎那份 7222 B 缓冲的
**后 1280 B 非零字节 = 1280/1280（100% 是上一次堆分配的残留）**。

---

## 2. 卡死是否复现 —— **未复现**（含判定依据）

### 2.1 两趟确定性回放

| 项目 | 汉化盘 | 英文原盘 |
|---|---|---|
| ISO | `work\builds\GR_ZH113b\GR_ZH113b.iso` | `work\builds\GR_EN_ORIG\GR_EN_ORIG.iso` |
| 输入脚本 | `work\builds\GR_MEMDRIFT\inputs\zh_long.txt`（211 行，生成器 `gen_input.py`） | `...\en_long.txt`（同一时间线） |
| BIOS | `SCPH-90006_BIOS_VX_HK_2.20.bin`（= 用户实机 Japan v02.20） | 同左（保证逐帧可比） |
| 命令 | `run_memdrift.py --tag zh113b_long --frames 80000 --periodram 2500 --snap 300` | `--tag en_orig_long`（同参数） |
| 结果 | `zh113b_long`：跑到 **f30,600**（8.5 分钟游戏时间）被判为"已漂到主菜单"而终止 | `en_orig_long`：**跑满 80,000 帧 / 26.2 分钟**，`exit=0` |
| **TLB Miss / Trap / Bus Error** | **0 / 0 / 0** | **0 / 0 / 0** |
| `pcsample` distinct PC | 全段 99（92.1% 在 `0x00411FB0`） | 全段 121（97.4% 在 `0x00411FB0`） |
| 用户那两个 PC | `0x001024D0` / `0x00102584` 各 **0 次** | 各 **0 次** |
| 截图 | 最长"逐字节相同"连续段 = 菜单的 1500 帧周期动画（已核实是菜单，不是卡死） | 266 张，**无任何冻结段** |

游戏 CRC 对照（便于对齐用户存档）：`GR_EN_ORIG` = **3E571E95**、`GR_ZH113b` = **7A361FB5**、
`GR_ZH113b_fix` = **7A361FB7**。用户 `sstates` 里三个 CRC 的存档都有
（`(3E571E95).01/10.p2s` 11:01–11:09 = 英文盘；`(7A361FB5).01/02.p2s` 19:49–19:50 = 汉化盘；
`(7A361FB7).01.p2s` 20:19:58 = **卡死前 12 秒那次**）。

模拟器：研究构筑 `third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe`（PCSX2 v2.8.2-1-gcd5e3304c，
与用户官方 v2.8.2 同 `Savestate version 0x9a590000`）。实测 **53–60 fps**，即 1 帧 ≈ 1 真实帧。

### 2.2 判定依据（四条，都指向"没复现"）

1. **汉化盘 30,600 帧回放：`TLB Miss = 0`、`Trap exception = 0`、`Bus Error = 0`**
   （`Select-String -Path work\builds\GR_MEMDRIFT\zh113b_long\emulog.txt -Pattern 'TLB Miss'` → 0 条）。
   用户环境是在 224 s ≈ 第 13.5k 帧**必然**进入死循环；我们在同一张盘上跑过了 30.6k 帧。
2. **`-grpcsample` 逐 PC 采样：用户那两个 PC `0x001024D0` / `0x00102584` 在我们的样本里出现 0 次**
   （`python work\builds\GR_MEMDRIFT\pcstat.py ...`；7,660 个样本覆盖 f4..f30,640，全段 99 个不同 PC）。
3. **兄弟任务（GR_FPS）在同一张盘上跑满 20,000 帧，`tlb=0 / trap=0 / unmapped=0`**
   （`work\builds\GR_FPS\out\zh113b_probe\ANALYSIS.json`）。
4. **英文原盘跑满 80,000 帧（26.2 分钟）同样 `TLB Miss = 0`**，且 PC 分布与汉化盘**同形**
   （两张盘的等待/主循环 PC 都是 `0x00411FB0`，占比 92%/97%）⇒ **这一轮的场景对两张盘都是"无害"的**，
   不是"只有汉化盘会中招而恰好没中"。
5. **唯一一次"冻结"不是这个 bug**：把用户实机存档载进研究构筑后，游戏在 ~200 帧内
   在**异常向量**上踩野指针冻结，PC 与故障地址都与用户的完全不同（§2.3）。

### 2.3 用户存档实验（做过了，结论是"用不了"，但过程有信息量）

用户的卡死是 224.47 s 发生的，而**实机在 212.9 s 存过一次档**（emulog 里有
`Saving save state ... SLUS-20613 (7A361FB7).01.p2s`）—— 即**卡死前 12 秒、人在关卡里**。

* 存档：`C:\Users\84363\AppData\Local\PCSX2\sstates\SLUS-20613 (7A361FB7).01.p2s`
  （15,729,262 B，2026-10-15 20:19:58；`Savestate Version.id` 内嵌 `0x9A590000`）。
* 研究构筑 `g_SaveVersion = (0x9A59 << 16) | 0`（`pcsx2\SaveState.h` L29）⇒ **版本一致，可以尝试载入**。
* 第一次（`zh113b_fix_state`）：日志出现
  `MTVU speedhack is enabled, saved states may not be stable` /
  `gifUnit: MTVU Mode has switched between save/load state`
  ⇒ 研究构筑 `vuThread=true`，用户 `vuThread=false`（见 §7 配置对照）⇒ 用
  `-grsetting EmuCore/Speedhacks vuThread 0` 重跑。
* 第二次（`zh113b_fix_state_v2`）：MTVU 告警消失，但仍在 **frame ~210** 出
  ```
  [6.2515] TLB Miss, pc=0x80000180 addr=0x70036513 [load]
  ```
  之后 PC 永久停在 **`0x8000F270`（内核区）**：`pcsample` 全段 distinct PC = **2**，
  93% 落在 `0x8000F270`；133 张截图里 **127 张逐字节相同**（f210..f3990）。

  ⇒ **这是我们构筑与用户构筑的存档互操作性问题，不是用户的 bug**：
  故障 PC（`0x80000180` / `0x8000F270`）与故障地址（`0x70036513`）都跟用户的
  （`0x001024D0`/`0x00102584`，`0x8`/`0x14`）**毫无关系**，且发生在载入后 200 帧内，
  完全没有"游玩一段时间才出现"的时间结构。

★ **这一条对本轮任务的判断很关键**：它说明"本地模拟器复现不了"不是因为我们没找对盘，
而是**研究构筑与用户实机在模拟器层面的差异足以改变结果**（§7）。

---

## 3. 命令清单（全部可复跑）

```powershell
# ── 生成确定性输入脚本（<frame> <button> <tap|hold|release>）──
python work\builds\GR_MEMDRIFT\gen_input.py --out work\builds\GR_MEMDRIFT\inputs\zh_long.txt --frames 80000
python work\builds\GR_MEMDRIFT\gen_input.py --out work\builds\GR_MEMDRIFT\inputs\en_long.txt --frames 80000

# ── 长回放 + 定时 EE/IOP RAM 快照 ──
python work\builds\GR_MEMDRIFT\run_memdrift.py --tag zh113b_long `
  --iso work\builds\GR_ZH113b\GR_ZH113b.iso --input work\builds\GR_MEMDRIFT\inputs\zh_long.txt `
  --frames 80000 --periodram 2500 --snap 300 --out work\builds\GR_MEMDRIFT\zh113b_long
python work\builds\GR_MEMDRIFT\run_memdrift.py --tag en_orig_long `
  --iso work\builds\GR_EN_ORIG\GR_EN_ORIG.iso --input work\builds\GR_MEMDRIFT\inputs\en_long.txt `
  --frames 80000 --periodram 2500 --snap 300 --out work\builds\GR_MEMDRIFT\en_orig_long

# ── 用户存档复现尝试（已证明不可用，留档）──
python work\builds\GR_MEMDRIFT\run_memdrift.py --tag zh113b_fix_state_v2 `
  --iso work\builds\GR_ZH113b_fix\GR_ZH113b_fix.iso `
  --state "C:\Users\84363\AppData\Local\PCSX2\sstates\SLUS-20613 (7A361FB7).01.p2s" `
  --input work\builds\GR_MEMDRIFT\inputs\from_state_play.txt `
  --frames 3000 --periodram 100 --snap 30 --memwatch "0x0055B000 0x2000 1" `
  --extra "-grsetting EmuCore/Speedhacks vuThread 0" `
  --out work\builds\GR_MEMDRIFT\zh113b_fix_state_v2

# ── 离线取证（只读 ISO）──
python work\builds\GR_MEMDRIFT\audit\font_face_audit.py      # face/nrec/闸门/越界 → audit/font_face_audit.json
python work\builds\GR_MEMDRIFT\audit\content_diff.py         # 逐条目 sha256 + COMMON.PAK 链 → audit/content_diff.json
python work\builds\GR_MEMDRIFT\audit\iso_container_diff.py   # ISO9660+IMG 条目字段 → audit/iso_container_diff.json
python work\builds\GR_MEMDRIFT\audit\find_fontbuf.py work\builds\GR_ZH113b\temp\dump_p1base
python work\builds\GR_MEMDRIFT\audit\find_readres.py         # 在 ELF 里找 nrec*10+0x10 的分配站点

# ── 漂移比对 / 单点时间线 / PC 分布 ──
python work\builds\GR_MEMDRIFT\analyze_memdrift.py --zh ...\zh113b_long --en ...\en_orig_long `
  --lo 0x100000 --hi 0x64BE80 --k 2 --out ...\drift_compare.json
python work\builds\GR_MEMDRIFT\timeline.py --dir ...\zh113b_long --addrs 0x0055B818,0x005C4D2C
python work\builds\GR_MEMDRIFT\pcstat.py ...\zh113b_long\pcsample.txt
```

**模拟器开关用法（`third_party\emu\pcsx2_src\pcsx2-gsrunner\GRResearch.cpp` 里读出来的，本轮实测可用）**

| 开关 | 作用 | 本轮用途 |
|---|---|---|
| `-grperiodram N` | 每 N 帧转存**全部 EE RAM(32 MB)+IOP RAM(2 MB)** → `period_f%08u_{eeram,iopram}.bin` | 漂移序列（帧号在文件名里） |
| `-grmemwatch <addr> <size> <iv>` | 每 iv 帧往 `memwatch.bin` 追加 `[u32 frame][u32 addr][u32 size][data]`，**每帧 fflush、共享打开可实时 tail** | 帧号心跳；`0x0055B000 0x2000 1` 逐帧盯分配器状态 |
| `-grpcsample 1` | 每 4 帧写 `<frame> <cpuRegs.pc>` 到 `pcsample.txt` | ★ 卡死判定（PC 分布塌缩） |
| `-grsnap N` | 每 N 帧截图 | 画面静止判定 |
| `-grstate <p2s>` | 启动后直接载入存档 | 用户存档复现实验 |
| `-grwatch <addr> <size>` | 逐重编译块轮询该区间，记录"哪个块改的它"（`watch.txt` 的 `writer_block=`）**开启 trace-all-blocks，慢**；命中上限 64 | 未用（先要定位到具体地址，见 §8） |
| `-grsetting <sec> <key> <val>` | 内存里覆盖设置（**不写 ini**） | `EmuCore/Speedhacks vuThread 0` |
| `-grbiosname <file>` | 指定 BIOS（否则扫描到哪个用哪个） | 对齐用户实机 Japan v02.20 |

---

## 4. 内存漂移取证

### 4.1 采样序列

* 汉化盘 `GR_ZH113b`：**12 份**（f2500, 5000, …, 30000），每份 EE 32 MB + IOP 2 MB
  → `work\builds\GR_MEMDRIFT\zh113b_long\period_f*_{eeram,iopram}.bin`
* 英文原盘 `GR_EN_ORIG`：同间隔同帧号（见 `en_orig_long\RESULT.json`）
* 逐帧分辨率的分配器状态：`zh113b_long\memwatch.bin`（每帧 0x2000 字节）

> ★ **必须对齐共同帧**：否则"汉化盘变了 N 次、英文盘 0 次"只是样本数不同造成的假阳性。
> `analyze_memdrift.py` 已内置对齐（取两盘帧号交集后各自重采）。

### 4.2 漂移曲线（ELF 映像区 VA 0x100000..0x64BE80，逐 32-bit 字比较相邻样本）

**对齐到共同帧（f2500..f30000，各 12 份样本）后**：

```
ZH:  f2500→f5000   82 B | f5000→f7500    9 B | f7500→f10000  23 B | f10000→f12500 12 B
     f12500→f15000 18 B | f15000→f17500 15 B | f17500→f20000 13 B | f20000→f22500 44 B
     f22500→f25000 14 B | f25000→f27500 14 B | f27500→f30000 15 B
EN:  f2500→f5000  103 B | f5000→f7500    9 B | f7500→f10000  23 B | f10000→f12500 10 B
     f12500→f15000 18 B | f15000→f17500 14 B | f17500→f20000 13 B | f20000→f22500 40 B
     f22500→f25000 14 B | f25000→f27500 14 B | f27500→f30000 15 B
```

★★ **两条曲线逐段几乎完全相同**（9/23、13、14/14/15 完全一致，其余 ±2 B）。
⇒ **ELF 映像区（含分配器状态、全部 .data/.bss 结构）的活动量在两张盘上是一个量级、
同一个形状** —— **没有"汉化盘特有的累积"**。
（另外 §4.5 的截图大小逐帧对照也证明两条回放**帧对齐、落在同一个游戏状态**：
f15000 ZH=76,575 B / EN=84,582 B，f2100 两张盘**同为 441,016 B**。
尺寸不同只因为界面文字一个是中文一个是英文。）

### 4.3 ★ "只在汉化盘上变化"的位置（`drift_compare_aligned.json` 的 `zh_only_drift`）

对齐后只剩 **8 个字，每个都只变过 11 对里的 2 对**：

| 地址 | 汉化盘 | 英文原盘 | 备注 |
|---|---|---|---|
| 0x0055B818 | `0131CDB0 → 00833BF0`（2/11） | `0055B808`（0/11） | 落在分配器状态 VA 0x0055B7A0 的 bin 区内部 |
| 0x0055B81C | `00896350 → 00833AB0`（2/11） | `0055B808`（0/11） | 同上，紧邻 |
| 0x005C4D2C | `09000000 → 0902F452`（2/11） | `696E7307`（0/11） | 英文盘是静态 ASCII、汉化盘是中文文本区 |
| 0x005C4D40 | `00000062 → F43C0062`（2/11） | `6570696E`（0/11） | 同上 |
| 0x005D5D34 | `09200280 → 414D0282`（2/11） | `6E6F6973`（0/11） | 同上 |
| 0x005D6A20 | `65520902 → 616D0902`（2/11） | `00000077`（0/11） | 同上 |
| 0x005D6A24 | `75636974 → 6D5F6E69`（2/11） | `332D0380`（0/11） | 同上 |
| 0x005D6A28 | `4649656C → 5F756E65`（2/11） | `3536372E`（0/11） | 同上 |

**解读（不夸大）**：

* **0x0055B818 / 0x0055B81C 是把"落点"指到分配器身上的唯一两处**（它们在
  `malloc_state` 的 bin 数组里）。但要同时说清：① 该区**本来就是 dlmalloc 的 bin 数组**，
  正常分配/释放就会改它，"变过"不等于"坏了"；② 幅度只有 2/11，与 EN 侧同一量级的抖动
  （EN 在别的 bin 上也有等价变化，只是这 11 对里没轮到这两格）无法区分；
  ③ **12 份样本里没有任何一个 bin 字段的末值变成 0** —— 而"变 0"才是用户日志里的崩溃形态。
  ⇒ **本轮数据不足以把这两处判成损伤**；它们是"下一步该盯的点"，不是结论。
* 0x005C4D2x / 0x005D6A2x 一片：英文盘上是**静态 ASCII**、汉化盘上被改写 2 次 ——
  形态上是**汉化新增的中文文本暂存区**（英文盘不走这条路）。属于"汉化引入的差异"，
  但**没有越界证据**（相邻的 EN 静态常量在 ZH 侧也没有被破坏）。
* `[3] 首样本非 0、末样本为 0`（"结构指针被清零"）在 ELF 映像区只有 **3 处**
  （`0x005EC884 0x00079A40→0`、`0x005EC8A4 0x30→0`、`0x00633BC8 0x1→0`，各只变 1 次，
  都发生在装载关卡那一次 f2500→f5000）；全 32 MB 内有 2310 处，但**几乎全是"只变一次"**、
  集中在 0x00022xxx 一带 —— 那是**关卡装载时批量释放/重置**的正常现象，不是衰变。

### 4.4 分配器状态的逐样本解码（`0x0055B7A0`，汉化盘）

```
frame   smallmap  dvsize    least     dv        top       tree0_fd  tree0_bk
2500    F7177FFA  0183E110  0055B798  0146FE70  0055B7A8  012A2870  012A27D0
5000    FB5F7FFE  01602850  0055B798  0055B7A0  0055B7A8  012A2C70  0085D3F0
7500    FB5F7FFE  01602850  0055B798  0055B7A0  0055B7A8  012A2C70  0085D3F0
10000   FB5F7FFE  01602850  0055B798  0055B7A0  0055B7A8  008652E0  00865DC0
12500   FB5F7FFE  01602850  0055B798  0055B7A0  0055B7A8  00866360  008655A0
15000   FB5F7FFE  01602850  0055B798  0055B7A0  0055B7A8  0085D3F0  0086B560
17500   FB5F7FFE  01602850  0055B798  0055B7A0  0055B7A8  00864A10  0085DEC0
20000   FB5F7FFE  01602850  0055B798  0055B7A0  0055B7A8  00864A10  0085DEC0
22500   FB1F60FE  0172E8B0  0055B798  00724FF0  0055B7A8  0087CD80  0085EF60
25000   FB1F60FE  0172E8B0  0055B798  00724FF0  0055B7A8  0085BE50  0085D3F0
27500   FB1F60FE  0172E8B0  0055B798  00724FF0  0055B7A8  008339C0  0085D6D0
30000   FB1F60FE  0172E8B0  0055B798  00724FF0  0055B7A8  0085CB70  00865770
```

* `least` 恒为 `0x0055B798`（= 状态地址−8）⇒ 堆的最低地址没变过，**没有堆基址漂移**。
* `top` 恒为 `0x0055B7A8`（自指哨兵）⇒ **top 指针没有掉进 bin 数组**。
* 那个 ~24 MB 的尺寸字段在 f2500 变更一次（0x0183E110 → 0x01602850，**减少** 2.29 MB），
  f22500 又一次（→ 0x0172E8B0，**增加** 1.11 MB），**来回摆而不是单调下降** ⇒ **不是泄漏**。
* `tree0_fd/bk` 一直在换 ⇒ 正常分配抖动。

★ **诚实结论：在汉化盘 2,500–30,000 帧这个窗口里，分配器状态全程健康，没有任何 bin
字段衰变成 0，也没有单调泄漏。** 这与 §2 的"未复现"完全一致。

### 4.5 ★★ 英文原盘的同址对照（**结构完全同形**）

```
EN frame  smallmap  dvsize    least     dv        top       tree0_fd
2500      FF53FFFE  017E2EC0  013C5180  013C5180  0055B7A8  0084F790
5000      FB84604E  015A7600  0055B7A0  0055B7A0  0055B7A8  013438F0
10000     FB84604E  015A7600  0055B7A0  0055B7A0  0055B7A8  008C3E80
15000     FB84604E  015A7600  0055B7A0  0055B7A0  0055B7A8  008C4550
20000     FB84604E  015A7600  0055B7A0  0055B7A0  0055B7A8  008C3E80
22500     F980404E  016D3660  013C65D0  013C65D0  0055B7A8  01095E90
25000     F980404E  016D3660  013C65D0  013C65D0  0055B7A8  0124A400
30000     F980404E  016D3660  013C65D0  013C65D0  0055B7A8  01095E90
```

并排看（数值不同只因为**堆地址本来就不同**，要比的是**结构事件**）：

| 帧 | 汉化盘 | 英文原盘 | 判定 |
|---|---|---|---|
| 2500 | `dv/least` = 堆地址 `0146FE70`，尺寸 0x0183E110 | `dv/least` = 堆地址 `013C5180`，尺寸 0x017E2EC0 | **同一事件**（关卡装载后存在大块 dv） |
| 2500→5000 | `dv/least` → `0055B7A0`（自指 = 无 dv），尺寸降 0x01602850 | `dv/least` → `0055B7A0`，尺寸降 0x015A7600 | **同一事件、同一方向** |
| 5000–20000 | 冻结不变 | 冻结不变 | 同形 |
| 20000→22500 | `dv/least` → 堆地址 `00724FF0`，尺寸升 0x0172E8B0 | `dv/least` → `013C65D0`，尺寸升 0x016D3660 | **同一事件、同一方向** |
| `top`（+0x18） | 12 份恒为 `0055B7A8`（自指哨兵） | 12 份恒为 `0055B7A8` | 两盘都**没有** top 指针掉进 bin 数组 |

⇒ **两张盘的分配器走的是同一个状态机、在同样的帧、朝同样的方向**，
只有堆地址不同（资源/文本布局不同）。**这是一条很强的对照证据：本窗口内分配器没有汉化特有的病态。**

### 4.6 ★★ 英文原盘**跑满 80,000 帧**的分配器演化（"抖动不等于坏"的对照）

```
EN frame  smallmap  dvsize    least     dv        top
30000     F980404E  016D3660  0055B798  013C65D0  0055B7A8
32500     F902487E  016D3660  0055B798  013C7230  0055B7A8
37500     F0018FFE  01713680  0055B798  00735900  0055B7A8
42500     FD17E1FE  016D3660  0055B798  013DC010  0055B7A8
47500     FF1000DE  01713680  0055B798  0055B7A0  0055B7A8
50000     F3FFFDFE  016866A0  0055B798  00FBC430  0055B7A8
55000     FFC0407E  016866A0  0055B798  00FBA0E0  0055B7A8
62500     FF8140FE  016866A0  0055B798  0074D690  0055B7A8
70000     FFEA007E  016866A0  0055B798  00FBA370  0055B7A8
75000     FFDF49FE  016866A0  0055B798  00AD92B0  0055B7A8
77500     73DFC0FE  016A66E0  0055B798  0055B7A0  0055B7A8
```

★★★ f32,500 之后**几乎每一份样本的 `smallmap`、`dv` 都在变**，堆地址在 0x007xxxxx..0x014xxxxx
之间大幅跳动 —— 即**未改动的英文原盘在这 26 分钟里做了极其密集的分配/释放**，
而它 **`TLB Miss = 0`、`top` 12 份恒为自指哨兵 `0x0055B7A8`、运行到底不崩**。

⇒ **"分配器状态一直在变"本身不是病**。用户那种崩溃必须是**某一处具体的破坏**，
而不是"时间长了堆就乱"。这条对照把 §6 的成因假设收窄成"必须有一个具体的越界写/误解析"，
而不是"堆用久了自然坏"。

### 4.7 ★★ 本节结论（重要）

> **在"两次回放帧对齐 + 同 BIOS + 同输入脚本"的条件下，汉化盘与英文原盘的
> EE RAM 变化量、变化形状、分配器状态演化几乎完全相同；
> 2,500–30,000 帧窗口内没有观察到任何"只在汉化盘上出现、且随时间累积"的损坏，
> 也没有观察到分配器空闲链表衰变或堆泄漏。**
>
> 这是一个**阴性结果**，它本身有价值：它说明**触发条件没有被这一轮回放覆盖到**
> （见 §4.8 的局限），而不是说明盘没问题 —— §5 的两条**静态**缺陷是确凿存在的。
> 下一步应当把"真在关卡里持续游玩"这一条件补上（§8-5）。

### 4.8 ★ 局限（必须写明）

这一轮汉化盘回放**大部分时间不在关卡内**，因此**没有覆盖"持续游玩"这个触发条件**：

* 截图证据：`snap_f00021000.png` = **游戏主菜单**（光标在「统计」），
  `snap_f00019200.png` = 「统计」成绩页；`snap_f00000900.png` = 关卡开场**过场动画**。
* f20700 之后的截图呈**严格 1500 帧（25 s）周期、且逐字节 SHA256 相同**
  （f21000/22500/24000 三张同 hash，f21300/22800/24300 三张同 hash…）⇒ 是菜单的循环动画，
  不是在关卡里跑动。
* `pcstat.py` 也印证：全段 99 个不同 PC，**92% 落在 `0x00411FB0`**（游戏自己的等待/主循环），
  即绝大部分时间在"等下一帧"，不是在游戏逻辑里。
* 原因：`nav_play.txt` 的 F 段（f19400–f31400，`select/triangle/circle/square/l1/l2/r2/r3/l3/start`
  轮询）把任务退出了 —— 与本轮 BIOS 换成用户实机 v02.20 后**引导时序整体位移**叠加，
  落点全错。这是**导航脚本的问题，不是取不到数据**：把这一段删掉、或改用默认 BIOS 重标定即可。

---

## 5. 越界核查结论（任务书第 3 条）

完整版见 `work\builds\GR_MEMDRIFT\audit\font_face_audit.md`，这里只给结论与最硬的取证。

### 5.1 越界码清单（**有**，且穷尽）

| face | nrec | 越界单字节码 | UV 落到图集外 |
|---|---|---|---|
| large | 224 | `0x00..0x1F` | 无 |
| default | 224 | `0x00..0x1F` | 无 |
| **huge** | **96** | `0x00..0x1F` ∪ **`0x80..0xFF`** | **`0x80..0xFF` 共 128 个，U/V 全为负** |

汉化盘实际会用的高位单字节码（`tools\font_pipeline\data\charset_compiled_zh16.json` 的 `codes`）
共 **103 个** = `0x80..0xA0`(33) ∪ `0xBA..0xFF`(70)：
**103/103 在 `huge` 上 `idx ≥ 96`，103/103 的 `slot = idx−224 < 0` ⇒ UV 全为负。**
英文原盘同一批码在 `huge` 上 `idx < 224` ⇒ 走记录表 ⇒ 正常。

判据来自**汉化盘自己的 ELF**（`audit/ZH113b_SLUS_206.13.elf`）：

```
00416f78  80c30020  lb   $v1, 32($a2)     ; face[+0x20] = 码基址
00416f80  310800ff  andi $t0, $t0, 0x00FF ; idx = (码 − 码基址) & 0xFF
00416fb0  8cc30044  lw   $v1, 68($a2)     ; face[+0x44] = nrec
00416fb4  0103102b  sltu $v0, $t0, $v1    ; idx < nrec ?
（GetGlyphUV cave）
004170a8  2508ff20  addiu $t4, $a1, -224  ; slot = idx − 224  ← idx<nrec<224 时这里是负数
004170b0  00000000  div   $t4, 62         ; row（向零截断）
004170c8  00000000  mult  $t4, 16         ; U0 = 16*col
```

`face[+0x20] = 0x20` **不是照抄文档，而是运行期实测**：在 EE RAM 快照里按
"`+0x44`=nrec、`+0x38`=记录数组指针、记录矩形合法"三条件搜到两个真实 face 对象：

```
nrec=224  face+0x20=0x20  face@0x688B64  recs@0x687430
nrec=96   face+0x20=0x20  face@0x688BF4  recs@0x688740
```

### 5.2 ★ 与"声明长度不匹配"**同源**，并且**已取到引擎缓冲的直接物证**

```
huge face 记录数  224 → 96      ⇒ 少 128 条 × 10 B = 1280 B
FONT.RES 展开长度 7222 → 5942   ⇒ 正好少 1280 B
ISO 条目 real 字段 7222（**没跟着改**）
```

在项目自己的帧 258/260/262 EE RAM 转存里搜到**引擎实际解析的那份 FONT.RES**：

```
work\builds\GR_ZH113b\temp\dump_p1base\newfontrevisedrs_f00000258_eeram.bin
  资源起点 = EE 0x1FF695C
  faces    = [('large',32,7,224), ('default',32,7,224), ('huge',16,6,96)]
  记录区结束 = 资源+0x1624
  0x1620..0x1736（278 B 真风格块）: 非零 106 B
  0x1736..0x1C36（多出来的 1280 B）: 非零 **1280 / 1280**   ← 100% 残留，不是零
```

⇒ 引擎缓冲确实按条目 `real` **7222 B**，实际只写 5942 B，**尾部 1280 B 是上一次堆分配的残留**；
三份快照（f258/f260/f262）逐字节相同 ⇒ 稳态。

**覆盖范围**：`GR_ZH98 / GR_ZH113b / GR_ZH113b_fix / GR_ZH124` **全部** `real=7222 实际=5942 huge=96`，
`GR_EN_ORIG` 是 `7222/7222/huge=224`。⇒ **自 ZH98 起每张汉化盘都带这个缺陷。**

### 5.3 闸门（另一条独立判据）

汉化盘 ELF 的 4 个闸门站点立即数**完全一致 = 0xB1**（`0x416EE8 / 0x417160 / 0x41751C / 0x5656A4`，
第 4 处在原盘是一段 NOP，被用成 cave）⇒ 本盘对偶前导区间 = `0xA1..0xB0`（16×94 = **1504 槽**），
与构建报告的 `pair: 1504` 精确吻合 ⇒ **盘自洽**。

★ 但 `charset_compiled_zh16.json` 已是 **2026-10-15 的 `0xB5→0xBA` 世代**（`pair_of` 的 lead 到 0xB9、
25×94 = 2350 对）。**用现在这份 charset 去编 gate=0xB1 的盘会写出 0xB1..0xB9 的前导**，
而盘上解码器会把它们当单字节 ⇒ 一个汉字裂成两个字形 + 撞上 §5.1 的 huge 越界。
这是**潜在（本盘当前未触发）**的编码器/解码器失配，下一次构建前必须挡住。

---

## 6. 最可能的成因（1~2 条）

### 成因 ①（首选，证据最全）：`huge` face 记录表被截断，但 ISO 条目的 `real` 没跟着改

链条（①–③ 已实证，④–⑤ 为强推断，§8 给了定案方法）：

1. 构建时把 `huge` face 的记录数从 **224 砍到 96**（为了腾 FONT.RES 的 1280 B 空间），
   LZO 子流随之只解出 **5942 B**。
2. 但 IMG 条目的 `real` 仍写 **7222** ⇒ 引擎拿到一个 **7222 B** 的缓冲。
3. 后 **1280 B 没有被写入**，保留的是**上一次堆分配的残留**（实测 1280/1280 非零）。
   ⇒ 这 1280 B 的内容**取决于堆历史**，因而**与关卡/时机有关** —— 这正解释
   「好几关都复现」「游玩达到一定时间之后才出现」而**不是某个固定点立刻复现**。
4. **（待证）** 资源解析器在 3 个 face 之后继续解析"风格块"，若其终止条件基于**条目长度**
   而不是资源自带长度，就会把这 1280 B 残留当成风格块条目读 → 结构字段被写入野值。
5. **（待证）** 那些野值后来在绘制/分配路径上被当作指针或长度使用 → 堆的空闲链表（bin）
   被写坏 → 分配器扫 bin 时读到 `next = 0` → `NULL+0x8` / `NULL+0x14` 死循环
   （**正是用户日志里的形态**，见 §1.1）。

### 成因 ②（附带，确定存在但严重度较低）：`huge` face 的 103 个高位单字节码全部产负 UV

`huge` 从 224→96 的**直接**后果：该 face 上所有 `≥0x80` 的单字节码（手柄按键图标、
符号、拉丁扩展）都取不到记录，落到网格公式的**负 slot**，采样到 1024×512 图集之外。
英文原盘同码正常。**只要有任何一处用 `huge` face 画这些码，就必然画错。**

> 两条成因**同一个根**：`huge` face 的 224→96。修掉截断，两条一起消失。

---

## 7. 用户环境 vs 本机研究环境的差异（解释"为什么本地复现不了"）

| 项 | 用户实机 | 本机研究构筑 | 影响 |
|---|---|---|---|
| 模拟器 | 官方 PCSX2 **v2.8.2** | `pcsx2-gsrunner.exe`（**v2.8.2-1-gcd5e3304c**，带 GR 插桩 + 移植期本地修改） | ★ 存档互操作失败（§2.3）；EE/IOP 时序可能有别 |
| MTVU `vuThread` | **false** | **true**（`Documents\PCSX2\inis\PCSX2.ini`） | ★ 载入用户存档直接崩（已用 `-grsetting` 覆盖为 0 消除该告警，但仍失败） |
| BIOS | Japan **v02.20**（SCPH-90006 HK） | 默认扫到 `SCPH-70000_BIOS_V12_JPN_2.00.bin` | 本轮已用 `-grbiosname SCPH-90006_BIOS_VX_HK_2.20.bin` 对齐 |
| 引导模式 | （用户配置未写，走默认） | `EnableFastBoot=true` | 引导时序不同 ⇒ 同一份按键脚本落点不同 |
| GameFixes / 宽屏补丁 | 未开 | `EnableGameFixes=true`、`EnableWideScreenPatches=true` | `patches.zip` 缺失 ⇒ 实际无补丁生效，但开关状态不同 |
| 渲染器 | `Renderer=15`（硬件）| `Renderer=-1`（自动） | 只影响 GS，不影响 EE 堆 |
| 输入 | 手柄 + `-grinput` 注入 | | 注入是 `Pad::SetControllerState`，与 Pad1 绑定无关 |

**结论**：本地跑不出卡死，**不能**据此否认用户的现象；但也不能据此把成因说成已定案。

---

## 8. 若要定案，还需要什么（按性价比排序）

1. **★ 最便宜、最决定性：改一个 u32 做 A/B。**
   把 `GR_ZH113b_fix.iso` 的 `MENU.IMG` 条目表里 `FONT.RES` 的 `real` 从 **7222 改成 5942**
   （`MENU.IMG` 内偏移 `0xB9120+9*4`，即 `iso_off_of_FONT.RES_entry + 48*4 + 7*4`），
   `stored` 不动 ⇒ 磁盘内容一个字节都不变、LBA 不动，**只改声明长度**。
   在用户实机上跑同一段流程：若卡死消失 ⇒ 成因 ① 定案；若仍卡死 ⇒ 成因 ① 被否证。
   （本轮**没有**做，因为纪律禁止写 ISO；改动点已在 `audit/iso_container_diff.py` 的输出里给全。）
2. **把 `huge` face 的记录数恢复成 224**（需要 1280 B 空间：`MENU.IMG` 尾部或 `COMMON.PAK`
   的 4 B 尾料 + 条目重排都能腾出来；`docs\FONTRES_STRUCTURE_r83.md` §4 已证明容器内部
   没有可压缩空间，所以要动**布局**）。这一条同时消掉成因 ① 与 ②。
   ★ 注意：**别只改 `nrec` 而不补记录** —— 那会让 `GetGlyphUV` 去读不存在的记录。
3. **解析器终止条件的静态定案**：反汇编 `RSFontMgr::ReadResourceFile`，看它在 3 个 face 之后
   解析"风格块"时的循环上界是**条目长度**还是**资源自带长度**。
   本轮已备好工具（`audit/find_readres.py`：在 ELF 里搜 `sll rd,rt,2 / addu / sll rd,rd,1`
   的 ×10 序列，命中 66 处；下一步应改为从 `__nwa` 包装器 `0x00102020`/`0x00102D40`
   的调用点反查，或直接在 PCSX2 里对 `0x1FF695C` 下读断点）。
   ★ **本轮试过一次、没打中**：`zh113b_parse265`（`-grmaxframes 265 -grpcring 8192`）拿到的
   `exectrace_tail.txt` 最后 512 个执行块是**主等待循环 + BIOS 异常路径**
   （`0x00411EA8..0x00414E18`、`0x00411B20`、`0x80000180`…），**不是 FONT.RES 解析器** ——
   因为资源在 f258–262 就已经解析完，f265 已经过了。
   ⇒ 要打中请把窗口压到 **f255–f258**（`-grmaxframes 258`），或对 `0x1FF695C` 设读断点。
4. **在用户实机上抓"坏掉的那一刻"**（本地跑不出，只能靠实机）：
   * 用官方 PCSX2 的 `PauseOnTLBMiss`（`EmuCore/CPU/Recompiler`，默认关）打开 ⇒ 第一次
     TLB Miss 就会暂停在 `cpuRegs` 现场，可直接看 `$t9` / `$a0` 是哪个 bin、`$v0` 是不是 0；
   * 或在卡死前用官方 PCSX2 的调试器在 `0x0055B7A0`（分配器状态）上设**写断点**，
     看是哪条指令把它写坏的 —— 这一条与本地 `-grwatch 0x0055B7A0 0x200` 等效，
     而且用户环境能真正复现。
5. **补一轮"真在关卡里"的漂移取证**（本轮的最大缺口）：把 `nav_play.txt` 的
   F 段（f19400–f31400）删掉（它在 f19200 就已经把任务退成「统计」页了），
   或者改用默认 BIOS 重标定引导时序；目标是**进关卡后持续移动+开火 ≥72,000 帧**，
   再重复 §4 的比对。本轮已经把机器全部备好（`gen_input.py` 的动作循环、
   `run_memdrift.py` 的采样、`analyze_memdrift.py` 的对齐比对），只差一份落点正确的引导段。

---

## 9. 未达成项（如实列出）

1. **未复现卡死**（§2）。因此**没有"卡死瞬间"的内存快照**，§6 的 ④⑤ 两步仍是推断。
2. **未取得"关卡内 ≥20 分钟持续游玩"的帧**：汉化盘实际跑到 f30,600，其中
   **绝大部分在过场/菜单**（§4.8 有截图与 PC 分布证据）。英文原盘**跑满了 80,000 帧 / 26.2 分钟**，
   但同一脚本下同样以过场/菜单为主。⇒ **时长要求满足在"帧数/游戏时间"口径上，
   但"持续游玩"这个触发条件没有被覆盖**，这是本轮最大的缺口。
3. **用户存档在本地不可用**（§2.3）—— 这本是最接近定案的一条路，被模拟器构筑差异挡住；
   已把剩余差异列在 §7。
4. 未做 §8-1 的 `real=7222→5942` A/B（纪律禁止写 ISO），也未做 §8-2 的 `huge` 恢复实验。
5. §8-3 的解析器定位**试过一次但没打中**（窗口取晚了，见 §8-3 的★）。
6. 分配器状态的**逐帧**对照只做在用户存档那一轮（`memwatch 0x0055B000 0x2000 1`，
   但那一轮因存档不可用而作废）；两张盘的长回放用的是 2,500 帧粒度。**逐帧粒度仍待补**。
