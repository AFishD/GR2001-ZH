# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..'))

r"""fix_slot_fld26.py — ft_slot_zh34.bin 的 large/default fld[1] 16→26 (CharHeight=26 → 缩放条 y=31)
等价于 offset_fix build_m26_slot.py 的手术, 施加在 X0=4 新槽上。huge 保持 16。
"""
import struct, sys, os
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'hanliu', 'tools'))
from ft_dpc import dp_compress
from lz77_decode import decode_entry

HERE = os.path.join(REPO_ROOT, 'work', 'builds', 'GR_ZH62', 'font_out')
slot = open(os.path.join(HERE, 'ft_slot_zh34.bin'), 'rb').read()
back, stats = decode_entry(slot)
back = bytearray(back)
print('decoded %dB' % len(back))

# face0 large / face1 default 的 fld[1] 槽内偏移 (offset_fix 定案: 名后第2个u32)
def face_off(ft, idx):
    p = 28
    for i in range(idx):
        l = struct.unpack_from('<I', ft, p)[0]; p += 4 + l + 56
        nrec = struct.unpack_from('<I', ft, p - 56 + 16)[0] * struct.unpack_from('<I', ft, p - 56 + 20)[0]
        p += nrec * 10
    l = struct.unpack_from('<I', ft, p)[0]
    return p + 4 + l + 4  # 名后第2个u32 = fld[1]

for idx, nm in ((0, 'large'), (1, 'default')):
    off = face_off(back, idx)
    old = struct.unpack_from('<I', back, off)[0]
    assert old == 16, (nm, hex(off), old)
    struct.pack_into('<I', back, off, 26)
    print('%s fld[1] @%#x: 16 -> 26' % (nm, off))
# huge fld[1] 应保持 16
off2 = face_off(back, 2)
print('huge fld[1] =', struct.unpack_from('<I', back, off2)[0], '(保持)')

payload = dp_compress(bytes(back), verbose=False)
assert len(payload) <= 4413, len(payload)
frame = struct.pack('<II', len(payload), len(back)) + payload
slot2 = frame + b'\x00' * (4421 - len(frame))
back2, _ = decode_entry(slot2)
assert back2 == bytes(back), '回环 FAIL'
open(os.path.join(HERE, 'ft_slot_zh34_fld26.bin'), 'wb').write(slot2)
print('ft_slot_zh34_fld26.bin 写出 (%dB), 回环 PASS' % len(slot2))
