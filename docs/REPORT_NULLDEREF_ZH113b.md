# REPORT_NULLDEREF_ZH113b.md — `GR_ZH113b` / `GR_ZH113b_fix` 硬卡死根因审计（只读诊断）

> 执行者 = 汉化执行者（NULL 解引用根因定位子代理）· 2026-10-15
> 仓库根 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> **只读**：`GR_ZH113b.iso`、`GR_ZH113b_fix.iso`、`GR_EN_ORIG.iso`、`third_party\orig\ps2\*.iso`、
> `%LOCALAPPDATA%\PCSX2` **一字未改**；未写任何 ISO；未 commit / 未切分支 / 未 merge。
> 写入范围仅：`work\builds\GR_NULLHUNT\**`、本文件。
> 全部命令与原始输出见 §8。**未使用 `Select-Object -First N`。**

---

## 0. 一句话结论

```
★ 先把任务书的一个前提纠正掉：
  emulog 里的 pc=0x101dd8 / 0x101e34 / 0x102008 / 0x1024d0 / 0x102584 不是 IOP 代码,
  而是 **EE 侧 SLUS_206.13 里游戏自带的 dlmalloc**:
     0x101D10..0x102018  chunk_free__FP6_arenaP12malloc_chunk
     0x102050..         chunk_alloc__FP6_arenaUl
  ⇒ 现象是"分配器的 bin 链表走到了 NULL": 0x1024D0 `ld t3,8(v0)` / 0x102584 `lw v0,20(v0)`,
     v0=0 ⇒ NULL+0x8 / NULL+0x14 反复缺页 ⇒ 画面静止。**这是堆被写坏的"受害者现场"，不是元凶。**

★ 本次审计把"汉化 vs 英文原盘"的全部差异过了一遍，得到两条硬结论：
  ① **容器/ISO 层是干净的** —— ISO9660 五盘逐字节相同; GR.IMG 条目表与原盘**逐字节相同**;
     MENU.IMG 条目表只差 **2 个条目 / 8 字节**; 名字区与哈希表**逐字节相同**;
     686 + 4070 个条目在汉化盘上 **0 越界 / 0 重叠 / 0 全零**;
     全盘 `stored > real`（历史上"读流截断 ⇒ 引擎空转"的根因）**0 条**;
     COMMON.PAK 记录链 4 条完好、末尾 `63 00 00 00` 哨兵在位（PAK+0x61D0F，两盘同址）。
     ⇒ **"汉化让某个资源读不出来 ⇒ 拿到 NULL 句柄"这条在容器层不成立。**
  ② **汉化对 ELF 的全部 68 处改动，其中 35 处集中在每帧都跑的中文文字/字体/UI 渲染链上**;
     18 个停顿 PC 的指令字节 **EN 与 ZH 完全相同**（元凶不在崩溃点，只在别处写坏堆）;
     并且 `ZH113b → ZH113b_fix` 的"+1 字节修复"实测就是**修了一个"读取偏移差 2"的错误**
     （`lhu a1,2(t0)` → `lhu a1,0(t0)`），**证明这一类错误确实被发布过**。

★ 新增的、此前报告中未出现过的两处硬不一致（见 §3.7，最高价值）：
  · FONT.RES：IMG 条目 `real`=7,222（未改），而 FONT.RES **内部头** `real`=5,942；
    明文从 7,222 B 缩到 5,942 B，尾部 2,924/3,081 B **全零**；'huge' 面记录数 **224 → 96**；
    MENU 与 GR 两份 FONT.RES 在英文盘上 md5 相同、在汉化盘上**不再相同**。
  · COMMON.PAK `new_font_revised`：**psm 0x13(PSMT8)/512×512 → 0x14(PSMT4)/1024×512**，
    而 `px_size` 恒为 0x40010、`clut_size` 恒为 1040 **未变**。
```

**我认为最可能的 1~2 条**：**候选 1（文字渲染链改写的变长步进/码位偏移 ⇒ 越界写 ⇒ 堆损坏）** 与
**候选 2（FONT.RES 内部头与条目 `real` 不一致 + 'huge' 面记录数腰斩）**。理由见 §4。

**本轮还结掉了一条我原本高度怀疑的方向（见 §4 候选 4、§8-13）**：
cave 落点 `sceRemove/sceMkdir/sceFormat/sceDopen/sceDclose` 在**英文原盘上调用者 = 0**
⇒ 汉化把它们当 code cave 用是**正确**的，**不是风险**；`sceIpuInit` 的 cave 落在其符号末尾的**全零空隙**。
⇒ 汉化的 cave 选址是经过功课的。**元凶更可能在"改了真在跑的代码"，而不在 cave 选址。**

---

## 1. 用户报告的硬事实复核（结果：全部复现，但 CPU 归属要纠正）

| 事实 | 复核结果 | 证据 |
|---|---|---|
| `GR_ZH113b_fix\emulog.txt` 尾部无限重复 `pc=0x1024d0 addr=0x8 [load]` / `pc=0x102584 addr=0x14 [load]` | ✅ 复现 | 该文件 731 行；`[224.4736]` 起 `0x1024d0/addr=0x8` ×17、`0x102584/addr=0x14` ×17，直到 `[233.5082] Pausing...` |
| "TLB Miss 共 50 条（PCSX2 上限）" | ✅ 该 log 里 TLB Miss 恰好 **50 条**（打满上限）。但分属**三次不同事件** | 命令 §8-2：`224.47` 段 **34 条**（`0x1024d0`/`0x102584`，**load**）；更早的两段共 **16 条**：`[124.98xx]` 10 条、`[152.4997]/[200.0484]` 6 条（`0x101dd8/0x101e34/0x102008`，**store**）|
| 早前两案 `F364/F365` 指纹 `0x101dd8/0x101e34/0x102008` | ✅ 同一族，但**同一个函数** | 见下表 |
| "IOP 侧代码在反复解引用 NULL+0x8 / NULL+0x14" | ❌ **前提错误** | 见下 |

### 1.1 ★ 停顿 PC 的准确归属（命令 §8-3）

`SLUS_206.13` ELF 头：`e_type=2 machine=8 entry=0x100008 phoff=0x34 phnum=2`；
`PH[0] off=0x80 vaddr=0x100000 filesz=0x4DED00` ⇒ **`FILE = VA − 0xFFF80`**（自证：VA `0x101DD8` → FILE `0x1E58`，反算一致）。

| VA | FILE | 符号 | 符号内偏移 | EN vs ZH 该地址 16 字节 |
|---|---|---|---|---|
| `0x00101D10` | 0x1D90 | `chunk_free__FP6_arenaP12malloc_chunk` | +0x0 | **SAME** |
| `0x00101DD8` | 0x1E58 | `chunk_free__FP6_arenaP12malloc_chunk` | +0xC8 | **SAME** |
| `0x00101DE4` | 0x1E64 | 同上 | +0xD4 | **SAME** |
| `0x00101E08` | 0x1E88 | 同上 | +0xF8 | **SAME** |
| `0x00101E34` | 0x1EB4 | 同上 | +0x124 | **SAME** |
| `0x00101E6C` | 0x1EEC | 同上 | +0x15C | **SAME** |
| `0x00101FE0` | 0x2060 | 同上 | +0x2D0 | **SAME** |
| `0x00102000` | 0x2080 | 同上 | +0x2F0 | **SAME** |
| `0x00102008` | 0x2088 | 同上 | +0x2F8 | **SAME** |
| `0x00102220` | 0x22A0 | `chunk_alloc__FP6_arenaUl` | +0x1D0 | **SAME** |
| **`0x001024D0`** | 0x2550 | `chunk_alloc__FP6_arenaUl` | **+0x480** | **SAME** |
| **`0x00102584`** | 0x2604 | `chunk_alloc__FP6_arenaUl` | **+0x534** | **SAME** |
| `0x001024E8` | 0x2568 | `chunk_alloc__FP6_arenaUl` | +0x498 | **SAME** |
| `0x0051B660` | 0x41B6E0 | `LoadingTexturePak__12UITextureMgrFiPCc` | +0x0 | SAME |
| `0x0051B7AC` | 0x41B82C | 同上 | +0x14C | SAME |
| `0x0051B0D8` | 0x41B158 | `GetTexture__12UITextureMgrFRC10RSFilename` | +0x98 | SAME |
| `0x0051C4C0` | 0x41C540 | `DecodeImage__9UITextureFPCci` | +0x1C0 | SAME |
| `0x003F6038` | 0x2F60B8 | `HandleControllerFiredWeapon__12AwarenessMgrFP13RSGameMessage` | +0x68 | SAME |

