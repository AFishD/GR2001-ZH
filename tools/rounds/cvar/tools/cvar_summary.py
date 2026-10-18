# -*- coding: utf-8 -*-
r"""cvar_summary.py — 由 components.json 生成给报告/指南用的汇总数字

用法: python cvar_summary.py --components components.json --out summary.json
"""
import argparse
import json
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048


def ents(d, lba):
    b = lba * SEC
    noff = struct.unpack_from('<I', d, b + 0x10)[0]
    nend = struct.unpack_from('<I', d, b + 0x04)[0]
    names = [x.decode('latin-1') for x in d[b + noff:b + nend].split(b'\x00') if x]
    return [(nm, list(struct.unpack_from('<12I', d, b + 0x830 + 48 * i)))
            for i, nm in enumerate(names)], b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--components', required=True)
    ap.add_argument('--orig', default=r'..\GR_EN_ORIG\GR_EN_ORIG.iso')
    ap.add_argument('--zh', default=r'..\GR_ZH113b\GR_ZH113b.iso')
    ap.add_argument('--out', required=True)
    x = ap.parse_args()
    C = json.load(open(x.components, encoding='utf-8'))
    out = {'components': {}, 'p6_categories': {}, 'font_res': {}}

    for comp, c in C['components'].items():
        items = []
        for k, it in c['items'].items():
            items.append({'item': k, 'runs': it['runs'], 'bytes': it['bytes'],
                          'iso_lo': it['iso_lo'], 'iso_hi': it['iso_hi'],
                          'kind': it['kind']})
        items.sort(key=lambda z: -z['bytes'])
        out['components'][comp] = {'runs': len(c['runs']), 'bytes': c['bytes'],
                                   'items': items}

    # ---- P6 归类
    cats = {}
    for it in out['components'].get('P6_other', {}).get('items', []):
        n = it['item']
        if '_MESSAGE_MC_' in n:
            k = 'P6a *_MESSAGE_MC_*.RSB 调色板/像素改写 (20 个条目, 5 语言 x MC_1..4)'
        elif '空隙' in n and '.ATR' in n:
            k = 'P6b .ATR 条目之间的对齐空隙 (角色/武器/爆破/狙击模型表尾部)'
        elif n.endswith('COMMON.PAK [#3451]'):
            k = 'P6c GR.IMG::COMMON.PAK (与 MENU 那份重复的字库 PAK)'
        elif '_SPECIAL_FEATURE.XML' in n or 'OPTIONS.XML' in n or 'UNLOCKED' in n:
            k = 'P6d 非英语 SPECIAL_FEATURE/OPTIONS XML'
        elif 'PKM.BMZ' in n:
            k = 'P6e MENU.IMG::PKM.BMZ'
        elif 'NTSC_IKE.RES' in n:
            k = 'P6f MENU.IMG::NTSC_IKE.RES'
        elif 'EN_STRINGS.TXT' in n:
            k = 'P6g EN_STRINGS.TXT (MENU, 被搬到 MENU.IMG 末尾)'
        elif re.search(r'_(STRINGS)\.(RES|TXT)', n) and 'EN_' not in n:
            k = 'P6h 非英语 DE/ES_STRINGS.RES / .TXT'
        elif '空隙' in n and '.PSS' in n:
            k = 'P6i .PSS 视频条目之间的空隙 (DS_INTRO/OUTRO 调色板)'
        elif '空隙' in n and '.SS' in n:
            k = 'P6j BNK_*.SS 音色库条目之间的空隙'
        elif '_ATR.DIR' in n:
            k = 'P6k *_ATR.DIR 索引表'
        else:
            k = 'P6z 其它: ' + n
        a = cats.setdefault(k, {'items': 0, 'runs': 0, 'bytes': 0})
        a['items'] += 1
        a['runs'] += it['runs']
        a['bytes'] += it['bytes']
    out['p6_categories'] = cats

    # ---- FONT.RES 内部头 (EN vs ZH)
    for tag, p in (('EN', x.orig), ('ZH', x.zh)):
        d = open(p, 'rb').read()
        for lba, nm in ((776286, 'MENU.IMG'), (19175, 'GR.IMG')):
            E, b = ents(d, lba)
            for i, (n2, f) in enumerate(E):
                if n2 == 'FONT.RES':
                    blob = bytes(d[b + f[8]:b + f[8] + f[6]])
                    f0, f1, f2 = struct.unpack_from('<3I', blob, 0)
                    tail = blob[f0 + 8:]
                    out['font_res']['%s::%s' % (tag, nm)] = {
                        'img_stored': f[6], 'img_real': f[7], 'img_off': f[8],
                        'internal_f0': f0, 'internal_f1': f1, 'internal_f2': f2,
                        'f0_plus8_eq_stored': f0 + 8 == f[6],
                        'f1_eq_img_real': f1 == f[7],
                        'tail_len_after_f0plus8': len(tail),
                        'tail_all_zero': all(c == 0 for c in tail),
                        'name': blob[0x0D:0x0D + 24].split(b'\x00')[0].decode('latin-1'),
                    }
        del d

    # ---- 字库容器 (w/h/px_size) EN vs ZH
    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
    import cvar_build as CB
    out['atlas'] = {}
    for tag, p in (('EN', x.orig), ('ZH', x.zh)):
        d = open(p, 'rb').read()
        for lba, nm in ((776286, 'MENU.IMG'), (19175, 'GR.IMG')):
            pk = CB.check_pak(d, nm, lba)
            r1 = pk['records'][1]
            out['atlas']['%s::%s' % (tag, nm)] = {
                'w': r1['w'], 'h': r1['h'], 'px_size': r1['px_size'],
                'half': r1['w*h/2'], 'inv1': r1['inv1_px_size_eq_half_plus16'],
                'inv2': r1['inv2_half_mod2048_eq0'], 'pak_stored': pk['pak_stored'],
                'all_records': [(r['name'], r['w'], r['h'], r['px_size'])
                                for r in pk['records']]}
        del d

    with open(x.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print('== 部件汇总 ==')
    for comp in ('P1_elf', 'P2_atlas', 'P3_ft', 'P4_text', 'P5_book', 'P6_other'):
        c = out['components'].get(comp)
        if c:
            print('  %-10s runs=%-6d bytes=%-8d 结构数=%d'
                  % (comp, c['runs'], c['bytes'], len(c['items'])))
    print('\n== P6 分类 ==')
    for k in sorted(cats, key=lambda z: -cats[z]['bytes']):
        a = cats[k]
        print('  %-70s 项=%-4d runs=%-6d bytes=%d' % (k, a['items'], a['runs'], a['bytes']))
    print('\n== FONT.RES 内部头 ==')
    for k, v in out['font_res'].items():
        print('  %-14s IMG stored=%-6d real=%-7d | 内部 f0=%-6d f1=%-7d f2=%-6d'
              % (k, v['img_stored'], v['img_real'], v['internal_f0'],
                 v['internal_f1'], v['internal_f2']))
        print('                 f0+8==stored:%s  f1==IMG.real:%s  尾部 %d B 全零=%s  name=%r'
              % (v['f0_plus8_eq_stored'], v['f1_eq_img_real'],
                 v['tail_len_after_f0plus8'], v['tail_all_zero'], v['name']))
    print('\n== 字库容器 (new_font_revised) ==')
    for k, v in out['atlas'].items():
        print('  %-14s w=%-5d h=%-4d px_size=0x%X half=%-7d inv1=%s inv2=%s PAK=%d'
              % (k, v['w'], v['h'], v['px_size'], v['half'], v['inv1'], v['inv2'],
                 v['pak_stored']))
    print('→ %s' % x.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
