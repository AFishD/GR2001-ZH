# -*- coding: utf-8 -*-
r"""make_table_r71.py — round71: 从 GR_ZH114 的标题表生成注入表 (只动 text_edited 一列)。

A 类: A0045..A0053 (9 条空标题, 原版 EN/IT 为空) -> 音乐 1 .. 音乐 9
B 类: A0022 DS Soldiers 沙漠士兵 -> 荒漠围攻士兵
      A0035 DS vehicles 沙漠车辆 -> 荒漠围攻车辆

做法 = **外科手术式**替换: 逐行按 id 命中后, 只把该行里 `text_edited` 那一格换掉,
其余字符 (含 BOM / 换行 / 引号风格 / 备注列) **一个字节都不动**。

输出:
  r71/GR_ZH117_text_sf_titles.csv   注入表 (喂给 inject_text_csv.py)
  r71/edits_list.txt                11 条改动的 字宽/字节 逐条清单
"""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                               # noqa: E402

V114 = os.path.join(REPO, 'work', 'builds', 'GR_ZH114')
SRC = os.path.join(V114, 'text', 'GR_ZH114_text_sf_titles.csv')
FONT_CSV = os.path.join(V114, 'font', 'GR_ZH114_font_charset.csv')
OUT_CSV = os.path.join(HERE, 'GR_ZH117_text_sf_titles.csv')
OUT_LIST = os.path.join(HERE, 'edits_list.txt')

# id -> (英文原名, 盘上现值, 新值, 依据)
EDITS = [
    ('A0022', 'DS Soldiers', '沙漠士兵', '荒漠围攻士兵',
     'DS = Desert Siege = 用户新译 T0030 的《荒漠围攻》(同 round68 的 25 条口径)'),
    ('A0035', 'DS vehicles', '沙漠车辆', '荒漠围攻车辆',
     '同上 (DS = Desert Siege)'),
]
for _i in range(1, 10):
    EDITS.append(('A%04d' % (44 + _i), '', '', '音乐 %d' % _i,
                  '原版 EN/IT 空标题; DE/ES/FR 均填 Musik/Música/Musique N (音乐组第 %d 条)' % _i))
EDITS.sort()


def load_font():
    d = {}
    with io.open(FONT_CSV, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            d[row['char']] = (row['kind'], row['has_glyph'])
    return d


def main():
    raw = io.open(SRC, 'rb').read()
    text = raw.decode('utf-8')
    lines = text.split('\n')
    L = []

    # ---- 1) 逐行外科替换 ----
    idx_of = {}
    for i, ln in enumerate(lines):
        if ln.startswith('SFXML:'):
            idx_of[ln.split(',', 1)[0][6:]] = i
    L.append('# 源表 %s' % os.path.relpath(SRC, REPO))
    L.append('# 行数 %d (含表头/空尾行)' % len(lines))
    for (sid, en, old, new, why) in EDITS:
        assert sid in idx_of, 'id 不在表里: %s' % sid
        i = idx_of[sid]
        ln = lines[i]
        # text_en / text_zh / text_edited 三格在 dup_count 之后, 形如  ,"EN","ZH","EDITED",
        needle = ',"%s","%s","%s",' % (en, old, old)
        assert ln.count(needle) == 1, ('%s: 定位串出现 %d 次 (期望 1): %r'
                                       % (sid, ln.count(needle), needle))
        lines[i] = ln.replace(needle, ',"%s","%s","%s",' % (en, old, new))
        L.append('  %-14s %-38s | %-8s -> %-8s' % (sid, en or '(空)', old or '(空)', new))
    text2 = '\n'.join(lines)

    # ---- 2) 校验: 只有这 11 行的 text_edited 变了 ----
    def parse(t):
        return list(csv.DictReader(io.StringIO(t[len('\ufeff'):] if t.startswith('\ufeff') else t)))
    a, b = parse(text), parse(text2)
    assert len(a) == len(b) == 145, (len(a), len(b))
    changed = []
    for x, y in zip(a, b):
        assert x['id'] == y['id']
        for col in y:
            if col == 'text_edited':
                continue
            assert x[col] == y[col], '%s 列 %s 被动了' % (x['id'], col)
        if x['text_edited'] != y['text_edited']:
            changed.append((y['id'], x['text_edited'], y['text_edited']))
    want = dict(('SFXML:' + e[0], e[3]) for e in EDITS)
    assert len(changed) == len(EDITS), '变化行数 %d != %d' % (len(changed), len(EDITS))
    for (rid, o, n) in changed:
        assert want[rid] == n, (rid, o, n)
    L.append('# 校验: 145 行; 只有 %d 行的 text_edited 变了; 其余 16 列逐格相同 ✓'
             % len(changed))

    # ---- 3) 字库 (charset + 真字形) 逐字核 ----
    font = load_font()
    bad = []
    for (sid, en, old, new, why) in EDITS:
        for c in new:
            if c not in font:
                bad.append('%s: %r 不在字符集' % (sid, c))
            elif font[c][1] != '1':
                bad.append('%s: %r 无字形' % (sid, c))
    L.append('# 字库: 11 条新串全部字符都在 charset 且 has_glyph=1 ✓' if not bad
             else '# 字库: %s' % bad)
    assert not bad, bad

    # ---- 4) 宽度清单 ----
    L.append('')
    L.append('%-14s %-6s %-14s %-12s %-6s %-6s %s'
             % ('id', 'tag', 'text_zh(盘上)', 'text_edited(新)', 'oldpx', 'newpx', 'Δpx/ΔB'))
    tag_of = dict((r['id'], r['tag']) for r in a)
    tot_d = 0
    for (sid, en, old, new, why) in EDITS:
        rid = 'SFXML:' + sid
        w0, w1 = T.strlen(old), T.strlen(new)
        tot_d += w1 - w0
        L.append('%-14s %-6s %-14s %-12s %-6d %-6d %+d / %+d'
                 % (rid, tag_of[rid], old or '(空)', new, w0, w1, w1 - w0, len(new) - len(old)))
    L.append('# 合计 Δ宽 = %+d px' % tot_d)

    # ---- 5) 写盘 ----
    io.open(OUT_CSV, 'wb').write(text2.encode('utf-8'))
    io.open(OUT_LIST, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    print('\nwrote %s (%d B)' % (OUT_CSV, os.path.getsize(OUT_CSV)))
    print('wrote %s' % OUT_LIST)
    return 0


if __name__ == '__main__':
    sys.exit(main())