⇒ **18 个停顿/相关 PC 上，汉化一个字节都没改。** 元凶不在崩溃点。

### 1.2 死循环的准确形状（反汇编，EN 版；ZH 同字节）

```
0x001024C0  lw  v0,20(t9)        ; v0 = t9->bk            (t9 = bin)
0x001024C4  bc1?:  ...           ; 条件不满足则继续
0x001024C8  addiu t2,t2,1
0x001024D0  ld  t3,8(v0)         ; ★ 缺页 addr=0x8   ⇒ v0 == NULL  (读 v0->size)
0x001024D4  and  t8,t3,t5
0x001024D8  subu t3,t8,a1
0x001024DC  slti t4,t3,32
   ...
0x00102584  lw  v0,20(v0)        ; ★ 缺页 addr=0x14  ⇒ v0 == NULL  (读 v0->bk)
0x00102588  bne v0,t9,0x1024D0   ; v0(0) != bin ⇒ 跳回循环顶
```

即 dlmalloc `chunk_alloc` 的 **bin 链表遍历**：`for (victim = bin->bk; victim != bin; victim = victim->bk)`
在 `victim == NULL` 时既读 `+0x8` 又读 `+0x14`，两条都缺页 ⇒ 同时间戳无限重复。
`chunk_free` 侧的 `0x101DD8`（`lw t1,20(a1)` / `sw t1,20(t2)` / `sw t2,16(t1)`）就是 dlmalloc 的 **unlink**。
两者都只可能由 **堆元数据（bin 数组 / chunk 头）被写坏** 引起。

---

## 2. 审计方法（全部只读；脚本在 `work\builds\GR_NULLHUNT\tools\`）

| 脚本 | 作用 |
|---|---|
| `nh_lib.py` | ISO (mmap ACCESS_READ) / ISO9660 目录记录（含双端序自洽检查）/ IMG 头 + 48 B 条目表 |
| `nh_stage1.py` | 侦察：ISO 树 + IMG 头 + 条目数自证 + 锚点自证 |
| `nh_elf.py` / `nh_stage3_elf.py` | ELF 解析（PH/SH/symtab 38722 符号）、VA↔FILE、**精确**逐字节差异、停顿 PC 归属 |
| `nh_stage4_elfdis.py` | 每个 ELF 差异 run 的**指令级** EN/ZH 对照 |
| `nh_iso_diff.py` | 全盘逐字节差异（1 MB → 4 KB → 字节 run）并按 ISO9660 文件分类 |
| `nh_stage5_img.py` / `nh_query.py` | 两份 IMG 全部条目审计（stored≠real / 越界 / 重叠 / 对齐 / 空条目 / ZH-EN 逐字段） |
| `nh_stage7_iso9660.py` | 五盘 ISO9660 对照（含 `third_party\orig\ps2` 原始盘） |
| `nh_stage8_zhfix.py` | `ZH113b` vs `ZH113b_fix` 的精确差异 + VA 归属 |
| `nh_stage9_caves_res.py` | cave 空间原始内容核查 + 全条目可读性验证 |
| `nh_stage10_pak2.py` / `nh_stage11_fontres.py` / `nh_stage12_ftrec.py` | COMMON.PAK 记录链、FONT.RES LZO 子流、解压后字表记录结构 |
| `nh_stage13_ctx.py` | 关键差异点的上下文反汇编 |

**自证锚点（任务书给定，全部对上）**：`COMMON.PAK` `stored==real==400,659`；
`FONT.RES` `stored=4,421 / real=7,222`。⇒ 48 B 条目字段口径正确
（`u32[0]`=名字偏移、`u32[6]`=stored、`u32[7]`=real、`u32[8]`=off；表在容器 `+0x830`、步长 48）。

---

## 3. 审计结果

### 3.1 ISO9660 层（第 3 项任务）——**零差异**

命令 §8-6。五份盘（`third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso`、
`GR_EN_ORIG`、`GR_K99`、`GR_ZH113b`、`GR_ZH113b_fix`）：

```
全部 5 盘: size=1,648,164,864 B ; vol_size=804,768 ; root=(261,384) ; path=(257,26) ; 文件数=26
26 个文件的 LBA/长度:  相对 TRUE_ORIG 的不同条目数 = 0（五盘全 0）
双端序自洽 (ext_le==ext_be && sz_le==sz_be): 26/26 全部 True，五盘一致
字节级: LBA 0..16(系统/授权)=0  LBA 16..64(PVD+路径表)=0  LBA 256..261=0
        SYSTEM.CNF=0  目录区 LBA 262..294 = 0   (相对 TRUE_ORIG 的不同字节数)
```

| 文件 | LBA | 声明长度 | 五盘是否一致 |
|---|---|---|---|
| `/SLUS_206.13;1` | 295 | 37,453,732 | ✅ |
| `/GR.IMG;1` | 19,175 | 1,550,563,328 | ✅ |
| `/MENU.IMG;1` | 776,286 | 58,300,882 | ✅ |

⇒ **任务书里"ISO9660 里 MENU.IMG 的声明长度被改过"这一假设不成立**：
汉化盘与原盘的目录记录**逐字节相同**。`58,300,882 % 2048 = 466 ≠ 0` 是**原盘本来就有的**非扇区对齐，
不是汉化引入；五盘一致 ⇒ 与本次卡死无关。

### 3.2 两份 IMG 的全部条目（第 1 项任务）

`MENU.IMG` @LBA 776286 声明 58,300,882 B；`GR.IMG` @LBA 19175 声明 1,550,563,328 B。

| 盘 | IMG | 条目数 | 表末尾 vs 头 h3 | 空条目 | **stored>real** | stored≠real | stored或real=0 | off+stored 越界 | off+stored 与下一入口重叠 | off 未 2048 对齐 | 数据全零条目 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EN_ORIG | GR.IMG | 4070 | 0x30350 == 0x30350 | 0 | **0** | 1452 | 66 | 0 | 0 | 3875 | 0 |
| EN_ORIG | MENU.IMG | 686 | 0x88D0 == 0x88D0 | 0 | **0** | 212 | 0 | 0 | 0 | 678 | 0 |
| ZH113b | GR.IMG | 4070 | 0x30350 == 0x30350 | 0 | **0** | 1452 | 66 | 0 | 0 | 3875 | 0 |
| ZH113b | MENU.IMG | 686 | 0x88D0 == 0x88D0 | 0 | **0** | 212 | 0 | 0 | 0 | 677 | 0 |
| **ZH113b_fix** | GR.IMG | 4070 | 同上 | 0 | **0** | 1452 | 66 | 0 | 0 | 3875 | 0 |
| **ZH113b_fix** | MENU.IMG | 686 | 同上 | 0 | **0** | 212 | 0 | 0 | 0 | 677 | 0 |

**关键读数**：

* ★ **`stored > real` 全盘 0 条。** 历史上"`stored` 改大而 `real` 留旧值 ⇒ 读流在
  `min(stored,real)` 处截断 ⇒ `LoadingTexturePak` 记录链读不到 `0x63` 哨兵 ⇒ 无限循环"
  （`docs/REPORT_final_364.md` §3）**这一根因在本盘不成立**。
