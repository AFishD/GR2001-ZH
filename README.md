# 《幽灵行动》(PS2, SLUS-206.13) 中文汉化 —— 2,400 字成品 + 卡死修复 · 公开快照

**快照日期 2026-10-18** · 分支 `snapshot-2026-10-18`（= 本仓库 `main`）

本仓库是《Tom Clancy's Ghost Recon》(PS2 USA 版, SLUS-206.13, "ike" 引擎) 全量中文汉化工程
**收尾阶段的公开快照**：发布 **2,400 字中文成品盘**的**补丁 + 工具 + 验收归档文档**，
其中包含本轮定位并修好的**游戏内卡死缺陷**（任务完成处画面定死、只能强退）。

> **本快照不含任何原游戏数据**：没有 ISO、没有字库/图形/文本资源、没有模拟器二进制。
> 只有**补丁脚本（逐字节站点表）、复现脚本与文档**。使用者须**自备正版原盘**自行重建基底。
> 详见文末「版权、免责与授权」。

---

## 1. 成品身份（逐项可复核）

| 项 | 值 |
|---|---|
| 尺寸 | `1,648,164,864` 字节（1,571.81 MiB） |
| **sha256** | `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5` |
| **md5** | `d24c324eb955a8c8dbaf92f6c766da2c` |
| Game CRC (PCSX2) | **`CFDB8C97`** ⇒ 即时存档文件名必须是 `SLUS-20613 (CFDB8C97).01.p2s` |
| 主程序 | `SLUS_206.13` @ LBA 295 / 37,453,732 B / sha256 `6fce4f45…38e73a` |
| 相对基底差异 | **78 字节 / 25 处**，全部落在 6 个声明窗口内（窗口外 0 字节） |
| 基底（必需） | `GR_REBUILD2400.iso` sha256 `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0` |
| 英文原盘（链路起点） | sha256 `2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531` |

成品盘**本身不在本快照里**（1.57 GB 游戏数据 + 版权原因）。本快照给的是**造出它的那 78 字节**。

---

## 2. 修的是什么（F4 / OOMFIX / F7 三件套）

卡死根因：**PS2 版内存分配器的空闲桶链被写坏后原地无限自旋**（链头落在 RAM 之外，
`bne` 回边永不退出）。三件套把「链头非法」从**无限自旋**改成**走既有出口**：

| 名 | 站点 VA | 原字 → 新字 | cave | 一句话 |
|---|---|---|---|---|
| **F4** | `0x00102588` | `0x1459FFD1` → `0x081068D7` | `0x0041A35C`（36 B） | malloc 大块桶链扫描：链头不在 RAM 内就 bail 到既有出口 |
| **OOMFIX** | `0x00539174` | `0xAE620004` → `0x08154012` | `0x00550048`（44 B） | 解压器 malloc 返回 NULL 时不再写 `NULL+4`，改走失败分支（`s0=0`） |
| **F7** | `0x001021D4` | `0x1447FFEA` → `0x08177B31` | `0x005DECC4`（36 B） | own-bin 回边（本轮新病灶）：链头非法就 bail，截断自旋 |

全部写在**原盘既有的全零区**里；ELF 头 0x1000 B、4 个闸门、9 个参照区均逐字节未动
（每次施工/校验都会重新读盘断言）。

**验收结论（详细过程见 `docs/`）**：三闸门 ✅ · dump_font 家族 ✅ · 载荷级裸旧码 0 ✅ ·
逐字符 0 差异 ✅ · 实机 6000 帧（191 截图 / TLB 0 / Trap 0）✅ · **与基底逐帧 191/191 相同** ✅ ·
**同现场回归：未修盘 70,266 次 Trap 直接死 vs 本盘 Trap 0** ✅ ·
**复现性：从基底出盘 sha256 与成品逐字节相同**（本机 9.1 s，exit 0）✅

---

## 3. 怎么用 `tools/final_fix/`

