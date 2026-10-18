# -*- coding: utf-8 -*-
r"""round59 / 复核 step 1 (只读): 现役盘 GR_ZH108 上 "x=1008 的搬字记录" 到底有几条、是不是那 4 条、
   x=1008 是不是**唯一**越过安全上界的落点、以及安全上界到底是多少。

只读: 只 mmap 读 3 张盘 (GR_ZH108 现役 / GR_ZH98 搬字前 / GR_EN_ORIG 原版), 一个字节都不写回盘。

产出 (写进本目录):
  recon_zh109.json   全部数字 (给补丁的硬断言当基线)
  recon_zh109.log    人读日志

用法: python recon_zh109.py
"""
import io
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:                                                       # noqa: BLE001
    pass

import csv                                                              # noqa: E402
import dump_font as D                                                   # noqa: E402
import tcslib                                                           # noqa: E402

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
ISO108 = os.path.join(REPO, 'work', 'builds', 'GR_ZH108', 'GR_ZH108.iso')
ISO98 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
ISOEN = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
TEXT108 = os.path.join(REPO, 'work', 'builds', 'GR_ZH108', 'text')
LAYOUT54 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r54', 'layout.json')
FACE_ORDER = ['large', 'default', 'huge']
W, H = 1024, 512
LOG = []


def log(s=''):
    print(s)
    LOG.append(s)


def face_tables(ft_blob):
    p = 0
    l0 = struct.unpack_from('<I', ft_blob, p)[0]
    p += 4 + l0
    nf = struct.unpack_from('<I', ft_blob, p)[0]
    p += 4
    out = []
    for _ in range(nf):
        l = struct.unpack_from('<I', ft_blob, p)[0]
        nm = ft_blob[p + 4:p + 4 + l].decode('latin-1')
        p += 4 + l
        fld = list(struct.unpack_from('<14I', ft_blob, p))
        p += 56
        nrec = fld[4] * fld[5]
        out.append((nm, fld, p, nrec))
        p += nrec * 10
    return out


def load(iso):
    w = D.load_font(iso)
    ad = w['atlas']
    g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(ad['h'], ad['w'])
    ink = g < 128
    tables = face_tables(w['ft_blob'])
    rec = {}
    for (nm, fld, off, nrec) in tables:
        d = {}
        for i in range(nrec):
            b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', w['ft_blob'], off + 10 * i)
            d[i + 0x20] = (b0, b1, u0, v0, u1, v1)
        rec[nm] = d
    return dict(w=w, ad=ad, ink=ink, tables=tables, rec=rec, W=ad['w'], H=ad['h'],
                names=[t[0] for t in tables])


def text_occ(textdir):
    occ = {}
    for fn in sorted(os.listdir(textdir)):
        if fn.endswith(('_text_long.csv', '_text_long_nowrap.csv', '_text_short.csv')):
            with io.open(os.path.join(textdir, fn), encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f):
                    for ch in (row.get('text_edited') or ''):
                        occ[ch] = occ.get(ch, 0) + 1
    return occ


def rects_of(M, nm):
    """非退化矩形 {code: (u0,v0,u1,v1)}。"""
    return {c: r[2:6] for c, r in M['rec'][nm].items() if r[4] > r[2] and r[5] > r[3]}


