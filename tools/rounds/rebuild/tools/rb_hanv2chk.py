# -*- coding: utf-8 -*-
r"""rb_hanv2chk.py -- 只读：核对 docs/han_v2 下的解码态/容器产物与原盘、K2 拼装盘的对应关系。
"""
import hashlib
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
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def main():
    ORIG = os.path.join(REPO, 'third_party', 'orig', 'ps2',
                        "Tom Clancy's Ghost Recon (USA).iso")
    K2 = os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', '_probe_k2only.iso')
    HV = os.path.join(REPO, 'docs', 'han_v2')
    orig = T.Iso(ORIG)
    k2 = T.Iso(K2)
    for tag, iso in (('ORIG', orig), ('K2  ', k2)):
        men = zx_lib.entries(iso, zx_lib.MENU_LBA)
        gr = zx_lib.entries(iso, zx_lib.GR_LBA)
        P('==== %s ====' % tag)
        for (nm, ent, idxname) in (('MENU', men, 'MENU.PAK/FONT/COMMON/STRINGS'),
                                   ('GR', gr, 'GR side')):
            for e in ent:
                if e['name'] in ('EN_STRINGS.RES', 'FONT.RES', 'COMMON.PAK',
                                 'EN_SPECIAL_FEATURE.XML'):
                    slot = bytes(iso.read(e['iso_off'], e['stored']))
                    subs = T.lzo_subs(slot)
                    blob = b''.join(s[0] for s in subs) if subs else b''
                    P('%s#%-5d %-24s stored=%-8d real=%-8d 子流=%-3d 展开=%-8d sha=%s' %
                      (nm, e['idx'], e['name'], e['stored'], e['real'],
                       len(subs) if subs else 0, len(blob), sha(blob)))
                    if e['name'] == 'COMMON.PAK':
                        P('        pak slot sha=%s' % sha(slot))
                        P('        recs: %s' % [(r[0], r[1], r[2], r[3], r[4], r[5], r[6])
                                                for r in T.parse_pak_records(slot)])
                    if e['name'] == 'EN_STRINGS.RES' and blob:
                        P('        展开前 32B: %s' % blob[:32].hex())
    orig.close()
    k2.close()

    P('')
    P('==== docs/han_v2 候选 ====')
    for rel in ('GR_EN_STRINGS_RES_decoded.bin', 'artifacts/RES_decoded_stream.bin',
                'artifacts/EN_STRINGS_RES_decoded.bin',
                'artifacts/EN_STRINGS_plain_full.bin',
                'res_zh/EN_STRINGS_ZH.bin',
                'artifacts/font_rsfb_engine.bin',
                'artifacts/COMMON_PAK.bin', 'COMMON_PAK_ZH12.bin',
                'COMMON_PAK_ZH3.bin', 'COMMON_PAK_ZH4.bin', 'COMMON_PAK_ZH5.bin',
                'COMMON_PAK_ZH6.bin', 'COMMON_PAK_pairs.bin',
                'COMMON_PAK_pairs_expanded.bin'):
        p = os.path.join(HV, rel.replace('/', os.sep))
        if not os.path.exists(p):
            P('  [缺] %s' % rel)
            continue
        b = open(p, 'rb').read()
        P('  %-42s %9d sha=%s  头32B=%s' % (rel, len(b), sha(b), b[:32].hex()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
