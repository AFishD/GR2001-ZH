# -*- coding: utf-8 -*-
r"""verify_h640_rows.py — 独立核算 h=640 的行/格账（核对"418 空闲格 ≥ 368"）

网格: Y0=2 CH=16 NCOL=62 SKIP_ROW=12 SKIP_ROWS=3  ⇒ y(r) = 2 + 16*(r + 3*[r>=12])
已知占用（来自图集逐行墨量与 FONT.RES 记录）:
  行 0..23  满墨（主字区）
  行 24     部分占用（y=434；尾段空闲）
  行 25/26  EN 带 (v0,v1)=(452,468) 92 条记录
  行 27     键盘带 (v0,v1)=(482,498) 28 条记录
"""
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
Y0, CH, NCOL, SKIP_ROW, SKIP_ROWS = 2, 16, 62, 12, 3


def y(r):
    return Y0 + CH * (r + (SKIP_ROWS if r >= SKIP_ROW else 0))


print('=== h=640 行表 ===')
rows = []
r = 0
while y(r) + CH <= 640:
    rows.append(r)
    r += 1
print('  总行数 %d (row 0..%d)' % (len(rows), rows[-1]))
print('  总格数 = %d × %d = **%d**' % (len(rows), NCOL, len(rows) * NCOL))
print()
for r in rows:
    yy = y(r)
    tag = ''
    if r <= 23:
        tag = '主字区（满墨）'
    elif r == 24:
        tag = '部分占用（尾段可放新字）'
    elif r in (25, 26):
        tag = '★ EN 带 (452/468) ×92 —— 计划搬走'
    elif r == 27:
        tag = '★ 键盘带 (482/498) ×28 —— 计划搬走'
    elif r >= 28:
        tag = '★ 新增可用行'
    print('  row %-3d y=%-4d .. %-4d  %s' % (r, yy, yy + CH, tag))
print()
print('=== 空闲格核算（按执行任务的 418 的口径）===')
tail24 = 46
freed = 3 * NCOL           # row 25/26/27 搬走两条带后腾出
new = 3 * NCOL             # row 28/29/30
print('  行24尾段          %3d' % tail24)
print('  行25/26/27（腾出） %3d' % freed)
print('  行28/29/30（新增） %3d' % new)
print('  ─────────────────────')
print('  合计              %3d  ⇒ 需求 368 ⇒ %s（余 %d）' % (tail24 + freed + new, '✅ 够' if tail24 + freed + new >= 368 else '✗ 不够', tail24 + freed + new - 368))
print()
print('=== 更宽口径（若两条带搬到 row 31+ 之后，其原占格全释放）===')
print('  行 31..%d 可用作两条带的新家 = 每行 %d 格' % (rows[-1], NCOL))
print('  ⇒ 两条带共 92+28 = 120 条记录，占 ~%d 格 ⇒ 行 31/32 两行 = %d 格 足够 ✓' % (120, 2 * NCOL))
print('  ⇒ 那样可释放的行更多，但**执行任务给的 418 是保守值，已足够** ✓')