def main():
    doc = {}
    log('=' * 100)
    log('round59 复核: 现役盘 GR_ZH108 上「x=1008」的那几条搬字记录 + 安全上界取证 (只读)')
    log('=' * 100)

    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    code2ch = {int(v): k for k, v in cs['codes'].items()}
    occ = text_occ(TEXT108)
    KEEP_HARD = {0x7B, 0x7D, 0xB1, 0xB5}

    def is_live(code):
        if code in KEEP_HARD or 0x20 <= code <= 0x7E:
            return True
        if code in code2ch:
            return occ.get(code2ch[code], 0) > 0
        return False

    M108 = load(ISO108)
    M98 = load(ISO98)
    MEN = load(ISOEN)
    log('装载: 108 面=%s; 98 面=%s; EN 面=%s' % (M108['names'], M98['names'], MEN['names']))
    log('图集: 108 = %dx%d psm=0x%02X; 98 = %dx%d psm=0x%02X; EN = %dx%d psm=0x%02X'
        % (M108['ad']['w'], M108['ad']['h'], M108['ad']['psm'],
           M98['ad']['w'], M98['ad']['h'], M98['ad']['psm'],
           MEN['ad']['w'], MEN['ad']['h'], MEN['ad']['psm']))
    doc['atlas'] = dict(zh108=[M108['ad']['w'], M108['ad']['h'], M108['ad']['psm']],
                        zh98=[M98['ad']['w'], M98['ad']['h'], M98['ad']['psm']],
                        en=[MEN['ad']['w'], MEN['ad']['h'], MEN['ad']['psm']])

    # ── ① 三张盘: 所有 face 的矩形 x 上界 ────────────────────────────────
    log('')
    log('① 各盘各 face 的矩形 u/v 上界 (只统计非退化矩形):')
    up = {}
    for tag, M in (('GR_ZH108', M108), ('GR_ZH98', M98), ('GR_EN_ORIG', MEN)):
        for nm in M['names']:
            rs = rects_of(M, nm)
            if not rs:
                continue
            mu1 = max(r[2] for r in rs.values())
            mv1 = max(r[3] for r in rs.values())
            nx = sorted(c for c, r in rs.items() if r[2] > 992)
            up['%s/%s' % (tag, nm)] = dict(n=len(rs), max_u1=mu1, max_v1=mv1,
                                           over992=['0x%02X' % c for c in nx])
            log('   %-18s 记录 %3d 条  max(u1)=%4d  max(v1)=%3d  u1>992 的: %s'
                % ('%s/%s' % (tag, nm), len(rs), mu1, mv1,
                   ' '.join('0x%02X' % c for c in nx) or '(无)'))
    doc['u1_bounds'] = up

    # ── ② 现役盘: u0 >= 976 / u1 > 992 的逐条明细 ───────────────────────
    log('')
    log('② 现役盘 GR_ZH108 上 u0 >= 976 的记录 (全 3 face; 附是否活字形/正文出现次数):')
    det = []
    for nm in FACE_ORDER:
        rs = rects_of(M108, nm)
        for c in sorted(rs):
            u0, v0, u1, v1 = rs[c]
            if u0 < 976:
                continue
            ink = int(M108['ink'][v0:v1, u0:u1].sum())
            ch = code2ch.get(c, '')
            det.append(dict(face=nm, code='0x%02X' % c, char=ch, rect=[u0, v0, u1, v1],
                            w=u1 - u0, h=v1 - v0, ink=ink, live=is_live(c),
                            occ=occ.get(ch, 0), in_charset=bool(ch)))
    for d in det:
        log('   %-7s %-6s %-3s rect=(%4d,%3d,%4d,%4d) %2dx%-2d ink=%4d 活=%-5s 正文=%d %s'
            % (d['face'], d['code'], d['char'] or '-', d['rect'][0], d['rect'][1], d['rect'][2],
               d['rect'][3], d['w'], d['h'], d['ink'], d['live'], d['occ'],
               '(charset)' if d['in_charset'] else '(无映射)'))
    doc['x_ge_976'] = det
    big = sorted(set(d['code'] for d in det if d['rect'][0] >= 992 and d['ink'] > 0))
    log('   ⇒ u0>=992 且**有墨**的码位 %d 条: %s' % (len(big), ' '.join(big)))
    log('   ⇒ u0>=992 但有墨的记录里**活着**的: %s'
        % ' '.join(d['code'] + (d['char'] or '?') for d in det
                   if d['rect'][0] >= 992 and d['ink'] > 0 and d['live']))
    doc['bad_inked'] = big

    # ── ③ 「个」的 before/after: 记录 + 像素 ────────────────────────────
    log('')
    log('③ 0xEE「个」: 搬字前 (GR_ZH98) vs 现役 (GR_ZH108) 记录与像素:')
    ee = {}
    for tag, M in (('GR_ZH98', M98), ('GR_ZH108', M108)):
        for nm in FACE_ORDER:
            r = M['rec'][nm].get(0xEE)
            if r is None:
                continue
            ee['%s/%s' % (tag, nm)] = list(r)
            log('   %-18s pad=%d advance=%d rect=(%d,%d,%d,%d) 框内墨=%d'
                % ('%s/%s' % (tag, nm), r[0], r[1], r[2], r[3], r[4], r[5],
                   int(M['ink'][r[3]:r[5], r[2]:r[4]].sum())))
    doc['code_0xEE'] = ee
    old = ee['GR_ZH98/large']
    new = ee['GR_ZH108/large']
    a = M98['ink'][old[3]:old[5], old[2]:old[4]]
    b = M108['ink'][new[3]:new[5], new[2]:new[4]]
    log('   ⇒ 搬字前 (288,354,304,370) 的 16x16 点阵 与 现役 (1008,195,1024,211) 的点阵: '
        '墨 %d vs %d, 逐像素相等=%s (差异 %d px)'
        % (int(a.sum()), int(b.sum()), bool(np.array_equal(a, b)), int((a ^ b).sum())))
    doc['code_0xEE_pixels_equal'] = bool(np.array_equal(a, b))
    # 现役盘上旧位置是否已清空
    cleared = int(M108['ink'][old[3]:old[5], old[2]:old[4]].sum())
    log('   ⇒ 现役盘上**旧位置** (288,354,304,370) 的墨 = %d %s'
        % (cleared, '(已清空 ✓)' if cleared == 0 else '(没清干净!)'))
    doc['code_0xEE_old_cleared'] = cleared
    # 这一格点阵长什么样 (ASCII 画出来给人看)
    log('   搬字前那 16x16 点阵 (# = 墨):')
    for row in a:
        log('      ' + ''.join('#' if v else '.' for v in row))

    # ── ④ 双 84 条搬字记录的落点 vs x 上界 ─────────────────────────────
    lay = json.load(io.open(LAYOUT54, encoding='utf-8'))
    log('')
    log('④ round54 的 layout.json: 计划 %d 条, bands=%s x_step=%d n_cells=%d'
        % (len(lay['moves']), lay['layout']['bands'], lay['layout']['x_step'],
           lay['layout']['n_cells']))
    over = [m for m in lay['moves'] if m['new'][0] >= 992]
    log('   计划里落点 x>=992 的 %d 条: %s'
        % (len(over), ' '.join('0x%02X%s@%d' % (m['code'], m['char'], m['new'][0]) for m in over)))
    log('   计划里落点 x 最大值 = %d (64 列布局 ⇒ 最右格 x=1008)' % max(m['new'][0] for m in lay['moves']))
    doc['layout54'] = dict(n=len(lay['moves']), bands=lay['layout']['bands'],
                           x_step=lay['layout']['x_step'], n_cells=lay['layout']['n_cells'],
                           max_new_x=max(m['new'][0] for m in lay['moves']),
                           planned_x_ge_992=[dict(code='0x%02X' % m['code'], char=m['char'],
                                                  old=m['old'], new=m['new']) for m in over])
    # 逐条: 计划的新矩形 与 现役盘上的实际矩形 对照; 像素与 GR_ZH98 旧矩形对照
    log('')
    log('   逐条核对 (计划 new vs 现役盘实际; 像素 = 现役新矩形 vs GR_ZH98 旧矩形):')
    n_px_ok, n_px_bad, moved_now = 0, [], 0
    rows = []
    for m in lay['moves']:
        c = m['code']
        r98 = M98['rec']['large'].get(c)
        r108 = M108['rec']['large'].get(c)
        old98 = list(r98[2:6]) if r98 else None
        cur = list(r108[2:6]) if r108 else None
        cur_ink = int(M108['ink'][cur[1]:cur[3], cur[0]:cur[2]].sum()) if cur else 0
        pa = M98['ink'][m['old'][1]:m['old'][3], m['old'][0]:m['old'][2]]
        pb = M108['ink'][cur[1]:cur[3], cur[0]:cur[2]] if cur else None
        same = bool(pb is not None and pa.shape == pb.shape and np.array_equal(pa, pb))
        if same:
            n_px_ok += 1
        else:
            n_px_bad.append(dict(code='0x%02X' % c, char=m['char'], planned=m['new'],
                                 actual=cur, ink_now=cur_ink, ink_98=int(pa.sum())))
        moved_now += 1 if (cur and cur != old98) else 0
        rows.append(dict(code='0x%02X' % c, char=m['char'], old98=old98, planned=m['new'],
                         actual=cur, actual_ink=cur_ink, px_equal_to_98_old=same))
    log('   84 条里: 现役盘矩形 != GR_ZH98 矩形 (真被搬过) = %d 条; '
        '现役新矩形像素 == GR_ZH98 旧矩形像素 = %d/%d 条'
        % (moved_now, n_px_ok, len(lay['moves'])))
    if n_px_bad:
        log('   !! 像素对不上的: %s' % json.dumps(n_px_bad, ensure_ascii=False)[:800])
    doc['layout54_rows'] = rows
    doc['layout54_px_ok'] = n_px_ok
    doc['layout54_px_bad'] = n_px_bad

    # ── ⑤ 安全上界证据: 对偶网格最大 x + 活字形落点 ─────────────────────
    live_cols = {}
    maxx = -1
    for ch, (b1, b2) in cs['pair_of'].items():
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            continue
        slot = tcslib.pair_slot(b1, b2)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        maxx = max(maxx, x)
        live_cols.setdefault(x, []).append(ch)
    log('')
    log('⑤ 安全上界证据 (对偶网格公式 tcslib.atlas_cell_xy_engine_view: x = 16*(slot%%62), col<=61):')
    log('   全部在册对偶字 %d 个, 引擎采样格 x 最大值 = **%d** (col=61), 即引擎自己寻址到的最右一列'
        % (sum(len(v) for v in live_cols.values()), maxx))
    for x in sorted(live_cols)[-4:]:
        log('     x=%4d (col=%2d): %d 个活字形, 例: %s'
            % (x, x // 16, len(live_cols[x]), ''.join(live_cols[x][:12])))
    doc['pair_grid_max_x'] = maxx
    doc['pair_grid_cols'] = {str(k): len(v) for k, v in sorted(live_cols.items())}
    # 这些格子真的有墨吗
    ink_at_max = 0
    for ch in live_cols[maxx]:
        slot = tcslib.pair_slot(*cs['pair_of'][ch])
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        ink_at_max += int(M108['ink'][y:y + 16, x:x + 16].sum())
    log('   x=%d 那一列 %d 个活字形在图集上的总墨 = %d px ⇒ 引擎确实在采样 x=%d 并画得出来'
        % (maxx, len(live_cols[maxx]), ink_at_max, maxx))
    doc['pair_grid_max_x_ink'] = ink_at_max

    # ── ⑥ 现役盘: 单字节/ASCII 224 条记录里 u1 > 992 的 ────────────────
    log('')
    log('⑥ 现役盘 default 面 224 条记录里 u1 > 992 (越过 x=976+16=992 这条线) 的:')
    rs = rects_of(M108, 'default')
    cnt = 0
    for c in sorted(rs):
        u0, v0, u1, v1 = rs[c]
        if u1 <= 992:
            continue
        cnt += 1
        ch = code2ch.get(c, '')
        log('   0x%02X %-3s rect=(%4d,%3d,%4d,%4d) ink=%4d 活=%s 正文=%d'
            % (c, ch or '-', u0, v0, u1, v1, int(M108['ink'][v0:v1, u0:u1].sum()),
               is_live(c), occ.get(ch, 0)))
    log('   共 %d 条' % cnt)
    doc['default_u1_over_992'] = cnt

    # ── ⑦ 现役盘: 可落点清单 (bands y=195/211, x<=976, 无墨/无记录/无对偶格) ──
    used_mask = np.zeros((H, W), dtype=bool)
    for ch, (b1, b2) in cs['pair_of'].items():
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            continue
        x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(b1, b2))
        if 0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H:
            used_mask[y:y + 16, x:x + 16] = True
    rec_mask = np.zeros((H, W), dtype=bool)
    rec_by = {}
    for nm in FACE_ORDER:
        for c, (u0, v0, u1, v1) in rects_of(M108, nm).items():
            rec_mask[v0:v1, u0:u1] = True
            rec_by.setdefault((u0, v0, u1, v1), []).append('0x%02X/%s' % (c, nm))
    free_cells = []
    for y0 in (195, 211):
        for k in range(W // 16):
            x0 = 16 * k
            if x0 + 16 > 976 + 16:            # 只要 x<=976
                continue
            blk = M108['ink'][y0:y0 + 16, x0:x0 + 16]
            if blk.any() or used_mask[y0:y0 + 16, x0:x0 + 16].any() \
               or rec_mask[y0:y0 + 16, x0:x0 + 16].any():
                continue
            free_cells.append([x0, y0])
    log('')
    log('⑦ bands y=195/211 内 x<=976 且 无墨/无对偶格/无记录的 16x16 空格: %d 个' % len(free_cells))
    log('   %s' % ' '.join('(%d,%d)' % (x, y) for x, y in free_cells))
    doc['free_cells_bands'] = free_cells

    # ── ⑧ 越界(>=992)区域里到底有什么: 逐列静/动 ───────────────────────
    log('')
    log('⑧ x=976..1023 各 16 列的墨量与覆盖情况:')
    for x0 in range(976, 1024, 16):
        blk = M108['ink'][:, x0:x0 + 16]
        cov = rec_mask[:, x0:x0 + 16]
        log('   x=%4d..%4d 墨 %5d px; 被记录覆盖 %5d px; 被对偶格覆盖 %d px'
            % (x0, x0 + 15, int(blk.sum()), int(cov.sum()),
               int(used_mask[:, x0:x0 + 16].sum())))
    doc['edge_cols'] = dict(
        ink={str(x): int(M108['ink'][:, x:x + 16].sum()) for x in range(976, 1024, 16)},
        rec={str(x): int(rec_mask[:, x:x + 16].sum()) for x in range(976, 1024, 16)},
        grid={str(x): int(used_mask[:, x:x + 16].sum()) for x in range(976, 1024, 16)})

    io.open(os.path.join(HERE, 'recon_zh109.log'), 'w', encoding='utf-8', newline='\n').write(
        '\n'.join(LOG) + '\n')
    io.open(os.path.join(HERE, 'recon_zh109.json'), 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print('[out] recon_zh109.json / recon_zh109.log')
    return 0


if __name__ == '__main__':
    sys.exit(main())
