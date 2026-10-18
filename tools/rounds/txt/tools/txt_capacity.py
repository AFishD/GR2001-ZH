# -*- coding: utf-8 -*-
r"""txt_capacity.py —— (1) 确认 RSFontMgr 顶点缓冲的固定容量常量与 +0x6C 的写入者；
(2) 统计 3 个容器里 0xB1 / 0xB5（原盘 DrawString 有图标特判）的出现形态。只读。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 're', 'toolbelt'))
import tcslib as T                                                       # noqa: E402
import importlib.util                                                    # noqa: E402

_s = importlib.util.spec_from_file_location('cd', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)
_s2 = importlib.util.spec_from_file_location('cs', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_syms.py'))
CS = importlib.util.module_from_spec(_s2)
_s2.loader.exec_module(CS)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ELF = os.path.join(ROOT, r'third_party\orig\ps2\slus_out\SLUS_206.13')
elf = CD.Elf(ELF)
syms = CS.load_syms(ELF)
rng = sorted([(v, v + s, n) for (v, s, _i, _x, n) in syms if v and s])


def owner(va):
    best = None
    for (a, b, n) in rng:
        if a <= va < b and (best is None or a > best[0]):
            best = (a, b, n)
    return best[2] if best else '?'


va0, off0, fsz = elf.text()
print('== (1) 原盘 ELF 里 1280 / 0x500 与 fontmgr+0x6C 的证据 ==')
hits = []
for va in range(va0, va0 + fsz - 4, 4):
    w = elf.word(va)
    op = w >> 26
    rs, rt, imm = (w >> 21) & 0x1F, (w >> 16) & 0x1F, w & 0xFFFF
    # slti rt, rs, 1280
    if op == 0x0A and imm == 1280:
        hits.append(('slti $%d,$%d,1280' % (rt, rs), va))
    # addiu rt, zero, 1280
    if op == 0x09 and rs == 0 and imm == 1280:
        hits.append(('addiu $%d,zero,1280' % rt, va))
    # sw rt, 108(base)
    if op == 0x2B and imm == 108:
        hits.append(('sw $%d,108($%d)' % (rt, rs), va))
for (txt, va) in hits:
    print('   0x%08X  %-26s in %s' % (va, txt, owner(va)))
print()
print('== (2) 3 个容器里 0xB1 / 0xB5 的形态统计 ==')
ISOS = (('EN_TRUE', r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"),
        ('ZH113b', r"work\builds\GR_ZH113b\GR_ZH113b.iso"),
        ('CVAR04', r"work\builds\GR_CVAR\CVAR_04_text.iso"))
for tag, rel in ISOS:
    iso = T.Iso(os.path.join(ROOT, rel))
    print('  --- %s ---' % tag)
    for (lba, idx, name, kind) in ((T.MENU_LBA, 25, 'RES@MENU', 'LANG'),
                                   (T.GR_LBA, 902, 'RES@GR', 'LANG'),
                                   (T.MENU_LBA, 283, 'SFXML', 'XML')):
        e = iso.img_entry(lba, idx)
        blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
        if kind == 'LANG':
            ents, used = T.parse_lang(blob)
            pays = [bytes(e2.data) for e2 in ents]
            struct_bytes = 0
        else:
            pays = [m.group(1) for m in
                    __import__('re').finditer(rb'<text>(.*?)</text>', blob,
                                              __import__('re').S)]
            used = T.xml_tail_start(blob)
            struct_bytes = 0
        tot = sum(len(p) for p in pays)
        bare = sum(p.count(b'\xb1') for p in pays)
        bare5 = sum(p.count(b'\xb5') for p in pays)
        ent_with = sum(1 for p in pays if b'\xb1' in p or b'\xb5' in p)
        # 形态：在"对偶码 [0xA1,0xBA) + trail [0xA1,0xFE]"的语义下分类
        lead, trail, single = 0, 0, 0
        for p in pays:
            i = 0
            while i < len(p):
                b = p[i]
                if 0xA1 <= b < 0xBA and i + 1 < len(p) and 0xA1 <= p[i + 1] <= 0xFE:
                    if b in (0xB1, 0xB5):
                        lead += 1
                    if p[i + 1] in (0xB1, 0xB5):
                        trail += 1
                    i += 2
                else:
                    if b in (0xB1, 0xB5):
                        single += 1
                    i += 1
        print('     %-10s payload=%6d B  0xB1 裸字节=%4d  0xB5 裸字节=%4d  含它们的条目=%4d'
              '  | 形态: 当 lead=%d  当 trail=%d  裸单字节=%d'
              % (name, tot, bare, bare5, ent_with, lead, trail, single))
    iso.close()
