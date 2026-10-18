# docs/ 索引 —— 一篇一行（收尾整理版 2026-10-18）

> **怎么读这份索引**：`状态` 四档 = **权威**（结论/规则/验收，冲突时以此为准）· 
> **历史**（过程记录，结论未被推翻）· **已过时**（结论被部分取代或路线被否证，文首有订正横幅）· 
> **已归档**（移到 `docs/_obsolete/`，被推翻路线或一次性过程产物）。
> `引用` = 仓库内（docs + `tools/final_fix/`）有多少个文件提到本文件名 —— 0 表示"孤篇"。
> 错误断言的逐条订正见 **`docs/CORRECTIONS.md`**；工程当前状态见 **`docs/STATUS.md`**。
> 子目录：`docs/han_v2/`（汉化 v2 过程数据 123 文件）· `docs/img/`（5 张取证图）· `docs/_obsolete/`（21 篇归档）。

| 文件 | 状态 | 一句话内容 | 引用 |
|---|---|---|---|
| `BUILD_MANIFEST.md` | 已过时 | 2026-09-18 ISO 重建校对与清理记录（早期构筑指示表） | 2 |
| `BUILD_TOOLCHAIN.md` | 权威 | 构筑工具链与 ISO 配方（IMG 条目字段、注入路径） | 15 |
| `BUILD_VERSIONS.md` | 权威 | 历代盘谱系与版本号规则（含 2400 线 → GR_ZH126） | 7 |
| `CAPACITY_2400.md` | 权威 | 2400 线几何/容量落地：h=644 / 64 列 / GATE 0xBA ⇒ 2350 对偶槽 | 13 |
| `CAPACITY_2400_FA2400.md` | 权威 | FA2400 收尾出盘：几何 / 字形 / charset / 全量验收 | 2 |
| `CONTAINER_INVENTORY_r83.md` | 历史 | R83 像素容器区域清单 + h=512 容量账 | 2 |
| `CORRECTIONS.md` | 权威 | ★ 历史错误断言订正表（7 条 + 附录），冲突时以此为准 | 27 |
| `DFIX_REPORT.md` | 已过时 | pkt 候选修复盘四张 + 冒烟（路线已被实机否证，见 CORRECTIONS §7） | 4 |
| `FONTRES_STRUCTURE_r83.md` | 历史 | FONT.RES 权威结构（反汇编实证：三段式容器 + 记录字段） | 5 |
| `FONT_CURRENT_STATE.md` | 权威 | 现役字库权威状态（盘内实测） | 12 |
| `FONT_PIPELINE.md` | 历史 | font_pipeline 现役字库链说明（ZH62 实证） | 3 |
| `HOOKED_EMU_GUIDE.md` | 历史 | HookWatch 版 PCSX2 使用手册（写监视 + 取证） | 2 |
| `HOOKEMU_QT2_GUIDE.md` | 权威 | 用户手册：QT2 取证版模拟器怎么用 | 7 |
| `PATCH_INVENTORY.md` | 权威 | 44 处 ELF 字节补丁全量清单（逐字节核实） | 9 |
| `PLACEHOLDER_AND_SYMBOLS.md` | 权威 | 占位符/控制标记/图标/像符号的真字，一页说清 | 5 |
| `PROGRESS.md` | 权威 | 90+ 轮编年进度（最大的一篇；查历史细节用） | 13 |
| `REBUILD_PLAN.md` | 权威 | 从幸存工具链重建 2400 盘的计划（英文原盘 ⊕ K2 转储） | 4 |
| `REBUILD_REPORT.md` | 权威 | 重建执行记录 + 与真 K2 盘的逐帧/逐项对照 | 2 |
| `RELEASE_NOTES_2400.md` | 权威 | 交付说明（给用户）：这一张盘是什么、修了什么、怎么用 | 6 |
| `REPORT_ARCHIVE.md` | 历史 | 2026-10-18 收尾归档执行报告（A–E 全记录）——历史记录，盘名按当时 | 4 |
| `REPORT_ARCHIVE2.md` | 历史 | 2026-10-18 推精简快照 + main 带修复 + work/ 精简执行报告（A–F） | 3 |
| `REPORT_COMBFIX.md` | 权威 | 卡死修复组合盘：失效模式判定 + 四张盘 + 验证（F4+OOMFIX+F7 的取证来源） | 9 |
| `REPORT_CULPRIT_STORE.md` | 权威 | 肇事 store、指针来源、调用者与归因判定 | 5 |
| `REPORT_DISASM_ROOTCAUSE.md` | 权威 | 反汇编根因报告：游玩卡死 / 2fps —— 21 处站点逐条判定 | 6 |
| `REPORT_EMU_SETTINGS_SYNC.md` | 权威 | 模拟器设置与用户官方 PCSX2 全面同步 | 1 |
| `REPORT_FPS_BISECT.md` | 历史 | 钩子二分：每帧开销不在钩子、全在数据侧 | 2 |
| `REPORT_FPS_ZH113b.md` | 历史 | 游玩中回退到 ~2fps 的实机排查 | 2 |
| `REPORT_HEAP_EXHAUSTION.md` | 权威 | 堆耗尽的两层分离离线取证（最早分叉点） | 6 |
| `REPORT_HOOKED_EMU.md` | 历史 | HookWatch 版 PCSX2 的实现与取证能力报告 | 1 |
| `REPORT_HOOKEMU_QT2.md` | 历史 | QT2 取证版模拟器的实现报告（用户手册见 HOOKEMU_QT2_GUIDE） | 3 |
| `REPORT_HOOKEMU_QT2_REBUILD.md` | 权威 | QT2 便携取证构筑「误删事故」的重建与验证 | 5 |
| `REPORT_HOOK_BISECT.md` | 已过时 | 钩子二分打靶 + CVAR_04 同源性判定（否证 huge 面成因的关键取证） | 5 |
| `REPORT_LAYOUT_AUDIT.md` | 权威 | B 线布局/步进一致性审计；U1「×94 一个字都没丢」的判定出处 | 3 |
| `REPORT_MEMDRIFT_ZH113b.md` | 已过时 | 随时间累积损坏的专项取证（A 线） | 2 |
| `REPORT_NULLDEREF_ZH113b.md` | 历史 | GR_ZH113b 硬卡死根因审计 + 历史断言否证表（CORRECTIONS §1/§2/§6 的依据） | 6 |
| `REPORT_OOMFIX.md` | 权威 | 解压器 NULL 检查修复（OOMFIX）出盘 + 确定性复现 | 8 |
| `REPORT_RELEASE_VERIFY.md` | 权威 | 成品盘全量验收：身份 / 字库 / 文本 / 实机 6000 帧 / 同现场回归 | 8 |
| `REPORT_SAVESTATE_REPRO.md` | 权威 | 用户即时存档的本地复现（LAY 线） | 3 |
| `REPORT_SENTINEL_FIX.md` | 权威 | 哨兵 trail 重排：修复版 2400 成品盘 + 基底容量证明 | 9 |
| `REPORT_SPINFIX.md` | 权威 | 分配器自旋的复现与四处修复（F1F2 已被否证，见 CORRECTIONS §7） | 5 |
| `REPORT_TEXT_OVERFLOW.md` | 历史 | 文本层⇒卡死机理取证（中文只有英文 48.6%、TXT_03 等长对照）—— CORRECTIONS §3 的依据 | 5 |
| `REPORT_USERDUMP_ANALYSIS.md` | 权威 | 用户真机双 dump 现场分析（坏桶 126 是谁写坏的） | 5 |
| `REPORT_atlas_artifact.md` | 历史 | 这是 dump 工具的读法问题，不是盘上的数据坏了，也不是原版数据 —— 那些像素根本不是像素。** | 6 |
| `REPORT_brief2.md` | 历史 | 性质**: gsrunner 双盘 (ZH61 / EN 原盘) 同 fast-nav 实拍 + drawlog/组件钩子逐帧对照 + 静态反汇编。 | 2 |
| `REPORT_btn_placeholder.md` | 历史 | 结论：8/8 项验收全部通过**，往返**零字节差异**，老 CSV **不受影响**。 | 1 |
| `REPORT_build_font_dump.md` | 历史 | 版本文件夹内「文本 + 字库」快照的产出（构筑产物目录收敛） | 5 |
| `REPORT_build_text_integration.md` | 历史 | 日期 2026-10-10 · 目录 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization` · | 3 |
| `REPORT_cave_count_vs_bytes.md` | 历史 | 1. **H1 的字面形式（cave 里"按字符数申请缓冲、按字节数写"）在本轮被穷举检查后【不成立】。** | 3 |
| `REPORT_charset_guard.md` | 已过时 | 只检查**注入器确实会写**的条目 —— 与主循环的过滤条件完全一致： | 2 |
| `REPORT_csv_text_tool.md` | 历史 | 日期 2026-10-09 · 分支 `round29/csv-text-tool` · 现役基底 `work/builds/GR_ZH89/GR_ZH89 | 8 |
| `REPORT_dump_all_containers.md` | 历史 | 工具：`tools/text_csv/dump_containers.py`（新增，只读 ISO） | 3 |
| `REPORT_dump_font_capacity.md` | 历史 | 1. **`dump_font.py` 的 `cell_x/cell_y` 原来几乎全是错的**（用的旧口径 `x = 4+16*col`， | 4 |
| `REPORT_edge_fix_zh109.md` | 历史 | ![修复前后对照](../work/builds/GR_ZH109/fig_edge_fix.png) | 1 |
| `REPORT_elf_reencode_fix.md` | 历史 | 工具：`tools/iso_build/font_compact.py`（`r56.1` → **`r57.0`**； | 2 |
| `REPORT_en_column.md` | 历史 | 结论：8/8 项验收全部通过。** 列位置正确、对齐 2250/2261（99.51%）、往返**零字节差异**、 | 2 |
| `REPORT_expand_font_329.md` | 已过时 | 字形管线可用**(§2); 329 个新汉字已写进现役盘**原本就空着**的 329 个引擎格 | 4 |
| `REPORT_final_364.md` | 已过时 | ★ 交付盘 work\builds\GR_F364\GR_F364.iso  = 基底 GR_ZH124.iso + **只加高图集 h 512→640** | 4 |
| `REPORT_font_capacity_decompile.md` | 已过时 | 「1504」不是引擎上限，是汉化自己写的常量。** 整条 DBCS 判定 / 字符解码 / 字形寻址 / | 5 |
| `REPORT_font_capacity_route.md` | 已过时 | 「贴图加高」这条路的瓶颈不是 r73 报告担心的 `+0x30` 记账（那条已被本报告读透，是误报）， | 2 |
| `REPORT_font_cleanup.md` | 历史 | 碎片清了 14940 个黑点（图集墨从 104748 降到 89808），顺手把 144 个"再也用不到的旧字" | 1 |
| `REPORT_font_content_logic_split.md` | 已过时 | `RSFontMgr::ReadResourceFile(const char*)`（入口 `0x00219380`，1284 B，2 个调用者： | 4 |
| `REPORT_font_ext_fix.md` | 历史 | 跑不进主菜单的元凶不是文本注入、也不是 FONT.RES（FT 记录表），而是旧补丁写进「字库图集」的那 | 3 |
| `REPORT_font_ext_zh93.md` | 历史 | 任务书给的算式是「合法对偶空间 1222 − 已用 1144 = 78 空位 ≥ 76」。实测发现这个算式**漏了一项**： | 3 |
| `REPORT_font_usage_tool.md` | 历史 | 字库能腾出来的格位，比看上去少得多 —— 但本来就够用。** | 2 |
| `REPORT_glyph_align.md` | 历史 | 那些字以前在游戏里显示的是「同一排里另一个字」（比如"毫米"会显示成"命切"）； | 4 |
| `REPORT_glyph_truncation_anchor.md` | 历史 | 新增 `tools/iso_build/glyph_geometry.py` + CLI `tools/iso_build/scan_glyph_geome | 1 |
| `REPORT_icon_codes.md` | 历史 | 对象盘**：实验基盘 `work/builds/GR_ZH93/GR_ZH93.iso`（`e037f629…8d19be`，**只读**）； | 3 |
| `REPORT_iso_space_ledger.md` | 权威 | ISO 空位盘点与最大容量（round78） | 3 |
| `REPORT_names_and_12px.md` | 历史 | 角色档案（`.ATR`）的 `<ActorName>` 全部换成「**理想标准译名 + 名·姓 分界点**」： | 3 |
| `REPORT_navopt.md` | 历史 | 日期: 2026-09-24。目标: gsrunner 开机到主菜单 ≤ 1 分钟。 | 2 |
| `REPORT_pc_structure.md` | 历史 | 1. **PC 装的是官方简体中文版**（`Ike.log`：`Ghost Recon (RELEASE) version = 1.4.0.0`，安装路径  | 2 |
| `REPORT_plan_c_zh93.md` | 历史 | 历史先例（提交 `eebe52ef`，`patch_zh220_planc.py`）把 gate 从 `0xAE` 抬到 **`0xB4`** | 4 |
| `REPORT_probe_lead_limit.md` | 历史 | 分支 `main`（未切分支、未 commit）；执行日期见本目录 mtime；执行者 = 探针子代理。 | 4 |
| `REPORT_r71_scene_reduce.md` | 历史 | 底本 = `work/builds/GR_ZH109/text_backup_before_wrapfix/GR_ZH109_text_long.csv`  | 1 |
| `REPORT_r83_ft_record_route.md` | 历史 | ① 新盘 `work/builds/GR_ZH123/GR_ZH123.iso` 实机跑通**：6000 帧裸跑 **191 张截图** | 2 |
| `REPORT_r84.md` | 权威 | r84 执行记录（△ 修复 + W=2048 单变量 + 上限裁定） | 1 |
| `REPORT_record_band_fix.md` | 历史 | Lead 的定位大方向对（**就是"差一行"**：清带少清了 `yrow-1` 这一行），但两处需要订正： | 1 |
| `REPORT_reencode_coverage.md` | 历史 | 用户问"单独打补丁改那 8 条会不会每次重排都失效"—— 会。所以本轮把覆盖面补进了工具本身**： | 1 |
| `REPORT_release_pack.md` | 历史 | round43：ç/ñ 修正 + 首份「资料包」 | 4 |
| `REPORT_release_zh97.md` | 历史 | python tools\iso_build\patch_zh96_record_band.py ^ | 2 |
| `REPORT_relocate_zh104.md` | 历史 | `tools/iso_build/font_cell_map.py` 把 1504 个对偶槽位逐个分类（GR_ZH103 实测）： | 2 |
| `REPORT_save_crash.md` | 历史 | 用户从这个即时存档进去、走「战后回顾 → 继续 → 要保存吗?(是) → 选档案 → 选择文件」这条路, | 2 |
| `REPORT_sf_titles_dump.md` | 历史 | 分支: `round62/sf-titles-dump` | 1 |
| `REPORT_sf_titles_inject.md` | 历史 | 分支: `round63/sf-titles-inject`(Lead 已切好; **本轮不 commit**) | 1 |
| `REPORT_single_cell_verify.md` | 历史 | python tools/iso_build/single_cell_font.py --iso work/builds/GR_ZH98/GR_ZH98.i | 6 |
| `REPORT_split_by_kind.md` | 历史 | 原来是一张 `GR_ZH92_text.csv`：**2261 行**里混着三类完全不同的东西 —— | 3 |
| `REPORT_text_reduce.md` | 历史 | 受限字表文案改写（round64） | 4 |
| `REPORT_titles_r71.md` | 历史 | 在 **`GR_ZH114`**（= `GR_ZH111` + round68 的 36 条标题改动）之上，**只改 11 个标题**： | 1 |
| `REPORT_titles_rework.md` | 历史 | 特别收录 145 个标题按用户原文重做（round68） | 1 |
| `REPORT_workspace_cleanup.md` | 已过时 | 工作区清理记录 + 当时状态索引（2026-10-12） | 3 |
| `REPORT_wrap_and_title.md` | 历史 | 日期 2026-10-05 · 盘：`work/builds/GR_ZH84/GR_ZH84.iso`（现役） · 基准：`GR_EN_ORIG` | 5 |
| `REPORT_wrap_br_fix.md` | 历史 | 工具链的契约是「**CSV 里的换行 ↔ 盘上的换行**」： | 3 |
| `REPORT_wrap_control.md` | 历史 | round36 / 分支 `round34/wrap-control` / 2026-10-10** | 2 |
| `REPORT_zh82s_sf_title.md` | 历史 | 日期 2026-10-08 · 分支 `round27/sf-inner-title` · 产物 `tools/iso_build/patch_zh_sf_ | 1 |
| `REPORT_zh82t_title_center.md` | 历史 | 标题走 `RSTextComponent::DrawTheString`, 其 jal 被 **GR_ZH61** 挂钩到 tail-cave `0x565 | 3 |
| `REPORT_zh82w_text_space.md` | 历史 | 日期 2026-10-08 · 分支 `round27/sf-text-space` · 盘 `work/builds/GR_ZH82_W/GR_ZH82_ | 2 |
| `REPORT_zh89_spaces.md` | 历史 | 日期 2026-10-09 · 分支 `round28/zh87-space-cleanup` · 产物 `work/builds/GR_ZH89/GR_Z | 1 |
| `REPORT_zh90_order_label.md` | 历史 | 分支：`round29/fix-command-label` | 4 |
| `REPORT_zh_heap_corruption.md` | 历史 | 用"TLB Miss 行数"这个零成本指标，用户的两次会话给出了 50 : 0 的硬分离：** | 5 |
| `RISK_BUDGET_r84.md` | 权威 | R84 风险预算（gap 3→0 ⇒ 364 字全落盘） | 3 |
| `SCRIPT_VERSION_MAP.md` | 权威 | 脚本版本关系图（2026-09-26） | 3 |
| `STATUS.md` | 权威 | ★ 工程当前状态（现役盘 / 规则 / 云端 / 文档索引指针）—— 先读这篇 | 30 |
| `TEXT_MIGRATION_0xBA.md` | 权威 | 旧单字节码全量迁移 + 回写工具链同步（GATE 0xB1 → 0xBA） | 4 |
| `TOOLS.md` | 权威 | tools/ 现役工具链说明 | 1 |
| `iso_layout.json` | 权威 | 三个镜像成员（LBA / 字节数）的机读布局表 | 1 |

### `docs/_obsolete/` —— 已归档（被推翻路线 / 一次性过程产物，共 21 篇）

| 文件 | 状态 | 一句话内容 | 引用 |
|---|---|---|---|
| `AB_TEST_GUIDE.md` | 已归档 | ① AB_01 与 AB_02 打的是同一个站点（DrawString+0x33C）。静态证据（TASK1_STATIC.md 任务 1-A）显示 | 5 |
| `CSFIX_TEST_GUIDE.md` | 已归档 | 1. **A 盘现在还不存在**：本会话开始后 `work\builds\**` 下的**所有 ISO 被外部删除**（取证见 | 1 |
| `CVAR_TEST_GUIDE.md` | 已归档 | 配套盘组：`work\builds\GR_CVAR\`（盘表、sha256、自检结果见该目录 `README.md`）。 | 6 |
| `DISASM_TEST_GUIDE.md` | 已归档 | 1. **重建盘请保留 `SLUS_206.13` 的 ELF 原样**（不要顺手"优化"它）。 | 5 |
| `OOMFIX_TEST_GUIDE.md` | 已归档 | 不要用旧的即时存档（savestate）来验证这次修复。** | 3 |
| `REPORT_16px.md` | 已归档 | 日期：2026-09-16。执行：子代理 16px。产物目录：`work\zh16b\subagent_16px\`。 | 3 |
| `REPORT_SENTINEL.md` | 已归档 | ① ★★ 原盘引擎**没有 2 字节解码**：DrawString 的主循环**每条分支都只前进 1 字节** | 3 |
| `REPORT_W2048_r84.md` | 已归档 | ⇒ 引擎侧结论**：游戏**能启动、能跑满 6000 帧、能命中 WPNRPK74**， | 3 |
| `REPORT_atlas_stall_threshold.md` | 已归档 | 「像素容器变大 ⇒ 读盘停摆」不是引擎的尺寸阈值，而是构筑不变式被违反。** | 1 |
| `REPORT_font_compact.md` | 已归档 | `GR_ZH105`：在用 1175 格 + 空闲 329 格，空闲格**散在** row 2/9/10/11/13/18/19/20/21/22/23/2 | 2 |
| `REPORT_font_repack.md` | 已归档 | 以后每一轮打包都会自动把字库"压实"一遍：把在用的字全部挪到最前面、把空出来的地方扫干净。 | 1 |
| `REPORT_font_testpage.md` | 已归档 | 分支 `round60/font-test-page` · 执行者 = 字库测试页子代理 · 2026-10-14 | 1 |
| `REPORT_hook_nav.md` | 已归档 | 分支 `round61/hook-nav` · 执行者 = 模拟器钩子/闭环导航子代理 · 2026-10-13 | 1 |
| `REPORT_noautowrap.md` | 已归档 | `RSTextComponent::DoWordWrap @0x21CC10` 序言（裸 ELF；可复跑 | 2 |
| `REPORT_reclut_crash.md` | 已归档 | 这是原版游戏（未改动的英文盘）自身的空指针虚函数调用 bug，与汉化无关。** | 2 |
| `REPORT_reclut_crash2.md` | 已归档 | 本轮这条链不是汉化引入的：把用户的即时存档喂给「一字节未改的英文原盘 `GR_EN_ORIG`」、并且把 RAM 里 | 1 |
| `REPORT_sf_nowrap.md` | 已归档 | 要**：特别收录介绍框（各内页的介绍正文）**停止自动折行**，让用户手调的 `{WRAP}`（盘上 `{br}`） | 1 |
| `REPORT_texture_limit_rootcause.md` | 已归档 | 任务书与 `dump_decode_cave.py` 写的是 `ISO = 0x93800 + (VA − 0x100080)`（= VA − 0x6C88 | 1 |
| `REPORT_w2048_probe.md` | 已归档 | ❌ 判据全不过 ⇒「图集变大被引擎挡住」被确证**：以 `GR_ZH123.iso`（实机已证 ✓）为基底， | 1 |
| `REPORT_zero_missing_glyph_build.md` | 已归档 | 口径**：`tcslib.GlyphCache.check_text` 同款 —— `ord(ch) < 0x80` 一律放行；其余必须在 | 1 |
| `REPORT_zero_missing_glyph_build2.md` | 已归档 | round82 零缺字路线（本文写明 GR_ZH121 不可发布） | 3 |

### 统计

* 根目录 md/json：**106** 篇 = 权威 **34** · 历史 **60** · 已过时（就地标记）**11**
* 归档到 `_obsolete/`：**21** 篇（索引见上表；归档理由逐篇写在 `docs/_obsolete/README.md`）
* 本表由 `docs/README.md` 维护者手工分类 + 脚本生成（生成器逻辑见 `docs/REPORT_FINALIZE.md` §C）
