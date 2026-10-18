# -*- coding: utf-8 -*-
r"""r57 探针: 0x1F035800 附近那批"真中文"串到底在哪个文件/条目里? (只读)"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_before_r56.json'))
iso = tcslib.Iso(ISO)
TGT = 0x1F035800
print('LBA = %d' % (TGT // 2048))

# ---- PVD: 文件表 (LBA 16) ----
pvd = bytes(iso.mm[16 * 2048:17 * 2048])
print('PVD 前 8B: %s' % pvd[:8].hex(' '))
root = struct.unpack_from('<I', pvd, 156 + 2)[0]           # root dir extent LBA (LE at 158)
root_len = struct.unpack_from('<I', pvd, 156 + 10)[0]
print('root dir LBA %d len %d' % (root, root_len))
rec = bytes(iso.mm[root * 2048:root * 2048 + root_len])
off = 0
while off < len(rec):
    L = rec[off]
    if L == 0:
        off = (off // 2048 + 1) * 2048
        if off >= len(rec):
            break
        continue
    ext = struct.unpack_from('<I', rec, off + 2)[0]
    size = struct.unpack_from('<I', rec, off + 10)[0]
    flags = rec[off + 25]
    nlen = rec[off + 32]
    nm = rec[off + 33:off + 33 + nlen]
    try:
        nm_s = nm.decode('ascii')
    except UnicodeDecodeError:
        nm_s = nm.hex()
    print('   %-16s LBA %-9d size %-11d %s' % (nm_s, ext, size, 'DIR' if flags & 2 else ''))
    off += L

# ---- 容器列表里离 TGT 最近的条目 ----
print('\n离 0x%X 最近的 IMG 条目:' % TGT)
ents = []
for (tag, lba, idx, e) in FC.enumerate_containers(iso):
    ents.append((e['iso_off'], e['iso_off'] + e['stored'], tag, idx, e['name']))
ents.sort()
import bisect                                                          # noqa: E402
i = bisect.bisect_right([x[0] for x in ents], TGT) - 1
for k in range(max(0, i - 3), min(len(ents), i + 4)):
    a, b, tag, idx, nm = ents[k]
    print('   0x%X..0x%X %s#%d %-28s %s' % (a, b, tag, idx, nm,
                                            '★ 命中区间内' if a <= TGT < b else ''))

print('\n目标区上下文 (0x%X..0x%X):' % (TGT - 32, TGT + 192))
for o in range(TGT - 32, TGT + 192, 32):
    raw = bytes(iso.mm[o:o + 32])
    print('   0x%X %s | %r' % (o, raw.hex(' '), old.decode(raw)[0]))
iso.close()
