# -*- coding: utf-8 -*-
r"""content_diff.py — GR_ZH113b vs GR_EN_ORIG 的**逐条目内容**差异 + COMMON.PAK 记录链实测

为什么必须做内容比对: MENU.IMG 的条目表字段 (stored/real/off) 可能**一字不变**,
而条目内容已经换成更大的东西 (图集 512x512 → 1024x512) ⇒ 只比字段会漏掉真正的改动。

本轮输出的关键量:
  · 每个条目 stored 字节的 sha256 —— ZH vs EN 不同的条目清单
  · COMMON.PAK 的**完整记录链**: 每条 name/psm/w/h/clut/px_size/px_off/end
    ⇒ 链尾 end 与条目声明长度 stored 的关系 (溢出? 余量?)
  · FONT.RES 的展开长度/nrec/fld
"""
import hashlib
import json
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                          # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_MEMDRIFT', 'audit')
MENU_LBA = 776286
GR_LBA = 19175
DISCS = [('ZH113b', os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')),
         ('EN_ORIG', os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))]


def pak_chain(pak):
    """COMMON.PAK 记录链: <u32 type><u32 nameLen><name><u32 psm><u32 w><u32 h><u32 clut>
    <clut 字节><u32 px_size><px 字节>  ; type==0x63 结束哨兵"""
    out, p = [], 0
    n = len(pak)
    while p + 8 <= n:
        t = struct.unpack_from('<I', pak, p)[0]
        if t == 0x63:
            out.append(dict(kind='END', at=p))
            break
        nl = struct.unpack_from('<I', pak, p + 4)[0]
        if nl > 256 or p + 8 + nl > n:
            out.append(dict(kind='BAD', at=p, type=t, nameLen=nl))
            break
        nm = pak[p + 8:p + 8 + nl].split(b'\x00')[0].decode('latin-1')
        q = p + 8 + nl
        psm, w, h, clut = struct.unpack_from('<4I', pak, q)
        q += 16
        px_size = struct.unpack_from('<I', pak, q + clut)[0]
        px_off = q + clut + 4
        end = px_off + px_size
        out.append(dict(kind='REC', at=p, name=nm, psm=psm, w=w, h=h,
                        clut=clut, px_size=px_size, px_off=px_off, end=end,
                        rect_bytes=px_size))
        p = end
    return out


