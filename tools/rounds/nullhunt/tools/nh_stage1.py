# -*- coding: utf-8 -*-
r"""nh_stage1.py — 侦察: ISO9660 树 + IMG 头 + 条目表锚点自证 (只读)

用法: python nh_stage1.py
输出: work/builds/GR_NULLHUNT/evidence/stage1_iso_tree.txt
      work/builds/GR_NULLHUNT/evidence/stage1_img_head.txt
"""
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(N.EVID, exist_ok=True)


def main():
    iso_tree = io.StringIO()
    img_head = io.StringIO()

    for tag in ('ZH113b', 'ZH113b_fix', 'EN_ORIG'):
        iso = N.Iso(N.ISO[tag])
        pv = iso.pvd()
        iso_tree.write('=' * 100 + '\n')
        iso_tree.write('%s  %s\n' % (tag, iso.path))
        iso_tree.write('  file=%s B  sectors=%s\n' % (N.fmt(iso.size), N.fmt(iso.sectors)))
        iso_tree.write('  PVD vol_size(LE)=%s  vol_size(BE)=%s  root_lba=%s root_size=%s\n'
                       % (N.fmt(pv['vol_size']), N.fmt(pv['vol_size_be']),
                          N.fmt(pv['root_lba']), N.fmt(pv['root_size'])))
        iso_tree.write('  path_table lba=%s size=%s\n'
                       % (N.fmt(pv['path_lba']), N.fmt(pv['path_size'])))
        files = iso.files()
        for p in sorted(files, key=lambda k: files[k]['lba']):
            f = files[p]
            end = f['lba'] * N.SEC + f['size']
            iso_tree.write('  %-40s LBA=%-8d size=%-12s flags=%d end_byte=%-12s dual_ok=%s\n'
                           % (p, f['lba'], N.fmt(f['size']), f['flags'], N.fmt(end),
                              f['dual_ok']))
            if not f['dual_ok']:
                iso_tree.write('      !! 双端序不一致: ext_be=%d sz_be=%d (LE ext=%d sz=%d)\n'
                               % (f['ext_be'], f['sz_be'], f['lba'], f['size']))
        iso.close()

    # ---- IMG 头 + 锚点自证 ----
    for tag in ('ZH113b', 'ZH113b_fix', 'EN_ORIG'):
        iso = N.Iso(N.ISO[tag])
        files = iso.files()
        for p, f in sorted(files.items(), key=lambda kv: kv[1]['lba']):
            if not p.upper().endswith('.IMG'):
                continue
            lba = f['lba']
            hdr = iso.img_header(lba)
            names = iso.img_names(lba, hdr)
            img_head.write('=' * 100 + '\n')
            img_head.write('%s  %s  (ISO9660 declared LBA=%d size=%s)\n'
                           % (tag, p, lba, N.fmt(f['size'])))
            img_head.write('  header u32[0..11] @+0x00: %s\n'
                           % ' '.join('%d' % v for v in hdr['raw']))
            img_head.write('    size(h0)=%s names_end(h1)=0x%X sector(h2)=%s tbl_end(h3)=0x%X\n'
                           % (N.fmt(hdr['size']), hdr['names_end'], hdr['sector'], hdr['tbl_end']))
            img_head.write('    names_start(h4)=0x%X data_start(h5)=%s h8=0x%X h9=%s h10=%s h11=%s\n'
                           % (hdr['names_start'], hdr['data_start'], hdr['h8'],
                              hdr['h9'], hdr['h10'], hdr['h11']))
            img_head.write('  名字区: start=0x%X end=0x%X len=%s  条目数(按 \\0 分割非空)=%d\n'
                           % (hdr['names_start'], hdr['names_end'],
                              N.fmt(hdr['names_end'] - hdr['names_start']), len(names)))
            tbl_end_calc = N.TAB_OFF + N.TAB_STEP * len(names)
            img_head.write('  推算条目表末尾 = 0x830 + 48*%d = 0x%X  (头部 h3=0x%X %s)\n'
                           % (len(names), tbl_end_calc, hdr['tbl_end'],
                              'OK' if tbl_end_calc == hdr['tbl_end'] else
                              'MISMATCH d=%d' % (hdr['tbl_end'] - tbl_end_calc)))
            img_head.write('  名字区起点 0x%X %s 表末尾(0x%X)\n'
                           % (hdr['names_start'], '>= ' if hdr['names_start'] >= tbl_end_calc else '< !!',
                              tbl_end_calc))
            # 条目数 vs 声明长度 覆盖检查
            ents, _h, _n = iso.img_entries(lba, len(names))
            maxend = max((e['off'] + e['stored']) for e in ents)
            minoff = min((e['off']) for e in ents if e['off'])
            img_head.write('  条目数据区: min off=%s  max(off+stored)=%s  ISO 声明 size=%s (%s)\n'
                           % (N.fmt(minoff), N.fmt(maxend), N.fmt(f['size']),
                              'COVERED' if maxend <= f['size'] else
                              '!! OVERFLOW by %s' % N.fmt(maxend - f['size'])))
            avail = iso.size - lba * N.SEC
            img_head.write('  物理可用 = %s B (%s 扇区);  ISO 声明 size = %s ⇒ 头room %s B\n'
                           % (N.fmt(avail), N.fmt(avail // N.SEC), N.fmt(f['size']),
                              N.fmt(avail - f['size'])))
            img_head.write('  前 8 个名字: %s\n' % names[:8])
        iso.close()

    # ---- 锚点自证: COMMON.PAK / FONT.RES ----
    img_head.write('\n' + '=' * 100 + '\n锚点自证 (任务书给定): COMMON.PAK stored==real==400659 ; FONT.RES stored=4421 real=7222\n')
    for tag in ('ZH113b', 'ZH113b_fix', 'EN_ORIG'):
        iso = N.Iso(N.ISO[tag])
        files = iso.files()
        mi = [f for p, f in files.items() if p.upper().endswith('MENU.IMG')][0]
        ents, hdr, names = iso.img_entries(mi['lba'], None)
        img_head.write('-' * 80 + '\n%s MENU.IMG @LBA %d 条目数=%d\n' % (tag, mi['lba'], len(ents)))
        for want in ('COMMON.PAK', 'FONT.RES'):
            for e in ents:
                if e['name'] == want:
                    img_head.write('   %-12s idx=%-4d off=%-10s stored=%-10s real=%-10s '
                                   'raw0=0x%X raw[1..5]=%s raw[9..11]=%s\n'
                                   % (want, e['idx'], N.fmt(e['off']), N.fmt(e['stored']),
                                      N.fmt(e['real']), e['nameoff'], e['raw'][1:6],
                                      e['raw'][9:12]))
        # 名字偏移自证
        e0 = ents[0]
        nm_off = hdr['names_start'] + e0['nameoff'] if e0['nameoff'] < 0x100000 else e0['nameoff']
        probe = bytes(iso.mm[hdr['base'] + e0['nameoff']:hdr['base'] + e0['nameoff'] + 40]) \
            if e0['nameoff'] < 0x200000 else b''
        img_head.write('   [自证] 条目0 name=%r raw[0](名字偏移)=0x%X; 容器内该偏移处字节=%r\n'
                       % (e0['name'], e0['nameoff'], probe[:32]))
        img_head.write('   [自证] names_start=0x%X + raw[0]=0x%X = 0x%X ⇒ 该处=%r\n'
                       % (hdr['names_start'], e0['nameoff'], hdr['names_start'] + e0['nameoff'],
                          bytes(iso.mm[hdr['base'] + hdr['names_start'] + e0['nameoff']:
                                       hdr['base'] + hdr['names_start'] + e0['nameoff'] + 32])))
        iso.close()

    with open(os.path.join(N.EVID, 'stage1_iso_tree.txt'), 'w', encoding='utf-8') as f:
        f.write(iso_tree.getvalue())
    with open(os.path.join(N.EVID, 'stage1_img_head.txt'), 'w', encoding='utf-8') as f:
        f.write(img_head.getvalue())
    print(iso_tree.getvalue())
    print(img_head.getvalue())


if __name__ == '__main__':
    main()
