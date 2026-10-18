# -*- coding: utf-8 -*-
r"""make_probe_r45.py — round45 探针盘: 在**引擎采样格**涂实心块, 用实机 A/B 判定 drift 真伪。

原理 (round44 查实 + 本轮复核):
  · 像素容器是 **GIF 封包流**: 每段 48B 包头 + 64 行数据 (TRXPOS.y = 0/64/…/448);
  · 引擎采样 = 引擎图 (按封包还原) 的 (16*col, yrow(row)) 格;
  · 引擎图 (x,y) ↔ 「整块当裸图」的 flat 坐标 = tcslib.atlas_flat_pos(x, y)  = x + 96*(y//64+1),
    溢出 1024 则减 1024 且 y+1。
⇒ 想让「slot(row,col) 这个字」在游戏里变成实心块, 就把 (16*col, yrow) 这个**引擎格**
   按 atlas_flat_pos 换算成 flat 格, 在那里涂 16x16 全 0 (墨)。

探针选字 (都能在实机可到的界面看到, 见 temp/r45/a2_run.log):
  · 米/毫/匣/斤/采/坐/款/扳/倍 = grid 行 19 的常用字 (武器长描述里的"毫米/弹匣/公斤/扳机"…);
  · 岩 = 任务书指定的 (row21, col10) —— 它的引擎格 (160, 386);
  · 药 = grid 行 ≤18 的**正对照**: PHI 与段错位相同 ⇒ 两种口径指向同一物理格,
    它变成块只能证明"我的 引擎格→flat 换算"没错 (不构成 drift 判据, 但可验收映射实现)。

用法:
  python tools/iso_build/make_probe_r45.py <src.iso> <dst.iso> [--chars 米毫…] [--no-json]
只读基盘, 只改 COMMON.PAK 里 new_font_revised 的像素容器 (等长覆盖, ISO 尺寸不变)。
"""
import io
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402

W, H = 1024, 512
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH
DEFAULT_CHARS = '米毫匣斤采坐款扳倍岩药虽裂钢额造题誉衍轮震衣鼓链聚延栓略挂偏'
OUT_JSON = os.path.join(REPO, 'work', 'builds', 'GR_ZH97_probe', 'temp', 'r45',
                        'probe_cells.json')


