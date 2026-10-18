# STATUS.md —— 《幽灵行动》PS2 版（SLUS-206.13）汉化工程 · 当前状态

> 更新：2026-10-18 · 本文件是**唯一**的现状入口；历史过程见 `docs\PROGRESS.md` 与各轮 `REPORT_*.md`。
> 收尾归档的完整命令与结果：`docs\REPORT_ARCHIVE.md`

---

## 1. 一句话现状

**2,400 字成品盘已交付并通过全量验收**（`work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso`）；
**卡死根因（分配器空闲链被写坏 ⇒ 链头落在 RAM 之外 ⇒ 原地无限自旋）已定位**，
**已用三件套 F4 / OOMFIX / F7 修复，并被实机回归证实**（未修盘 70,266 次 Trap 直接死 vs 本盘 0）；
**残余风险 7 条**（见 §5）。

| 项 | 值 |
|---|---|
| 成品盘 | `work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso`（= `GR_COMBFIX\COMBFIX_2400.iso` 逐字节同源） |
| 尺寸 / sha256 / md5 | 1,648,164,864 B / `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5` / `d24c324eb955a8c8dbaf92f6c766da2c` |
| ELF / Game CRC | `SLUS_206.13` @ LBA 295 / **`CFDB8C97`**（即时存档名 `SLUS-20613 (CFDB8C97).01.p2s`） |
| 修复工具（唯一权威） | `tools\final_fix\apply_fix.py` + `fix_spec.json`（表）/ `repro.ps1`（一键）/ `README.md` |
| 基底链 | 英文原盘 `2b42ea7c…` → `GR_REBUILD2400.iso` `d7f83d7e…` → 本盘（相对基底 **78 B / 25 处**，窗口外 0 B） |
| 交付说明 / 验收 | `docs\RELEASE_NOTES_2400.md` / `docs\REPORT_RELEASE_VERIFY.md` |
| 验收结论 | 三闸门 ✅ · dump_font ✅ · 载荷级裸旧码 0 ✅ · 逐字符 0 差异 ✅ · 实机 6000 帧 191 截图 TLB 0 Trap 0 ✅ · 与基底逐帧 **191/191 相同** ✅ · 同现场回归 **70,266 Trap vs 0** ✅ |
| 复现性 | **已实测**：`apply_fix.py` 从基底出盘 → sha256 与成品**逐字节相同**（本机 9.1 s，exit 0）；`repro.ps1` 端到端 14.1 s |

---

## 2. 修复三件套（都在游戏盘 ELF 内，逐站点表见 `tools\final_fix\fix_spec.json`）

| 名 | 站点 VA | 原字 → 新字 | cave | 作用 |
|---|---|---|---|---|
| **F4** | `0x00102588` | `0x1459FFD1` → `0x081068D7` | `0x0041A35C`（36 B） | malloc 大块桶链扫描：链头不在 RAM 内就 bail 到既有出口 |
| **OOMFIX** | `0x00539174` | `0xAE620004` → `0x08154012` | `0x00550048`（44 B） | 解压器 malloc 返回 NULL 时不再写 NULL+4，改走失败分支（`s0=0`） |
| **F7** | `0x001021D4` | `0x1447FFEA` → `0x08177B31` | `0x005DECC4`（36 B） | own-bin 回边（本轮新病灶）：链头非法就 bail，截断自旋 |

根因与定位过程：`docs\REPORT_COMBFIX.md`（本轮新病灶 F7）· `docs\REPORT_SPINFIX.md`（F4）·
`docs\REPORT_OOMFIX.md`（OOMFIX）· `docs\REPORT_HEAP_EXHAUSTION.md` · `docs\REPORT_USERDUMP_ANALYSIS.md`。

---

## 3. 怎么用这张盘

1. 复制 `GR_ZH2400_FINAL.iso` 到任意位置（别改字节）。
2. **不要读旧的即时存档**（`.p2s` 会把整块 32 MB 旧主存盖回 RAM ⇒ 补丁"不生效"；文件名 CRC 不符也读不到）。
   正确做法：从记忆卡存档继续，或从关卡开头进。一定要用旧档 ⇒ 改名成 `SLUS-20613 (CFDB8C97).01.p2s`；
   本盘能救（日志里可能出现 1~2 行 `TLB Miss`，属正常，关键是**不会无限重复、画面不会定死**）。
3. 复现原卡死场景：打到完成全部目标 → 出现「任务完成」提示后继续按确认 / 等它切结算。

---

## 4. 复跑与校验（不需要模拟器）

```powershell
$py = 'C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

# 校验成品（身份 + 三件套在位 + 相对基底 78 B/25 处全在窗口内）
& $py tools\final_fix\apply_fix.py --verify-only `
      --iso work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso

