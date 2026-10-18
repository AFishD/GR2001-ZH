# -*- coding: utf-8 -*-
"""r39 探针 12: 「长串密度」—— 随机数据里 >=16/>=20 字节全可打印串的理论与实测概率。只读。"""
import collections
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T
import font_usage as FU

ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
iso = T.Iso(ZH)
idx = FU.CharsetIndex()
conts = FU.build_container_list(iso)
PR = re.compile(rb'[\x20-\x7e]{%d,}')


def longs(blob, L):
    """长度 >= L 的全可打印 ASCII 串: (条数, 字节数, 去重条数)"""
    n = b = 0
    s = set()
    for m in PR.finditer(blob):
        g = m.group(0)
        if len(g) < L:
            continue
        n += 1
        b += len(g)
        s.add(g)
    return n, b, len(s)


random.seed(20261005)
print('--- 纯随机数据 (理论 / 实测) ---')
for mb in (1, 4, 16):
    rnd = bytes(random.randrange(256) for _ in range(mb << 20))
    line = '   %2d MB: ' % mb
    for L in (12, 16, 20, 24):
        n, b, d = longs(rnd, L)
        th = (mb << 20) * ((95.0 / 256) ** L)
        line += 'L>=%d 实测 %5d (理论 %.1f) %.5f%%  ' % (L, n, th, 100.0 * b / len(rnd))
    print(line)

print('\n--- 关键容器: 长串条数 / 占比 ---')
names = (('D01_BEACH.MIS', 'MIS'), ('DE_STRINGS.TXT', 'TXT'), ('CAMPAIGN.XML', 'XML'),
         ('DEMOLITIONS-01.ATR', 'ATR'), ('EN_STRINGS.RES', 'RES'),
         ('MULTIPLAYER_KIT.DIR', 'OTHER'), ('GR_VOXLIST.LST', 'OTHER'),
         ('MP04_VALLEY.BMZ', 'RSB'), ('D01_BEACH.BMZ', 'RSB'), ('PKM.BMZ', 'RSB'),
         ('MAIN_MENU_PS2.RSB', 'RSB'), ('M11_POW_CAMP.BMZ', 'RSB'),
         ('ZZZ.PSS', 'MEDIA'), ('MUSIC.TM', 'MEDIA'), ('BNK_95_05.SS', 'MEDIA'),
         ('LOGOUBI.PSS', 'MEDIA'), ('D01_BEACH.SHT', 'MEDIA'), ('D01_BEACH.AOL', 'OTHER'),
         ('SLUS_206.13', 'ELF'), ('ILINK.IRX', 'ISO_FILE'))
by = {}
for c in conts:
    by.setdefault((c['name'], c['kind']), c)
print('%-28s %-8s %10s | %8s %8s %8s %8s' %
      ('name', 'kind', 'blob', 'L>=12', 'L>=16', 'L>=20', 'L>=24'))
for (nm, kd) in names:
    c = by.get((nm, kd))
    if c is None:
        print('   !! 缺 %s' % nm)
        continue
    blob, _r = FU.container_blob(iso, c)
    row = []
    for L in (12, 16, 20, 24):
        n, b, d = longs(blob, L)
        row.append('%d/%.4f' % (n, 100.0 * b / max(1, len(blob))))
    print('%-28s %-8s %10d | %8s %8s %8s %8s' % (nm[:28], kd, len(blob), *row))

print('\n--- 全盘: 每个容器的 L>=16 字节占比 分布 (按 kind, 只统计 >=64B 的容器) ---')
agg = collections.defaultdict(list)
for c in conts:
    blob, _r = FU.container_blob(iso, c)
    if len(blob) < 64:
        continue
    n, b, d = longs(blob, 16)
    agg[c['kind']].append((b / float(len(blob)), n, d, c['name']))
print('%-10s %5s %10s %10s %10s %10s' % ('kind', 'n', '中位%', 'p90%', '最大%', '最大容器'))
for k in sorted(agg):
    v = sorted(agg[k])
    med = v[len(v) // 2][0] * 100
    p90 = v[int(len(v) * .9)][0] * 100
    print('%-10s %5d %10.4f %10.4f %10.4f %s' %
          (k, len(v), med, p90, v[-1][0] * 100, v[-1][3][:28]))
iso.close()
