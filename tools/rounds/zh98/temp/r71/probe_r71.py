# -*- coding: utf-8 -*-
"""round71 probe:
1) charset CSV (GR_ZH114 dump) -> char -> (kind, has_glyph)
2) check every char of the candidate titles
3) print current values (text_en / text_zh / text_edited) for the target ids
"""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
V114 = os.path.join(REPO, 'work', 'builds', 'GR_ZH114')

CSV_FONT = os.path.join(V114, 'font', 'GR_ZH114_font_charset.csv')
CSV_TITLES = os.path.join(V114, 'text', 'GR_ZH114_text_sf_titles.csv')

CAND = [
    ('A-music-1', '音乐 1'),
    ('A-music-9', '音乐 9'),
    ('B-ds-soldiers', '荒漠围攻士兵'),
    ('B-ds-vehicles', '荒漠围攻车辆'),
    ('ref-old', '沙漠士兵'),
    ('opt-fear', '恐惧的总和'),
    ('opt-fear2', '惊天核网'),
    ('ref-nowrap', '幽灵行动'),
    ('opt-laser', '激光测距仪'),
]

TARGET_IDS = ['A0022', 'A0035', 'A0044', 'A0045', 'A0046', 'A0053',
              'A0084', 'A0113', 'A0143']


def load_charset():
    d = {}
    with io.open(CSV_FONT, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            d[row['char']] = (row['kind'], row['has_glyph'], row['unicode'])
    return d


def load_titles():
    with io.open(CSV_TITLES, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    cs = load_charset()
    rows = load_titles()
    L = []
    L.append('# charset csv: %s' % CSV_FONT)
    kinds = {}
    for ch, (k, hg, u) in cs.items():
        kinds[(k, hg)] = kinds.get((k, hg), 0) + 1
    L.append('charset entries = %d' % len(cs))
    for k in sorted(kinds):
        L.append('   kind=%-8s has_glyph=%s -> %d' % (k[0], k[1], kinds[k]))
    L.append('')
    L.append('# candidate strings')
    for name, s in CAND:
        miss = [c for c in s if c not in cs]
        noglyph = [c for c in s if c in cs and cs[c][1] != '1']
        L.append('%-16s %-14s len=%2d  not_in_charset=%s  has_glyph=0=%s'
                 % (name, s, len(s), ''.join(miss) or '-', ''.join(noglyph) or '-'))
    L.append('')
    L.append('# per-char detail')
    seen = []
    for _n, s in CAND:
        for c in s:
            if c not in seen:
                seen.append(c)
    for c in seen:
        if c in cs:
            k, hg, u = cs[c]
            L.append('   %s  %-9s kind=%-7s has_glyph=%s' % (c, u, k, hg))
        else:
            L.append('   %s  <NOT IN CHARSET>' % c)
    L.append('')
    L.append('# current title rows (target ids)')
    L.append('id,tag,kind,text_en,text_zh,text_edited,len_bytes,max_bytes')
    for r in rows:
        sid = r['id'].split(':')[-1]
        if sid in TARGET_IDS:
            L.append('%s,%s,%s,%s,%s,%s,%s,%s' % (
                sid, r['tag'], r['kind'], r['text_en'], r['text_zh'],
                r['text_edited'], r['len_bytes'], r['max_bytes']))
    out = os.path.join(HERE, 'probe_r71.txt')
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))
    print('wrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
