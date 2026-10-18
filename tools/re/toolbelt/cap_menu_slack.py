# -*- coding: utf-8 -*-
r"""cap_menu_slack.py -- round73 裁决用: MENU.IMG 里 COMMON.PAK / FONT.RES 的槽位与"身后余量"。

只读。回答一个问题：L1（把 new_font_revised 记录加高到 1024，记录 +0x40300 字节）
到底要不要搬动 MENU.IMG 里别的东西？身后有没有余量可以原地长大？

用法: python tools/re/toolbelt/cap_menu_slack.py [--iso PATH] [--json OUT]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

DEFAULT_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
MENU_LBA = 776286
SEARCH = 700


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=DEFAULT_ISO)
    ap.add_argument('--json', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                   'temp', 'r75', 'menu_slack.json'))
    a = ap.parse_args()
    iso = tcslib.Iso(a.iso)
    ents = []
    for i in range(SEARCH):
        e = iso.img_entry(MENU_LBA, i)
        if e is None:
            break
        ents.append(dict(idx=i, name=e['name'], off=e['off'], stored=e['stored'],
                         real=e['real'], iso_off=e['iso_off']))
    iso.close()

    # order by off; compute each entry's tail gap to the next entry start
    byoff = sorted(ents, key=lambda e: e['off'])
    for k, e in enumerate(byoff):
        nxt = byoff[k + 1] if k + 1 < len(byoff) else None
        e['next_name'] = nxt['name'] if nxt else None
        e['gap_to_next'] = (nxt['off'] - (e['off'] + e['stored'])) if nxt else None

    rep = dict(iso=a.iso, menu_lba=MENU_LBA, entries=byoff)

    def find(nm):
        for e in byoff:
            if e['name'] == nm:
                return e
        return None

    pak, ft = find('COMMON.PAK'), find('FONT.RES')
    rep['common_pak'] = pak
    rep['font_res'] = ft
    if pak:
        rec = 0x4044C                       # new_font_revised 记录长度 (现役实测)
        rep['L1_needs'] = dict(record_off_in_pak=0x1031, old_record_len=rec,
                               new_record_len=rec + 0x40000,
                               pak_growth=0x40000,
                               pak_new_len=pak['stored'] + 0x40000,
                               gap_after_pak=pak['gap_to_next'],
                               inplace_possible=(pak['gap_to_next'] or 0) >= 0x40000)
    txt = json.dumps(rep, indent=1, ensure_ascii=False, default=str)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, 'w', encoding='utf-8') as f:
        f.write(txt)
    for e in byoff:
        if e['off'] < 0x400000 or (e['gap_to_next'] or 0) > 20000 or e['name'] in (
                'COMMON.PAK', 'FONT.RES'):
            print('%-28s idx=%-3d off=0x%08X stored=%-8d real=%-8d gap_to_next=%-10s (%s)'
                  % (e['name'], e['idx'], e['off'], e['stored'], e['real'],
                     e['gap_to_next'], e['next_name']))
    print()
    print(json.dumps(rep.get('L1_needs'), indent=1, ensure_ascii=False))
    # free gaps larger than 4 KB
    gaps = [(e['gap_to_next'], e['name'], e['next_name'], e['off'] + e['stored'])
            for e in byoff if (e['gap_to_next'] or 0) > 4096]
    gaps.sort(reverse=True)
    print()
    print('== >4KB 的空隙 (off_end, len) ==')
    for g, a_, b_, off in gaps[:12]:
        print('   0x%08X  len=%-9d  between %s -> %s' % (off, g, a_, b_))
    print('   total gaps >4KB = %d bytes' % sum(g for g, *_ in gaps))
    print()
    scan_elf_literals(a.iso)


ELF_LBA, SEC = 295, 2048


def scan_elf_literals(iso_path):
    """ELF 主段里有没有硬编码的 MENU.IMG 内部偏移 / COMMON.PAK 偏移 (原版 & 现役两份)。"""
    import struct
    targets = {
        'common.pak off in IMG': 0x57400,
        'font_revised rec off': 0x58431,
        'new_font_revised name': 0x5B0C0,      # placeholder, name is ASCII not an int
        'pak end in IMG': 0xB9113,
        'FONT.RES off in IMG': 0xB9120,
        'pak walk end (rel)': 0x61D0F,
        'pak walk end +4': 0x61D13,
        'font rec len': 0x4044C,
        'MENU abs off of pak': 776286 * SEC + 0x57400,
        'MENU abs off of FONT.RES': 776286 * SEC + 0xB9120,
    }
    with open(iso_path, 'rb') as f:
        f.seek(ELF_LBA * SEC)
        head = f.read(0x40)
        (phoff,) = struct.unpack_from('<I', head, 0x1C)
        (phes, phn) = struct.unpack_from('<HH', head, 0x2A)
        f.seek(ELF_LBA * SEC + phoff)
        ph = f.read(phes * phn)
        end = 0
        for i in range(phn):
            t, o, v, pa, fs_, ms, fl, al = struct.unpack_from('<8I', ph, i * phes)
            if t == 1:
                end = max(end, o + fs_)
        f.seek(ELF_LBA * SEC)
        d = f.read(end)
    print('== ELF(%s) 里搜硬编码偏移 (4 字节小端) ==' % os.path.basename(iso_path))
    for k, v in targets.items():
        pat = struct.pack('<I', v & 0xFFFFFFFF)
        n = d.count(pat)
        print('  %-26s 0x%08X  hits=%d' % (k, v & 0xFFFFFFFF, n))


main()
