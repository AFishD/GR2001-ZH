# -*- coding: utf-8 -*-
r"""v4_scan_bare.py — 只在**条目文本区**里扫"裸 lead 字节" (0xA1..0xB0 未成对), 并统计
新盘 / 现役盘各自的文本用字节。结构区 (u32 len/count) 不算。
另: 输出 16 新字 + 的/你/荐/志/略 的码位与图集格。
"""
import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import tcslib                                          # noqa: E402

cs = tcslib.Charset()
NEW = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')


def entries_of(iso_p):
    iso = tcslib.Iso(iso_p)
    out = []
    for (lba, idx, nm) in ((tcslib.MENU_LBA, 25, 'MENU#25 LANG'),
                           (tcslib.MENU_LBA, tcslib.XML_IDX, 'MENU#283 SFXML'),
                           (tcslib.GR_LBA, 902, 'GR#902 LANG')):
        e = iso.img_entry(lba, idx)
        blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(e['iso_off'], e['stored'])))
        if nm.endswith('SFXML'):
            for (k, off, ln, body) in tcslib.parse_sfxml(blob):
                out.append((nm, 'T%04d' % k, body))
        else:
            for e2 in tcslib.parse_lang(blob)[0]:
                out.append((nm, 'G%03d.I%03d' % (e2.g, e2.i), e2.data))
    iso.close()
    return out


print('== 条目文本区内的裸 lead 字节 (0xA1..0xB0 未成对) ==')
for tag, p in (('GR_ZH93 (新)', NEW),
               ('GR_ZH92 (现役, 用旧 charset 读)', os.path.join(REPO, 'work', 'builds',
                                                              'GR_ZH92', 'GR_ZH92.iso'))):
    ents = entries_of(p)
    tot, examples = 0, []
    for (nm, rid, body) in ents:
        i, n = 0, len(body)
        while i < n:
            v = body[i]
            if 0xA1 <= v < tcslib.PAIR_LEAD_HI and i + 1 < n and 0xA1 <= body[i + 1] <= 0xFE:
                i += 2
                continue
            if 0xA1 <= v < tcslib.PAIR_LEAD_HI:
                tot += 1
                if len(examples) < 5:
                    examples.append('%s:%s@%d=0x%02X' % (nm, rid, i, v))
            i += 1
    print('  %-32s 条目 %d, 裸 lead 字节 %d %s' % (tag, len(ents), tot,
                                                 ('例: ' + ', '.join(examples)) if tot else '✓'))

print()
print('== 17+2 个关键字的码位与图集格 ==')
js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


meta = js.get('_font_ext_planc_zh93', {})
for ch in '虽螺衍衣裂誉贡轮迟造钢题额鼓（）荐的你志略':
    p = js['pair_of'].get(ch)
    c = js['codes'].get(ch)
    if p:
        s = (p[0] - 0xA1) * 94 + (p[1] - 0xA1)
        r, cc = s // 62, s % 62
        print('  %s : 对偶 %02X%02X slot=%4d 引擎格=(%4d,%3d)  %s'
              % (ch, p[0], p[1], s, 16 * ((cc + PHI[r]) % 64), yrow(r),
                 meta.get('placed', {}).get(ch, '')))
    else:
        print('  %s : 单字节 0x%02X' % (ch, c))
