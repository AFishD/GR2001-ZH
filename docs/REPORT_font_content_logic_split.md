# REPORT_font_content_logic_split.md — 字库「内容 / 逻辑」分离的反编译结论

> ⚠ **历史错误断言订正（2026-10-18 收尾轮）**：本文含已被实测/实机否证的表述 —— 见 `docs/CORRECTIONS.md` §1。
> 原文保留作过程记录；**结论冲突时以 `docs/CORRECTIONS.md` + `docs/STATUS.md` 为准**。

> 面向目标：**结合 PC 版结构，把内容与逻辑彻底拆开，最终完全利用 ISO 空位实现完全扩容不缺字**。
> 本轮用 Ghidra（r5900 处理器工程 `GRLocEE`）反编译了字体与资源查找链，回答"容量上限到底在哪一层"。

---

## 一、★ 结论先行：**字形容量在 ELF 里没有固定上限**

`RSFontMgr::ReadResourceFile(const char*)`（入口 `0x00219380`，1284 B，2 个调用者：
`IkeUIMgr::PreInit` `0x274F20` / `IkeUIMgr::Create` `0x2750F0`）反编译原文（节选）：

```c
void ReadResourceFile__9RSFontMgrFPCc(int param_1, undefined8 param_2)
{
  uVar2 = diSearchFile(param_2);                       // 按文件名找到字体资源
  __ct__9idistreamFi(auStack_8240, 1, uVar2);
  Read__(auStack_8240, auStack_8258);                  // ★ 读一个字符串
  ConvertToRSString__10RSUIStringCFv(auStack_8250, auStack_8258);
  __ct__10RSFilenameFRC8RSString(auStack_20, auStack_8250);
  __as__10RSFilenameFRC10RSFilename(param_1 + 0x1c, auStack_20);   // ★★ 存进 mgr+0x1c
  ...
  read__(auStack_8240, &iStack_8244, 4);               // ★ 4 字节 = face 数
  for (iVar4 = 0; iVar4 < iStack_8244; iVar4++) {      // 逐 face
      读一个字符串 + 14 个 4 字节字段
      iVar6 = iStack_a0 * iStack_9c;                   // ★ nrec = fld[4] × fld[5]
      lVar3 = __nwa__FUi(iVar6 * 10 + 0x10);           // ★ 按 nrec 动态分配（10 B/条）
      iVar1 = __construct_new_array(lVar3, 0x2199e0, 0, 10, iVar6);
      ... 每条记录：读 1 字节、1 字节，再 4 个 2 字节（= u0/v0/u1/v1）...
```

### 由此确立的三条

| # | 事实 | 出处 |
|---|---|---|
| 1 | **`mgr+0x1c` 里放的"贴图名"来自资源文件里的第一个字符串** | 上面的 `__as__(param_1+0x1c, …)`；与旧报告 `GetTexture(ui_text_mgr, mgr+0x1c)` 一致 |
| 2 | **记录条数 `nrec = fld[4] × fld[5]`，用 `__nwa(nrec*10+0x10)` 动态分配** | 同上 ⇒ **ELF 侧无固定上限**，只由资源里的两个字段决定 |
| 3 | **face 数是从文件读的 4 字节** | 同上 ⇒ 同样数据驱动 |

⇒ **⇒ 也就是说：字体资源 = 「贴图名 + face 数 + 每 face 的 W/H + 记录表」，全是**数据**；
"逻辑"只是 ELF 里的采样/寻址代码。**
⇒ **⇒ 想扩容，本质上只要：换一张更大的贴图 + 把资源里的"贴图名"改成指向它。记录表会跟着 W×H 自动扩大。**

---

## 二、贴图是**按文件名**找到的，查找走 IOP 的 RPC

```
LoadIndexedRSB__12UITextureMgrFRC10RSFilename   @0x51B230  376 B  1 调用者
  └ 被 GetTexture__12UITextureMgrFRC10RSFilename @0x51B040  248 B  21 调用者 调用

  uVar5 = <文件名>;
  uVar2 = diSearchFile(uVar5);            // ★ 按文件名搜索
  __ct__9idistreamFi(..., uVar2);
  lVar3 = __nw__FUi(0x50);                // 分配 UITexture（0x50 B）
  __as__8RSStringFRC8RSString(puVar6+0xe, name);   // 名字存进 UITexture+0x38
  lVar4 = LoadRSBFile(lVar3, ...);        // 解析 RSB 流
```

```
diSearchFile    @0x4D1290   64 B  **29 个调用者**
diSearchFileEx  @0x4D11D0  188 B  13 个调用者
  piVar1 = (int *)eeRpcSendCommand(**0xffffffff80010010**, param_1);   // ★ 发 RPC 给 IOP
  if (-1 < *piVar1) { *param_2 = piVar1[1]; *param_3 = piVar1[2]; ... }  // [句柄, LBA, 大小, …]
```

**⇒ 所有资源查找（字体资源、贴图 RSB、模型、地图、音效…）都经这一个 RPC 落到 IOP。**
`diSearchFile` 的 29 个调用者里包含：`RSFontMgr::ReadResourceFile`、`UITextureMgr::LoadIndexedRSB`、
`LoadingTexturePak`、`RSRootContainer::ReadResourceFile`、`RSFileData::FindFile/Register/RegisterFullPath`、
`RSStrMgr::ReadKeyStrings/ReadResourceFile`、`RSModsFinder/RSModsSystem` 等。

**⇒ 因此"大贴图能不能放在别处"取决于 IOP 侧挂了哪些容器、按什么顺序搜**（模块就在盘上：
`MODULES\RPC.IRX` 230,000 B、`MODULES\IOPRP242.IMG` 252,409 B，**都是未压缩/半压缩的 IOP 模块**，可继续逆向）。
ELF 侧只发现通用挂载入口 `sceMount` @0x417F80（620 B）与 `sceUmount` @0x4181F0（28 B）。

---

## 三、字体管理器全部函数一览（供后续工作直接引用）

