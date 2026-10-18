# -*- coding: utf-8 -*-
r"""zx_prefixchk.py — 只读: 现役容器 8 个段前缀的逐字节差异 (验证"模板+SSAY"重建是否合法)

若除 SSAY 字段 (偏移 20..24) 之外还有别的差异 ⇒ zx_lib.AtlasWriter 的模板法有问题。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

ISO = os.path.join(zx_lib.REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
e = [x for x in zx_lib.entries(iso, zx_lib.MENU_LBA) if x['name'] == 'COMMON.PAK'][0]
pak = iso.read(e['iso_off'], e['stored'])
_nm, psm, w, h, clut, px, PX = tcslib.parse_pak_records(pak)[1]
ct = pak[PX:PX + px]
segs = zx_lib.seg_table(ct, 1024)
prefs = [(row, doff, ct[doff - 48:doff]) for (row, doff, nb) in segs]
base = prefs[0][2]
print('段前缀逐段对比 (基准 = seg0):')
for (row, doff, p) in prefs:
    d = [i for i in range(48) if p[i] != base[i]]
    print('  首行 %-4d doff=0x%-7X 与 seg0 不同的字节偏移 = %s'
          % (row, doff, d if d else '无'))
print('\nseg0 前缀 : %s' % base.hex(' '))
print('seg7 前缀 : %s' % prefs[-1][2].hex(' '))
print('\n尾部 16 B (no-op tag): %s' % ct[-16:].hex(' '))
# 段数据长度
print('段数据长度: %s' % [(r, n) for (r, _d, n) in segs])
iso.close()
