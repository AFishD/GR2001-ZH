# -*- coding: utf-8 -*-
r"""r57: ELF 语言槽表区 (0x50B820..0x50B8F4) 逐字节 + 全盘码串计数 (只读)。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_before_r56.json'))
new = tcslib.Charset()
iso = tcslib.Iso(ISO)
mm = iso.mm
ELF = 295 * tcslib.SEC

lo, hi = ELF + 0x478010, ELF + 0x478100
print('ELF 槽表区 绝对 0x%X..0x%X (ELF 相对 0x478010..0x478100):' % (lo, hi))
for off in range(lo, hi, 16):
    raw = bytes(mm[off:off + 16])
    t, _ = old.decode(raw)
    print('  0x%06X (elf+0x%06X) %s | %r' % (off, off - ELF, raw.hex(' '), t))

print('\n按 NUL 切槽 (ELF 相对 0x478020..0x4780F4):')
b = bytes(mm[ELF + 0x478020:ELF + 0x4780F4])
for i, part in enumerate(b.split(b'\x00')):
    t, _ = old.decode(part)
    print('  slot%-2d @elf+0x%06X len=%-3d %-46s 旧解=%r' % (i, 0x478020 + sum(len(x) + 1 for x in b.split(b'\x00')[:i]), len(part), part.hex(' '), t))

print('\n全盘码串计数 (旧 charset 口径):')
for name, pat in (('请等待(a3d6a1f8a2df)', bytes.fromhex('a3d6a1f8a2df')),
                  ('请等待(新 a3d5a1f8a2de)', bytes.fromhex('a3d5a1f8a2de')),
                  ('载入中(a2a9a1a7d6)', bytes.fromhex('a2a9a1a7d6')),
                  ('载入中...(a2a9a1a7d62e2e2e)', bytes.fromhex('a2a9a1a7d62e2e2e'))):
    data = bytes(mm[:])
    cnt, pos, start = 0, [], 0
    while True:
        k = data.find(pat, start)
        if k < 0:
            break
        cnt += 1
        pos.append(k)
        start = k + 1
    print('  %-28s 命中 %d 处: %s' % (name, cnt, ', '.join('0x%X' % p for p in pos[:12])))
iso.close()