| 文件 | 作用 |
|---|---|
| `apply_fix.py` | **唯一**打补丁 / 校验器（施工 + 8 项自查 + 成品身份比对，26 条断言） |
| `fix_spec.json` | 单一真源：站点/原字/新字/cave 逐字、声明窗口、参照区、基底链、成品身份、验收结论索引、残余风险 |
| `repro.ps1` | 一键复跑（从基底出成品并核对 sha256），端到端 14.1 s |
| `README.md` | 三件套完整说明（含「路径 B 解封配方」与全部残余风险原文） |

### 3.1 出盘（从基底 ⇒ 成品）

```powershell
python tools\final_fix\apply_fix.py `
      --base <你的>\GR_REBUILD2400.iso `
      --out  <任意>\GR_ZH2400_FINAL.iso
```

脚本任一条断言不通过就**拒绝写盘并非 0 退出**；通过则打印「复现成功」并写出 `--meta`（默认 `<out>.meta.json`）。

### 3.2 校验一张已有的盘

```powershell
python tools\final_fix\apply_fix.py --verify-only `
      --iso  <你的>\GR_ZH2400_FINAL.iso `
      --base <你的>\GR_REBUILD2400.iso
```

（不带 `--base` 只查身份 + 三件套在位 + 闸门，约 5 秒；带 `--base` 追加「参照区未被动 +
差异 78 B / 25 run 全在窗口内」。）

