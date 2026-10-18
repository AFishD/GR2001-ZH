# -*- coding: utf-8 -*-
r"""explore2.py — 勘察: ISO 文件树 / IMG 条目规模 / .ATR 内容 / ELF"""
import os
import struct
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
SEC = 2048


def read_dir(mm, lba, size):
    out = []
    data = bytes(mm[lba * SEC:lba * SEC + size])
    i = 0
    while i < len(data):
        L = data[i]
        if L == 0:
            i = (i // SEC + 1) * SEC
            if i >= len(data):
                break
            continue
        if i + L > len(data) or L < 34:
            break
        rec = data[i:i + L]
        ext = struct.unpack_from('<I', rec, 2)[0]
        sz = struct.unpack_from('<I', rec, 10)[0]
        out.append((rec[33:33 + rec[32]].decode('latin-1'), ext, sz, rec[25]))
        i += L
    return out


iso = T.Iso(ISO)
mm = iso.mm
pvd = 16 * SEC
root_lba = struct.unpack_from('<I', mm, pvd + 158)[0]
root_size = struct.unpack_from('<I', mm, pvd + 166)[0]
print('ISO size = %d B (%.1f MB), root_lba=%d' % (iso.size, iso.size / 1048576, root_lba))
files = []


def walk(lba, size, prefix):
    for nm, ext, sz, fl in read_dir(mm, lba, size):
        if nm in ('\x00', '\x01'):
            continue
        p = prefix + '/' + nm if prefix else nm
        if fl & 2:
            walk(ext, sz, p)
        else:
            files.append((p, ext, sz))


walk(root_lba, root_size, '')
print('ISO 文件树: %d 个文件' % len(files))
for p, lba, sz in sorted(files, key=lambda x: -x[2])[:20]:
    print('   %-40s LBA=%-8d %10d B' % (p, lba, sz))

elf = [f for f in files if 'SLUS' in f[0].upper()]
print('ELF 候选: %s' % [(p, l, s) for p, l, s in elf])

for lba, tag in ((T.GR_LBA, 'GR.IMG'), (T.MENU_LBA, 'MENU.IMG')):
    base = lba * SEC
    noff = struct.unpack_from('<I', mm, base + 0x10)[0]
    nend = struct.unpack_from('<I', mm, base + 4)[0]
    names = [x.decode('latin-1') for x in bytes(mm[base + noff:base + nend]).split(b'\x00') if x]
    tot_stored = tot_real = 0
    exts = {}
    for i, nm in enumerate(names):
        r = struct.unpack_from('<12I', mm, base + T.TAB_OFF + T.TAB_STEP * i)
        stored, real, off = r[6], r[7], r[8]
        tot_stored += stored
        tot_real += real
        e = os.path.splitext(nm)[1].upper() or '(无扩展名)'
        d = exts.setdefault(e, [0, 0, 0])
        d[0] += 1
        d[1] += stored
        d[2] += real
    print('\n== %s: %d 个条目, stored 合计 %.1f MB, real 合计 %.1f MB'
          % (tag, len(names), tot_stored / 1048576, tot_real / 1048576))
    for e, d in sorted(exts.items(), key=lambda x: -x[1][2]):
        print('   %-14s n=%-5d stored=%9d real=%9d' % (e, d[0], d[1], d[2]))

# .ATR 抽样: 有没有 CJK?
cs = T.Charset()
base = T.GR_LBA * SEC
noff = struct.unpack_from('<I', mm, base + 0x10)[0]
nend = struct.unpack_from('<I', mm, base + 4)[0]
names = [x.decode('latin-1') for x in bytes(mm[base + noff:base + nend]).split(b'\x00') if x]
t0 = time.time()
atr_n = 0
atr_cjk = {}
atr_blob_tot = 0
for i, nm in enumerate(names):
    if not nm.upper().endswith('.ATR'):
        continue
    r = struct.unpack_from('<12I', mm, base + T.TAB_OFF + T.TAB_STEP * i)
    stored, real, off = r[6], r[7], r[8]
    raw = iso.read(base + off, stored)
    blob = b''.join(s[0] for s in T.lzo_subs(raw)) if stored != real else raw
    atr_blob_tot += len(blob)
    txt, _ = cs.decode(blob)
    for ch in txt:
        if ord(ch) >= 0x80 and not (0xE000 <= ord(ch) <= 0xE0FF):
            atr_cjk[ch] = atr_cjk.get(ch, 0) + 1
    atr_n += 1
print('\n== .ATR: %d 个, 解压后合计 %d B; 出现的非 ASCII 字符 %d 种: %s'
      % (atr_n, atr_blob_tot, len(atr_cjk), ''.join(sorted(atr_cjk))[:200]))
print('   耗时 %.1fs' % (time.time() - t0))
iso.close()