# 一键复跑（从基底出成品并与交付盘逐字节比对）
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1
```

> 从**英文原盘**起的那条链（`work\builds\GR_REBUILD\tools\rb_build.py`）当前**不可直接复跑**：
> 它依赖已随历史清理删除的 `work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf`（sha256 `5cb59175…`）。
> 解封配方（从 K2 cdvd 转储取 LBA 295 起 18,288 扇区）见 `tools\final_fix\README.md` §4。

---

## 5. 残余风险（7 条 · 完整原文见 `docs\RELEASE_NOTES_2400.md` §4 与 `tools\final_fix\fix_spec.json`）

1. **分配器 unsorted 桶回边（`0x102200` 一带）仍未校验**：F7 只护住 own-bin 回边；补第三个 36 B 零区在 ELF 里已扫不到（`REPORT_COMBFIX.md` §3.2）。
2. **F7 上界放宽到 512 MB**（`0x1FFFFFFE`）：坏值落在 `[32 MB, 512 MB)` 时会多扫一轮，日志多 1~2 行 `TLB Miss`（不会自旋）。
3. **归因"汉化是否抬高触发率"未判定**：没做同场景「汉化 vs 英文」定量对照；本轮只把已发生的堆损坏从致命改成可恢复。
4. **ES / FR 语言表**抬闸门后仍带旧单字节码 (28+29)×2 处（主机语言 = ES/FR 会吞字）；**DE / IT** 结构异常（74+76 处）明确未动。中文/英文主机语言不渲染这些表。
5. **保留槽 1872..2344（473 个）无字形**：按设计，文本不引用 ⇒ 不会出现空白方块。
6. **SF XML 里 5 处「配不出对的前导 `0xA4`」**：上游既有缺陷（`REPORT_SENTINEL_FIX.md` §4/§8.1 已登记），原样保留。
7. **若干参照盘已不在盘上**（`GR_ZH124.iso`、`GR_F364.iso`、`GR_FA2400_K2*.iso`、`GR_REBUILD2400_allpat.iso`、`GR_SPINFIX_F4.iso`；2026-10-18 归档又删掉被取代的 `COMBFIX_A/B.iso`）。受影响的验收已用等价/更强方式替代（`REPORT_RELEASE_VERIFY.md` §B/§D），sha256 记录在 `tools\final_fix\fix_spec.json`。

---

## 6. 磁盘与仓库现状（2026-10-18 第二轮精简后）

* `work\`：**20.04 GB / 66,074 文件 → 9.21 GB / 24,083 文件**（本轮再释放 **10.83 GB**，54%）；
  C: 剩余空间 51.05 GB → **62.73 GB**。明细见 `docs\REPORT_ARCHIVE2.md` §C。
* `work\` 保留（5 个顶层）：`builds\`（成品 1.53 GB + 基底 1.53 GB + **`GR_HOOKEMU_QT2\**`（未动）3.69 GB + 被引用证据）、
  `tools\`（Ghidra/JDK/工程库/自研脚本 2.01 GB）、`temp\`(8 MB)、`_planc\`(5 MB)、`_briefs_recovered\`(0.6 MB)。
* 本轮**点名删除**的盘（sha256 已存证，见 `REPORT_ARCHIVE2.md` §C.4）：`GR_LAYOUT\LAY_fix1_bytecount.iso`
  （`a69a9ca4…`，未修对照盘）· `GR_COMBFIX\COMBFIX_2400.iso`（`d8007873…`，**与成品逐字节相同**）·
  `GR_COMBFIX\COMBFIX_C.iso`（`5c4c9f70…`，用户实机验证过的 F4 线盘）。
* git：当前分支 **`round73/font-decompile`**（**不是** `main`）；远端 `public` = `https://github.com/AFishD/GR2001-ZH.git`。
* **归档提交 = `01ab3530`**（52 文件 / 20,184 行），随后 `8a2554ca`、`2cd167f4` 补记；
  本轮 **`a48c4241`**（`删除: 清理误入库的 work/ 测试产物（ISO/转储/中间盘）`，移除 4,771 条 / 11,364,158 行）
  ⇒ **当前树的 432 个文件里不再有 `work/**` 与 3 张 1.5 GB ISO**。
* **推送状态：已达成**（本轮完成，见 §6b）——上一轮记录的「未达成（24 个 >100 MB blob / 32.9 GB）」已绕过：
  不推完整历史，改为**孤儿精简快照**直推 `main`。
