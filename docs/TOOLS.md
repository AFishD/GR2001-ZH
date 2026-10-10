# tools/ — 现役工具链 (依赖与说明)

全部脚本**相对仓库根推导路径** (无绝对路径); Python 依赖: numpy / opencv-python(cv2) / Pillow,
解释器 = anaconda (`<anaconda3>\python.exe`)。版本谱系见 docs/SCRIPT_VERSION_MAP.md。

## font_pipeline/ — 字库链 (ZH62 实证, 重放见 docs/FONT_PIPELINE.md)
- `gen_font16.py` 基座渲染 (X0=20) · `build_font.py` X0=4 变体 (补丁+exec 基座, 衍生体写版本夹 font_out/)
- `fix_slot_fld26.py` 字表 fld26 · `make_pak.py` 8 段 GIF 重封装 · `shift.py` 行移位+横杠 (自检 vs 现役 89B)
- 内部依赖: `tools/hanliu/tools/{ft_dpc, lz77_decode}` (sys.path 注入); 输入: data/ + docs/han_v2/artifacts/COMMON_PAK.bin
  + third_party/fonts/方正像素16.ttf; 产物: work/builds/GR_ZH62/font_out/ (随版本归档)

## capture/ — 模拟器采集
- `run_brief2.py` / `run_brief2_en.py` 快速导航简报采集 (55s 前缀 nav_p2.txt) · `run_opt.py` 导航采集
- 依赖: third_party/emu/pcsx2/pcsx2-gsrunner (2.8.2 定制; **ISO 参数须反斜杠绝对路径**)
- 转储/记忆卡 → work/builds/<被测版本>/temp/ (EN 原盘 → builds/GR_EN_ORIG/temp/); cv2 读写中文路径须 imdecode/imencode

## iso_build/ — 盘构筑
- `make_build.py` 版本化构筑 (work/builds/<版本>/{ISO, extract/, temp/, build_info.json}; 基底自动探测; --patch 接口接断言式补丁; `--from` 指定基底 / `--no-textdump` 关文本总表 / `--expand-entry` / `--verify-img`)
- **`patch_zh12px.py`** —— **任务名(关卡名)专用 12px 双字库** 一步到位 (7 步: 图集 `v=480..495` 铺 14 字形 / 空闲码位 `0x84..0x91` 换码 / ELF `GR-` / `MENU.IMG #170 <MapName>` / `default` 面占位码位 `0x5E`/`0x60` ← idx 16/17 原 16px / idx 45,16,17 → 12px / `#25`,`#902` 日期换占位)。
  **用法**: `make_build.py GR_ZHxxx --from work/builds/GR_ZH253 --patch tools/iso_build/patch_zh12px.py`
  环境变量: `GR_MAPNAME=1` 额外改 `GR.IMG #661` 副本 (实测无效且有副作用, 默认关); `BASE12PX=1` 只做换码位不做 M/0/1 重定向。
  **三个关键机制**: ①采样 `u = 记录 u0 − 288`; ②推进 = `rec[1]`; ③**码位 ≥ 0x80 宽度被当全宽** ⇒ 占位码位必须 `< 0x80`。
  证据 `work/_dis/TWELVEPX_ROUND1..9.md`; 对比图 `work/archive/cmp/GR_ZH353_final.png`。
- `patch_zh220_planc.py` —— Plan C 码位方案参考 (0x7F..0x83)
- ZH61→ZH62 断言式构建器 build_zh62.py 已归档 (archive/GR_ZH62 分支 tools/iso_build/); 下一代盘照其断言纪律编写补丁脚本, 经 --patch 接入

## emu_build/ — 模拟器构建
- `build_pcsx2.sh [--configure|--purge]` (git-bash 直跑; junction C:\grbuild→仓库; MSVC 14.51 便携链,
  根可用 MVC_ROOT 覆盖; **换源码版本后必须手删 third_party/emu/pcsx2 构建目录**)
- `build_env.py` 环境变量参考; REPORT_port282.md 移植报告

## measure/ — 计量
- `cv_vcheck.py` 「日」字标定盘垂直偏移检测 (二值化+低通; 用法: python cv_vcheck.py img.png ...)

## maint/ — 仓库维护
- `gen_thirdparty_manifest.py` third_party md5 清单重生成 (→ third_party/readme.md)

## gr_tools/ — 16px 代解码/封装库 (CLI 工具/断言式补丁脚本用; font_pipeline 消费的是 hanliu/tools 的 ft_dpc/lz77_decode)
lz77_decode (槽位/PAK) · lzo1x_c (LZO 压缩) · gr_lz · img_tool/img_patch · res_encode · iso_tool/splice_iso ·
font_res_{parse,probe,scan}
⚠ 与 hanliu/tools 同名模块为**代际冻结变体** (字节级不同, 各自被不同脚本钉死, 严禁互换)。

## hanliu/ — ZH7 时代工具箱正本 (字表 CSV→盘复现; 文档 docs/han_v2/)
- 活依赖: tools/{ft_dpc, lz77_decode} (font_pipeline 钉死); fonts/texts 为早期资产; 内部 build_PS_v* 等变体属其自身管线


## 构筑后处理 (每次构筑自动执行)

- `tools/diag/dump_all_text.py` —— 从任意 ISO 导出六类文本来源 (MENU:RES / GR:RES /
  MENU:SF / MENU:TXT / GR:ATR / 其它), 与参考盘 (默认 `work/builds/GR_EN_ORIG`) 逐条并列对照,
  产出 `all_text.csv` / `summary.txt` / `summary.json`;
- `tools/diag/text_table_xlsx.py` —— 渲染多 sheet Excel (总览 / 全部文本 / 分来源),
  冻结首行 + 自动筛选 + 差异行高亮;
- 由 `tools/iso_build/make_build.py` 在构筑末尾自动调用 (`--no-textdump` 可关),
  `build_info.json` 记 `text_table` 路径。

## 模拟器导航

- `tools/capture/nav_state.py` —— **状态机导航** (推荐):
  用模拟器 `-grdrawwin` 产出的 drawlog 作运行时状态钩子, 解出每帧绘制文本,
  按特征串分类界面 (`FILE_SELECT` / `SPECIAL_FEATURES` / `CAMPAIGN_DIFF` /
  `MULTI_NAME` / `OPTIONS` / `MAIN_MENU`), 据此迭代调整输入直至命中目标界面,
  取代盲按时序。
  用法: `python tools/capture/nav_state.py <版本> --target special [--frames 8000]`
- **输入语法要点** (`GRResearch.cpp`): `tap`/`press` 默认**按住 12 帧** → 菜单连发、
  落点不可计数; 必须 `tap` + 紧跟一行 `release`(fr+2) 做 2~3 帧短按, 每次精确 ±1 项。
- 主菜单 9 项**首尾环绕**: 1训练 2战术演习 3战役 4快速任务/重放 5多人游戏 6统计
  7特别收录 8选项 9制作组; 光标初始第 1 项 → **上移 3 次 = 特别收录**。
