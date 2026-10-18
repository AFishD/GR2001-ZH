# STATUS.md —— 《幽灵行动》PS2 版（SLUS-206.13）汉化工程 · 当前状态

> 更新：**2026-10-18（脚本归位轮）** · 本文件是**唯一**的现状入口；历史过程见 `docs\PROGRESS.md` 与各轮 `REPORT_*.md`。
> 文档总索引：**`docs\README.md`**（一篇一行）· 历史错误断言订正：**`docs\CORRECTIONS.md`**
> 收尾轮全记录：**`docs\REPORT_FINALIZE.md`**（A–D 全部命令与结果）
> **脚本归位 + `work\` 清理轮全记录：`docs\REPORT_SCRIPTS_MOVE.md`** · 脚本索引：**`tools\README_scripts.md`**

---

## 1. 一句话现状

**2,400 字成品盘已交付并通过全量验收**，2026-10-18 按版本号规则改名为
**`work\builds\GR_RELEASE\GR_ZH126.iso`**（原名 `GR_ZH2400_FINAL.iso`，**只改文件名，内容一字节未动**）；
**卡死根因（分配器空闲链被写坏 ⇒ 链头落在 RAM 之外 ⇒ 原地无限自旋）已定位**，
**已用三件套 F4 / OOMFIX / F7 修复，并被实机回归证实**（未修盘 70,266 次 Trap 直接死 vs 本盘 0）；
**复现链已修好：从英文原版 ISO 出发，整链逐字节复现成品**（实测，见 §4）；
**残余风险 7 条**（见 §5）。

| 项 | 值 |
|---|---|
| 成品盘 | `work\builds\GR_RELEASE\GR_ZH126.iso`（= `GR_COMBFIX\COMBFIX_2400.iso` 逐字节同源） |
| 尺寸 / sha256 / md5 | 1,648,164,864 B / `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5` / `d24c324eb955a8c8dbaf92f6c766da2c` |
| ELF / Game CRC | `SLUS_206.13` @ LBA 295 / **`CFDB8C97`**（即时存档名 `SLUS-20613 (CFDB8C97).01.p2s`） |
| 修复工具（唯一权威） | `tools\final_fix\apply_fix.py` + `fix_spec.json`（表）/ **`repro_from_eng.ps1`（端到端权威配方）** / `rebuild_base.py`（基底重建）/ `repro.ps1`（快捷） |
| 基底链 | 英文原盘 `2b42ea7c…` ⊕ K2 cdvd 转储 ⇒ `GR_REBUILD2400.iso` `d7f83d7e…` ⇒ 本盘（相对基底 **78 B / 25 处**，窗口外 0 B） |
| 交付说明 / 验收 | `docs\RELEASE_NOTES_2400.md` / `docs\REPORT_RELEASE_VERIFY.md` |
| 验收结论 | 三闸门 ✅ · dump_font ✅ · 载荷级裸旧码 0 ✅ · 逐字符 0 差异 ✅ · 实机 6000 帧 191 截图 TLB 0 Trap 0 ✅ · 与基底逐帧 **191/191 相同** ✅ · 同现场回归 **70,266 Trap vs 0** ✅ |
| 复现性 | **★ 已达成（本轮修复）**：英文原盘 → 基底（4.4 s，sha256 与声明值一致）→ 三件套 → 成品（sha256 与交付盘一致） |
| 云端公开快照 | `public` = https://github.com/AFishD/GR2001-ZH.git · 见 §8 |
| **脚本位置（2026-10-18 起）** | **全部在 `tools\`**：各轮脚本 `tools\rounds\<主题>\**`（36 个主题 / 1,000 文件）· 逆向工具带 `tools\re\toolbelt\`（264）· 自研 Ghidra 脚本 `tools\re\ghidra_scripts\`（17）· 快照机具 `tools\snapshot\`（7）· 权威归档 `tools\final_fix\`（6）。索引 `tools\README_scripts.md`，对照表 `tools\scripts_move_map.csv` |

### 1.1 ★★ 强制规则（2026-10-18 确立 · 不可绕过）

**今后一切构筑必须从英文原版 ISO 出发**：

```
third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso
sha256 2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531   (1,648,164,864 B)
```

**禁止以上一版汉化 ISO 为基底。** 目的 = 可复现：基底必须是「外部只读原盘 + 只读 cdvd 转储」的
函数，而不是历史产物链上的一环。执行体 = `tools\final_fix\rebuild_base.py` +
`tools\final_fix\repro_from_eng.ps1`；`work\builds\GR_REBUILD\GR_REBUILD2400.iso` 降级为
**开发期快捷基底**。**旧表述「必须从 `GR_REBUILD2400.iso` 起」已作废**（`CORRECTIONS.md` §8）。

---

## 2. 修复三件套（都在游戏盘 ELF 内，逐站点表见 `tools\final_fix\fix_spec.json`）

| 名 | 站点 VA | 原字 → 新字 | cave | 作用 |
|---|---|---|---|---|
| **F4** | `0x00102588` | `0x1459FFD1` → `0x081068D7` | `0x0041A35C`（36 B） | malloc 大块桶链扫描：链头不在 RAM 内就 bail 到既有出口 |
| **OOMFIX** | `0x00539174` | `0xAE620004` → `0x08154012` | `0x00550048`（44 B） | 解压器 malloc 返回 NULL 时不再写 NULL+4，改走失败分支（`s0=0`） |
| **F7** | `0x001021D4` | `0x1447FFEA` → `0x08177B31` | `0x005DECC4`（36 B） | own-bin 回边（本轮新病灶）：链头非法就 bail，截断自旋 |

根因与定位过程：`docs\REPORT_COMBFIX.md`（本轮新病灶 F7）· `docs\REPORT_SPINFIX.md`（F4）·
`docs\REPORT_OOMFIX.md`（OOMFIX）· `docs\REPORT_HEAP_EXHAUSTION.md` · `docs\REPORT_USERDUMP_ANALYSIS.md`。

> **已被实机否证的候选修复**（不要再复活）：`F1` / `F1b` / flavor A/B / `pkt` 候选 / `SPINFIX_F1F2`。
> 见 `docs\CORRECTIONS.md` §7。

---

## 3. 怎么用这张盘

1. 复制 `GR_ZH126.iso` 到任意位置（别改字节）。
2. **不要读旧的即时存档**（`.p2s` 会把整块 32 MB 旧主存盖回 RAM ⇒ 补丁"不生效"；文件名 CRC 不符也读不到）。
   正确做法：从记忆卡存档继续，或从关卡开头进。一定要用旧档 ⇒ 改名成 `SLUS-20613 (CFDB8C97).01.p2s`；
   本盘能救（日志里可能出现 1~2 行 `TLB Miss`，属正常，关键是**不会无限重复、画面不会定死**）。
3. 复现原卡死场景：打到完成全部目标 → 出现「任务完成」提示后继续按确认 / 等它切结算。

---

## 4. 复跑与校验（不需要模拟器）

```powershell
$py = 'C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

