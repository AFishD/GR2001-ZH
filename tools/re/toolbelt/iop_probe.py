# -*- coding: utf-8 -*-
r"""iop_probe.py — 从 ISO 取出 IOP 模块并初探: 头、字符串、容器/挂载线索

RPC.IRX @LBA19032 (230,000 B) / IOPRP242.IMG @LBA18737 (252,409 B) / MCMAN.IRX @18874 …
目的: 找"挂了哪些容器(MENU.IMG/GR.IMG)、按什么顺序搜"的线索 —— 决定大贴图能否放别处。
"""
import os
import re
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r80')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402
os.makedirs(OUT, exist_ok=True)

MODS = [
    ('RPC.IRX', 19032, 230000),
    ('IOPRP242.IMG', 18737, 252409),
    ('MCDMAN.IRX', 18874, 86341),
    ('SIO2MAN.IRX', 19150, 6161),
]
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)

STR_RE = re.compile(rb'[ -~]{6,}')
KEY = [b'.IMG', b'.img', b'.PAK', b'.pak', b'.RSB', b'.rsb', b'mount', b'Mount', b'MOUNT',
       b'open', b'Open', b'cdrom', b'iso', b'ISO', b'container', b'Container', b'file', b'File',
       b'IOPRP', b'RPC', b'sceCd', b'CdSearch', b'diSearch', b'GAME', b'DATA']

for name, lba, size in MODS:
    raw = iso.read(lba * 2048, size)
    p = os.path.join(OUT, name.replace('.', '_'))
    open(p, 'wb').write(raw)
    print('=' * 84)
    print('%s  (%d B) 头 64 字节: %s' % (name, len(raw), raw[:64].hex()))
    # 头标识
    magic = raw[:4]
    if magic == b'\x7fELF':
        etype = struct.unpack_from('<H', raw, 0x10)[0]
        machine = struct.unpack_from('<H', raw, 0x12)[0]
        entry = struct.unpack_from('<I', raw, 0x18)[0]
        phoff = struct.unpack_from('<I', raw, 0x1C)[0]
        phnum = struct.unpack_from('<H', raw, 0x2C)[0]
        print('  → **ELF** type=%d machine=%d(8=MIPS) entry=0x%08X phoff=0x%X phnum=%d'
              % (etype, machine, entry, phoff, phnum))
    elif raw[:4] == b'PS2I':
        print('  → PS2 IOP 可加载模块 (PS2I)')
    else:
        print('  → 未知 magic %r' % magic)
    # 字符串
    strs = [m.group().decode('ascii', 'replace') for m in STR_RE.finditer(raw)]
    hits = {}
    for s in strs:
        for k in KEY:
            kk = k.decode()
            if kk in s:
                hits.setdefault(kk, set()).add(s)
                break
    print('  可打印字符串 %d 条; 与容器/文件相关的关键词命中:' % len(strs))
    for k in sorted(hits):
        ex = sorted(hits[k])[:6]
        print('    %-10s %3d 条  例: %s' % (k, len(hits[k]), ' | '.join(x[:52] for x in ex)))
    # 全字符串落盘
    with open(os.path.join(OUT, name.replace('.', '_') + '.strings.txt'), 'w', encoding='utf-8') as f:
        for s in strs:
            f.write(s + '\n')
    print()
