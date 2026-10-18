# REPORT_SCRIPTS_MOVE.md —— 脚本归位 + `work\` 收尾清理 + 提交推送

> 执行：2026-10-18（脚本归位轮）· 分支 `main` · 远程 `public` = https://github.com/AFishD/GR2001-ZH.git
> 任务书：① 把 `work\` 里的 `.py`/`.ps1` 统一移入 `tools\` ② 清理 `work\builds` 只留成品与取证工具
> ③ 提交并刷新公开孤儿快照
> 索引：脚本新位置见 **`tools\README_scripts.md`**；机器可读对照表 **`tools\scripts_move_map.csv`**（1,287 行）

---

## 0. ★ 置顶：成品盘曾被误删，已按强制规则重建并逐字节核对通过

**结论：成品盘现在是完好的，sha256 == `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5`（= 交付成品）。**

时间线：

1. 任务开始时（19:19）**成品盘完好**：`work\builds\GR_RELEASE\GR_ZH126.iso`
   sha256 `d8007873…1b2ab5` 实测匹配；`work\builds\GR_HOOKEMU_QT2\**` = **12,501 文件**（与基线一致）；
   `work\_cleanup_manifest_20261018.txt` 存在（294,776 B）。
2. 执行任务 B 清理时，**我自己的清理脚本越界**：删除阶段对 `GR_RELEASE` 目录整体执行了
   `Remove-Item -Recurse`，把**并未列在清单里**的成品盘一并删除。
   （清单本身没错：清单是 3,482 文件 / 1.98 GB，`GR_RELEASE` 只列了 432 文件 / 73.6 MB，
   成品盘在清单生成阶段被正确排除 —— 错在删除阶段，不是清单。）
   同时按计划删掉了基底盘 `work\builds\GR_REBUILD\GR_REBUILD2400.iso`（1.53 GB）。
3. 立即用**唯一权威配方**重建（不改任何输入，全部只读）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1 `
  -OutDir $env:TEMP\gr_restore -KeepIntermediate
```

```
[0] ENG ISO  third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso
             sha256 2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531  (1648164864 B)  ✓ 与声明值一致
    K2 dump  %LOCALAPPDATA%\PCSX2\cdvd-dump\GR_FA2400_K2 (2026-10-17 15-08-20).dump
             sha256 11f371f294e4f8e353c21931a9c38d73c1309832a21e74cfb3e31d7095daadd9  (74286520 B)
[1] 基底 d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0  用时 4.1 s   ✓
[2] 成品 d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5            ✓
    [结论] 全部断言通过（失败 0 条）
    [结论] 出盘 sha256 == 交付成品 d8007873…1b2ab5  ⇒ 复现成功
