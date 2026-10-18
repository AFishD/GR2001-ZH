# -*- coding: utf-8 -*-
r"""f364_probe1.py -- 只读侦察②: 文本容器里的 0xB4 / 0x7F / ASCII 字节预算 + FONT.RES 记录 95/148

用法: python work\tools\f364_probe1.py [iso]
"""
import collections
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def main(argv):
    src = argv[0] if argv else os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
    P('f364_probe1.py  src=%s' % src)
    iso = T.Iso(src)

    # ---------- 文本容器 ----------
    for name, spec in T.RES.items():
        for cp in spec['copies']:
            img, lba, idx, tag = cp
            e = iso.img_entry(lba, idx)
            raw = iso.read(e['iso_off'], e['stored'])
            subs = T.lzo_subs(raw)
            blob = b''.join(s[0] for s in subs)
            nb4 = blob.count(b'\xb4')
            n7f = blob.count(b'\x7f')
            n0 = blob.count(b'\x00')
            census = collections.Counter(b for b in blob if b < 0xA1)
            P('[txt] %-28s iso_off=0x%-9X slot=%-7d frame=%-7d blob=%-8d subs=%d'
              % (tag, e['iso_off'], e['stored'], sum(s[1] + 8 for s in subs), len(blob),
                 len(subs)))
            P('      0xB4 x %d ; 0x7F x %d ; 0x00 x %d (blob 尾部陈旧区 %d B)'
              % (nb4, n7f, n0, len(blob) - (T.parse_lang(blob)[1] if name == 'LANG'
                                            else T.xml_tail_start(blob))))
            small = sorted((b, c) for b, c in census.items() if b < 0x20 or b == 0x7F)
            P('      控制/0x7F 字节: %s' % ['0x%02X x%d' % (b, c) for b, c in small])
            P('      <0x20 总数 %d ; 0x7F 数 %d ; ASCII 0x20..0x7E 总数 %d'
              % (sum(c for b, c in census.items() if b < 0x20), census.get(0x7F, 0),
                 sum(c for b, c in census.items() if 0x20 <= b <= 0x7E)))
            # 0xB4 的后继字节分布
            nx = collections.Counter()
            i = 0
            while i < len(blob):
                if blob[i] == 0xB4:
                    nx[blob[i + 1] if i + 1 < len(blob) else -1] += 1
                i += 1
            bad = sum(c for b, c in nx.items() if 0xA1 <= b < 0xFF)
            P('      0xB4 后继字节: %d 种 ; 落在合法 trail [0xA1,0xFE] 的 = %d / %d'
              % (len(nx), bad, nb4))
            P('      后继样本: %s'
              % ' '.join('%02X:%d' % (b, c) for b, c in sorted(nx.items())[:16]))

    # ---------- FONT.RES ----------
    names = []
    for i in range(2000):
        e = iso.img_entry(T.MENU_LBA, i)
        if e['name'].startswith('?'):
            break
        names.append(e['name'])
    e_ft = iso.img_entry(T.MENU_LBA, names.index('FONT.RES'))
    ft_slot = iso.read(e_ft['iso_off'], e_ft['stored'])
    exp = b''.join(s[0] for s in T.lzo_subs(ft_slot))
    faces, endp = zx_lib.ft_records(exp, 28)
    P('[ft ] 槽 %d frame %d 展开 %d endp 0x%X'
      % (e_ft['stored'], sum(s[1] + 8 for s in T.lzo_subs(ft_slot)), len(exp), endp))
    for (fn, fld, rows) in faces:
        P('[ft ] face %-8s nrec=%d' % (fn, fld[4] * fld[5]))
        for k in (0x20 - 0x20, 0x5F - 0x20, 0x7E - 0x20, 95, 148, 146, 147, 149):
            off, r = rows[k]
            P('      rec[%3d] (code 0x%02X) off=0x%-5X  b0=%3d b1=%3d  rect=(%d,%d)-(%d,%d)'
              % (k, k + 0x20, off, r[0], r[1], r[2], r[3], r[4], r[5]))
    # 96..223 里是否有「未定义」矩形
    for (fn, fld, rows) in faces:
        z = [k for k, (o, r) in enumerate(rows) if r[4] <= r[2] or r[5] <= r[3]]
        P('[ft ] face %-8s 空矩形记录 %s' % (fn, z))
    # 记录矩形去重
    rects = collections.Counter()
    for (fn, fld, rows) in faces:
        for k, (o, r) in enumerate(rows):
            rects[(r[2], r[3], r[4], r[5])] += 1
    P('[ft ] 不同矩形数 %d ; 出现最多的: %s'
      % (len(rects), rects.most_common(6)))
    iso.close()
    return 0


if __name__ == '__main__':
    rc = main(sys.argv[1:])
    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, 'f364_probe1.txt'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    sys.exit(rc)