| 函数 | 地址 | 大小 | 调用者 |
|---|---|---|---|
| `RSFontMgr::ReadResourceFile(const char*)` | 0x00219380 | 1284 | 2 |
| `RSFontMgr::DrawString(...)` 三个重载 | 0x00219A70 / 0x00219E00 / 0x00219EB0 | 12 / 176 / 72 | 7 / 2 / 13 |
| **`RSFontMgr::AddOneWord(...)`** | 0x00219F50 | 572 | 0（虚调用）|
| `RSFontMgr::Flush()` | 0x0021A190 | 248 | 12 |
| `RSFontMgr::Draw()` | 0x0021A290 | 196 | 4 |
| `RSFontMgr::Reset()` | 0x0021A360 | 80 | 5 |
| **`RSFontMgr::ReallocateSize(int)`** | 0x0021A3B0 | 160 | 1 |
| `RSFontMgr::Initialize(int)` | 0x0021A450 | 24 | 0 |
| `RSFontMgr::Create()` | 0x0021A5B0 | 284 | 2 |
| `RSFontMgr::GetFont(int)` / `Get()` | 0x003A17D0 / 0x003A17E0 | 8 / 12 | 4 / 4 |
| `UITextureMgr::GetTexture(const RSFilename&)` | 0x0051B040 | 248 | 21 |
| `UITextureMgr::LoadIndexedRSB(const RSFilename&)` | 0x0051B230 | 376 | 1 |
| `UITextureMgr::LoadingTexturePak(int, const char*)` | 0x0051B660 | 1224 | 5 |
| `UITexture::LoadRSBFile(istream&)` | 0x0051C810 | 4344 | 4 |

---

## 四、顺带查清的两件崩溃相关问题（如实记录，含一条**自我否证**）

### 4.1 ELF 补丁在 `RSFontMgr` 里的分布（原版 `GR_EN_ORIG` vs 汉化 `GR_ZH113b` 逐字对照）
`0x219380..0x21A600`（1184 字）中 **20 字不同**，全部落在 **DrawString/解码路径**：

```
0x219BCC  jal 0x0040BFC8        →  jal 0x00416ED0      ; 字符解码换成汉化 cave
0x219BD0  addiu $a0,$sp,0xDF    →  addiu $a0,$sp,0xDE  ; 缓冲基址前移 1 字节
0x219BD4  lb    $a1,0xDF($sp)   →  lhu   $a1,0xDE($sp) ; 单字节读 → 双字节读
0x219C08  addiu $v1,$zero,-75   →  addiu $v1,$zero,181 ; 0xFFFFFFB5 → 0x000000B5（同一个 16 位值 0xB5）
0x219C14  addiu $v1,$zero,-79   →  addiu $v1,$zero,177 ; 0xFFFFFFB1 → 0x000000B1
```
⇒ **这组改动是自洽的**：既然读改为**无符号半字**，比较常量也必须从"负值"改成"同值的正值"。
⇒ **`RSFontMgr::ReallocateSize`(0x21A3B0) 与 `AddOneWord`(0x219F50) 一个字节都没动。**

### 4.2 ★ 一条被我自己否证的假设（留档以免重走）
曾怀疑"缓冲从 `sp+0xDF` 挪到 `sp+0xDE` 撞上了相邻栈槽"。
逐指令统计该函数内 `sp` 相对引用：

| 版本 | sp+222 | sp+223 | sp+224 |
|---|---|---|---|
| 原版 | **0 处** | 4 处 | 1 处（`addiu $sp` 收帧）|
| 汉化 | 4 处 | **0 处** | 1 处 |

⇒ **完美对称：只是整体前移 1 字节，`sp+222` 原本无人使用** ⇒ **该假设不成立**，已从候选里划掉。

---

## 五、对目标的可执行结论

| 步骤 | 内容 | 状态 |
|---|---|---|
| ① | **确认容量上限不是 ELF 常量** | ✅ 本报告（`nrec = fld[4]×fld[5]` + `__nwa` 动态分配）|
| ② | **确认贴图按名字查找、名字来自资源数据** | ✅ 本报告（`mgr+0x1c` + `diSearchFile`）|
| ③ | **查清 IOP 侧挂了哪些容器、搜索顺序**（决定大贴图能否放 GR.IMG 的 1.55 GB 空位）| ⏳ 下一步（逆向 `MODULES\RPC.IRX` / `IOPRP242.IMG`）|
| ④ | **找出整盘可用字节**（MENU.IMG 内部零尾料 / GR.IMG 内部空位 / 8bpp→4bpp 回收 / 盘尾 28,672 B）| ⏳ 并行任务 `64829930` |
| ⑤ | **PC 版结构对照**（`.rsb` 同源性、PC 如何无上限）| ⏳ 并行任务 `d69bc993` |
| ⑥ | 按 ①②③④⑤ 拼出"零缺字"盘 | 待 |

---

## 六、工具与产物（可复现）

```
work\tools\gh.bat                                   Ghidra headless 包装器（环境重定向已封好）
work\tools\ghidra_proj_ee\GRLocEE                   r5900:LE:32:default 工程（默认 MIPS 不认 MMI，必须用这个）
work\tools\ghidra_scripts\{FontHost,FontHost2,DiSearch,RootContainer}.java
work\tools\{font_host2,disearch,rootcontainer}.log  本次全部反编译原文
work\tools\elf_diff_fontmgr.py                      原版↔汉化 ELF 区段对照
work\tools\dis_pair.py                              两版本逐指令并排
work\tools\sp_slot_hunt.py                          sp 相对引用的偏移归组统计
```

## 七、已知限制

1. **IOP 侧的容器搜索顺序尚未确认** —— 这是"大贴图放哪"的最后一块；`RPC.IRX` / `IOPRP242.IMG` 未反编译。
2. `RSRootContainer::ReadResourceFile` 直至本轮结束时未取到其完整 C（脚本按体积取前 10 个函数，它未入选）。
3. 本报告的所有结论均来自**静态反编译 + 磁盘字节对照**；**尚未做任何实机验证**。
4. `diSearchFileEx` 的 `eeRpcSendCommand(0x80010010, …)` 里的模块号/功能号语义未展开。

---

## 八、【round 3 追加】容器表在主 ELF 里，且是数据 ⇒ 推荐"路 B"

### 8.1 主 ELF 里的容器表（实证）
在 `SLUS_206.13.elf` 内搜到：
```
@0x004858F1  ...ani.mpg.Ghost Recon.....**\MENU.IMG;1**.....host0:q:\ike\menu.img...**\GR.IMG;1**...
             ...host0:q:\ike\gr.img.....-mission...M01_CAVES.mis...-toe...m03.toe...
@0x00477FD1  ION_PS2...REPLAY..PS2_NEW_PROFILE.AFTER_ACTION....SINGLE_PLATOON..
             **\GR.IMG;1**.......host0:q:\ike\gr.img.....menu....load_new_1.rsb...
```
⇒ **挂载容器 = `MENU.IMG` + `GR.IMG`，清单是 ELF 内的数据（PS2 名 + PC 路径成对出现）** ⇒
  ① 可新增容器；② **同一份代码带 PC 路径 ⇒ PC/PS2 共用，是"结合 PC 版结构"的直接接口**。