def main():
    report = {}
    iso = {}
    ents = {}
    for tag, path in DISCS:
        i = tcslib.Iso(path)
        iso[tag] = i
        ents[tag] = {}
        for (lba, imgname) in ((MENU_LBA, 'MENU.IMG'), (GR_LBA, 'GR.IMG')):
            base = lba * 2048
            noff = struct.unpack_from('<I', i.mm, base + 0x10)[0]
            nend = struct.unpack_from('<I', i.mm, base + 4)[0]
            names = [x.decode('latin-1') for x in
                     bytes(i.mm[base + noff:base + nend]).split(b'\x00') if x]
            lst = []
            for k, nm in enumerate(names):
                r = struct.unpack_from('<12I', i.mm, base + 0x830 + 48 * k)
                lst.append(dict(idx=k, name=nm, stored=r[6], real=r[7], off=r[8],
                                iso_off=base + r[8]))
            ents[tag][imgname] = lst

    print('=' * 78)
    print('### 逐条目内容 sha256 差异 (raw stored 字节)')
    changed = []
    for imgname in ('MENU.IMG', 'GR.IMG'):
        zl, el = ents['ZH113b'][imgname], ents['EN_ORIG'][imgname]
        zz = {x['name']: x for x in zl}
        ee = {x['name']: x for x in el}
        n_same = n_diff = 0
        for nm in sorted(set(zz) & set(ee)):
            a, b = zz[nm], ee[nm]
            ha = hashlib.sha256(iso['ZH113b'].read(a['iso_off'], a['stored'])).hexdigest()[:16]
            hb = hashlib.sha256(iso['EN_ORIG'].read(b['iso_off'], b['stored'])).hexdigest()[:16]
            if ha == hb:
                n_same += 1
            else:
                n_diff += 1
                changed.append(dict(img=imgname, name=nm, idx=a['idx'],
                                    zh=dict(stored=a['stored'], real=a['real'], off=a['off'], sha=ha),
                                    en=dict(stored=b['stored'], real=b['real'], off=b['off'], sha=hb)))
        print('  %-9s 内容相同 %d 个 ; **内容不同 %d 个**' % (imgname, n_same, n_diff))
    print('  ---- 内容不同的条目 ----')
    for c in changed:
        print('   %-9s %-28s stored %d→%d  real %d→%d  off %d→%d'
              % (c['img'], c['name'], c['en']['stored'], c['zh']['stored'],
                 c['en']['real'], c['zh']['real'], c['en']['off'], c['zh']['off']))
    report['content_changed'] = changed

    # ---- COMMON.PAK 记录链 ----
    print('=' * 78)
    print('### COMMON.PAK 记录链实测 (declared vs 实际内容)')
    report['pak'] = {}
    for tag in ('ZH113b', 'EN_ORIG'):
        e = [x for x in ents[tag]['MENU.IMG'] if x['name'] == 'COMMON.PAK'][0]
        pak = iso[tag].read(e['iso_off'], e['stored'])
        chain = pak_chain(pak)
        print('  [%s] 条目 stored=%d real=%d off=0x%X' % (tag, e['stored'], e['real'], e['off']))
        for r in chain:
            if r['kind'] == 'END':
                print('      END 哨兵 @0x%X  ⇒ 链占用 %d B ; 声明 stored=%d ; 余量=%d'
                      % (r['at'], r['at'], e['stored'], e['stored'] - r['at']))
            elif r['kind'] == 'BAD':
                print('      !! 坏记录 @0x%X type=%s nameLen=%s' % (r['at'], r.get('type'), r.get('nameLen')))
            else:
                flag = ''
                if r['end'] > e['stored']:
                    flag = '  ★★ 越过声明长度 %d B' % (r['end'] - e['stored'])
                print('      @0x%-7X %-20s psm=0x%02X %dx%d clut=%d px_size=0x%X px@0x%X end=0x%X%s'
                      % (r['at'], r['name'], r['psm'], r['w'], r['h'], r['clut'],
                         r['px_size'], r['px_off'], r['end'], flag))
        report['pak'][tag] = dict(entry=dict(stored=e['stored'], real=e['real'], off=e['off']),
                                  chain=chain)

    # ---- FONT.RES ----
    print('=' * 78)
    print('### FONT.RES')
    report['font'] = {}
    for tag in ('ZH113b', 'EN_ORIG'):
        e = [x for x in ents[tag]['MENU.IMG'] if x['name'] == 'FONT.RES'][0]
        raw = iso[tag].read(e['iso_off'], e['stored'])
        ft = b''.join(s[0] for s in tcslib.lzo_subs(raw))
        endp, faces = tcslib.parse_ft_faces(ft)
        print('  [%s] stored=%d real=%d 展开=%d ; 记录区结束 @0x%X ; 余 %d B'
              % (tag, e['stored'], e['real'], len(ft), endp, len(ft) - endp))
        for (nm, fld, recs) in faces:
            print('      %-8s fld4=%d fld5=%d nrec=%d 实存记录=%d'
                  % (nm, fld[4], fld[5], fld[4] * fld[5], len(recs)))
        report['font'][tag] = dict(stored=e['stored'], real=e['real'], expanded=len(ft),
                                   records_end=endp,
                                   faces=[dict(name=n, fld=[int(x) for x in f], nrec=f[4] * f[5],
                                               recs=len(r)) for (n, f, r) in faces])

    for i in iso.values():
        i.close()
    with open(os.path.join(OUT, 'content_diff.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('\n写出 %s' % os.path.join(OUT, 'content_diff.json'))


if __name__ == '__main__':
    main()
