# -*- coding: utf-8 -*-
r"""r57 判据分析 v2: "码位变更过的对偶码" 是关键 —— 只重编码**真会变**的段。

只读; 秒级 (用 calib_r57.json)。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(io.open(os.path.join(HERE, 'calib_r57.json'), encoding='utf-8'))
old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_before_r56.json'))
new = tcslib.Charset()
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso'))
TRUE_OFFS = {0x50B820, 0x50B858, 0x50B870, 0x50B8A8, 0x50B8D8,
             0x50B840, 0x50B860, 0x50B890, 0x50B8C0, 0x50B8E8}

# ---- 哪些字/码位变了? ----
changed_pairs = set()
for p, ch in old.pair_of.items():
    if new.pair_of.get(p) != ch:
        changed_pairs.add(p)
for p, ch in new.pair_of.items():
    if old.pair_of.get(p) != ch:
        changed_pairs.add(p)
print('旧 pair_of=%d, 新 pair_of=%d, 码位变更的对偶码=%d'
      % (len(old.pair_of), len(new.pair_of), len(changed_pairs)))
print('  例: %s' % ' '.join('%02X%02X:%s→%s' % (p[0], p[1], old.pair_of.get(p, '?'),
                                             new.pair_of.get(p, '?'))
                            for p in sorted(changed_pairs)[:8]))
for ch in '载入中请等待':
    print('  %s: 旧 %s → 新 %s %s' % (ch, old.encode_strict(ch).hex(' '),
                                      new.encode_strict(ch).hex(' '),
                                      '(未变)' if old.encode_strict(ch) == new.encode_strict(ch)
                                      else '★变了'))
unchanged_pairs = set(old.pair_of) - changed_pairs
print('  未变的旧对偶码 %d 个 (这些字节重编码后**一模一样**)' % len(unchanged_pairs))


def units_of(buf):
    out, i, n = [], 0, len(buf)
    while i < n:
        v = buf[i]
        if v < 0x80:
            out.append((i, 1, chr(v), None)); i += 1
        elif i + 1 < n and (v, buf[i + 1]) in old.pair_of:
            out.append((i, 2, old.pair_of[(v, buf[i + 1])], (v, buf[i + 1]))); i += 2
        elif v in old.codes:
            out.append((i, 1, old.codes[v], None)); i += 1
        else:
            break
    return out


def feat(r):
    off, nb = r['off'], r['nbytes']
    raw = bytes(iso.mm[off:off + nb])
    u = units_of(raw)
    npair = sum(1 for x in u if x[1] == 2)
    nchg = sum(1 for x in u if x[3] in changed_pairs)
    cs0, ce = r['cstr']
    cstr = bytes(iso.mm[cs0:ce])
    cu = units_of(cstr)
    cnp = sum(1 for x in cu if x[1] == 2)
    cchg = sum(1 for x in cu if x[3] in changed_pairs)
    ccjk = sum(1 for x in cu if '\u4e00' <= x[2] <= '\u9fff')
    return dict(raw=raw, npair=npair, nchg=nchg, ratio=round(npair / max(1, len(u)), 3),
                cstr_text=''.join(x[2] for x in cu),
                c_len=len(cu), c_npair=cnp, c_chg=cchg, c_cjk=ccjk,
                c_ratio=round(cnp / max(1, len(cu)), 3),
                c_clean=(len(cu) > 0 and cu[-1][0] + cu[-1][1] == len(cstr)),
                c_text_ratio=round((cnp + sum(1 for x in cu if x[1] == 1 and ord(x[2]) < 0x80))
                                   / max(1, len(cu)), 3))


for r in rows:
    r.update(feat(r))
    r['is_true'] = r['off'] in TRUE_OFFS

print('\n真文本段:')
for r in rows:
    if r['is_true']:
        print('  @0x%06X %-8r run: pair=%d/%d ratio=%.2f chg=%d | cstr: len=%d pair=%d chg=%d '
              'cjk=%d ratio=%.2f clean=%s'
              % (r['off'], r['text'], r['npair'], r['npair'] + (r['nbytes'] - 2 * r['npair']),
                 r['ratio'], r['nchg'], r['c_len'], r['c_npair'], r['c_chg'], r['c_cjk'],
                 r['c_ratio'], r['c_clean']))

print('\n有"变更对偶码"的段共 %d / %d' % (sum(1 for r in rows if r['nchg'] or r['c_chg']), len(rows)))

RULES = {
    'X1 段内 pair_ratio==1.0 且含变更对偶码':
        lambda r: r['ratio'] == 1.0 and r['nchg'] > 0,
    'X2 段内含变更对偶码 (只要真变)':
        lambda r: r['nchg'] > 0,
    'X3 C串口径: 两侧0x00 & 整串干净 & 串内对偶比>=0.5 & 含变更对偶码':
        lambda r: (r['span_pre'] == 0 and r['span_post'] == 0 and r['c_clean']
                   and not any(0x00 <= b < 0x20 or 0x7F <= b < 0xA0 for b in
                               bytes(iso.mm[r['cstr'][0]:r['cstr'][1]]))
                   and r['c_ratio'] >= 0.5 and r['c_chg'] > 0),
    'X4 = X3 但 串内对偶比>=0.4':
        lambda r: (r['span_pre'] == 0 and r['span_post'] == 0 and r['c_clean']
                   and not any(0x00 <= b < 0x20 or 0x7F <= b < 0xA0 for b in
                               bytes(iso.mm[r['cstr'][0]:r['cstr'][1]]))
                   and r['c_ratio'] >= 0.4 and r['c_chg'] > 0),
    'X5 = X3 但 串内对偶比>=0.6':
        lambda r: (r['span_pre'] == 0 and r['span_post'] == 0 and r['c_clean']
                   and not any(0x00 <= b < 0x20 or 0x7F <= b < 0xA0 for b in
                               bytes(iso.mm[r['cstr'][0]:r['cstr'][1]]))
                   and r['c_ratio'] >= 0.6 and r['c_chg'] > 0),
    'X6 = X3 但 串内对偶比>=0.75':
        lambda r: (r['span_pre'] == 0 and r['span_post'] == 0 and r['c_clean']
                   and not any(0x00 <= b < 0x20 or 0x7F <= b < 0xA0 for b in
                               bytes(iso.mm[r['cstr'][0]:r['cstr'][1]]))
                   and r['c_ratio'] >= 0.75 and r['c_chg'] > 0),
}
for nm, fn in RULES.items():
    sel = [r for r in rows if fn(r)]
    hit = sum(1 for r in sel if r['is_true'])
    print('\n判据 %-52s 选中 %5d (真文本 %d/10)' % (nm, len(sel), hit))
    for r in sel:
        if not r['is_true']:
            print('    ✗ @0x%06X %-10r raw=%-20s nchg=%d ratio=%.2f | cstr=%r (ratio=%.2f chg=%d)'
                  % (r['off'], r['text'], r['raw'].hex(' '), r['nchg'], r['ratio'],
                     r['cstr_text'], r['c_ratio'], r['c_chg']))
iso.close()