### 8.2 IOP 侧是一个"IMG 虚拟文件系统"（RPC.IRX 符号实证）
```
open_img · read_img_sync · close_img · find_file · match_pattern · translate_pointers
diSetHashTable · diGetHashTable · diSearchHashTable · diLoadImage · diUnloadImage
diGetImageFileHandle · diGetFileFlag · diGetZippedSize / diSetZippedSize / diSetUnzippedSize
```
`IOPRP242.IMG` 内字符串：`CdSearchFile: searching %s...` / `CD_cachefile: %d files found` /
`CD_cachefile: dir not found` / `cdrom0:` / `open fail directory %s`

**整体链路**：
```
主 ELF 容器表(MENU.IMG;1 · GR.IMG;1)   ← 数据，可加容器
  → RS 引擎 open_img 打开 → diSetHashTable 把条目列表交给 IOP
  → diSearchFile(名字) → IOP 哈希查找 → 返回 [句柄/LBA/大小]
  → UITextureMgr::LoadIndexedRSB 读句柄 → 解析 RSB
```

### 8.3 ★ 推荐路线 B：把大字形贴图放进 `GR.IMG` 的条目
| 优势 | 说明 |
|---|---|
| 不动 ISO 结构 | 不新增容器、不改 LBA、不改盘尺寸 |
| 不碰容器表 | `GR.IMG` 已在表里 |
| 不改 ELF 逻辑 | 只改**字体资源里的贴图名字符串**（数据，§一已证）|
| 容量 ≈ GR.IMG 内部空位 | 容器 1.55 GB，极可能 GB 级余量 |
| 记录表自动扩容 | `nrec = fld[4]×fld[5]` + `__nwa` 动态分配（§一已证）|

⇒ **剩余为工程量**：① 量 GR.IMG 内部空位（并行任务 `64829930`）；② 把新图集作为条目写进 `GR.IMG`；
  ③ 改字体资源的贴图名；④ 记录表随 W×H 自动变大 ⇒ **零缺字**。

### 8.4 备选路线 A：新增一个容器（如 `FONT.IMG`）
把第 5 个条目加入主 ELF 的容器表并新建容器文件 —— **需动 ISO 结构**（新增文件 ⇒ 改 ISO9660 目录），
风险高于路 B，仅在路 B 的 GR.IMG 空位不足时才考虑。

### 8.5 工具
```
work\tools\iop_probe.py      取 IOP 模块 + 头识别 + 字符串分类（产物在 work/builds/GR_ZH98/temp/r80/）
work\tools\ghidra_scripts\FileRegistry.java   反编译 RS 文件注册表
work\tools\fileregistry.log                   本次反编译原文
```

---

## 九、【round 4 追加】ISO 空间总账（实测）与"零缺字"施工方案

### 9.1 IMG 容器实测（`work/tools/img_space.py`，盘 `GR_ZH113b`）
| 容器 | 条目数 | 最后一条结束 | 容器大小 | **尾料** | 条目内余量 |
|---|---|---|---|---|---|
| `GR.IMG` @19175 | **4070** | 1,550,497,792 | 1,550,563,328 | **65,536 B** | 0 |
| `MENU.IMG` @776286 | **686** | 58,239,646 | 58,300,882 | **61,236 B** | 0 |

⚠ **纠正一个乐观判断**：`GR.IMG` 是**压满**的（前 4000 条 stored 869 MB / real 977 MB，容器 1.55 GB 几乎用尽）
⇒ **"GR.IMG 有 GB 级空位"不成立** ✗；但**仍比先前估计多 65 KB**（先前漏算了 GR.IMG 尾料）。

### 9.2 ★ 关键发现：条目表末尾与名字区之间各有一块空隙
```
GR.IMG   表结束 0x030350 → 名字区起 0x034CB0  = **18,784 B**
MENU.IMG 表结束 0x0088D0 → 名字区起 0x00D230  = **18,784 B**
⇒ 各够放 391 条 48 字节条目 ⇒ **加新条目完全不必搬动数据** ✓✓
   （此前担心"加条目要整体平移所有 off"，此处实测不成立）
```

### 9.3 可用空间总账
```
GR.IMG 尾料                                  65,536 B
MENU.IMG 尾料                                61,236 B
ISO 尾（改 MENU.IMG 目录记录 data length）    28,672 B
────────────────────────────────────────────────────
合计                                       ≈ **155,444 B**
```

### 9.4 能买到多少字位
`y = 2 + 16×(r + 3×[r≥12])`，`h` 为图集高：
| h | 需要空间 | 行数 | 格数 | 对偶字位（扣图标/ASCII 带≈3 行）|
|---|---|---|---|---|
| 512（现役）| 0 | 28 | 1736 | 1504 |
| 640 | +66,016 B ✓ | ≈37 | 2294 | ≈2108 |
| **768** | **+131,648 B ✓**（在 155,444 内）| 44 | 2728 | **≈2542** ✓✓ |
| 832 | +197,632 B ✗ 超出 | — | — | — |

⇒ 需求 **1876** ⇒ **h=768 盈余约 660 格**。**h=768 即天花板附近。**

### 9.5 施工方案（**不动 ISO 结构、不改文件 LBA、不改盘尺寸**）
1. `GR.IMG` 与 `MENU.IMG` **各加一个新条目**（用表区那 18,784 B 空隙，数据不搬）；
2. 新图集（h=768）写入新条目，吃掉两容器尾料 126,772 B；
3. 改 `MENU.IMG` 目录记录 data length（ISO 偏移 `0x828D8` 小端 / `0x828DC` 大端）吃下 ISO 尾 28,672 B；
4. 改字体资源里的**贴图名字符串**指向新条目（数据改动，见 §一）；
5. 记录表 `nrec = fld[4]×fld[5]` 随 W×H 自动扩容（见 §一）；
6. ⇒ **0 缺字**。

### 9.6 工具
```
work\tools\img_space.py     IMG 容器条目/余量/尾料盘点（本报告 9.1 的数据来源）
work\tools\iso_gaps.py      ISO9660 PVD + 根目录 + 间隙 + MENU.IMG 目录记录定位
work\tools\downloaded       (无)
```

### 9.7 已知限制
- 图素高度换算的"图标/ASCII 带占用 3 行"是沿用现役布局的推算，**未实机验证 h=768**；
- 新增条目后**是否被引擎的哈希表接受**（`diSetHashTable` 传给 IOP 的条目列表会不会带上新条目）**未验证** —— 需探针；
- `GR.IMG`/`MENU.IMG` 条目表的**条目数字段位置**本轮未显式定位（靠"名字缺失即停"解析），加条目时需先定位它。

---

## 十、【round 5 追加】IMG 头结构与"加新条目"的精确配方（前置未知已清零）

