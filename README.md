# 《幽灵行动》(PS2, SLUS-206.13) 中文汉化 —— 成品 `GR_ZH126` + 卡死修复 · 公开快照

**快照日期 2026-10-19**（收尾轮 2026-10-18 生成）· 分支 `snapshot-2026-10-19`（= 本仓库 `main`）

本仓库是《Tom Clancy's Ghost Recon》(PS2 USA 版, SLUS-206.13, "ike" 引擎) 全量中文汉化工程
**收尾阶段的公开快照**：发布**成品盘 `GR_ZH126`** 的**补丁 + 构筑/复现工具 + 全部文本文档**，
其中包含定位并修好的**游戏内卡死缺陷**（任务完成处画面定死、只能强退）。

> **本快照不含任何原游戏数据**：没有 ISO、没有字库/图形/文本资源、没有模拟器二进制。
> 只有**补丁脚本（逐字节站点表）、基底重建脚本、复现脚本与文档**。使用者须**自备正版原盘**。
> 详见文末「版权、免责与授权」。

---

## 1. 成品身份（逐项可复核）

| 项 | 值 |
|---|---|
| 盘名 | **`GR_ZH126.iso`**（2026-10-18 由 `GR_ZH2400_FINAL.iso` **改名**而来；**内容一字节未动**） |
| 尺寸 | `1,648,164,864` 字节（1,571.81 MiB） |
| **sha256** | `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5` |
| **md5** | `d24c324eb955a8c8dbaf92f6c766da2c` |
| Game CRC (PCSX2) | **`CFDB8C97`** ⇒ 即时存档文件名必须是 `SLUS-20613 (CFDB8C97).01.p2s` |
| 主程序 | `SLUS_206.13` @ LBA 295 / 37,453,732 B / sha256 `6fce4f45…38e73a` |
| 相对基底差异 | **78 字节 / 25 处**，全部落在 6 个声明窗口内（窗口外 0 字节） |
| 基底 | `GR_REBUILD2400.iso` sha256 `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0` |
| 英文原盘（**唯一合法起点**） | sha256 `2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531` |

> **版本号依据**：轮次序列已用最高 = `GR_ZH125` ⇒ 成品取 **126**（`2400` 是容量标签，不是轮次号）。
> 详见 `docs/REPORT_FINALIZE.md` §A。

成品盘**本身不在本快照里**（1.57 GB 游戏数据 + 版权原因）。本快照给的是**造出它的那 78 字节**
以及**从英文原盘一路重建它的全部脚本**。

---

## 2. ★★ 强制规则：一切构筑**必须从英文原版 ISO 出发**

```
third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso
sha256 2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531
```

**禁止以上一版汉化 ISO 为基底。** 目的 = 可复现：基底必须是「外部只读原盘 + 只读 cdvd 转储」
的函数，而不是历史产物链上的一环。执行体 = `tools/final_fix/rebuild_base.py` +
`tools/final_fix/repro_from_eng.ps1`。

**实测（2026-10-18）**：英文原盘 + K2 cdvd 块转储 ⇒ 基底（4.4 秒，sha256 与声明值一致）
⇒ 施加三件套 ⇒ 成品（sha256 与交付盘**逐字节相同**）。**旧配方「必须从 `GR_REBUILD2400.iso` 起」已作废**。

---

## 3. 修的是什么（F4 / OOMFIX / F7 三件套）

卡死根因：**PS2 版内存分配器的空闲桶链被写坏后原地无限自旋**（链头落在 RAM 之外，
`bne` 回边永不退出）。三件套把「链头非法」从**无限自旋**改成**走既有出口**：

| 名 | 站点 VA | 原字 → 新字 | cave | 一句话 |
|---|---|---|---|---|
| **F4** | `0x00102588` | `0x1459FFD1` → `0x081068D7` | `0x0041A35C`（36 B） | malloc 大块桶链扫描：链头不在 RAM 内就 bail 到既有出口 |
| **OOMFIX** | `0x00539174` | `0xAE620004` → `0x08154012` | `0x00550048`（44 B） | 解压器 malloc 返回 NULL 时不再写 `NULL+4`，改走失败分支（`s0=0`） |
| **F7** | `0x001021D4` | `0x1447FFEA` → `0x08177B31` | `0x005DECC4`（36 B） | own-bin 回边（本轮新病灶）：链头非法就 bail，截断自旋 |

