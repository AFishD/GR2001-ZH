# -*- coding: utf-8 -*-
r"""r57: ELF 段表 + 候选段落段归属 (只读)。"""
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
ELF_OFF = 295 * tcslib.SEC
iso = tcslib.Iso(ISO)
mm = iso.mm
hdr = bytes(mm[ELF_OFF:ELF_OFF + 64])
e_phoff, e_shoff = struct.unpack_from('<II', hdr, 0x1C)
e_phentsize, e_phnum, e_shentsize, e_shnum = struct.unpack_from('<HHHH', hdr, 0x2A)
e_shstrndx = struct.unpack_from('<H', hdr, 0x32)[0]
print('e_phoff=0x%X n=%d  e_shoff=0x%X ent=%d n=%d  shstrndx=%d'
      % (e_phoff, e_phnum, e_shoff, e_shentsize, e_shnum, e_shstrndx))

secs = []
for i in range(e_shnum):
    o = ELF_OFF + e_shoff + i * e_shentsize
    name, typ, flags, addr, off, size, link, info, align, entsize = \
        struct.unpack_from('<IIIIIIIIII', mm, o)
    secs.append(dict(i=i, nameoff=name, type=typ, flags=flags, addr=addr, off=off, size=size,
                     align=align, entsize=entsize))
stroff = ELF_OFF + secs[e_shstrndx]['off']
shstr = bytes(mm[stroff:stroff + secs[e_shstrndx]['size']])


def nm(s):
    e = shstr.find(b'\x00', s['nameoff'])
    return shstr[s['nameoff']:e].decode('latin-1')


print('\n%-3s %-16s %-10s %-6s %-12s %-12s %-10s %s'
      % ('#', 'name', 'type', 'flags', 'file_off', 'iso_off', 'size', 'addr'))
sec_ranges = []
for s in secs:
    s['sname'] = nm(s)
    if s['type'] != 8 and s['size']:                 # 跳过 NOBITS
        a, b = ELF_OFF + s['off'], ELF_OFF + s['off'] + s['size']
        sec_ranges.append((a, b, s))
    print('%-3d %-16s 0x%08X 0x%06X 0x%08X   0x%08X   0x%08X 0x%08X  %s'
          % (s['i'], s['sname'], s['type'], s['flags'], s['off'],
             ELF_OFF + s['off'], s['size'], s['addr'],
             ('X' if s['flags'] & 0x4 else '.') + ('W' if s['flags'] & 0x1 else '.')
             + ('A' if s['flags'] & 0x2 else '.')))


def sec_of(off):
    for a, b, s in sec_ranges:
        if a <= off < b:
            return s
    return None


rows = json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      'calib_r57.json'), encoding='utf-8'))
print('\n候选段 %d 个; 按段表归属:' % len(rows))
agg = {}
for r in rows:
    s = sec_of(r['off'])
    k = s['sname'] if s else '(段表之外)'
    agg.setdefault(k, []).append(r)
for k, v in sorted(agg.items(), key=lambda kv: -len(kv[1])):
    s = sec_of(v[0]['off'])
    print('  %-16s %6d 段  文件偏移 0x%X..0x%X  flags=%s'
          % (k, len(v), (s['off'] if s else -1),
             (s['off'] + s['size'] if s else -1),
             (('X' if s['flags'] & 0x4 else '.') + ('W' if s['flags'] & 0x1 else '.')
              + ('A' if s['flags'] & 0x2 else '.')) if s else '-'))

print('\n★ 5 条载入提示条所在段:')
for off in (0x50B820, 0x50B840, 0x50B858, 0x50B870, 0x50B8A8, 0x50B8D8, 0x50B8C0, 0x50B890,
            0x50B8E8):
    s = sec_of(off)
    print('  0x%06X → %s (flags=%s)' % (off, s['sname'] if s else '?',
                                        (('X' if s['flags'] & 0x4 else '.')
                                         + ('W' if s['flags'] & 0x1 else '.')
                                         + ('A' if s['flags'] & 0x2 else '.')) if s else '-'))
print('\n★ Lead 点名的 7 段巧合 + 判据 A/B 选中的假阳 (前 20) 的段归属:')
for off in (0x3397CA, 0x33C1A2, 0x3484AA, 0x34871A, 0x378C2A, 0x3C15A6, 0x3C1866, 0x43D51E,
            0x43F18A, 0x96C9F, 0xAFF8F, 0xB7AB6, 0xC0126, 0xE195A, 0x136929, 0x19947F, 0x2A2D1A,
            0x3DCEF8, 0x3E7298, 0x463836):
    s = sec_of(off)
    print('  0x%06X → %s' % (off, s['sname'] if s else '(段表之外)'))
iso.close()
