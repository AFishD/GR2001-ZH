# REPORT_ARCHIVE.md —— 2026-10-18「收尾归档」执行报告（A–E 全记录）

> 仓库根：`C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> 执行：收尾归档执行者（本报告 = A/B/C/D/E 五步的命令与结果原文，含未达成项）
> 关联：`docs\STATUS.md`（现状）· `docs\RELEASE_NOTES_2400.md` §7（交付说明的归档小节）·
> `tools\final_fix\`（归并后的唯一权威修复工具）

---

## 0. 摘要

| 步骤 | 做了什么 | 结果 |
|---|---|---|
| **A** | git 现状清点（分支/远端/忽略规则/脏文件分类） | ✅ 完成 —— 当前分支 **`round73/font-decompile`**（**不是** main）；远端 `public` 存在；`work/**` 被 `.gitignore:61` 忽略但**已有 4771 个文件被历史跟踪** |
| **B** | 归并出唯一一份修复脚本 `tools\final_fix\`（4 文件）+ 清理 `work\builds` 实验产物 | ✅ 释放 **5.228 GB**（13,155 个文件）；**实测复现**：从基底出盘 sha256 与成品逐字节相同 |
| **C** | 把修复 + 文档提交到**当前分支**（不切分支、不 merge、不动 `work\builds` 的 ISO） | ✅ 提交完成（hash 见 §C.5 补记）；未纳入清单见 §C.4 |
| **D** | 推送云端 | ❌ **未达成**：凭据可用，但本分支要上传 **32.9 GB / 24 个 >100 MB 的 blob** ⇒ GitHub 必拒。原因、证据与三条可选路径见 §D |
| **E** | 更新文档与状态 | ✅ `docs\STATUS.md`（新建）· `docs\RELEASE_NOTES_2400.md` §7（归档信息）· 本文件 |

**成品盘没有被改动过**：`work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso`
sha256 `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5` / md5 `d24c324eb955a8c8dbaf92f6c766da2c`
/ 1,648,164,864 B / ELF CRC **`CFDB8C97`**（归档前后各复核一次，数值一致）。

---

## A. git 现状清点

### A.1 命令与原始结果

```powershell
git status --short ; git branch -vv ; git remote -v ; git log --oneline -5 ; git rev-parse --abbrev-ref HEAD
```

| 命令 | 结果 |
|---|---|
| `git rev-parse --abbrev-ref HEAD` | **`round73/font-decompile`** |
| `git rev-parse --short HEAD` | `6f81e48b`（round93：slot→row 映射刚性修正） |
| `git remote -v` | `public  https://github.com/AFishD/GR2001-ZH.git (fetch/push)` |
| `git status --porcelain`（归档前） | **4 modified · 270 deleted · 49 untracked** |
| `git ls-files work/` | **4771**（`work/**` 虽被忽略，但历史轮次已入库的文件仍在索引里） |
| `git ls-files docs/` / `tools/` / 全部 | 94 / 270 / **5151** |
| `git rev-list --count HEAD` | **290**（本仓库全部历史就只有 290 个提交） |

### A.2 三件确认事项

**① 当前在哪个分支** ⇒ `round73/font-decompile`（**不是** `main`；`main` 停在 `fe4991d1`）。

**② `work/**` 是否被 `.gitignore` 忽略** ⇒ **是**：

```powershell
git check-ignore -v work/builds/GR_RELEASE/GR_ZH2400_FINAL.iso
# .gitignore:61:work/**	work/builds/GR_RELEASE/GR_ZH2400_FINAL.iso
git check-ignore -v work/builds/GR_COMBFIX/tools/x.py
# .gitignore:61:work/**	work/builds/GR_COMBFIX/tools/x.py
```

> 但注意：`.gitignore` 只影响**新文件**。早前轮次入库的 `work/builds/**`（CSV/JSON/PNG，以及 3 张 1.5 GB 的
> `GR_TEST_FONT3.iso` / `GR_TEST_PROBE_LEAD.iso` / `GR_ZH111.iso` 等）**仍在索引与 HEAD 里** ⇒
> 这既是"270 个已跟踪文件被删"的来源，也是 §D 推送失败的根因。

**③ 主分支叫什么 / 工作区有多少未提交改动** ⇒ 主分支 = **`main`**（远端也有 `main`，但它停在 **f0583003**，
即 2026-10-11 的**孤儿公开快照**提交，与本地 HEAD **没有共同祖先**）。归档前脏文件分类：

| 类别 | 数量 | 分类结论 |
|---|---|---|
| `work/builds/**` 被删的**已跟踪**文件（` D`） | **270** | **历史遗留**：早期轮次把测试产物入了库，后来又按"work 不入库"策略从磁盘删掉，但删除从未提交 |
| `tools/**` 修改（` M`） | **4** | **历史遗留（与本修复无关）**：`tools/diag/dump_all_text.py`、`tools/font_pipeline/data/charset_compiled_zh16.json`（= **HASHR 版 2,300 对偶**，不是成品的 2,350；成品那份在 `work/builds/GR_HASHR/backup/charset_compiled_zh16.json.before_hashr`）、`tools/text_csv/inject_text_csv.py`、`tools/text_csv/tcslib.py`；4 个文件的 mtime 都是 **10-15**（早于本次归档） |
| `docs/**` 未跟踪（`??`） | **47** | **本次汉化/修复产生的文档**（10-14 ~ 10-18 的 2400 产品线与卡死修复全过程文档；**全部**是本次交付的直接产物） |
| `tools/text_csv/gate_pairs.json`、`tools/final_fix/`（`??`） | 2 | 前者=历史遗留（10-15，0xBA 迁移用），后者=**本次归档产物** |

> 另有 1 个未跟踪文件 `docs\REPORT_HOOKEMU_QT2_REBUILD.md`（mtime 17:27）—— 它属于**仍在运行的 Qt 钩子便携版
> 重建执行者**（`work\builds\GR_HOOKEMU_QT2\**`），本报告**故意不提交**它，避免把别人写到一半的文件入库。

---

## B. 只留一份脚本 + 清理构筑目录

### B.1 `tools\final_fix\` —— 唯一的、可复现修复与成品的那套脚本

放在**被 git 跟踪的树**里的理由：`.gitignore:61` 是 `work/**`（整个 work 不入库），只有 `tools/**` 能进版本控制。

| 文件 | 内容 |
|---|---|
| `apply_fix.py`（402 行） | **唯一**打补丁/校验器：施工 + 8 项自查 + 成品身份比对；`--verify-only` 只校验不写盘 |
| `fix_spec.json` | **单一真源**：3 站点（VA/ISO off/ELF off/原字/新字/延迟槽/出口）+ 3 cave 逐字与反汇编 + 声明窗口 + 参照区 + 4 闸门 + 基底链（含 2 个 cdvd 转储 sha256）+ 成品身份 + **验收结论索引**（10 条）+ 7 条残余 + 已归档盘 sha256 |
| `repro.ps1`（90 行，纯 ASCII） | 一键复跑：核对基底 → 出盘 → 与交付盘逐字节比对 → 报 PASS/FAIL |
| `README.md` | 中文说明：怎么打补丁、怎么验证、一键复跑（路径 A/B）、补丁表、已知残余、用法边界 |

**权威版本来源（已在 README/§provenance 里逐条标注）**：
`F4` ← `work\builds\GR_SPINFIX\tools\spinfix_apply.py` 的 `CAVE_F4`（逐字相同）；
`OOMFIX` ← `work\builds\GR_OOMFIX\tools\oomfix_apply.py` 原样（含 `s0=0`）；
`F7` ← `work\builds\GR_COMBFIX\tools\combfix_apply.py` 新写；
**已清理掉的当轮实验分支**：`F1`（`0x101DC0` / cave `0x55B730`）、`F1b`（`0x101D60`）、`combfix_apply.py` 的 flavor `A`/`B`。

**实测（本机，python = `C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`）**：

```powershell
# ① 校验成品（26 条断言）
& $py tools\final_fix\apply_fix.py --verify-only --iso work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso --base work\builds\GR_REBUILD\GR_REBUILD2400.iso
#   ⇒ 5.5 s，exit 0，全部 OK，结论「该盘就是交付成品」
# ② 从基底复现（写盘）
& $py tools\final_fix\apply_fix.py --base work\builds\GR_REBUILD\GR_REBUILD2400.iso --out <临时目录>\GR_ZH2400_FINAL.iso
#   ⇒ 9.1 s，exit 0；出盘 sha256 = d8007873…b2ab5 = 成品 ⇒ 逐字节相同
# ③ 一键
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1
#   ⇒ 14.1 s，exit 0，输出「OK byte-identical to the shipped disc / REPRODUCTION OK」
```

**一键复跑链路（如实）**：
`路径 A（已实测）` = `GR_REBUILD2400.iso`（`d7f83d7e…443ca0`）→ `apply_fix.py` → 成品。
`路径 B（从英文原盘起，当前被卡住）` = `work\builds\GR_REBUILD\tools\rb_build.py` 需要 3 个外部/已删输入，
实测报错：

```
FileNotFoundError: 'C:\...\work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf'
```

| 输入 | 现状 | 期望 sha256 |
|---|---|---|
| `third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso` | ✅ 在盘上（只读） | `2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531` |
| `%LOCALAPPDATA%\PCSX2\cdvd-dump\GR_FA2400_K2 (2026-10-17 15-08-20).dump` | ⚠ 在盘上但在**仓库外** | `11f371f294e4f8e353c21931a9c38d73c1309832a21e74cfb3e31d7095daadd9` |
| `%LOCALAPPDATA%\PCSX2\cdvd-dump\GR_ZH113b (2026-10-15 19-39-44).dump` | ⚠ 同上 | `57c9e9d147106c7c7dbc5e41b6a80ffa6ce7ea984ec21b33505fb765b40dbf74` |
| `work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf` | ❌ **已随历史清理删除**（目录在、文件没了） | `5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8` |

⇒ 这**正是**任务书预判的情形：**必须从 `GR_REBUILD2400.iso` 起**（sha256 见上）。解封配方（从 K2 转储取
LBA 295 起 18,288 扇区写出该 ELF）写在 `tools\final_fix\README.md` §4。

### B.2 清理规则（先打印清单再执行）

规则（**证据优先**，避免删掉被引用的东西）：只在任务书点名的 20 个实验目录内动手，删除对象 =
`{.iso, .bin, .p2s, .png, .elf, .dmp, .npy, .zip, .7z, .pch, .dat}` + `__pycache__`，
且**排除** `\bios\`、`\emu\` 路径，且**该文件的相对路径没有出现在任何 `docs\**` / `work\builds\**` 的
`.md`/`.json` 全文里**（脚本见 §附录）。**脚本（`.py`/`.ps1`）、报告、关键 JSON/CSV 一律保留。**

被引用而**受保护未删**的 14 个文件（其中 2 个是关键盘）：

```
1571.81 MB  work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso          ← 同现场回归的「未修对照盘」
1571.81 MB  work\builds\GR_REBUILD\GR_REBUILD2400.iso             ← 修复链基底（一键复跑第 1 步输入）
   14.55 MB  work\builds\GR_REPRO\common\state_LAY_fix1_bytecount.p2s
   14.25 MB  work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s
    0.25 MB  work\builds\GR_CULPRIT\shots\lay_state.png
    ... （其余为 GR_DFIX / GR_REBUILD 的 font_atlas 证据图）
```

### B.3 清单与释放量（执行结果）

```
[refs] referenced work-builds path entries = 4035  (scanned 1875 md/json files)
[keep] skipped because referenced by md/json = 14 files
[plan] to delete = 13155 files / 5.228 GB
```

| 目录 | 文件数 | 释放 |
|---|---|---|
| `GR_COMBFIX`（仅 A/B 两个**被取代的变体盘**） | 2 | 3,143.6 MB |
| `GR_FPS` | 4,628 | 845.1 MB |
| `GR_SPINFIX` | 1,575 | 290.7 MB |
| `GR_REBUILD` | 1,260 | 243.7 MB |
| `GR_DFIX` | 1,004 | 222.2 MB |
| `GR_LAYOUT` | 805 | 177.8 MB |
| `GR_OOMFIX` | 1,326 | 166.8 MB |
| `GR_MEMDRIFT` | 748 | 139.0 MB |
| `GR_REPRO` | 491 | 61.2 MB |
| `GR_HASHR` | 385 | 53.0 MB |
| 其余 10 个目录（FPSBISECT/CULPRIT/SENT/NULLHUNT/HOOK/AB/TXT/CVAR/HEAP/HUGE） | 931 | 11.9 MB |

按类型：`.iso`（变体盘）3,143.6 MB / `.png` 1,707.8 MB（10,620 张运行截图）/ `.bin` 401.6 MB（RAM 快照）/
`.p2s` 99.8 MB / `__pycache__` 0.4 MB。

```
work\builds  BEFORE = 22.418 GB   AFTER = 17.19 GB   FREED = 5.228 GB
C: free      42.58 GB  →  47.49 GB
```

**删除后 `work\builds` 剩余（≥20 MB 的目录）**：`GR_COMBFIX` 3,733.7 · `GR_HOOKEMU_QT2` 3,694.4（**未动**）·
`GR_RELEASE` 1,711.7 · `GR_REBUILD` 1,591.4 · `GR_LAYOUT` 1,583.2 · `GR_HOOKEMU` 980.9 · `GR_THR86` 394.6 ·
`GR_ZH98` 348.6 · `GR_F364` 277.8 · `GR_ZH105` 238.2 · `GR_SPINFIX` 235.4 · `GR_TEST_FONT1` 234.1 · `GR_ZH116` 213.2 ·
`GR_OOMFIX` 178.1 · `GR_ZH107` 175.6 · `GR_ZH108` 173.9 · `GR_CAP2400` 171.8 · `GR_FA2400_K2` 158.3 · `GR_REPRO` 157.9 ·
`GR_ZH106` 154.1 · `GR_FA2400` 124.5 · `GR_CULPRIT` 104.7 · `GR_ZH109` 97.6 · `GR_TEST_FONT2` 94.7 · `GR_ZH115` 79.1 ·
`GR_FPSBISECT` 58.4 · `GR_F365` 51.2 · `GR_ZH113` 48.1 · `GR_ZH111` 45.1 ·（其余 40+ 个目录均 < 33 MB）。

**保留清单（要点）**：成品 `GR_RELEASE\GR_ZH2400_FINAL.iso`+meta（及其 191 帧实机验收证据 `GR_RELEASE\runs`、
`states`、`temp`）· `GR_COMBFIX\{COMBFIX_2400.iso, COMBFIX_C.iso, states\*, tools\*, *.md, out\, runs\}` ·
`GR_HOOKEMU_QT2\**`（**一个字都没动**）· `GR_ZH98\temp\LEAD_CAPACITY_2400.md` 与 `r82\*`（charset 快照/LEAD 文书）·
`GR_TXMIG\temp\handoff\glyph_handoff.json` · `GR_HASHR\backup\charset_compiled_zh16.json.before_hashr`（重建链要用的
K2 charset）· 被 `docs\**` 引用的全部证据 · 各目录**全部 `.py/.ps1/.md/.json/.csv/.txt`**。

**两张关键盘被特意保留（与任务书字面删除清单的偏差，理由如下）**：
`GR_REBUILD\GR_REBUILD2400.iso`（1.57 GB）= 修复链基底，删了就没法"从基底一键复现"；
`GR_LAYOUT\LAY_fix1_bytecount.iso`（1.57 GB）= 「同现场回归」里那张**未修对照盘**（70,266 次 Trap 的来源），
其基底 `GR_LAYOUT\base\` 已被历史清理清空 ⇒ **不可重建**。若你确认不要这两张，可再释放 **3.14 GB**。

**已删除的变体盘身份**（sha256 记进 `tools\final_fix\fix_spec.json · archived_away_disks`，meta/runs 证据保留）：
`COMBFIX_A.iso` = `e12f2770d041f5ac02079c37fcb7137a49310538adb79dba026224cbb4edccc2` ·
`COMBFIX_B.iso` = `3959498be967447b0404745885a0fc7f616c85d97dfa7833979b563531c16b41`。

---

## C. 提交（在当前分支，不切分支、不 merge）

### C.1 策略（按任务书 C-1）

当前分支 `round73/font-decompile` **不是**主分支 ⇒ 按"**不擅自 merge**"的要求：**没有** `git switch main`、
**没有** merge、**没有**动远端。修复与文档提交在**当前分支**上。
**建议**（等你决定）：`git switch main && git merge round73/font-decompile`
（或先 `git diff main..round73/font-decompile --stat` 复核）；远端 `public/main` 停在 10-11 的孤儿公开快照，
与本地 `main` 无共同祖先，合并前需要先想清楚"公开快照怎么出"（见 §D）。

### C.2 提交内容（只 `git add` 明确列出的路径，不用 `git add -A`）

```
tools/final_fix/{README.md, apply_fix.py, fix_spec.json, repro.ps1}     ← 4 个（本次归档产物）
docs/STATUS.md  docs/RELEASE_NOTES_2400.md                              ← 新建 / 更新
docs/{REPORT_RELEASE_VERIFY, REPORT_COMBFIX, REPORT_SPINFIX, REPORT_OOMFIX, REPORT_HEAP_EXHAUSTION,
      REPORT_USERDUMP_ANALYSIS, CAPACITY_2400, CAPACITY_2400_FA2400, OOMFIX_TEST_GUIDE, REBUILD_PLAN,
      REBUILD_REPORT, REPORT_LAYOUT_AUDIT, DFIX_REPORT, DISASM_TEST_GUIDE, REPORT_DISASM_ROOTCAUSE,
      CSFIX_TEST_GUIDE, REPORT_SENTINEL_FIX, REPORT_SENTINEL, REPORT_CULPRIT_STORE, REPORT_SAVESTATE_REPRO,
      REPORT_EMU_SETTINGS_SYNC, HOOKED_EMU_GUIDE, REPORT_HOOKED_EMU, HOOKEMU_QT2_GUIDE, REPORT_HOOKEMU_QT2,
      REPORT_FPS_ZH113b, REPORT_FPS_BISECT, REPORT_MEMDRIFT_ZH113b, REPORT_NULLDEREF_ZH113b,
      REPORT_HOOK_BISECT, REPORT_TEXT_OVERFLOW, TEXT_MIGRATION_0xBA, RISK_BUDGET_r84, REPORT_r84,
      REPORT_W2048_r84, REPORT_w2048_probe, REPORT_atlas_stall_threshold, REPORT_texture_limit_rootcause,
      REPORT_r83_ft_record_route, CONTAINER_INVENTORY_r83, FONTRES_STRUCTURE_r83, REPORT_final_364,
      REPORT_zero_missing_glyph_build2, AB_TEST_GUIDE, CVAR_TEST_GUIDE}.md   ← 45 个（2400 线与修复全过程文档）
```

共 **51 个文件，19,775 行新增**（`git diff --cached --stat` 末行）：`51 files changed, 19775 insertions(+)`。

### C.3 提交前自检（原文）

```powershell
git status --porcelain        # 计数
# staged(A/M/D): 51   unstaged(M/D): 274   untracked(??): 2
git diff --cached --stat | tail
# docs/TEXT_MIGRATION_0xBA.md | 777 ++++++++++   tools/final_fix/README.md | 193 +++
# tools/final_fix/apply_fix.py | 402 +++          tools/final_fix/fix_spec.json | 244 +++
# tools/final_fix/repro.ps1 | 90 +++              51 files changed, 19775 insertions(+)
```

> `git status` 里 **没有任何 `work/builds` 的 ISO / 大二进制进入暂存区**（`.gitignore` 已确认拦截：§A.2）。

### C.4 **未纳入本次提交**的改动清单（按任务书要求逐条列出）

| 未纳入项 | 数量 | 为什么没纳入 | 建议 |
|---|---|---|---|
| `work/builds/**` 已跟踪文件的**删除**（` D`） | **270** | 与本修复无关的**历史遗留**（策略变更导致，非本次删除；本次清理删掉的 13,155 个文件全部是**未被跟踪**的，故没有新增 D 条目） | 若要让索引与磁盘一致，可另起一个 `chore(work): 提交 work/ 陈旧跟踪文件的删除` 提交（内容仍在 git 历史里，可恢复） |
| `tools/**` 的修改（` M`） | **4** | 10-15 的历史改动（text/charset 工具链），**与本修复无直接关系**；且 `charset_compiled_zh16.json` 是 **HASHR 版 2,300 对偶**，与成品的 2,350 不同口径 | 由熟悉该轮的人单独提交（我未改动这些文件） |
| `tools/text_csv/gate_pairs.json`（未跟踪） | 1 | 10-15 的历史产物（0xBA 迁移），非本次归档产物 | 同上 |
| `docs/REPORT_HOOKEMU_QT2_REBUILD.md`（未跟踪） | 1 | **仍在运行的执行者** `ee5069bd`（`work\builds\GR_HOOKEMU_QT2\**`）正在写它（mtime 17:27） | 等它写完由它自己提交 |

### C.5 commit message（实际使用）

```
修复: 消除 PS2 版内存分配器自旋导致的游戏卡死 (F4/OOMFIX/F7) + 2,400 字成品验收归档

- 归并 work/builds/{GR_COMBFIX,GR_SPINFIX,GR_OOMFIX}/tools 的补丁脚本为唯一权威工具 tools/final_fix/
  (apply_fix.py 施工+8 项自查 · fix_spec.json 单一真源 · repro.ps1 一键复跑 · README.md 说明书);
  删掉只用于当轮 A/B 实验的分支 (F1/F1b、flavor A/B)
- 三件套: F4 0x00102588→cave 0x0041A35C · OOMFIX 0x00539174→cave 0x00550048 · F7 0x001021D4→cave 0x005DECC4;
  相对基底只改 78 B / 25 处, 声明窗口外 0 B
- 成品 work/builds/GR_RELEASE/GR_ZH2400_FINAL.iso sha256 d8007873… / md5 d24c324e… / ELF CRC CFDB8C97;
  实测 apply_fix.py 从基底 GR_REBUILD2400.iso 出盘 = 与成品逐字节相同 (exit 0), repro.ps1 端到端 14.1 s
- 验收结论索引见 docs/REPORT_RELEASE_VERIFY.md: 三闸门 / dump_font / 载荷级裸旧码 0 / 逐字符 0 差异 /
  实机 6000 帧 191 截图 TLB 0 Trap 0 / 与基底逐帧 191-191 相同 / 同现场回归 未修 70,266 Trap vs 本盘 0
- 归档文档: docs/STATUS.md (现状 + 7 条残余) · docs/REPORT_ARCHIVE.md (A-E 全记录) ·
  docs/RELEASE_NOTES_2400.md §7 归档信息
- 清理 work/builds 5.228 GB 实验产物 (13,155 文件); 保留成品/候选/实机验证盘、基底、未修对照盘与被 docs 引用的证据
```

> 归档提交 hash 与推送结果见 §D.4「补记」（本文件随该提交入库 ⇒ 无法自指哈希，故在随后的小提交里补记）。

### C.5b 提交结果补记（提交后填写）

* **归档提交 = `01ab3530`**，分支 **`round73/font-decompile`**，父提交 `6f81e48b`；
  `52 files changed, 20184 insertions(+)`（= §C.2 的 51 个文件 + 本文件）。
* 提交信息文件：`%TEMP%\gr_commit_msg.txt`（内容即 §C.5，中英双语；未入库）。
* 提交后工作树剩余：`unstaged 274`（270 个 `work/builds` 陈旧删除 + 4 个 `tools/**` 历史改动）、
  `untracked 2`（`docs/REPORT_HOOKEMU_QT2_REBUILD.md`、`tools/text_csv/gate_pairs.json`）—— 明细见 §C.4。
* 本補記所在的提交紧随其后（`git log --oneline -2` 可见），不含任何代码/数据改动。

---

## D. 推送云端：**未达成**（凭据可用，但内容体量必被拒）

### D.1 命令与结果

```powershell
git remote -v
# public  https://github.com/AFishD/GR2001-ZH.git (fetch)
# public  https://github.com/AFishD/GR2001-ZH.git (push)

git fetch --all --prune          # exit 0
git branch -r
#   public/HEAD -> public/main
#   public/main
#   public/snapshot-2026-10-11
git ls-remote --heads public
# f0583003ab15e69955c70d2c02b1b66495f7ee07  refs/heads/main
# f0583003ab15e69955c70d2c02b1b66495f7ee07  refs/heads/snapshot-2026-10-11
git rev-list --left-right --count HEAD...public/main
# 290   1
```

* `fetch` 成功（exit 0），远端没有新东西；`public/main` 与 `public/snapshot-2026-10-11` **指向同一个提交**
  f0583003，而它是**孤儿提交（无 parent）**—— 即上次对外发布用的是"公开快照"办法，而不是真实历史。
* `290 1` 的含义：HEAD 有 290 个提交不在 `public/main` 里（= 本仓库**全部**历史），
  `public/main` 有 1 个提交不在 HEAD 里（那个孤儿快照）⇒ 二者**无共同祖先**，谈不上"落后/领先"。

### D.2 凭据探测（**没有上传任何对象**）

```powershell
git push public f0583003ab15e69955c70d2c02b1b66495f7ee07:refs/heads/snapshot-2026-10-11
# Everything up-to-date     [exit=0]
git ls-remote --heads public      # 探测前后完全一致（未改动远端任何一个分支）
```

⇒ **凭据/连通性正常**（HTTPS 走 `credential.helper=helper-selector`），远端分支一个字节没变。

### D.3 为什么不能 **直接** `git push`（硬证据）

```
git rev-list --objects public/main..HEAD   →  23,066 个对象 = 290 commit + 2,348 tree + 20,428 blob
blob 合计 = 32,921.4 MB（32.9 GB）
其中 > 100 MB 的 blob = 24 个；> 20 MB 的 = 116 个
最大的几个：
  1571.8 MB × 15 个（早前轮次入库的整盘 ISO：GR_TEST_FONT3 / GR_TEST_PROBE_LEAD / GR_ZH111 …）
   482.5 MB × 3 个（memwatch.bin 内存监视转储）
   103.6 MB × 1 个（GR_ZH98/temp/r56/runs105b.json）
```

同时 HEAD 的**工作树本身**也是 9,752 MB（其中 `work/` 9,745 MB，含 3 张仍在索引里的 1.5 GB ISO；
**去掉 `work/` 只有 7.1 MB**）。

结论：**GitHub 单文件硬上限 100 MB**（超限 `remote: error: File … exceeds GitHub's file size limit of 100.00 MB`，
且单次 push 还有 2 GB 量级的实际限制）⇒ 这条分支**无法**直接推到 GitHub：要么被拒，要么先白传几十 GB。
因此我**没有**发起这次注定失败的 33 GB 上传（避免长时间占满带宽而结果仍是失败）。

### D.4 三条可选路径（**需要你/父代理决定**，我未擅自执行）

| 方案 | 做法（现成命令） | 代价 / 风险 |
|---|---|---|
| **① 孤儿"公开快照"分支（推荐，仓库既有做法）** | 用**临时索引**只把 `tools/`+`docs/`+`.gitignore`+`.gitattributes`+`README.md`+`third_party/readme.md`（≈ **7.1 MB**）打成**无父提交**，再推成新分支：<br>`$env:GIT_INDEX_FILE="$env:TEMP\snapidx"; git read-tree --empty; git add -- tools docs .gitignore .gitattributes README.md third_party/readme.md; $t=git write-tree; $c=git commit-tree $t -m "GR2001-ZH 公开快照 2026-10-18 — 2400 成品 (GR_ZH2400_FINAL, ELF CRC CFDB8C97) + F4/OOMFIX/F7 卡死修复 + tools/final_fix"; git branch snapshot-2026-10-18 $c; git push public snapshot-2026-10-18` | 只上传 ~7 MB；**不改历史、不 force、不快进 main**；但会把 `docs/**` 里 47 篇过程文档**公开发布**（上次快照同样含 docs）。需你点头"可以公开发布这些文档" |
| **② 换一个能收 33 GB 的远端 / 用 LFS** | 提供自建 Git 服务或对象存储；或把大 blobs 迁 Git LFS（需重写历史 ⇒ 与"不改历史"冲突，只能对新仓库做） | 成本高；GitHub 免费额度/单文件限制依旧 |
| **③ 只推"小文件"的分支** | 与①同法，但把 `docs/` 也筛一遍（例如只放 `STATUS/RELEASE_NOTES/REPORT_ARCHIVE/final_fix`），做成"对外交付包"分支 | 最保守；但仓库里就没有完整过程文档 |

> **我的建议**：选 **①**（与 2026-10-11 那次公开快照同法），但**先由你确认可以公开发布 `docs/**` 这 47 篇文档**；
> 一旦确认，上面那条命令一条就能完成，且不会触碰 `main`、不需要 force。

### D.5 推送结果补记（提交后填写）

* **归档提交**：`01ab3530`（`round73/font-decompile`）。
* **远端推送：未执行。** 依据 §D.3 的硬数字（32.9 GB / 24 个 >100 MB 的 blob）⇒ 必被 GitHub 拒；
  为避免"上传几十 GB 之后仍然失败"，**没有**发起该次 push（**没有**使用 `--force`，**没有**改历史，
  **没有**删除/新建任何远端分支）。
* **远端零改动证明**：§D.2 的凭据探测 `exit=0`（`Everything up-to-date`），探测前后
  `git ls-remote --heads public` 输出**完全一致**（`main` 与 `snapshot-2026-10-11` 都在 `f0583003`）。
* **需要什么**：你（或父代理）在 §D.4 的 ①/②/③ 里选一个，尤其需要**明确同意把 `docs/**` 公开发布**
  （方案①）或给出可收 33 GB 的远端（方案②）。

---

## E. 文档与状态更新

| 文件 | 动作 | 内容 |
|---|---|---|
| `docs\STATUS.md` | **新建** | 唯一现状入口：一句话现状（2,400 成品已交付并通过全量验收 / 卡死根因=分配器空闲链被写坏、已定位已修已实机证实 / **残余风险 7 条**）+ 成品身份表 + 三件套表 + 怎么用 + 复跑与校验命令 + 7 条残余 + 磁盘与仓库现状 + 下一步建议 |
| `docs\RELEASE_NOTES_2400.md` | **更新**（新增 §7 归档信息） | 成品 sha256/md5/CRC/尺寸 · `tools\final_fix` 路径与内容 · 复现实测 · 清理释放量 · git 提交指向本报告 · 推送状态（未达成 + 原因摘要） |
| `docs\REPORT_ARCHIVE.md` | **新建**（本文件） | A–E 全部命令与结果、清理清单与释放量、提交/推送状态、未达成项与"需要什么" |

---

## F. 未达成项（如实，含原因与所需条件）

1. **推送云端：未达成。**
   原因：本分支历史含 **24 个 >100 MB 的 blob（合计 32.9 GB）**，GitHub 单文件上限 100 MB ⇒ 必被拒；
   为避免"白传 33 GB 仍失败"，**没有**发起这次上传。
   需要：**你确认走 §D.4 方案①（公开快照，~7 MB）或指定其它远端**；确认后一条命令即可完成。
2. **"从英文原盘一键复现"：未达成（链路被历史清理截断）。**
   原因：`rb_build.py` 需要 `work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf`（已删）+ 2 个**仓库外**的
   PCSX2 cdvd 转储。⇒ 现可靠起点 = `GR_REBUILD2400.iso`（sha256 `d7f83d7e…443ca0`，**已特意保留**）。
   需要：按 `tools\final_fix\README.md` §4 的解封配方从 K2 转储重建那个 ELF（sha256 必须为 `5cb59175…`）。
3. **主分支合并：未执行（按纪律只给建议）。** 建议 `git switch main && git merge round73/font-decompile`。
4. **与任务书字面清单的两处偏差（已说明理由）**：`GR_REBUILD2400.iso` 与 `LAY_fix1_bytecount.iso` 未删
   （前者是复现链基底，后者是不可重建的"未修对照盘"）。若确认不要，可再释放 3.14 GB。
5. **两处未纳入本次提交**：`work/builds` 的 270 个陈旧跟踪文件删除、`tools/**` 的 4 个历史改动 +
   `tools/text_csv/gate_pairs.json`（清单见 §C.4）。

---

## 附录 1：清理脚本（可重跑，dry-run 默认）

脚本本体：`%TEMP%\gr_cleanup.ps1`（本次执行用；逻辑如下，可直接照抄复现本次判定）

```powershell
# 1) 从 docs\** 与 work\builds\** 的全部 .md/.json 里抽取被引用的 work\builds 路径（4035 条）
#    正则: work[\\/]builds[\\/][A-Za-z0-9_\.\\/ \(\)\-]+   （并把 // 折叠成 /，去掉尾部标点）
# 2) 只在 20 个点名目录内挑删除对象:
#    扩展名 ∈ {.iso,.bin,.p2s,.png,.elf,.dmp,.npy,.zip,.7z,.pch,.dat} 或路径含 \__pycache__\
#    排除路径含 \bios\ 或 \emu\ 的文件
#    只删「相对路径不在引用集合里」的文件（精确匹配，不做目录级遮蔽）
# 3) 另外无条件删除被取代的变体盘 work\builds\GR_COMBFIX\COMBFIX_{A,B}.iso
# 4) 先打印「按目录 / 按扩展名」清单与合计，再执行删除；脚本 .py/.ps1/报告/JSON/CSV 一律不在删除集合里
```

完整待删清单曾导出为 `%TEMP%\gr_cleanup_manifest.csv`（13,155 行，含每个文件的相对路径与字节数；
该文件在系统临时目录，未入库）。

## 附录 2：本次用到的主要命令一览

```powershell
# A 清点
git status --short; git branch -vv; git remote -v; git log --oneline -5; git rev-parse --abbrev-ref HEAD
git check-ignore -v work/builds/GR_RELEASE/GR_ZH2400_FINAL.iso
# B 修复包实测
& $py tools\final_fix\apply_fix.py --verify-only --iso work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso --base work\builds\GR_REBUILD\GR_REBUILD2400.iso
& $py tools\final_fix\apply_fix.py --base work\builds\GR_REBUILD\GR_REBUILD2400.iso --out $env:TEMP\gr_repro\GR_ZH2400_FINAL.iso
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1
& $py work\builds\GR_REBUILD\tools\rb_build.py --out $env:TEMP\gr_repro\GR_REBUILD2400.iso   # ⇒ 卡在缺 K2_SLUS_206.13.elf
# B 清理
& "$env:TEMP\gr_cleanup.ps1"            # dry-run（打印清单）
& "$env:TEMP\gr_cleanup.ps1" -Execute   # 执行
# C 提交
git add -- tools/final_fix docs/...      # 明确列路径（见 §C.2）
git status --porcelain; git diff --cached --stat
git commit -F <message-file>
# D 远端
git fetch --all --prune; git ls-remote --heads public
git push public f0583003…:refs/heads/snapshot-2026-10-11   # 凭据探测（不上传对象）
```