* 条目数 = **686（MENU）/ 4070（GR）**，不是任务书说的 682；表末尾与头字段 `h3` 精确吻合
  （`0x830 + 48×686 = 0x88D0`，`0x830 + 48×4070 = 0x30350`）。
* `stored == 0 或 real == 0` 的 66 条**在英文原盘上就存在**（`BNK_95_00.SB` 等，`u32[5]=1`，是空槽位），
  `GR.IMG` 两盘完全一致。
* 3875/3878 个条目 `off` 非 2048 对齐 —— **原盘如此**，不是汉化引入。
* **MENU.IMG 唯一"越界"是我的检查用 `off+max(stored,real)` 造成的假阳性**：
  `#25 EN_STRINGS.RES` 的 `off+stored = 58,187,776+47,570 = 58,235,346 ≤ 58,300,882` ✓；
  只是它的 `real=128,545` 是解压后大小，本来就大于容器余量。**判定：不是问题。**

### 3.3 ZH vs EN 逐字段差异（第 1 项任务）

命令 §8-5。**计划内 / 计划外分类结果**：

```
/GR.IMG;1 : EN_ORIG → ZH113b / ZH113b_fix
  仅 EN 有的名字 = 0 ; 仅 ZH 有的名字 = 0
  ★ 字段不同的条目数 = 0 / 4070      ← 条目表与原盘逐字节相同
  字节级: 条目表 0/195360 不同 ; 名字区 0/71621 ; 哈希区 0/16384 ; 头部 0/2096 ;
          数据区前 1 MB 0/1048576 不同

/MENU.IMG;1 : EN_ORIG → ZH113b / ZH113b_fix
  ★ 字段不同的条目数 = 2 / 686   （按字段统计 {'stored':2, 'real':1, 'off':1}）
  ★ 计划外（动了 u32[0] 名字偏移 或其它未预期字段）= 0 条
  字节级: 条目表 8/32928 不同（=2 条目×4 B）; 名字区 0/11542 ; 哈希区 0/16384 ; 头部 0/2096
```

| # | 名字 | EN: stored / real / off | ZH: stored / real / off | 判定 |
|---|---|---|---|---|
| 3 | `COMMON.PAK` | 400,659 / 400,659 / 357,376 | **完全相同** | 计划内（原地重写，字节数不变）|
| 4 | `FONT.RES` | 4,421 / 7,222 / 758,048 | **完全相同** | 计划内（**但内部头改了，见 §3.7**）|
| 25 | `EN_STRINGS.RES` | 47,570 / 128,545 / 58,187,776 | **完全相同** | 计划内（原地重写）|
| **30** | **`EN_STRINGS.TXT`** | 2,749 / 6,930 / **2,414,080** | **2,718 / 6,628 / 58,236,928** | 计划内（缩短 + **搬位**）|
| **282** | **`NTSC_IKE.RES`** | **38,051** / 319,009 / 57,309,200 | **38,284** / 319,009 / 57,309,200 | 计划内（原地 +233 B）|

* `#30 EN_STRINGS.TXT` 新位置 `58,236,928` **恰好 2048 对齐**（2048×28436），
  区间 `58,236,928..58,239,646` 落在声明长度 58,300,882 之内 ⇒ **不越界**。
* `#282 NTSC_IKE.RES` `real` 未变（319,009）、`off` 未变，`stored` +233 ⇒ 压缩流变长，**长度自洽**。

### 3.4 全盘差异地图（"汉化到底动了什么"）

命令 §8-4。`EN_ORIG` vs `ZH113b_fix`：**182 个 run / 2,026,149 B（全盘 0.122934%）**

| 区域 | run | 字节 |
|---|---|---|
| `/MENU.IMG;1` | 108 | 1,519,603 |
| `/GR.IMG;1` | 52 | 455,946 |
| `/SLUS_206.13;1` | 22 | 50,600 |
| ISO 系统区 / PVD / 目录记录 / 路径表 / MODULES | **0** | **0** |

⇒ **差异 100% 落在三个文件内**，没有任何"计划外区域"。

### 3.5 ELF 补丁面（第 4 项任务）——**68 处 / 1,849 字节，无一处计划外**

命令 §8-3。ELF 尺寸两盘相同（37,453,732 B）。精确差异 run **411** 个 / **1,849 B**；
按"间距 ≤4 B 合并"得 **68 处**（覆盖 2,392 B）。

**按所属函数归并（全部 68 处）**：

| 函数 | 处数 | 字节 | 归类 |
|---|---|---|---|
| `s_Pool` | 6 | 797 | **cave 代码**（EN 上前 791 B 全零，是真空）|
| `sceRemove` | 1 | 360 | **cave 代码**（EN 上是真代码！）|
| `sceMkdir` | 1 | 236 | cave（越过了符号 size 428 的 +0x160..+0x24C 边界）|
| `sceDclose` | 1 | 232 | cave（EN 上是真代码）|
| `sceDopen` | 1 | 192 | cave（越过了符号 size 200 的尾部）|
| `sceFormat` | 2 | 147 | cave（EN 上是真代码）|
| `sceIpuInit` | 1 | 24 | cave（EN 上 **ALL-ZERO**，是真空）|
| `strlwr` / `strupr` | 2+2 | 21 / 21 | cave（EN 上是真代码）|
| `@5689 @5690 @5694 @5695 @5696 @5698` | 6 | 166 | cave（EN 上是真**字符串**：见 §3.6）|
| `DrawString__9RSFontMgr…` | **12** | **46** | **中文文字路径** |
| `DrawText__10IkeButton3Fv` / `DrawText__15IkeKeyMapButtonFv` / `DrawText__13IkeBaseButtonFv` | 1+1+1 | 4+4+8 | 文字路径 |
| `ComputeDrawXY__15RSTextComponent…` | 4 | 12 | 文字路径（换行/坐标）|
| `DoWordWrap__15RSTextComponent…` | 3 | 16 | 文字路径（软换行）|
| `SetText__6RSHTMLFRC10RSUIString` / `SetText__15RSTextComponent…` | 1+1 | 8+8 | 文字路径 |
| `ReadResource__15RSTextComponent…` | 1 | 8 | 文字资源读取 |
| `DrawTheString__15RSTextComponent…` | 1 | 4 | 文字路径 |
| `StringWidth__6RSFontCFPCc` | 2 | 8 | 字体度量 |
| `CharWidth__6RSFontCFc` | 1 | 8 | 字体度量 |
| `ComputeCharTextureCoords__6RSFontCFcRfRfRfRf` | 1 | 8 | 字体 UV |
| `AddOneWord__9RSFontMgr…` | 2 | 2 | 字体顶点写入 |
| `Flush__9RSFontMgrFv` / `Draw__9RSFontMgrFv` | 1+1 | 1+1 | 字体提交 |
| `DrawLetters__12IkeFontTableFv` | 1 | **1** | 字体表遍历 |
| `SetLinearSampling__8UIPacketFb` | 1 | 4 | GS 纹理滤波 |
| `kShortcutDefaultSC__FUii` | 4 | 14 | 快捷键默认表 |
| `DrawNN__14NewPS2ShortcutFv` | 1 | 20 | 快捷键 UI |
| `GetUISoldierAbbreviateName__Fii` / `GetActorNameAbbreviated__9ActorFileCFv` | 1+1 | 4+4 | 名字缩写（中文姓名）|
| `DisplayMessages__11ChatDisplayFv` | 1 | 2 | 消息显示 |
| `kBtnExplanationMapMax` | 1 | 1 | 常量 |

**逐条要点（`stage4_elf_disasm.txt` / `stage13_ctx.txt` 全文可查）**：