def yrow(r):
    return tcslib.GRID_Y0 + CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def main(src, dst, chars, do_json=True):
    iso = tcslib.Iso(src)
    pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
            break
    assert pak_e, '找不到 COMMON.PAK'
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    iso.close()
    rec = [r for r in tcslib.parse_pak_records(bytes(pak)) if r[0] == 'new_font_revised']
    assert len(rec) == 1, rec
    _nm, psm, w, h, clut, px_size, PX = rec[0]
    assert (psm, w, h) == (0x14, W, H), (psm, w, h)
    print('[pak] COMMON.PAK off=0x%X  图集 px_off=0x%X psm=0x%02X %dx%d' % (pak_e['iso_off'], PX, psm, w, h))

    nb = np.frombuffer(bytes(pak[PX:PX + W * H // 2]), dtype=np.uint8).reshape(H, W // 2)
    A = np.empty((H, W), dtype=np.uint8)
    A[:, 0::2] = nb & 0x0F
    A[:, 1::2] = (nb >> 4) & 0x0F
    BASE_INK = (A == 0).copy()
    print('[img] 原图墨点 %d' % int(BASE_INK.sum()))

    blob = bytes(pak[PX:PX + px_size])
    segs = tcslib.atlas_container_segments(blob, W // 2)
    print('[seg] %d 段: %s' % (len(segs), [(r, hex(o), n) for r, o, n in segs]))

    cs = tcslib.Charset()
    by_slot = {}
    for ch, (b1, b2) in cs.enc_pair.items():
        by_slot[tcslib.pair_slot(b1, b2)] = ch
    # slot -> char 反查 (含未用槽的"占位"信息)
    cell_owner = {}
    for slot, ch in by_slot.items():
        row, col = slot // NCOL, slot % NCOL
        p = col + tcslib.atlas_row_phase(row)
        cell_owner[(row, col)] = ch

    placed = []
    for ch in chars:
        assert ch in cs.enc_pair, '%s 不是对偶字 (不在 charset)' % ch
        b1, b2 = cs.enc_pair[ch]
        slot = tcslib.pair_slot(b1, b2)
        row, col = slot // NCOL, slot % NCOL
        ex, ey = CW * col, yrow(row)
        fx, fy = tcslib.atlas_flat_pos(ex, ey, W)
        ink_before = int(BASE_INK[fy:fy + CH, fx:fx + CW].sum())
        # 这个 flat 格现在是谁的字形? (按写入侧口径: 每格的字形属于 flat 列 - PHI 的槽)
        ph = tcslib.atlas_row_phase(row)
        owner_col = (fx // CW - ph) % tcslib.GRID_MOD
        owner = cell_owner.get((row, owner_col), '（未用槽/非本行）')
        A[fy:fy + CH, fx:fx + CW] = 0                       # 全 0 = 实心墨块
        placed.append(dict(char=ch, code='%02X%02X' % (b1, b2), slot=slot, row=row, col=col,
                           engine=(ex, ey), flat=(fx, fy),
                           ink_before=ink_before, prev_owner=owner))
        print('  [探针] %s  slot=%4d (row%2d col%2d) 引擎格=(%4d,%3d) → flat=(%4d,%3d)'
              '  原格墨=%3d (该格原属: %s)'
              % (ch, slot, row, col, ex, ey, fx, fy, ink_before, owner))

    NEW_INK = (A == 0)
    diff = int((BASE_INK != NEW_INK).sum())
    # 变更像素必须全落在探针格的 16x16 矩形里 (块可能跨 16 行的行界, 所以按像素核, 不按格核)
    allowed = np.zeros((H, W), dtype=bool)
    for d in placed:
        fx, fy = d['flat']
        allowed[fy:fy + CH, fx:fx + CW] = True
    outside = int(((BASE_INK != NEW_INK) & ~allowed).sum())
    assert outside == 0, '有 %d 个像素改在授权格之外' % outside
    cells = sorted({(d['flat'][0], d['flat'][1]) for d in placed})
    print('[self] 图集改动 %d 像素, 全在 %d 个探针格 (16x16) 的矩形内 ✓' % (diff, len(cells)))

    packed = ((A[:, 1::2] << 4) | A[:, 0::2]).astype(np.uint8)
    assert packed.nbytes == W * H // 2
    pak[PX:PX + packed.nbytes] = packed.tobytes()

    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(pak_e['iso_off'])
        f.write(bytes(pak))
    sz_src, sz_dst = os.path.getsize(src), os.path.getsize(dst)
    assert sz_src == sz_dst, (sz_src, sz_dst)
    print('[iso] → %s (尺寸不变 %d B)' % (dst, sz_dst))

    # 回读核对
    with open(dst, 'rb') as f:
        f.seek(pak_e['iso_off'])
        pak2 = f.read(pak_e['stored'])
    rec2 = [r for r in tcslib.parse_pak_records(pak2) if r[0] == 'new_font_revised'][0]
    nb2 = np.frombuffer(pak2[rec2[6]:rec2[6] + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
    A2 = np.empty((H, W), dtype=np.uint8)
    A2[:, 0::2] = nb2 & 0x0F
    A2[:, 1::2] = (nb2 >> 4) & 0x0F
    INK2 = (A2 == 0)
    for d in placed:
        fx, fy = d['flat']
        assert INK2[fy:fy + CH, fx:fx + CW].all(), '回读不一致 %s' % d['char']
    # 逐字节对照: 只有这些格变了
    nd = int((INK2 != BASE_INK).sum())
    assert nd == diff, (nd, diff)
    print('[ver] 回读: %d 个探针格全实心 ✓ ; 全图仅 %d 像素变化 (只在探针格) ✓' % (len(placed), nd))

    if do_json:
        io.open(OUT_JSON, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(dict(src=os.path.relpath(src, REPO), dst=os.path.relpath(dst, REPO),
                            segments=[[r, o, n] for r, o, n in segs],
                            placed=placed, pixels_changed=diff),
                       ensure_ascii=False, indent=1) + '\n')
        print('[rep] → %s' % OUT_JSON)
    return 0


if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    chs = DEFAULT_CHARS
    for x in sys.argv[1:]:
        if x.startswith('--chars='):
            chs = x.split('=', 1)[1]
    sys.exit(main(args[0], args[1], chs, do_json='--no-json' not in sys.argv))
