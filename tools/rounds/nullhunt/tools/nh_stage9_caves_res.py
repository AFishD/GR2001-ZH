# -*- coding: utf-8 -*-
r"""nh_stage9_caves_res.py
 (a) 检查汉化所用 code cave 在英文原盘上是否真的是"空白/自由"空间
 (b) 列出 MENU.IMG 全部条目名 + GR.IMG 中与火箭筒/L1(小队/地图)相关的候选名
 (c) 对两份 IMG 的全部条目做**可读性验证**: 区间在容器内、非全零、前后哨兵字节
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N   # noqa: E402
import nh_elf as E   # noqa: E402
import nh_stage3_elf as S3   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ELF 差异 run #48..#53 与 #56..#67 的 VA 区间 (来自 stage4) —— 即汉化写入的 cave
CAVES = [
    ('sceRemove body',     0x416ED0, 0x417037),
    ('sceMkdir  tail',     0x417050, 0x41713B),
    ('sceFormat mid',      0x417150, 0x4171C7),
    ('sceFormat tail',     0x417200, 0x41721A),
    ('sceDopen  tail',     0x417500, 0x4175BF),
    ('sceDclose tail',     0x417600, 0x4176E7),
    ('sceIpuInit',         0x411690, 0x4116A7),
    ('strlwr',             0x407078, 0x40708B),
    ('strupr',             0x408928, 0x40893B),
    ('s_Pool #0',          0x565672, 0x56571B),
    ('s_Pool #1',          0x565730, 0x56576F),
    ('s_Pool #2',          0x565776, 0x5657DB),
    ('s_Pool #3',          0x5657E2, 0x5658BF),
    ('s_Pool #4',          0x565900, 0x5659A7),
    ('s_Pool #5',          0x565A00, 0x565A46),
    ('@5689',              0x577FA0, 0x577FB5),
    ('@5690',              0x577FC0, 0x578006),
    ('@5694',              0x578010, 0x57801F),
    ('@5695',              0x578028, 0x578032),
    ('@5696',              0x578040, 0x578061),
    ('@5698',              0x578068, 0x578073),
]

ROCKET_RE = re.compile(r'rocket|missile|explo|proj|muzzle|flash|smoke|grenade|rpg|at4|law|warhead|launch|impact', re.I)
L1_RE = re.compile(r'(^|[^a-z])(map|squad|team|order|commo|radio|roster|hud|compass|pda|brief|objective|'
                   r'icon|waypoint|marker|tactical|order_|gui|menu|cursor|status|unit|buddy|fireteam)', re.I)


def main():
    e_en, _ = S3.load_elf('EN_ORIG')
    e_zh, _ = S3.load_elf('ZH113b_fix')
    buf = io.StringIO()
    buf.write('== (a) 汉化 code cave 在英文原盘上的原始内容 ==\n')
    buf.write('%-18s %-10s %-10s %-6s  %s\n'
              % ('cave', 'VA_start', 'VA_end', '字节', 'EN 原盘内容 (是否全零/是否像数据)'))
    for (nm, va0, va1) in CAVES:
        o0, _ = e_en.va2off(va0)
        o1, _ = e_en.va2off(va1)
        if o0 is None:
            buf.write('%-18s 0x%08X  (不在 PT_LOAD 内)\n' % (nm, va0))
            continue
        blob = e_en.b[o0:o1]
        nz = sum(1 for c in blob if c)
        allz = 'ALL-ZERO' if nz == 0 else '%d/%d 非零' % (nz, len(blob))
        kind = 'zeros' if nz == 0 else ('instruction-like' if nz > len(blob) * 0.5 else 'sparse')
        buf.write('%-18s 0x%08X 0x%08X %-6d %-14s %s\n'
                  % (nm, va0, va1, len(blob), allz, kind))
        buf.write('        EN: %s\n' % blob[:40].hex(' '))
        buf.write('        ZH: %s\n' % e_zh.b[o0:o0 + 40].hex(' '))

    # ---------------- (b)(c) 资源 ----------------
    iso_en = N.Iso(N.ISO['EN_ORIG'])
    iso_zh = N.Iso(N.ISO['ZH113b_fix'])
    outnames = io.StringIO()
    filt = io.StringIO()
    read = io.StringIO()
    for tag, iso in (('EN_ORIG', iso_en), ('ZH113b_fix', iso_zh)):
        for path in ('/MENU.IMG;1', '/GR.IMG;1'):
            f = iso.files()[path]
            ents, hdr, names = iso.img_entries(f['lba'], None)
            base = f['lba'] * N.SEC
            outnames.write('#### %s %s  (%d 条)\n' % (tag, path, len(ents)))
            for e in ents:
                outnames.write('%-5d %-30s off=%-10d stored=%-9d real=%-9d\n'
                               % (e['idx'], e['name'], e['off'], e['stored'], e['real']))
            # 过滤
            for e in ents:
                if ROCKET_RE.search(e['name']) or L1_RE.search(e['name']):
                    filt.write('%-12s %-13s %-5d %-30s off=%-10d stored=%-9d real=%-9d\n'
                               % (tag, path.replace('/', ''), e['idx'], e['name'],
                                  e['off'], e['stored'], e['real']))
            # 可读性
            bad = []
            allzero = []
            for e in ents:
                if e['off'] == 0 and e['stored'] == 0:
                    continue
                end = e['off'] + e['stored']
                if e['off'] > f['size'] or end > f['size']:
                    bad.append((e, 'off/stored 超出容器声明 size'))
                    continue
                blob = iso.rd(base + e['off'], e['stored'])
                if e['stored'] and max(blob) == 0:
                    allzero.append(e)
            read.write('%-12s %-13s 条目=%-5d 越界=%-3d 数据全零=%-3d\n'
                       % (tag, path, len(ents), len(bad), len(allzero)))
            for (e, why) in bad:
                read.write('    ★越界 #%d %s off=%d stored=%d end=%d size=%d (%s)\n'
                           % (e['idx'], e['name'], e['off'], e['stored'], end, f['size'], why))
            for e in allzero:
                read.write('    ★全零 #%d %s off=%d stored=%d real=%d\n'
                           % (e['idx'], e['name'], e['off'], e['stored'], e['real']))
    iso_en.close()
    iso_zh.close()

    with open(os.path.join(N.EVID, 'menu_img_names.txt'), 'w', encoding='utf-8') as fh:
        fh.write(outnames.getvalue())
    with open(os.path.join(N.EVID, 'gr_img_names_filtered.txt'), 'w', encoding='utf-8') as fh:
        fh.write(filt.getvalue())
    with open(os.path.join(N.EVID, 'resource_candidates.md'), 'w', encoding='utf-8') as fh:
        fh.write('# 火箭筒开火 / L1(小队·地图) 界面候选资源\n\n## cave 空间核查\n\n```\n'
                 + buf.getvalue() + '```\n\n## 可读性验证 (两份 IMG 全条目)\n\n```\n'
                 + read.getvalue() + '```\n\n## 候选条目 (名字过滤)\n\n```\n'
                 + filt.getvalue()[:60000] + '```\n')
    print(buf.getvalue())
    print(read.getvalue())
    print('候选条目数 =', filt.getvalue().count('\n'))
    print('→ evidence/menu_img_names.txt, gr_img_names_filtered.txt, resource_candidates.md')


if __name__ == '__main__':
    main()