```
run#0  DrawText__10IkeButton3Fv   +0x140 : subu v0,v1,v0        → addiu v0,v1,-21
run#1  DrawText__15IkeKeyMapButton+0x54 : subu v0,v1,v0        → addiu v0,v1,-16
run#2  DrawLetters__12IkeFontTable+0xB8 : addiu a3,s1,3        → addiu a3,s1,5     ★ 步长 3→5
run#3  DrawString__9RSFontMgr     +0x4  : sq ra,160(sp)        → j 0x565930       (cave→s_Pool)
run#4  DrawString                  +0x6C : (原指令)            → j 0x417200       (cave→sceFormat)
run#5  DrawString                  +0x15C: jal 0x40BFC8         → jal 0x416ED0     ★ 改调 DBCS 解码 cave
                                          addiu a0,sp,223      → addiu a0,sp,222
                                          lb a1,223(sp)        → lhu a1,222(sp)   ★ 1 字节读→2 字节读
run#6  DrawString                  +0x174: lb a1,223(sp)       → lhu a1,222(sp)
run#7  DrawString                  +0x199: addiu v1,zero,-75   → addiu v1,zero,181
run#8  DrawString                  +0x1A1: -75 / -79           → 181 / 177
run#9  DrawString                  +0x225: -75                 → 181
run#10 DrawString                  +0x230: lb a0,223(sp)       → lhu a0,222(sp)
run#11 DrawString                  +0x23D: -79                 → 177
run#12 DrawString                  +0x2B5: -75                 → 181
run#13 DrawString                  +0x2C9: -79                 → 177
run#14 DrawString                  +0x33C: nop ; addiu s0,s0,1 → lbu v0,221(sp) ; addu s0,s0,v0   ★★ 变长步进, 读 sp+221
run#15 AddOneWord__9RSFontMgr      +0xA4 : addiu a1,zero,1     → addiu a1,zero,0   (SetLinearSampling(pkt,true→false))
run#16 AddOneWord                  +0x1A8: 同上                 → 同上
run#17 Flush__9RSFontMgrFv         +0x34 : 同上                 → 同上
run#18 Draw__9RSFontMgrFv          +0x34 : 同上                 → 同上
run#19 StringWidth__6RSFont        +0x74 : jal 0x21AD10         → j 0x417150
run#20 StringWidth                 +0x90 : lw v0,24(s3)         → j 0x565670
run#21 CharWidth__6RSFont          +0x8  : lbu v0,36(a0) ; beq  → j 0x416F40 ; nop
run#22 ComputeCharTextureCoords    +0x0  : lw t2,40(a0) ; andi  → j 0x417050 ; nop   ★ 函数入口被重定向
run#48 sceRemove  body  由 cave 覆盖 360 B（符号 size 仅 28）
run#49 sceMkdir   +0x160 起覆盖 236 B（超出符号 size 428 的末尾）
run#52 sceDopen   +0x90  起覆盖 192 B（超出符号 size 200 的末尾）
run#53 sceDclose  +0xC8  起覆盖 232 B
run#54 SetLinearSampling +0x8 : 4 B
run#56..61 s_Pool +0x1E82..+0x2210 : cave 代码 797 B
run#62..67 @5689..@5698 : 覆盖 EN 上的多语言 loading 字符串 166 B
```

**计划外 ELF 差异：0 处。** 68 处全部落在上表函数内，没有一处在未被上述函数覆盖的地址；
ELF 头 / PH / SH / `.strtab` / `.symtab` / `.relmain` / `.debug` / `.line` **逐字节未动**
（差异 run 全部落在 `main` 节 VA 0x100000..0x5DED00 内）。

### 3.6 cave 空间核查：哪些是真空、哪些是**覆盖真代码**

命令 §8-8。**这是本次审计里最需要 Lead 注意的一条**：

| cave 区 | VA 区间 | EN 原盘内容 | 判定 |
|---|---|---|---|
| `sceIpuInit` | 0x411690..0x4116A7 (23 B) | **ALL-ZERO** | ✅ 真空 |
| `s_Pool #0..#5` | 0x565672..0x565A46 (791 B) | **ALL-ZERO** | ✅ 真空 |
| `strlwr` / `strupr` | 0x407078 / 0x408928 (19 B 各) | 真代码 | ⚠️ 覆盖 |
| `sceRemove` body | 0x416ED0..0x417037 (359 B) | 真代码（263/359 非零） | ⚠️ **覆盖 359 B** |
| `sceMkdir` tail | 0x417050..0x41713B (235 B) | 真代码 | ⚠️ 覆盖 |
| `sceFormat` | 0x417150..0x41721A (119+26 B) | 真代码 | ⚠️ 覆盖 |
| `sceDopen` tail | 0x417500..0x4175BF (191 B) | 真代码 | ⚠️ 覆盖 |
| `sceDclose` tail | 0x417600..0x4176E7 (231 B) | 真代码 | ⚠️ 覆盖 |
| `@5689` | 0x577FA0..0x577FB5 | `"Chargement en cours.."`（法语） | ⚠️ 覆盖**字符串** |
| `@5690` | 0x577FC0..0x578006 | `"Veuillez patienter !"` / `"Lade..."` / `"Bitte wa"` | ⚠️ 覆盖字符串 |
| `@5694` | 0x578010..0x57801F | `"Attendere prego"`（意） | ⚠️ 覆盖字符串 |
| `@5695` | 0x578028..0x578032 | `"Cargando.."`（西） | ⚠️ 覆盖字符串 |
| `@5696` | 0x578040..0x578061 | `"Espere, por favor..."` + `"Loading.."` | ⚠️ 覆盖字符串 |
| `@5698` | 0x578068..0x578073 | `"Please wait"` | ⚠️ 覆盖字符串 |

⇒ 汉化把 **DBCS 解码 cave 写进了 `sceRemove`/`sceMkdir`/`sceFormat`/`sceDopen`/`sceDclose` 的
真实函数体**（这些是 Sony SDK 的内存卡/文件 API 包装）。只有在"游戏从不调用它们"的前提下才安全；
**本次审计没有做调用者（xref）扫描，因此这一点是未达成的风险项**，见 §6。

### 3.7 ★ 新发现的两处硬不一致

#### (A) FONT.RES：**IMG 条目 `real` 与 FONT.RES 内部头 `real` 不一致**（命令 §8-9 / §8-10）

`FONT.RES` 自身是 `{u32 comp_len}{u32 real_len}{LZO 流}`：

| 盘 | IMG | 条目 stored / real | 内部头 comp / real | `comp+8` vs `stored` | 实际解压 | **残余** |
|---|---|---|---|---|---|---|
| EN_ORIG | MENU #4 | 4,421 / 7,222 | 4,413 / 7,222 | **4,421 == stored** ✅ | 7,222 == entry real ✅ | **0 B** |
| EN_ORIG | GR #906 | 4,421 / 7,222 | 4,413 / 7,222 | ✅ | ✅ | 0 B |
| **ZH113b(_fix)** | MENU #4 | **4,421 / 7,222** | **1,489 / 5,942** | **1,497 ≠ 4,421** ❌ | 5,942 | **2,924 B（全零）** |
| **ZH113b(_fix)** | GR #906 | **4,421 / 7,222** | **1,332 / 5,942** | **1,340 ≠ 4,421** ❌ | 5,942 | **3,081 B（全零）** |

解压后字表结构（命令 §8-11，口径 = `work\tools\zx_lib.ft_records`，`blob[24]` = 面数）：

| 项 | EN_ORIG | ZH113b_fix | 差 |
|---|---|---|---|
| 明文长度 | 7,222 B | **5,942 B** | **−1,280 B** |
| 面数 | 3（`large` / `default` / `huge`） | 3（同名） | 0 |
| `large` 记录数 | 32×7 = 224 | 32×7 = 224 | 0 |
| `default` 记录数 | 32×7 = 224 | 32×7 = 224 | 0 |
| **`huge` 记录数** | **16×14 = 224** | **16×6 = 96** | **−128** |
| 合计记录 | 672 | **544** | **−128** |
| `u` 取值范围 | [0, 513] | [0, 992] | 图集变宽（1024）|
| `v` 取值范围 | [0, 476] | MENU [195,498] / GR [178,436] | — |
| 明文 md5 | `965215984cc5958f6e390c6bc1122be5`（MENU 与 GR **相同**） | MENU `61821b97ff50f05c4e93f340fcdc83c5` / GR `1f517a009230610855ab3dbda51b7d9f` | **两份不再相同** |

