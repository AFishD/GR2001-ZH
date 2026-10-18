# -*- coding: utf-8 -*-
r"""p12_audit.py — 全量审计: 每个走 FT 记录表的码位 (ASCII + 单字节), 引擎采样窗里到底有没有墨。

引擎口径: 单字节/ASCII 的采样窗 = 记录矩形 (u0,v0,u1,v1) **本身** (round45 实机 A/B 已证),
不做任何相位/偏置换算。所以"窗里没墨" = 这个字节画出来是空白 (或别人的像素)。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
import dump_font                                       # noqa: E402
import repack_font                                     # noqa: E402

VER = sys.argv[1] if len(sys.argv) > 1 else 'GR_ZH94'
ISO = os.path.join(REPO, 'work', 'builds', VER, VER + '.iso')
f = dump_font.load_font(ISO)
a = f['atlas']
A = repack_font.Atlas(a['pak'], a['px_off'], a['px_size'], a['w'], a['h'], a['psm'])
cs = tcslib.Charset()
faces = dict((x[0], x[2]) for x in f['faces'])

print('=== %s ===' % VER)
for face in ('large', 'default', 'huge'):
    recs = faces[face]
    empty = []
    nz = 0
    for idx, r in enumerate(recs):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 <= u0 or v1 <= v0:
            continue
        n = int(A.eng[v0:v1, u0:u1].sum())
        if n == 0:
            empty.append(idx + 0x20)
        else:
            nz += 1
    print('face %-8s 记录 %3d 条, 有墨 %3d, **空 %3d**' % (face, len(recs), nz, len(empty)))

print()
print('--- default face (引擎实际用的那个) 里"引擎窗是空的"的码位 ---')
recs = faces['default']
empty = []
for idx, r in enumerate(recs):
    _b0, _b1, u0, v0, u1, v1 = r
    if u1 <= u0 or v1 <= v0:
        continue
    n = int(A.eng[v0:v1, u0:u1].sum())
    if n == 0:
        empty.append((idx + 0x20, u0, v0, u1, v1))
print('  空记录 %d 条:' % len(empty))
for (code, u0, v0, u1, v1) in empty:
    ch = cs.codes.get(code)
    tag = ('单字节「%s」' % ch) if ch else (
        ('ASCII %r' % chr(code)) if code < 0x80 else '（本盘未映射）')
    inflat = 'flat有墨' if int(_flat[A] if False else 0) else ''
    print('     0x%02X %-16s rect=(%4d,%4d,%4d,%4d)' % (code, tag, u0, v0, u1, v1))

print()
print('--- 对照: 这些"空记录"在 flat 口径里有没有墨 ---')
stride = A.w // 2
n = min(len(A.cont) // stride, A.h)
arr = np.frombuffer(bytes(A.cont[:n * stride]), dtype=np.uint8).reshape(n, stride)
flat = np.zeros((A.h, A.w), dtype=bool)
flat[:n, 0::2] = (arr & 0x0F) == 0
flat[:n, 1::2] = (arr >> 4) == 0
for (code, u0, v0, u1, v1) in empty:
    ch = cs.codes.get(code)
    print('     0x%02X %-16s flat 墨=%4d' % (code, ('「%s」' % ch) if ch else '', int(flat[v0:v1, u0:u1].sum())))

print()
print('--- 这些空码位在用户文本里出现过吗 (只看 text_edited) ---')
tdir = os.path.join(REPO, 'work', 'builds', VER, 'text')
if os.path.isdir(tdir):
    import csv
    import collections
    cnt = collections.Counter()
    for fn in sorted(os.listdir(tdir)):
        if not fn.endswith('.csv'):
            continue
        with open(os.path.join(tdir, fn), encoding='utf-8-sig', newline='') as fh:
            for r in csv.DictReader(fh):
                for ch in (r.get('text_edited') or ''):
                    cnt[ch] += 1
    for (code, u0, v0, u1, v1) in empty:
        ch = cs.codes.get(code)
        if ch and cnt.get(ch):
            print('     ★ 0x%02X「%s」在译文里出现 %d 次 ⇒ 游戏里显示为空白!' % (code, ch, cnt[ch]))