### 10.1 头结构（GR.IMG 与 MENU.IMG 一致）
| 偏移 | 含义 | MENU.IMG | GR.IMG |
|---|---|---|---|
| +0x00 | 容器大小 | 58,300,882 | 1,550,563,328 |
| +0x04 | **名字区结束** | 65,350 (0xFF46) | 287,861 (0x46475) |
| +0x08 | 扇区 2048 | 2048 | 2048 |
| +0x0C | **条目表结束** | 35,024 (0x88D0) | 197,456 (0x30350) |
| +0x10 | **名字区起始** | 53,808 (0xD230) | 216,240 (0x34CB0) |

★ **条目数没有独立字段，是从表结束算出来的**：
`count = (u32[+0x0C] − 0x830) / 48` ⇒ MENU (35024−2096)/48 = **686** ✓ / GR (197456−2096)/48 = **4070** ✓ 完全吻合。

### 10.2 内部布局
```
MENU.IMG : 0x0000 头 | 0x0830 表(686×48=32,928B)→0x88D0 | **0x88D0..0xD230 空隙 18,784 B**
           0xD230 名字区(≈11.8 KB) | **0x10000 起 数据区**
GR.IMG   : 0x0000 头 | 0x0830 表(4070×48=195,360B)→0x30350 | **0x30350..0x34CB0 空隙 18,784 B**
           0x34CB0 名字区 | **0x46800 起 数据区**
```
⇒ **头+表+名字全部落在前 64 KB 内，数据区从 0x10000/0x46800 起，加条目动不到数据** ✓✓

### 10.3 加新条目的配方
1. **条目表尾追加 48 字节记录**，并把 `u32[+0x0C]` += 48（条目数自动 +1）；
2. **名字写进名字区**：把名字区**整体前移**到表尾之后（利用那 18,784 B 空隙），
   只更新 `u32[+0x0C]`（名字区起始）与 `u32[+0x04]`（名字区结束）；
3. **不碰数据区**（数据起点 0x10000 / 0x46800 不动）⇒ 所有既有条目的 `off` 无需改。
⇒ 新条目即可被读到（`diSetHashTable` 把条目列表交给 IOP 的哈希表）。

### 10.4 工具
```
work\tools\img_header.py    IMG 头字段定位（本报告 10.1 的数据来源）
work\tools\img_space.py     条目/余量/尾料盘点
```

### 10.5 仍未验证
- **新条目被引擎接受**（探针待做）；
- 新名字写进名字区后**名字区末尾与 0x10000 之间只剩 ~186 B**（MENU），
  本配方靠"名字区整体前移"提供余量 ⇒ **落地时需精确控制名字区长度 ≤ 18,784 B** ✓（686 个名字约 11.8 KB，够）

---

## 十一、【round 7 追加】方案第 4 步的精确编辑点：FONT.RES 里的贴图名字符串

### 11.1 实测
```
FONT.RES = MENU.IMG 条目 #4 ; 容器内 off=0xB9120 ; stored=4421 ; real=7222
前 96 字节:
  d1050000 36170000 2a140000 00 **6e65775f666f6e745f726576697365642e727362** 03 5d02 05 4c 00 03 6c61726765 …
  u32[0]=1489  u32[1]=5942  u32[2]=5162  NUL  ★ "new_font_revised.rsb" (22 字符 + NUL)  face 数 = 03 ✓
```
- **贴图名字符串 = FONT.RES 内偏移 `+0xD`**
- **ISO 绝对偏移 = `0x5ECE8120 + 0xD = 0x5ECE812D`**
- 其后 `03` = **face 数 3**（与既有认知"3 个 face"吻合 ⇒ 解析正确性交叉验证 ✓）

### 11.2 编辑方式
| 新名字长度 | 处置 |
|---|---|
| ≤ 22 字符 | **等长覆盖**（不足处以 NUL 补齐到 23 字节）⇒ 零结构改动 ✓ |
| > 22 字符 | 需同步改前面的长度字段/后续偏移 ⇒ 避免 |

### 11.3 方案六步的精确落点总表
| 步 | 精确落点 | 依据 |
|---|---|---|
| 1 | 加新条目：`MENU.IMG`/`GR.IMG` **表尾 + `u32[+0x0C]`**（表后各有 18,784 B 空隙）| round 5/6 实测 |
| 2 | 新图集写进容器**尾料**（GR 65,536 + MENU 61,236 = 126,772 B）| round 4 实测 |
| 3 | 吃 ISO 尾：`MENU.IMG` 目录记录 data length `0x828D8`(LE)/`0x828DC`(BE)| 前轮定位 |
| 4 | **改贴图名：`FONT.RES +0xD`（ISO `0x5ECE812D`）** | **round 7（本轮）** |
| 5 | 记录表 `nrec = fld[4]×fld[5]` 随 W×H 自动扩容 | 反编译 `ReadResourceFile` |
| 6 | ⇒ 0 缺字 | — |

### 11.4 工具
```
work\tools\font_res_name.py  定位 FONT.RES 与其中的贴图名字符串（本报告 11.1 数据来源）
```

### 11.5 仍未验证
- **实机门**（新条目被引擎接受）：本轮两次尝试均因**另一实例占用**（`pcsx2-gsrunner` pid 43780）
  而无产出（dump 仅 0 字节 console.txt，疑为单实例锁）⇒ **判据未取得**，
  绝不以 `exit=0` 冒充通过；
- 新条目名 > 22 字符的路径未设计；
- `u32[1]=5942 / u32[2]=5162` 语义未展开（不影响本方案）。

---

## 十二、【round 14 追加】★ 实机门**已通过** —— 加新条目被引擎接受（附我自己工具的一个真 bug 与修正）

### 12.1 对照实验（裸跑 gsrunner，2,600 帧，同一输入表，模拟器空闲）
| 盘 | `TLB Miss` 行数 | 针 `'newfontrevisedrs'`（字库贴图名）| `'WPNRPK74'` |
|---|---|---|---|
| `GR_ZH113b`（未改动）| **0** ✓ | **1173 hits** ✓ | 1230 hits |
| 旧补丁（**移动名字区**）| **4** ✗ | **0 hits** ✗ | — |
| **新补丁（追加名字）** | **0** ✓ | **1173 hits** ✓ | 1230 hits |

⇒ **引擎接受新增条目**：引导干净、TLB 0、字体照常加载 ✓✓
（针命中数与未改动基线**完全一致** ⇒ 无副作用）

### 12.2 ★ 修正了一个真 bug（旧配方会毁掉字体加载）
```
✗ 旧做法「把名字区整体前移到表尾之后」——
   IMG 的 48 字节条目记录里存的是**指向名字区的偏移/索引**；
   移动名字区而不同步索引 ⇒ 全部指向被清零的旧位置
   ⇒ 实测后果：字库贴图名 needle 由 1173 掉到 **0**，并出现 4 次 TLB Miss
✓ 正确做法：**不动名字区本体**，把新名字**追加在名字区末尾之后**
   （MENU.IMG: 名字区声明末尾 0xFF46 → 数据区起点 0x10000，另有约 186 B 空隙）
   ⇒ 只更新「名字区结束」`u32[+0x04]`；
      **不动 `u32[+0x10]`（名字区起始）**；**不动任何条目记录** ✓✓
```
`work/tools/img_add_entry.py` 已按此修正，测试盘已重建并实机通过。

