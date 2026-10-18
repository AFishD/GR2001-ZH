# -*- coding: utf-8 -*-
r"""migrate_scan_all_entries.py — ★ 全 IMG 条目扫掠: 除了那 3 个文本容器, 还有谁含旧单字节码?

    python tools/re/toolbelt/migrate_scan_all_entries.py <iso> [--gate 0xBA] [--base-gate 0xB1] [--out DIR]

为什么必须做这一步: 迁移范围按 LEAD §1.4 是"3 个容器"; 但引擎在闸门 0xBA 下把
`0xB1..0xB9` 一律当前导 —— 只要**任何**被渲染的资源里还有裸旧码, 就一样会吞字。
`dump_all_text.py` 只导出 5 个来源 (MENU:RES / MENU:SF / MENU:TXT / GR:RES / GR:ATR),
**`GR:MIS`(任务简报) 根本不在它的导出范围里** ⇒ "MIS 是英文原文、0 处" 这句话没有 dump 证据。

本工具把 MENU.IMG / GR.IMG 的**所有条目**解压后按**基底闸门语义**扫一遍, 列出
"哪些条目里以单字节形式出现 `0xB1..gate-1`" —— 用来回答: 迁移范围是不是真的只有 3 个容器。
只读: 不改任何文件。
"""
import argparse
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402

# 已知的 3 个文本容器 (迁移范围)
KNOWN = {('MENU.IMG', 25), ('GR.IMG', 902), ('MENU.IMG', 283)}


def scan_body(blob, base_gate, gate):
    """按基底闸门语义: 返回 (裸 [base_gate,gate) 字节数, 逐码计数)。"""
    n, per, i, m = 0, {}, 0, len(blob)
    while i < m:
        c = blob[i]
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
    ap.add_argument('--gate', default='0xBA')
    ap.add_argument('--base-gate', default='0xB1')
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    base_gate, gate = int(a.base_gate, 16), int(a.gate, 16)
    out = os.path.abspath(a.out or os.path.join(REPO, 'work', 'builds', 'GR_TXMIG',
                                                'temp'))
    os.makedirs(out, exist_ok=True)
    iso = T.Iso(a.iso)
    res, hits_total, n_ent = [], 0, 0
    for (img, lba) in (('MENU.IMG', T.MENU_LBA), ('GR.IMG', T.GR_LBA)):
        n_all = 0
        for i in range(4096):
            e = iso.img_entry(lba, i)
            if not e['name'] or e['name'].startswith('?') or e['off'] == 0:
                break
            n_all += 1
            n_ent += 1
            if e['stored'] == 0:
                continue
            raw = iso.read(e['iso_off'], e['stored'])
            subs = T.lzo_subs(raw)
            blob = b''.join(s[0] for s in subs) if subs else raw
            n, per = scan_body(blob, base_gate, gate)
            if n:
                hits_total += n
                res.append(dict(img=img, idx=i, name=e['name'], stored=e['stored'],
                                decomp=len(blob), n=n,
                                per={('0x%02X' % k): v for k, v in sorted(per.items())},
                                known=(img, i) in KNOWN))
        print('[img] %-9s 条目 %d' % (img, n_all))
    print('[sum] 条目合计 %d ; 含裸 `0xB1..0x%02X` 的条目 %d 个 / 处数合计 %d'
          % (n_ent, gate - 1, len(res), hits_total))
    for d in sorted(res, key=lambda x: -x['n']):
        print('   %-9s #%-4d %-28s 解压 %8d B · 裸码 %5d 处 %s %s'
              % (d['img'], d['idx'], d['name'], d['decomp'], d['n'],
                 d['per'], '← 已知迁移范围 (abc 之外!)' if not d['known'] else '(已知容器)'))
    json.dump(dict(iso=os.path.abspath(a.iso), base_gate=base_gate, gate=gate,
                   entries=n_ent, hits=hits_total, items=res),
              open(os.path.join(out, 'scan_all_entries.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