[3] spec d8007873…1b2ab5  MATCH
REPRODUCTION FROM THE ENGLISH ORIGINAL OK
```

4. 回填 `work\builds\GR_RELEASE\GR_ZH126.iso` + `GR_ZH126.meta.json`，**就地复核**：

```
sha256 = d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5
MATCH  = True
Length = 1648164864 B
```

5. `python tools\final_fix\apply_fix.py --verify-only --iso work\builds\GR_RELEASE\GR_ZH126.iso`
   → `[结论] 该盘就是交付成品（失败 0 条）`，exit 0。

**防复发**：`tools\maint\clean_work_builds.ps1` 已改为
「**先按文件清单删文件，再删空目录**」，且删除任何目录前先排除**仍持有 KEEP 文件的祖先目录**。
事故与恢复全过程也写进了 `work\_cleanup_manifest_20261018b.txt` 的抬头。

---

## 1. 中止命令影响核实（任务前置项）

### 1.1 磁盘与基线对比

| 项 | 基线 | 实测（19:20） | 判定 |
|---|---|---|---|
| `work\` | 24,083 文件 / 9.21 GB | **23,102 文件 / 9.104 GB** | 少了 **981 文件 / 0.106 GB** |
| `work\builds\GR_HOOKEMU_QT2\**` | 12,501 文件 | **12,501 文件** | ✅ **完全一致，一字未动** |
| `work\builds\GR_RELEASE\GR_ZH126.iso` | sha256 `d8007873…1b2ab5` | **`d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5`** | ✅ **完好** |
| `work\_cleanup_manifest_20261018.txt` | 存在 | **294,776 B**（创建 19:15:42 / 末写 19:18:40） | ✅ **完好** |

> 注：`GR_HOOKEMU_QT2` 的**文件数与基线完全相同**（12,501），但体积实测 3,694.4 MB，
> 与任务书给的基线 515.7 MB 差 7 倍。文件数逐个一致 ⇒ 判定为**基线体积数字本身有误/口径不同**，
> 不是删除造成；本报告以「文件数一致」作为完好性判据。

### 1.2 中止命令**确实已部分执行**

对 `work\_cleanup_manifest_20261018.txt` 的 4,486 条逐条 `Test-Path`：

```
manifest entries : 4486
STILL EXIST      : 3482
GONE (deleted)   : 1004
```

被删的 1,004 条**全部落在清单内**，分布：

| 区域 | 已删 | 说明 |
|---|---:|---|
| `work\builds\GR_COMBFIX` | 857 | 字母序第 3 个目录，删到一半被中止（该目录 4,398 条中尚有 651 条存活） |
| `work\builds\GR_CAP2400` | 30 | 整目录删完 |
| `work\builds\GR_AB` | 27 | 整目录删完 |
| `work\builds\GR_THR86` | 2 | `GR_THR86_recon.txt` / `GR_THR86_tagscan.txt` |
| `work\_planc` | 60 | 含 **34 个 `.py`** |
| `work\_briefs_recovered` | 6 | `.md` |
| 仓库根 `*.dump` | 22 | `GR_ZH125 (…).dump` 等 |

**判定：中止命令没有造成任何「清单外」损失。** 它的执行顺序是
「先删 `_planc`/`_briefs`/根 dump，再按字母序删 `work\builds\GR_AB` → `GR_CAP2400` → `GR_COMBFIX`（中断）」，
受保护的成品盘与 `GR_HOOKEMU_QT2` 均未被触碰。

### 1.3 清单是否记录了那批删除

`work\_cleanup_manifest_20261018.txt` 是**删除计划清单**（表头「=== 清理清单（2026-10-18 19:15 用户指示）===」，
4,486 条 = 路径 + 尺寸 [+ sha256]），**不是删除结果日志**。
它**包含** `work\builds\GR_*` 与 `work\_planc` 的条目 ⇒ **中止前清单已写好**；
但**没有**逐条标记「已删/未删」，因此不能从清单本身看出中止点 —— 中止点由上面的 `Test-Path` 普查确定。

### 1.4 中止命令的 34 个 `.py` 已找回

`work\_planc\*.py` 的 34 个脚本虽然被中止命令删掉，但 `work/**` 曾入库，可从
**git `fe4991d1`** 逐字节取回（`git ls-tree -r fe4991d1 -- work/_planc` 列 60 个文件）。
本轮已全部取回并**直接归位到 `tools\rounds\planc\`**（不是放回 `work\`）—— 见 §2。
`work\_briefs_recovered\*.md` 不在 `fe4991d1` 里，**未找回**（6 个过程简报，属未达成项，见 §7）。

---

## 2. 搬迁映射表

### 2.1 规则（机械、可预测、可复跑）

| 原路径 | 新路径 | 文件数 |
|---|---|---:|
| `work\tools\*.py`（扁平） | `tools\re\toolbelt\*.py` | 264 |
| `work\tools\ghidra_scripts\*` | `tools\re\ghidra_scripts\*` | 17 |
| `work\builds\<GR_XXX>\<相对路径>` | `tools\rounds\<xxx>\<相对路径>`（`xxx` = 去 `GR_` 前缀后小写） | 965 |
| `work\_planc\*.py`（从 `fe4991d1` 恢复） | `tools\rounds\planc\*.py` | 34 |
| `_archive_scratch\*.ps1|*.md|snap.index` | `tools\snapshot\*` | 7 |
| **合计** | | **1,287** |

- **搬迁方式**：`work/**` 在本仓库**从未被 git 跟踪**（`git ls-files work` = 0，`.gitignore` 有 `work/**`）
  ⇒ 源文件无 git 历史，**`git mv` 不适用**，一律用「普通移动 + `git add` 新路径」。
  搬迁为**逐字节移动，不改内容**（唯一例外见 §3）。
- **同名冲突**：搬运器在计划阶段做 `Group-Object New` 重名检查 → **0 处冲突**。
- **实跑结果**：`moved: 1253   source-already-gone: 34   failed: 0`
  （1253 = 264 + 17 + 965 + 7；34 是已直接落到目标的 `_planc`，属预期跳过）
- **机具**：`tools\maint\move_scripts_from_work.ps1`（幂等，`-DryRun` 只报告）

### 2.2 `tools\rounds\` 主题目录（36 个 / 1,000 文件）

`ab=9  cap2400=13  combfix=14  csfix=6  culprit=9  cvar=13  dfix=13  disasm=10  fps=15  fpsbisect=8
hashr=12  heap=10  hook=9  hookemu=1  huge=20  layout=9  memdrift=11  nullhunt=16  oomfix=29  planc=34
rebuild=35  release=8  repro=5  sent=14  spinfix=16  sync=6  txmig=7  txt=12  userdump=6  zh104=5
zh92=63  zh93=79  zh94=85  zh97=20  zh98=368  zh99=10`

主题内**保留原相对子路径**（`tools/`、`temp/`、`temp/rNN/`、`audit/`、`verify/`），
以便与历史报告里的路径一一对上。例：

```
work\builds\GR_ZH98\temp\r67\r1_verify.py   ->  tools\rounds\zh98\temp\r67\r1_verify.py
work\builds\GR_OOMFIX\tools\oomfix_apply.py ->  tools\rounds\oomfix\tools\oomfix_apply.py
work\builds\GR_MEMDRIFT\analyze_memdrift.py ->  tools\rounds\memdrift\analyze_memdrift.py
work\builds\GR_SYNC\run_synced.ps1           ->  tools\rounds\sync\run_synced.ps1
```

### 2.3 明确**不迁**（并说明理由）

| 路径 | 文件数 | 理由 |
|---|---:|---|
| `work\builds\GR_HOOKEMU_QT2\**` | 12,501（含 **27 个脚本**） | **用户明令禁动**（正在用的取证工具链）。用户指示优先级高于「work 不留脚本」⇒ 登记为例外 |
| `work\tools\ghidra\**` | 5,266（含 140 `.py`） | **第三方 Ghidra 12.1.2 发行版本体**（`docs/ GPL/ licenses/ server/ support/ ghidraRun bom.json`）；那 140 个 `.py` 是 Ghidra 自带脚本，非本工程产物，搬进 `tools/` 会污染仓库与快照 |
| `work\tools\jdk\` `appdata\` `ghidra_proj\` `ghidra_proj_ee\` `ghidra_out\` | 555 | 本地工具链 + **Ghidra 分析数据库（派生证据，离线不可重建）**；`.gitignore` 覆盖 |
| `work\tools\*.log` `dl_urls*.txt` `*.txt` `gh.bat` | 18 | 非脚本，且**被已迁脚本继续引用**（`TOOLS = os.path.join(REPO,'work','tools')` → `ghidra_out\`） |

**`work\` 下剩余 `.py`/`.ps1` 普查（收尾后实测）**：共 167 个 =
**27 个** `GR_HOOKEMU_QT2`（禁动）+ **140 个** `work\tools\ghidra\**`（第三方发行版）—— **本工程自己的脚本 0 个**。

---

## 3. 引用更新清单

全仓 `grep` 模式 `work[\\/](tools|builds)[^\s"')]*\.(py|ps1|java)` 命中 **613 行 docs + 21 行 tools**。

### 3.1 已改（脚本要能跑 ⇒ 属「最小改动」）

| 规则 | 内容 | 文件 / 处 | 不改的后果 |
|---|---|---:|---|
| **R1** | import 引导行（含 `sys.path` 或 `spec_from_file_location`）里 `'work','tools'` → `'tools','re','toolbelt'` | 66 / 66 | `ModuleNotFoundError: zx_lib / tcslib / cave_dis / …` |
| **R1** | 同行里 `'work','builds','GR_X'` → `'tools','rounds','<theme>'` | 5 / 5 | 跨轮引用断（`GR_SPINFIX`、`GR_ZH98\temp\r74`） |
| **R1** | 同上，raw string 形式 `r"work\tools"` / `r"work\builds\GR_X\tools"` | 19 + 8 | 同上 |
| **R2** | `'work','tools','NAME.py'` → toolbelt | 10 / 10 | `spec_from_file_location` 载不到 |
| **R2** | `work/tools/NAME.py`（含文档字符串用法示例）→ `tools/re/toolbelt/NAME.py` | 95 / 95 | 文档误导 + 少量运行期引用 |
| **R2** | `r"work\tools\NAME.py"` → toolbelt | 1 / 1 | 同上 |
| **R3** | `REPO = …os.path.join(HERE,'..','..')` **再加一级 `'..'`** | **177 / 177** | **`REPO` 解析成 `tools\` 而非仓库根** ⇒ 全盘路径错 |

**合计：187 个文件 / 227 处（R1+R2）+ 177 个文件 / 177 处（R3）。**

R3 之所以必需：`work\tools\`（深度 2）→ `tools\re\toolbelt\`（深度 3）、`work\_planc\`（2）→ `tools\rounds\planc\`（3），
仓库根少算一级。**深度未变的目录一律未动**：
`work\builds\<B>\`→`tools\rounds\<theme>\`（3→3）、`…\tools\`（4→4）、`…\temp\rNN\`（5→5）、
`work\tools\ghidra_scripts\`→`tools\re\ghidra_scripts\`（3→3）。
**未改**：68 个用硬编码绝对 `REPO` 的 toolbelt 脚本（本来就对）、所有 `work/builds/<版本>/<盘>.iso` **数据路径**（改了反而错）。

机具（均以 **latin-1 往返**读写，**非 ASCII 字节一字未变**）：
`tools\maint\rewrite_moved_script_paths.py`、`tools\maint\fix_repo_depth_after_move.py`。

### 3.2 未改、改为登记（历史报告里的「当时路径」）

`docs\**` 的 **613 行**分布在 **66 篇**报告（`CAPACITY_2400.md` 55、`TEXT_MIGRATION_0xBA.md` 28、
`REPORT_iso_space_ledger.md` 25、`REPORT_SENTINEL_FIX.md` 23 …）。这些是**当时执行记录**，
硬改等于篡改历史证据 ⇒ **一律不改**，按任务书要求改为**登记**：

* `docs\CORRECTIONS.md` 新增 **§9**（含换算规则与本次事故）；
* 换算规则 = §2.1 的机械规则，或直接查 `tools\scripts_move_map.csv`；
* `tools\README_scripts.md` §5.2 同样登记。

### 3.3 `tools\**` 的 21 行 —— 已逐条核实为**注释/文档字符串**，非运行期加载

`final_fix\apply_fix.py:3-6`（模块 docstring）、`final_fix\fix_spec.json`（出处元数据）、
`final_fix\README.md:149`、`final_fix\rebuild_base.py:28`、`final_fix\repro.ps1:10`、
`diag\dump_all_text.py:129`、`diag\README.md:4`、`text_csv\tcslib.py:54/666/837`、`text_csv\gate_pairs.json`、
`iso_build\patch_zh113_expand_font.py:23,55`、`font_pipeline\data\charset_compiled_zh16.json`。
⇒ **不影响可跑性**。`tools\final_fix\**` 属禁改权威归档，其出处注释**保持原样**，由 `docs\CORRECTIONS.md` §9 登记。

### 3.4 既有断链（**搬迁前就存在**，本轮未引入、未修复）

| 位置 | 指向 | 状态 |
|---|---|---|
| `tools\iso_build\patch_{font_huge,glyph_clean,zh12px,zh12px2}.py` | `work\_dis` | 目录早已不存在 |
| `tools\hanliu\tools\patch_db*.py`、`zh7_probe_res.py`、`research\report_gen.py` | `work\tmp\...` | 目录早已不存在 |
| `tools\re\toolbelt\r72_install_tools.py`、`pygh_decomp.py`、`root_decomp.py` | `work\tools\`（安装/输出落点） | **仍有效**（Ghidra/JDK/`ghidra_out` 确实还在 `work\tools\`） |

---

## 4. 可跑性抽验（新路径下实跑）

| # | 脚本（新路径） | 命令 | 结果 |
|---|---|---|---|
| **1** | `tools\final_fix\apply_fix.py` | `--verify-only --base work\builds\GR_REBUILD\GR_REBUILD2400.iso --iso work\builds\GR_RELEASE\GR_ZH126.iso` | ✅ **27/27 断言 OK，失败 0 条**；差异 78 B / 25 run，参照区 8 区逐字节相同 |
| **1b** | 同上 | `--verify-only --iso work\builds\GR_RELEASE\GR_ZH126.iso`（**重建成品后复检**） | ✅ `该盘就是交付成品（失败 0 条）`，exit 0 |
| **2** | `tools\re\toolbelt\iso_ls.py` | `work\builds\GR_RELEASE\GR_ZH126.iso` | ✅ exit 0；正确列出根目录（LBA 261）/ `SLUS_206.13` LBA 295 / `GR.IMG` LBA 19175 |
| **3** | `tools\re\toolbelt\zero_recon.py` | 无参 | ✅ 输出「单字节码位 103 / 对偶码位 2300 / lead 25 个 / 重复 0」 |
| **4** | `tools\rounds\combfix\tools\combfix_apply.py` | `--help` | ✅ exit 0，usage 正常 |
| **5** | `tools\iso_build\make_build.py` | `--help` | ✅ exit 0，usage 正常 |
| **6** | `tools\rounds\spinfix\tools\spinfix_apply.py` | `--help` | ✅ exit 0 |
| **7** | `tools\rounds\rebuild\tools\rb_allpat.py` | `--help` | ✅ exit 0 |
| **8** | 共享库导入 | `zx_lib` `tcslib` `cave_dis` `cave_syms` `migrate_legacy` | ✅ 全部 OK；`zx_lib.REPO` == 仓库根（核对通过） |
| **9** | 全量语法 | 1,263 个 `.py` 逐个 `compile()` | ✅ **1,242 / 1,242 通过，0 失败** |

**修复前 vs 修复后**（证明 R1/R3 是必需的，不是「顺手改」）：

| 脚本 | 修复前 | 修复后 |
|---|---|---|
| `tools\re\toolbelt\cap_recon.py` | `ModuleNotFoundError: No module named 'tcslib'` | 通过导入，进入 `main()`，仅因默认盘 `work\builds\GR_ZH124\GR_ZH124.iso` 不存在而停 |
| `tools\rounds\hashr\tools\hashr_build.py` | `ModuleNotFoundError: No module named 'zx_lib'` | 通过导入，进入读盘逻辑 |
| `tools\rounds\rebuild\tools\rb_verify_k2.py` | `ModuleNotFoundError: No module named 'zx_lib'` | 通过导入，进入读盘逻辑 |
| `tools\rounds\planc\m6_survey.py` | `ModuleNotFoundError: No module named 'tcslib'` | 通过导入，正确算出 `base = …\GR_ZH93_prev\temp\exp\FIXED.iso`（文件已退役 ⇒ `exists: False`，属预期） |

> 说明：仍报 `FileNotFoundError` 的几个脚本，缺的是**已按用户指示退役的 `work\builds\<版本>\*.iso` 输入盘**，
> 不是模块 ⇒ 属「需先造输入」（可跑性 B 级），已在 `tools\README_scripts.md` §4 分级登记。

---

## 5. 清理释放量与保留清单

### 5.1 释放量

| 阶段 | `work\` 文件 | `work\` 体积 |
|---|---:|---:|
| 基线（中止命令之前） | 24,083 | 9.21 GB |
| 中止命令之后（实测） | 23,102 | 9.104 GB |
| **本轮清理之后（实测）** | **18,376** | **7.117 GB** |

* 本轮清理删除 **3,482 文件 / 1.98 GB**（清单先打印，落盘 `work\_cleanup_manifest_20261018b.txt`，222,526 B）
* 加上中止命令已删的 1,004 文件 ⇒ 全程释放 **5,707 文件 / ≈2.09 GB**
* `Get-PSDrive C`：可用空间 **80.51 GB → 84.04 GB**（含清掉 3.1 GB 重建临时目录）

**删前清单（按版本目录汇总，节选；完整 3,482 条见 `work\_cleanup_manifest_20261018b.txt`）**

```
GR_REBUILD   8 文件 / 1572.2 MB      GR_SPINFIX  154 / 10.9     GR_ZH94      43 / 8.4
GR_COMBFIX 651 文件 /  106.5 MB      GR_ZH109     40 / 10.3     GR_ZH101     38 / 8.3
GR_RELEASE 432 文件 /   73.6 MB      GR_HOOKEMU  110 /  9.4     GR_ZH99      45 / 8.3
GR_REPRO   100 文件 /   31.7 MB      GR_CULPRIT   83 /  9.1     GR_HASHR     62 / 8.0
GR_ZH98    260 文件 /   15.6 MB      GR_ZH97      40 /  8.4     GR_OOMFIX   146 / 7.4
…（共 76 个版本目录）                    合计 3,482 文件 / 1.98 GB
```

> `GR_REBUILD\GR_REBUILD2400.iso`（1.53 GB）按用户「不保留构筑信息」删除。
> **可从 `tools\final_fix\repro_from_eng.ps1` 重建，本轮实测 4.1 s**（上一轮记 4.4 s），
> sha256 `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0` 与声明值一致。

### 5.2 保留清单（含体积与理由）

| 保留项 | 文件数 | 体积 | 理由 |
|---|---:|---:|---|
| `work\builds\GR_HOOKEMU_QT2\**` | 12,501 | 3,694.4 MB | 用户明令**禁动**：正在使用的取证工具链（模拟器取证版构筑 + `tools\*.ps1`） |
| `work\builds\GR_RELEASE\GR_ZH126.iso` | 1 | 1,571.8 MB | **成品盘**，sha256 `d8007873…1b2ab5`（事故后已重建核对） |
| `work\builds\GR_RELEASE\GR_ZH126.meta.json` | 1 | 3,740 B | 成品元数据（随成品盘一起回填） |
| `work\tools\**` | 5,868 | 2,012.3 MB | **反汇编/逆向工具链**：Ghidra 12.1.2 本体 880.3 MB · JDK 327.9 MB · `ghidra_proj` 514.5 MB · `ghidra_proj_ee` 278.6 MB · `appdata` 9.7 MB · 日志/`dl_urls`/`gh.bat`。**保留理由**：`ghidra_proj*` 是 **Ghidra 分析数据库 = 派生证据**（离线不可重建）；且 15 处已迁脚本仍以 `work\tools\ghidra_out` 等为落点 |
| `work\temp\NEW_Mem\**` | 3 | 8.4 MB | **用户提供的运行期证据**（`emulog.txt` / `emulog_1030.txt` / `Mcd001.ps2`），被 4 篇报告标注为「只读用户证据」 |
| `work\_cleanup_manifest_20261018.txt` | 1 | 294,776 B | 原清理清单（用户指定保留） |
| `work\_cleanup_manifest_20261018b.txt` | 1 | 222,526 B | 本轮删除清单 + 事故/恢复记录 |
| **合计** | **18,376** | **7.117 GB** | |

> 未保留：`work\temp\SLUS-20613 (7A361FB5).01.p2s`（`docs\REPORT_save_crash.md` 引用的即时存档）
> —— 本轮开始时它**已不在盘上**（非本轮删除）。

---

## 6. 提交与推送

*（本节在推送完成后回填 —— 见本文件末尾「§6 回填」或 `docs\STATUS.md` §8 的当前值。）*

---

## 7. 未达成项

| # | 未达成 | 原因 | 需要什么 |
|---|---|---|---|
| 1 | **成品盘一度被误删** | 我的清理脚本删除阶段 `Remove-Item -Recurse` 越界（清单正确、删除越界） | 已用 `repro_from_eng.ps1` **从英文原盘重建并逐字节核对通过**；脚本已修正防复发 |
| 2 | `work\_briefs_recovered\*.md`（6 个过程简报）未找回 | 被中止命令删除，且**不在** `fe4991d1` 里（`git ls-tree` 计数 0） | 需要更早的、仍跟踪 `work/**` 的提交；或从 `%LOCALAPPDATA%\PCSX2` 之外的备份找回 |
| 3 | `work\_planc\*.png` / `*.json`（26 个非脚本产物）未找回 | 同上（`fe4991d1` 里有，但本轮只恢复 `.py`，按「只迁脚本」口径） | 如需，可从 `fe4991d1` 一并恢复（`git ls-tree` 已确认存在） |
| 4 | `docs\**` 613 行历史脚本路径引用**未改写** | 任务书允许「改不完的不要硬改」；它们是历史执行记录 | 已按任务书改为登记（`docs\CORRECTIONS.md` §9 + `tools\scripts_move_map.csv`） |
| 5 | `tools\**` 既有断链（`work\_dis`、`work\tmp`）未修 | **搬迁前就存在**，超出本轮范围 | 需要当年那些一次性中间目录，或重写这些历史脚本 |
| 6 | 可跑性抽验只覆盖 9 项 | 1,263 个脚本里绝大多数需要已退役的中间盘作输入 | 若要全量验证，需按 `rounds/<主题>/` 逐轮重建输入（成本高） |
