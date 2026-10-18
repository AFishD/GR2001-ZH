# -*- coding: utf-8 -*-
r"""thr_patch_atlas.py -- round86 general atlas geometry probe (arbitrary w/h, ISO grow OK)

    python tools/re/toolbelt/thr_patch_atlas.py <src.iso> <dst.iso> --w 1024 --h 640
                                        [--real-mode fixed|skip] [--seg-data 0x8000]
                                        [--force-menu-size N] [--force-vol N] [--dry-run]

Base = `work\builds\GR_ZH124\GR_ZH124.iso` (191 screenshots on real hardware OK).

The only variable is w / h of `new_font_revised`; everything else below is the
mechanically necessary consequence:

  * record +0x01C w / +0x020 h
  * record +0x438 px_size = nseg*48 + payload + 16
  * INVARIANT #2: px_size == w*h/2 + 16, and the nseg*48 segment headers are
    CARVED OUT of the pixel area (payload = w*h/2 - nseg*48).
    Equivalent test: (w*h/2) % 2048 == 0.
    Violating it makes the engine hang on the memory-card screen.
  * pixel container: nseg = ceil(h / (seg_data/(w/2))), each segment
    48 B header + <=seg_data bytes; the old 512 rows (x < 1024) are copied
    byte-for-byte, new area filled with 0x11
  * INVARIANT #1: COMMON.PAK entry stored(+24) AND real(+28) must be synced.
    Updating only `stored` truncates the engine read stream at PAK+real(old)
    which looks like "container got bigger -> stall" (the historic probe bug).
  * 682 off fields shifted by +delta; MENU.IMG declared size / ISO9660 dir
    record / PVD volume size updated only when needed

NOT touched: psm / clut+1040 B palette / record names / record count / FONT.RES /
ELF / charset / text / names region / IMG +0x20 4096-slot hash table / chain sentinel.
"""
import argparse
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'tools', 'text_csv')))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

REPO = zx_lib.REPO
SEC = 2048
MENU_LBA = tcslib.MENU_LBA
SEG_DATA_MAX = 0x8000
SEG_HEAD_BYTES = 48
EMPTY = 0x11
TAIL_BYTES = 16
OUT = os.path.join(REPO, 'work', 'builds', 'GR_THR86')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def pvd_vol(iso):
    pvd = iso.read(16 * SEC, SEC)
    return (struct.unpack_from('<I', pvd, 80)[0], struct.unpack_from('>I', pvd, 84)[0],
            16 * SEC + 80, 16 * SEC + 84)


def root_dir(iso):
    pvd = iso.read(16 * SEC, SEC)
    root = pvd[156:156 + 34]
    return (struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0])


