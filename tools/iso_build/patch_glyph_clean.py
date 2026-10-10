# -*- coding: utf-8 -*-
r"""patch_glyph_clean.py — 清除字库图集里的杂散墨点 (逐像素白名单, 可重放)

用法:
    python patch_glyph_clean.py <src_iso> <dst_iso>

═══════════════════════════════════════════════════════════════════════════════
一、目标资源
═══════════════════════════════════════════════════════════════════════════════
  MENU.IMG @LBA 776286, 内部偏移 0x58431, 长 0x4044C
      = COMMON.PAK 内记录 "new_font_revised" (1024x512 PSMT4, psm=0x14)
  像素平面 = 记录 + 0x44C, 0x40000 字节 (每字节 = 偶列低半字节 + 奇列高半字节)

  ⚠ CLUT 关键事实 (本补丁的核心前提, 已从盘上 CLUT 实测):
       CLUT 数据在记录 +0x38 (记录 +0x28 起是 16 B 的 GIF tag)
       CLUT[0] = (R255,G255,B255,A127) → **不透明白 = 墨**
       CLUT[1..255] = (R255,G255,B255,A0) → **全透明**
    ⇒ texel 值 **0 = 墨**, **1 = 空**。
    ⇒ 「清除墨点」= 把该 texel 从 0 改成 **1** (改成 0 反而会**画上**一个墨点)。
       —— 本补丁因此把白名单像素置 **1**, 而不是置 0。

═══════════════════════════════════════════════════════════════════════════════
二、白名单 (逐像素, 只有这些像素会被改动)
═══════════════════════════════════════════════════════════════════════════════
  定位方法: 用 方正像素16.ttf 按 gen_font16.py 的同一渲染法生成 16x16 模板,
            对全图集做滑窗匹配 → 得到每个字的真实格位; 再逐格比对, 列出
            「盘上有墨而模板无墨」的多余像素 (杂散墨点)。

  A 组 —— 用户实测的「地」「里」+ 同带同机理的「进」(全部位于单字节带):
      该带 (单字节码 0xC2..0xDA) 在盘上被整体烘到 y=339..354,
      而引擎对单字节码走 FONT.RES 记录路径, 记录 v0=338 → 实际采样 y=339..354;
      于是该带每一格的**第 15 行 (y=354)** 与下一行 (row19) 字形的**第 0 行**共用。
      对末行为空的字, y=354 上属于下一行字形的墨点就变成字形下方的渗墨。

      (315,354) 「里」 格 (304,339) 内 row15 col11  ← 下一行 (x=304) 字形「乔」首行残留
      (342,354) 「进」 格 (336,339) 内 row15 col 6  ← 下一行 (x=336) 字形「亨」首行残留
      (388,354) 「地」 格 (384,339) 内 row15 col 4  ← 下一行 (x=384) 字形「伟」首行残留
      (393,354) 「地」 格 (384,339) 内 row15 col 9  ← 同上
      ⇒ 与用户报告完全吻合: 地 下方 2 px, 里 下方 1 px。

      ⚠ 代价说明 (已核实): 这 4 个 texel 同时是「乔 / 亨 / 伟」三个字格的首行。
        三者 slot = 1197 / 1199 / 1202, 但全仓库 UI 文本普查
        (work/_squad/UI_TEXT_SURVEY.txt, 1165 个文本站点) 中
        「乔」「亨」「伟」出现次数均为 **0** ⇒ 无可见损失。
        (而「地」17 处、「进」7 处、「里」4 处 ⇒ 收益明确。)

  B 组 —— (本版**未纳入**) 全图集扫描还发现 4 处「模板之外有墨」的同类候选:
      (321,129) 画  /  (642,192) 、  /  (562,192)(570,192)(561,193)(570,193) 。
      但实测把「。」格那 4 点清掉后, 「小队设置」界面上「开始」按钮的「开」字
      底部笔画会变短 ⇒ 判定为**误伤**, 已整体剔除。
      根因: 现役图集是历代补丁拼起来的, 「开」「画」等字在盘上并非 FZXS16 精确渲染
      (与 FZXS16 模板本身就差 5~20 像素), 因此「模板之外的墨点」无法与
      「另一版字体的合法笔画」可靠区分 —— 必须逐点实机取证后才可纳入。
      (扫描明细见 work/_dis/r26_strays.py 输出与 docs/GLYPH_CLEAN_FIX.md。)

═══════════════════════════════════════════════════════════════════════════════
三、自检 (补丁内强制断言)
═══════════════════════════════════════════════════════════════════════════════
  1. 每个白名单像素当前必须是 0 (墨); 若不是 → 报错退出 (基底盘不符)
  2. 改完后, 除白名单像素外 **全图集逐 texel 不变** (含 57 个 非0/1 的 texel)
  3. 除白名单所在的 4 个字节外, **MENU.IMG 的 PAK 记录逐字节不变**
  4. 除 PAK 记录的像素平面外, **整个 ISO 逐字节不变**
"""
import contextlib
import io as _io
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'work', '_dis'))
import x12_lib as L                                        # noqa: E402

