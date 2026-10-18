# -*- coding: utf-8 -*-
r"""s4_copies.py (round44 实验) — 两条收尾核对:
  A. 字节级: 逐行确认 "flat(dump) 行 = payload 行 右移 48*(k+1) 字节" (k = 段号), 不靠字形匹配;
  B. 字形级: 对若干对偶字列出**全部**低误差命中位置 ⇒ 引擎格(payload 16*col)上到底有没有字形。
只读。
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

import numpy as np                                                # noqa: E402
import tcslib                                                     # noqa: E402
import dump_font                                                  # noqa: E402
import s3_recon as S3                                             # noqa: E402  (复用封包解析/模板)

LOG = []


def log(s):
    print(s)
    LOG.append(s)


def all_matches(inkimg, tpl, thresh=2, maxn=40):
    """模板的全部低误差位置 (不做 top-k 截断), 返回 [(err, y, x), ...]。"""
    H, W = inkimg.shape
    th, tw = tpl.shape
    oh, ow = H - th + 1, W - tw + 1
    f = inkimg.astype(np.int32)
    C = np.zeros((oh, ow), np.int32)
    for i in range(th):
        for j in range(tw):
            if tpl[i, j]:
                C += f[i:i + oh, j:j + ow]
    ii = np.zeros((H + 1, W + 1), np.int32)
    ii[1:, 1:] = np.cumsum(np.cumsum(f, 0), 1)
    Sm = ii[th:, tw:] - ii[:-th, tw:] - ii[th:, :-tw] + ii[:-th, :-tw]
    mism = int(tpl.sum()) + Sm - 2 * C
    ys, xs = np.where(mism <= thresh)
    out = sorted(((int(mism[y, x]), int(y), int(x)) for y, x in zip(ys, xs)))
    return out[:maxn], int((mism <= thresh).sum())


def main():
    iso = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
    font = dump_font.load_font(iso)
    at = font['atlas']
    w, h = at['w'], at['h']
    stride = w // 2
    blob = at['pak'][at['px_off']:at['px_off'] + at['px_size']]
    payload, segs, _meta = S3.payload_from_packets(blob, w, h, stride=stride, fill=0x11)
    i_pay = S3.ink4(payload, w, h)
    i_dmp = S3.ink_gray(dump_font.atlas_gray(at), w, h)

    # ── A. 逐行字节级位移 ──
    log('=' * 78)
    log('[A] 逐行字节级核对: flat(dump) 行 vs payload 行 的最小差异循环位移')
    log('    y   段号  实测位移(texel)  预期 96*(k+1)  该行差异(texel)')
    bad = 0
    for y in list(range(0, 20)) + list(range(60, 70)) + list(range(126, 132)) + \
            list(range(190, 196)) + list(range(254, 260)) + list(range(318, 324)) + \
            list(range(382, 388)) + list(range(446, 452)):
        if y >= h:
            continue
        a = i_pay[y].astype(np.int16)
        b = i_dmp[y].astype(np.int16)
        best, bs = None, None
        for s in range(0, w, 16):
            d = int(np.abs(np.roll(a, s) - b).sum())
            if best is None or d < best:
                best, bs = d, s
        k = min(y // 64, 7)
        exp = 96 * (k + 1)
        ok = (bs == exp) and best == 0
        bad += 0 if ok else 1
        log('  %4d %5d %14d %14d %13d %s' % (y, k, bs, exp, best, 'OK' if ok else '**不一致**'))
    log('[A] 结论: %s' % ('全部行位移 = 96*(段号+1) texel, 差异 0 ⇒ flat 视图就是"每段右移 6 格"的错位图'
                          if bad == 0 else '有 %d 行不符合' % bad))

    # ── B. 字形副本位置 ──
    log('=' * 78)
    log('[B] 若干对偶字在 payload(引擎口径) 里的**全部**低误差命中 (err<=2), 位置以"格"表示:')
    cs = tcslib.Charset()
    want = ['区', '显', '纵', '米', '俊', '螺', '贡', '欧', '袁', '虽', '衍', '衣', '裂', '誉',
            '轮', '迟', '造', '钢', '题', '额', '鼓', '荐']
    report = []
    for ch in want:
        p = cs.enc_pair.get(ch)
        if not p:
            log('  %s: 不在 charset 的 pair 里' % ch)
            continue
        slot = tcslib.pair_slot(*p)
        row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
        tpl = S3.render16(ch)
        if not tpl.any():
            log('  %s: TTF 无字形, 跳过' % ch)
            continue
        hits, n = all_matches(i_pay, tpl, thresh=2, maxn=12)
        cells = ['(col%+d,row%+d,y%+d)' % (x // 16 - col, y // 16 - row, y - (2 + 16 * (row + (3 if row >= 12 else 0))))
                 for (_e, y, x) in hits]
        engine_cell_hit = any(x == 16 * col and y == 2 + 16 * (row + (3 if row >= 12 else 0))
                              for (_e, y, x) in hits)
        report.append(dict(char=ch, slot=slot, row=row, col=col, n_hits=n,
                           engine_cell_hit=engine_cell_hit,
                           hits=[dict(err=e, y=y, x=x) for (e, y, x) in hits]))
        log('  %s slot=%4d row=%2d col=%2d | payload 命中 %2d 处 | 引擎格(16*col=%4d) 有字形: %s'
            % (ch, slot, row, col, n, 16 * col, '✓' if engine_cell_hit else '**没有**'))
        log('        前几个: %s' % ', '.join('err=%d @%s' % (h[0], c) for h, c in zip(hits[:6], cells[:6])))
    need = [r for r in report if not r['engine_cell_hit']]
    log('[B] 引擎格(payload 16*col)没有字形的字: %d / %d 个: %s'
        % (len(need), len(report), ' '.join(r['char'] for r in need)))
    with io.open(os.path.join(HERE, 's4_copies.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(row_shift_ok=(bad == 0), glyphs=report), f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(HERE, 's4_copies.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
