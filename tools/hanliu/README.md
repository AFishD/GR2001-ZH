# hanliu — Ghost Recon (PS2) 汉化工具链

对《Tom Clancy's Ghost Recon》(USA, SLUS-206.13, "ike" 引擎) 的完整汉化工具链、
全部原始文本与统一文档。**从字表 CSV 出发可逐字节复现 GR_ZH7 全量中文盘**
（40000 帧 gsrunner 实测 PASS；示例 `build\example_zh7\` 已随 main 瘦身归档于
archive/GR_ZH36 等版本分支）。

> 核心文档：`..\..\docs\han_v2\HANIZATION_MANUAL.md`（项目全时间线 + 逆向方法论 +
> 引擎铁律 + 工具手册 + 从零复现指南）。本 README 只做目录导览。

## 目录

```
hanliu\
  tools\            工具链（收编自项目各工作目录 + 新整合件；原件均未动）
    gr_lz.py lz77_decode.py lzo1x_c.py res_encode.py     ← 格式层: IMG/LZO1X/RES
    img_patch.py img_tool.py iso_tool.py splice_iso.py   ← 档案层: IMG 补丁 / ISO
    font_res_parse.py font_res_probe.py font_res_scan.py ft_dpc.py zh7_build.py
                                                         ← 字体层: FONT.RES/atlas
    patch_db1_elf.py … build_PS_v5.py dis4.py …          ← ELF 层: DBCS 补丁/反汇编
    probe_iso.py run_iso.py probe_run3.py run_bisect.py verify_iso.py ← 组装/实测
    font_build.py text_replace.py make_iso.py run_test.py export_texts.py
                                                         ← 新整合件（见下）
    research\         普查与测算脚本（hanzi_demand 字频 / gr_res 普查 / pcfont / slus_scan）
    __init__.py       每个工具的用途与自检方式清单
  texts\            原始文本导出（6 张 CSV + README，行数全部与源核对）
    menu_res_en.csv   MENU RES 2232 条     gr_res_en.csv   GR RES 2232 条
    txt_family.csv    TXT 家族 2220 行     atr_actors.csv  .ATR 1193 档案
    mis_briefings.csv .MIS 46 份简报       pc_official_zh.csv 官方 PC 中文 2902 行
  build\ (已随 main 瘦身归档: git checkout archive/GR_ZH36 -- hanliu/build 可取回)
    example_zh7\      端到端可复现示例：字表 CSV → MENU（与 GR_ZH7 逐字节一致）
  fonts\
    FONTS.md          SimHei/Zpix 路径、取形方式、授权注记 + 布局/字表数据
  docs\              各工具详细用法与从零复现指南（HANIZATION_MANUAL 的拆分版）
```

## 新整合件（本次为交付编写，内核全部复用已实机验证的逻辑）

| 工具 | 作用 | 内核来源 |
|---|---|---|
| `font_build.py` | 字表 CSV → COMMON.PAK 像素差异 + FONT.RES 记录表（单字节 / DBCS 标记对两种策略；parse 回环 + DP 压缩 + 槽回环 + PAK 差异白名单自检） | zh7_build.py 布局/绘制 + ft_dpc.py |
| `text_replace.py` | 翻译 CSV → 8 子流 RES blob（≤47,570 槽检）/ GR.IMG RES / TXT / ATR；字表外字符报错（宁少勿错） | zh7_build.py encode + res_encode/lzo1x_c |
| `make_iso.py` | 原盘 + 补丁 MENU(@LBA776286) + 补丁 ELF(@LBA295) → 原尺寸成品 ISO + 回读自检 | probe_iso.py / splice_iso.py |
| `run_test.py` | gsrunner 一键测试（预置 zh2nav/quick/bisect 导航，needle/cdvd 卡死判据解析） | run_iso.py / probe_run3.py |
| `export_texts.py` | 一键导出 texts\ 全部 6 张 CSV（带基准条数自检） | res_encode/gr_lz + 本次 PC RES 破译 |

## 快速开始（三个常用场景）

```bat
set PY=<anaconda3>\python.exe

:: 1) 导出全部原始文本
%PY% tools\export_texts.py

:: 2) 复现 GR_ZH7（dry-run，不拼 ISO; example_zh7 已归档, 先
::    git checkout archive/GR_ZH36 -- hanliu/build 取回）
%PY% build\example_zh7\zh7_pipeline.py

:: 3) 用自己的译文迭代 RES（不改字体）
%PY% tools\text_replace.py --mode res --charset build\example_zh7\out\charset_compiled.json ^
     --input my_trans.csv --base-res <8子流基底> --target menu --out new_blob.bin
```

## 自检方式

- 库模块（gr_lz / lz77_decode / lzo1x_c / res_encode / img_patch / img_tool / ft_dpc /
  font_build / text_replace / make_iso / run_test / export_texts）：
  `python -c "import <名>"` 无副作用。
- 顶层执行脚本（探针/构建器/ELF 补丁/dis4 等，import 即执行）：`python -m py_compile`。
- 2026-09-13 全量自检：**62 个脚本全部通过**（12 import 级 + 50 compile 级）。

## 红线（改代码前必读）

1. IMG 条目表 off/stored/real 三字段不动；RES/FONT.RES/PAK 一律**槽位内原位覆写**。
2. FONT.RES 的 0xFF"槽"= 表尾 + huge 头，禁写；条目表 real 必须保持 7,222。
3. 0x80-0x9F 是引擎毒区；0xA1 码位 + u0=0 的记录会被渲染冻结（u0 ≥ 1）。
4. RES 写回必须复刻基底 8 子流布局，单大子流 = 帧 740 必死。
5. gsrunner 的 ISO 参数必须**反斜杠路径**；实测记忆卡: 原 memcards_db1 已清理,
   现用 third_party/emu/run/memcards (换记忆卡基准需重校 nav 计时)。
