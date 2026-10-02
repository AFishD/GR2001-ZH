# Ghost Recon (PS2) 汉化工程

《Tom Clancy's Ghost Recon》(USA, SLUS-206.13, "ike" 引擎) 的全量中文汉化:
16px 方正像素字库全链重建 + 菜单/对话框/标题/简报全界面渲染修复 + 任务文本汉化。

> **现役盘: GR_ZH68** — `work/builds/GR_ZH68/GR_ZH68.iso`
> (sha256 `240b149f…`; 一步重建: `make_build.py GR_ZH69 --from work/builds/GR_ZH62
> --patch tools/iso_build/patch_zh68_all.py` — 合并补丁, 与增量链逐字节等价)
> 增量谱系 ZH63→68 (读卡对话框/EN带像素16/帮助条居中, 含两轮被否决方案) 见
> docs/BUILD_VERSIONS.md + docs/PROGRESS.md §27-33。

## 目录结构 (main 只存现役; 历史在各版本分支)

| 目录 | 内容 |
|---|---|
| **`docs/`** | `PROGRESS.md` (轮次日志/踩坑流水) · `PATCH_INVENTORY.md` (ELF/数据面补丁逐字清单) · `BUILD_VERSIONS.md` (每个构筑版本的差异) · `BUILD_MANIFEST.md` + `iso_layout.json` (ISO 布局) · `SCRIPT_VERSION_MAP.md` (脚本版本关系) · `TOOLS.md` / `FONT_PIPELINE.md` (工具依赖与用法) · `REPORT_*.md` (近期轮报告) · `han_v2/` (逆向方法论手册 + 引擎机制; 数据资产不入库, 见版权与数据资产) |
| **`tools/`** | 现役工具链: `font_pipeline/` (字库链: 渲染→X0=4→fld26→8 段封装→行移位, 重放残差 89B)、`iso_build/` (构筑器 make_build.py, --patch 接断言式补丁)、`capture/` (快速导航采集)、`emu_build/` (gsrunner v2.8.2 构建配方)、`measure/`、`maint/`、`gr_tools/` + `hanliu/` (解码/压缩库 — 两套**代际冻结变体**, 详见 docs/TOOLS.md) |
| **`third_party/`** | 不入库 (仅 readme.md md5 清单): `orig/` (PS2 原盘 ×2 + PC 版原装)、`fonts/方正像素16.ttf`、`emu/` (PCSX2 源码 gr-2.8.2 分支 + 部署运行时 + BIOS/记忆卡)、`deps/` (构建依赖) |
| **`work/`** | 会话临时区 (整体不入库), **只按版本整理**: `builds/<版本>/` (ISO + `extract/` 字表文本 + `font_out/` 字库链产物 + `temp/` 测试产物/转储/记忆卡); EN 原盘基线夹 `builds/GR_EN_ORIG/` 同构 |

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

- 轮次与踩坑: docs/PROGRESS.md (§1-26)
- 补丁逐字清单: docs/PATCH_INVENTORY.md
- 工具怎么用: docs/TOOLS.md · 字库怎么重建: docs/FONT_PIPELINE.md
- 版本间差了什么: docs/BUILD_VERSIONS.md · 脚本代际: docs/SCRIPT_VERSION_MAP.md
- 引擎机制与方法论: docs/han_v2/HANIZATION_MANUAL.md
