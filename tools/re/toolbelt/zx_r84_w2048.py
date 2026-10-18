# -*- coding: utf-8 -*-
r"""zx_r84_w2048.py — round84：**W=2048 单变量实验盘**（Lead 裁定批准，round 123/124）

    python tools/re/toolbelt/zx_r84_w2048.py <src.iso> <dst.iso> [--dry-run]

★ 唯一的变量 = 图集**宽度 1024 → 2048**（h 保持 512，一个字节都不动）
  ① 记录 +0x01C  W     1024 → 2048
  ② 记录 +0x43C  px_size 0x40010 → 0x80010
  ③ 像素容器：8 段（段数不变！）每段数据 0x8000 → 0x10000（64 行 × 2048px@4bpp = 1024 B/行）
     · 段首行 SSAY 仍 0/64/128/…/448（行的物理位置不变）
     · IMG tag nloop 2048 → 4096（= 段字节 / 16）
     · 旧像素放在每行的**左半**（x=0..1023），右半填 0x11（调色板 1 = 透明）
  ④ COMMON.PAK 变长 +262,144 ⇒ MENU.IMG 内其后的全部条目 off 顺移（名字区/4096 槽表不动）
  ⑤ MENU.IMG 头部 size 同步；ISO9660 目录记录长度由 iso_tools.safe_rebuild 更新
  ⑥ **不动**：h / FONT.RES 内容 / ELF / charset / 文本 / 名字区 / 4096 槽哈希表

产出 work/builds/GR_ZH98/temp/r84/w2048_report.json
"""
import argparse
import io
import json
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np          # noqa: E402
import tcslib               # noqa: E402
import zx_lib               # noqa: E402
import iso_tools            # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r84')
os.makedirs(OUT, exist_ok=True)
W_OLD, W_NEW = 1024, 2048
H = 512
SEG_ROWS = 64
SEG_DATA_NEW = (W_NEW // 2) * SEG_ROWS        # 0x10000
EMPTY = 0x11                                  # 调色板索引 1 = 透明
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def build_container(old_ct, segs):
    """旧容器(1024 宽, 8 段) → 新容器(2048 宽, 8 段)。

    ★ GIFTAG IMG 的 `NLOOP` 是 **16 字节单位**（`atlas_container_segments` 用 `nloop*16` 当字节数）。
      旧: 段数据 32,768 B ⇒ nloop = 32768/16 = 2048 ✓（与盘上实测一致）
      新: 段数据 65,536 B ⇒ nloop = 65536/16 = **4096**
    """
    out = bytearray()
    for k, (first_row, doff, nb) in enumerate(segs):
        pre = bytearray(old_ct[doff - 48:doff])
        nloop_old = struct.unpack_from('<I', pre, 32)[0] & 0x7FFF
        assert nloop_old == nb // 16, (k, nloop_old, nb)
        nloop_new = SEG_DATA_NEW // 16
        struct.pack_into('<I', pre, 32,
                         (struct.unpack_from('<I', pre, 32)[0] & ~0x7FFF) | nloop_new)
        out += pre
        seg = bytearray(b'\x11' * SEG_DATA_NEW)
        rowbytes_old = W_OLD // 2
        rowbytes_new = W_NEW // 2
        nrow = nb // rowbytes_old
        for j in range(nrow):
            src = doff + j * rowbytes_old
            dst = j * rowbytes_new
            seg[dst:dst + rowbytes_old] = old_ct[src:src + rowbytes_old]
        out += seg
        P('  [ct] seg%d 首行=%3d 数据 %d→%d B ; IMG nloop %d→%d (=数据/16)'
          % (k, first_row, nb, SEG_DATA_NEW, nloop_old, nloop_new))
    out += old_ct[-16:]                       # 尾部 no-op GIFTAG
    return bytes(out)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', default=os.path.join(OUT, 'w2048_report.json'))
    a = ap.parse_args(argv)
    P('=' * 80)
    P('zx_r84_w2048.py  ★ 单变量: 图集 W 1024 → 2048（h 不动）')
    P('  src = %s' % a.src)
    P('  dst = %s' % (a.dst or '(dry-run)'))
    P('=' * 80)

    iso = tcslib.Iso(a.src)
    names = []
    for i in range(2000):
        e = iso.img_entry(zx_lib.MENU_LBA, i)
        if e['name'].startswith('?'):
            break
        names.append(e['name'])
    e_pak = iso.img_entry(zx_lib.MENU_LBA, names.index('COMMON.PAK'))
    e_ft = iso.img_entry(zx_lib.MENU_LBA, names.index('FONT.RES'))
    names0 = zx_lib.names_region(iso, zx_lib.MENU_LBA)
    hash0 = zx_lib.hash_region(iso, zx_lib.MENU_LBA)
    pak = bytearray(iso.read(e_pak['iso_off'], e_pak['stored']))
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    P('[img] COMMON.PAK #%d off=0x%X stored=%d ; FONT.RES #%d off=0x%X stored=%d'
      % (names.index('COMMON.PAK'), e_pak['off'], e_pak['stored'],
         names.index('FONT.RES'), e_ft['off'], e_ft['stored']))
    assert (e_pak['off'], e_pak['stored']) == (0x57400, 400659)
    assert (e_ft['off'], e_ft['stored'], e_ft['real']) == (0xB9120, 4421, 7222)

    recs = tcslib.parse_pak_records(bytes(pak))
    nm, psm, aw, ah, clut, px_size, PX = recs[1]
    assert (nm, psm, aw, ah, px_size) == ('new_font_revised', 0x14, W_OLD, H, 0x40010)
    old_ct = bytes(pak[PX:PX + px_size])
    segs = zx_lib.seg_table(old_ct, W_OLD)
    P('[ct ] 旧容器 %d B ; %d 段 ; 段数据 %s'
      % (px_size, len(segs), [s[2] for s in segs]))
    assert len(segs) == 8

    new_ct = build_container(old_ct, segs)
    new_px = len(new_ct)
    P('[ct ] 新容器 %d B (Δ %+d) ; px_size 0x%X' % (new_px, new_px - px_size, new_px))
    assert new_px == 8 * 48 + 8 * SEG_DATA_NEW + 16, new_px

    # ── PAK: 替换容器 + 改两个字段 ──
    # ★ 字段位置由解析器自身给出（不手推）:
    #   记录格式 {u32 type}{u32 nameLen}{name}{u32 psm}{u32 w}{u32 h}{u32 clut}{clut}{u32 px}{px}
    #   q = p+8+nl  ⇒ psm@q, w@q+4, h@q+8, clut@q+12, px_size@q+16+clut, 像素@q+20+clut
    #   本记录: p=0x1031, q=0x1049 ⇒ psm+0x18, w+0x1C, h+0x20, clut+0x24, px_size+0x438, px+0x43C
    rec_off = PX - 0x43C                       # 记录起点在 PAK 里的绝对偏移
    pxsz_off = rec_off + 0x438                 # px_size 字段绝对偏移
    P('[pak] 记录起点 @PAK+0x%X (+0x1C=W, +0x438=px_size, +0x43C=像素)' % rec_off)
    assert rec_off == 0x1031, hex(rec_off)
    assert struct.unpack_from('<I', pak, rec_off)[0] == 0          # type
    assert struct.unpack_from('<I', pak, rec_off + 4)[0] == 16     # nameLen
    w_now = struct.unpack_from('<I', pak, rec_off + 0x1C)[0]
    px_now = struct.unpack_from('<I', pak, pxsz_off)[0]
    h_now = struct.unpack_from('<I', pak, rec_off + 0x20)[0]
    psm_now = struct.unpack_from('<I', pak, rec_off + 0x18)[0]
    P('[pak] 回读: psm=0x%X W=%d h=%d px_size=0x%X @PAK+0x%X'
      % (psm_now, w_now, h_now, px_now, pxsz_off))
    assert (psm_now, w_now, h_now, px_now) == (0x14, W_OLD, H, 0x40010)

    new_pak = bytearray(pak[:PX] + new_ct + pak[PX + px_size:])
    struct.pack_into('<I', new_pak, rec_off + 0x1C, W_NEW)
    struct.pack_into('<I', new_pak, pxsz_off, new_px)
    psm2 = struct.unpack_from('<I', new_pak, rec_off + 0x18)[0]
    h2 = struct.unpack_from('<I', new_pak, rec_off + 0x20)[0]
    c2 = struct.unpack_from('<I', new_pak, rec_off + 0x24)[0]
    assert (psm2, h2, c2) == (0x14, H, 1040), (hex(psm2), h2, c2)
    P('[pak] 新 PAK %d B (Δ %+d)' % (len(new_pak), len(new_pak) - len(pak)))

    # 其余三个记录必须逐字节不变
    tail_old = bytes(pak[PX + px_size:])
    tail_new = bytes(new_pak[PX + new_px:])
    P('[pak] 容器之后的 %d B 逐字节不变: %s' % (len(tail_old), tail_old == tail_new))
    assert tail_old == tail_new

    # ── MENU.IMG: 换 PAK + 后移其后的条目 off ──
    MENU_SIZE = 58300882
    delta = len(new_pak) - len(pak)
    img = bytearray(iso.mm[zx_lib.MENU_LBA * 2048: zx_lib.MENU_LBA * 2048 + MENU_SIZE])
    assert len(img) == MENU_SIZE
    old_off = e_pak['off']
    new_img = bytearray(img[:old_off]) + new_pak + bytearray(img[old_off + len(pak):])
    # 所有 off > old_off 的条目 off += delta
    n_moved = 0
    for i in range(len(names)):
        to = 0x830 + 48 * i
        off = struct.unpack_from('<I', new_img, to + 32)[0]
        if off > old_off:
            struct.pack_into('<I', new_img, to + 32, off + delta)
            n_moved += 1
    # ★ COMMON.PAK 自己的 stored 也要更新（iso_tools 只改 ISO9660 目录记录，不改 IMG 表）
    pak_idx = names.index('COMMON.PAK')
    to_pak = 0x830 + 48 * pak_idx
    struct.pack_into('<I', new_img, to_pak + 24, len(new_pak))
    P('[img] COMMON.PAK 表 stored %d → %d (@IMG+0x%X)'
      % (e_pak['stored'], len(new_pak), to_pak + 24))
    assert struct.unpack_from('<I', new_img, to_pak + 32)[0] == old_off, 'PAK off 不应变'
    assert len(new_pak) == e_pak['stored'] + delta
    P('[img] MENU.IMG %d → %d B (Δ %+d) ; 后移条目 %d 个' % (len(img), len(new_img), delta, n_moved))
    new_ft_off = e_ft['off'] + delta
    P('[img] FONT.RES 新 off = 0x%X → 0x%X' % (e_ft['off'], new_ft_off))
    # 头部 size 同步
    struct.pack_into('<I', new_img, 0, len(new_img))
    # 名字区 / 4096 槽表 必须逐字节不变
    assert bytes(new_img[53808:65350]) == names0, '名字区被动了'
    assert bytes(new_img[37424:37424 + 16384]) == hash0, '4096 槽哈希表被动了'
    P('[img] 名字区 / 4096 槽哈希表 逐字节不变 ✓')
    # FONT.RES 槽逐字节不变
    assert bytes(new_img[new_ft_off:new_ft_off + e_ft['stored']]) == ft_slot, 'FONT.RES 槽被动了'
    P('[img] FONT.RES 槽 (%d B) 逐字节不变 ✓' % e_ft['stored'])

    if a.dry_run:
        P('[dry-run] 不写盘')
        _save(a, dict(dry=True, ct_old=px_size, ct_new=new_px, pak_new=len(new_pak),
                      menu_new=len(new_img)))
        return 0

    # ── 写盘：ISO 重建（MENU.IMG 变大 ⇒ LBA 不动、文件变长）──
    iso.close()
    # ★ iso_tools.IsoImage 的路径键带 ISO9660 版本后缀 `;1`
    P('[iso] safe_rebuild: 只替换 MENU.IMG 内容（LBA 全部不动）')
    n = iso_tools.safe_rebuild(a.src, a.dst, replace={'MENU.IMG;1': bytes(new_img)}, verbose=True)
    assert 'MENU.IMG;1' in n, sorted(n)
    P('[iso] 尺寸 %d → %d (Δ %+d)' % (os.path.getsize(a.src), os.path.getsize(a.dst),
                                      os.path.getsize(a.dst) - os.path.getsize(a.src)))
    # 回读断言
    iso2 = tcslib.Iso(a.dst)
    assert zx_lib.names_region(iso2, zx_lib.MENU_LBA) == names0
    assert zx_lib.hash_region(iso2, zx_lib.MENU_LBA) == hash0
    e2 = iso2.img_entry(zx_lib.MENU_LBA, names.index('COMMON.PAK'))
    e2f = iso2.img_entry(zx_lib.MENU_LBA, names.index('FONT.RES'))
    P('[A6] 回读 PAK stored %d == %d ; FONT.RES off 0x%X == 0x%X'
      % (e2['stored'], len(new_pak), e2f['off'], new_ft_off))
    assert e2['stored'] == len(new_pak) and e2f['off'] == new_ft_off
    pak2 = bytes(iso2.read(e2['iso_off'], e2['stored']))
    assert pak2 == bytes(new_pak), 'PAK 回读不一致'
    ft2 = bytes(iso2.read(e2f['iso_off'], e2f['stored']))
    assert ft2 == ft_slot, 'FONT.RES 回读不一致'
    # 字段回读
    ct2 = pak2[e2['stored'] - 0:] if False else pak2
    rr = tcslib.parse_pak_records(pak2)
    nm2, psm2b, w2, h2b, clut2, px2, pxoff2 = rr[1]
    P('[A7] 回读记录: %s psm=0x%X W=%d h=%d clut=%d px_size=0x%X'
      % (nm2, psm2b, w2, h2b, clut2, px2))
    assert (psm2b, w2, h2b, clut2, px2) == (0x14, W_NEW, H, 1040, new_px)
    # 逐 texel：新容器左半 == 旧容器（引擎口径）
    img_old, cov_old = zx_lib.decode_engine(old_ct, W_OLD, H)
    img_new, cov_new = zx_lib.decode_engine(pak2[pxoff2:pxoff2 + px2], W_NEW, H)
    same = bool((img_new[:, :W_OLD] == img_old).all())
    P('[A8] 新容器左半 (0..%d) 逐 texel == 旧容器: %s ; 右半是全空: %s'
      % (W_OLD, same, not img_new[:, W_OLD:].any()))
    assert same and not img_new[:, W_OLD:].any()
    iso2.close()
    _save(a, dict(dry=False, ct_old=px_size, ct_new=new_px, pak_new=len(new_pak),
                  menu_new=len(new_img), n_moved=n_moved, same_left=same))
    return 0


def _save(a, extra):
    with io.open(a.report, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(extra=extra, log=LOG), f, ensure_ascii=False, indent=1)
    P('[out] %s' % a.report)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
