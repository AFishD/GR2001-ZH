# tools/ 脚本索引（`work\` → `tools\` 归位后）

> 本轮（2026-10-18）把 **`work\` 下全部 `.py`/`.ps1` 统一迁出**，按「来源区域 + 用途」落到 `tools\`。
> 迁移是**逐字节移动**（不改内容）；只有 187 + 177 个文件为了**还能跑**做了最小改动，逐条见 §5。
> 完整「原路径 → 新路径」机器可读对照表：**`tools/scripts_move_map.csv`**（1,287 行）。
> 复跑搬运/修复本身：`tools/maint/` 下三个脚本（见 §6）。

---

## 1. 目录结构与映射规则

| 新路径 | 来源 | 数量 | 说明 |
|---|---|---|---|
| `tools/rounds/<主题>/**` | `work\builds\<版本>\**` | 1,000 | 各轮构筑/验证脚本；**保留原相对子路径**（`tools/`、`temp/`、`temp/rNN/`、`audit/`、`verify/`） |
| `tools/re/toolbelt/*.py` | `work\tools\*.py`（扁平） | 264 | 逆向/取证通用工具带（`zx_*` `zero_*` `cave_*` `cap_*` `pc_*` `fa_*` `space_*` `thr_*` `root_*` `migrate_*` `verify_*` …） |
| `tools/re/ghidra_scripts/*` | `work\tools\ghidra_scripts\*` | 17 | 自研 Ghidra 脚本（16 `.java` + `decomp_crash.py`） |
| `tools/rounds/planc/*.py` | `work\_planc\*.py`（已删，从 git `fe4991d1` 恢复） | 34 | round 方案 C 图集重编码工具链 |
| `tools/snapshot/*` | `_archive_scratch\*.ps1|*.md|snap.index` | 7 | 公开孤儿快照机具（`make_snapshot*.ps1`、`prune_work.ps1`、`build_protect.ps1`、快照 README） |
| `tools/maint/*` | 本轮新增 | 3 | 搬运器 + 两个引用修复器（见 §6） |
| `tools/final_fix/**` | **未动** | 6 | 权威归档；`apply_fix.py` / `rebuild_base.py` / `repro*.ps1` / `fix_spec.json` / `README.md` |

**主题目录命名规则（机械、可预测）**：`work\builds\GR_XXX\...` → `tools\rounds\<xxx>\...`，
即**去掉 `GR_` 前缀后小写**（`GR_HASHR`→`hashr`、`GR_COMBFIX`→`combfix`、`GR_SPINFIX`→`spinfix`、
`GR_OOMFIX`→`oomfix`、`GR_REPRO`→`repro`、`GR_HEAP`→`heap`、`GR_USERDUMP`→`userdump`、
`GR_CULPRIT`→`culprit`、`GR_NULLHUNT`→`nullhunt`、`GR_MEMDRIFT`→`memdrift`、`GR_FPS`→`fps`、
`GR_FPSBISECT`→`fpsbisect`、`GR_ZH98`→`zh98` …）。

### 主题目录一览（36 个）

| 主题 | 脚本 | 主题 | 脚本 | 主题 | 脚本 |
|---|---:|---|---:|---|---:|
| `zh98` | 368 | `huge` | 20 | `culprit` | 9 |
| `zh94` | 85 | `nullhunt` | 16 | `hook` | 9 |
| `zh93` | 79 | `spinfix` | 16 | `layout` | 9 |
| `zh92` | 63 | `fps` | 15 | `ab` | 9 |
| `rebuild` | 35 | `combfix` | 14 | `release` | 8 |
| `planc` | 34 | `sent` | 14 | `fpsbisect` | 8 |
| `oomfix` | 29 | `cvar` | 13 | `txmig` | 7 |
| `zh97` | 20 | `dfix` | 13 | `csfix` | 6 |
| `zh99` | 10 | `cap2400` | 13 | `sync` | 6 |
| `heap` | 10 | `hashr` | 12 | `userdump` | 6 |
| `disasm` | 10 | `txt` | 12 | `repro` | 5 |
| `memdrift` | 11 | `zh104` | 5 | `hookemu` | 1 |

> `zh98/temp/` 里其实堆着 round 50–76 的脚本（`r50`…`r76`、`r51_lead`、`r52_lead`、`verify/`），
> 当年就落在该版本目录下，本轮**原样保留该结构**以便与历史报告对得上。

---

## 2. 明确**没有**迁移的东西（及其理由）

| 路径 | 文件数 | 为什么不迁 |
|---|---:|---|
| `work\builds\GR_HOOKEMU_QT2\**` | 12,501（含 27 脚本） | **用户明令禁动** —— 正在使用的取证工具链（`build_qt2.ps1`、`src\**`、`tools\*.ps1`、`deps\**`）。用户指示优先级高于「work 不留脚本」，故此处保留并在 `docs/REPORT_SCRIPTS_MOVE.md` 登记为例外。 |
| `work\tools\ghidra\**` | 5,266（含 140 `.py`） | **第三方 Ghidra 发行版本体**（`docs/` `GPL/` `licenses/` `server/` `support/` `ghidraRun` `bom.json`）。那 140 个 `.py` 是 Ghidra 自带的，不是本工程的脚本；搬进 `tools/` 会污染仓库与快照。 |
| `work\tools\jdk\` `appdata\` `ghidra_proj\` `ghidra_proj_ee\` `ghidra_out\` | 555 | 本地工具链与 **Ghidra 分析数据库（= 派生证据，离线不可重建）**；`.gitignore` 覆盖，不入库。 |
| `work\tools\*.log` `dl_urls*.txt` `*.txt` `gh.bat` | 18 | 非脚本；且**被已迁脚本继续引用**（如 `TOOLS = os.path.join(REPO,'work','tools')` → `ghidra_out\`），故留在原位。 |
| `work\builds\GR_RELEASE\GR_ZH126.iso` | 1 | 成品盘（见 `docs/REPORT_SCRIPTS_MOVE.md` §5 的事故与恢复）。 |

---

## 3. 怎么跑（环境注意）

```powershell
# 仓库根执行；Python 3.8
python tools\final_fix\apply_fix.py --verify-only --iso work\builds\GR_RELEASE\GR_ZH126.iso

# .ps1 在本机被执行策略拦（未签名）⇒ 必须显式 Bypass
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1
```

- `tools\final_fix\apply_fix.py --verify-only --base <基底> --iso <成品>` = **27 条断言**；
  只给 `--iso` 时是 20 条（第 ③ 段需要基底才能判）。
- 已迁脚本用 `REPO = <repo 根>` 定位兄弟模块；`sys.path` 引导已指向
  `tools\re\toolbelt` 与 `tools\text_csv`，**无需设置 PYTHONPATH**。

---

## 4. 可直接复跑性分级

| 级别 | 含义 | 代表 |
|---|---|---|
| **A 可直接复跑（输入齐备）** | 依赖的 ISO / JSON / 字符集都在 | `final_fix\apply_fix.py`、`final_fix\rebuild_base.py`、`re\toolbelt\iso_ls.py`、`re\toolbelt\zero_recon.py`、`rounds\combfix\tools\combfix_apply.py`、`iso_build\make_build.py`、`rounds\spinfix\tools\spinfix_apply.py`、`rounds\rebuild\tools\rb_allpat.py` |
| **B 需先造输入** | 依赖已退役的 `work\builds\<版本>\*.iso`；用 `repro_from_eng.ps1` + 对应 `rounds/<主题>/` 重建后再跑 | `rounds\hashr\tools\hashr_build.py`、`rounds\rebuild\tools\rb_verify_k2.py`、`rounds\zh98\temp\r67\r1_verify.py`、`rounds\planc\m6_survey.py` |
| **C 历史一次性** | 指向已不存在的一次性中间物（如 `work\_dis`、`work\tmp`、`work\builds\GR_ZH93_prev\...\FIXED.iso`） | `iso_build\patch_zh12px.py`、`iso_build\patch_font_huge.py`、`hanliu\tools\patch_db*.py`（**均为搬迁前就存在的既有断链，非本轮引入**） |

---

## 5. 引用更新清单（本轮实际改动）

`grep` 全仓 `work[\\/](tools|builds)[^\s"')]*\.(py|ps1|java)` 得 **613 行 docs + 21 行 tools** 命中。
处置如下。

### 5.1 已改（脚本要能跑，属「最小改动」）

| 规则 | 改动 | 文件数 / 处数 | 说明 |
|---|---|---:|---|
| **R1** | import 引导行（含 `sys.path` 或 `spec_from_file_location`）里的 `'work','tools'` → `'tools','re','toolbelt'` | 66 + 19 | 否则 `ModuleNotFoundError: zx_lib / tcslib / cave_dis / …` |
| **R1** | 同上行里的 `'work','builds','GR_X'` → `'tools','rounds','<theme>'` | 5 + 8 | 跨轮引用（`GR_SPINFIX`、`GR_NULLHUNT`、`GR_OOMFIX`、`GR_ZH98\temp\r74`） |
| **R2** | `'work','tools','NAME.py'` / `work/tools/NAME.py` / `r"work\tools\NAME.py"` → toolbelt | 10 + 95 + 1 | 含 `.py`/`.java` 的脚本引用（含文档字符串里的用法示例） |
| **R3** | `REPO = …os.path.join(HERE,'..','..')` → 再加一级 `'..'` | **177** | `work\tools\`（深度 2）→ `tools\re\toolbelt\`（深度 3）、`work\_planc\` → `tools\rounds\planc\` 后，仓库根少算一级；不改则 `REPO` 会解析成 `tools\` |

合计改动 **187 个文件 / 227 处**（R1+R2）+ **177 个文件 / 177 处**（R3）。
机具：`tools/maint/rewrite_moved_script_paths.py`、`tools/maint/fix_repo_depth_after_move.py`（均以 latin-1 往返读写，**非 ASCII 字节一字未变**）。
**未改**：68 个用硬编码绝对 `REPO` 的 toolbelt 脚本（本来就对）、所有 `work/builds/<版本>/<盘>.iso` 之类**数据路径**（改了反而错）。
深度未变的目录**一律未动**：`work\builds\<B>\`→`tools\rounds\<theme>\`（3→3）、`…\tools\`（4→4）、`…\temp\rNN\`（5→5）、`work\tools\ghidra_scripts\`→`tools\re\ghidra_scripts\`（3→3）。

### 5.2 未改、改为登记（历史报告里的「当时路径」）

`docs\**` 的 **613 行**脚本路径引用分布在 66 篇报告里（`CAPACITY_2400.md` 55、`TEXT_MIGRATION_0xBA.md` 28、
`REPORT_iso_space_ledger.md` 25 …）。这些是**当时执行记录**，硬改会篡改历史证据，故**一律不改**：

- 在 **`docs/CORRECTIONS.md`** 增列一条总说明（含换算规则）；
- 换算规则 = 本文件 §1 的机械规则，或直接查 `tools/scripts_move_map.csv`。

`tools\**` 里指向已迁脚本的 **21 行**全部位于**文档字符串/注释**（已逐条核实：`final_fix\apply_fix.py:3-6`、
`final_fix\fix_spec.json`、`final_fix\README.md:149`、`final_fix\rebuild_base.py:28`、`final_fix\repro.ps1:10`、
`diag\dump_all_text.py:129`、`diag\README.md:4`、`text_csv\tcslib.py`、`text_csv\gate_pairs.json`、
`iso_build\patch_zh113_expand_font.py:23,55`、`font_pipeline\data\charset_compiled_zh16.json`），
**不是运行期加载** ⇒ 不影响可跑性。`tools\final_fix\**` 属禁改归档，其出处注释保持原样并由 `docs/CORRECTIONS.md` 登记。

### 5.3 既有断链（**搬迁前就存在**，本轮未引入、未修复）

| 位置 | 指向 | 状态 |
|---|---|---|
| `tools\iso_build\patch_{font_huge,glyph_clean,zh12px,zh12px2}.py` | `work\_dis` | 目录早已不存在 |
| `tools\hanliu\tools\patch_db*.py`、`zh7_probe_res.py`、`research\report_gen.py` | `work\tmp\...` | 目录早已不存在 |
| `tools\re\toolbelt\r72_install_tools.py`、`pygh_decomp.py`、`root_decomp.py` | `work\tools\`（安装/输出落点） | **仍有效**：Ghidra/JDK/`ghidra_out` 确实还在 `work\tools\` |

---

## 6. 本轮新增的机具（可复跑）

| 脚本 | 作用 |
|---|---|
| `tools/maint/move_scripts_from_work.ps1` | 搬运器（幂等）。`-DryRun` 只报告。含从 git `fe4991d1` 恢复 `_planc` 34 个脚本；产出 `tools/scripts_move_map.csv` |
| `tools/maint/rewrite_moved_script_paths.py` | R1/R2 引用修复；`--apply` 才写 |
| `tools/maint/fix_repo_depth_after_move.py` | R3 仓库根深度修复；`--apply` 才写 |
| `tools/maint/clean_work_builds.ps1` | `work\builds` 退役清理（先打清单再删；**已修正**为「先删文件、再删空目录，且排除仍持有 KEEP 文件的祖先目录」） |

---

## 7. 抽验结果（新路径下实跑）

| # | 脚本 | 命令 | 结果 |
|---|---|---|---|
| 1 | `tools\final_fix\apply_fix.py` | `--verify-only --base work\builds\GR_REBUILD\GR_REBUILD2400.iso --iso work\builds\GR_RELEASE\GR_ZH126.iso` | ✅ **27/27 断言 OK，失败 0 条** |
| 1b | 同上 | `--verify-only --iso work\builds\GR_RELEASE\GR_ZH126.iso`（重建成品后复检） | ✅ 失败 0 条 |
| 2 | `tools\re\toolbelt\iso_ls.py` | `work\builds\GR_RELEASE\GR_ZH126.iso` | ✅ exit 0，正确列出根目录/MODULES（LBA 261 / SLUS_206.13 LBA 295） |
| 3 | `tools\re\toolbelt\zero_recon.py` | 无参 | ✅ 输出「单字节码位 103 / 对偶码位 2300 / lead 25 个」 |
| 4 | `tools\rounds\combfix\tools\combfix_apply.py` | `--help` | ✅ exit 0 |
| 5 | `tools\iso_build\make_build.py` | `--help` | ✅ exit 0 |
| 6 | `tools\rounds\spinfix\tools\spinfix_apply.py` | `--help` | ✅ exit 0 |
| 7 | `tools\rounds\rebuild\tools\rb_allpat.py` | `--help` | ✅ exit 0 |
| 8 | 共享库导入 | `zx_lib` `tcslib` `cave_dis` `cave_syms` `migrate_legacy` | ✅ 全部 OK |
| 9 | 全量语法 | 1,263 个 `.py` 逐个 `compile()` | ✅ **1,242 / 1,242 通过，0 失败** |

---

## 8. 事故与恢复（必读）

清理 `work\builds` 时，删除阶段对 `GR_RELEASE` 目录用了 `Remove-Item -Recurse`，**连带删除了本不在清单里的成品盘**
`work\builds\GR_RELEASE\GR_ZH126.iso`。已按强制规则用 `tools\final_fix\repro_from_eng.ps1` **从英文原盘重建**：

- 英文原盘 `2b42ea7c…8531`（核对通过）+ K2 转储 74,286,520 B `11f371f2…add9`
- ⇒ 基底 `d7f83d7e…43ca0`，**4.1 s**
- ⇒ 成品 **`d8007873…1b2ab5` == 交付成品，逐字节相同**，27 条断言全过
- 已回填 `work\builds\GR_RELEASE\GR_ZH126.iso` + `GR_ZH126.meta.json`；`--verify-only` 复检失败 0 条
- 清理脚本已修正，杜绝复发。详见 `docs/REPORT_SCRIPTS_MOVE.md` §5 与 `docs/CORRECTIONS.md`。
