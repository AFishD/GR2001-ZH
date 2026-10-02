# 脚本版本关系图 (2026-09-26)

原则: **tools/ = 现役可重放工具链; docs/ = 报告与手册; work/ = 未跟踪的会话临时文件;
历史 = 版本分支体系: archive/GR_ZH36...GR_ZH62 (各代全工作树指针) + archive/early-builds (ZH3-ZH11 素材/ELF 世系/早期菜单, orphan 提交); catch-all 归档分支已删除**; 其余一切历史代 = 归档分支
`archive/pre-simplify-20260926`** (路径 = 当年原路径)。第三方数据在 third_party/
(md5 清单 third_party/readme.md)。

## 一、字库链 (现役 ZH62 字库的唯一来源, tools/font_pipeline/)

重放闭合实测: 263,244B 字库条目 reproduces 至差 **89B** = 1B ZH49 NLOOP 修复
+ 88B EN 带微调 (ZH38-41 标定时代, slots 1307/1308/1310/1369/1370/1372/1427)。

| 阶段 | 脚本 (tools/font_pipeline/) | 作用 | 原产地 (版本分支/历史) |
|---|---|---|---|
| 0 输入 | data/{charset_compiled_zh16.json, ft_expanded_zh16.bin, atlas_zh16.png, atlas_zh14.png, ft_expanded_zh14.bin} | 13px/14px 时代字表/图集 + FT 展开 (atlas_zh14 = EN 带 texel 拷贝源, atlas_zh16 = 3 字缺字回退源) | work/zh16, work/zh14 |
| 0 输入 | docs/han_v2/artifacts/COMMON_PAK.bin + third_party/fonts/方正像素16.ttf | 原始字体容器 / 字形源 | — |
| 1 基座 | gen_font16.py | 16px 渲染 + PAK 重建 (X0=20; 补丁基座) | 历史: subagent_16px (archive/GR_ZH36 时代) |
| 2 变体 | build_font.py → gen_font16_x04.py | X0 20→4 (PSMT4 采样偏置+4 乱码修复), 图标窗左移16 | 历史: subagent_mojibake (archive/GR_ZH37E+ 时代) |
| 3 字表 | fix_slot_fld26.py | FT fld[1] 16→26 ×2 (**重放与现役 FT 字节全等**) | 历史: subagent_mojibake (archive/GR_ZH37E+ 时代) |
| 4 封装 | make_pak.py | 像素容器 → 8 段自闭合 GIF (盘侧拆传; 技术源自 subagent_split/make_pak_v21 (archive/GR_ZH37E+ 时代)) | 历史: subagent_mojibake (archive/GR_ZH37E+ 时代) |
| 5 行移 | build_zh38_final.py / build_zh38a.py | 每行左移 2B (=4 texel, 图标带豁免) + slot1426 横杠 = **现役编码** | 历史: subagent_root2 (archive/GR_ZH40 时代) |
| 6 盘 | build_zh35.py / build_zh36.py (+ zh16_iso) | MENU_V23/V24 + V22/V23 ELF 装配 | subagent_mojibake / subagent_final |
| 7 节点 | build_zh49.py (work/zh16b/archive/GR_ZH49 时代 → 归档) | 字库 CLUT 节点 NLOOP 0x40→0x04 | archive/GR_ZH49 时代 |
| 5 行移 | shift.py | 阶段 4 产物 → 行左移 2B + slot1426 横杠 → font_entry_zh62.bin (自检 vs 现役 89B) | 提取自 subagent_root2/build_zh38_final |

缺件声明: work/zh16/MENU_ZH16.img (58M, 阶段 6 完整 ISO 装配输入, 未跟踪) 已不在 —
经 hanliu 链再生; 阶段 5 的 88B EN 带微调未逐格归因 (ZH38a Phase2/zh39p/zh41 标定族)。
data/ 的 COMMON_PAK_ZH16.bin 与 ft_slot_zh16.bin (v16 代产物, 现役链不读) 已删 —
由基座 gen_font16.py (X0=20) 可原样重生成。

## 二、其它现役工具 (tools/)

