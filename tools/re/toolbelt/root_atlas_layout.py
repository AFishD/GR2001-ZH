# -*- coding: utf-8 -*-
r"""root_atlas_layout.py -- 逐字节解剖 new_font_revised 像素容器（READ-ONLY）。

自足实现：ISO9660 找 MENU.IMG -> IMG 头 +0x20 条目表 -> COMMON.PAK 记录链 ->
new_font_revised 记录 -> 容器。打印：
  · 记录头字段（type/nameLen/name/psm/w/h/clut_size/px_size）
  · 容器: 每 16 B 处以 GIF tag 口径 (NREG/FLG/NLOOP/EOP/PRE) 扫描，
    列出所有"结构 tag"（A+D / IMAGE）与其 payload 长度、TRXPOS 的 SSAY/DSAY
  · 与 px_size / 段数 / 1 个 NLOOP 字节数对账

用法: python tools/re/toolbelt/root_atlas_layout.py <iso> [<iso> ...]
"""
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
MENU_LBA = 776286


def img_entries(mm, lba=None):
    """mm = 从 MENU.IMG 起点开始的完整前 0x10000 字节。"""
    noff = struct.unpack_from('<I', mm, 0x10)[0]
    nend = struct.unpack_from('<I', mm, 0x04)[0]
    print('  names 区 0x%X..0x%X (%d B) ; data_start=0x%X ; size=0x%X'
          % (noff, nend, nend - noff, struct.unpack_from('<I', mm, 0x14)[0],
             struct.unpack_from('<I', mm, 0x00)[0]))
    names = [x.decode('latin-1') for x in bytes(mm[noff:nend]).split(b'\x00') if x]
    out = []
    for i, nm in enumerate(names):
        r = struct.unpack_from('<12I', mm, 0x830 + 48 * i)
        out.append(dict(name=nm, raw=list(r), stored=r[6], real=r[7], off=r[8]))
    return out


def pak_records(pak, verbose=True):
    """PAK = <u32 mode><u32 nl><name> 后接「模式体」。

    mode 0  : <u32 psm><u32 w><u32 h><u32 clut_size><clut><u32 px_size><px>
    mode 1-3: <u32 psm><u32 w><u32 h>[<u32 clut_size><clut> 仅 psm∈{0x13,0x14}]<u32 px_size><px>
    """
    p = 0
    recs = []
    while p + 8 <= len(pak):
        mode, nl = struct.unpack_from('<II', pak, p)
        if nl < 1 or nl > 64 or p + 8 + nl > len(pak):
            if verbose:
                print('  [walk] 停在 0x%X: mode=%d nl=%d（非法/哨兵）' % (p, mode, nl))
            break
        nm = pak[p + 8:p + 8 + nl].split(b'\x00')[0].decode('latin-1', 'replace')
        r = p + 8 + nl
        if mode == 0:
            psm, w, h, clut_size = struct.unpack_from('<4I', pak, r)
            q = r + 16
            clut = pak[q:q + clut_size]
            q += clut_size
            px_size, = struct.unpack_from('<I', pak, q)
            q += 4
            px = pak[q:q + px_size]
            recs.append(dict(mode=mode, name=nm, off=p, psm=psm, w=w, h=h,
                             clut_size=clut_size, clut=clut, px_size=px_size, px=px,
                             px_at=q, end=q + px_size))
            p = q + px_size
        elif mode in (1, 2, 3):
            psm, w, h = struct.unpack_from('<3I', pak, r)
            q = r + 12
            clut_size = 0
            clut = b''
            if psm in (0x13, 0x14):
                clut_size, = struct.unpack_from('<I', pak, q)
                q += 4
                clut = pak[q:q + clut_size]
                q += clut_size
            px_size, = struct.unpack_from('<I', pak, q)
            q += 4
            px = pak[q:q + px_size]
            recs.append(dict(mode=mode, name=nm, off=p, psm=psm, w=w, h=h,
                             clut_size=clut_size, clut=clut, px_size=px_size, px=px,
                             px_at=q, end=q + px_size))
            p = q + px_size
        else:
            print('  [walk] 未知 mode=%d @0x%X name=%r' % (mode, p, nm))
            break
    return recs


def taginfo(b):
    """16 B GIF tag -> (nloop, nreg, flg, nreg_field, prim, eop, pre, regs)"""
    lo, hi = struct.unpack_from('<II', b, 0)
    nloop = lo & 0x7FFF
    eop = (lo >> 15) & 1
    pre = (lo >> 46) & 1
    prim = (lo >> 47) & 0x7FF
    flg = (lo >> 58) & 3
    nreg_f = (lo >> 60) & 0xF
    regs = hi
    return dict(nloop=nloop, eop=eop, pre=pre, prim=prim, flg=flg, nreg=nreg_f, regs=regs,
                lo=lo, hi=hi)


