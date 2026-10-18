# -*- coding: utf-8 -*-
r"""space_cap.py -- 字库「最大容量」参数化算术（只读，纯计算）。

给定 (W, H, CW, CH, Y0, SKIP_ROW, SKIP_ROWS, NCOL, 图标窗, EN 带)，算：
  * 网格行数 / 可用行 / 可用格
  * GIF 段数 N = ceil(H/64)、两种记账口径的 px_size、相对现役的**记录增量**
  * 是否需要**重渲字形**（CW<16 或 CH<16）/ 是否改文本度量（advance）

另回答: 要 1868 格（1504 现役 + 364 缺字）到底哪些配置够。

用法: python tools/re/toolbelt/space_cap.py [--json OUT]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))

EN_BAND = (452, 468)                  # 现役盘 FT ASCII 记录 v0/v1（实测）
KB_BAND = (482, 498)                  # ★ large/default 键盘带 v0/v1（28 条记录, u∈[0,448)）—— 实测
ICON_WIN = (198, 222)                 # DrawString 硬编码图标 UV (1,198)-(21,218)/(25,198)-(45,218)
CUR = dict(W=1024, H=512, CW=16, CH=16, Y0=2, SKIP_ROW=12, SKIP_ROWS=3, NCOL=62)
CUR_PX = 0x40010                      # 现役 px_size (squeeze 口径, h=512, N=8)
CUR_REC = 1084 + CUR_PX               # 现役 new_font_revised 记录长 = 263244
NEED_NEW = 364                        # 用户缺字
NEED_NEW_3 = 367                      # + 3 个被吃的单字节汉字
NEED_CELLS = 1876                     # gate->0xB5 的净 pair 码位（口径对照用）
FREE_NOW = 46                         # ★ 现役真实空闲格实测 = 46（row24 尾）+ 34（row27 尾，作储备）
FREE_NOW_ROW27 = 34
NEED_PAIRS = 1876                     # gate->0xB5 的净码位数 (20*94-3-1)


def yrow(r, Y0, CH, SKIP_ROW, SKIP_ROWS):
    return Y0 + CH * (r + (SKIP_ROWS if r >= SKIP_ROW else 0))


def ev(H, CW, CH, Y0, SKIP_ROW, SKIP_ROWS, ncol, skip_en=True, en_band=EN_BAND,
       kb_band=KB_BAND):
    """skip_en=True: EN 带所在的整行不可用(与 r75 口径一致)
       kb_band      : ★ 键盘带所在的整行也不可用（r75/任务书漏了这一条，本轮实测补上）"""
    rows = []
    r = 0
    while True:
        y = yrow(r, Y0, CH, SKIP_ROW, SKIP_ROWS)
        if y + CH > H:
            break
        rows.append((r, y))
        r += 1
        if r > 500:
            break
    hole = (Y0 + CH * SKIP_ROW, Y0 + CH * (SKIP_ROW + SKIP_ROWS))
    covers_icon = (hole[0] <= ICON_WIN[0] and hole[1] >= ICON_WIN[1])
    blocked = []
    for (r, y) in rows:
        for band in ((en_band,) if not skip_en else (en_band, kb_band)):
            if not (y + CH <= band[0] or y >= band[1]):
                blocked.append(r)
                break
    blocked_set = set(blocked)
    usable = [(r, y) for (r, y) in rows if r not in blocked_set]
    N = (H + 63) // 64
    px_squeeze = 512 * H + 16
    px_addon = 512 * H + 48 * N + 16
    return dict(H=H, CW=CW, CH=CH, Y0=Y0, SKIP_ROW=SKIP_ROW, SKIP_ROWS=SKIP_ROWS, ncol=ncol,
                nrows=len(rows), hole=list(hole), covers_icon=covers_icon,
                en_blocked_rows=sorted(set(blocked)), usable_rows=len(usable),
                cells=len(usable) * ncol,
                free_cells=len(usable) * ncol - 1504,
                segs=N,
                px_squeeze='0x%X' % px_squeeze, px_addon='0x%X' % px_addon,
                d_squeeze=px_squeeze - CUR_PX, d_addon=px_addon - CUR_PX,
                record_squeeze=1084 + px_squeeze, record_addon=1084 + px_addon,
                max_x=ncol * CW, fits_W=ncol * CW <= CUR['W'],
                en_ok=(len(usable) * ncol - 1504) >= NEED_NEW_3,
                need_rerender=(CW < 16 or CH < 16),
                advance_change=CW != 16,
                lineheight_change=CH != 16,
                vram_kb=(256 if H <= 512 else 512))


def best_skip(H, CW, CH, Y0, ncol, skip_en=True):
    best = None
    for sr in range(1, 60):
        for sn in range(1, 8):
            hole = (Y0 + CH * sr, Y0 + CH * (sr + sn))
            if not (hole[0] <= ICON_WIN[0] and hole[1] >= ICON_WIN[1]):
                continue
            e = ev(H, CW, CH, Y0, sr, sn, ncol, skip_en)
            if best is None or e['cells'] > best['cells']:
                best = e
    return best


def r75_accounting(W, px_size):
    """r75 §4.1 的分块记账复算: B'=(0x10000/W)<<2; u=B'+16; c=ceil(P/u);
    +0x30 = P - 16c; npackets = ceil((P-16c)/B'); 交付 = (P-16c) + 16*npackets.
    返回 (B', c, plus30, npackets, delivered, slack, safe)  safe=False 表示落在
    (B', B'+16) 的危险窗口 (npackets = c-1, 少交 16 字节)。
    """
    Bp = (0x10000 // W) << 2
    u = Bp + 16
    c = -(-px_size // u)
    plus30 = px_size - 16 * c
    npk = -(-plus30 // Bp)
    delivered = plus30 + 16 * npk
    slack = c * u - px_size
    safe = not (Bp < slack < Bp + 16)
    return Bp, c, plus30, npk, delivered, slack, safe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                   'temp', 'r78', 'cap.json'))
    a = ap.parse_args()
    rep = dict(cur=CUR, cur_px='0x%X' % CUR_PX, cur_record=CUR_REC,
               need_cells=NEED_CELLS, need_pairs=NEED_PAIRS,
               en_band=list(EN_BAND), icon_win=list(ICON_WIN), rows=[])
    print('=== r75 §4.1 分块记账复算 (W=1024) ===')
    for H, px in ((512, 0x40010), (576, 0x481C0), (592, 0x4A1F0), (608, 0x4C1F0),
                  (640, 0x501F0), (1024, 0x80310)):
        Bp, c, p30, npk, dev, slack, safe = r75_accounting(1024, px)
        print('  H=%-4d px=0x%X  B\'=%-4d 包数=%-5d +0x30=%-8d 交付=%-8d ==px? %-5s '
              'slack=%-4d 安全=%s' %
              (H, px, Bp, c, p30, dev, dev == px, slack, safe))

    # 1) 现役常数下的现状确认
    base = ev(512, 16, 16, 2, 12, 3, 62)
    rep['baseline'] = base
    print('=== 基线确认 ===')
    print('  行数=%d 可用行=%d EN 挡行=%s 可用格=%d  (任务书给 1612)' %
          (base['nrows'], base['usable_rows'], base['en_blocked_rows'], base['cells']))

    # 2) 不改格距、只动跳行/列数（零字节）
    print('\n=== A. 零额外字节 / 不改格距 (CW=CH=16) ===')
    for ncol in (62, 63, 64):
        for H in (512, 544, 560, 576, 592, 608, 624, 640):
            b = best_skip(H, 16, 16, 2, ncol)
            if not b:
                continue
            b['ncol'] = ncol
            b['cells'] = b['usable_rows'] * ncol
            b['en_ok'] = b['cells'] >= NEED_CELLS
            rep['rows'].append(b)
            if H == 512 or b['en_ok']:
                print('  H=%-4d ncol=%d skip=%d+%d rows=%d usable=%d cells=%4d 够=%s '
                      'd_px(sq)=%-7d d_px(add)=%-7d' %
                      (H, ncol, b['SKIP_ROW'], b['SKIP_ROWS'], b['nrows'], b['usable_rows'],
                       b['cells'], b['en_ok'], b['d_squeeze'], b['d_addon']))

    # 3) 只加高（不动格距）= 无需重渲
    print('\n=== B1. 只加高贴图 + **其它常量一个都不改** (CW=CH=16, NCOL=62, Y0=2, SKIP=12+3) ===')
    for H in range(512, 1025, 16):
        b = ev(H, 16, 16, 2, 12, 3, 62)
        rep.setdefault('grow_fixed', []).append(b)
    for b in rep['grow_fixed']:
        print('  H=%-4d rows=%-3d EN挡=%s usable=%-3d cells=%4d 够=%-5s segs=%-2d '
              'px(sq)=%-8s px(add)=%-8s d(sq)=%-7d d(add)=%-7d' %
              (b['H'], b['nrows'], b['en_blocked_rows'], b['usable_rows'], b['cells'],
               b['en_ok'], b['segs'], b['px_squeeze'], b['px_addon'],
               b['d_squeeze'], b['d_addon']))

    print('\n=== B2. 加高 + **同时调 SKIP**（best_skip）===')
    for H in range(512, 1025, 16):
        b = best_skip(H, 16, 16, 2, 62)
        b['ncol'] = 62
        b['cells'] = b['usable_rows'] * 62
        b['en_ok'] = b['cells'] >= NEED_CELLS
        rep.setdefault('grow', []).append(b)
    for b in rep['grow']:
        if b['H'] in (512, 544, 560, 576, 592, 608, 624, 640, 704, 768, 832, 896, 960, 1024):
            print('  H=%-4d skip=%d+%d rows=%-3d usable=%-3d cells=%4d 够=%-5s segs=%-2d '
                  'd(sq)=%-7d d(add)=%-7d' %
                  (b['H'], b['SKIP_ROW'], b['SKIP_ROWS'], b['nrows'], b['usable_rows'],
                   b['cells'], b['en_ok'], b['segs'], b['d_squeeze'], b['d_addon']))

    # 4) 改格距（H=512 固定，零额外字节）
    print('\n=== C. 改格距 (H=512 不变) → 零额外字节，但要重渲字形 ===')
    for CW in (16, 15, 14, 13, 12):
        for CH in (16, 15, 14, 13, 12):
            ncol = 1024 // CW
            b = best_skip(512, CW, CH, 2, ncol)
            if not b:
                continue
            b['ncol'] = ncol
            b['cells'] = b['usable_rows'] * ncol
            b['en_ok'] = b['cells'] >= NEED_CELLS
            rep.setdefault('pitch', []).append(b)
    for b in sorted(rep['pitch'], key=lambda z: -z['cells']):
        if b['cells'] >= 1500:
            print('  CW=%-2d CH=%-2d ncol=%-3d skip=%d+%d rows=%d usable=%d cells=%4d 够=%s '
                  '重渲=%s 步进变=%s 行高变=%s' %
                  (b['CW'], b['CH'], b['ncol'], b['SKIP_ROW'], b['SKIP_ROWS'], b['nrows'],
                   b['usable_rows'], b['cells'], b['en_ok'], b['need_rerender'],
                   b['advance_change'], b['lineheight_change']))

    # 5) 加高 + 改列数（混合）
    print('\n=== D. 加高 + 列数放宽（CW=16 不变 → 步进宽不变；NCOL>62 要重排格位）===')
    for H in (512, 576, 640):
        for ncol in (62, 64):
            b = best_skip(H, 16, 16, 2, ncol)
            b['ncol'] = ncol
            b['cells'] = b['usable_rows'] * ncol
            b['en_ok'] = b['cells'] >= NEED_CELLS
            rep.setdefault('mix', []).append(b)
            print('  H=%-4d ncol=%d skip=%d+%d usable=%d cells=%4d 够=%s d(sq)=%d d(add)=%d' %
                  (H, ncol, b['SKIP_ROW'], b['SKIP_ROWS'], b['usable_rows'], b['cells'],
                   b['en_ok'], b['d_squeeze'], b['d_addon']))

    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    json.dump(rep, open(a.json, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('\n-> %s' % a.json)


main()
