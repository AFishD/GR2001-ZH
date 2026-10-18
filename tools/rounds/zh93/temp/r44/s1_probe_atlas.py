# -*- coding: utf-8 -*-
r"""s1_probe_atlas.py (round44 实验) — 量化四张盘的图集: psm / 尺寸 / 逐行墨点 / 引擎采样覆盖

只读。产出 log + json (temp/r44/)。
回答的问题是:
  ① 各盘图集记录的 psm 到底是多少 (0x13=8bpp / 0x14=4bpp) —— 线性读法按 psm 选;
  ② y=0 / y=1 的墨点有多少、在哪; 是"字形顶边"还是别的;
  ③ 引擎格位公式枚举出的**全部采样窗**覆盖了图集的哪些行 ⇒ y=0/y=1 是否被采样;
  ④ 逐行"孤儿墨点" (= 不落在任何引擎采样窗里的墨) 分布 ⇒ 有没有 4 行周期。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(p):
    while True:
        if os.path.isfile(os.path.join(p, 'tools', 'text_csv', 'tcslib.py')):
            return p
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit('!! 找不到仓库根')
        p = q


REPO = find_repo(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                      # noqa: E402
import dump_font                                                   # noqa: E402

ISOS = [
    ('GR_EN_ORIG', os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')),
    ('GR_ZH91', os.path.join(REPO, 'work', 'builds', 'GR_ZH91', 'GR_ZH91.iso')),
    ('GR_ZH92', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')),
    ('GR_ZH93', os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')),
]

PSM_NAME = {0x00: 'PSMCT32', 0x02: 'PSMCT16', 0x13: 'PSMT8', 0x14: 'PSMT4',
            0x1B: 'PSMT8H', 0x24: 'PSMT4HL', 0x2C: 'PSMT4HH', 0x30: 'PSMZ32'}


def gray_by_psm(atlas):
    """按 psm 选读法: 0x14 = 4bpp (2 texel/byte, 偶 x 低 nibble); 其余 = 1 texel/byte (8bpp)。"""
    psm, pak, off, w, h = atlas['psm'], atlas['pak'], atlas['px_off'], atlas['w'], atlas['h']
    if psm == 0x14:
        return dump_font.atlas_gray(atlas), '4bpp-linear'
    if psm in (0x13, 0x1B):
        px = pak[off:off + w * h]
        return bytes(0 if b == 0 else 255 for b in px), '8bpp-linear'
    raise SystemExit('!! 没实现 psm=0x%02X 的读法' % psm)


def engine_windows(atlas_w, atlas_h, faces):
    """穷举**引擎可能采样的一切窗** —— 返回 (win_list, 说明 dict)。

    来源全部是本工程已定稿的口径 (tcslib):
      · 对偶码: 全部 1504 个 slot 的引擎格 16x16 (= atlas_cell_xy_engine),
        外加回绕列字形低 1 行的那一份 (y+1 起 16 行);
      · 单字节/ASCII: 三个 face 的全部 FT 记录矩形, 以及记录矩形 +DU/+DV 的实测偏置窗;
      · 再宽放 ±16 px 的"最大可能偏移"(远超任何实测值), 用来把结论做成**下界**。
    """
    wins, notes = [], {}
    n_slot = tcslib.pair_capacity()
    for s in range(n_slot):
        x, y = tcslib.atlas_cell_xy_engine(s)
        wins.append((x, y, x + tcslib.CW, y + tcslib.CH))
        wins.append((x, y + 1, x + tcslib.CW, y + 1 + tcslib.CH))
    n_grid = len(wins)
    n_rec = 0
    for (_nm, _fld, recs) in faces:
        for (_b0, _b1, u0, v0, u1, v1) in recs:
            if u1 <= u0 or v1 <= v0:
                continue
            n_rec += 1
            for (dx, dy) in ((0, 0), (tcslib.GLYPH_DU, tcslib.GLYPH_DV)):
                wins.append((u0 + dx, v0 + dy, u1 + dx, v1 + dy))
    n_single = len(wins) - n_grid
    notes['slots'] = n_slot
    notes['grid_windows'] = n_grid
    notes['record_windows'] = n_single
    notes['records'] = n_rec
    notes['min_y'] = min(w[1] for w in wins)
    notes['max_y'] = max(w[3] for w in wins)
    notes['wide'] = 'grid+record(+DU/+DV)'
    return wins, notes


def row_in_windows(wins, y):
    """该行被哪些窗覆盖 (返回覆盖它的 x 区间列表, 已合并)。"""
    segs = sorted((w[0], w[2]) for w in wins if w[1] <= y < w[3])
    out = []
    for a, b in segs:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def ink_xs(gray, w, y):
    base = y * w
    return [x for x in range(w) if gray[base + x] == 0]


def analyse(tag, iso_path, want_rows=48, full=True):
    print('=' * 78)
    print('[%s] %s' % (tag, os.path.relpath(iso_path, REPO)))
    font = dump_font.load_font(iso_path)
    at = font['atlas']
    print('[%s] 图集: name=%s psm=0x%02X (%s) %dx%d clut=%d px_size=%d px_off=0x%X'
          % (tag, at['name'], at['psm'], PSM_NAME.get(at['psm'], '?'), at['w'], at['h'],
             at['clut'], at['px_size'], at['px_off']))
    gray, how = gray_by_psm(at)
    w, h = at['w'], at['h']
    print('[%s] 像素读法: %s; 墨 texel 总数 = %d' % (tag, how, gray.count(0)))

    wins, wn = engine_windows(w, h, font['faces'])
    print('[%s] 引擎采样窗: %d 个 (格 %d + 记录 %d, 记录 %d 条) y 范围 [%d, %d)'
          % (tag, len(wins), wn['grid_windows'], wn['record_windows'], wn['records'],
             wn['min_y'], wn['max_y']))

    # 逐行: 墨点数 / 左右边界 / 落在窗内 / 窗外的孤儿
    rows = []
    for y in range(h):
        xs = ink_xs(gray, w, y)
        segs = row_in_windows(wins, y)
        inw = sum(1 for x in xs if any(a <= x < b for a, b in segs))
        rows.append(dict(y=y, ink=len(xs), left=(xs[0] if xs else -1), right=(xs[-1] if xs else -1),
                         in_win=inw, orphan=len(xs) - inw,
                         cov=sum(b - a for a, b in segs)))
    n_orphan = sum(r['orphan'] for r in rows)
    rows_with_orphan = [r for r in rows if r['orphan']]
    print('[%s] 墨点总数 %d; 落在引擎窗内 %d; **窗外(引擎永不采样) %d**'
          % (tag, sum(r['ink'] for r in rows), sum(r['in_win'] for r in rows), n_orphan))
    print('[%s] 有孤儿墨点的行: %s'
          % (tag, ', '.join('y=%d:%d' % (r['y'], r['orphan']) for r in rows_with_orphan[:60])
             + (' …共 %d 行' % len(rows_with_orphan) if len(rows_with_orphan) > 60 else '')))
    print('[%s]  前 %d 行明细 (ink=墨点数, in/out=窗内/窗外, cov=该行被窗覆盖的 x 宽):' % (tag, want_rows))
    print('        y   ink  left right   in  out   cov')
    for r in rows[:want_rows]:
        print('      %4d %5d %5d %5d %4d %4d %5d'
              % (r['y'], r['ink'], r['left'], r['right'], r['in_win'], r['orphan'], r['cov']))
    # 每 4 行的周期性: 统计 y%4 == k 的孤儿总数
    per4 = {k: sum(r['orphan'] for r in rows if r['y'] % 4 == k) for k in range(4)}
    per16 = {k: sum(r['orphan'] for r in rows if r['y'] % 16 == k) for k in range(16)}
    print('[%s] 孤儿墨点按 y%%4 分组: %s' % (tag, per4))
    print('[%s] 孤儿墨点按 y%%16 分组: %s' % (tag, per16))

    # y=0 / y=1 是不是被任何窗覆盖?
    for y in (0, 1):
        segs = row_in_windows(wins, y)
        print('[%s] y=%d 被引擎窗覆盖的 x 段: %s ⇒ %s'
              % (tag, y, segs if segs else '无', '**引擎永不采样这一行**' if not segs else '被采样!'))
    # 单独看"y=0 的墨点里有没有任何一个落在窗内"
    xs0 = ink_xs(gray, w, 0)
    print('[%s] y=0 墨点 %d 个: x∈[%s]; 前 64 个 x = %s'
          % (tag, len(xs0), ('%d..%d' % (xs0[0], xs0[-1])) if xs0 else '-',
             xs0[:64] if xs0 else []))
    if len(xs0) and all(xs0[i] + 1 == xs0[i + 1] for i in range(min(13, len(xs0) - 1))):
        print('[%s]   ⚠ y=0 开头有连续段 x=0..%d' % (tag, xs0[13] if len(xs0) > 13 else xs0[-1]))
    for y in (2, 3):
        xs = ink_xs(gray, w, y)
        print('[%s] y=%d 墨点 %d 个: x 前 24 = %s' % (tag, y, len(xs), xs[:24]))
    # raw 前 64 字节 (判断文件头是否有垃圾)
    raw = at['pak'][at['px_off']:at['px_off'] + 64]
    print('[%s] 像素区前 64 字节: %s' % (tag, raw.hex(' ')))
    return dict(tag=tag, iso=os.path.relpath(iso_path, REPO).replace('\\', '/'),
                psm=at['psm'], psm_name=PSM_NAME.get(at['psm'], '?'), w=w, h=h, how=how,
                px_off=at['px_off'], px_size=at['px_size'], clut=at['clut'],
                ink_total=gray.count(0), windows=wn,
                orphan_total=n_orphan,
                orphan_rows=dict((r['y'], r['orphan']) for r in rows_with_orphan),
                per4=per4, per16=per16,
                row0_xs=xs0, head64=raw.hex(),
                rows=[dict(y=r['y'], ink=r['ink'], in_win=r['in_win'], orphan=r['orphan'])
                      for r in rows[:full and 96 or 96]])


def main():
    out = []
    for tag, p in ISOS:
        if not os.path.isfile(p):
            print('!! 缺 ISO: %s' % p)
            continue
        out.append(analyse(tag, p))
    jp = os.path.join(HERE, 's1_probe_atlas.json')
    with io.open(jp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('=' * 78)
    print('[s1] 结论速览')
    for r in out:
        print('  %-11s %-9s %4dx%-4d  墨 %7d  窗外 %6d  y=0 墨 %3d  窗 y 范围 [%d,%d)'
              % (r['tag'], r['psm_name'], r['w'], r['h'], r['ink_total'], r['orphan_total'],
                 len(r['row0_xs']), r['windows']['min_y'], r['windows']['max_y']))
        print('              孤儿按 y%%4: %s' % r['per4'])
    print('[s1] JSON → %s' % os.path.relpath(jp, REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
