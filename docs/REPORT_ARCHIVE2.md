# REPORT_ARCHIVE2.md —— 2026-10-18「推精简快照 + main 带修复 + `work/` 与仓库精简」执行报告（A–F 全记录）

> 上一轮（只做归档与清理、未推送）见 `docs\REPORT_ARCHIVE.md`。
> 本文件记录**第二轮**：造孤儿精简快照 → 推送云端（main 带上修复）→ 精简 `work\` → 精简仓库当前树 → 文档更新。
> 全部结论均给出**命令与原始输出**；未达成的写「未达成 + 原因 + 需要什么」。

---

## 0. 摘要

| 任务 | 结果 | 关键 id / 数字 |
|---|---|---|
| **A** 造精简孤儿快照 | ✅ 完成 | 提交 **`2c899a418593a31ebacd11f2b8b734ee61311052`**；**66 文件 / 1,979,767 B（1.89 MB）**；树 `5c06f648` |
| **B** 推送云端 | ✅ **达成** | 首次：`main` `f0583003` → **`2c899a41`**（`+ f0583003...2c899a41 (forced update)`，`--force-with-lease`）；随后 `main` 与 `snapshot-2026-10-18` **一同快进**（`2c899a41..59e43d45`）到文档同步提交 ⇒ 两分支恒同指；备份 `snapshot-2026-10-11` = `f0583003` **未动** |
| **C** 精简 `work/` | ✅ 完成 | **20.04 GB / 66,074 文件 → 9.21 GB / 24,083 文件**；**释放 10.83 GB**；删除 41,991 个文件 / 1,948 个空目录 |
| **D** 精简仓库当前树 | ✅ 完成 | 提交 **`a48c4241`**：`git rm -r --cached work` 移除 **4,771 条 / 11,364,158 行**；当前树 **432 文件**；`git gc --prune=now` 3.1 min：**17 包 → 1 包，size-pack 21.45 → 21.60 GiB（历史 blob 未回收）** |
| **E** 文档更新 | ✅ 完成 | 本文件 + `docs\STATUS.md`（新增「归档与云端」）+ `docs\RELEASE_NOTES_2400.md`（§7 归档信息改写） |
| **F** 最终自检 | ✅ 完成 | 见 §F；成品 sha256 复核仍 = `d8007873…1b2ab5` |

一句话：**修复已进云端 `main`，旧公开状态有独立分支兜底，`work/` 减半而全部证据（docs 精确引用的）与成品/基底/Qt 钩子版一条未丢。**

---

## A. 造精简孤儿快照

### A.1 做法（为什么不用 `git switch --orphan`）

`git switch --orphan` 会**清空工作区里所有受版本控制的文件**；本仓库工作区还有 4,771 个入库的 `work/` 文件、
270 条「已删除」状态和 20 GB 未跟踪产物，直接切分支风险高。因此改用**临时索引 + 底层管道**造孤儿提交：

```powershell
# _archive_scratch\make_snapshot.ps1（ASCII-only；PS 5.1 按 ANSI 读 .ps1）
$env:GIT_INDEX_FILE = '_archive_scratch\snap.index'   # 只动这个临时索引
git read-tree --empty
git add -f -- <59 个 docs 文件> <4 个 tools\final_fix 文件>
git update-index --add --cacheinfo 100644,<blob>,README.md      # 快照专用 README（不覆盖 dev 分支的 README）
git update-index --add --cacheinfo 100644,<blob>,.gitignore
git update-index --add --cacheinfo 100644,<blob>,.gitattributes
$tree   = git write-tree          # 5c06f648ead8c9d78356e76864e302f9519f8e15
$commit = git commit-tree $tree -F _archive_scratch\snapshot_msg.txt   # 无 -p ⇒ 孤儿
git branch -f snapshot $commit
```

**当前分支、当前索引、工作区文件全程未被改动**（提交后 `git status` 条目数与操作前一致）。

### A.2 快照内容（`git ls-tree -r -l 5c06f648`）

| 顶层 | 文件数 | 体积 |
|---|---|---|
| `docs/` | 59 | 1,873.3 KB |
| `tools/`（只有 `final_fix/`） | 4 | 48.6 KB |
| `README.md`（快照专用公开版） | 1 | 9.7 KB |
| `.gitignore` | 1 | 1.7 KB |
| `.gitattributes` | 1 | 0.1 KB |
| **合计** | **66** | **1,979,767 B ≈ 1.89 MB** |

* **目标 ≤ 10 MB ⇒ 达成**（1.89 MB），且**全部为文本**：无 ISO、无 `.bin`、无 PNG、无模拟器二进制。
* `.gitignore` 沿用白名单策略（`*.iso` / `work/**` / `third_party/**` 一律不入库），`.gitattributes` 原样（禁止行尾转换）。

### A.3 `docs/` 取舍（逐个判断，共 59 篇）

* **48 篇 = 本次汉化/修复产生的文档**（提交 `01ab3530` 的 `docs` 部分，含 `STATUS.md` 现状索引）。
  用户口径的「47 篇」与本轮实际入库的 48 篇差 1：`01ab3530` 里 `docs/**` 就是 **48 个文件**
  （`git show --name-only 01ab3530 | grep '^docs/' | wc`），此处**以 git 事实为准**并如实说明。
* **11 篇 = 被上述 48 篇以相对路径直接引用的既有文档**，为让归档内链接不悬空而一并纳入：
  `PROGRESS.md`、`BUILD_TOOLCHAIN.md`、`BUILD_VERSIONS.md`、`PLACEHOLDER_AND_SYMBOLS.md`、
  `REPORT_build_font_dump.md`、`REPORT_csv_text_tool.md`、`REPORT_font_content_logic_split.md`、
  `REPORT_probe_lead_limit.md`、`REPORT_zh_heap_corruption.md`、`REPORT_zh90_order_label.md`、
  `han_v2/BOOT_SCREENS.md`。
  （判定方法：正则抽取 48 篇里所有 `docs/...` 引用，取「存在于盘上但不在 48 篇内」的集合。）
* **明确未纳入**：其余 83 篇旧文档、`docs/img/**`（r46 图集对比图 0.56 MB，未被 48 篇引用）、
  `tools/**`（除 `final_fix`）、`third_party/**`、`work/**`。
  **上一轮公开过的 267 个文件（完整工具链 + `han_v2/` 逆向方法论手册 + 早期报告）未删除、未改写，
  仍在分支 `snapshot-2026-10-11`（`f0583003`）**——这是「取舍」而不是「丢失」。
* **未纳入但被引用（会 404）**：`docs/REPORT_HOOKEMU_QT2_REBUILD.md` 被 48 篇之一引用，
  但该文件**从未入库**（`git log --all -- docs/REPORT_HOOKEMU_QT2_REBUILD.md` 无输出；工作区未跟踪），
  故不纳入快照。**如实登记为已知断链**。

### A.4 提交前自检

```
refs: files=719 dirs=225                 # 保护清单（见 §C.1）
docs: 59 (fix 48 + cited 11)  tools: 4
tree: 5c06f648ead8c9d78356e76864e302f9519f8e15
tree files: 66   tree bytes: 1979767 (1.89 MB)
（无 .iso / 无大二进制：全部扩展名为 .md/.py/.json/.ps1/.gitignore/.gitattributes）
敏感信息扫描：ghp_ / github_pat_ / password= / api_key= / Bearer / AKIA / PRIVATE KEY / 邮箱  ⇒ 全部 clean
```

### A.5 提交信息（subject 与正文要点）

```
快照: 2,400 字中文成品 + 卡死修复（F4/OOMFIX/F7）与验收归档 2026-10-18
```
正文含：成品身份四件套（尺寸/sha256/md5/CRC/ELF）、基底链、三件套逐站点表、验收结论、
本快照内容与体积、**docs 取舍说明**、7 条残余风险、以及「从英文原盘重建基底的链路当前不可复跑」的说明。

---

## B. 推送云端（**达成**）

### B.1 先确认备份（动 main 之前）

```
$ git ls-remote --heads public
f0583003ab15e69955c70d2c02b1b66495f7ee07        refs/heads/main
f0583003ab15e69955c70d2c02b1b66495f7ee07        refs/heads/snapshot-2026-10-11
```

⇒ **旧的公开状态已由 `snapshot-2026-10-11` 独立保存**（与 `main` 同指 `f0583003`），
因此不需要另建 `pre-fix-snapshot` 分支（任务书 B.1 的条件不成立）。

### B.2 两条 push 的原始输出

```powershell
$ git push public snapshot:refs/heads/snapshot-2026-10-18
remote: Create a pull request for 'snapshot-2026-10-18' on GitHub by visiting:
remote:      https://github.com/AFishD/GR2001-ZH/pull/new/snapshot-2026-10-18
To https://github.com/AFishD/GR2001-ZH.git
 * [new branch]        snapshot -> snapshot-2026-10-18
exit=0

$ git push public snapshot:refs/heads/main '--force-with-lease=refs/heads/main:f0583003ab15e69955c70d2c02b1b66495f7ee07'
To https://github.com/AFishD/GR2001-ZH.git
 + f0583003...2c899a41 snapshot -> main (forced update)
exit=0
```

* 第二条**只用了 `--force-with-lease` 且显式钉住旧值**（`refs/heads/main:f0583003…`）——
  若远端 `main` 在我读取之后被任何人改动过，这条推送会**被拒而不是覆盖**。
  全程**没有裸 `--force`、没有 `--delete`、没有改本地历史**。
* 非快进是唯一途径：快照是与 `f0583003` **无共同祖先**的孤儿提交。

### B.3 推送后复核（`git fetch --all` 之后）

```
$ git fetch --all            # exit=0
$ git ls-remote --heads public
2c899a418593a31ebacd11f2b8b734ee61311052        refs/heads/main
f0583003ab15e69955c70d2c02b1b66495f7ee07        refs/heads/snapshot-2026-10-11
2c899a418593a31ebacd11f2b8b734ee61311052        refs/heads/snapshot-2026-10-18

$ git log --oneline -1 public/main
2c899a41 快照: 2,400 字中文成品 + 卡死修复（F4/OOMFIX/F7）与验收归档 2026-10-18

$ git ls-tree -r --name-only public/main | Measure-Object
Count : 66

$ git ls-tree --name-only public/main
.gitattributes
.gitignore
README.md
docs
tools

$ git log --oneline -1 public/snapshot-2026-10-11
f0583003 GR2001-ZH 公开快照 2026-10-11 — 现役盘 GR_ZH92 (文本表按 kind 拆分 + {WRAP} 人工断点控制)
```

**结论**：云端三个分支状态明确 —— `main` = 新快照（带修复），`snapshot-2026-10-18` = 同一提交，
`snapshot-2026-10-11` = 旧公开状态（未动）。**推送未达成项：无。**

### B.4 后续两次「文档同步」推送（都是**快进**，无需 force）

首次推送之后，为了让**公开快照里内嵌的归档文档**与事实一致（STATUS/RELEASE_NOTES/本文件都写在快照里），
又在快照链上追加了文档提交并 `main`、`snapshot-2026-10-18` **一同快进**：

```
$ git push public snapshot:refs/heads/snapshot-2026-10-18     # 2c899a41..59e43d45  (fast-forward)
$ git push public snapshot:refs/heads/main                    # 2c899a41..59e43d45  (fast-forward)
```

* **修复内容始终在 `2c899a41`**（`main` 的历史里保留着这个「修复落点的孤儿精简快照」），
  后续提交**只改文档**，不改 `tools/final_fix/**`、不改成品身份、不改任何补丁字节。
* `main` 与 `snapshot-2026-10-18` 因此**始终指向同一个提交**；本节所述的这几次同步之后，
  二者的当前值请以 `git ls-remote --heads public` 为准（**本文件内嵌在快照里，无法自指自己所在的提交哈希**，
  这是「记录推送结果的文档本身也在被推送」时的固有限制，如实说明）。

---

## C. 精简 `work/`

### C.1 保留清单（先 grep 生成保护清单，再删）

保护清单由 `_archive_scratch\build_protect.ps1` 生成：扫描 `docs/**/*.md|*.json` +
`tools/final_fix/**` + 根 `README.md`，抽出全部 `work\...` 路径引用（**1,755 个 token**），
解析后得到 **719 个精确文件引用 + 225 个被引用目录**。

保留规则（`_archive_scratch\prune_work.ps1`，默认 dry-run）：

| # | 保留对象 | 实测 |
|---|---|---|
| 1 | 成品 `GR_RELEASE\GR_ZH2400_FINAL.iso` + `GR_ZH2400_FINAL.meta.json` | 1,571.8 MB |
| 2 | 基底 `GR_REBUILD\GR_REBUILD2400.iso` + `build_info_rebuild.json`（`repro.ps1` 的起点） | 1,571.8 MB |
| 3 | **`work\builds\GR_HOOKEMU_QT2\**`（用户明令禁动） | 3,694.4 MB / 12,501 文件 |
| 4 | **被 docs 精确引用的证据文件**（719 个精确引用，去掉被点名的 ISO） | 123.5 MB / 697 文件 |
| 5 | 被引用目录内的**小证据**（≤1 MB 的 json/csv/txt/md/log/tsv/ini/patch/diff/xml，且路径不含 `\temp\ \extract\ \dump_* \out\ \build\ \deps\ \src\` 等「可重建段」） | 241.7 MB / 2,232 文件 |
| 6 | 被引用目录内 `\runs\ \shots\ \evidence\ \audit\` 的**取证截图** PNG ≤1 MB | 205.1 MB / 1,734 文件 |
| 7 | 全部自研脚本 `.py/.ps1/.java/.sh/.bat`（第三方源码树除外） | 2.9 MB / 929 文件 |
| 8 | 轮次笔记小 md（≤1 MB，第三方树除外） | 3.1 MB / 224 文件 |
| 9 | `work\tools\**` 逆向工具链（Ghidra/JDK/Ghidra 工程库/自研脚本） | 2,011 MB / 5,774 文件 |
| 10 | `work\_planc\**` + `work\_briefs_recovered\**`（小证据目录） | 3.5 MB / 18 文件 |

**明确的删除规则**：其余一切（构筑盘、`temp/`、`extract/`、`dump_*`、轮次中间盘、模拟器构建产物、
未被引用的 p2s/PNG/bin/npy、被取代的实验盘、`work\tools\dl\*.zip` 可重下安装包）。

### C.2 删除清单（**执行前打印**，脚本输出原文，按顶层目录 / 大件）

```
DELETE: 41991 files / 10.87 GB

Dir                                               MB Files
work\builds\GR_COMBFIX                        3528.2  1026
work\builds\GR_LAYOUT                         1576.1     5
work\builds\GR_HOOKEMU                         971.5 11162
work\tools\dl                                  741.8     2
work\builds\GR_THR86                           394.3  4667
work\builds\GR_ZH98                            331.7  2686
work\builds\GR_F364                            277.1  1506
work\builds\GR_ZH105                           233.9  1001
work\builds\GR_TEST_FONT1                      229.7   997
work\builds\GR_SPINFIX                         224.4   339
work\builds\GR_ZH116                           213.2  5145
work\builds\GR_ZH107                           171.3   702
work\builds\GR_CAP2400                         170.8  1122
work\builds\GR_OOMFIX                          170.6   241
work\builds\GR_ZH108                           169.4   697
work\builds\GR_FA2400_K2                       157.7   721
work\builds\GR_ZH106                           149.7   664
work\builds\GR_REPRO                           126.2   310
work\builds\GR_FA2400                          124.2   974
work\builds\GR_CULPRIT                          95.6   192
work\temp\skill_fetch                           92.2   136
...（其余 60+ 个目录合计 < 90 MB/个，完整逐文件清单见 §附录 1）

DELETE items > 50 MB:
  1,571.8 MB  work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso
  1,571.8 MB  work\builds\GR_COMBFIX\COMBFIX_C.iso
  1,571.8 MB  work\builds\GR_COMBFIX\COMBFIX_2400.iso
    546.3 MB  work\tools\dl\ghidra_12.1.2.zip
    195.6 MB  work\tools\dl\jdk21.zip
```

### C.3 执行结果

```
deleted files: freed 10.83 GB, failures 3
  （3 个失败 = work\temp\skill_fetch\...\.git\objects\pack\*.{idx,pack,rev}，Windows 只读属性 ⇒
    随后清除 ReadOnly 并删除，skill_fetch 整目录已消失）
removed empty dirs: 1948
AFTER: work = 9.25 GB / 24116 files        # 再清掉 skill_fetch 残留 ⇒ 最终 9.21 GB / 24,083 文件
```

| 指标 | 精简前 | 精简后 |
|---|---|---|
| `work\` 总大小 | **20.04 GB** | **9.21 GB** |
| `work\` 文件数 | 66,074 | 24,083 |
| 释放 | — | **10.83 GB**（54%） |
| C: 剩余空间 | 51.05 GB | **62.73 GB**（+11.68 GB） |

精简后 `work\` 顶层只剩 5 项：

```
  7,400.68 MB  DIR  builds     （= 成品 1.53 GB + 基底 1.53 GB + GR_HOOKEMU_QT2 3.69 GB + 各被引用证据）
  2,013.78 MB  DIR  tools      （Ghidra 12.1.2 / JDK / Ghidra 工程库 / 自研脚本；dl 安装包已删）
      8.37 MB  DIR  temp
      4.99 MB  DIR  _planc
      0.55 MB  DIR  _briefs_recovered
```

保留验证（逐条 `Test-Path`，全部 OK）：成品 ISO、成品 meta、基底 ISO、`GR_HOOKEMU_QT2\qt\pcsx2-qt.exe`、
`GR_HOOKEMU_QT2\runs\REBUILD\qt_manifest_sha256.txt`、`tools\final_fix\apply_fix.py`、
`GR_RELEASE\runs\smoke_GR_ZH2400_FINAL\win_f00005970_eeram.bin`、`GR_COMBFIX\states\S1b_low0_C.p2s`、
`work\tools\ghidra_scripts\FontDecomp.java`；三张点名删除的盘确认 `gone`。

### C.4 删除盘 sha256 存证（**删除前**计算，文本留档）

```
a69a9ca44049eaed4085239a2b8d10af58888f54f62a51e40c1ece22dd2d2808  (md5 aeddc22a75577529190a569e829f1030)
  work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso          # 「同现场回归」的未修对照盘

d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5  (md5 d24c324eb955a8c8dbaf92f6c766da2c)
  work\builds\GR_COMBFIX\COMBFIX_2400.iso               # = 交付成品【逐字节相同】⇒ 删除零信息损失

5c4c9f70ee3d15dc406354c599dfe2bb1b80a0d16c4a1c2b73b2d036f4b31f4d  (md5 e5f652573da2d8b79c1b94cdcfcfbf46)
  work\builds\GR_COMBFIX\COMBFIX_C.iso                  # 用户实机验证过的那张（F4 线）
```

（完整文件：`_archive_scratch\deleted_iso_hashes.txt`。）

### C.5 ⚠ 如实登记：与既有文档记载的**冲突**

`tools\final_fix\README.md` §4 与 `docs\STATUS.md` §6（上一轮写）都写着
「**特意保留** `GR_LAYOUT\LAY_fix1_bytecount.iso`（未修对照盘，其基底已删、不可重建）」。

本轮任务书 C.2 **点名把该盘列入删除**，并说明「除主分支所需以外都删」⇒ **已按任务书删除**，
sha256 已存证（§C.4）。影响与代价：

* 「同现场回归（未修盘 70,266 Trap 直接死 vs 本盘 Trap 0）」这条验收**今后无法再原样复跑**
  （对照盘不可重建）；结论本身与其运行日志/截图**仍在**（`docs\REPORT_COMBFIX.md`、
  `GR_COMBFIX\runs\**` 中被引用的取证文件、以及 `fix_spec.json · acceptance_index`）。
* 我**没有**修改 `tools\final_fix\**`（任务书明令禁动），因此该 README §4 的那句「特意保留」
  在本次之后**已过时**；本文件与 `docs\STATUS.md` §6 已按事实改写。**若需要恢复该盘，只能从仓库外备份找回。**

### C.6 明确未动

`work\builds\GR_HOOKEMU_QT2\**`（12,501 文件 / 3.69 GB，一条未删）、成品 ISO、`tools\final_fix\**`（4 文件）、
`docs\**`、被 docs 引用的证据（§C.1 的 4/5/6 类）、全部自研脚本。
取证用的两个崩溃即时存档 `GR_COMBFIX\states\S1b_{bin121_low0,low0_C}.p2s`（各 14.25 MB）
与 32 MB `win_f00005970_eeram.bin` 都**保留**（被 docs 精确引用）。

---

## D. 精简整个仓库（当前树）

### D.1 `git rm -r --cached work`（在 `round73/font-decompile` 上，不在 snapshot 分支）

```
$ git ls-files work | Measure-Object
Count : 4771
$ git rm -r --cached --quiet work        # exit=0（--cached ⇒ 磁盘文件一个没动）
$ git diff --cached --shortstat
 4771 files changed, 11364158 deletions(-)
$ git ls-files work | Measure-Object
Count : 0
$ Test-Path work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso   ⇒ OK on disk（成品仍在盘上）
```

提交（**只**包含这批删除，未 `git add -A`）：

```
a48c4241  删除: 清理误入库的 work/ 测试产物（ISO/转储/中间盘）
2cd167f4  docs: STATUS 补记归档提交 01ab3530/8a2554ca 与推送未达成状态
$ git ls-files | Measure-Object   ⇒ 432   # 当前分支树不再含 4,771 个 work 文件与 3 张 1.5 GB ISO
```

### D.2 `git count-objects -vH` 与 `git gc --prune=now`

```
===== gc 之前 =====
count: 4167                    # 松散对象
size: 1.24 GiB
in-pack: 37170
packs: 17
size-pack: 21.45 GiB
prune-packable: 0
garbage: 0

$ git gc --prune=now           # exit=0，耗时 3.1 min

===== gc 之后 =====
count: 0
size: 0 bytes
in-pack: 23176
packs: 1
size-pack: 21.60 GiB
prune-packable: 0
garbage: 0
.git 目录实测占用：21.61 GiB
```

| 指标 | gc 前 | gc 后 | 说明 |
|---|---|---|---|
| pack 数 | 17 | **1** | 17 个包合并成 1 个 |
| in-pack 对象 | 37,170 | **23,176** | −13,994：**不可达/悬空对象**被 `--prune=now` 清掉 |
| 松散对象 | 4,167（1.24 GiB） | **0** | 全部收进 pack |
| **size-pack** | **21.45 GiB** | **21.60 GiB** | **+0.15 GiB —— 基本没变** |
| `.git` 实测占用 | ≈22.7 GiB | **21.61 GiB** | 略降（松散对象被压缩、重复包被合并） |

**怎么读这个结果**：本轮从**当前树**里移除了 4,771 个 `work/` 文件（含 3 张 1.5 GB ISO），
但 `git gc` 之后 pack **不降反微增**——因为那些大 blob **仍然可以从历史提交到达**
（`round73/font-decompile` 之前的所有提交、`main`、`archive/*` 等分支都在引用它们），
`gc` 的职责只是「打包 + 清理不可达对象」，**不会、也不该**回收历史里可达的对象。
这就是「只精简当前树」与「真正回收」之间的分界线（见下）。

### D.3 **如实说明：这只精简了「当前树」，历史里的 blob 仍在 pack 中**

* 被删掉的 4,771 个 `work/` 文件、3 张 1.5 GB ISO、24 个 >100 MB 的 blob **依然可从历史提交到达**
  （它们存在于 `round73/font-decompile` 之前的各代提交、以及 `main`/`archive/*` 等分支的历史里），
  `git gc` 只能把它们**继续打包**，不会回收。
* **真正回收**必须**重写历史**（`git filter-repo` / BFG）：
  ```powershell
  # 【未执行 · 高风险 · 会改掉所有 commit hash · 需强推所有分支】
  git clone --mirror . ..\GR_backup.git                     # 先做全量镜像备份
  pip install git-filter-repo
  git filter-repo --path work --invert-paths --force        # 删除所有历史里的 work/
  # 或 BFG: java -jar bfg.jar --delete-folders work --no-blob-protection .
  git push public --force --all ; git push public --force --tags
  ```
  代价与风险：**每个 commit hash 都会变**（所有分支指针/引用/子模块失效）、必须 `--force` 强推
  **所有**分支（含 `snapshot-2026-10-11` 这份「旧公开状态的保全」）、任何他人克隆都必须重新克隆；
  一旦出错且无镜像备份则不可恢复。
* **本轮不需要它**：云端要求（≤100 MB/blob、孤儿精简快照）已由 §A/§B 达成；本地仓库 21.45 GiB
  的 pack 只是**占磁盘**，不影响任何功能。**故仅作为建议登记，未执行**（任务书 D.3 亦要求只建议）。

---

## E. 文档与状态更新（本轮）

| 文件 | 改动 |
|---|---|
| `docs\REPORT_ARCHIVE2.md` | **新增**（本文件）：A–F 全命令与结果、推送原文、精简清单与释放量、未达成/需确认项 |
| `docs\STATUS.md` | 新增 **§6b「归档与云端」**（快照分支名、main 新 hash、推送结果、仓库体积、`work\` 保留清单、下一步）；§6 磁盘/仓库现状与 §7 下一步按事实改写 |
| `docs\RELEASE_NOTES_2400.md` | §7「归档信息」改写：云端位置与分支名（`main` = `snapshot-2026-10-18` = `2c899a41`）、推送**已达成**、`work/` 精简新数字、被删盘 sha256 索引 |

---

## F. 最终自检（原文见本文件末尾 §F 与对话回报）

见 `docs\STATUS.md` §6b 与下节「最终自检」；关键项：`git log --oneline -6`、`git branch -vv`、
`git status --short | Measure-Object`、`git count-objects -vH`、远端分支列表、
成品 sha256 复核 = `d8007873…1b2ab5`。

---

## 附录 1：脚本与清单文件（都在仓库根 `_archive_scratch\`，未入库）

| 文件 | 作用 |
|---|---|
| `build_protect.ps1` | 从 docs/README 抽取 `work\...` 引用 → `protect_files.txt` / `protect_dirs.txt`（719 + 225 条） |
| `prune_work.ps1` | 精简规划 + 执行（默认 dry-run；`-Execute` 才删）；逐文件写 manifest |
| `work_prune_manifest_20261018.csv` | **删除清单**（41,991 行：Path/Size/Reason） |
| `work_keep_manifest_20261018.csv` | **保留清单**（24,113 行：Path/Size/Reason） |
| `deleted_iso_hashes.txt` | 三张被删盘的 sha256/md5/尺寸存证 |
| `make_snapshot.ps1` | 用临时索引造孤儿快照树/提交（不碰当前分支与索引） |
| `snapshot_msg.txt` / `snapshot_README.md` | 快照提交信息 / 快照公开版 README 源文本 |

> `_archive_scratch\` 是**未跟踪**的临时目录（其中的 `.md`/`.ps1`/`.csv` 因 `.gitignore` 白名单会显示为
> `??`）；如需清理可直接删掉整个目录，仓库历史不受影响。

## 附录 2：未达成 / 需确认项

1. **`docs/REPORT_HOOKEMU_QT2_REBUILD.md` 断链**（在公开快照里会 404）：该文件从未入库，
   如需补链请先确认其内容可公开并入库，再刷新快照分支。
2. **`tools\final_fix\README.md` §4「特意保留 LAY_fix1 对照盘」已过时**（该盘本轮按任务书删除）。
   因任务书禁动 `tools\final_fix\**`，未修改；如需修正请授权改这一行。
3. **`work\tools\**`（2.01 GB：Ghidra 12.1.2 + JDK + Ghidra 工程库）本轮保留**：它是继续逆向的
   环境，不属于任务书点名的「构筑盘/实验产物」；若确认不再做反编译，可再释放约 2.0 GB
   （`work\tools\dl\*.zip` 0.72 GB 已删）。
4. **历史 blob 未回收**（§D.3）：需 `git filter-repo`/BFG 重写历史，**未执行**（高风险，需单独授权 + 全量备份）。
5. **本地 dev 分支 `round73/font-decompile` 尚未并入本地 `main`**（`fe4991d1`）：本轮按任务书只把
   **云端 main** 带上修复；本地 `main` 与 dev 分支的关系仍待决定（见 `docs\STATUS.md` §7）。
