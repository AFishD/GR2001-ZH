# -*- coding: utf-8 -*-
r"""p9_verify.py — 独立复核探针盘 (不复用探针工具自己的结论)。

1. 从**盘上**解出 EN_SPECIAL_FEATURE.XML 的 blob, 定位目标 <text>;
2. 把它按"探针块的字节结构"翻译成人话 (每行显示每个 pair 的实际字节);
3. 图集: 逐个新格验证"确有那个字的字形"(逐像素与源格相同);
4. 打印前三块, 供人眼核对实拍时屏幕上该出现什么。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                                     # noqa: E402
import tcslib                                                             # noqa: E402
import inject_text_csv as inj                                             # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_TEST_PROBE_LEAD', 'GR_TEST_PROBE_LEAD.iso')
cs = tcslib.Charset()
iso = tcslib.Iso(ISO)
c = inj.Container(iso, 'SFXML', tcslib.RES['SFXML']['copies'][0], cs)
print('[容器] %s#%d 槽 %d B 帧 %d B; 展开 %d B' % (c.img, c.idx, c.slot, c.frame_len, len(c.blob)))

# ---- 定位 (不用 make_font_testpage, 自己按 XML 找) ----
blob = c.blob
import re                                                                 # noqa: E402
item_off = None
for m in re.finditer(rb'<item\b([^>]*)>', blob):
    nm = re.search(rb'name\s*=\s*"([^"]*)"', m.group(1))
    if nm and cs.decode(nm.group(1))[0] == '开发访谈 1':
        item_off = m.start()
        break
assert item_off is not None, '找不到 <item name="开发访谈 1">'
mo = re.compile(rb'<text>').search(blob, item_off)
mc = re.compile(rb'</text>').search(blob, mo.end())
data = blob[mo.end():mc.start()]
print('[目标] <text> 载荷 [0x%X, 0x%X) = %d B' % (mo.end(), mc.start(), len(data)))

# ---- 人话翻译 ----
name_of = {}
for ch, pr in cs.enc_pair.items():
    name_of[tuple(pr)] = ch
BLOCK_HEAD = b'PROBE'


def show(seg, indent='   '):
    out = []
    for tok in seg.split(b'{br}'):
        if not tok:
            continue
        s = tok.decode('latin-1')
        s = s.replace('{p}', '⏎段落')
        out.append(indent + repr(s))
    return out


first = data.find(BLOCK_HEAD)
print('\n== 第一块探针 (盘上逐字节) ==')
seg = data[first:first + 200]
end = seg.find(b'{p}')
print('   %r' % seg[:end + 3])
print('\n== 每行 = 哪些字节 ==')
for line in seg[:end].split(b'{br}'):
    if not line:
        continue
    tag, _, rest = line.partition(b': ')
    bs = rest.split(b' ')
    desc = []
    for b in bs:
        if len(b) == 2:
            ch = name_of.get((b[0], b[1]), '?')
            desc.append('%02X%02X→%s' % (b[0], b[1], ch))
        elif len(b) == 1:
            desc.append('%02X→%s' % (b[0], cs.codes.get(b[0], '(无单字节字形/图标码)')))
    print('   %-5s %s' % (tag.decode('latin-1'), '  '.join(desc)))
n_blocks = data.count(BLOCK_HEAD)
print('\n[结构] 整段载荷 %d B, 含 %d 个探针块, 每块 %d B (含 %d 个空格)'
      % (len(data), n_blocks, data.find(BLOCK_HEAD, first + 1) - first,
         data[first:first + 200].count(b' ')))

# ---- 图集复核 ----
f = D.load_font(ISO)
atlas = f['atlas']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, 'engine'), dtype=np.uint8).reshape(H, W)
src_cells = {'我': (0xA6, 0xA9), '国': (0xA5, 0xDE), '山': (0xA7, 0xC2)}
tgt = {'我': [(0xAD, 0xD0), (0xAE, 0xB1), (0xB0, 0xB1), (0xB1, 0xB1)],
       '国': [(0xAD, 0xD1), (0xAE, 0xB2), (0xB0, 0xB2), (0xB1, 0xB2)],
       '山': [(0xAD, 0xD2), (0xAE, 0xB3), (0xB0, 0xB3), (0xB1, 0xB3)]}
ok = True
print('\n== 图集: 新格 vs 源格 (逐像素) ==')
for ch, pr in src_cells.items():
    sx, sy = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(*pr))
    ref = (gray[sy:sy + 16, sx:sx + 16] == 0)
    for t in tgt[ch]:
        tx, ty = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(*t))
        got = (gray[ty:ty + 16, tx:tx + 16] == 0)
        same = bool((got == ref).all())
        ok &= same
        print('   %s %02X%02X slot=%4d cell=(%4d,%3d) 墨=%3d 与源格相同=%s'
              % (ch, t[0], t[1], tcslib.pair_slot(*t), tx, ty, int(got.sum()), same))
print('\n[结论] 图集抄写 %s' % ('全部逐像素一致 ✓' if ok else '✗ 有不一致'))
iso.close()
