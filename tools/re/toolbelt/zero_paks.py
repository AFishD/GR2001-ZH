# -*- coding: utf-8 -*-
r"""zero_paks.py — 盘点 4 个「引擎自己会加载」的 pak 条目（common/menu/loading/action）的余量

动机: 字体图集今天住在 COMMON.PAK 的 mode-0 记录里（引擎 LoadingTexturePak(0) 装载）。
      如果 MENU.PAK / LOADING.PAK / ACTION.PAK 里有足够余量，就能把「加高后的图集」
      作为**新记录**塞进去 —— 名字经 FindSurface 命中，不需要新的顶层条目名，
      也不需要动 diSearchFile 的名字表。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
os.makedirs(OUT, exist_ok=True)
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
LS = []


def say(s=''):
    print(s)
    LS.append(s)


def walk(pak):
    """返回 [dict(...)] 与终止原因"""
    ents = []
    q = 0
    while q + 8 <= len(pak):
        mode, nl = struct.unpack_from('<II', pak, q)
        if nl < 1 or nl > 64 or q + 8 + nl > len(pak):
            return ents, 'BAD nl @0x%X (mode=%d nl=%d)' % (q, mode, nl)
        nm = pak[q + 8:q + 8 + nl].split(b'\x00')[0].decode('latin-1', 'replace')
        r = q + 8 + nl
        if mode == 0:
            psm, w, h, clut = struct.unpack_from('<IIII', pak, r)
            r2 = r + 16 + clut
            px = struct.unpack_from('<I', pak, r2)[0]
            ents.append(dict(off=q, name=nm, mode=mode, psm=psm, w=w, h=h, clut=clut,
                             px=px, end=r2 + 4 + px))
            q = r2 + 4 + px
        elif mode in (1, 2, 3):
            # mode1: (见反编译 0x51B660) 读 4/4/4, 可能再读 clut + px
            psm, w, h = struct.unpack_from('<III', pak, r)
            r2 = r + 12
            if psm in (0x13, 0x14):
                cz = struct.unpack_from('<I', pak, r2)[0]
                r2 += 4 + cz
            px = struct.unpack_from('<I', pak, r2)[0]
            ents.append(dict(off=q, name=nm, mode=mode, psm=psm, w=w, h=h, clut=0,
                             px=px, end=r2 + 4 + px))
            q = r2 + 4 + px
        else:
            return ents, 'unknown mode=%d @0x%X' % (mode, q)
        if q == len(pak):
            return ents, 'EXACT-END'
        if q > len(pak):
            return ents, 'OVERRUN'
    return ents, 'loop-end'


for img, lba, size in (('MENU.IMG', 776286, 58300882), ('GR.IMG', 19175, 1550563328)):
    base = lba * 2048
    cnt = (struct.unpack_from('<I', iso.mm, base + 0x0C)[0] - 0x830) // 48
    names = [x.decode('latin-1') for x in
             bytes(iso.mm[base + struct.unpack_from('<I', iso.mm, base + 0x10)[0]:
                               base + struct.unpack_from('<I', iso.mm, base + 4)[0]]).split(b'\x00') if x]
    ents = [struct.unpack_from('<12I', iso.mm, base + 0x830 + 48 * i) for i in range(cnt)]
    say('=' * 78)
    say('%s: %d 条目' % (img, cnt))
    for i, n in enumerate(names):
        if n.upper().endswith('.PAK'):
            e = ents[i]
            say('  #%-5d %-16r off=0x%-9X stored=%-9d real=%-9d' % (i, n, e[8], e[6], e[7]))
            if e[6] > 8 << 20:
                say('        （>8MB，跳过 walk）')
                continue
            pak = iso.read(base + e[8], e[6])
            sub, why = walk(pak)
            used = sub[-1]['end'] if sub else 0
            say('        walk %d 记录, 结束 0x%X / 0x%X (%s) ⇒ 内部尾料 %d B'
                % (len(sub), used, len(pak), why, len(pak) - used))
            for s in sub[:12]:
                say('          @0x%-8X %-22r mode=%d psm=0x%02X %dx%d px=0x%X'
                    % (s['off'], s['name'], s['mode'], s['psm'], s['w'], s['h'], s['px']))
            if len(sub) > 12:
                say('          … 共 %d 条' % len(sub))

iso.close()
open(os.path.join(OUT, 'paks.txt'), 'w', encoding='utf-8').write('\n'.join(LS) + '\n')
print('\n[OUT] %s' % os.path.join(OUT, 'paks.txt'))