def find_menu_record(iso):
    rl_lba, rl_len = root_dir(iso)
    d = iso.read(rl_lba * SEC, rl_len)
    i = 0
    while i < len(d):
        L = d[i]
        if L == 0:
            i = (i // SEC + 1) * SEC
            if i >= len(d):
                break
            continue
        rec = d[i:i + L]
        nm = rec[33:33 + rec[32]].decode('latin-1')
        if nm.upper().startswith('MENU'):
            return (rl_lba * SEC + i, nm, struct.unpack_from('<I', rec, 10)[0],
                    struct.unpack_from('>I', rec, 14)[0])
        i += L
    raise AssertionError('root dir has no MENU.IMG')


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--w', type=int, required=True)
    ap.add_argument('--h', type=int, required=True)
    ap.add_argument('--real-mode', default='fixed', choices=['fixed', 'skip'])
    ap.add_argument('--seg-data', type=int, default=SEG_DATA_MAX)
    ap.add_argument('--force-menu-size', type=int, default=0)
    ap.add_argument('--force-vol', type=int, default=0)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', default=None)
    a = ap.parse_args(argv)
    if not a.report:
        a.report = os.path.join(OUT, 'patch_%dx%d_%s_report.json' % (a.w, a.h, a.real_mode))
    P('=' * 78)
    P('thr_patch_atlas.py  atlas geometry probe %dx%d ; real-mode=%s ; seg-data=0x%X'
      % (a.w, a.h, a.real_mode, a.seg_data))
    P('=' * 78)

    iso = tcslib.Iso(a.src)
    vol_le, vol_be, vol_off_le, vol_off_be = pvd_vol(iso)
    m_abs, m_name, m_len_le, m_len_be = find_menu_record(iso)
    hdr = zx_lib.header(iso, MENU_LBA)
    names0 = zx_lib.names_region(iso, MENU_LBA)
    hash0 = zx_lib.hash_region(iso, MENU_LBA)
    ents = zx_lib.entries(iso, MENU_LBA)
    e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
    P('[iso] %d B = %d sect ; PVD vol %d ; MENU rec @0x%X len %d/%d'
      % (iso.size, iso.size // SEC, vol_le, m_abs, m_len_le, m_len_be))
    assert vol_le == vol_be == iso.size // SEC
    assert m_len_le == m_len_be == hdr['size']
    P('[img] IMG size %d ; entries %d ; names %d..%d ; hash@0x%X'
      % (hdr['size'], len(ents), hdr['names_start'], hdr['names_end'], hdr['hash_off']))
    P('[img] COMMON.PAK #%d off=0x%X stored=%d real=%d ; FONT.RES #%d off=0x%X stored=%d real=%d'
      % (e_pak['idx'], e_pak['off'], e_pak['stored'], e_pak['real'], e_ft['idx'], e_ft['off'],
         e_ft['stored'], e_ft['real']))
    assert (e_pak['off'], e_pak['stored'], e_pak['real']) == (0x57400, 400659, 400659)

    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = tcslib.parse_pak_records(pak)
    assert len(recs) == 4 and recs[1][0] == 'new_font_revised'
    nm, psm, W_OLD, H_OLD, clut, CT_OLD, px_off = recs[1]
    assert (psm, W_OLD, H_OLD, clut, CT_OLD) == (0x14, 1024, 512, 1040, 0x40010)
    assert px_off == 0x146D
    rec_off = px_off - 0x43C
    h_bytes = bytes(pak[rec_off + 0x20:rec_off + 0x24])
    pal_bytes = bytes(pak[rec_off + 0x28:rec_off + 0x438])
    name_bytes = bytes(pak[rec_off:rec_off + 0x18])
    ct_old = bytes(pak[px_off:px_off + CT_OLD])

    # ---- old container -> row map (engine view: TRXPOS first row + rows inside segment) ----
    segs_old = [s for s in tcslib.atlas_container_segments(ct_old, W_OLD // 2) if s[2] > 0]
    rw_old = W_OLD // 2
    rowmap = {}
    for (row0, doff, nb) in segs_old:
        nfull = nb // rw_old
        for i in range(nfull):
            rowmap[row0 + i] = ct_old[doff + i * rw_old:doff + (i + 1) * rw_old]
        rest = nb - nfull * rw_old
        if rest:
            rowmap[row0 + nfull] = ct_old[doff + nfull * rw_old:doff + nb]
    P('[ct ] old container %d B (0x%X) ; %d segs ; rowmap %d rows (last row %d B)'
      % (CT_OLD, CT_OLD, len(segs_old), len(rowmap), len(rowmap[max(rowmap)])))

    # ---- new container ----
    rw_new = a.w // 2
    seg_rows = a.seg_data // rw_new
    assert seg_rows > 0
    nseg = (a.h + seg_rows - 1) // seg_rows
    CT_NEW = a.w * a.h // 2 + TAIL_BYTES
    payload = CT_NEW - nseg * SEG_HEAD_BYTES - TAIL_BYTES
    assert payload > 0 and payload % 16 == 0, (payload, nseg)
    P('[ct ] px_size invariant: w*h/2 + 16 = %d + 16 = **%d** ; %d seg-heads %d B carved out'
      ' => payload %d B (%.4f rows) ; (w*h/2) %% 2048 = %d'
      % (a.w * a.h // 2, CT_NEW, nseg, nseg * SEG_HEAD_BYTES, payload,
         payload / float(rw_new), (a.w * a.h // 2) % 2048))
    head_tpl = bytearray(ct_old[0:48])
    tail = bytes(ct_old[CT_OLD - TAIL_BYTES:])
    assert tail[:4] == b'\x00\x80\x00\x00'
    body = bytearray()
    segs_new = []
    off = 0
    for k in range(nseg):
        row0 = k * seg_rows
        want = min(a.seg_data, payload - off)
        assert want > 0 and want % 16 == 0, (k, want, off, payload)
        head = bytearray(head_tpl)
        struct.pack_into('<I', head, 16, 0)
        struct.pack_into('<I', head, 20, row0)
        struct.pack_into('<Q', head, 24, 0x52)
        struct.pack_into('<I', head, 32, (want // 16) | 0x8000)
        struct.pack_into('<I', head, 36, 0x08000000)
        segs_new.append(dict(k=k, first_row=row0, doff=len(body) + SEG_HEAD_BYTES, nb=want,
                             nloop=want // 16))
        body += head
        nrow = want // rw_new
        rest = want - nrow * rw_new
        for i in range(nrow):
            row = bytearray(b'\x11' * rw_new)
            old = rowmap.get(row0 + i, b'')
            n = min(len(old), rw_new)
            row[0:n] = old[0:n]
            body += row
        if rest:
            row = bytearray(b'\x11' * rw_new)
            old = rowmap.get(row0 + nrow, b'')
            n = min(len(old), rest)
            row[0:n] = old[0:n]
            body += row[0:rest]
        off += want
    assert off == payload, (off, payload)
    body += tail
    ct_new = bytes(body)
    assert len(ct_new) == CT_NEW, (len(ct_new), CT_NEW)
    delta = CT_NEW - CT_OLD
    P('[ct ] new container %d B (0x%X) ; %d segs ; rows/seg %d ; delta = **%+d B**'
      % (CT_NEW, CT_NEW, nseg, seg_rows, delta))
    for s in segs_new:
        P('       seg%-2d first_row=%-4d nloop=%-5d nb=%-6d' % (s['k'], s['first_row'],
                                                                s['nloop'], s['nb']))
    chk = [s for s in tcslib.atlas_container_segments(ct_new, rw_new) if s[2] > 0]
    assert len(chk) == nseg and [s[0] for s in chk] == [s['first_row'] for s in segs_new]
    assert [s[2] for s in chk] == [s['nb'] for s in segs_new]
    assert sum(s[2] for s in chk) == payload
    P('[ct ] readback seg table OK ; pixels total %d == payload = w*h/2 - %d*48 = %d'
      % (sum(s[2] for s in chk), nseg, payload))
    bad = 0
    ndone = 0
    for (row0, doff, nb) in chk:
        for i in range(nb // rw_new):
            y = row0 + i
            old = rowmap.get(y)
            if old is None:
                continue
            ndone += 1
            new = ct_new[doff + i * rw_new:doff + i * rw_new + len(old)]
            if new != old:
                bad += 1
    P('[ct ] old pixels preserved row-by-row: %d rows checked, %d mismatch %s'
      % (ndone, bad, 'OK' if bad == 0 else 'FAIL'))
    assert bad == 0

    # ---- new PAK ----
    nb_ = bytearray(pak[:px_off])
    struct.pack_into('<I', nb_, rec_off + 0x1C, a.w)
    struct.pack_into('<I', nb_, rec_off + 0x20, a.h)
    struct.pack_into('<I', nb_, px_off - 4, CT_NEW)
    nb_ += ct_new
    nb_ += pak[px_off + CT_OLD:]
    new_pak = bytes(nb_)
    assert len(new_pak) - len(pak) == delta
    r2 = tcslib.parse_pak_records(new_pak)
    assert [r[0] for r in r2] == [r[0] for r in recs]
    assert (r2[1][2], r2[1][3], r2[1][5]) == (a.w, a.h, CT_NEW)
    assert bytes(new_pak[rec_off:rec_off + 0x18]) == name_bytes
    assert bytes(new_pak[rec_off + 0x28:rec_off + 0x438]) == pal_bytes
    P('[pak] new PAK %d B ; rec#1 = %dx%d px_size=0x%X ; name/palette byte-identical OK'
      % (len(new_pak), a.w, a.h, CT_NEW))

    # ---- new MENU.IMG ----
    old_end = e_pak['off'] + e_pak['stored']
    last_end = max(e['off'] + e['stored'] for e in ents)
    need = last_end + delta
    new_size = hdr['size'] if need <= hdr['size'] else ((need + SEC - 1) // SEC) * SEC
    if a.force_menu_size:
        assert a.force_menu_size >= need, 'force-menu-size too small'
        new_size = a.force_menu_size
    new_vol = max(vol_le, MENU_LBA + (new_size + SEC - 1) // SEC)
    if a.force_vol:
        assert a.force_vol >= new_vol, 'force-vol too small'
        new_vol = a.force_vol
    P('[menu] PAK end 0x%X ; last entry end %d ; +delta => need %d ; IMG size %d -> **%d** ;'
      ' sectors to %d (vol %d)%s'
      % (old_end, last_end, need, hdr['size'], new_size, new_vol, vol_le,
         ' => ISO MUST grow' if new_vol > vol_le else ' => ISO unchanged'))
    old_phys = bytes(iso.read(MENU_LBA * SEC, min(vol_le * SEC - MENU_LBA * SEC, hdr['size'])))
    new_menu = bytearray(old_phys)
    if new_size > len(new_menu):
        new_menu += b'\x00' * (new_size - len(new_menu))
    tail_data = bytes(new_menu[old_end:last_end])
    new_menu[e_pak['off']:e_pak['off'] + len(new_pak)] = new_pak
    new_menu[old_end + delta:last_end + delta] = tail_data
    struct.pack_into('<I', new_menu, 0, new_size)
    n_off = 0
    for e in ents:
        if e['off'] >= e_ft['off']:
            struct.pack_into('<I', new_menu, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 32,
                             e['off'] + delta)
            n_off += 1
        if e['idx'] == e_pak['idx']:
            struct.pack_into('<I', new_menu, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 24,
                             e['stored'] + delta)
            if a.real_mode == 'fixed':
                struct.pack_into('<I', new_menu,
                                 zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 28,
                                 e['real'] + delta)
    P('[menu] entry table: off %d entries (+%d) ; COMMON.PAK stored %d->%d ; real %s'
      % (n_off, delta, e_pak['stored'], e_pak['stored'] + delta,
         ('%d->%d SYNCED' % (e_pak['real'], e_pak['real'] + delta)) if a.real_mode == 'fixed'
         else 'UNCHANGED (bug reproduced on purpose)'))
    assert n_off == 682, n_off
    assert bytes(new_menu[hdr['names_start']:hdr['names_end']]) == names0, 'names region changed'
    assert bytes(new_menu[hdr['hash_off']:hdr['hash_off'] + 16384]) == hash0, 'hash table changed'
    exp_meta = bytearray(new_menu[0:e_pak['off']])
    for e in ents:
        if e['off'] >= e_ft['off']:
            struct.pack_into('<I', exp_meta, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 32,
                             e['off'] + delta)
        if e['idx'] == e_pak['idx']:
            struct.pack_into('<I', exp_meta, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 24,
                             e['stored'] + delta)
            if a.real_mode == 'fixed':
                struct.pack_into('<I', exp_meta, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 28,
                                 e['real'] + delta)
    assert bytes(new_menu[0:e_pak['off']]) == bytes(exp_meta), 'unplanned metadata change'
    P('[menu] metadata before PAK 0x%X B: 0 unplanned changes OK' % e_pak['off'])

    if a.dry_run:
        P('[dry ] not writing')
        _save(a, dict(dry=True, delta=delta, ct_new=CT_NEW, new_size=new_size,
                      new_vol=new_vol, nseg=nseg))
        iso.close()
        return 0

    # ---- write ----
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    with open(a.src, 'rb') as fi, open(a.dst, 'wb') as fo:
        while True:
            blk = fi.read(1 << 22)
            if not blk:
                break
            fo.write(blk)
        if new_vol > vol_le:
            fo.write(b'\x00' * ((new_vol - vol_le) * SEC))
    with open(a.dst, 'r+b') as f:
        f.seek(MENU_LBA * SEC)
        f.write(bytes(new_menu))
        f.seek(m_abs + 10)
        f.write(struct.pack('<I', new_size) + struct.pack('>I', new_size))
        if new_vol != vol_le:
            f.seek(vol_off_le)
            f.write(struct.pack('<I', new_vol) + struct.pack('>I', new_vol))
    P('[out] %s (%d B = %d sect)' % (a.dst, os.path.getsize(a.dst),
                                     os.path.getsize(a.dst) // SEC))

    # ---- readback assertions ----
    iso2 = tcslib.Iso(a.dst)
    hdr2 = zx_lib.header(iso2, MENU_LBA)
    ents2 = zx_lib.entries(iso2, MENU_LBA)
    e2 = ents2[e_pak['idx']]
    e2ft = ents2[e_ft['idx']]
    pak2 = bytes(iso2.read(e2['iso_off'], e2['stored']))
    assert pak2 == new_pak
    r3 = tcslib.parse_pak_records(pak2)
    P('[A1] readback PAK %d B ; rec#1 %dx%d psm=0x%02X clut=%d px_size=0x%X'
      % (len(pak2), r3[1][2], r3[1][3], r3[1][1], r3[1][4], r3[1][5]))
    assert (r3[1][1], r3[1][2], r3[1][3], r3[1][4], r3[1][5]) == (psm, a.w, a.h, clut, CT_NEW)
    ct2 = pak2[r3[1][6]:r3[1][6] + r3[1][5]]
    s2 = [s for s in tcslib.atlas_container_segments(ct2, rw_new) if s[2] > 0]
    P('[A2] readback container %d B ; %d segs ; first rows %s' % (len(ct2), len(s2),
                                                                  [s[0] for s in s2]))
    assert len(s2) == nseg
    assert bytes(pak2[rec_off + 0x28:rec_off + 0x438]) == pal_bytes
    assert bytes(pak2[rec_off:rec_off + 0x18]) == name_bytes
    P('[A3] name / palette 1040 B byte-identical OK')
    assert bytes(pak2[rec_off + 0x20:rec_off + 0x24]) == struct.pack('<I', a.h)
    if a.h == H_OLD:
        assert bytes(pak2[rec_off + 0x20:rec_off + 0x24]) == h_bytes
    ft2 = bytes(iso2.read(e2ft['iso_off'], e2ft['stored']))
    assert ft2 == bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    assert e2ft['off'] == e_ft['off'] + delta
    P('[A4] FONT.RES byte-identical, off 0x%X -> 0x%X (+%d) OK' % (e_ft['off'], e2ft['off'], delta))
    assert zx_lib.names_region(iso2, MENU_LBA) == names0
    assert zx_lib.hash_region(iso2, MENU_LBA) == hash0
    assert hdr2['size'] == new_size
    v2, v2b, _, _ = pvd_vol(iso2)
    assert (v2, v2b) == (new_vol, new_vol)
    m2 = find_menu_record(iso2)
    assert m2[2] == m2[3] == new_size and m2[0] == m_abs
    assert os.path.getsize(a.dst) == new_vol * SEC
    P('[A5] IMG size %d OK ; ISO9660 len %d/%d OK ; PVD vol %d OK ; ISO %d sect OK'
      % (new_size, m2[2], m2[3], v2, new_vol))
    if a.real_mode == 'fixed':
        assert (e2['stored'], e2['real']) == (e_pak['stored'] + delta, e_pak['real'] + delta)
        P('[A6] COMMON.PAK entry stored %d->%d ; **real %d->%d** (+%d SYNCED) OK'
          % (e_pak['stored'], e2['stored'], e_pak['real'], e2['real'], delta))
    else:
        assert (e2['stored'], e2['real']) == (e_pak['stored'] + delta, e_pak['real'])
        P('[A6] COMMON.PAK entry stored %d->%d ; real stays %d (stored>real, bug reproduced) OK'
          % (e_pak['stored'], e2['stored'], e2['real']))
    iso2.close()
    iso.close()
    _save(a, dict(dry=False, w=a.w, h=a.h, real_mode=a.real_mode, delta=delta,
                  ct_old=CT_OLD, ct_new=CT_NEW, nseg=nseg, seg_rows=seg_rows,
                  seg_data=a.seg_data, payload=payload,
                  wh2_mod2048=(a.w * a.h // 2) % 2048,
                  pak_old=len(pak), pak_new=len(new_pak), menu_old=hdr['size'],
                  menu_new=new_size, vol_old=vol_le, vol_new=new_vol,
                  n_off_shift=n_off,
                  w_field_iso=e_pak['iso_off'] + rec_off + 0x1C,
                  h_field_iso=e_pak['iso_off'] + rec_off + 0x20,
                  px_size_field_iso=e_pak['iso_off'] + px_off - 4,
                  container_iso=e_pak['iso_off'] + px_off,
                  entry_pak_iso=e_pak['iso_off'] + zx_lib.TAB_OFF
                  + zx_lib.TAB_STEP * e_pak['idx']))
    return 0


def _save(a, extra):
    d = dict(extra=extra, log=LOG)
    os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
    with io.open(a.report, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    with io.open(os.path.splitext(a.report)[0] + '.log', 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % a.report)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