# ★ 权威配方：从英文原版 ISO 起，整链复现（基底 + 成品，逐项核 sha256）
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1

# 校验成品（身份 + 三件套在位 + 相对基底 78 B/25 处全在窗口内）
& $py tools\final_fix\apply_fix.py --verify-only `
      --iso work\builds\GR_RELEASE\GR_ZH126.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso

# 快捷配方（开发期：直接用现成基底出成品并与交付盘逐字节比对）
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1
```

**实测（本机，2026-10-18）**：

| 步骤 | 命令 | 结果 |
|---|---|---|
| 基底重建 | `rebuild_base.py`（英文原盘 ⊕ K2 转储） | **4.4 s**，sha256 `d7f83d7e…443ca0` == 声明值 ✅ |
| 三件套出盘 | `apply_fix.py` | sha256 `d8007873…1b2ab5` == 交付成品 ✅ |
| 成品自证 | `apply_fix.py --verify-only --iso GR_ZH126.iso --base GR_REBUILD2400.iso` | **27 条断言全 OK / 失败 0**，ELF CRC `CFDB8C97` ✅ |

> **断链已修**：旧配方 `work\builds\GR_REBUILD\tools\rb_build.py` 依赖已被历史清理删除的
> `work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf` ⇒ 今天必在 `[A1]` 处 `FileNotFoundError`。
> 新配方改为**从 K2 cdvd 转储现场取 ELF**（LBA 295 起 18,288 扇区，截到 37,453,732 B，
> 断言 sha256 `5cb59175…`）⇒ **只需英文原盘 + 两块只读转储，仓库内 `work\**` 一个文件都不需要**。

---

## 5. 残余风险（7 条 · 完整原文见 `docs\RELEASE_NOTES_2400.md` §4 与 `tools\final_fix\fix_spec.json`）

