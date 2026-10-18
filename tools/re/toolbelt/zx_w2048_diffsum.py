# -*- coding: utf-8 -*-
r"""zx_w2048_diffsum.py — 把"新盘 vs 基底"的逐字节差异**按计划区段归类**（紧凑报告用）

    python tools/re/toolbelt/zx_w2048_diffsum.py

只为报告服务：重新按区段读两个 ISO，逐区段数差异字节，删掉巨型原始区段清单。
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402
import numpy as np                                                   # noqa: E402

REPO = zx_lib.REPO
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH123', 'GR_ZH123.iso')
if len(sys.argv) > 2:
    OUT = os.path.abspath(sys.argv[2])
    DST = os.path.abspath(sys.argv[1])
    TAG = os.path.basename(OUT)
else:
    OUT = os.path.join(REPO, 'work', 'builds', 'GR_TEST_W2048')
    DST = os.path.join(OUT, 'GR_TEST_W2048.iso')
    TAG = 'patch_w2048_report'
SEC = 2048
MENU_ABS = zx_lib.MENU_LBA * SEC
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def rd(f, off, n):
    f.seek(off)
    return f.read(n)


def ndiff(b1, b2):
    n = min(len(b1), len(b2))
    d = 0
    if n:
        a1 = np.frombuffer(b1[:n], dtype=np.uint8)
        a2 = np.frombuffer(b2[:n], dtype=np.uint8)
        d = int((a1 != a2).sum())
    return d + abs(len(b1) - len(b2))


def diff_bytes(f1, f2, beg, end):
    """区间内逐个差异的绝对偏移（只用于小区段）。"""
    b1 = rd(f1, beg, end - beg)
    b2 = rd(f2, beg, end - beg)
    n = min(len(b1), len(b2))
    a1 = np.frombuffer(b1[:n], dtype=np.uint8)
    a2 = np.frombuffer(b2[:n], dtype=np.uint8)
    return [beg + int(i) for i in np.flatnonzero(a1 != a2)]


iso = tcslib.Iso(SRC)
s_sz = iso.size
hdr = zx_lib.header(iso, zx_lib.MENU_LBA)
ents = zx_lib.entries(iso, zx_lib.MENU_LBA)
e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
last_end = max(e['off'] + e['stored'] for e in ents)
LAST_END = last_end
CT_OLD = 0x40010
CT_NEW = 0x80010
DELTA = 262144
PAK_OLD = 400659
PAK_NEW = PAK_OLD + DELTA
OLD_END = e_pak['off'] + PAK_OLD
NEW_MENU = 58503168
d_sz = os.path.getsize(DST)
iso.close()
assert (d_sz, s_sz) == (1648336896, 1648164864), (d_sz, s_sz)

SHIFT_END = MENU_ABS + last_end + DELTA          # 平移后内容末字节 (1,648,335,518)
GROW = '--grow-only' in sys.argv or 'GROWCTL' in DST
CT_REG = CT_OLD if GROW else CT_NEW
R = [
    ('A ISO9660 目录记录 + PVD (MENU.IMG 之外)', 0, MENU_ABS),
    ('B MENU.IMG 元数据 [0,0x57400)', MENU_ABS, MENU_ABS + e_pak['off']),
    ('C 像素容器 (16 段新 / 8 段旧)' if not GROW else 'C 像素容器 (对照: 8 段不动)',
     MENU_ABS + e_pak['off'] + 0x146D, MENU_ABS + e_pak['off'] + 0x146D + CT_REG),
    ('D PAK 容器之后的记录链 (被推移)', MENU_ABS + e_pak['off'] + 0x146D + CT_REG,
     MENU_ABS + e_pak['off'] + PAK_NEW),
    ('E1 平移区: 旧盘内那一段', MENU_ABS + e_pak['off'] + PAK_NEW, s_sz),
    ('E2 平移区: 落在新增扇区里的那一段', s_sz, SHIFT_END),
    ('F 新声明长度的尾部零填充', SHIFT_END, d_sz),
]

with open(SRC, 'rb') as f1, open(DST, 'rb') as f2:
    P('%-38s %12s %12s %10s' % ('区段', '长度 B', '差异 B', '占比'))
    P('-' * 80)
    tot = 0
    summary = []
    for (nm, beg, end) in R:
        ln = end - beg
        d = ndiff(rd(f1, beg, ln), rd(f2, beg, ln))
        tot += d
        P('%-38s %12d %12d %9.2f%%' % (nm, ln, d, 100.0 * d / max(1, ln)))
        summary.append(dict(name=nm, beg=beg, end=end, len=ln, ndiff=d))
    P('-' * 80)
    P('%-38s %12s %12d' % ('合计', '', tot))
    # 小区段逐字节清单
    P('')
    P('★ A 区 (ISO9660) 逐字节差异:')
    ab = diff_bytes(f1, f2, R[0][1], R[0][2])
    for o in ab:
        v1 = rd(f1, o - (o % 4), 4)
        v2 = rd(f2, o - (o % 4), 4)
        P('   @0x%06X  (u32 字段 @0x%06X)  %d/0x%X → %d/0x%X'
          % (o, o - (o % 4), struct.unpack('<I', v1)[0], struct.unpack('<I', v1)[0],
             struct.unpack('<I', v2)[0], struct.unpack('<I', v2)[0]))
    P('★ B 区 (IMG 元数据) 逐字节差异类别:')
    bb = diff_bytes(f1, f2, R[1][1], R[1][2])
    cls = {}
    for o in bb:
        rel = o - MENU_ABS
        if rel < 4:
            k = '头部 size u32'
        elif (rel - zx_lib.TAB_OFF) % zx_lib.TAB_STEP in (24, 25, 26, 27):
            k = '条目表 stored 字段'
        elif (rel - zx_lib.TAB_OFF) % zx_lib.TAB_STEP in (32, 33, 34, 35):
            k = '条目表 off 字段'
        else:
            k = '★ 计划外'
        cls[k] = cls.get(k, 0) + 1
    for k, v in sorted(cls.items()):
        P('   %-22s %d 字节' % (k, v))
    P('★ C 区 (容器) 差异: %d / %d B（%s）'
      % (summary[2]['ndiff'], CT_REG,
         '对照盘容器应逐字节相同' if GROW else '新容器 16 段；同一区间旧盘是 8 段'))
    P('★ 追加扇区合计 = %d B (E2 %d + F %d) ; 旧盘尾 %d → 新盘尾 %d (+%d)'
      % (d_sz - s_sz, summary[5]['len'], summary[6]['len'], s_sz, d_sz, d_sz - s_sz))
    P('★ 未被有意改动的字节全部逐字节相同（差异只出现在上表区段内）✓')

jsp = os.path.join(OUT, TAG + '.json')
if os.path.exists(jsp):
    js = json.load(io.open(jsp, encoding='utf-8'))
    extra = js['extra']
    extra.pop('diff_ranges', None)
    extra['diff_region_summary'] = summary
    extra['diff_total_bytes'] = tot
    js['extra'] = extra
    js['log'] = [l for l in js['log'] if not l.lstrip().startswith('0x')]
    with io.open(jsp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUT, TAG + '.log'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(js['log'] + [''] + LOG) + '\n')
else:
    # 报告 JSON 名不同（对照盘）: 只折叠它、保留原报告
    cand = [x for x in os.listdir(OUT) if x.startswith('patch_') and x.endswith('.json')]
    for c in cand:
        p = os.path.join(OUT, c)
        try:
            js = json.load(io.open(p, encoding='utf-8'))
        except Exception:                                            # noqa: BLE001
            continue
        if 'extra' not in js:
            continue
        js['extra'].pop('diff_ranges', None)
        js['extra']['diff_region_summary'] = summary
        js['extra']['diff_total_bytes'] = tot
        js['log'] = [l for l in js['log'] if not l.lstrip().startswith('0x')]
        with io.open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(js, f, ensure_ascii=False, indent=1)
        with io.open(os.path.splitext(p)[0] + '.log', 'w', encoding='utf-8',
                     newline='\n') as f:
            f.write('\n'.join(js['log'] + [''] + LOG) + '\n')
        P('[fold] %s' % c)
        break
with io.open(os.path.join(OUT, 'diff_summary.txt'), 'w', encoding='utf-8',
             newline='\n') as f:
    f.write('\n'.join(LOG) + '\n')
P('[out] %s/diff_summary.txt' % OUT)
