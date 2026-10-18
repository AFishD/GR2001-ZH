# -*- coding: utf-8 -*-
r"""probe_r63.py — round63 前置探针 (只读 GR_ZH109.iso)。

看清 MENU.IMG#283 (SFXML copies[0]) 的真实结构 + 把 145 个标题与英文原盘
(GR.IMG#4058 EN_SPECIAL_FEATURE.XML) 对照列出, 供挑"真实错译"。
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402
import inject_text_csv as inj                                         # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
VIEW = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_r62',
                    'GR_ZH109_view_sf_titles.csv')
ITEM = re.compile(rb'<(studio|item|group)\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')
OUT = os.path.join(HERE, 'probe_r63_titles.txt')


def attrs(blob):
    """返回 [(tag, off, val)] —— 按 blob 顺序的全部 <studio|item|group name=…> 属性。"""
    out = []
    for m in ITEM.finditer(blob):
        nm = NAME.search(m.group(2))
        if nm:
            out.append((m.group(1).decode(), m.start(2) + nm.start(1), nm.group(1)))
    return out


def main():
    iso = T.Iso(ISO)
    cs = T.Charset()
    spec = T.RES['SFXML']['copies'][0]
    c = inj.Container(iso, 'SFXML', spec, cs)
    print('tag          = %s' % c.tag)
    print('entry        = stored=%d real=%d off=%d iso_off=0x%X'
          % (c.entry['stored'], c.entry['real'], c.entry['off'], c.entry['iso_off']))
    print('blob len     = %d   (sum sizes = %d)' % (len(c.blob), sum(c.sizes)))
    print('substreams   = %d  sizes=%s' % (len(c.sizes), c.sizes))
    print('frame len    = %d / slot %d  (free %+d)'
          % (c.frame_len, c.slot, c.slot - c.frame_len))
    ue = T.xml_tail_start(c.blob)
    print('used_end     = %d  (tail %d B)' % (ue, len(c.blob) - ue))
    print('tail head    = %s' % c.blob[ue:ue + 64].hex(' '))
    print('tail tail    = %s' % c.blob[-64:].hex(' '))
    print('tail all 0?  = %s   tail unique bytes=%d   tail non-0=%d'
          % (all(b == 0 for b in c.blob[ue:]), len(set(c.blob[ue:])),
             sum(1 for b in c.blob[ue:] if b)))
    print('text elems   = %d' % len(T.parse_sfxml(c.blob)))
    print('real==blob?  = %s   real==sum(sizes)? %s'
          % (c.entry['real'] == len(c.blob), c.entry['real'] == sum(c.sizes)))
    print('last substream ends at %d (blob %d)'
          % (sum(c.sizes), len(c.blob)))

    mine = attrs(c.blob)
    print('\nblob 里 name 属性 = %d' % len(mine))
    rows = list(csv.DictReader(open(VIEW, encoding='utf-8-sig')))
    zhm = [r for r in rows if r['copy_role'] == 'zh-main']
    en = [r for r in rows if r['container'].startswith('GR.IMG#4058')]
    print('view 表 zh-main=%d / EN(GR#4058)=%d' % (len(zhm), len(en)))
    bad = 0
    for r, (tag, off, val) in zip(zhm, mine):
        want = cs.marks_to_pua(r['text'])
        got = cs.decode(val)[0]
        if (int(r['offset']), int(r['len_bytes']), r['tag']) != (off, len(val), tag) \
                or got != want:
            bad += 1
            print('  !! #%s 不符: csv off=%s len=%s tag=%s text=%r | blob off=%d len=%d '
                  'tag=%s dec=%r' % (r['entry_index'], r['offset'], r['len_bytes'],
                                     r['tag'], r['text'], off, len(val), tag, got))
    print('view 表与 blob 逐条自证不符 = %d ✓' % bad)

    # 与英文原盘对照 (GR.IMG#4058)
    en_blob = inj.Container(iso, 'SFXML', T.RES['SFXML']['copies'][0], cs)
    spec_en = ('GR.IMG', T.GR_LBA, 4058, 'EN_SPECIAL_FEATURE.XML@GR')
    cen = inj.Container(iso, 'SFXML', spec_en, cs)
    en_attrs = attrs(cen.blob)
    print('EN 盘 (GR#4058) name 属性 = %d' % len(en_attrs))

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('#  idx tag     off    len  zh                                   '
                '| EN\n')
        for n, ((tag, off, val), r, (etag, eoff, eval_)) in \
                enumerate(zip(mine, zhm, en_attrs), 1):
            zh = cs.decode(val)[0]
            en_t = eval_.decode('latin-1')
            f.write('%4d  %-6s %6d %4d  %-34s | %s\n'
                    % (n, tag, off, len(val), zh, en_t))
        f.write('\n# 只列 zh-main 里含 >=2 连续汉字的 (%d 条)\n' % len(zhm))
    print('→ %s' % OUT)
    iso.close()


if __name__ == '__main__':
    main()