全部写在**原盘既有的全零区**里；ELF 头 0x1000 B、4 个闸门、9 个参照区均逐字节未动
（每次施工/校验都会重新读盘断言）。**已被实机否证的候选修复**（F1 / F1b / flavor A、B / `pkt` /
`SPINFIX_F1F2`）**不在成品盘里**，见 `docs/CORRECTIONS.md` §7。

**验收结论（详细过程见 `docs/`）**：三闸门 ✅ · dump_font 家族 ✅ · 载荷级裸旧码 0 ✅ ·
逐字符 0 差异 ✅ · 实机 6000 帧（191 截图 / TLB 0 / Trap 0）✅ · **与基底逐帧 191/191 相同** ✅ ·
**同现场回归：未修盘 70,266 次 Trap 直接死 vs 本盘 Trap 0** ✅ ·
**复现性：从英文原盘整链出盘，sha256 与成品逐字节相同** ✅

---

## 4. 怎么用 `tools/final_fix/`

| 文件 | 作用 |
|---|---|
| `apply_fix.py` | **唯一**打补丁 / 校验器（施工 + 8 项自查 + 成品身份比对，26–27 条断言） |
| `fix_spec.json` | 单一真源：站点/原字/新字/cave 逐字、声明窗口、参照区、基底链、成品身份、**强制规则**、验收结论索引、残余风险、已归档盘 sha256 |
| `rebuild_base.py` | ★ **从英文原盘重建基底**（原盘 ⊕ K2 cdvd 转储 ⇒ `GR_REBUILD2400.iso`，7 组硬断言） |
| `repro_from_eng.ps1` | ★ **端到端一键复跑（权威配方）**：英文原盘 → 基底 → 三件套 → 成品，逐项核 sha256 |
| `repro.ps1` | 快捷复跑（路径 A：直接用现成基底出成品 / `-VerifyOnly` 校验成品盘） |
| `README.md` | 完整说明（强制规则、补丁表、7 条残余风险原文、已删对照盘的订正说明） |

### 4.1 端到端（权威配方）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1
```

### 4.2 只要出盘 / 只要校验

```powershell
python tools\final_fix\apply_fix.py --base <你的>\GR_REBUILD2400.iso --out <任意>\GR_ZH126.iso

python tools\final_fix\apply_fix.py --verify-only `
      --iso  <你的>\GR_ZH126.iso `
      --base <你的>\GR_REBUILD2400.iso
