# -*- coding: utf-8 -*-
r"""patch_font_huge.py — 只修「汉化字库 huge 面被截断」(16px 主线补丁)

## 背景 (第 11 轮定位)
英文原盘 FONT.RES 的三个面: large 224 / default 224 / **huge 224** (fld=[…,16,14] → 16×14);
汉化盘被改成 large 224 / default 224 / **huge 96** (fld=[…,16,6] → 16×6)。
引擎渲染任何码位 ≥ 0x80 (idx = code−0x20 ≥ 96) 且使用 huge 面时**读到面外**,
面外紧跟 `{u32 nstyles}=8` ⇒ 记录 = {f0=8, f1=0, …} ⇒ **字符推进 = 0**
⇒ 文本布局死循环 ⇒ 用户报的「所有战术演习任务进入游戏后卡死」。

## 修法
把 huge 面记录数恢复成 224, 新增的 128 条**复制 default 面同 idx 的记录**
(字形/推进都合法), 其余字节不动。FT 5942 → 7222 B (与原盘一致)。

用法: make_build.py GR_ZH266 --from work/builds/GR_ZH256 --patch tools/iso_build/patch_font_huge.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
sys.path.insert(0, os.path.join(REPO, 'work', '_dis'))
import x12_lib as L                                      # noqa: E402
import iso_tools as T                                    # noqa: E402
from lz77_decode import lzo1x_decompress                 # noqa: E402
from lzo1x_c import compress as lzo_compress             # noqa: E402

MENU_LBA = 776286
TAB_OFF, TAB_STEP = 0x830, 48
E_STORED, E_OFF = 6, 8
OFF_FT, FT_SLOT = 0xB9120, 4421
EN_HUGE = (16, 14)          # 英文原盘 huge 面 fld[4], fld[5]
WIDTH_TAB_OFF = 0x4891C4    # ELF 宽度表 (覆盖码位 0x00..0x9B)
ELF_LBA = 295
DOT_CODE = 0x99             # 合法空闲码位, 用作 16px 间隔号 '·'
BAND_V, STEP = 480, 14
CELL_W, CELL_H = 8, 16


def lz_records(blob):
    parts, q = [], 0
    while q + 8 <= len(blob):
        L, S = struct.unpack_from('<II', blob, q)
        if L == 0 or q + 8 + L > len(blob) or S > 16_000_000:
            break
        dd, err, _ = lzo1x_decompress(blob[q + 8:q + 8 + L], out_size=S)
        if err:
            break
        parts.append((q, L, S, bytes(dd)))
        q += 8 + L
    return parts, q


def main(src, dst):
    d = bytearray(open(src, 'rb').read())
    base = MENU_LBA * 2048
    e = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * 4)
    assert e[E_OFF] == OFF_FT and e[E_STORED] == FT_SLOT, 'FONT.RES 位置异常'
    fblob = bytes(d[base + e[E_OFF]:base + e[E_OFF] + e[E_STORED]])
    frecs, consumed = lz_records(fblob)
    ft = bytearray(frecs[0][3])
    p = 0
    l0 = struct.unpack_from('<I', ft, p)[0]
    p += 4 + l0
    nf = struct.unpack_from('<I', ft, p)[0]
    p += 4
    faces = []
    for _ in range(nf):
        l = struct.unpack_from('<I', ft, p)[0]
        p += 4 + l
        fld_off = p
        fld = list(struct.unpack_from('<14I', ft, p))
        p += 56
        nr = fld[4] * fld[5]
        faces.append((p, nr, fld_off, fld))
        p += nr * 10
    styles_off = p
    huge = faces[-1]
    if huge[1] >= EN_HUGE[0] * EN_HUGE[1]:
        print('[ft  ] huge 面已是 %d 条, 无需补' % huge[1])
    else:
        cur = huge[1]
        add = EN_HUGE[0] * EN_HUGE[1] - cur
        src_off = faces[1][0]
        newrecs = bytearray()
        for k in range(add):
            newrecs += ft[src_off + (cur + k) * 10:src_off + (cur + k) * 10 + 10]
        fld = list(huge[3])
        fld[4], fld[5] = EN_HUGE
        ft[huge[2]:huge[2] + 56] = struct.pack('<14I', *fld)
        ft = ft[:styles_off] + newrecs + ft[styles_off:]
        faces[-1] = (huge[0], EN_HUGE[0] * EN_HUGE[1], huge[2], fld)
        print('[ft  ] ★ huge 面 %d → %d 条 (补 %d, 复制 default 面)'
              % (cur, EN_HUGE[0] * EN_HUGE[1], add))

    # ---- 16px 间隔号 '·' (码位 0x99) ----
    #   ATR 补丁把 '·' 编成单字节 0xB7 (非字集合法码) ⇒ 引擎当 DBCS 首字节 ⇒ 名字错位。
    #   这里: 图集画 3×3 中点 + 三面写记录 + 宽度表置 8。
    A, _ = L.read_atlas(src)
    A2 = A.copy()
    dot_u = 24 * STEP + 4
    A2[BAND_V:BAND_V + CELL_H, dot_u:dot_u + CELL_W] = 1
    for yy in range(3):
        for xx in range(3):
            A2[BAND_V + 6 + yy, dot_u + 2 + xx] = 0
    dot_rec = struct.pack('<BB4H', 0, 8, dot_u + 288, BAND_V,
                          dot_u + 288 + CELL_W, BAND_V + CELL_H)
    nd = 0
    for (fo, nr, _d, _f) in faces:
        if DOT_CODE - 0x20 < nr:
            ft[fo + (DOT_CODE - 0x20) * 10:fo + (DOT_CODE - 0x20) * 10 + 10] = dot_rec
            nd += 1
    print('[dot ] 码位 0x99 = 16px 中点 (图集 u=%d..%d), 写入 %d 面' % (dot_u, dot_u + CELL_W - 1, nd))
    d[ELF_LBA * 2048 + WIDTH_TAB_OFF + DOT_CODE] = 8
    px = L.pack_atlas(A2)
    OFF_PAK_REC, PIX_OFF = 0x58431, 0x44C
    d[base + OFF_PAK_REC + PIX_OFF:base + OFF_PAK_REC + PIX_OFF + len(px)] = px

    # ---- ATR 人名非法间隔号 0xB7 → 0x99 ----
    names = T.img_names(d, 19175)
    nfix = 0
    for i, nm in enumerate(names):
        if not nm.upper().endswith('.ATR'):
            continue
        ee = struct.unpack_from('<12I', d, 19175 * 2048 + TAB_OFF + TAB_STEP * i)
        off, stored = ee[E_OFF], ee[E_STORED]
        if not off or not stored:
            continue
        b = 19175 * 2048 + off
        seg = bytes(d[b:b + stored])
        if b'\xb7' in seg:
            d[b:b + stored] = seg.replace(b'\xb7', bytes([DOT_CODE]))
            nfix += 1
    print('[atr ] 间隔号 0xB7 → 0x99: 修正 %d 个 .ATR' % nfix)

    cf = lzo_compress(bytes(ft))
    tail = fblob[8 + frecs[0][1]:consumed]
    new_fblob = struct.pack('<II', len(cf), len(ft)) + cf + tail
    assert len(new_fblob) <= FT_SLOT - 8, 'FONT.RES 重压超槽'
    d[base + e[E_OFF]:base + e[E_OFF] + len(new_fblob)] = new_fblob
    print('      FONT.RES 重压 %d B (槽 %d, 余 %d)' % (len(new_fblob), FT_SLOT, FT_SLOT - len(new_fblob)))
    open(dst, 'wb').write(bytes(d))
    print('[iso ]', dst)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
