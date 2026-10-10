# Ghost Recon (PS2) 汉化工程

《Tom Clancy's Ghost Recon》(USA, SLUS-206.13, "ike" 引擎) 的全量中文汉化:
16px 方正像素字库全链重建 + 菜单/对话框/标题/简报全界面渲染修复 + 任务文本汉化
+ **任务名(关卡名)专用 12px 双字库**。

> **现役盘（2026-10-09 · GR_ZH91）**
>
> | 盘 | 用途 | 关键点 |
> |---|---|---|
> | **`GR_ZH92`** | **★ 现役盘** | `work/builds/GR_ZH92/`（`GR_ZH92.iso` sha256 `1d30c106…`；同目录自带 `text/` 文本表与 `font/` 字库快照）<br>= ZH82 在役 ELF 状态 + 子界面标题居中还原 + 字库杂散墨点清理<br>+ **特别收录金框条目名条件化居中** + **全量删除多余空格 (792 处, 排版零变化)** + **小队设置按钮错译修正 (命令→顺序)**<br>审计 `r23_audit_inventory.py` **缺失 0**；人名**纯英文** |
> | `GR_EN_ORIG` | 英文原盘基线 | 硬链接到原盘，零额外占用 |
>
> **★ 分支纪律**：每次改动**先开 git 分支**，做完再合并（round26/round27/round28 已合并）。
>
> **★ 版本号规则**：每次改动产出新盘用**新版本号**（单调递增，跳过历史已用编号；
> 当前现役 `GR_ZH91`，下一个新盘从 `GR_ZH92` 起 —— `zh88` 为历史 capacity 实验编号，跳过）。
>
> **⚠ 铁律**
> 1. `docs/PATCH_INVENTORY.md` 是 ELF 补丁**唯一权威总账**；改完 ELF 必须跑
>    `tools/iso_build/audit_inventory.py <iso>`，结果必须**「缺失 0 条」**。
> 2. **用户认证过的值不得被后续补丁覆盖**（`0x21D940`=K21、`0x565910`=+7 都被 `patch_zh85` 误回退过）。
> 3. `GR.IMG` 条目 `off`/`stored` 与原盘逐条一致；人名保持**英文原名**。
> 4. 字库图集是 **PSMT4 4bit 调色板索引**：**0=墨、1=空**；`0xB7` 是字集里 `小` 的合法码位；
>    引擎对单字节码采样窗 = `[v0+1, v1+1)`。
> 5. 同一旋钮管多类场景时必须**条件化**（形状判据），并在全帧回归里验证旁路场景零改动。
>
> 修复脚本: `patch_glyph_clean.py` / `patch_zh_title_center.py` / `patch_zh_sf_title.py` / `patch_zh_sf_text.py` / `patch_zh_sf_spaces_all.py` / `patch_zh_fix_order_label.py`。
>
**文本工具链**（dump → 人工在 CSV 里改换行 → 注入）: `tools/text_csv/`，说明见 `tools/text_csv/FORMAT.md` 与 `docs/REPORT_csv_text_tool.md`。
> 详见 `docs/PROGRESS.md §58–§69`。




## 12px 双字库方案（`GR_ZH366`）

**需求**：只有**任务名（关卡名）**用 12px，不污染其它 16px 文本。

**关卡名来源**：`EN_STRINGS.RES`（`MENU.IMG #25` / `GR.IMG #902`）里该任务的 **`Name` 条目**，
显示时截断到第一个空格；战役另拼 ELF 静态串 `GR-`。

**实现**（`tools/iso_build/patch_zh12px2.py`）：

| 步骤 | 内容 |
|---|---|
| 1 | MENU.IMG 图集 `v=480..495` 铺 25 个 12px 字形（步进 14 texel） |
| 2 | 占位码位 `0x7F..0x91` + `0x93..0x98`（跳过 0x92），FT **三个面**改记录 |
| 2a | **修 huge 面截断**：汉化字库 huge 面只有 96 条（原盘 224 条）⇒ 补齐 128 条（复制 default 面记录） |
| 3 | ELF 字符串资源 `GR-`（VA `0x57ED20`）→ 占位码位 |
| 4 | ELF 宽度表（`0x4891C4`）25 个码位 → 8 |
| 5 | 语言表：**只改 `Name` 条目**的首个 token，**字符串结构（`" - 中文"`）原样保留**；`MapName` 一律不动 |

**结果**：战役 `GR-M01` 全 12px ✓；训练关 `T0N` ✓；战术演习 **`TAC1`..`TAC5`**
（token 只有 4 B，写不下 5 B 的 `TAC01`）。

**逐轮证据**：`work/_dis/TWELVEPX_ROUND1..10.md`、`work/_dis/R11_TAC_HANG.md`。
**对比图**：`work/archive/cmp/GR_ZH363_final.png`（关卡名）、`work/archive/cmp/GR_ZH366_hangfix.png`（卡死修复）。



