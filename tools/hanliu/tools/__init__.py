# -*- coding: utf-8 -*-
"""hanliu.tools — Ghost Recon (PS2, SLUS-206.13) 汉化工具链包

全部脚本收编自项目各工作目录（原件保留原处未动），来源标注见各文件头部
「[hanliu 收编]」横幅。分层：

  [格式层]  IMG 档案 / LZO1X / RES / ISO
    gr_lz.py          IMG 档案解析 + 纯字面量安全编码 (encode_literals/frame_substream)
    lz77_decode.py    标准 LZO1X 解码器 —— 全项目解码基准 (decode_entry/lzo1x_decompress)
    lzo1x_c.py        minilzo 兼容压缩器 (RES 8 子流写回: compress(level=7, use_m1, use_m4))
    res_encode.py     *_STRINGS.RES 解析/文本同构/重建/轮转自检
    img_patch.py      IMG 安全补丁 (原地覆写/空隙/尾部追加, --framed 压缩框架)
    img_tool.py       IMG 列表/解包/重建 (rebuild 重排偏移, 补丁勿用)
    iso_tool.py       ISO9660 list/extract/build
    splice_iso.py     同尺寸 MENU.IMG 原位拼接进原盘 (LBA 776286)

  [字体层]  FONT.RES + COMMON.PAK atlas
    font_res_parse.py FONT.RES face 结构解析探针 (顶层执行)
    font_res_probe.py FONT.RES+atlas 矩形叠加渲染探针 (顶层执行)
    font_res_scan.py  FONT.RES 10B 记录组边界扫描
    ft_dpc.py         LZO1X DP 最优压缩器 —— FONT.RES 写回内核 (payload ≤ 4413B)
    zh7_build.py      ZH7 一体构建参照实现 (顶层执行; 参数化版见 build/example_zh7)

  [ELF 层]  SLUS_206.13 DBCS 补丁 (DrawString 绘制链 16 位化)
    patch_db1_elf.py  Stage1 synth-byte 补丁 (实机 PASS)
    patch_db2_elf.py  Stage2 v1 (boot 毒, 仅存档)
    patch_db2b_elf.py Stage2 v2 (存档)
    patch_db2c.py     Stage2 参数化 + MIPS Asm 套件 (build_PS_v5 依赖其文本)
    build_PS.py       Stage2 v3 → SLUS_P_S.elf (二分矩阵全绿)
    build_PS_v4.py    v3 + 槽位 lh→lhu → SLUS_P_T.elf (GR_DB7 实证对渲染)
    build_PS_v5.py    v4 + lead 标记制(A1-A3) → SLUS_P_U.elf (GR_ZH7 终版采用)
    dis4.py           PS2 EE 手写反汇编器 (slus_scan 版, 顶层执行)
    dis4P.py          dis4 参数化变体 (dbcs 版)
    elf_info.py       ELF 头/节/符号表摘要
    dwarf_probe.py    DWARF 调试信息探针
    font_parse.py     PC 版 font.res 解析 (PC_FONT_MECHANISM 证据链)
    fres.py           PC 版 RES 探针

  [组装/实测层]
    probe_iso.py      参数化实验盘组装 (ELF@LBA295 + MENU@LBA776286 → ISO)
    run_iso.py        zh2 nav 40000 帧 gsrunner 实测
    probe_run3.py     4300 帧快判 (boot 挂死判定)
    run_bisect.py     15500 帧二分 (Name Entry 字母=字形探针)
    run_bisect_win.py 二分窗口变体
    verify_iso.py     核对 ISO 内 ELF/MENU 与产物一致

  [新增整合件]  (本项目为交付新写, 内核复用上述验证过的逻辑)
    font_build.py     字库生成器 (字表→COMMON.PAK 像素差异+FONT.RES 记录表)
    text_replace.py   文本替换器 (CSV→RES blob / GR.IMG RES / TXT / ATR)
    make_iso.py       一键组装成品 ISO (基底+ELF+MENU)
    run_test.py       gsrunner 一键测试 + 健康判据解析
    export_texts.py   全部原始文本导出 → hanliu/texts/*.csv

  research/         普查与测算脚本 (hanzi_demand / gr_res / pcfont / slus_scan)

自检方式:
  - 库模块 (gr_lz/lz77_decode/lzo1x_c/res_encode/ft_dpc/img_patch/img_tool):
        python -c "import <name>"            # 无副作用
  - 顶层执行脚本 (探针/构建器/ELF 补丁/组装实测): 语法级自检
        python -m py_compile <name>          # 这些脚本 import 即执行, 勿盲目 import
"""
