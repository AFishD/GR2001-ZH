# -*- coding: utf-8 -*-
r"""probe_a4.py -- 查清 SF 容器里 5 个 0xA4 字节的性质 (只读探测, 不改任何东西)。"""
import collections
import importlib.util
import io
import json
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
spec = importlib.util.spec_from_file_location(
    'mla', os.path.join(REPO, 'tools', 're', 'toolbelt', 'migrate_legacy_audit.py'))
m = importlib.util.module_from_spec(spec)
sys.modules['mla'] = m
spec.loader.exec_module(m)
cs = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'backup',
                                    'charset_compiled_zh16.json.before_hashr'),
                       encoding='utf-8'))
codes = {int(v): k for k, v in cs['codes'].items()}
pair = {tuple(v): k for k, v in cs['pair_of'].items()}


def dec(bb):
    o, j = [], 0
    while j < len(bb):
        cc = bb[j]
        if 0xA1 <= cc < 0xBA and j + 1 < len(bb) and 0xA1 <= bb[j + 1] <= 0xFE \
                and (cc, bb[j + 1]) in pair:
            o.append(pair[(cc, bb[j + 1])])
            j += 2
            continue
        if cc in codes:
            o.append(codes[cc])
            j += 1
            continue
        o.append(chr(cc) if 32 <= cc < 127 else '{%02X}' % cc)
        j += 1
    return ''.join(o)


def dump(tag, iso):
    rows, body = m.payload_rows(iso, 776286, 283, 'SFXML')
    c = collections.Counter()
    for (_k, ba, _r) in rows:
        for b in range(256):
            if ba.count(b):
                c['%02X' % b] += ba.count(b)
    print('%s : rows=%d blob=%d' % (tag, len(rows), len(body)))
    print('   字节直方图(前 20): %s' % c.most_common(20))
    print('   A4 出现 %d 次 ; A0 出现 %d 次' % (c.get('A4', 0), c.get('A0', 0)))
    for (k, ba, r) in rows:
        if 0xA4 in ba:
            s = dec(ba)
            print('   [A4] %-10s off=%d : %s' % (k, r, s[:150]))
    return rows


isoA = m.Iso(os.path.join(REPO, 'work', 'builds', 'GR_RELEASE', 'GR_ZH2400_FINAL.iso'))
isoB = m.Iso(os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'GR_REBUILD2400.iso'))
isoE = m.Iso(os.path.join(REPO, 'third_party', 'orig', 'ps2',
                          "Tom Clancy's Ghost Recon (USA).iso"))
dump('FINAL ', isoA)
dump('BASE  ', isoB)
# 英文原盘: 同一 node# 的英文原文, 看 0xA4/空格
rowsE, bodyE = m.payload_rows(isoE, 776286, 283, 'SFXML')
print('ENG   : rows=%d blob=%d' % (len(rowsE), len(bodyE)))
for (k, ba, r) in rowsE:
    if k in ('node#800', 'node#870'):
        print('   ENG %-10s : %s' % (k, dec(ba)[:200]))
        print('       raw head:', ba[:80].hex())
isoA.close(); isoB.close(); isoE.close()