### 12.3 判据与复现命令（可复用）
```powershell
$gs='third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe'
& $gs -grdumpdir <dump> -grmaxframes 2600 -grsnap 30 -grinput <输入表> -logfile <dump>\emulog.txt -- <ISO>
判据① TLB Miss = 0 行
判据② emulog 里 `GR: needle 'newfontrevisedrs'` 命中数 ≈ 1173（与基线一致）
```
⚠ 注意：`tools/iso_build/fix_zh118_run.py` 因带 `-grscanframes 1000000`（全程 RAM 扫描）在本案下产出空 dump，
**裸跑 gsrunner 才有效** ✓（已在 r76 记录过 exit=0 假信号的问题）

### 12.4 对方案的影响
- **方案第 1 步（加新条目）实机验证通过** ✓✓ ⇒ 后续第 2/4/5 步可放心执行；
- 第 2 步（把 h=768 图集写进新条目）与第 4 步（改 FONT.RES 贴图名）待构建任务 `e2a0b778` 落地；
- 仍需注意审计报告 F6（对偶分支判据恒假 ⇒ 抬 nrec 前必须修）。

---

## 十三、【round 18 追加】PC 版结构剖析的结论（任务 d69bc993）与对方案的影响

见 `docs/REPORT_pc_structure.md`（464 行）。要点：

### 13.1 ★ 订正：`Chinese.dat` 我读错过
`@0x0000 CAA4 C0FB A3A1` = **「胜利！」**（不是我先前说的「失败！」）；
`恢复/出错/名字/人物` 均不在表内。我那次是撞上 **cp936 控制台二次乱码**。
真相：`Chinese.dat` = **1101×2B GBK 字符集表**（零重复 ⇒ 不是句表），且 `⊂ gbtext.def`（严格子集）。

### 13.2 PC 的两套字库
- **(甲) ike 原生 `RSFontMgr`**：`Data/Shell/font.res`(4796B) + `Art/new_font_revised.rsb`(262253B)
  —— **与 PS2 同名、同源、同构**（`font.res` 里同样是"文件名级静态常量"）。
- **(乙) 中文 DBCS 本地化字库（PC 独有）**：`gbtext.def` = **1288×2B [lead,trail] GBK 码表**（记录序 = 槽位）
  + `GB{12,16,24}{00..04}.TGA`（512×512×4 32bpp 页纹理）。

### 13.3 ★★ 关键洞察：PC 的绕法是「寻址从**存下来**改成**算出来**」
```
PC 容量上限全是代码常量（页宽 512 / perRow=512/S / perPage=perRow² / page=slot/perPage /
每字号 ≤5 页 / 字号 1..39 / 槽位=u16）⇒ 12px 档 5×1764 = 8820 槽 ≥ GB2312 全体 7445
PS2 用「逐字形 u0/v0/u1/v1/advance 记录表」⇒ 撞 FONT.RES 展开态 7222 B 上限
PC 用「均匀网格 + 现算地址」⇒ 唯一的表是 2B/字的码表 ⇒ **无表可撞**
⇒ **PC 不是"容器更大"，是"寻址方式不同"** ✓✓
```

### 13.4 ⇒ 对方案的影响（采纳与修正）
| 档 | 内容 | 裁定 |
|---|---|---|
| **P0** ★ | 把 cave 网格常量 `NCOL/CW/CH/Y0/SKIP_ROW/SKIP_ROWS` 从**立即数**改成**数据表 `lw`** | **采纳，优先做**（以后改容量不用改代码；先例 V10→V11 只改 2B）|
| **P1** | 图集 1024×512 → **1024×1024**（`px_size 0x40010→0x80010`，**+262,144 B**）+ `NCOL 62→124` ⇒ 4bpp 下 **2048 格** | ⚠ **空间不够**：预算 ≈**220,980 B** ⇒ **差约 41 KB** ✗ |
| **P1'** ★ | 改为 **h=768**（**+131,648 B** ✓ 在预算内）⇒ 44 行 × 62 ≈ **2728 格** > 需求 **1876** | **采纳（推荐）** ✓✓ |
| **P2** | 照抄 PC"多页" | **不采纳**（RSFontMgr 只有一个字形 UIModel ⇒ 动三处而收益同 P1）|

### 13.5 可直接复用的同源性收获
- **`.rsb` 是 PC/PS2 同一容器格式**：`{mode}{w}{h}{p0..p3}` + `Σp≤8` 时 CLUT=`2^Σp×4` + 表面 `w*h*Σp/8` + 定长尾块（mode 4/5/6/9 = 53/61/65/66 B，末 4B 恒 `FF FF FF FF`）。
  决定性反证：`GB1600.tga` 转 R5G6B5 后整幅在 `gb1600.rsb` 内匹配于 **0x2B** ✓；套到 PS2 `LOAD_NEW_1.RSB` = 28+1024+230400 = 231452 ✓。
  **⇒ 改写 .rsb 时尾块必须原样保留** ⚠。
- **`.qob`/`.pob` PC 与 PS2 逐字节完全相同** ✓（GRASS_1.QOB 635B ≡ 635B）。
- **`.mis/.atr/.kit/.gun/.gtf` 是同一份 XML**，PC 明文 / PS2 压缩（M01_CAVES.MIS 共同前缀 201 B ✓）。
- **`igor.exe`** = RSE 官方 RSB 编辑器（内含字体生成代码）⇒ 可用于生成/校验 `.rsb` 图集。

### 13.6 空间总账（最终）
```
MENU.IMG 尾料 61,236 + pda×2 转 4bpp 回收 65,536 + GR.IMG 尾料 65,536 + ISO 尾 28,672
⇒ **≈ 220,980 B**      需求: h=768 = 131,648 B ✓（余 ~89 KB）
```
⇒ **采用 h=768，不采用 1024×1024（+262,144 B 超出预算）** ✓

---

## 十四、【round 20 追加】★ 空位盘点的**两个否证**与更优方案（任务 64829930）

见 `docs/REPORT_iso_space_ledger.md`（42,414 B）。**本节推翻本报告 §九/§十二 的两条判断：**

