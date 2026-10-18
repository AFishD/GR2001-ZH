# -*- coding: utf-8 -*-
r"""migrate_scan_lang_tables.py — 10 份 *_STRINGS.RES 拷件的**逐表体检** (只读)

    python tools/re/toolbelt/migrate_scan_lang_tables.py <iso> [--base-gate 0xB1] [--gate 0xBA]

`migrate_scan_all_entries.py` 的全 IMG 扫掠发现: 除 3 个已迁移容器外, **非英文语言表**
(DE/ES/FR/IT_STRINGS.RES, 各 2 份拷件) 里也有裸 `0xB1..0xB9`。它们**不在** LEAD §1.4
声明的迁移范围内。本工具把它们逐表说清楚: 能不能按 LANG 解析、装的是哪种语言、
"以单字节形式出现"的旧码有几处 —— 供 LEAD 裁决是否需要一并迁移。
只读, 不改任何文件。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402

LANGS = (('MENU.IMG', T.MENU_LBA), ('GR.IMG', T.GR_LBA))


def legacy_walk(data, base_gate, gate):
    """基底闸门语义下的裸 `[base_gate,gate)` 计数 (= legacy_singles 口径)。"""
    n, per, i, m = 0, {}, 0, len(data)
    while i < m:
        c = data[i]
        if 0xA1 <= c < base_gate:
            i += 2
            continue
        if base_gate <= c < gate:
            n += 1
            per[c] = per.get(c, 0) + 1
        i += 1
    return n, per


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--base-gate', default='0xB1')
    ap.add_argument('--gate', default='0xBA')
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    base_gate, gate = int(a.base_gate, 16), int(a.gate, 16)
    out = os.path.abspath(a.out or os.path.join(REPO, 'work', 'builds', 'GR_TXMIG',
                                                'temp'))
    iso = T.Iso(a.iso)
    cs = T.Charset()
    rows = []
    for (img, lba) in LANGS:
        for i in range(1000):
            e = iso.img_entry(lba, i)
            if not e['name'] or e['name'].startswith('?') or e['off'] == 0:
                break
            if not e['name'].endswith('STRINGS.RES'):
                continue
            raw = iso.read(e['iso_off'], e['stored'])
            subs = T.lzo_subs(raw)
            blob = b''.join(s[0] for s in subs) if subs else raw
            rec = dict(img=img, idx=i, name=e['name'], stored=e['stored'],
                       decomp=len(blob), lzo=bool(subs))
            # (a) 全 blob 裸计数 (含结构区/尾巴)
            rec['raw_n'], rec['raw_per'] = legacy_walk(blob, base_gate, gate)
            # (b) 按 LANG 解析后的**载荷**计数
            try:
                ents, used = T.parse_lang(blob)
                rec['lang_ok'] = True
                rec['entries'] = len(ents)
                rec['used'] = used
                n, per = 0, {}
                for x in ents:
                    k, p = legacy_walk(x.data, base_gate, gate)
                    n += k
                    for kk, vv in p.items():
                        per[kk] = per.get(kk, 0) + vv
                rec['payload_n'], rec['payload_per'] = n, per
                txt = ''.join(cs.decode(x.data)[0] for x in ents)
                rec['cjk'] = sum(1 for c in txt if '\u4e00' <= c <= '\u9fff')
                rec['ascii'] = sum(1 for c in txt if c.isascii() and c.isprintable())
                rec['sample'] = txt[:70]
            except Exception as ex:                                      # noqa: BLE001
                rec['lang_ok'] = False
                rec['why'] = str(ex)[:90]
                rec['head64'] = blob[:64].hex()
            rows.append(rec)
    print('[表] %d 份 *_STRINGS.RES 拷件' % len(rows))
    print('  %-9s %-4s %-18s %9s %6s %8s %8s %7s %7s'
          % ('IMG', '#', 'name', '解压B', '条目', 'LANG解析', '载荷旧码', '全blob', 'CJK'))
    agg = {}
    for r in rows:
        print('  %-9s %-4d %-18s %9d %6s %8s %8s %7d %7s'
              % (r['img'], r['idx'], r['name'], r['decomp'],
                 r.get('entries', '-'), 'OK' if r['lang_ok'] else '失败',
                 r.get('payload_n', '-'), r['raw_n'], r.get('cjk', '-')))
        if r['lang_ok']:
            k = r['name']
            a2 = agg.setdefault(k, [0, 0, 0])
            a2[0] += 1
            a2[1] += r['payload_n']
            a2[2] += r['raw_n']
    print()
    print('[汇] 按表名 (拷件数 / 载荷旧码合计 / 全 blob 裸计数合计):')
    for k in sorted(agg):
        print('   %-20s %d 份 · 载荷 %5d 处 · 全 blob %5d 处'
              % (k, agg[k][0], agg[k][1], agg[k][2]))
    json.dump(dict(iso=os.path.abspath(a.iso), base_gate=base_gate, gate=gate,
                   tables=rows), open(os.path.join(out, 'scan_lang_tables.json'), 'w',
                                      encoding='utf-8'), ensure_ascii=False, indent=1)
    iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
