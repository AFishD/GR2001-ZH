# -*- coding: utf-8 -*-
r"""build_fix5657.py — 把那条 1 指令修复并入 F364 血统，出两个盘

修复: VA 0x5657E0 (ISO = VA - 0x6C780 = 0x4F9060): 0x95050002 -> 0x95050000  (lhu a1,2(t0) -> lhu a1,0(t0))
产出:
  A) work/builds/GR_F365/GR_F365.iso  = GR_F364 + 修复   （h=640 血统 + 修复）
  B) work/builds/GR_ZH125/GR_ZH125.iso = GR_ZH124 + 修复  （h=512 血统 + 修复，用作隔离对照）
每个盘都做: 逐字节差异核对（必须恰好 2 字节，落在 0x4F9060/0x4F9061）+ 尺寸核对 + sha256
"""
import hashlib
import os
import shutil
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OFF = 0x5657E0 - 0x6C780          # 0x4F9060
OLD, NEW = 0x95050002, 0x95050000
JOBS = [
    ('work/builds/GR_ZH113b/GR_ZH113b.iso', 'work/builds/GR_ZH113b_fix', 'GR_ZH113b_fix.iso'),
]
GATES = [(0x416EE8, 0x3AA768), (0x417160, 0x3AA9E0), (0x41751C, 0x3AAD9C), (0x5656A4, 0x4F8F24)]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


free = shutil.disk_usage(REPO).free
print('  磁盘可用 %.1f GB' % (free / 1e9))

for src_rel, out_dir, name in JOBS:
    src = os.path.join(REPO, src_rel)
    out = os.path.join(REPO, out_dir, name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print()
    print('=== %s -> %s ===' % (src_rel, os.path.relpath(out, REPO)))
    if not os.path.exists(src):
        print('  ✗ 缺源盘'); continue
    # 源盘当前值
    with open(src, 'rb') as f:
        f.seek(OFF); cur = struct.unpack('<I', f.read(4))[0]
    print('  源盘 @0x%X = %08X (%s)' % (OFF, cur, 'BUGGY' if cur == OLD else 'FIXED' if cur == NEW else '???'))
    if cur != OLD:
        print('  ✗ 源盘不是 buggy 态，跳过'); continue
    if not os.path.exists(out):
        print('  复制中…')
        shutil.copyfile(src, out)
    with open(out, 'r+b') as f:
        f.seek(OFF); f.write(struct.pack('<I', NEW))
        f.seek(OFF); chk = struct.unpack('<I', f.read(4))[0]
    print('  写入后 @0x%X = %08X %s' % (OFF, chk, '✓' if chk == NEW else '✗'))
    # 差异核对
    diffs = []
    with open(src, 'rb') as a, open(out, 'rb') as b:
        pos = 0
        while True:
            x, y = a.read(1 << 22), b.read(1 << 22)
            if not x:
                break
            if x != y:
                for i in range(min(len(x), len(y))):
                    if x[i] != y[i]:
                        diffs.append(pos + i)
            pos += len(x)
    print('  逐字节差异 %d 个: %s %s' % (len(diffs), ['0x%X' % d for d in diffs[:6]],
                                     '✓ 恰好 2 字节且位置正确' if diffs == [OFF, OFF + 1] else '✗'))
    print('  尺寸 %d B (%s) · sha256 %s' % (os.path.getsize(out),
          '与源盘相同 ✓' if os.path.getsize(out) == os.path.getsize(src) else '不同 ✗',
          sha(out)[:24]))
    # gate 站点值（应与 F364 一致：0xB5）
    with open(out, 'rb') as f:
        vals = []
        for va, o in GATES:
            f.seek(o); vals.append('%08X' % struct.unpack('<I', f.read(4))[0])
    print('  4 个 gate 字: %s （0xB5 态 = 2CA900B5/2D0900B5/2D4B00B5/2D6C00B5）' % ' '.join(vals))
print()
print('  完成。')