MENU_LBA = 776286
OFF_PAK_REC = 0x58431
PAK_REC_LEN = 0x4044C
PIX_OFF = 0x44C
W, H = 1024, 512
INK, BLANK = 0, 1          # CLUT[0]=不透明白(墨), CLUT[1..]=透明

# (atlas_x, atlas_y, 所属字, 组, 说明)
WHITELIST = [
    (315, 354, '里', 'A', '格(304,339) row15 col11 —— 本字末行为空, 该点为下一行字形「乔」首行残留'),
    (342, 354, '进', 'A', '格(336,339) row15 col 6 —— 同上 (下一行字形「亨」)'),
    (388, 354, '地', 'A', '格(384,339) row15 col 4 —— 同上 (下一行字形「伟」)'),
    (393, 354, '地', 'A', '格(384,339) row15 col 9 —— 同上'),
]


def nibble_index(x, y):
    """返回 (字节在像素平面内的下标, 半字节位置 'lo'|'hi')"""
    assert 0 <= x < W and 0 <= y < H, (x, y)
    return y * (W // 2) + (x // 2), ('lo' if x % 2 == 0 else 'hi')


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]
    assert os.path.isfile(src), src
    assert os.path.abspath(src) != os.path.abspath(dst), '源与目标不能是同一文件'

    # ---------- 1. 读源盘 ----------
    raw = open(src, 'rb').read()
    base = MENU_LBA * 2048 + OFF_PAK_REC
    rec = raw[base:base + PAK_REC_LEN]
    assert len(rec) == PAK_REC_LEN, '读不到完整 PAK 记录'
    nl = struct.unpack_from('<I', rec, 4)[0]
    psm, w, h, clut = struct.unpack_from('<IIII', rec, 8 + nl)
    assert (psm, w, h) == (0x14, W, H), '字库记录头不符: psm=%#x w=%d h=%d' % (psm, w, h)
    # CLUT 自检: 索引 0 必须是「不透明白」
    clut_base = 8 + nl + 16 + 16           # 头部 + 16B GIF tag
    c0 = struct.unpack_from('<4B', rec, clut_base + 0)
    c1 = struct.unpack_from('<4B', rec, clut_base + 4)
    assert c0 == (255, 255, 255, 127), 'CLUT[0] 不是不透明白: %s' % (c0,)
    assert c1[3] == 0, 'CLUT[1] 不是全透明: %s' % (c1,)

    pix_off = base + PIX_OFF
    pix = bytearray(raw[pix_off:pix_off + (W * H) // 2])
    assert len(pix) == (W * H) // 2

    def texel(x, y):
        i, half = nibble_index(x, y)
        return (pix[i] & 0x0F) if half == 'lo' else (pix[i] >> 4)

    # ---------- 2. 逐像素白名单校验 + 清除 ----------
    print('[patch_glyph_clean] 源盘 %s' % src)
    print('[patch_glyph_clean] 字库记录 @MENU.IMG+0x%X  像素平面 @记录+0x%X' % (OFF_PAK_REC, PIX_OFF))
    print('[patch_glyph_clean] 白名单 %d 像素 (A 组 %d / B 组 %d)'
          % (len(WHITELIST),
             sum(1 for e in WHITELIST if e[3] == 'A'),
             sum(1 for e in WHITELIST if e[3] == 'B')))
    touched = {}
    for (x, y, ch, grp, note) in WHITELIST:
        old = texel(x, y)
        assert old == INK, ('白名单像素 (%d,%d) [%s] 当前值 = %d, 不是墨(0) —— 基底盘不符'
                            % (x, y, ch, old))
        i, half = nibble_index(x, y)
        if half == 'lo':
            pix[i] = (pix[i] & 0xF0) | BLANK
        else:
            pix[i] = (pix[i] & 0x0F) | (BLANK << 4)
        new = texel(x, y)
        touched[i] = touched.get(i, 0) + 1
        print('   [%s组] %-2s 图集(%4d,%4d)  字节#%6d 半字节=%-2s  %d -> %d   %s'
              % (grp, ch, x, y, i, half, old, new, note))
    exp_bytes = {nibble_index(x, y)[0] for (x, y, _c, _g, _n) in WHITELIST}
    assert set(touched) == exp_bytes, '被碰字节集合与白名单不符'
    print('[assert] 共改动 %d 个像素平面字节 (白名单 %d 像素分布在 %d 字节上)'
          % (len(touched), len(WHITELIST), len(exp_bytes)))

    # ---------- 3. 断言: 除白名单外全图集逐 texel 不变 ----------
    for y in range(H):
        row_off = y * (W // 2)
        for i in range(W // 2):
            gi = row_off + i
            if gi in touched:
                continue
            assert pix[gi] == raw[pix_off + gi], '非白名单字节 #%d 被改动' % gi
    wl = {(x, y) for (x, y, _c, _g, _n) in WHITELIST}
    changed = 0
    for y in range(H):
        for x in range(W):
            i, half = nibble_index(x, y)
            o = (raw[pix_off + i] & 0x0F) if half == 'lo' else (raw[pix_off + i] >> 4)
            n = (pix[i] & 0x0F) if half == 'lo' else (pix[i] >> 4)
            if o != n:
                changed += 1
                assert (x, y) in wl, '白名单外的 texel (%d,%d) 发生变化' % (x, y)
    assert changed == len(WHITELIST), '变化 texel 数 %d != 白名单 %d' % (changed, len(WHITELIST))
    print('[assert] 全图集 524288 texel 逐点校验: 仅白名单 %d 点变化, 其余全部不变 ✓' % changed)

    # ---------- 4. 写目标盘 + 断言只有这 8 字节不同 ----------
    out = bytearray(raw)
    out[pix_off:pix_off + len(pix)] = pix
    diff_bytes = [i for i in range(len(raw)) if raw[i] != out[i]]
    assert len(diff_bytes) == len(exp_bytes), \
        '预期只改 %d 字节, 实际 %d' % (len(exp_bytes), len(diff_bytes))
    for i in diff_bytes:
        assert pix_off <= i < pix_off + len(pix), '改动越出像素平面: %d' % i
    print('[assert] 整个 ISO 逐字节校验: 仅 %d 字节变化, 全部位于像素平面 ✓' % len(diff_bytes))
    assert len(out) == len(raw), 'ISO 尺寸变化'
    open(dst, 'wb').write(bytes(out))
    print('[patch_glyph_clean] 已写 %s  (%d 字节, 尺寸不变)' % (dst, len(out)))
    print('[patch_glyph_clean] 完成: 清除 %d 个杂散墨点' % len(WHITELIST))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
