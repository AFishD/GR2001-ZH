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

## 6. 磁盘与仓库现状（2026-10-18 归档后）

* `work\builds`：清理掉 13,155 个实验产物文件 / **释放 5.228 GB** ⇒ 22.42 GB → **17.19 GB**；C: 剩余 **47.5 GB**。
* 保留的关键盘：成品 `GR_ZH2400_FINAL.iso` · 候选 `COMBFIX_2400.iso` · 用户实机验证过的 `COMBFIX_C.iso` ·
  基底 `GR_REBUILD2400.iso` · **未修对照盘** `GR_LAYOUT\LAY_fix1_bytecount.iso`（其基底已删、不可重建）。
* git：当前分支 **`round73/font-decompile`**（**不是** `main`）；远端 `public` = `https://github.com/AFishD/GR2001-ZH.git`。
  主分支合并策略（**未执行，待决定**）见 `docs\REPORT_ARCHIVE.md` §C。
* **归档提交 = `01ab3530`**（`修复: 消除 PS2 版内存分配器自旋导致的游戏卡死 (F4/OOMFIX/F7) + 2,400 字成品验收归档`，
  52 文件 / 20,184 行；父提交 `6f81e48b`），紧随其后 `8a2554ca`（补记提交/推送状态）。两者都**只在当前分支**。
* **推送状态：未达成** —— 凭据可用（探测 push 返回 `Everything up-to-date`，远端零改动），但本分支历史含
  **24 个 >100 MB 的 blob（合计 32.9 GB）** ⇒ 必被 GitHub 拒；三条可选路径见 `docs\REPORT_ARCHIVE.md` §D。
* 归档清理明细（删了什么/留了什么/释放多少）：`docs\REPORT_ARCHIVE.md` §B。

---

## 7. 下一步（建议）

1. **决定主分支合并**：`main` 落后 290 个提交（远端 `public/main` 停在 10-11 公开快照），当前分支是 `round73/font-decompile` ⇒ 建议 `git switch main && git merge round73/font-decompile`（或先 review）。
2. 若要让「从英文原盘一键复现」复活：补 `work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf`（配方见 `tools\final_fix\README.md` §4）。
3. 残余风险 1（unsorted 桶回边）如需收口，得先在 ELF 里找/造第三个 36 B 零区。
4. 工作区仍有历史未提交改动（`work\builds` 下 270 个已跟踪文件的删除 + 4 个 `tools\**` 的历史改动），清单见 `docs\REPORT_ARCHIVE.md` §C.4。
