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
- `make_build.py` 版本化构筑 (work/builds/<版本>/{ISO, extract/, temp/, build_info.json}; 基底自动探测; --patch 接口接断言式补丁)
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
