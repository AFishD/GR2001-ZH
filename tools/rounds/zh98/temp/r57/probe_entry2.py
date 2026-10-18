# -*- coding: utf-8 -*-
r"""r57 探针3: 用 img_entry 遍历 GR.IMG 全条目, 找 0x1F035800 归属; 并看被过滤掉的条目 (只读)。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
iso = tcslib.Iso(ISO)
GR = 19175
LO = 0x1F035800
n = FC.img_entry_count(iso, GR)
print('GR.IMG 条目数 (名字表口径) = %d' % n)
rows = []
skipped = []
for i in range(n):
    try:
        e = iso.img_entry(GR, i)
    except Exception as exc:                                           # noqa: BLE001
        print('  #%d img_entry 抛异常: %s' % (i, exc))
        break
    if e['stored'] <= 0 or e['off'] <= 0 or e['stored'] > 0x7FFFFFFF:
        skipped.append((i, e['name'], e['off'], e['stored'], e['real'], e['iso_off']))
        continue
    rows.append((e['iso_off'], e['iso_off'] + e['stored'], i, e['name'], e['stored'], e['real']))
rows.sort()
print('有效条目 %d, 被过滤 %d' % (len(rows), len(skipped)))
for (i, nm, off, st, rl, io) in skipped[:20]:
    print('   [跳过] #%-5d %-28s off %-9d stored 0x%-8X real 0x%-8X iso_off 0x%X'
          % (i, nm, off, st, rl, io))
import bisect                                                          # noqa: E402
starts = [r[0] for r in rows]
k = bisect.bisect_right(starts, LO) - 1
print('\n0x%X 附近:' % LO)
for j in range(max(0, k - 4), min(len(rows), k + 5)):
    a, b, i, nm, st, rl = rows[j]
    print('   0x%X..0x%X #%-5d %-28s stored 0x%X real 0x%X %s'
          % (a, b, i, nm, st, rl, '★ 命中' if a <= LO < b else ''))
# 空隙统计
print('\n最大的 5 个空隙 (条目之间):')
gaps = []
for j in range(1, len(rows)):
    g = rows[j][0] - rows[j - 1][1]
    if g > 0:
        gaps.append((g, rows[j - 1][1], rows[j][0], rows[j - 1][3], rows[j][3]))
gaps.sort(reverse=True)
for g, a, b, na, nb in gaps[:5]:
    print('   0x%X..0x%X (%d B)  %s → %s %s' % (a, b, g, na, nb, '★ 含目标' if a <= LO < b else ''))
iso.close()