⇒ 三个可独立指认的异常：
1. **条目 `real`(7,222) 与内容实际明文长度(5,942) 差 1,280 B**；
2. **`huge` 面的记录数组被砍掉 128 条（224→96）**，而 `large`/`default` 不变；
3. **同样的 FONT.RES 在 MENU.IMG 与 GR.IMG 两份副本上，英文盘逐字节相同、汉化盘不同**。

#### (B) COMMON.PAK `new_font_revised`：**psm / 尺寸换了，但 px_size 与 clut_size 没换**

命令 §8-9。记录链（两盘完全同址、尾部哨兵在位）：

```
EN_ORIG  COMMON.PAK = 400,659 B, 记录 4 条, 最后记录 end=0x61D0F, 尾料 4 B
  rec @0x0      arrow              mode=0 psm=0x0  32x32
  rec @0x1031   new_font_revised   mode=0 psm=0x13 512x512  clut=1040  px_size=0x40010  end=0x4147D
  rec @0x4147D  pda-lcd-02         mode=0 psm=0x13 256x256  clut=1040  px_size=0x10010
  rec @0x518C3  pda_counterparts   mode=0 psm=0x13 256x256  clut=1040  px_size=0x10010
  尾部 16 B: 63 00 00 00        ← ★ 记录链哨兵在 PAK+0x61D0F 就位
ZH113b(_fix) 完全相同的布局/长度/哨兵地址, 但:
  rec @0x1031   new_font_revised   mode=0 psm=0x14 1024x512 clut=1040  px_size=0x40010  end=0x4147D
                                     ↑ PSMT8→PSMT4      ↑ 宽 512→1024（px_size 与 clut_size 未变）
```

* `psm 0x13`(PSMT8, 8bpp)：`px_size = w*h + 16 = 512*512+16 = 0x40010` ✅ 自洽
* `psm 0x14`(PSMT4, 4bpp)：`px_size = w*h/2 + 16 = 1024*512/2+16 = 0x40010` ✅ 自洽
  （这也解释了为什么**条目表完全没动**：字库扩容是"同字节数换格式"，不是"PAK 变大"。
  任务书里"PAK 变大后 682 个条目整体后移"的假设**不成立**。）
* **但 `clut_size` 保持 1040 未变**（PSMT8 与 PSMT4 的调色板布局/条数并不相同），
  且**所有下游按 psm 分支的代码都没有对应的可见改动**（只有 `SetLinearSampling+0x8` 4 B）。

#### (C) `ZH113b → ZH113b_fix` 的"+1 字节修复"实测内容

命令 §8-7。全盘逐字节差异 **1 个 run、精确 1 个字节**，位置：

```
ELF FILE 0x465860..0x465861   VA 0x5657E0   (s_Pool +0x1FF0, 即汉化自己的 cave 代码)
   ZH113b     : 95 05 00 02   lhu a1,2(t0)
   ZH113b_fix : 95 05 00 00   lhu a1,0(t0)
上下文(fix 版):                                    ...  判据
   0x5657C8  lw t0,72(s0)
   0x5657CC  beq t0,zero,0x565828     ; t0 == NULL 就跳过
   0x5657D4  lw a0,4(t0)
   0x5657D8  beq a0,zero,0x565828     ; a0 == NULL 就跳过
 * 0x5657E0  lhu a1,0(t0)             ; 取 16 位码位 (修前是 +2)
   0x5657E4  jal 0x565760
```

⇒ **"+1 字节修复"就是修掉一个"读取偏移差 2"的错误。**
⇒ 这证明 **"cave 里的读取偏移写错"这一类错误确实被发布过（ZH113b）**，
  因此**同一类错误在其它 cave 站点上是否还有残留，是本次审计最应该追的线索** —— 见候选 1。

### 3.8 条目可读性验证（第 2 项任务）

命令 §8-8。对**两份 IMG 的全部条目**（686 + 4070），逐条用条目表字段算出区间并实际读取：

```
EN_ORIG      /MENU.IMG;1   条目=686   越界=0   数据全零=0
EN_ORIG      /GR.IMG;1     条目=4070  越界=0   数据全零=0
ZH113b_fix   /MENU.IMG;1   条目=686   越界=0   数据全零=0
ZH113b_fix   /GR.IMG;1     条目=4070  越界=0   数据全零=0
```

火箭筒 / L1 相关的候选条目（名字过滤命中 220 条，完整列表见
`work\builds\GR_NULLHUNT\evidence\gr_img_names_filtered.txt`、`menu_img_names.txt`）：

| IMG | # | 名字 | EN stored/real/off | ZH |
|---|---|---|---|---|
| MENU | 74 | `AT4.GUN` | 1,075 / 2,729 / 46,941,488 | **完全相同** |
| MENU | 106 | `RPG7.GUN` | 1,050 / 2,673 / 46,975,056 | **完全相同** |
| MENU | 108 | `RUSSIANAT4.GUN` | 1,040 / 2,599 / 46,977,184 | **完全相同** |
| MENU | 59 | `MISSILE.PRJ` | 936 / 936 / 46,927,008 | **完全相同** |
| MENU | 60 | `RPG7.PRJ` | 941 / 941 / 46,927,952 | **完全相同** |
| MENU | 282 | `NTSC_IKE.RES` | 38,051 / 319,009 / 57,309,200 | stored **38,284**（+233）|
| GR | 2798 / 2856 / 2861 / 2841 / 2857 | 同上一组 | — | **完全相同** |
| GR | 912 | `NTSC_IKE.RES` | 38,051 / 319,009 / 212,866,144 | **完全相同**（注意：MENU 那份改了，GR 这份没改！）|

⇒ **容器层没有"读不出来"的资源**。火箭筒与 L1 用到的资源条目在汉化盘上**字段与原盘一致、
区间不越界、数据非零**。（注：`NTSC_IKE.RES` 在 MENU 与 GR 上出现"改一份不改另一份"的
不一致，与 §3.7(A) 的 FONT.RES 现象同类，已在候选 2 中列出。）

---

## 4. 候选清单（按可能性排序）

> 每条 = 「差异点 → 为什么可能导致资源加载失败 / NULL 句柄 → 验证方法 → 我能否用现有工具验证」

### ★ 候选 1（最可能）：汉化改写的**中文文字渲染链**里有残留的"偏移/步进"错误 ⇒ 越界写 ⇒ 堆元数据被写坏

* **差异点（硬证据）**
  * 崩溃点在**游戏自带 dlmalloc**（`chunk_alloc`/`chunk_free`），而这 **18 个 PC 上汉化 0 字节改动**
    （§1.1）⇒ 崩溃点是受害者，元凶必须在**别处写坏堆**。
  * 汉化对 ELF 的 68 处改动里，**35 处**集中在这条**每帧都跑**的文字/字体/UI 链（§3.5）。
  * `DrawString +0x33C`：`nop ; addiu s0,s0,1` → **`lbu v0,221(sp) ; addu s0,s0,v0`**
    —— 循环步进从"固定 +1"改成"**从栈上读一个变长值**"；而同一函数另三处（+0x15C/+0x174/+0x230）
    读的是 **`sp+222`**，`+0x33C` 却读 **`sp+221`**（§3.5 run#14）。
  * `ZH113b → ZH113b_fix` 的**唯一** 1 字节修复，实测就是修同类的"读取偏移差 2"
    （`lhu a1,2(t0)`→`lhu a1,0(t0)`，§3.7(C)）⇒ **这一类错误确实上过盘**。
  * `DrawLetters +0xB8`：`addiu a3,s1,3` → `addiu a3,s1,5`（步长常数 +2）。