1. **分配器 unsorted 桶回边（`0x102200` 一带）仍未校验**：F7 只护住 own-bin 回边；补第三个 36 B 零区在 ELF 里已扫不到（`REPORT_COMBFIX.md` §3.2）。
2. **F7 上界放宽到 512 MB**（`0x1FFFFFFE`）：坏值落在 `[32 MB, 512 MB)` 时会多扫一轮，日志多 1~2 行 `TLB Miss`（不会自旋）。
3. **归因"汉化是否抬高触发率"未判定**：没做同场景「汉化 vs 英文」定量对照；本轮只把已发生的堆损坏从致命改成可恢复。
4. **ES / FR 语言表**抬闸门后仍带旧单字节码 (28+29)×2 处（主机语言 = ES/FR 会吞字）；**DE / IT** 结构异常（74+76 处）明确未动。中文/英文主机语言不渲染这些表。
5. **保留槽 1872..2344（473 个）无字形**：按设计，文本不引用 ⇒ 不会出现空白方块。
6. **SF XML 里 5 处「配不出对的前导 `0xA4`」**：上游既有缺陷（`REPORT_SENTINEL_FIX.md` §4/§8.1 已登记），原样保留。
7. **若干参照盘已不在盘上**（`GR_ZH124.iso`、`GR_F364.iso`、`GR_FA2400_K2*.iso`、`GR_REBUILD2400_allpat.iso`、`GR_SPINFIX_F4.iso`、`COMBFIX_A/B.iso`、`GR_LAYOUT\LAY_fix1_bytecount.iso`）。受影响的验收已用等价/更强方式替代（`REPORT_RELEASE_VERIFY.md` §B/§D），sha256 记录在 `tools\final_fix\fix_spec.json · archived_away_disks`。

---

## 6. 文档（2026-10-18 整理后）

