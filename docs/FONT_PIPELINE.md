# font_pipeline — 现役字库链 (ZH62 实证)

重放闭合: 263,244B 字库条目 vs 现役盘仅差 89B (1B ZH49 NLOOP + 88B ZH38-41 EN 带标定微调)。

重放顺序 (产物落 work/builds/GR_ZH62/font_out/ — 字库链产物随版本归档):
1. `python tools/font_pipeline/build_font.py`        — X0=4 变体渲染 → COMMON_PAK_V16X.bin / atlas_v16x.png / ft_slot_zh34.bin
2. `python tools/font_pipeline/fix_slot_fld26.py`   — FT fld[1] 16→26 → ft_slot_zh34_fld26.bin
3. `python tools/font_pipeline/make_pak.py`          — 8 段 GIF 重封装 → common_pak_seg_tmp.bin
4. `python tools/font_pipeline/shift.py`             — 行左移 2B + slot1426 横杠 → font_entry_zh62.bin (自检 vs 现役 89B = 1B NLOOP + 88B EN 带微调)
5. (整盘装配) build_zh35/36 为历史参考, 在归档分支

输入: data/ (13px 时代字表/图集) + docs/han_v2/artifacts/COMMON_PAK.bin + third_party/fonts/方正像素16.ttf
（三者均为游戏衍生本地资产, 公开库不入库, 需自备原盘与字体再生）
版本谱系: docs/SCRIPT_VERSION_MAP.md
