# tools\final_fix\ —— 幽灵行动 PS2 汉化 2400 线 · **卡死修复三件套 + 成品** 唯一归档

> ## ★★ 强制规则（2026-10-18 收尾确立 · 不可绕过）
>
> **今后一切构筑必须从英文原版 ISO 出发：**
>
> ```
> third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso
> sha256 2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531   (1,648,164,864 B)
> ```
>
> **禁止以上一版汉化 ISO 为基底。** 目的 = 可复现：基底必须是「外部只读原盘 + 只读 cdvd 转储」
> 的函数，而不是历史产物链上的某一环（那样一旦中间盘被清理，链条就断）。
>
> * 执行体：`rebuild_base.py`（原盘 ⊕ K2 转储 ⇒ 基底）+ `repro_from_eng.ps1`（端到端一条命令）
> * `work\builds\GR_REBUILD\GR_REBUILD2400.iso` 降级为**开发期快捷基底**（§4 路径 A）；
>   它本身也可由本规则重建（实测 4.4 秒，逐字节相同）。
> * 旧配方「必须从 `GR_REBUILD2400.iso` 起」**作废**（该表述已被本节取代）。
> * 实测证据：2026-10-18 从英文原盘跑完整条链 ⇒ 产出 sha256 `d8007873…1b2ab5` == 成品
>   （`docs\REPORT_FINALIZE.md` §B）。
>
> 本目录 = 整个 2400 产品线「修复 + 出盘 + 校验 + 基底重建」的**唯一一份脚本**（收尾归档时从
> `work\builds\GR_COMBFIX|GR_SPINFIX|GR_OOMFIX\tools\` 归并而来，实验分支已清理）。
> 成品盘：`work\builds\GR_RELEASE\GR_ZH126.iso`（2026-10-18 由 `GR_ZH2400_FINAL.iso` **改名**而来，
> 只动文件名与引用，ISO 内容一字节未改 —— 见 §4.3）
> 全量验收：`docs\REPORT_RELEASE_VERIFY.md` · 交付说明：`docs\RELEASE_NOTES_2400.md`

---

## 0. 一句话

游戏内卡死（任务完成处画面定死、只能强退）的根因是**分配器的桶链被写坏后原地自旋**。
本目录的三件套把「链头非法」从**无限自旋**改成**走既有出口**，并顺带堵住解压器对 NULL 的写。
成品盘 = 2400 产品线基底 + 这一组补丁，**只改 78 字节 / 25 处**，全部在声明窗口内，窗口外 0 字节。

| 名 | 站点 VA | 原字 → 新字 | cave | 一句话 |
|---|---|---|---|---|
| **F4** | `0x00102588` | `0x1459FFD1` → `0x081068D7` | `0x0041A35C`（36 B） | malloc 大块桶链扫描：链头不在 RAM 内就 bail |
| **OOMFIX** | `0x00539174` | `0xAE620004` → `0x08154012` | `0x00550048`（44 B） | 解压器 malloc 返回 NULL 时不再写 NULL+4，改走失败分支（`s0=0`） |
| **F7** | `0x001021D4` | `0x1447FFEA` → `0x08177B31` | `0x005DECC4`（36 B） | own-bin 回边：链头非法就 bail 到既有「换下一个桶」出口 |

成品身份（逐项可复核）：

```
尺寸    1,648,164,864 B
sha256  d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5
md5     d24c324eb955a8c8dbaf92f6c766da2c
ELF     SLUS_206.13 @ LBA 295 / 37,453,732 B / sha256 6fce4f45…38e73a
Game CRC (PCSX2)  CFDB8C97   ⇒ 即时存档名必须写 SLUS-20613 (CFDB8C97).01.p2s
```

---

## 1. 目录内容（只有这 6 个文件）

| 文件 | 作用 |
|---|---|
| `apply_fix.py` | **唯一**打补丁 / 校验器（施工 + 8 项自查 + 成品身份比对） |
| `fix_spec.json` | 补丁表与全部事实的**单一真源**：站点/原字/新字/cave 逐字、声明窗口、参照区、基底链、成品身份、验收结论索引、已知残余、已归档盘 sha256、**强制规则** |
| `rebuild_base.py` | **从英文原盘重建基底**（原盘 ⊕ K2 cdvd 转储 ⇒ `GR_REBUILD2400.iso`，含 7 组硬断言） |
| `repro_from_eng.ps1` | ★ **端到端一键复跑（权威配方）**：英文原盘 → 基底 → 三件套 → 成品，逐项核 sha256 |
| `repro.ps1` | 快捷复跑（路径 A：直接用现成基底出成品 / `-VerifyOnly` 校验成品盘） |
| `README.md` | 本文件 |

> 为什么放 `tools\` 而不是 `work\`：`.gitignore:61` 是 `work/**`（整个 work 不入库），
> `tools/**` 才受版本控制 ⇒ 只有放在 `tools\final_fix\` 的这份才能进 git、跟着分支走。

---

## 2. 怎么打补丁

```powershell
$py = 'C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

& $py tools\final_fix\apply_fix.py `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso `
      --out  D:\somewhere\GR_ZH126.iso
```

脚本会（**任一条不通过就拒绝写盘 / 非 0 退出**）：

1. **基底指纹**：sha256 必须是 `d7f83d7e…443ca0`（= `GR_REBUILD2400.iso`）、尺寸 1,648,164,864 B、ELF sha256 `5cb59175…`；
2. **施工前断言**：3 个站点原字逐一相符（`1459FFD1 / AE620004 / 1447FFEA`）、3 个 cave 必须是**全零区**；
3. 写站点跳转 + 写 cave 字（`fsync`）；
4. **写后回读**（全部重新读盘，不信任中间量）：站点/cave 逐字相符、ELF LBA 与尺寸未变、ELF 头 0x1000 B 未动、4 个闸门未动、7 个参照区「除声明字外逐字节相同」；
5. **差异窗口**：与基底比较必须恰好 **78 B / 25 run**，且**全部落在 6 个声明窗口内**（窗口外 0 B）；
6. **成品身份**：sha256 / md5 / ELF sha256 / CRC32(xor) 与交付成品逐项相等 ⇒ 打印「复现成功」。

> 实测（本机，2026-10-18）：从基底出盘 **9.1 秒**，`exit=0`，出盘 sha256 == 成品 sha256。

输出 `--meta`（默认 `<out>.meta.json`）里有：基底指纹、逐站点表、差异 run 全表、身份四件套。

## 3. 怎么验证一张已有的盘

```powershell
& $py tools\final_fix\apply_fix.py --verify-only `
      --iso  work\builds\GR_RELEASE\GR_ZH126.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso
```

* 不带 `--base`：只查身份 + 三件套在位 + 闸门（约 5 秒）；
* 带 `--base`：追加「参照区未被动 + 差异 78 B / 25 run 全在窗口内」。

> 实测（本机）：**5.5 秒，26 条断言全 OK，失败 0 条**，结论「该盘就是交付成品」。
> 本仓库里 `COMBFIX_2400.iso` 与 `GR_ZH126.iso` 逐字节相同，用同一条命令都可校验。

### 真正的「全量验收」不在这份脚本里

`apply_fix.py` 只管**字节级身份与补丁在位**。下面这些属于**验收层**，结论与原始证据索引在
`fix_spec.json · acceptance_index`（每条都指到具体文件）：

三闸门 / 2350 槽 / 保留槽 473 / 借槽 5 / ASCII 182 条 · dump_font 家族 · 载荷级裸旧码 0 · 逐字符 0 差异 ·
实机 6000 帧（191 截图 / TLB 0 / Trap 0）· 与基底**逐帧 191/191 相同** · 补丁存活回读（第 5970 帧 RAM）·
**同现场回归**（未修盘 70,266 Trap 直接死 vs 本盘跑完 Trap 0；另一现场未修纯读死循环 vs 本盘 F7 bail 命中 3 次）。

---

## 4. 一键复跑

### 路径 B ★（**权威配方 · 从英文原盘起 · 已实测逐字节成功**）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1
```

做的四件事（每步都硬断言，任一不符即非 0 退出）：

1. 核英文原盘 sha256（`2b42ea7c…8531`）+ 打印两块 cdvd 转储的路径与 sha256；
2. `rebuild_base.py`：**英文原盘 ⊕ K2 块转储 ⇒ 基底**，断言基底 sha256 == `d7f83d7e…443ca0`；
3. `apply_fix.py`：基底 ⇒ 三件套 ⇒ 成品，断言 sha256 == `d8007873…1b2ab5`；
4. 与交付成品 `work\builds\GR_RELEASE\GR_ZH126.iso` 逐字节比对（sha256 相同）。

> **实测（本机，2026-10-18）**：`rebuild_base.py` **4.4 秒**出基底、sha256 与声明值一致；
> `apply_fix.py` 出成品、sha256 与交付成品一致 ⇒ **整链从英文原盘逐字节复现成功**。
> 命令原文、断言清单与两份 stdout 见 `docs\REPORT_FINALIZE.md` §B。

#### 路径 B 的输入（全部只读；两个转储在**仓库外**的用户级缓存里，随时可能被清）

| 输入 | 现状 | sha256 | 字节 |
|---|---|---|---|
| `third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso` | ✅ 盘上（只读） | `2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531` | 1,648,164,864 |
| `%LOCALAPPDATA%\PCSX2\cdvd-dump\GR_FA2400_K2 (2026-10-17 15-08-20).dump` | ⚠ 盘上但在仓库外 | `11f371f294e4f8e353c21931a9c38d73c1309832a21e74cfb3e31d7095daadd9` | 74,286,520 |
| `%LOCALAPPDATA%\PCSX2\cdvd-dump\GR_ZH113b (2026-10-15 19-39-44).dump` | ⚠ 同上 | `57c9e9d147106c7c7dbc5e41b6a80ffa6ce7ea984ec21b33505fb765b40dbf74` | 77,748,244 |

> ★ K2 的**真 ELF** 不再需要任何中间文件：`rebuild_base.py` 从 K2 转储的
> **LBA 295 起 18,288 扇区**（ISO 604,160 .. 38,057,891）现取，截到 37,453,732 B，
> 断言 sha256 == `5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8`。
> 这正是 2026-10-18 断链的修复点 —— 旧配方读的 `work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf`
> **已被历史清理删除**，故 `work\builds\GR_REBUILD\tools\rb_build.py` 今天必在 [A1] 处
> `FileNotFoundError` 中止。该脚本**已退役**，不要再按它复现；它的数学已被
> `rebuild_base.py` 逐行承接下来（`fix_spec.json · single_source_of_truth` 有登记）。
>
> 换句话说：**断链已修**。上面三点是唯一的硬依赖；仓库内 `work\**` 一个文件都不需要。

### 路径 A（**开发期快捷基底**，最短链路；不是发布口径）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1
```

做的事：核对基底 sha256 → `apply_fix.py` 出盘到临时目录 → 把出盘 sha256 与交付成品比 → 报 PASS/FAIL。
**前提只剩一个**：`work\builds\GR_REBUILD\GR_REBUILD2400.iso`（= 路径 B 第 1 步的产物，本仓库保留着，
sha256 `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0`）。
它不是发布口径的起点（发布口径必须走路径 B），只是省掉 4.4 秒重建的开发便利。

### 4.3 成品改名（2026-10-18）

`GR_ZH2400_FINAL.iso` → **`GR_ZH126.iso`**（`GR_ZH2400_FINAL.meta.json` → `GR_ZH126.meta.json`）：
按版本号规则去掉 `_FINAL` 后缀、取下一个未用轮次号（依据见 `docs\REPORT_FINALIZE.md` §A）。
**只动文件名与引用，ISO 内容一字节未改** —— sha256 `d8007873…1b2ab5` / md5 `d24c324e…6da2c` /
尺寸 1,648,164,864 B / ELF CRC `CFDB8C97` 改名前后完全相同。
历史运行目录 `runs\smoke_GR_ZH2400_FINAL\` 等**保留原名**（那是当时实跑的原始记录，里面的
命令行/emulog 是史实，不做改写）。

### 4.4 已删对照盘 `LAY_fix1_bytecount.iso`（**订正旧记载**）

旧版本 §4 曾写"收尾归档时**特意保留** `GR_LAYOUT\LAY_fix1_bytecount.iso`（同现场回归的未修对照盘）"。
**该表述已过时且与事实矛盾**：那张盘**已按指示删除**（不在盘上，实测 `Test-Path` = False）。

* 它的身份仍可核对：sha256 `a69a9ca44049eaed4085239a2b8d10af58888f54f62a51e40c1ece22dd2d2808`
  （1,648,164,864 B；ELF sha256 `0a986bb3…87b9`，Game CRC `7A761FCA`）；
* **结论仍然在**：它的作用 = 「同现场回归」里那张未修对照盘 —— 未修盘 46 帧内 **70,266 次 Trap**
  直接死 / 另一现场纯读死循环，而本成品盘同现场跑完、Trap 0 / F7 bail 命中 3 次
  （`docs\REPORT_RELEASE_VERIFY.md` §F、`docs\REPORT_COMBFIX.md`、`docs\REPORT_OOMFIX.md`）；
* **原始日志/截图/存档仍在**：`work\builds\GR_RELEASE\runs\reg_p1_FINAL_S1\`、
  `runs\reg_p2_FINAL_S1b\`、`work\builds\GR_LAYOUT\`（`results_fix1_bytecount.txt` / `run_fix1_bytecount.txt` /
  `LAY_fix1_bytecount.meta.json`）、`work\builds\GR_SPINFIX\runs\smoke_LAY_fix1_bytecount\`。
* 该盘**不可由 EN 原盘逐字节重建**（它是 2400 基底 + 1 字节 `0x21AC40` 的实验组合，且基底线路特殊），
  所以"删了就删了"——留 sha256 是为了判定"手上这张是不是它"。

> `GR_REBUILD2400.iso` 则**仍然保留在盘上**（1.57 GB）：它现在是**可重建的**（路径 B，4.4 秒），
> 保留它只是省时间；真要清理也不影响复现链。

---

## 5. 补丁表（逐站点 + 逐 cave）

站点（`iso_off = VA - 0x6C780`；`elf_off = VA - 0x6C780 - 295×2048`）：

| 名 | VA | ISO off | ELF off | 原字 / 原指令 | 新字 / 新指令 | 延迟槽 |
|---|---|---|---|---|---|---|
| F4 | `0x00102588` | `0x00095E08` | `0x0002608` | `1459FFD1  bne $v0,$t9,-47` | `081068D7  j 0x0041A35C` | `0x10258C` 未改 |
| OOMFIX | `0x00539174` | `0x004CC9F4` | `0x04391F4` | `AE620004  sw $v0,4($s3)` | `08154012  j 0x00550048` | `0x539178` 未改 |
| F7 | `0x001021D4` | `0x00095A54` | `0x0002254` | `1447FFEA  bne $v0,$a3,-22` | `08177B31  j 0x005DECC4` | `0x1021D8` 未改 |

cave（全部写在原盘既有的**零区**里，逐字表见 `fix_spec.json`）：

| 名 | VA | 字节 | 逐字（9/11/9 字） |
|---|---|---|---|
| F4 | `0x0041A35C` | 36 | `0322082B 004D582B 002B0824 10200002 00000000 08040934 00000000 08040964 00000000` |
| OOMFIX | `0x00550048` | 44 | `10400005 00000000 AE620004 AE620008 0814E45F 00000000 AE600004 AE600008 0000802D 0814E4A8 00000000` |
| F7 | `0x005DECC4` | 36 | `00E2082B 0046182B 00230824 10200003 00000000 08040860 00000000 08040878 00000000` |

不变量（每次出盘都会断言）：4 个闸门 `0x416EE8 / 0x417160 / 0x41751C / 0x5656A4 = 0x…00BA`、
ELF 头 0x1000 B、DBCS cave 全区 `0x416E00..0x417800`、ZH cave block B `0x565600..0x565B00`、
SPINFIX CAVE_F1 区 `0x55B730..0x55B780`（本轮**未使用**）、解压器 `0x539110..0x539310`、
解压器调用者 `0x51BE10..0x51C000`、RSFont 区 `0x21AC00..0x21AE00`、分配器镜像 `0x101C00..0x102700`。

**已删除的实验分支**（不在本目录，也不该再复活）：
`F1`（`0x101DC0` / cave `0x55B730`）、`F1b`（`0x101D60` / cave `0x5DECC4`）、
`combfix_apply.py` 的 flavor `A` / `B`（`A` = F4+OOMFIX；`B` = +F1+F1b）。
原因：它们**拦不住**本轮的「野 free + 插链」，且 F1/F1b 会带来 660..810 段 6 帧像素差异
（`docs\REPORT_COMBFIX.md`）⇒ 成品盘不带它们。

---

## 6. 已知残余（7 条 · 完整原文见 `fix_spec.json · known_residuals`）

1. 分配器 **unsorted 桶回边（`0x102200` 一带）仍未校验**：F7 只护住 own-bin 回边；补第三个 36 B 零区在 ELF 里已扫不到。
2. F7 上界取 `0x1FFFFFFE`（512 MB）：坏值落在 `[32 MB, 512 MB)` 时会多跑一轮，代价是日志多 1~2 行 `TLB Miss`（**不会自旋、不会定死**）。
3. 「汉化是否抬高触发率」**未判定**：没做同场景「汉化 vs 英文」定量对照；本轮只把已发生的堆损坏由致命改成可恢复。
4. ES / FR 语言表抬闸门后仍带旧单字节码 (28+29)×2 处（主机语言 = ES/FR 会吞字）；DE/IT 结构异常（74+76 处）明确未动。中文/英文主机语言不渲染这些表。
5. 保留槽 `1872..2344`（473 个）按设计无字形、文本不引用 ⇒ 不会出现空白方块。
6. SF XML 里 5 处「配不出对的前导 `0xA4`」为上游既有缺陷，原样保留（`docs\REPORT_SENTINEL_FIX.md` §4/§8.1）。
7. 若干**参照盘已不在盘上**（`GR_ZH124.iso`、`GR_F364.iso`、`GR_FA2400_K2*.iso`、`GR_REBUILD2400_allpat.iso`、`GR_SPINFIX_F4.iso`），受影响的验收已用等价/更强方式替代。

另外，本次归档清理删掉了两张**已被取代的变体盘**（`COMBFIX_A.iso` / `COMBFIX_B.iso`）——
sha256 与理由记在 `fix_spec.json · archived_away_disks`，其 `meta.json` / `runs/` 证据仍在。

---

## 7. 用法边界（脚本自身的纪律）

* `apply_fix.py` **只读**输入盘，**只写** `--out` 与 `--meta`；绝不原地改输入盘。
* 拒绝覆盖已存在的 `--out`（要覆盖必须显式 `--force`）。
* 基底指纹不符、站点原字不符、cave 非零 ⇒ **拒绝施工**，一个字节都不写。
* 所有断言都不依赖上一次运行的中间产物：全部**重新读盘**计算。