* **索引**：`docs\README.md` —— 一篇一行的「标题 / 状态（权威·历史·已过时·已归档）/ 一句话 / 引用数」。
* **订正表**：`docs\CORRECTIONS.md` —— 7 条历史错误断言逐条订正（含实测证据）+ 附录 4 条口径变更。
* **归档区**：`docs\_obsolete\`（**21 篇**被推翻路线 / 一次性过程产物，逐篇写明归档理由）；
  根目录 **105** 篇（权威 34 · 历史 60 · 已过时【就地标记】11）。
* 骨干篇：`STATUS.md`（本文）· `RELEASE_NOTES_2400.md` · `REPORT_RELEASE_VERIFY.md` ·
  `CAPACITY_2400.md` · `REPORT_COMBFIX.md` · `REPORT_SPINFIX.md` · `REPORT_OOMFIX.md` ·
  `REPORT_USERDUMP_ANALYSIS.md` · `REPORT_HEAP_EXHAUSTION.md` · `REPORT_DISASM_ROOTCAUSE.md` ·
  `REPORT_SENTINEL_FIX.md` · `TEXT_MIGRATION_0xBA.md` · `BUILD_VERSIONS.md` · `PROGRESS.md`。
* **修掉的两处过时记载**（本轮）：
  1. `tools\final_fix\README.md` §4「**特意保留** `LAY_fix1_bytecount.iso`」⇒ 该盘**已删**，
     现行表述 = 「只留 sha256 + 结论/日志/截图仍在」（§4.4）；
  2. 旧配方「**必须从 `GR_REBUILD2400.iso` 起**」⇒ 改为「从 **ENG ISO** 起；`GR_REBUILD2400.iso`
     仅作开发期快捷基底」。

---

## 7. 磁盘与仓库现状（2026-10-18 脚本归位轮）

* C: 可用空间 **84.04 GB**（本阶段开工时 80.51 GB）。
* `work\`：**7.117 GB / 18,376 文件**（本轮由 9.21 GB / 24,083 文件降下来 ⇒ 释放 ≈2.09 GB / 5,707 文件）。
  * **★ 脚本已全部迁出 `work\`**：1,253 个 `.py`/`.ps1` 移入 `tools\`（+ 34 个从 git `fe4991d1` 恢复），
    索引见 **`tools\README_scripts.md`**，逐条对照 **`tools\scripts_move_map.csv`**（1,287 行）。
    `work\` 下剩余 167 个脚本 = **27 个** `GR_HOOKEMU_QT2`（用户禁动）+ **140 个** `work\tools\ghidra\**`（第三方 Ghidra 自带）
    —— **本工程自研脚本 0 个**。
  * `work\builds\` 现在只剩两个目录：**`GR_RELEASE\`**（成品 `GR_ZH126.iso` + meta）
    与 **`GR_HOOKEMU_QT2\`**（12,501 文件 / 3.61 GB，禁动）。76 个历史版本目录已全部退役
    （删前清单 `work\_cleanup_manifest_20261018b.txt`，3,482 文件 / 1.98 GB）。
    `GR_REBUILD2400.iso`（1.53 GB）按「不保留构筑信息」删除，**可从 `repro_from_eng.ps1` 4.1 s 重建**。
  * `work\tools\**` **2.01 GB / 5,868 文件** = 反编译环境（Ghidra 12.1.2 本体 880 MB / JDK 328 MB /
    `ghidra_proj*` 793 MB 工程库 / `appdata` / 日志）。**保留**：`ghidra_proj*` 是 Ghidra 分析数据库
    = 派生证据（离线不可重建），且 15 处已迁脚本仍以 `work\tools\ghidra_out` 等为落点。
  * `work\temp\NEW_Mem\**`（3 文件 / 8.4 MB）：**用户提供的运行期证据**，被 4 篇报告标注「只读用户证据」，保留。
* ⚠ **事故与恢复**：清理时删除阶段越界，**成品盘一度被误删**，已用 `tools\final_fix\repro_from_eng.ps1`
  **从英文原盘重建**，sha256 `d8007873…1b2ab5` **与交付成品逐字节相同**，`--verify-only` 复检失败 0 条。
  详见 `docs\REPORT_SCRIPTS_MOVE.md` §0 与 `docs\CORRECTIONS.md` §9。
* git：本地 `main` —— 见 §8 与 `docs\REPORT_SCRIPTS_MOVE.md` §6。
* **云端**：见 §8。

---

## 8. 归档与云端（2026-10-18 第三轮 · 收尾刷新）

| 项 | 值 |
|---|---|
| 公开快照分支 | **`snapshot-2026-10-19`**（本轮新建；与云端 `main` **同指一个提交**） |
| 快照提交 | **`569b8a543d1eea0d5a17300cd51ae1118156436a`**（首推 `f1a39efb` → 文档回填后 `569b8a54`；父 = 上一轮快照 ⇒ 两次都是**真快进**，**全程未用任何 `--force` / `--force-with-lease`**） |
| 快照体积 | **166 文件 / 4,447,911 B（4.24 MB）**，**全文本**（`.md` 142 · `.json` 13 · `.txt` 5 · `.py` 2 · `.ps1` 2 · `.gitignore`/`.gitattributes`；**禁用类型 0 个** —— `docs/han_v2` 的 `.bin/.MIS/.rsb/.BMB`、`docs/img/*.png` 一律排除） |
| 云端 `main` | **`5803b9ce → f1a39efb → 569b8a54`**（推送原文 `   5803b9ce..f1a39efb  snapshot-2026-10-19 -> main` 与 `   f1a39efb..569b8a54  snapshot-2026-10-19 -> main`，两次 exit 0） |
| 旧公开状态备份 | 分支 **`snapshot-2026-10-11`** = `f0583003`（267 文件，**未删除、未改写**） |
| 上一轮快照 | 分支 **`snapshot-2026-10-18`** = `5803b9ce`（67 文件，**未删除、未改写**） |
| 远端 | `public` = `https://github.com/AFishD/GR2001-ZH.git` |
| 本轮新增入库 | `docs\REPORT_HOOKEMU_QT2_REBUILD.md`（**修掉上一轮快照里的 404**）· `docs\README.md` · `docs\CORRECTIONS.md` · `docs\REPORT_FINALIZE.md` · `docs\_obsolete\**` · `tools\final_fix\rebuild_base.py` · `tools\final_fix\repro_from_eng.ps1` |
| 完整记录 | **`docs\REPORT_FINALIZE.md`**（A–D 全命令与原始输出、未达成项） |

> 说明：本小节写在**快照自身**里，因此**无法自指**当前提交哈希。云端 `main` /
> `snapshot-2026-10-19` 的**当前值**以 `git ls-remote --heads public` 为准。

---

## 9. 下一步（建议）

1. **残余风险 1（unsorted 桶回边 `0x102200`）**如需收口：先在 ELF 里找/造第三个 36 B 零区（`REPORT_COMBFIX.md` §3.2）。
2. **（可选）释放 `work\tools\**` 2.01 GB**：Ghidra/JDK 反编译环境，不再反编译即可删（**本轮未执行**）。
3. **（可选）清理 `work\builds\GR_REBUILD\GR_REBUILD2400.iso`（1.53 GB）**：
   它现在是**可重建**的（`rebuild_base.py` 4.4 s）⇒ 删掉不影响复现链（注意：删了以后
   快捷配方 `repro.ps1` 需先跑一次 `rebuild_base.py`）。
4. **（可选，高风险）真正回收历史体积**：`git filter-repo --path work --invert-paths`
   （改掉所有 commit hash、需强推所有分支）—— 仅建议，**未执行**（`REPORT_ARCHIVE2.md` §D.3）。
5. **（口径待用户裁决）`CORRECTIONS.md` §1**：任务书给的「MENU.IMG 声明长度零差异」与成品盘字节
   不符（实测 +7,726 B 扇区对齐）—— 本工程按"实测优先"登记，请确认口径。
