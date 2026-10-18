# GR2001-ZH —— 《幽灵行动》PS2 (SLUS-206.13) 简体中文汉化 · 公开快照

**2026-10-20 快照。** 本仓库是**公开只读快照**（孤儿提交），内容 = **脚本 + 文档**，
**不含任何 ISO、游戏数据、模拟器二进制**。

* 成品盘：`GR_ZH126.iso` — 1,648,164,864 B · sha256 `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5`
  （**不随快照发布**；按本仓库的强制规则，任何人可用「英文原版 ISO + 只读 cdvd 转储」在 4.1 s 内逐字节重建）
* 现役分支：`main` · 快照分支：`snapshot-2026-10-20` · 两者**同指一个提交**

---

## 一、这个快照里有什么

| 目录 | 内容 |
|---|---|
| `tools/final_fix/` | **唯一权威修复配方**：`apply_fix.py`（打补丁/校验，27 条断言）· `fix_spec.json`（补丁表）· `rebuild_base.py`（从英文原盘重建基底）· `repro_from_eng.ps1`（端到端复现）· `README.md` |
| `tools/rounds/<主题>/` | 各轮（36 个主题）的构筑 / 验证 / 取证脚本，**保留当年相对子路径**（`tools/`、`temp/`、`temp/rNN/`、`audit/`、`verify/`） |
| `tools/re/toolbelt/` | 逆向 / 取证通用工具带（264 个：`zx_*` `zero_*` `cave_*` `cap_*` `pc_*` `fa_*` `space_*` `thr_*` `root_*` `migrate_*` …） |
| `tools/re/ghidra_scripts/` | 自研 Ghidra 脚本（`.java` + `decomp_crash.py`） |
| `tools/iso_build/` `tools/text_csv/` `tools/font_pipeline/` `tools/diag/` `tools/capture/` `tools/hanliu/` `tools/maint/` `tools/snapshot/` | 构筑 / 文本 CSV / 字库管线 / 诊断 / 取证 / 维护 / 快照机具 |
| `tools/README_scripts.md` | **脚本总索引**：映射规则、主题一览、引用更新清单、可跑性分级、抽验结果 |
| `tools/scripts_move_map.csv` | 「原路径 → 新路径」逐条对照表（1,287 行） |
| `docs/` | 全部工程文档：现状入口 `STATUS.md` · 历史错误断言订正 `CORRECTIONS.md` · 本轮报告 `REPORT_SCRIPTS_MOVE.md` · 各轮 `REPORT_*.md` |

## 二、怎么复现成品盘

```powershell
# 需要（都不在快照里，请自备）：
#   third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso
#       sha256 2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531
#   PCSX2 cdvd 块转储 GR_FA2400_K2 (…).dump   (74,286,520 B)

powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1
```

链路（全部只读输入）：

```
英文原盘 ⊕ K2 cdvd 转储  --rebuild_base.py-->  GR_REBUILD2400.iso   d7f83d7e…43ca0   (4.1 s)
GR_REBUILD2400.iso + F4/OOMFIX/F7  --apply_fix.py-->  GR_ZH126.iso  d8007873…1b2ab5
```

单独校验一张已有的盘（不需要模拟器、不需要基底）：

```powershell
python tools\final_fix\apply_fix.py --verify-only --iso <盘.iso>
```

> **强制规则（2026-10-18 确立）**：一切构筑**必须从英文原版 ISO 出发**，禁止以上一版汉化 ISO 为基底。
> 细节见 `tools/final_fix/README.md` 顶部。

## 三、修复三件套（都在游戏盘 ELF 内）

| 名 | 站点 VA | 原字 → 新字 | cave | 作用 |
|---|---|---|---|---|
| **F4** | `0x00102588` | `0x1459FFD1` → `0x081068D7` | `0x0041A35C` | malloc 大块桶链扫描：链头不在 RAM 内就 bail |
| **OOMFIX** | `0x00539174` | `0xAE620004` → `0x08154012` | `0x00550048` | 解压器 malloc 返回 NULL 时不再写 NULL+4 |
| **F7** | `0x001021D4` | `0x1447FFEA` → `0x08177B31` | `0x005DECC4` | own-bin 回边：链头非法就 bail，截断自旋 |

## 四、本轮（2026-10-20 快照）相对上一快照的变化

1. **脚本统一归位**：`work\` 下全部 1,287 个 `.py`/`.ps1` 移入 `tools\`
   （`work\tools\*` → `tools/re/toolbelt/`；`work\builds\<版本>\*` → `tools/rounds/<主题>/`；
   `work\_planc\*` → `tools/rounds/planc/`；`_archive_scratch\*` → `tools/snapshot/`）。
2. **引用修复**：187 + 177 个脚本的 `sys.path` 引导与仓库根深度按新位置最小改动（逐条登记在 `tools/README_scripts.md` §5）。
3. **`work\` 收尾**：76 个历史版本目录退役（释放 ≈2.09 GB），只留成品盘、取证工具链与用户证据。
4. **一次事故已恢复**：清理时误删成品盘，已用 `repro_from_eng.ps1` 从英文原盘重建，
   sha256 与交付成品**逐字节相同**；清理脚本已修正。详见 `docs/REPORT_SCRIPTS_MOVE.md` §0 与 `docs/CORRECTIONS.md` §9。

## 五、不发布什么（`.gitignore` 一律不发布）

* 全部 ISO / 镜像 / `.bin` / 存档（`*.iso` `*.bin` `Mcd*.ps2` …）
* 游戏衍生数据资产：解包 dump、字库/图形/字符集 dump（`docs/han_v2/artifacts/**`、`docs/han_v2/mis_decoded/**`、
  `tools/font_pipeline/data/**`、`tools/hanliu/texts/*.csv`、`tools/hanliu/fonts/*` …）
* 第三方源码 / 依赖 / 模拟器（`third_party/**`）
* `work/**`（会话产物）

快照构建时会对树做**禁用扩展名扫描**（`.iso .elf .bin .mis .rsb .bmb .png .p2s .xlsx .dll .exe .zip .7z`），
命中即中止发布。

## 六、许可与致谢

汉化补丁与脚本为本工程原创。原游戏版权归 Ubisoft / Red Storm Entertainment 所有；
本仓库**不包含**任何游戏本体数据。第三方工具（Ghidra、PCSX2 等）版权归各自所有者。