**⚠ 制作组名单勘误**：真正的制作组名单是 **`GR.IMG #551..#565`**（15 个含 `CREDIT` 的文件，
共 826,392 B），三个中文盘实测 **0 字节差异**（完全不触碰）。
`EN_STRINGS.RES` 原盘内容是 `Victory!` / `Firefight` 等**游戏内 UI 提示文本**，
本地化成中文属预期交付内容，**不是**制作组名单。

## 目录结构 (main 只存现役; 历史在各版本分支)

| 目录 | 内容 |
|---|---|
| **`docs/`** | `PROGRESS.md` (轮次日志/踩坑流水) · `PATCH_INVENTORY.md` (ELF/数据面补丁逐字清单) · `BUILD_VERSIONS.md` (每个构筑版本的差异) · `BUILD_MANIFEST.md` + `iso_layout.json` (ISO 布局) · `SCRIPT_VERSION_MAP.md` (脚本版本关系) · `TOOLS.md` / `FONT_PIPELINE.md` (工具依赖与用法) · `REPORT_*.md` (近期轮报告) · `han_v2/` (逆向方法论手册 + 引擎机制; 数据资产不入库, 见版权与数据资产) |
| **`tools/`** | 现役工具链: `font_pipeline/` (字库链: 渲染→X0=4→fld26→8 段封装→行移位, 重放残差 89B)、`iso_build/` (构筑器 make_build.py, --patch 接断言式补丁)、`capture/` (快速导航采集)、`emu_build/` (gsrunner v2.8.2 构建配方)、`measure/`、`maint/`、`gr_tools/` + `hanliu/` (解码/压缩库 — 两套**代际冻结变体**, 详见 docs/TOOLS.md) |
| **`third_party/`** | 不入库 (仅 readme.md md5 清单): `orig/` (PS2 原盘 ×2 + PC 版原装)、`fonts/方正像素16.ttf`、`emu/` (PCSX2 源码 gr-2.8.2 分支 + 部署运行时 + BIOS/记忆卡)、`deps/` (构建依赖) |
| **`work/`** | 会话临时区 (整体不入库), **只按版本整理**: `builds/<版本>/` (ISO + `extract/` 字表提取 + `temp/` 转储/记忆卡); EN 原盘基线夹 `builds/GR_EN_ORIG/` 同构。**`extract/` 与 `temp/dump_*` 均为可重建产物**（`make_build.py` / `run_opt.py` 再生），清理时直接删 |

**版本分支**: `archive/GR_ZH36 … GR_ZH62` (每代盘的完整工作区指针) + `archive/early-builds`
(ZH3-ZH11 素材 / ELF 世系 / 早期菜单)。

## 构筑 (tools/iso_build/make_build.py)

```
python tools/iso_build/make_build.py GR_ZH63                  # 基底=最新构筑, 原样继承
python tools/iso_build/make_build.py GR_ZH63 --patch <补丁.py> # 继承 + 断言式补丁
python tools/iso_build/make_build.py GR_ZH63 --from work/builds/GR_ZH62
```
产出 `work/builds/GR_ZH63/`: 完整 ISO + extract/ (字表/字库记录/MENU.IMG) + temp/ (测试产物)。
字库再生: docs/FONT_PIPELINE.md (4 命令重放落 builds/<版本>/font_out/, 现役残差 89B)。

## 模拟器测试

gsrunner (PCSX2 v2.8.2 定制, 钩子: drawlog/组件级/TEX1) 部署于
`third_party/emu/pcsx2/pcsx2-gsrunner/`; 源码分支 gr-2.8.2 (third_party/emu/pcsx2_src 内嵌 git)。
采集: `tools/capture/run_brief2.py` (55 秒开机→简报导航), 产物落构筑夹 temp/。
ISO 参数须**反斜杠绝对路径**。

## 版权与数据资产

- 本仓库仅含**自研工具链与方法论文档**（脚本/手册/布局表/导航脚本），供学习研究使用。
- 游戏衍生数据资产**一律不入库**（本地保留）: 游戏文本导出（hanliu/texts CSV、任务简报
  MIS、字符串 dump）、字库数据（FONT.RES 展开/图集/容器）、模拟器截图与纹理。克隆后需
  **自备原盘**，经 `tools/hanliu/tools/export_texts.py` 与 `docs/FONT_PIPELINE.md` 字库链再生。
- "Tom Clancy's Ghost Recon" 及相关商标归 Ubisoft 所有; 本项目与其无隶属关系，
  不分发任何游戏内容。

## 关键文档入口

- 轮次与踩坑: docs/PROGRESS.md · 12px 逐轮证据: `work/_dis/TWELVEPX_ROUND1..9.md`
- 补丁逐字清单: docs/PATCH_INVENTORY.md
- 工具怎么用: docs/TOOLS.md · 字库怎么重建: docs/FONT_PIPELINE.md
- 版本间差了什么: docs/BUILD_VERSIONS.md · 脚本代际: docs/SCRIPT_VERSION_MAP.md
- 引擎机制与方法论: docs/han_v2/HANIZATION_MANUAL.md
- 字库实测现状: docs/FONT_CURRENT_STATE.md
