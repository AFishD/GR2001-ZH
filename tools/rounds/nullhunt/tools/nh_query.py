# -*- coding: utf-8 -*-
r"""nh_query.py — 针对 stage5 已导出的条目字段做定点查询/校验 (只读)

用法: python nh_query.py [关键词...]
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
J = os.path.join(N.EVID, 'stage5_img_fields.json')


def main():
    db = json.load(open(J, encoding='utf-8'))
    keys = sys.argv[1:]
    out = io.StringIO()
    out.write('定点查询: %s\n' % (keys or '(全部摘要)'))
    # 1) header/name/hash 字节级对比
    out.write('\n== 头部 / 名字区 / 哈希区 字节级对比 ==\n')
    for cont in ('/MENU.IMG;1', '/GR.IMG;1'):
        for tag in ('ZH113b_fix',):
            pass
    for cont in ('/MENU.IMG;1', '/GR.IMG;1'):
        en = db['EN_ORIG|' + cont]
        zh = db['ZH113b_fix|' + cont]
        # 头部由 lba 决定, 重新从盘读
        lba = 776286 if 'MENU' in cont else 19175
        iso_en = N.Iso(N.ISO['EN_ORIG'])
        iso_zh = N.Iso(N.ISO['ZH113b_fix'])
        h_en = iso_en.img_header(lba)
        for label, off, ln in (
                ('头部 0x000..0x830', 0, N.TAB_OFF),
                ('条目表', N.TAB_OFF, N.TAB_STEP * len(en)),
                ('名字区', h_en['names_start'], h_en['names_end'] - h_en['names_start']),
                ('哈希区', h_en['h8'], 16384),
                ('数据区前 1MB', 0x10000, 1 << 20)):
            base = lba * N.SEC
            a = iso_en.rd(base + off, ln)
            b = iso_zh.rd(base + off, ln)
            neq = sum(1 for x, y in zip(a, b) if x != y)
            out.write('  %-16s %-18s 不同 %8d / %-9d %s\n'
                      % (cont, label, neq, ln, 'SAME' if neq == 0 else '★DIFF'))
        iso_en.close()
        iso_zh.close()

    # 2) 关键条目
    out.write('\n== 关键条目字段 (EN_ORIG vs ZH113b_fix) ==\n')
    watch = keys or ['EN_STRINGS.RES', 'EN_STRINGS.TXT', 'COMMON.PAK', 'FONT.RES',
                     'NTSC_IKE.RES', 'RPG7.GUN', 'AT4.GUN', 'MISSILE.PRJ', 'RPG7.PRJ']
    for cont in ('/MENU.IMG;1', '/GR.IMG;1'):
        en = {e['name']: e for e in db['EN_ORIG|' + cont]}
        zh = {e['name']: e for e in db['ZH113b_fix|' + cont]}
        for w in watch:
            for nm in sorted(set([k for k in en if w.upper() in k.upper()]
                                 + [k for k in zh if w.upper() in k.upper()])):
                a, b = en.get(nm), zh.get(nm)
                fa = ('#%-5d stored=%-10s real=%-10s off=%-10s' %
                      (a['idx'], N.fmt(a['stored']), N.fmt(a['real']), N.fmt(a['off']))
                      ) if a else 'EN: (无)'
                fb = ('#%-5d stored=%-10s real=%-10s off=%-10s' %
                      (b['idx'], N.fmt(b['stored']), N.fmt(b['real']), N.fmt(b['off']))
                      ) if b else 'ZH: (无)'
                same = ''
                if a and b:
                    same = '  [字段全同]' if (a['stored'], a['real'], a['off']) == \
                        (b['stored'], b['real'], b['off']) else '  ★字段不同'
                out.write('  %-16s %-26s EN %s\n%47s ZH %s%s\n'
                          % (cont, nm, fa, '', fb, same))

    # 3) stored > real 全盘扫描 (截断风险)
    out.write('\n== [B] stored > real (读流截断风险) 全量 ==\n')
    tot = 0
    for k in sorted(db):
        hits = [e for e in db[k] if e['stored'] > e['real'] and e['off']]
        tot += len(hits)
        out.write('  %-28s %d 条\n' % (k, len(hits)))
        for e in hits:
            out.write('      #%-5d %-28s stored=%-10s real=%-10s off=%-10s d=%d\n'
                      % (e['idx'], e['name'], N.fmt(e['stored']), N.fmt(e['real']),
                         N.fmt(e['off']), e['stored'] - e['real']))
    out.write('  合计 %d 条\n' % tot)

    # 4) real==0 或 stored==0
    out.write('\n== stored==0 或 real==0 的条目 ==\n')
    for k in sorted(db):
        hits = [e for e in db[k] if e['off'] and (e['stored'] == 0 or e['real'] == 0)]
        if not hits:
            continue
        out.write('  %-28s %d 条\n' % (k, len(hits)))
        for e in hits[:80]:
            out.write('      #%-5d %-28s stored=%-8s real=%-8s off=%-10s raw=%s\n'
                      % (e['idx'], e['name'], N.fmt(e['stored']), N.fmt(e['real']),
                         N.fmt(e['off']), e['raw']))
    print(out.getvalue())
    with open(os.path.join(N.EVID, 'stage6_query.txt'), 'w', encoding='utf-8') as f:
        f.write(out.getvalue())


if __name__ == '__main__':
    main()
