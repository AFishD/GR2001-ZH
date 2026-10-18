# -*- coding: utf-8 -*-
r"""rb_sftext_k2cs.py -- 用 **K2 charset** 复核 SF XML 的 <text> 正文是否有未映射码
（`name=` 属性是 UTF-8、不是引擎码，本脚本**不计入**）。
"""
import collections
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

GATE, LEAD_LO = 0xBA, 0xA1


def main():
    iso_p = os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'GR_REBUILD2400.iso')
    T.CHARSET = os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'backup',
                             'charset_compiled_zh16.json.before_hashr')
    T.Charset.__init__.__defaults__ = (T.CHARSET,)
    iso = T.Iso(iso_p)
    e = [x for x in zx_lib.entries(iso, zx_lib.MENU_LBA)
         if x['name'] == 'EN_SPECIAL_FEATURE.XML'][0]
    blob = b''.join(s[0] for s in T.lzo_subs(bytes(iso.read(e['iso_off'], e['stored']))))
    iso.close()
    cs = T.Charset()
    pair_dec = {tuple(k): v for k, v in cs.pair_of.items()}
    singles = dict(cs.codes)
    bodies = T.parse_sfxml(blob)
    print('charset = %s (pair=%d single=%d)' % (os.path.basename(T.CHARSET),
                                                len(pair_dec), len(singles)))
    print('<text> 正文区间 %d ; 正文总字节 %d' %
          (len(bodies), sum(l for (_k, _o, l, _b) in bodies)))
    unm_p, unm_s = collections.Counter(), collections.Counter()
    for (_k, _o, _l, body) in bodies:
        i, n = 0, len(body)
        while i < n:
            c = body[i]
            if LEAD_LO <= c < GATE and i + 1 < n:
                if (c, body[i + 1]) not in pair_dec:
                    unm_p['%02X%02X' % (c, body[i + 1])] += 1
                i += 2
            else:
                if c >= 0x80 and c not in singles:
                    unm_s['%02X' % c] += 1
                i += 1
    print('★ <text> 正文里未映射对偶码: 种类 %d / 次数 %d %s' %
          (len(unm_p), sum(unm_p.values()), unm_p.most_common(8)))
    print('★ <text> 正文里未映射单字节(>=0x80): 种类 %d / 次数 %d %s' %
          (len(unm_s), sum(unm_s.values()), unm_s.most_common(8)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
