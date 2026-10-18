# -*- coding: utf-8 -*-
r"""rb_sfffd.py -- 只读：查明 rb_textaudit.py 在 SF XML 载荷里报出的未映射码到底是什么。
"""
import collections
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

GATE, LEAD_LO = 0xBA, 0xA1
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def main():
    iso_p = os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'GR_REBUILD2400.iso')
    T.CHARSET = os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'backup',
                             'charset_compiled_zh16.json.before_hashr')
    iso = T.Iso(iso_p)
    e = [x for x in zx_lib.entries(iso, zx_lib.MENU_LBA)
         if x['name'] == 'EN_SPECIAL_FEATURE.XML'][0]
    blob = b''.join(s[0] for s in T.lzo_subs(bytes(iso.read(e['iso_off'], e['stored']))))
    iso.close()
    cs = T.Charset()
    pair_dec = {tuple(k): v for k, v in cs.pair_of.items()}   # cs.pair_of 本身即 (b1,b2)→字
    singles = dict(cs.codes)
    P('blob %d B ; charset pair=%d single=%d' % (len(blob), len(pair_dec), len(singles)))

    # 只取 <text> 正文
    bodies = T.parse_sfxml(blob)
    P('<text> 正文区间 = %d' % len(bodies))
    unm = collections.Counter()
    pairs_unmapped = collections.Counter()
    for (_k, _o, _l, body) in bodies:
        i, n = 0, len(body)
        while i < n:
            c = body[i]
            if LEAD_LO <= c < GATE and i + 1 < n:
                if (c, body[i + 1]) not in pair_dec:
                    pairs_unmapped['%02X%02X' % (c, body[i + 1])] += 1
                i += 2
            else:
                if c not in singles and c >= 0x80:
                    unm['%02X' % c] += 1
                i += 1
    P('未映射的对偶码 (top20): %s' % pairs_unmapped.most_common(20))
    P('未映射的单字节 (>=0x80, top20): %s' % unm.most_common(20))
    P('未映射对偶码种类 %d / 总次数 %d ; 未映射单字节种类 %d / 次数 %d' %
      (len(pairs_unmapped), sum(pairs_unmapped.values()), len(unm), sum(unm.values())))
    # name= 属性
    nattr = 0
    aunm = collections.Counter()
    for m in re.finditer(rb'name="([^"]*)"', blob):
        nattr += 1
        for c in m.group(1):
            if c >= 0x80:
                aunm['%02X' % c] += 1
    P('name= 属性 %d 个 ; 属性里 >=0x80 的字节: %s' % (nattr, aunm.most_common(10)))
    out = os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'sfffd.txt')
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    P('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