| 目录/脚本 | 作用 | 原产地 |
|---|---|---|
| capture/{run_brief2.py, run_brief2_en.py, run_opt.py, nav_p2.txt, nav_opt.txt} | 快速导航采集 (55s 主菜单→简报), 转储→work/builds/<被测版本>/temp/ | subagent_brief2 / subagent_navopt |
| (已归档) build_zh62.py | ZH61→ZH62 断言式构建器, 存 archive/GR_ZH62 分支 tools/iso_build/; 下一代盘用 make_build.py --patch | subagent_brief2 |
| emu_build/{build_pcsx2.sh, build_env.py} | gsrunner v2.8.2 构建配方 (junction C:\grbuild) | round11 定版 + port282 |
| emu_build/REPORT_port282.md | 2.8.2 移植报告 | port282 轮 |
| gr_tools/ | 解码/封装库 (16px 代冻结变体; CLI/断言式补丁脚本用) | 早期 |
| hanliu/tools/ | ZH7 代原版库 (font_chain 钉死其 ft_dpc/lz77_decode; 与 gr_tools 同名模块为**代际冻结变体, 有字节差, 严禁互换**) | 早期正本 |
| hanliu/ | 汉化工具链正本 (CSV→ZH7 复现; ft_dpc/lz77 为字库链依赖) | 早期正本 |
| measure/cv_vcheck.py | 「日」字标定盘垂直偏移检测 (二值化+低通, PROGRESS §16 计量) | round §16 |
| maint/gen_thirdparty_manifest.py | third_party md5 清单生成 | round24 清理 |

## 三、历史代索引 (版本分支指针 + git 历史)

| 时代 | 目录 (work/zh16b/) | 产物/结论 | 被什么取代 |
|---|---|---|---|
| 13px 字库 | work/zh16, work/zh14 (已解散) | ZH7-ZH16 盘, charset/FT 基础 | 输入存活于 font_pipeline/data |
| 16px 可行性 | FEASIBILITY_ANALYSIS_R4.md, subagent_16px | v16 管线, ZH22 系列 | → mojibake (X0 修复) |
| v17 诊断 | subagent_16px_fix | V17/V17r2 (未通过) | → offset_fix |
| 偏移定案 | subagent_offset, subagent_offset_fix | fld26 + 0x21D940 cave 系 | → final |
| 拆传 | subagent_split | 8 段技术 (v21) | → mojibake (v22) |
| 乱码+X0 | subagent_mojibake | ZH34/35, X0=4 | → final |
| 完美盘 | subagent_final | ZH36 (v18b/v23 ELF) | → menu/pattern |
| 菜单乱码 | subagent_menu | ZH37E/37F | → root2 |
| 行移位 | subagent_pattern, subagent_root2 | ZH38/38A/39P/40/41/43 | → blackfix |
| 黑屏 | archive/GR_ZH49 时代 | ZH49 五字节 | → l1panel3 |
| 界面修复 | subagent_l1panel/2/3, dialog, root2 后期 | ZH50-61 (cave 系) | → brief2 |
| 简报目标 | subagent_brief2 (报告在 docs/) | ZH62 下沉补偿 | 现役 |
| 导航 | subagent_navopt (报告在 docs/) | 55s 快速导航 | 现役 (工具 tools/capture, 报告 docs/REPORT_navopt.md) |
| 模拟器 | subagent_gs (p4 备份), port282 | PATH3 修复, 2.8.2 移植 | gr-2.8.2 分支 (third_party/emu) |

## 三B、docs/han_v2 — 文档包 (仅手册; 数据资产本地保留不入库)
inject_v2/v3/v5/v6/v12/build_final 等 12 个历史注入脚本已移归档分支 (ZH7 代);
**artifacts/COMMON_PAK.bin 为现役字库链输入 — 本地保留, 公开库不入库**。

## 三C、构筑体系 (tools/iso_build/make_build.py)
- `python tools/iso_build/make_build.py GR_ZH<NN> [--patch <补丁脚本>] [--from <基底>]`
- 产出 work/builds/<版本>/: 完整 ISO + extract/ (字表 4421B / 字库记录 0x4044C / MENU.IMG 全量) + font_out/ (字库链产物, 字库链 5 脚本写入) + temp/ (测试产物/转储/记忆卡) + build_info.json
- 测试产物 (截图/日志/转储) 一律落对应版本 temp/; 转储工具 tools/capture/; EN 原盘基线夹 work/builds/GR_EN_ORIG/ 同构 (extract/ 存原盘 EN MENU.IMG 缓存)
- build/ 与 test_results/ 已并入 work/ (work/build 已被 builds 取代并删除); build/fonts 旧参照图已删 (链产物可再生成); work/ 顶层并列夹 font_out/cap 已并入版本夹, work/ 下只留 builds/

## 四、模拟器源码 (third_party/emu/pcsx2_src, 独立 git)
- 分支 gr-2.8.2 = v2.8.2 标签 + 钩子 cherry-pick (cd5e3304c) — **现役**
- 分支 master + 快照提交 a657fa313 — 钩子主快照 (2.9.32 代)
