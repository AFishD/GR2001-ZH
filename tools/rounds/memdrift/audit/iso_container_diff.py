# -*- coding: utf-8 -*-
r"""iso_container_diff.py — GR_ZH113b.iso vs GR_EN_ORIG.iso 的**容器层**差异 (只读)

只看三件事, 都是"引擎会当作长度/指针用"的字段:
  [1] ISO9660 目录记录里每个文件的 **声明长度** (extent size) —— 与 IMG 头里的 size 是否一致;
      MENU.IMG 的声明长度是任务书点名的改动项之一。
  [2] MENU.IMG / GR.IMG 的 **IMG 头** (size / names_end / sector / tbl_end / names_start /
      data_start / hash_off)。
  [3] 两个 IMG 的 **条目表**: name → (stored, real, off)。列出所有差异条目。
"""
import json
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                          # noqa: E402

SEC = 2048
OUT = os.path.join(REPO, 'work', 'builds', 'GR_MEMDRIFT', 'audit')

DISCS = [('ZH113b', os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')),
         ('EN_ORIG', os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))]


def iso_files(mm):
    """ISO9660: 从 PVD 的根目录记录递归列文件 → {name: (lba, size, flags)}"""
    pvd = 16 * SEC
    assert mm[pvd:pvd + 1] == b'\x01', '不是 PVD'
    def rec_at(off):
        out = []
        while off < len(mm) and mm[off] != 0:
            ln = mm[off]
            lba = struct.unpack_from('<I', mm, off + 2)[0]
            size = struct.unpack_from('<I', mm, off + 10)[0]
            flags = mm[off + 25]
            nid = mm[off + 32]
            nid = bytes(mm[off + 33:off + 33 + nid])
            out.append((nid, lba, size, flags, ln))
            off += ln
        return out, off
    root = pvd + 156
    root_lba = struct.unpack_from('<I', mm, root + 2)[0]
    root_size = struct.unpack_from('<I', mm, root + 10)[0]
    files = {}
    dirs = [(root_lba, root_size, '')]
    seen = set()
    while dirs:
        lba, size, _p = dirs.pop()
        if (lba, size) in seen:
            continue
        seen.add((lba, size))
        recs, _ = rec_at(lba * SEC)
        for (nid, dlba, dsize, flags, _ln) in recs:
            if nid in (b'\x00', b'\x01'):
                continue
            nm = nid.decode('latin-1').split(';')[0]
            if flags & 0x02:
                dirs.append((dlba, dsize, nm))
            else:
                files[nm] = (dlba, dsize, flags)
    return files


def img_header(mm, lba):
    base = lba * SEC
    h = struct.unpack_from('<12I', mm, base)
    return dict(size=h[0], names_end=h[1], sector=h[2], tbl_end=h[3], names_start=h[4],
                data_start=h[5], hash_off=h[8], raw=[int(x) for x in h])


def img_entries(mm, lba, limit=8192):
    base = lba * SEC
    hdr = img_header(mm, lba)
    names = [x.decode('latin-1') for x in
             bytes(mm[base + hdr['names_start']:base + hdr['names_end']]).split(b'\x00') if x]
    out = []
    for i, nm in enumerate(names):
        o = base + 0x830 + 48 * i
        if o + 48 > base + hdr['size']:
            break
        r = struct.unpack_from('<12I', mm, o)
        out.append(dict(idx=i, name=nm, stored=r[6], real=r[7], off=r[8], raw=[int(x) for x in r]))
    return hdr, out, names


def main():
    report = {}
    data = {}
    for tag, path in DISCS:
        print('=' * 78)
        print('### %s' % tag)
        iso = tcslib.Iso(path)
        d = {}
        files = iso_files(iso.mm)
        d['iso9660'] = {k: dict(lba=v[0], size=v[1], flags=v[2]) for k, v in sorted(files.items())}
        print('  [iso] 文件 %d 个' % len(files))
        # IMG 头
        d['img'] = {}
        for imgname in ('MENU.IMG', 'GR.IMG'):
            if imgname not in files:
                continue
            lba = files[imgname][0]
            hdr, ents, names = img_entries(iso.mm, lba)
            d['img'][imgname] = dict(lba=lba, iso_size=files[imgname][1], header=hdr,
                                     n_entries=len(ents))
            data[(tag, imgname)] = dict(hdr=hdr, ents=ents, names=names)
            print('  [img] %-9s lba=%d ISO9660声明长=%d ; IMG头 size=%d names_end=%d '
                  'tbl_end=%d data_start=%d hash_off=0x%X ; 条目 %d'
                  % (imgname, lba, files[imgname][1], hdr['size'], hdr['names_end'],
                     hdr['tbl_end'], hdr['data_start'], hdr['hash_off'], len(ents)))
            # ★ 声明长度 vs 头里 size: 两者不一致 ⇒ 加载器按哪个算?
            d['img'][imgname]['size_matches'] = (files[imgname][1] == hdr['size'])
            print('        ★ ISO9660 声明长度 == IMG 头 size ? %s'
                  % d['img'][imgname]['size_matches'])
        report[tag] = d
        iso.close()

    # ---- 条目表差异 ----
    for imgname in ('MENU.IMG', 'GR.IMG'):
        if ('ZH113b', imgname) not in data or ('EN_ORIG', imgname) not in data:
            continue
        z, e = data[('ZH113b', imgname)], data[('EN_ORIG', imgname)]
        zd, ed = {x['name']: x for x in z['ents']}, {x['name']: x for x in e['ents']}
        onlyz = sorted(set(zd) - set(ed))
        onlye = sorted(set(ed) - set(zd))
        print('=' * 78)
        print('### %s 条目表差异' % imgname)
        print('  ZH 条目 %d, EN 条目 %d ; 仅 ZH 有 %d, 仅 EN 有 %d'
              % (len(z['ents']), len(e['ents']), len(onlyz), len(onlye)))
        if onlyz:
            print('  仅 ZH 有: %s' % onlyz[:20])
        if onlye:
            print('  仅 EN 有: %s' % onlye[:20])
        chg = []
        for nm in sorted(set(zd) & set(ed)):
            a, b = zd[nm], ed[nm]
            if (a['stored'], a['real'], a['off']) != (b['stored'], b['real'], b['off']) or a['raw'] != b['raw']:
                chg.append(dict(name=nm, idx_zh=a['idx'], idx_en=b['idx'],
                                zh=[a['stored'], a['real'], a['off']],
                                en=[b['stored'], b['real'], b['off']],
                                zh_raw=a['raw'], en_raw=b['raw']))
        print('  ★ 内容/条目字段有变化的条目 = %d 个' % len(chg))
        for c in chg[:60]:
            print('     %-28s idx %d→%d  stored/real/off  ZH=%s  EN=%s'
                  % (c['name'], c['idx_en'], c['idx_zh'], c['zh'], c['en']))
            # 列出 12 个 u32 里到底哪几个变了
            dif = ['u%d:%d→%d' % (i, c['en_raw'][i], c['zh_raw'][i])
                   for i in range(12) if c['en_raw'][i] != c['zh_raw'][i]]
            print('        字段差: %s' % ' '.join(dif))
        report.setdefault('entry_diff', {})[imgname] = chg

    with open(os.path.join(OUT, 'iso_container_diff.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('\n写出 %s' % os.path.join(OUT, 'iso_container_diff.json'))


if __name__ == '__main__':
    main()