### 3.3 一键复跑

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1
```

### 3.4 ⚠ **必须从 `GR_REBUILD2400.iso` 起** —— 上游中间盘已删，如实说明

从**英文原盘**一键重建基底的那条链（`rb_build.py`）**当前不可直接复跑**：它依赖
2026-10-17 那轮产生的中间件 `K2_SLUS_206.13.elf`（sha256 `5cb59175…`），
该文件已随历史清理删除，再跑会在 `[A1]` 断言处 `FileNotFoundError` 中止（已实测）。

* **解封配方**（一步）：从 K2 cdvd 块转储（LBA 295 起连续 18,288 扇区 = 37,453,732 B）取出该 ELF，
  sha256 必须等于 `5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8`；
  随后整链即可复跑。命令与期望 sha256 见 `tools/final_fix/README.md` §4。
* 因此**今天最短可靠起点就是 `GR_REBUILD2400.iso`**（sha256 见 §1）。使用者若手里只有英文原盘，
  需先按上述配方补齐中间件。

---

## 4. 残余风险（7 条 · 完整原文见 `docs/RELEASE_NOTES_2400.md` §4 与 `tools/final_fix/fix_spec.json`）

1. **分配器 unsorted 桶回边（`0x102200` 一带）仍未校验**：F7 只护住 own-bin 回边；
   补第三个 36 B 零区在 ELF 里已扫不到。
2. **F7 上界放宽到 512 MB**（`0x1FFFFFFE`）：坏值落在 `[32 MB, 512 MB)` 时会多扫一轮，
   日志多 1~2 行 `TLB Miss`（**不会自旋、不会定死**）。
3. **「汉化是否抬高触发率」未判定**：没做同场景「汉化 vs 英文」定量对照；
   本轮只把已发生的堆损坏**由致命改成可恢复**。
4. **ES / FR 语言表**抬闸门后仍带旧单字节码（(28+29)×2 处，主机语言 = ES/FR 会吞字）；
   **DE / IT** 结构异常（74+76 处）明确未动。中文/英文主机语言不渲染这些表。
5. **保留槽 `1872..2344`（473 个）按设计无字形**，文本不引用 ⇒ 不会出现空白方块。
6. **SF XML 里 5 处「配不出对的前导 `0xA4`」**为上游既有缺陷，原样保留。
7. **若干参照盘已不在盘上**（`GR_ZH124.iso`、`GR_F364.iso`、`GR_FA2400_K2*.iso`、
   `GR_REBUILD2400_allpat.iso`、`GR_SPINFIX_F4.iso` 等），受影响的验收已用等价/更强方式替代，
   sha256 记录在 `fix_spec.json`。

---

## 5. 本快照里有什么

```
README.md                 本文件（项目简介 / 成品身份 / 用法 / 残余 / 免责）
tools/final_fix/          补丁与复现三件套（apply_fix.py / fix_spec.json / repro.ps1 / README.md）
docs/                     验收归档文档（60 篇）
.gitignore .gitattributes 防止 ISO / 大二进制 / 第三方资产被带进版本库
```

`docs/` 的关键入口：

| 主题 | 文档 |
|---|---|
| **现状一页纸（先看这个）** | `docs/STATUS.md` |
| **交付说明 / 怎么用成品盘** | `docs/RELEASE_NOTES_2400.md` |
| **全量验收（最完整的一份）** | `docs/REPORT_RELEASE_VERIFY.md` |
| **根因链条** | `docs/REPORT_COMBFIX.md`（F7 新病灶）· `docs/REPORT_SPINFIX.md`（F4）· `docs/REPORT_OOMFIX.md` · `docs/REPORT_HEAP_EXHAUSTION.md` · `docs/REPORT_USERDUMP_ANALYSIS.md` |
| **反汇编根因 / 哨兵 / 内存漂移** | `docs/REPORT_DISASM_ROOTCAUSE.md` · `docs/REPORT_SENTINEL.md` · `docs/REPORT_SENTINEL_FIX.md` · `docs/REPORT_MEMDRIFT_ZH113b.md` · `docs/REPORT_NULLDEREF_ZH113b.md` |
| **汉化容量 / 字库 / 文本工程** | `docs/CAPACITY_2400.md` · `docs/CAPACITY_2400_FA2400.md` · `docs/FONTRES_STRUCTURE_r83.md` · `docs/REPORT_font_capacity_decompile.md` · `docs/TEXT_MIGRATION_0xBA.md` |
| **复现/测试指引** | `docs/REBUILD_PLAN.md` · `docs/REBUILD_REPORT.md` · `docs/CSFIX_TEST_GUIDE.md` · `docs/OOMFIX_TEST_GUIDE.md` · `docs/CVAR_TEST_GUIDE.md` · `docs/DISASM_TEST_GUIDE.md` · `docs/AB_TEST_GUIDE.md` |
| **模拟器取证环境（带钩子的 PCSX2）** | `docs/HOOKED_EMU_GUIDE.md` · `docs/HOOKEMU_QT2_GUIDE.md` · `docs/REPORT_HOOKEMU_QT2.md` · `docs/REPORT_HOOKED_EMU.md` |
| **归档与仓库状态** | `docs/REPORT_ARCHIVE.md` · `docs/REPORT_ARCHIVE2.md` |

> **上一轮（2026-10-11）的公开快照**（含早期完整工具链、字库/文本工程脚本与
> `docs/han_v2/` 逆向方法论手册等 267 个文件）保存在分支 **`snapshot-2026-10-11`**
> （commit `f0583003`）。本快照为**瘦身版**：只保留 2,400 字成品这条线的补丁与归档文档。

---

## 6. 版权、免责与授权

* "Tom Clancy's Ghost Recon" 及相关商标、游戏数据版权归 **Ubisoft** 所有。
  本项目为**爱好者学习/研究性质的非官方汉化**，与 Ubisoft **无任何隶属或授权关系**。
* 本快照**只包含**：①对可执行代码的**逐字节补丁表与施工脚本**（78 字节 / 25 处，
  并在原盘既有的全零区写入约 116 字节的跳转桩）；②复现/校验脚本；③过程与结论文档。
  **不包含**任何原游戏文件、ISO 镜像、字库/图形资源、文本 dump、模拟器二进制或 BIOS。
* 使用者须**自备合法持有的正版游戏原盘**；重建基底与成品盘请在**自己的本地环境**完成，
  **请勿分发**任何由原盘派生的镜像或数据。
* 补丁的作用是**移植既有的失败退出路径**（把「链头非法 ⇒ 原地自旋」改成「⇒ 走既有出口」），
  不含任何规避版权保护的技术措施。
* 文档与脚本以「现状」提供，**不提供任何担保**；请在改动前自行备份原盘与存档。
