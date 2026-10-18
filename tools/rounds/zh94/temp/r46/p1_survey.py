# -*- coding: utf-8 -*-
r"""p1_survey.py — round46 勘察: 引擎格 / 可用格 / FT 记录矩形 / 现状用量。

只读。回答:
  ① 1504 个对偶 slot 各自的引擎格 (16*col, yrow(row));
  ② 哪些格被 ATLAS_ENGINE_SINGLE_CELLS 显式禁用 (51 个);
  ③ 哪些格被 **任何 face 的 FT 记录矩形** 覆盖 (排除②后还剩多少);
  ④ 哪些格被**手柄图标码**的小矩形覆盖;
  ⑤ 现状: 已用 pair 槽 = ?, 真正空白可用格 = ?, 剩余可用格 = ?
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
import dump_font                                       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'GR_ZH94.iso')
W, H = 1024, 512
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH


def yrow(r):
    return tcslib.GRID_Y0 + CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def main():
    font = dump_font.load_font(ISO)
    atlas, faces = font['atlas'], font['faces']
    gray = dump_font.atlas_gray(atlas, view='engine')
    ink = np.frombuffer(gray, dtype=np.uint8).reshape(H, W) == 0
    print('[atlas] psm=0x%02X %dx%d  引擎图墨点=%d' % (atlas['psm'], W, H, int(ink.sum())))

    cs = tcslib.Charset()
    print('[cs   ] pair=%d single=%d' % (len(cs.enc_pair), len(cs.enc_single)))

    # ---- ① 全部 slot → 格 ----
    slots = {}
    for s in range(tcslib.pair_capacity()):
        r, c = s // NCOL, s % NCOL
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        slots[s] = (r, c, x, y)
    bad = [s for s, (r, c, x, y) in slots.items() if y + CH > H or x + CW > W]
    print('[slot ] 容量=%d; 引擎格越出图集的 slot=%d %s'
          % (len(slots), len(bad), bad[:8]))
    rows = sorted(set(r for (r, c, x, y) in slots.values()))
    print('[slot ] 用到的网格行 = %s' % rows)
    print('[slot ] 行 24 的有效列 = %s'
          % sorted(set(c for (r, c, x, y) in slots.values() if r == 24)))

    # ---- ② 显式禁用 ----
    forb = dict(tcslib.ATLAS_ENGINE_SINGLE_CELLS)
    print('[forb ] ATLAS_ENGINE_SINGLE_CELLS = %d 格' % len(forb))

    # ---- ③ FT 记录矩形 (3 个 face 全部) ----
    protect = np.zeros((H, W), dtype=bool)
    rects = []
    for fname, fld, rs in faces:
        n = 0
        for idx, r in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            x0, x1 = max(0, u0), min(W, u1)
            y0, y1 = max(0, v0), min(H, v1)
            if x0 >= x1 or y0 >= y1:
                continue
            protect[y0:y1, x0:x1] = True
            rects.append((fname, idx + 0x20, u0, v0, u1, v1))
            n += 1
        print('[ft   ] face %-8s recs=%d 有效矩形=%d' % (fname, len(rs), n))
    print('[ft   ] 合计矩形 %d 条, 保护像素 %d (%.1f%% 图集)'
          % (len(rects), int(protect.sum()), 100.0 * protect.sum() / (W * H)))

    # ---- ④ 每格的判定 ----
    stat = dict(total=0, oob=0, forbidden=0, ft_hit=0, ink=0, blank=0)
    cat = {}
    for s in sorted(slots):
        r, c, x, y = slots[s]
        stat['total'] += 1
        if y + CH > H or x + CW > W:
            stat['oob'] += 1
            cat[s] = 'oob'
            continue
        if forb.get((r, c)):
            stat['forbidden'] += 1
            cat[s] = 'forbidden'
            continue
        if protect[y:y + CH, x:x + CW].any():
            stat['ft_hit'] += 1
            cat[s] = 'ft_rect'
            continue
        if ink[y:y + CH, x:x + CW].any():
            stat['ink'] += 1
            cat[s] = 'has_ink'
        else:
            stat['blank'] += 1
            cat[s] = 'blank'
    print()
    print('[格   ] 总 %(total)d = 越界 %(oob)d + 显式禁用 %(forbidden)d + 记录矩形 %(ft_hit)d '
          '+ 有墨 %(ink)d + **空白** %(blank)d' % stat)

    # ---- ⑤ 现状用量 ----
    used = {}
    for ch, (b1, b2) in cs.enc_pair.items():
        if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
            used[tcslib.pair_slot(b1, b2)] = ch
    dead = {ch: v for ch, v in cs.enc_pair.items() if not (tcslib.PAIR_LEAD_LO <= v[0] < tcslib.PAIR_LEAD_HI)}
    print('[用量 ] 在用 pair 槽(lead 合法)=%d; 死 pair=%d %s' % (len(used), len(dead), list(dead)[:10]))
    bad_use = [(s, used[s], cat[s]) for s in sorted(used) if cat[s] in ('forbidden', 'ft_rect', 'oob')]
    print('[用量 ] ★ 在用但坐在"不可用格"上的 pair 槽: %d 个' % len(bad_use))
    for s, ch, k in bad_use:
        r, c, x, y = slots[s]
        print('        %s slot=%d (row%d col%d) cell=(%d,%d) 格类别=%s' % (ch, s, r, c, x, y, k))
    free = [s for s in sorted(slots) if s not in used]
    print('[用量 ] 未占用 slot = %d' % len(free))
    fc = {}
    for s in free:
        fc[cat[s]] = fc.get(cat[s], 0) + 1
    print('[用量 ] 其中按格分类: %s' % fc)
    usable = stat['blank'] + stat['ink']            # 允许给 pair 用、但可能有旧墨
    print('[容量 ] **允许给对偶码用的格** = 1504 - 越界%d - 禁用%d - 记录矩形%d = %d'
          % (stat['oob'], stat['forbidden'], stat['ft_hit'], usable))
    print('[容量 ] 减去在用 %d ⇒ 重排后理论上可空出 %d 格' % (len(used), usable - len(used)))

    # ---- 谁把格占死了? 按行统计 ----
    print()
    print('[分行 ] row  yrow  总格 禁用 记录矩形 有墨 空白   在用pair')
    for r in rows:
        cs_ = [s for s in slots if slots[s][0] == r]
        f_ = sum(1 for s in cs_ if cat[s] == 'forbidden')
        t_ = sum(1 for s in cs_ if cat[s] == 'ft_rect')
        i_ = sum(1 for s in cs_ if cat[s] == 'has_ink')
        b_ = sum(1 for s in cs_ if cat[s] == 'blank')
        u_ = sum(1 for s in cs_ if s in used)
        print('        %3d  %4d  %4d  %4d  %6d  %4d  %4d   %6d'
              % (r, yrow(r), len(cs_), f_, t_, i_, b_, u_))

    # ---- 落在网格行上的 FT 记录矩形明细 (前 60) ----
    print()
    print('[明细 ] 与网格行相交的 FT 记录矩形 (前 80 条):')
    n = 0
    for (fn, code, u0, v0, u1, v1) in rects:
        hit = [r for r in rows if yrow(r) < v1 and yrow(r) + CH > v0]
        if not hit:
            continue
        cols = [c for c in range(NCOL)
                if any(x0 < u1 and u0 < x0 + CW for x0 in (CW * c,))
                and any(yrow(r) < v1 and v0 < yrow(r) + CH for r in hit)]
        print('        %-8s code=0x%02X (%4d,%4d)-(%4d,%4d) rows=%s cols=%s'
              % (fn, code, u0, v0, u1, v1, hit, cols))
        n += 1
        if n >= 80:
            print('        … 还有更多')
            break

    out = dict(stats=stat, cat=dict((str(k), v) for k, v in cat.items()),
               used=sorted(used), rects=[dict(face=f, code=c, u0=u0, v0=v0, u1=u1, v1=v1)
                                         for (f, c, u0, v0, u1, v1) in rects])
    with open(os.path.join(HERE, 'p1_survey.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print()
    print('[out  ] → %s' % os.path.join(HERE, 'p1_survey.json'))


if __name__ == '__main__':
    main()