* **为什么会导致 NULL 句柄**
  文字渲染器把"码位 → 字形记录 → UV → 顶点"逐字写出。若步进/偏移错，字符索引会**越过字符串缓冲**
  或**越过字形记录数组**，取到垃圾宽度/UV；顶点写入量随之与预分配容量不符 ⇒ 越过顶点缓冲尾
  ⇒ 相邻 `malloc` chunk 头被写坏 ⇒ 之后任何一次 `free`/`malloc` 的 bin 链遍历走到 NULL
  ⇒ 就是观测到的 `ld t3,8(v0)` / `lw v0,20(v0)` 无限缺页。
* **与触发条件吻合**：火箭筒开火（HUD 武器提示）与 L1（小队/地图界面）都是"**突然要画大量中文字**"
  的瞬时事件；英文盘全是单字节 ASCII，走不到这条 2 字节路径 ⇒ 英文盘永不触发。
* **验证方法**
  1. **静态（我能做，未达成）**：把 `DrawString+0x33C` 的 `lbu v0,221(sp)` 与
     `lhu a1,222(sp)` 的栈偏移做成一致性表，逐一核对所有 cave 站点读/写的缓冲偏移是否互洽；
     顺带核对 `0x219EB0`(run#2 的被调者) 对 `a3` 的用法。
  2. **静态（我能做，未达成）**：用 `FONT.RES` 解出的字形记录表，把 L1/火箭筒 HUD 用到的
     中文字符逐个映射成 (面, 记录号)，检查是否越出 `huge` 面的 96 条记录。
  3. **实机 A/B（需用户）**：出两版对照盘 —— ① 把 `+0x33C` 改回 `nop ; addiu s0,s0,1`；
     ② 把 `lbu v0,221(sp)` 改成 `lbu v0,222(sp)`。跑同一流程（火箭筒开火 / L1）。
  4. **实机取证（需用户）**：在 `AddOneWord`(0x219F50) / `Flush`(0x21A1A0) / `Draw`(0x21A2A0)
     下写监视，量顶点缓冲的**实际写入上界**。

### ★ 候选 2（次可能）：`FONT.RES` 的内部头与 IMG 条目 `real` 不一致 + `huge` 面记录数腰斩

* **差异点（硬证据，§3.7(A)）**
  * 条目 `real` = 7,222（**汉化没改**），FONT.RES 内部头 `real` = **5,942**，明文实长 = **5,942**。
  * 尾部残余 **2,924 B（MENU）/ 3,081 B（GR）全零**。
  * `huge` 面记录数 **224 → 96**（`large`/`default` 不变），合计 672 → 544。
  * **MENU 与 GR 两份 FONT.RES 在英文盘上 md5 相同，在汉化盘上不同**。
  * 同类现象还有：`NTSC_IKE.RES` #282（MENU）`stored` +233 而 GR #912 未改（§3.8）。
* **为什么会导致 NULL 句柄**
  * 项目已证的引擎口径是 **读流上界 = `min(stored, real)`**（`docs/REPORT_final_364.md` §3）。
    若 `RSFontMgr` 按条目 `real`(=7,222) 分配/解压，则尾部 **1,280 B 落在未初始化堆**上；
    字表解释器一旦走过 5,942 B 就会把未初始化垃圾当作记录。
  * `huge` 面只剩 96 条 ⇒ 任何以"记录号 ≥ 96"索引该面的字符都会**越出记录数组**进入
    那 278 B 尾部与之后的堆，取到垃圾 UV/宽度。
  * 而被汉化 **cave 重定向**的正是 `CharWidth`(+0x8 → `j 0x416F40`)、
    `ComputeCharTextureCoords`(+0x0 → `j 0x417050`)、`StringWidth`(+0x74/+0x90)、
    `DrawLetters`(+0xB8) —— 垃圾宽度/UV 会直接进入顶点与换行计算。
  * 大量中文字（L1 界面、武器提示）恰恰是**最可能命中 `huge` 面高位记录号**的地方。
* **验证方法**
  1. **静态 A/B（需重编盘，我未做）**：① 把 FONT.RES 明文补零回 7,222 B 并把内部头 `real` 改回
     7,222（`stored` 保持 4,421 不变 —— 因为同一 LZO 流可补零）；② 或把条目 `real` 改成 5,942。
     跑同一流程对比。
  2. **静态（我能做，未达成）**：把 `huge` 面的记录矩形与 `new_font_revised` 图集的
     实际槽位布局对账，确认 96 条是否覆盖了汉化文本实际用到的全部大字字符。
  3. **静态（我能做，未达成）**：确认 MENU 与 GR 两份 FONT.RES 该用哪一份、何时用；
     "改一份不改另一份"是否会命中。
  4. **内存取证（需用户）**：卡死时 dump EE RAM，找 `new_font_revised.rsb` 字表，
     量出**实际被写入的长度**（5,942 还是 7,222）与尾部内容 —— 这一条能一次性判定引擎用哪个长度。

### 候选 3：图集 **PSM 0x13(PSMT8)→0x14(PSMT4)** 但 `clut_size`/下游按 psm 分支的代码没跟着改

* **差异点（§3.7(B)）**：`new_font_revised` 由 `psm=0x13, 512×512` 变成 `psm=0x14, 1024×512`，
  `px_size=0x40010` 与 `clut_size=1040` **都没变**。
* **机理**：`psm` 是 GS `TEX0` 的位域，决定纹理解码方式；若任何一处按 8bpp 计算纹理字节数/
  线性偏移/调色板条数（`DecodeImage`、`SetLinearSampling`、`ComputeCharTextureCoords` 都被汉化碰过），
  纹理解码/上传就越界 → 堆损坏 → 分配器 bin 走空。
  另外 PSMT4 的调色板是 16 色/索引 4 bit，而 `clut_size=1040`（≈ 256 色 + 头）**是 PSMT8 的口径**。
* **验证方法**：① 实机 GS dump 看 `TEX0` 的 PSM 实际值（需用户）：
  ② 静态 A/B 把 `psm` 改回 `0x13` 且 `h=512`（牺牲字库容量）跑同一流程（需重编盘）。
* **我能否验证**：结构事实 ✅ 已证（§3.7(B)）；因果链 ❌ 需实机。

### 候选 4 —— **已排除**（本轮补做 xref 扫描后推翻）：cave 落点是游戏**从不调用**的函数

命令 §8-13。在**英文原盘** ELF 的 `main` 段全量扫描 `jal`/`j`，统计每个 cave 落点的调用者：

```
目标             VA           EN 调用数   汉化新增调用 (ZH − EN)
sceRemove      0x00416ED0    0          +0x219BCC     (汉化注入, 即 DrawString+0x15C)
sceMkdir       0x00416EF0    0          -
sceFormat      0x004170C0    0          -
sceDopen       0x00417470    0          -
sceDclose      0x00417538    0          +0x41765C/0x41768C/0x4176BC (cave 自调用)
sceIpuInit     0x00411458    1 (0x42878C)  -          ← 调用的是函数入口, cave 在其 +0x238 (EN 全零的空隙)
strlwr         0x00407060    3          -             ← ★ 被真正调用
strupr         0x00408910    8          -             ← ★ 被真正调用
cave@417050/417150/417200/417500/416F40/565930/565670  0  各 +1 (即汉化注入的跳转)
```

⇒ **`sceRemove`/`sceMkdir`/`sceFormat`/`sceDopen`/`sceDclose` 在英文原盘上调用者 = 0**
⇒ 汉化把它们当 code cave 用是**正确的**，**不构成风险**。
⇒ 汉化注入的每个 cave 目标都是 **EN=0 → ZH=1..3**，形状完全自洽（既有调用点被 `j` 改写 → cave → cave 再 `jal` 到这些死函数）。**本条作废。**

### 候选 5：`strlwr` / `strupr` 的函数体被改（这两个函数**确实被调用** 3 次 / 8 次）

* **差异点**：`strlwr+0x18..+0x2B`(20 B) + `strlwr+0x36`(1 B)、`strupr+0x18..+0x2B` + `+0x36`。
  反汇编显示改动是插入 ASCII 范围判断：`80 00 61 2c` = **`sltiu at,v1,128`**
  （原指令为 `00 16 03 00` 之类的移位组合）。
* **判断**：这是**必要的**修正（不做的话 DBCS 中文会被大小写转换破坏），
  语义方向正确；但它把 **11 个调用点**的行为从"转换全部字节"改成"只转换 <0x80 的字节"。
* **为什么仍列为候选**：任何依赖"高字节也被折叠"的调用者会拿到不同字符串
  ⇒ 若其后按长度/偏移拷贝，理论上可能越界。**与火箭筒/L1 的关联弱。**
* **验证方法（我可做，未达成）**：看这 11 个调用点（`0x53D894 / 0x540038 / 0x54898C /
  0x4D14DC / 0x4D1F14 / 0x4D3858 / 0x50BC18 / 0x50C680 / 0x53D944 / 0x540118 / 0x548900`）
  各自的上下文类型。

### 候选 6 —— **降级**（本轮补查后）：`EN_STRINGS.TXT`(#30) 搬位，旧位置**内容完好**，不构成卡死风险

命令 §8-13。`MENU.IMG + 2,414,080`（旧位置）在汉化盘上与英文原盘**逐字节完全相同**
（`213/2749` 全零字节、前 64 B 十六进制一致、可打印预览一致：`1// weapons and items..."WPN_M4"...`）
⇒ **旧副本没有被零化、也没有被覆写**。新位置 `58,236,928` 的内容是同一份资源的重压版
（头部 `u32 comp/real` 由 `b5 0a 00 00 / 12 1b 00 00` 变为 `96 0a 00 00 / e4 19 00 00`）。
⇒ 风险只剩"**若有按固定偏移读它，会读到旧英文文本**"（**文本正确性问题，不是 NULL/卡死**）。
* 补充：ELF 内"低 16 位等于 0x24D400"的立即数在 EN 有 663 处、ZH 661 处，
  **未做全局常量折叠，无法据此判定**（本项**未达成**）。

### 候选 7（低）：多语言 loading 字符串常量区（`@5689..@5698`）被中文覆盖

* **差异点（§3.6）**：EN 上是 `"Chargement en cours.."`(FR) / `"Veuillez patienter !"`(FR) /
  `"Lade..."`/`"Bitte wa"`(DE) / `"Attendere prego"`(IT) / `"Cargando.."`(ES) /
  `"Espere, por favor..."` + `"Loading.."` / `"Please wait"`；ZH 处被写成 GBK 中文。
* **机理**：这些是 NUL 结尾的常量串，按指针读 ⇒ 风险仅来自"若某处按固定长度拷贝"。
  与火箭筒/L1 的关联很弱；方向上很可能是**有意的**（把 EN 之外的语言槽回收成中文）。
* **验证方法（我可做，未达成）**：找 `0x577FA0 / 0x577FC0 / 0x578010 / 0x578028 / 0x578040 / 0x578068`
  的引用点，检查是否有长度假设。
* **我能否验证**：部分可以（静态，需要 pointer-to-constant 的 xref，比 `jal` 扫描麻烦）。

### 已排除（同样重要，避免重复劳动）

| 假设 | 判定 | 证据 |
|---|---|---|
| "`stored != real` 导致读流截断 ⇒ 引擎空转"（F364 根因）| ❌ **不成立** | 六盘（3 盘 × 2 IMG）`stored > real` **0 条**（§3.2）|
| "COMMON.PAK 变大 ⇒ 682 条目整体后移" | ❌ **不成立** | COMMON.PAK `stored==real==400,659`，条目表**逐字节未动**（§3.3）|
| "`LoadingTexturePak` 读不到 `0x63` 哨兵 ⇒ 死循环" | ❌ **不成立** | 记录链 4 条完好、哨兵在 PAK+`0x61D0F`、两盘同址（§3.7(B)）|
| "ISO9660 声明长度被改 / 非扇区对齐 ⇒ 启动挂" | ❌ **不成立** | 五盘 ISO9660 **逐字节相同**；非对齐是原盘自带（§3.1）|
| "某个资源读不出来 ⇒ 拿到 NULL 句柄" | ❌ **容器层不成立** | 686+4070 条目 **0 越界 / 0 重叠 / 0 全零**（§3.2、§3.8）|
| "汉化改坏了崩溃点代码" | ❌ **不成立** | 18 个停顿 PC 的指令字节 **EN==ZH**（§1.1）|
| "4 处 `addiu a1,zero,1→0` 改坏了写入量" | ❌ **不成立** | 上下文证明是 `SetLinearSampling(pkt, true→false)`，只影响 GS 纹理滤波（§8-12）|
| "名字表 / 哈希表被改 ⇒ 查找失败" | ❌ **不成立** | 名字区、哈希区、IMG 头全部**逐字节相同**（§3.3）|
| "cave 覆盖了游戏会调用的 SDK 函数 ⇒ 执行到 DBCS 解码器" | ❌ **不成立** | xref 扫描：`sceRemove/sceMkdir/sceFormat/sceDopen/sceDclose` 在英文原盘上**调用者 = 0**；`sceIpuInit` 的 cave 落在其符号末尾的**全零空隙**（§8-13）|
| "`EN_STRINGS.TXT` 搬位导致旧位置被零化/读到脏数据" | ❌ **不成立** | 旧位置在汉化盘上与英文原盘**逐字节完全相同**（§8-13）|

---

## 5. 我能用现有工具验证 vs 需要实机 A/B

| 项 | 我能否验证 | 状态 |
|---|---|---|
| `stored>real` / 越界 / 重叠 / 对齐 / 空条目 | ✅ 已做 | 完成（§3.2）|
| ZH vs EN 逐字段差异分类 | ✅ 已做 | 完成（§3.3）|
| ISO9660 五盘对照 | ✅ 已做 | 完成（§3.1）|
| ELF 全部字节差异 + 指令级对照 + 计划外判定 | ✅ 已做 | 完成（§3.5）|
| cave 空间是否真空白 | ✅ 已做 | 完成（§3.6）|
| FONT.RES 内部头 / 明文长度 / 记录结构 | ✅ 已做 | 完成（§3.7(A)）|
| COMMON.PAK 记录链 + psm/尺寸 | ✅ 已做 | 完成（§3.7(B)）|
| `ZH113b→fix` 的 1 字节内容 | ✅ 已做 | 完成（§3.7(C)）|
| cave 站点读取偏移一致性表（候选 1-验证①）| ✅ 能做 | **未达成** |
| L1/火箭筒字符 → `huge` 面记录号是否越界（候选 1-验证②）| ✅ 能做 | **未达成** |
| `sce*` cave 落点的调用者 xref 扫描（候选 4）| ✅ 已做 | **完成 → 候选 4 已排除**（§8-13）|
| `EN_STRINGS.TXT` 旧位置内容（候选 6）| ✅ 已做 | **完成 → 候选 6 已降级**（§8-13）|
| `@5689..@5698` 字符串引用点（候选 7）| ✅ 能做 | **未达成** |
| `strlwr`/`strupr` 11 个调用点的上下文（候选 5）| ✅ 能做 | **未达成** |
| "引擎用条目 `real` 还是 FONT.RES 内部 `real`" | ❌ **必须实机**（内存取证/断点） | 未达成 |
| 顶点缓冲实际写入上界 | ❌ **必须实机**（写监视） | 未达成 |
| 任何 A/B 因果确认 | ❌ **必须重编盘 + 实机**（本轮禁止写 ISO） | 未达成 |

---

## 6. 未达成项（如实列出）

1. **本轮没有跑 PCSX2**（任务书说"原则上不需要跑"），因此**没有新的断点/内存取证数据**；
   所有因果链都仍是"候选"，未做实机确认。
2. **没有做任何 A/B 盘**（禁止写 ISO）。候选 1/2/3 的验证必须由能写盘的执行者做。
3. **仍未做的静态验证**（现有只读工具就能做）：
   ① cave 站点「读写偏移一致性表」——候选 1 的核心疑点；
   ② 把 L1/火箭筒 HUD 用到的中文字符映射到 `huge` 面的记录号，看 96 条是否够——候选 2 的核心疑点；
   ③ `@5689..@5698` 字符串的引用点（pointer-to-constant xref）——候选 7；
   ④ `strlwr`/`strupr` 那 11 个调用点的上下文类型——候选 5；
   ⑤ 判定 `s_Pool` 这 40,960 B 在运行期的用途。
   （**已补做并结掉**：`sce*` cave 落点 xref → 候选 4 排除；`EN_STRINGS.TXT` 旧位置 → 候选 6 降级。）
4. **没有建立 cave 站点"读写偏移一致性表"**，因此没能判定 `DrawString+0x33C` 的 `sp+221`
   究竟是笔误还是刻意（候选 1 的核心疑点）。
5. **没有把 L1/火箭筒 HUD 实际用到的中文字符映射到 `huge` 面的记录号**，
   因此无法判定 `huge` 面 224→96 是否已越界使用（候选 2 的核心疑点）。
6. **`s_Pool` 的语义未确认**：我只证明它在英文原盘上前 791 B **全零**（因此前 791 B 可用作 cave），
   但没有确认这 40,960 B 的对象在运行期做什么、汉化写入的 791 B 是否会被引擎自己覆盖/使用。
7. **`NTSC_IKE.RES` #282（MENU）`stored` +233 的合法性未判**，只做了"区间在容器内、非零"的核对。
8. **未证明两次卡死是同一根因**：`[152.5]/[200.0]` 的 store 型
   (`0x101dd8/0x101e34/0x102008`) 与 `[224.5]` 起的 load 型 (`0x1024d0/0x102584`)
   落在**同一个 dlmalloc 的两个不同函数**上；我按"同一族（堆元数据被写坏）"处理，但没有证明是同一处写入者。
9. **未审计 `GR.IMG` 数据区**：`GR.IMG` 全盘有 52 个差异 run / 455,946 B，我确认了
   "条目表逐字节相同、无越界"，但**没有逐个核对这 52 处的内容语义**（它们主要是
   `EN_STRINGS.RES`@GR#902 与 `COMMON.PAK`@GR#3451 的原地重写）。
10. **未审计 `MENU.IMG` 的 108 个差异 run 的语义**，只核对了条目层与 FONT.RES/COMMON.PAK。

---

## 7. 建议 Lead 的下一步（按性价比）

1. **先做三项零成本静态验证**（都用现成只读工具，≈30 分钟）：
   cave 站点偏移一致性表、`huge` 面记录号越界检查、`sce*` cave 落点 xref 扫描。
2. **再做一版最小 A/B 盘（只改 1~2 字节）**去实机打靶，优先级：
   ① `DrawString+0x33C` 的 `lbu v0,221(sp)` → `lbu v0,222(sp)`（VA `0x00219DAC`）；
   ② `DrawString+0x33C` 整对改回原盘 `nop ; addiu s0,s0,1`；
   ③ 把 FONT.RES 内部头 `real` 与条目 `real` 对齐（两个方向各一版）。
3. **一次内存取证**能同时结掉候选 2：卡死时 dump EE RAM，量 `new_font_revised.rsb`
   字表在内存里的实际长度（5,942 还是 7,222）。

---

## 8. 命令与证据索引

全部脚本在 `work\builds\GR_NULLHUNT\tools\`，全部证据在 `work\builds\GR_NULLHUNT\evidence\`。
**全部命令都是只读**（`mmap(..., ACCESS_READ)`；无任何 `open(...,'wb')` 指向既有 ISO）。

| # | 命令 | 产出证据文件 |
|---|---|---|
| 1 | `python work\builds\GR_NULLHUNT\tools\nh_stage1.py` | `evidence/stage1_iso_tree.txt`、`stage1_img_head.txt` |
| 2 | `$m = Select-String work\builds\GR_ZH113b_fix\emulog.txt -Pattern 'TLB Miss'; $m.Count` → `50`；按行分组落盘 | **`emulog_tlbmiss_grouped.txt`** |
| 3 | `python work\builds\GR_NULLHUNT\tools\nh_stage3_elf.py` | `stage3_elf_layout.txt`、**`stage3_stall_pc.txt`**、`stage3_elf_diff.txt`、`stage3_elf_diff.json` |
| 4 | `python work\builds\GR_NULLHUNT\tools\nh_iso_diff.py EN_ORIG ZH113b_fix` | `stage2_isodiff_EN_ORIG_vs_ZH113b_fix.txt` |
| 5 | `python work\builds\GR_NULLHUNT\tools\nh_stage5_img.py` | **`stage5_img_audit.txt`**（3.0 MB）、`stage5_img_fields.json` |
| 6 | `python work\builds\GR_NULLHUNT\tools\nh_stage7_iso9660.py` | **`stage7_iso9660.txt`** |
| 7 | `python work\builds\GR_NULLHUNT\tools\nh_stage8_zhfix.py` + `nh_iso_diff.py ZH113b ZH113b_fix` | **`stage8_zh113b_vs_fix.txt`**、`stage2_isodiff_ZH113b_vs_ZH113b_fix.txt` |
| 8 | `python work\builds\GR_NULLHUNT\tools\nh_stage9_caves_res.py` | **`resource_candidates.md`**、`menu_img_names.txt`、`gr_img_names_filtered.txt` |
| 9 | `python work\builds\GR_NULLHUNT\tools\nh_stage10_pak2.py` | **`stage10_pak_fontres.txt`** |
| 10 | `python work\builds\GR_NULLHUNT\tools\nh_stage11_fontres.py` | **`stage11_fontres_streams.txt`** |
| 11 | `python work\builds\GR_NULLHUNT\tools\nh_stage12_ftrec.py` | **`stage12_ftrec.txt`** |
| 12 | `python work\builds\GR_NULLHUNT\tools\nh_stage13_ctx.py` | **`stage13_ctx.txt`** |
| 13 | `python work\builds\GR_NULLHUNT\tools\nh_query.py` | `stage6_query.txt` |
| 14 | `python work\builds\GR_NULLHUNT\tools\nh_stage4_elfdis.py` | **`stage4_elf_disasm.txt`**（90 KB，68 处逐指令对照） |
| 15 | `python work\builds\GR_NULLHUNT\tools\nh_stage14_xref.py` | **`stage14_xref.txt`**（cave 落点调用者 xref + `EN_STRINGS.TXT` 旧位置 + 立即数搜索）|

> 注：全部脚本只读（`mmap(..., ACCESS_READ)`），对本报告引用到的每一份既有 ISO **没有任何写入**；
> 唯一被本任务写入的位置是 `work\builds\GR_NULLHUNT\**` 与 `docs\REPORT_NULLDEREF_ZH113b.md`。
> `evidence/` 目录清单（15 个文件）：
> `stage1_iso_tree.txt` `stage1_img_head.txt` `emulog_tlbmiss_grouped.txt`
> `stage2_isodiff_EN_ORIG_vs_ZH113b_fix.txt` `stage2_isodiff_ZH113b_vs_ZH113b_fix.txt`
> `stage3_elf_layout.txt` `stage3_stall_pc.txt` `stage3_elf_diff.txt` `stage3_elf_diff.json`
> `stage4_elf_disasm.txt` `stage5_img_audit.txt` `stage5_img_fields.json` `stage6_query.txt`
> `stage7_iso9660.txt` `stage8_zh113b_vs_fix.txt` `stage9 → resource_candidates.md`
> `menu_img_names.txt` `gr_img_names_filtered.txt` `stage10_pak_fontres.txt`
> `stage11_fontres_streams.txt` `stage12_ftrec.txt` `stage13_ctx.txt`