### 14.1 ✗ 否证：「pda 两张 8bpp 贴图转 4bpp 无损回收 65,536 B」
实测用色：`pda-lcd-02` = **133 索引 / 43 种颜色**；`pda_counterparts` = **232 索引 / 206 种颜色**
⇒ 转 PSMT4（16 色）**有损**，会改 PDA 画面 ⇒ **无损回收 = 0 B**。（§十二的 65 KB 应作废。）

### 14.2 ✗ 否证：「格距 16→15 零重渲」
1,595 个带墨格中 **墨高 16 者 1,388 格**、墨宽 16 者 13 格，最大 bbox = **16×16（填满整格）**
⇒ 缩格距必切墨 ⇒ 必须重渲字形（并改文本度量）。

### 14.3 ✅ 更优方案：**H=592，仅 +40,960 B**
```
H=592 且其余网格常量一字不改 ⇒ 31 可用行 × 62 列 = **1922 格 ≥ 需求 1876** ✓✓
（若 SKIP_ROWS 3→2，H=576 也可达 1922，只需 +32,768 B —— 但要动一个网格常量）
空间来源:
  ① 用 ISO 目录记录把 MENU.IMG 声明长度吃到盘尾（+30,254 B，ISO 尺寸不变）；
  ② 把挡在 COMMON.PAK 身后的 2 条搬进 MENU.IMG 尾部（FONT.RES 4,421 + EN_MESSAGE_MC_4.RSB 69,404
     = 73,825 B；现尾 61,236 < 69,404 ⇒ 必须先做①）；
  ③ GR.IMG 侧搬走 1 条（D01_BEACH.PAK 108,571 B）。
```

### 14.4 可用空间分级（其实远超先前估计）
| 等级 | MENU.IMG | GR.IMG | 说明 |
|---|---|---|---|
| L1 全零未声明 | 70,691 | 187,657 | 最稳 |
| L2 孤儿非零（无条目覆盖）| 105,256 | 6,755,988 | 文件层按名读不到 |
| 合计 | 175,947 | **6,943,645** | 整盘 **7,119,592 B** |
⚠ 但**分散**（最大连续全零块仅 61,236 / 65,536 B）。
★ 另一个统一事实：两张 IMG 里 **`stored > real` 的条目数 = 0**（压缩条目一律 real > stored）⇒ "条目余量"为 0 字节。

---

## 十五、【round 31 追加】★★ 空位任务的**紧急更正**与两个实机探针（任务 64829930 终版）

### 15.1 ✗ 更正：**H=592 不够（差 8 格）⇒ 采用 H=608**
```
★ row 27（y=482..498）的**前 28 格不是空的** ——
   FONT.RES 里 `large`/`default` 两个 face 各有 **28 条** (u0,v0,u1,v1)=(0,482,16,498)…(432,482,448,498)
   采样窗 x∈[4,452) ⇒ 正好 28 格；实测该带墨 1,940 texel、x 范围 [4,446] ⇒ 逐格吻合
⇒ 被占的是 **3 行**（row 25/26 EN 带 + row 27 键盘带）⇒ 现役空闲只有 **46 格**（不是 108）
   交叉验证：`build_info.json` 的 font_compact 报 `usable_cells=1504`
★ 我先前"H=512 ⇒ 1612 吻合"是**用错基准**（1612 是原始格数，可用格 = 1504+46）⇒ 收回 ✓
```
| H | 空闲格 | ≥364？ | Δpx |
|---|---|---|---|
| 592 | 356 | ✗ 差 8 | +41,440 |
| **608** | **418** | ✅ 余 54 | **+49,632** |

### 15.2 ★★ 我漏掉的必需步骤：**ELF 4 处 gate `0xB1 → 0xB5`**
```
`sltiu t, lead, 0xB1` ⇒ lead ≤ 0xB0 ⇒ 16 lead ⇒ 最大 slot = 15×94+93 = **1503**（共 1504 槽）
⇒ **slot ≥ 1504 的使用必须先放宽 gate** ⚠ 4 处: 0x416EE8 / 0x417160 / 0x41751C / 0x5656A4
改成 **0xB5** ⇒ 20 lead ⇒ 最大 slot = 19×94+93 = **1879**（1880 槽）≥ 1504+364=1868 ✓ 余 12
```

### 15.3 ★★★ 两个探针盘实机 PASS
| 探针 | 改动 | 结果 |
|---|---|---|
| A | 只改 ISO 目录记录（+30,254，**全盘 6 字节差异**）| **到达「开发访谈 1」**，exit=0，346 s ✓ |
| B | A + 搬 2 条 + `COMMON.PAK stored +41,440` | **同样到达**，344 s；钩子序列逐字节相同；6 张 UI 截图**逐像素差异 = 0** ✓✓ |
⇒ **实机确立**: ① 游戏认 ISO9660 目录记录 data length ✓；② IMG 条目可搬迁 + `stored` 可变长 ✓
⇒ 唯一剩的未知: **字库记录本身**（`px_size` 变大 / h>512 的 512 KB 显存块）⇒ **探针 C**

### 15.4 空间与其它更正
- MENU.IMG 可用 **175,947 B**（全零 70,691 + 孤儿非零 105,256）；GR.IMG **6,835,244 B**（连续全零 ≥1KB 仅 187,657）；
  ISO 尾 **30,254 B**；`stored>real` 余量 **= 0**；全零死条目 **= 0**。
- **GR.IMG 侧唯一挡路的是 `D01_BEACH.PAK`（108,571 B）**；表项无 BE 镜像、无重名；
  "66 条删除项"是 `stored=0/real=0` 的别名（29 组共享 off）⇒ 占 0 字节。
- ⚠ **MENU 侧与 GR 侧 `COMMON.PAK` 内容差 116,527 B / 48,066 段（全在字库像素容器内）**
  ⇒ **GR 侧字库是另一个世代 ⇒ 若两处都要改，必须单独同步。**

---

## 十六、【round 33 追加】唯一缺字「嘚」(U+561A) 的解法（真正零缺字的最后一块）

### 16.1 事实（实测）
| 项 | 结果 |
|---|---|
| `third_party/fonts` 下的字体 | **只有 1 个**：`方正像素16.ttf` ⇒ 有「得/的/地」✓ **缺「嘚」** ✗ |
| **PC 官方简中版** | **也没有这个字** ✗（`ghost_recon_pc\Data\Shell\Art\gbtext.def` 1288×2B GBK 码表里查不到 U+561A）|
| 系统字体 | **全都有** ✓：`simhei.ttf`(黑体) · `msyh.ttc`(雅黑) · `simsun.ttc`(宋体) · `Deng.ttf`(等线) |

