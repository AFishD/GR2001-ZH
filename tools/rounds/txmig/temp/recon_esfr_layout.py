# -*- coding: utf-8 -*-
r"""recon_esfr_layout.py — ES/FR/DE/IT 语言表的 IMG 布局与容量侦察 (只读)

回答的问题 (任务 ② 的前置):
  1. ES/FR/DE/IT 四张表在 MENU.IMG / GR.IMG 里的条目字段 (off/stored/real) 与相邻条目间距;
  2. `parse_lang` 的 `used_end` 之后还有多少"陈旧尾巴"可吃 (迁移增长只能吃这个);
  3. 迁移增长量 = 载荷里裸旧码处数 (每处 +1 B) ⇒ 能不能在槽内吸收。
只读, 不改任何文件。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402

BASE_GATE, GATE = 0xB1, 0xBA
WANT = ('EN_STRINGS.RES', 'ES_STRINGS.RES', 'FR_STRINGS.RES',
        'DE_STRINGS.RES', 'IT_STRINGS.RES')


def walk(data):
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


def main(argv):
    iso_p = argv[0] if argv else os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                              'GR_ZH113b.iso')
    out = argv[1] if len(argv) > 1 else HERE
    iso = T.Iso(iso_p)
    rows = []
    for (img, lba) in (('MENU.IMG', T.MENU_LBA), ('GR.IMG', T.GR_LBA)):
        n = 0
        for i in range(1000):
            e = iso.img_entry(lba, i)
            if not e['name'] or e['name'].startswith('?') or e['off'] == 0:
                break
            n += 1
        for i in range(n):
            e = iso.img_entry(lba, i)
            if e['name'] not in WANT:
                continue
            nx = iso.img_entry(lba, i + 1) if i + 1 < n else None
            raw = iso.read(e['iso_off'], e['stored'])
            subs = T.lzo_subs(raw)
            blob = b''.join(s[0] for s in subs) if subs else raw
            for s in subs:
                assert s[0] != b'' or True
            rec = dict(img=img, idx=i, name=e['name'], off=e['off'], stored=e['stored'],
                       real=e['real'], iso_off=e['iso_off'], decomp=len(blob),
                       n_sub=len(subs), sub_sizes=[s[2] for s in subs],
                       next_idx=(i + 1 if nx else None),
                       next_name=(nx['name'] if nx else None),
                       next_off=(nx['off'] if nx else None),
                       img_gap=(nx['off'] - e['off'] - e['stored']) if nx else None)
            rec['raw_n'], rec['raw_per'] = walk(blob)
            try:
                ents, used = T.parse_lang(blob)
                rec['lang_ok'] = True
                rec['entries'], rec['used'] = len(ents), used
                rec['tail_free'] = len(blob) - used
                pn, pp = 0, {}
                for x in ents:
                    k, p = walk(x.data)
                    pn += k
                    for kk, vv in p.items():
                        pp[kk] = pp.get(kk, 0) + vv
                rec['payload_n'], rec['payload_per'] = pn, pp
                rec['growth'] = pn                       # 每处 +1 B
                rec['fits'] = pn <= rec['tail_free']
                # 最后 3 条目 (看 used_end 之后是什么)
                rec['last_ents'] = [dict(off=x.data_off, length=x.length,
                                         head=x.data[:12].hex()) for x in ents[-3:]]
                rec['tail_bytes'] = blob[used:used + 32].hex()
            except Exception as ex:                                        # noqa: BLE001
                rec['lang_ok'] = False
                rec['why'] = str(ex)[:120]
                rec['tail_free'] = None
                rec['head64'] = blob[:64].hex()
            rows.append(rec)
    json.dump(dict(iso=os.path.abspath(iso_p), rows=rows),
              open(os.path.join(out, 'recon_esfr_layout.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('%-9s %-4s %-16s %9s %8s %7s %7s %6s %8s %s'
          % ('IMG', '#', 'name', 'real', 'stored', 'decomp', 'used', 'tail', 'payload', 'fits'))
    for r in rows:
        print('%-9s %-4d %-16s %9d %8d %7d %7s %6s %8s %s'
              % (r['img'], r['idx'], r['name'], r['real'], r['stored'], r['decomp'],
                 r.get('used', '-'), r.get('tail_free', '-'), r.get('payload_n', '-'),
                 r.get('fits', 'n/a')))
        if r['lang_ok']:
            print('         sub_sizes=%s  逐码 %s  增长 %d B  (尾巴 %d B)'
                  % (r['sub_sizes'], r['payload_per'], r['growth'], r['tail_free']))
            print('         last_ents=%s' % r['last_ents'])
            print('         tail_bytes=%s' % r['tail_bytes'])
        else:
            print('         LANG 解析失败: %s' % r['why'])
            print('         head64=%s  全 blob 裸码 %s' % (r['head64'], r['raw_per']))
        print('         IMG 间距: next=#%s %s off=0x%X ⇒ gap=%s ; off=0x%X stored=%d real=%d'
              % (r['next_idx'], r['next_name'], r['next_off'] or 0, r['img_gap'],
                 r['off'], r['stored'], r['real']))
    iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
