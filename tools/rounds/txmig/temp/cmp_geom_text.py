# -*- coding: utf-8 -*-
r"""cmp_geom_text.py — 几何盘 vs 基底盘: 3 个文本容器**逐字符**比对 (只读)

为什么需要 (LEAD §13 的合并顺序): §13 把"几何盘"定为合并基底, 并要求
`migrate_legacy.py <几何盘> <成品盘> --no-elf` —— 前提是**几何盘的文本仍是基底语义**。
本工具实测这个前提: 两张盘各容器的解压 blob 与**基底闸门语义下的解码文本**逐一对比,
并给出裸 `0xB1..0xB9` 的逐码计数 (迁移量 = 这些字节的处数)。

只读; 产物写 temp/cmp_geom_text.json。
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402

BASE_GATE, GATE = 0xB1, 0xBA
LEGACY = {0xB2: '\u952e', 0xB3: '\u7ec3', 0xB4: '\u7528',
          0xB6: '\u51fb', 0xB7: '\u5c0f', 0xB8: '\u65f6', 0xB9: '\u6309'}
ICON = {0xB1: '\u25b3', 0xB5: '\u2715'}
CONTS = (('EN_STRINGS.RES@MENU', T.MENU_LBA, 25, 'LANG'),
         ('EN_STRINGS.RES@GR', T.GR_LBA, 902, 'LANG'),
         ('EN_SPECIAL_FEATURE.XML', T.MENU_LBA, 283, 'SFXML'))


def blob_of(iso, lba, idx):
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    subs = T.lzo_subs(raw)
    return (b''.join(s[0] for s in subs) if subs else bytes(raw)), e


def walk(data):
    """基底闸门语义: 返回 (裸 0xB1..0xB9 计数, 逐码)。"""
    n, per, i, m = 0, {}, 0, len(data)
    while i < m:
        c = data[i]
        if T.LEAD_LO <= c < BASE_GATE:
            i += 2
            continue
        if BASE_GATE <= c < GATE:
            n += 1
            per[c] = per.get(c, 0) + 1
        i += 1
    return n, per


def dec(data, pair_dec, codes):
    o, i, n = [], 0, len(data)
    while i < n:
        v = data[i]
        if v < 0x80:
            o.append(chr(v)); i += 1
        elif T.LEAD_LO <= v < BASE_GATE:
            if i + 1 >= n:
                o.append('\uFFFD'); i += 1; continue
            o.append(pair_dec.get((v, data[i + 1]), '\uFFFD')); i += 2
        else:
            o.append(codes.get(v) or LEGACY.get(v) or ICON.get(v) or ('<%02X>' % v)); i += 1
    return ''.join(o)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_a', help='待查盘 (几何盘)')
    ap.add_argument('--ref-iso', required=True)
    ap.add_argument('--out', default=HERE)
    a = ap.parse_args(argv)
    cs = T.Charset()
    pair_dec = dict(cs.pair_of)
    codes = {int(k) if isinstance(k, int) else k: v for k, v in cs.codes.items()}
    rows = []
    ia, ib = T.Iso(a.iso_a), T.Iso(a.ref_iso)
    for (tag, lba, idx, kind) in CONTS:
        ba, ea = blob_of(ia, lba, idx)
        bb, eb = blob_of(ib, lba, idx)
        na, pa = walk(ba)
        nb, pb = walk(bb)
        # 逐字符: 两张盘都用**基底语义**解
        if kind == 'LANG':
            ra = [bytes(e.data) for e in T.parse_lang(ba)[0]]
            rb = [bytes(e.data) for e in T.parse_lang(bb)[0]]
        else:
            ra = [d for (_k, _o, _l, d) in T.parse_sfxml(ba)]
            rb = [d for (_k, _o, _l, d) in T.parse_sfxml(bb)]
        ndiff, first = 0, None
        for k, (x, y) in enumerate(zip(rb, ra)):
            if dec(y, pair_dec, codes) != dec(x, pair_dec, codes):
                ndiff += 1
                if first is None:
                    first = '#%d 基底 %r ≠ 几何 %r' % (
                        k, dec(x, pair_dec, codes)[:40], dec(y, pair_dec, codes)[:40])
        rows.append(dict(tag=tag, blob_a=len(ba), blob_b=len(bb),
                         identical_blob=bool(ba == bb),
                         payloads_a=len(ra), payloads_b=len(rb),
                         char_diff=ndiff, first=first,
                         bare_a=na, bare_b=nb,
                         per_a={('0x%02X' % k): v for k, v in sorted(pa.items())},
                         per_b={('0x%02X' % k): v for k, v in sorted(pb.items())},
                         stored_a=ea['stored'], stored_b=eb['stored']))
    ia.close(); ib.close()
    print('=' * 96)
    print('几何盘 vs 基底盘 —— 3 个文本容器的基底语义比对 (只读)')
    print('  几何盘 = %s' % os.path.abspath(a.iso_a))
    print('  基底盘 = %s' % os.path.abspath(a.ref_iso))
    print('=' * 96)
    for r in rows:
        print('  %-24s blob %d / %d %s · 载荷 %d / %d · 逐字符不同 = **%d**'
              % (r['tag'], r['blob_a'], r['blob_b'],
                 '逐字节相同' if r['identical_blob'] else '★ 不同',
                 r['payloads_a'], r['payloads_b'], r['char_diff']))
        print('       裸 0xB1..0xB9 (基底语义): 几何 %4d 处 %s' % (r['bare_a'], r['per_a']))
        print('                                基底 %4d 处 %s' % (r['bare_b'], r['per_b']))
        if r['first']:
            print('       首差: %s' % r['first'])
    json.dump(dict(iso_a=os.path.abspath(a.iso_a), ref_iso=os.path.abspath(a.ref_iso),
                   rows=rows), io.open(os.path.join(a.out, 'cmp_geom_text.json'), 'w',
                                       encoding='utf-8', newline='\n'),
              ensure_ascii=False, indent=1)
    print()
    print('[out] %s' % os.path.join(a.out, 'cmp_geom_text.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