* **历史体积未回收**：被删的 `work/` blob 仍可从历史到达，`git gc --prune=now` 只能继续打包；
  真正回收需 `git filter-repo`/BFG 重写历史（高风险，**未执行**）⇒ `docs\REPORT_ARCHIVE2.md` §D.3。
* 归档清理明细：本轮 `docs\REPORT_ARCHIVE2.md` §C；上一轮 `docs\REPORT_ARCHIVE.md` §B。

---

## 6b. 归档与云端（2026-10-18 第二轮 · **已推送**）

| 项 | 值 |
|---|---|
| **公开快照分支** | **`snapshot-2026-10-18`** —— 与云端 `main` **同指一个提交**（= 快照链最新提交） |
| 首推的修复落点 | 提交 **`2c899a418593a31ebacd11f2b8b734ee61311052`**（孤儿；**修复内容就在这个提交里**，始终留在 `main` 历史中） |
| 快照体积 | **67 文件 / 2,007,423 B ≈ 1.91 MB**，全文本（无 ISO / 无游戏数据 / 无模拟器二进制） |
| **云端 `main`** | 首推把它从 `f0583003` 强更到 `2c899a41`（`git push public snapshot:refs/heads/main --force-with-lease`，原文 `+ f0583003...2c899a41 (forced update)`，exit 0）；随后为同步本小节等文档**快进**到 `59e43d45` 及后续文档提交 ⇒ 与 `snapshot-2026-10-18` 恒同指 |
| 旧公开状态备份 | 分支 **`snapshot-2026-10-11`** = `f0583003`（267 文件，**未删除、未改写**） |
| 远端 | `public` = `https://github.com/AFishD/GR2001-ZH.git`；`git ls-tree -r --name-only public/main` = 67 |
| 快照内容 | `tools\final_fix\**`(4) + `docs\**`(60 = 本轮 48 + 被引用 12) + 公开版 `README.md` + `.gitignore`/`.gitattributes` |
| 推送结果 | **达成，无未达成项**（无网络/凭据/权限错误；未用裸 `--force`、未删远端分支、未改本地历史） |
| `work\` 精简 | 释放 **10.83 GB**；保留清单与"未动"清单见 `REPORT_ARCHIVE2.md` §C.1/§C.6 |
| 仓库当前树 | `a48c4241` ⇒ 树 **432 文件**；pack 体积变化见 `REPORT_ARCHIVE2.md` §D.2 |
| 完整记录 | **`docs\REPORT_ARCHIVE2.md`**（A–F 全命令与原始输出、取舍说明、未达成/需确认项） |

> 说明：本小节写在**快照自身**里，因此**无法自指**当前提交哈希（每一次「记录推送结果」都会产生新提交）。
> 云端 `main` / `snapshot-2026-10-18` 的**当前值**以 `git ls-remote --heads public` 为准；
> 而**修复落点**永远是 `2c899a41`（在其历史中）。

> ⚠ **一处按任务书执行、但与旧文档记载冲突的事**：`GR_LAYOUT\LAY_fix1_bytecount.iso`（未修对照盘，基底已删、
> **不可重建**）本轮被**点名删除**。「同现场回归（70,266 Trap vs 0）」今后**不能原样复跑**，其结论与日志/截图
> 仍在。`tools\final_fix\README.md` §4 那句「特意保留」**已过时**（该目录本轮禁动，未修改）⇒ 见 §C.5。

---

## 7. 下一步（建议）

1. **残余风险 1（unsorted 桶回边 `0x102200`）**如需收口：先在 ELF 里找/造第三个 36 B 零区（`REPORT_COMBFIX.md` §3.2）。
2. **让「从英文原盘一键复现」复活**：补 `work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf`（配方见 `tools\final_fix\README.md` §4）。
3. **本地分支归置**：当前在 `round73/font-decompile`（工作区仍有 270 个 `work/` 已跟踪文件的删除状态残留、
   4 个 `tools\**` 历史改动未提交 ⇒ `REPORT_ARCHIVE.md` §C.4）。是否把 dev 分支并入本地 `main`（`fe4991d1`）待决定；
   **云端 `main` 已是本轮修复快照，不受影响**。
4. **（可选，高风险）真正回收历史体积**：`git filter-repo --path work --invert-paths`（改掉所有 commit hash、
   需强推所有分支）—— 仅建议，**未执行**，详见 `REPORT_ARCHIVE2.md` §D.3。
5. **（可选）继续精简**：`work\tools\**` 2.01 GB（Ghidra 12.1.2 / JDK / Ghidra 工程库；不再做反编译时可删）。
6. **补唯一断链**：`docs/REPORT_HOOKEMU_QT2_REBUILD.md` 从未入库（公开快照里 404）⇒ 确认可公开后入库并刷新快照分支。