```

脚本任一条断言不通过就**拒绝写盘并非 0 退出**；通过则打印「复现成功」并写出 `--meta`（默认 `<out>.meta.json`）。

### 4.3 复现链需要什么（全部只读）

| 输入 | 说明 |
|---|---|
| 英文原版 ISO | 使用者自备（sha256 见 §2） |
| `GR_FA2400_K2 (2026-10-17 15-08-20).dump` | PCSX2 CDVD 块转储（BDV2），sha256 `11f371f2…daadd9`；**K2 的真 ELF 由它现场取出**（LBA 295 起 18,288 扇区 ⇒ 37,453,732 B，sha256 `5cb59175…`） |
| `GR_ZH113b (2026-10-15 19-39-44).dump` | 同上，sha256 `57c9e9d1…0dbf74`（GR#3451 旁证候选） |

> 转储由 PCSX2 的 `CdvdDumpBlocks = true` 选项在实跑时产生；路径与期望 sha256 也在
> `tools/final_fix/README.md` §4 与 `fix_spec.json` 里。

---

## 5. 残余风险（7 条 · 完整原文见 `docs/RELEASE_NOTES_2400.md` §4 与 `tools/final_fix/fix_spec.json`）

1. **分配器 unsorted 桶回边（`0x102200` 一带）仍未校验**：F7 只护住 own-bin 回边。
2. **F7 上界放宽到 512 MB**（`0x1FFFFFFE`）：坏值落在 `[32 MB, 512 MB)` 时会多扫一轮，
   日志多 1~2 行 `TLB Miss`（**不会自旋、不会定死**）。
3. **「汉化是否抬高触发率」未判定**：没做同场景「汉化 vs 英文」定量对照。
4. **ES / FR 语言表**抬闸门后仍带旧单字节码（(28+29)×2 处，主机语言 = ES/FR 会吞字）；
   **DE / IT** 结构异常（74+76 处）明确未动。中文/英文主机语言不渲染这些表。
5. **保留槽 `1872..2344`（473 个）按设计无字形**，文本不引用 ⇒ 不会出现空白方块。
6. **SF XML 里 5 处「配不出对的前导 `0xA4`」**为上游既有缺陷，原样保留。
7. **若干参照盘已不在盘上**（`GR_ZH124.iso`、`GR_F364.iso`、`GR_FA2400_K2*.iso`、
   `GR_REBUILD2400_allpat.iso`、`GR_SPINFIX_F4.iso`、`COMBFIX_A/B.iso`、
   `GR_LAYOUT\LAY_fix1_bytecount.iso`），受影响的验收已用等价/更强方式替代。

> ⚠ **一处口径待裁决**（`docs/CORRECTIONS.md` §1）：任务书曾要求把「汉化改了 ISO9660 的 MENU.IMG
> 声明长度」订正为"零差异"，但**成品盘实测该处确实被改**（+7,726 B，扇区对齐；ISO9660 记录与
> IMG 容器头同步）。本工程按「实测优先」登记，请以实测表为准。

---

## 6. 本快照里有什么

```
README.md                 本文件（简介 / 成品身份 / 强制规则 / 用法 / 残余 / 免责）
docs/README.md            ★ 文档总索引：一篇一行（标题 / 状态 / 一句话 / 引用数）
docs/CORRECTIONS.md       ★ 历史错误断言订正表（7 条 + 附录）
docs/STATUS.md            ★ 工程当前状态（一页纸）
docs/REPORT_FINALIZE.md   ★ 本轮收尾全记录（改名 / 从 ENG ISO 复现 / 文档整理 / 云端）
docs/_obsolete/           已归档的 21 篇（被推翻路线 / 一次性过程产物，逐篇写明理由）
docs/han_v2/*.md          早期汉化 v2 逆向方法论（**仅文本**；.bin/.MIS/.rsb/.BMB 等过程数据不入库）
tools/final_fix/          补丁 + 基底重建 + 复现（6 个文件）
.gitignore .gitattributes 防止 ISO / 大二进制 / 第三方资产被带进版本库
```

**关键入口**：现状 `docs/STATUS.md` · 索引 `docs/README.md` · 订正 `docs/CORRECTIONS.md` ·
交付说明 `docs/RELEASE_NOTES_2400.md` · 全量验收 `docs/REPORT_RELEASE_VERIFY.md` ·
根因链 `docs/REPORT_COMBFIX.md` + `REPORT_SPINFIX.md` + `REPORT_OOMFIX.md` +
`REPORT_HEAP_EXHAUSTION.md` + `REPORT_USERDUMP_ANALYSIS.md` · 容量/字库 `docs/CAPACITY_2400.md` +
`CAPACITY_2400_FA2400.md` + `TEXT_MIGRATION_0xBA.md` · 模拟器取证 `docs/HOOKEMU_QT2_GUIDE.md`。

> **历史快照**：`snapshot-2026-10-11` = `f0583003`（267 文件，早期完整工具链与 `docs/han_v2` 数据）；
> `snapshot-2026-10-18` = `5803b9ce`（67 文件，上一轮精简快照）。两者**均未删除、未改写**。

---

## 7. 版权、免责与授权

* "Tom Clancy's Ghost Recon" 及相关商标、游戏数据版权归 **Ubisoft** 所有。
  本项目为**爱好者学习/研究性质的非官方汉化**，与 Ubisoft **无任何隶属或授权关系**。
* 本快照**只包含**：①对可执行代码的**逐字节补丁表与施工脚本**（78 字节 / 25 处，
  并在原盘既有的全零区写入约 116 字节的跳转桩）；②基底重建与复现/校验脚本；③过程与结论文档。
  **不包含**任何原游戏文件、ISO 镜像、字库/图形资源、文本 dump、模拟器二进制或 BIOS。
* 使用者须**自备合法持有的正版游戏原盘**；重建基底与成品盘请在**自己的本地环境**完成，
  **请勿分发**任何由原盘派生的镜像或数据。
* 补丁的作用是**移植既有的失败退出路径**（把「链头非法 ⇒ 原地自旋」改成「⇒ 走既有出口」），
  不含任何规避版权保护的技术措施。
* 文档与脚本以「现状」提供，**不提供任何担保**；请在改动前自行备份原盘与存档。
