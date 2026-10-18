# -*- coding: utf-8 -*-
r"""capacity_now.py — 按**引擎口径**核算字库容量与用量 (GR_ZH93, 方案C 之后)

引擎规则 (来自 patch_zh93_planc.py + docs/REPORT_plan_c_zh93.md):
  · lead 区间 [0xA1, 0xB1)  ⇒ 16 个 lead (0xA1..0xB0)
  · 对偶 slot = (lead-0xA1)*94 + (trail-0xA1),  trail 0xA1..0xFE (94)
  · row = slot//62, col = slot%62
  · 引擎格 x = 16*((col + PHI[row]) % 64),  y = 2 + 16*(row + 3*[row>=12])
  · 单字节码: 字节不在 lead 区间 ⇒ 走单字节路径
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
PNG = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'font', 'GR_ZH93_font_atlas.png')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LEAD_LO, LEAD_HI = 0xA1, 0xB1
TRAIL_LO, TRAIL_HI = 0xA1, 0xFF
NCOL = 62
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36,
       19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


def engine_cell(slot):
    r, c = slot // NCOL, slot % NCOL
    return 16 * ((c + PHI.get(r, 0)) % 64), yrow(r), r, c


def tool_cell(slot):
    """工具旧口径: atlas_cell_xy (NCOL=62, 无相位)"""
    r, c = slot // NCOL, slot % NCOL
    return 16 * c, yrow(r), r, c


def main():
    cs = json.load(io.open(CS, encoding='utf-8'))
    pairs = cs['pair_of']
    singles = cs['codes']

    n_lead = LEAD_HI - LEAD_LO
    n_trail = TRAIL_HI - TRAIL_LO
    cap_pair = n_lead * n_trail
    used_pair = len(pairs)
    print('=' * 74)
    print('字库容量与用量 (GR_ZH93, 方案C: lead 0xA1..0xB0)')
    print('=' * 74)
    print('【对偶(双字节)码位】')
    print('  容量 = %d lead (0xA1..0x%02X) × %d trail (0xA1..0x%02X) = %d'
          % (n_lead, LEAD_HI - 1, n_trail, TRAIL_HI - 1, cap_pair))
    print('  已用 = %d   ⇒ 空位 = %d' % (used_pair, cap_pair - used_pair))
    print('【单字节码位】')
    print('  已用 = %d 个 (0x%02X..0xFF 区间; lead 区间内不再允许单字节)'
          % (len(singles), min(singles.values())))
    print('【字符总数】charset 单字节 %d + 对偶 %d = %d 字'
          % (len(singles), len(pairs), len(singles) + len(pairs)))

    # 引擎格 vs 工具格 差异
    diff = [s for s in range(cap_pair) if engine_cell(s)[:2] != tool_cell(s)[:2]]
    print()
    print('【★ 格位公式差异】引擎格 vs 工具旧格位(atlas_cell_xy)')
    print('  公式不同而落点不同的 slot: %d / %d' % (len(diff), cap_pair))
    if diff:
        print('  例: slot %d → 引擎 %s / 工具 %s' % (diff[0], engine_cell(diff[0])[:2], tool_cell(diff[0])[:2]))

    # 图集占用: 从 dump 出的 PNG (2 倍最近邻) 还原 1024x512, 0=墨 1=空
    try:
        from PIL import Image
    except ImportError:
        print('\n(无 PIL, 跳过图集占用统计)')
        return
    im = Image.open(PNG).convert('L')
    w, h = im.size
    px = im.load()
    scale = w // 1024

    def cell_ink(x, y):
        """引擎格 (x,y) 里的墨点数 (0=墨)"""
        n = 0
        for dy in range(16):
            for dx in range(16):
                if px[(x + dx) * scale, (y + dy) * scale] < 128:
                    n += 1
        return n

    print()
    print('【图集】%dx%d (原图 %dx%d)' % (1024, 512, w, h))

    # 已用字的字形在位情况
    no_glyph = []
    for ch, (b1, b2) in pairs.items():
        s = (b1 - LEAD_LO) * 94 + (b2 - TRAIL_LO)
        x, y, r, c = engine_cell(s)
        if cell_ink(x, y) == 0:
            no_glyph.append((ch, s, x, y))
    print('  对偶字 %d 个中, 引擎格**空白**(无字形): %d 个' % (len(pairs), len(no_glyph)))
    if no_glyph:
        print('    ' + ', '.join('%s(slot %d)' % (c, s) for c, s, _, _ in no_glyph[:12]))

    # 空位里"引擎格真空"的 (可直接用)
    free_clean, free_dirty = [], []
    for s in range(cap_pair):
        if s in {(b1 - LEAD_LO) * 94 + (b2 - TRAIL_LO) for b1, b2 in pairs.values()}:
            continue
        x, y, r, c = engine_cell(s)
        (free_clean if cell_ink(x, y) == 0 else free_dirty).append(s)
    print()
    print('【★ 对偶空位的可用性 (关键)】')
    print('  空位总数            : %d' % (cap_pair - used_pair))
    print('  其中 引擎格真空(可直接用): **%d**' % len(free_clean))
    print('  其中 引擎格已有活字形(需先回收/重排): %d' % len(free_dirty))

    # 单字节码的占用
    used_single = sorted(singles.values())
    print()
    print('【单字节码位】已用 %d 个: %s%s'
          % (len(used_single), ' '.join('%02X' % b for b in used_single[:20]),
             ' …' if len(used_single) > 20 else ''))
    print('  剩余可用单字节码 (非 lead 区间且未被占用): ', end='')
    free_single = [b for b in range(0x80, 0x100) if not (LEAD_LO <= b < LEAD_HI) and b not in singles.values()]
    print('%d 个: %s%s' % (len(free_single), ' '.join('%02X' % b for b in free_single[:24]),
                          ' …' if len(free_single) > 24 else ''))


if __name__ == '__main__':
    main()