### 16.2 ★ 解法：用 `simhei.ttf` 按**现役同一配方**渲这一个字 ⇒ 不必改译文
```
配方（与 tools/font_pipeline/gen_font16.py 的 render16 完全一致）:
  ImageFont.truetype(ttf,16) ⇒ 原点画在 (8,8) ⇒ 取 canvas[8:24, 8:24] ⇒ 阈值 <128 为墨
风格比对（选 simhei 的依据，实测墨量）:
  方正像素16「得」= 183/256 · 「的」= 190/256
  **simhei.ttf「嘚」= 173/256** ✓ 同一密度档、结构一致 ⇒ 采用
  （msyh.ttc 墨 169/256 但预览发糊且出现整行墨 ⇒ 不采用）
```
⇒ **把它当作第 364 个字形填入 row 28..33 即可 ⇒ 零缺字且零文本改动** ✓✓

### 16.3 同时记录的两个待确认点
- `probe.txt` 报 `ok=363 / ok_edges=358` ⇒ 有 **5 个字**被判"边界可疑"：需确认是**触边可接受**（现役字里本就有墨宽/墨高=16 的填满格，见 §14.2 实测）还是需单独处理；
- `probe.txt` 已解出 **`FONT.RES` 记录表（styles）起点 = `0x1620`**，`large`/`default` 各 `nrec=224`、(v0,v1) 恰 6 组
  （含 `(452,468)×92` 与 **`(482,498)×28`**）—— 与 §15.1「row 27 键盘带占 28 格」**互相印证** ✓

### 16.4 工具
```
work\tools\glyph_avail.py      查某字在哪些字体里可用（本报告 16.1 数据来源）
work\tools\pc_glyph_grab.py    从 PC 版 gbtext.def + GB16*.TGA 取字（本报告 16.1 的 PC 侧证据）
work\tools\render_de_glyph.py  按现役配方渲染并打印 ASCII 预览（本报告 16.2 的选型依据）
```

---

## 十七、【round 43 追加】★★★ P1′ 实机通过 —— **引擎接受 1024×640 图集**（最大未知已消除）

### 17.1 探针设计（真·单变量，全盘仅差 1 字节）
```
只把 COMMON.PAK 里 `new_font_revised` 记录的 `h` 字段 512 → 640：
  记录 @pak+0x1031 ; h 在记录 +0x020 ; PAK @MENU.IMG off 0x57400 ; MENU.IMG @LBA 776286
  ⇒ ISO 绝对偏移 = 776286×2048 + 0x57400 + 0x1031 + 0x020 = **0x5EC87451**
  （LE: 512 = 00 02 00 00 → 640 = 80 02 00 00 ⇒ 只有最低字节变化 ⇒ 差异 = 1 字节）
未改: px_size(仍 0x40010) · 容器分段(仍 8 段) · FONT.RES · ELF · 文本 · 字形 · ISO 目录 · 任何条目 off
工具: `work\tools\p1p_patch_h.py`（含逐字节差异核对）
盘  : `work\builds\GR_TEST_P1P_H640\GR_TEST_P1P_H640.iso`
```
### 17.2 实机结果（裸跑 2,600 帧；基线 = `GR_ZH113b` 同命令同输入）
| 指标 | 基线 | P1′ | 判定 |
|---|---|---|---|
| `TLB Miss` | 0 | **0** | ✓ |
| needle `'newfontrevisedrs'` | 1173 hits | **1173 hits** | ✓ 一致 |
| needle `'WPNRPK74'` | 1230 hits | 1230 hits | ✓ 一致 |
| 截图（78 张）| — | **逐字节相同 78 / 不同 0** | ✓✓ |

⇒ **引擎接受 1024×640，且画面零变化** ✓✓

### 17.3 证据边界（不过度外推）
- ✓ 已证：纹理**绑定/格式/尺寸**路径接受 1024×640，且不破坏任何现有渲染；
- ✗ **未证**：**y > 511 新行的 UV 采样是否正确** —— 本次跑到的是开机/Logo 屏（`PressSTARTbutton` = 0 hits），
  屏幕上没有菜单文字 ⇒ 这是"不破坏"的证据，不是"新行可用"的证据；
- ⇒ **P2/P3（新字形上屏同屏对照）仍然必要。**

---

## 十八、【round 45-46 追加】IMG 条目记录的字段语义（**4,756 条全量核对通过**）

工具 `work\tools\verify_entry_fields.py`（可重跑）。MENU.IMG 686 条 + GR.IMG 4,070 条，两者一致：

| 字段 | 语义 | 证据 |
|---|---|---|
| **u32[0]** | **名字偏移（相对名字区起始）** | **686/686 · 4070/4070** 落在名字区内；**0 重复**；**单调递增**；逐条精确命中字符串 ✓ |
| u32[1] | 编号/索引类（范围恰为 `0..条目数`）| MENU max=686 · GR max=4070 ✓ |
| u32[2..5] | 多为 0（#4 FONT.RES 的 u32[4]=1 为标志）| — |
| **u32[6]** | **stored** | COMMON.PAK=400659 ✓ / FONT.RES=4421 ✓ |
| **u32[7]** | **real** | FONT.RES=**7222** ✓（与实测一致）|
| **u32[8]** | **off** | COMMON.PAK=0x57400 ✓ / FONT.RES=0xB9120 ✓ |
| u32[9]/u32[10] | 未定 | 与本方案无关 |
| u32[11] | 0 | — |

★ **这字段级解释了我 round 14 的实机发现**：「移动名字区 ⇒ 字库名 needle 1173→0、TLB 4」
   正是因为 **`u32[0]` 存的是相对名字区起始的偏移** ⇒ 移动名字区而不同步 `u32[0]` ⇒ 全部指向被清零的旧位置 ✓✓
   ⇒ 本方案「**不动名字区、新名字追加在末尾**」是唯一安全做法，再次得到印证 ✓

★ 布局常量（供构建）：条目表 @0x830 / 48 B 每条 / 表后空隙 **18,784 B** /
   `data_start`：MENU **0x10000** · GR **0x46800** / 名字区：MENU [0xD230,0xFF46) · GR [0x34CB0,0x46475)

---

## 十九、【round 48 追加】★ 高危：FONT.RES 不能用裸 LZO round-trip 写回

工具 `work\tools\verify_lzo_roundtrip.py`（可重跑）。实测：
```
FONT.RES (MENU #4): stored=4421 / real=7222 / off=0xB9120
  file 头 12 B = `d1 05 00 00 | 36 17 00 00 | 2a 14 00 00` ⇒ 1489 / 5942 / 5162
  0x0C 起 = 00 "new_font_revised.rsb" 00 + 二进制（记录表）

  tcslib.lzo_subs(raw) ⇒ **1 个子流**(comp=1489, real=5942)，解出 5942 B
  tcslib.lzo_pack([(chunk,5942)]) ⇒ **1497 B**（原始 4421 B）⇒ **Δ = −2924** ✗
  回读校验**通过**（内容等价）⇒ 丢的是"文件里的非 LZO 内容" ⇒ **静默毁盘** ⚠
```
⇒ **FONT.RES = [12 B 头] + [名字串] + [LZO 子流] + [其它数据]**，不是纯 LZO 文件；
  ⇒ 写回必须用**认识其结构的读写器**（`patch_zh113_expand_font.py` / `patch_zh93_font_ext.py` 等同族 ✓），
    并加"写回后重读 + 展开长度必须 5942 + 前 12 B 与名字串逐字节相同"的自检 ✓

