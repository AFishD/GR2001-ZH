# -*- coding: utf-8 -*-
"""show_edits_r68.py — 打印 r68 编辑表里所有 text_edited != text_zh 的行 + 宽度/字表体检."""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                               # noqa: E402

BASE = os.path.join(HERE, 'GR_ZH111_base_text_sf_titles.csv')
EDIT = os.path.join(HERE, 'GR_ZH114_text_sf_titles.csv')
OUT = os.path.join(HERE, 'edits_list.txt')
CHARSET_TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r64',
                           'available_charset.txt')


def baseline():
    with io.open(CHARSET_TXT, 'r', encoding='utf-8') as f:
        t = ''.join(ln for ln in f.read().splitlines() if not ln.startswith('#'))
    return set(ch for ch in t if ch.strip())


def lo(p):
    with io.open(p, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    bs, ed = lo(BASE), lo(EDIT)
    assert len(bs) == len(ed) == 145
    bch = baseline()
    L = []
    n = 0
    lines_changed = []
    for a, b in zip(bs, ed):
        assert a['id'] == b['id'], (a['id'], b['id'])
        for c in a:
            if c == 'text_edited':
                continue
            assert a[c] == b[c], '!! %s 列 %s 被改了' % (a['id'], c)
        if a['text_edited'] != b['text_edited']:
            n += 1
            lines_changed.append(b['id'])
    L.append('# 变动行 %d / 145' % n)
    L.append('')
    L.append('%-13s %-5s %-24s %-26s %5s %5s %6s %6s  %s'
             % ('id', 'tag', 'text_zh(盘上)', 'text_edited(新)', 'old字', 'new字',
                'oldpx', 'newpx', 'Δpx'))
    tot_old = tot_new = 0
    bad = []
    for a, b in zip(bs, ed):
        if a['text_edited'] == b['text_edited']:
            continue
        wo, wn = T.strlen(a['text_zh']), T.strlen(b['text_edited'])
        tot_old += wo
        tot_new += wn
        miss = ''.join(sorted(set(ch for ch in b['text_edited']
                                  if ord(ch) >= 0x80 and ch not in bch)))
        if miss:
            bad.append((b['id'], miss))
        L.append('%-13s %-5s %-24s %-26s %5d %5d %6d %6d  %+d%s'
                 % (b['id'], b['tag'], a['text_zh'], b['text_edited'],
                    len(a['text_zh']), len(b['text_edited']), wo, wn, wn - wo,
                    ('  ★超基线字: ' + miss) if miss else ''))
    L.append('')
    L.append('# 合计宽度 %d -> %d px (%+d)' % (tot_old, tot_new, tot_new - tot_old))
    L.append('# 超出 1285 基线字的行: %d %s' % (len(bad), bad))
    L.append('# 变动 id: %s' % ' '.join(lines_changed))
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L[-4:]))
    print('wrote', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