REGS = {0x0E: 'A+D', 0x00: 'PRIM', 0x01: 'RGBAQ', 0x02: 'ST', 0x03: 'UV', 0x04: 'XYZF2',
        0x05: 'XYZ2', 0x06: 'TEX0_1', 0x07: 'TEX0_2', 0x08: 'CLAMP_1', 0x09: 'CLAMP_2',
        0x0A: 'FOG', 0x0C: 'XYZF3', 0x0D: 'XYZ3', 0x13: 'FADE', 0x14: 'PRIM', 0x53: 'CLAMP'}


def scan_container(px, w_hint=None):
    print('  容器 %d 字节 (0x%X)' % (len(px), len(px)))
    n = len(px)
    hits = []
    for off in range(0, n - 15, 16):
        t = taginfo(px[off:off + 16])
        if t['flg'] == 1 and t['regs'] == 0x0E and t['nloop'] == 1 and t['eop'] == 1:
            hits.append((off, 'A+D/TRXPOS', t))
        elif t['flg'] == 2 and t['eop'] == 1 and t['nloop'] > 1:
            hits.append((off, 'IMAGE', t))
        elif t['nloop'] == 1 and t['regs'] == 0 and t['eop'] == 1 and t['flg'] == 1:
            hits.append((off, 'other-PACKED', t))
    print('  结构 tag 命中 %d 个:' % len(hits))
    prev = None
    for (off, kind, t) in hits[:80]:
        extra = ''
        if kind == 'A+D/TRXPOS':
            # TRXPOS: bit 0..10 SSAX, 11..21 SSAY, 22..32 DSAX, 33..43 DSAY, 59 DIR
            lo2, hi2 = struct.unpack_from('<II', px, off + 16)
            ssax = lo2 & 0x7FF
            ssay = (lo2 >> 11) & 0x7FF
            dsax = (lo2 >> 32) & 0x7FF
            dsay = (lo2 >> 43) & 0x7FF
            extra = ' SSAX=%d SSAY=%d DSAX=%d DSAY=%d' % (ssax, ssay, dsax, dsay)
        elif kind == 'IMAGE':
            extra = ' NLOOP=%d -> payload %d B' % (t['nloop'], t['nloop'] * 16)
        gap = '' if prev is None else '  (Δ=%d)' % (off - prev)
        print('    0x%06X  %-13s nloop=%-6d eop=%d flg=%d nreg=0x%X%s%s'
              % (off, kind, t['nloop'], t['eop'], t['flg'], t['nreg'], extra, gap))
        prev = off
    if len(hits) > 80:
        print('    ... (%d more)' % (len(hits) - 80))
    # 每 16 B 也统计一下非零密度，找尾部
    print('  末尾 48 B: %s' % px[-48:].hex())
    print('  开头 64 B: %s' % px[:64].hex())


def main():
    for path in sys.argv[1:]:
        print('=' * 100)
        print(path)
        with open(path, 'rb') as f:
            f.seek(MENU_LBA * SEC)
            head = f.read(0x30)
            noff = struct.unpack_from('<I', head, 0x10)[0]
            nend = struct.unpack_from('<I', head, 4)[0]
            need = max(nend, 0x830 + 48 * 700)
            f.seek(MENU_LBA * SEC)
            mm = f.read(need)
            ents = img_entries(mm)
            print('  MENU.IMG 条目数 = %d' % len(ents))
            pak_e = [e for e in ents if e['name'] == 'COMMON.PAK']
            print('  COMMON.PAK entry: %s' % pak_e)
            e = pak_e[0]
            f.seek(MENU_LBA * SEC + e['off'])
            pak = f.read(e['stored'])
        recs = pak_records(pak)
        for r in recs:
            print('  rec @0x%X %-20s mode=%d psm=0x%X %dx%d clut=%d px_size=0x%X px@0x%X end=0x%X'
                  % (r['off'], r['name'], r['mode'], r['psm'], r['w'], r['h'],
                     r['clut_size'], r['px_size'], r['px_at'], r['end']))
        if recs:
            print('  PAK len=%d ; 最后记录 end=0x%X ; 尾料=%d B'
                  % (len(pak), recs[-1]['end'], len(pak) - recs[-1]['end']))
        nfr = [r for r in recs if r['name'] == 'new_font_revised']
        if nfr:
            scan_container(nfr[0]['px'], nfr[0]['w'])


main()