★ 附带核实：**条目记录的 `real`(7222) ≠ 解压长度(5942)**（差 1,280）⇒ `real` 另有语义，
  建议改 `stored`/`off` 时**保持 `real` 原值**并说明 ✓

---

## 二十、【round 49 追加】★★★★★ 重大简化：**本方案不需要动 FONT.RES**

### 20.1 发现的硬事实（既有工具链证据）
```
tools/iso_build/patch_zh113_expand_font.py:
  L204 ft_slot = iso.read(ft_e['iso_off'], ft_e['stored'])     ← 只**读** FONT.RES
  L205 ft_blob_src = b''.join(s[0] for s in tcslib.lzo_subs(ft_slot))
  L207 pak = bytearray(...)                                     ← 真正的写入目标是 PAK
  L347 ---------- 5) 写回容器 (逐像素, 只走 set_px, 不碰包头) ----------
  L389 回读核验: PAK 里除像素容器以外逐字节不变; **FONT.RES 整块不变** ✓
⇒ **本项目历轮扩容从未写过 FONT.RES** —— 都是"往已有空闲格画字"，矩形早在记录里。
⇒ 而"搬两条活带"要求改记录 ⇒ 本项目**从未走过的路** ✗（叠加 §十九 的裸 LZO 静默毁盘风险）
```

### 20.2 ⇒ 重算：不需搬那两条活带
```
h=640 ⇒ 36 行（row 0..35）
可用新格 = row 24 尾 46 + row 28..35（8 行 × 62）496 = **542**
需求 368 ⇒ **余 174** ⇒ **row 25/26/27 原地不动** ⇒ **FONT.RES 零改动** ✓✓
```

### 20.3 ⇒ 新字形不需要新记录（关键推理）
```
cave 对偶解码: slot=(lead−0xA1)×94+(trail−0xA1) ; row=slot/62 ; col=slot%62 ; y=16×row+2
记录表分支判据 `sltu slot+0xE0, nrec` 按 F6 审计**恒假** ⇒ **记录分支从不执行** ✓
⇒ 对偶码一律走**硬编码网格公式**、宽 16px ⇒ **新 slot(1504..1867) 落进 row 24..30，无需记录** ✓
⇒ 现役 1504 字走的正是这条同一路径 ⇒ 已被实机验证 ✓✓
⇒ 但 slot ≥ 1504 **必须抬 gate 才能寻址** ⇒ **ELF 4 处 gate 是本方案唯一的代码改动** ✓
（此推理已请执行任务独立复核；若存疑则回退到"搬两条活带 + 严格写回自检"的旧路 ✓）
```

### 20.4 收敛后的实施清单（只动两处，不碰第三处）
```
① ELF 4 处 `sltiu …,0xB1` → `0xB5`（0x416EE8/0x417160/0x41751C/0x5656A4）—— 唯一代码改动
   （成本：净可得 1876、余 8；备选 0xC0 ⇒ 余 1000+，见 §十七/§十九 相关说明）
② PAK 长大 +66,016（图集 512→640 行，px_size 0x40010→0x501F0，10 段自闭合包）
   + 搬走挡路 2 条（FONT.RES 4,421 + EN_MESSAGE_MC_4.RSB 69,404）到容器尾
   + ISO 目录记录延长 30,254（0x828D8 LE / 0x828DC BE）⇒ **ISO 尺寸不变**
③ ★ **FONT.RES 逐字节不变** ⇒ 列为**硬断言第 ⑦ 条** ✓✓
```

---

## 二十一、【round 52 追加】⚠⚠ **修正 §二十 的错误结论**：slot→row 映射是刚性的

### 21.1 我错在哪
```
cave 网格公式: **row = slot / NCOL（62）· col = slot % NCOL** ⇒ **slot 刚性映射到固定行** ✗
gate 抬到 0xB5 时新 slot 上限 1879 ⇒ 新字落行:
   slot 1504..1549 ⇒ row 24 ✓(46 格)   slot 1550..1611 ⇒ **row 25 ✗ EN 带**
   slot 1612..1673 ⇒ **row 26 ✗ EN 带**  slot 1674..1735 ⇒ **row 27 ✗ 键盘带**
   slot 1736..1879 ⇒ row 28..30 ✓(144 格)
⇒ **可用新格 = 46 + 144 = 190 < 364** ✗✗
⇒ §二十 说"rows 28..35 有 496 格"错在：那些行对应 slot 1736..2231，
   而 0xB5 的 gate **只到 slot 1879** ⇒ rows 31..35 **够不到** ✗
```
### 21.2 修正后的方案（仍**不动 FONT.RES** ✓）
```
① gate `0xB1 → 0xB7` ⇒ lead A1..B6 = 22 个 ⇒ 对偶空间 22×94 = **2068 slot**（上限 2067）
② **跳着分配 slot**: 允许区间 = **1504..1549** ∪ **1736..2053** = **364** ✓（跳过 slot 1550..1735）
   ⇒ row 25/26/27 两条活带**原地不动** ✓
③ 图集 **h=640** ✓（最大行 33，y ≤ 626 ✓；P1′ 已实机验证 h=640 被接受 ✓）
④ ★ **FONT.RES 逐字节不变** ✓（网格公式现算 UV；两条记录分支皆不可达 ✓ —— 该推理仍成立）
⑤ 成本: gate 0xB7 失去单字节码 **B1..B6**（△/键/练/用/B5/B6）⇒ 需迁入对偶空间占 6 slot
   ⇒ 需求 = 1504+364+6 = **1874** ≤ 2068（余 **194**）✓
   文本迁移量: 键 503 + 练 471 + 用 595 = **1569 处**（△ **0 次** ⇒ 免费）；B5/B6 待查
```
### 21.3 教训（写进方法论）
- **"有多少空格" ≠ "能放多少字"**：后者由 **slot→(row,col) 的刚性映射** 决定 ✗
  ⇒ 任何"容量"结论都必须先做 **slot 分配表**（每个字 ⇒ lead/trail ⇒ slot ⇒ row/col ⇒ 是否落在允许空行）✓
- 本条已列为执行任务的**强制核对项**（见 `LEAD_CORRECTION_slot_row_mapping.md` ✓）
