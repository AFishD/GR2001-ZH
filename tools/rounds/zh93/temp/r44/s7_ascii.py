# -*- coding: utf-8 -*-
r"""s7_ascii.py — 用盘上**自己的 FT 记录**判定: 引擎看到的图集是 flat(现役 dump 读法) 还是 payload(按封包还原)?

判据 (不需要 TTF, 也不需要任何本工程的约定):
  引擎画单字节/ASCII 时**直接用 FT 记录矩形 (u0,v0,u1,v1) 当 UV/采样窗** (这是盘上的数据,
  不是我们的推测; round64 起 EN 带就是按记录的 v=452 写进 seg7 的 payload 行的)。
  ⇒ 记录矩形里到底有没有墨, 两种读法只有一个成立。
"""
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
import dump_font                                                  # noqa: E402
import s3_recon as S3                                             # noqa: E402

LOG = []


def log(s):
    print(s)
    LOG.append(s)


def main():
    iso = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
    font = dump_font.load_font(iso)
    at = font['atlas']
    w, h = at['w'], at['h']
    stride = w // 2
    blob = at['pak'][at['px_off']:at['px_off'] + at['px_size']]
    payload, _segs, _m = S3.payload_from_packets(blob, w, h, stride=stride, fill=0x11)
    i_pay, i_dmp = S3.ink4(payload, w, h), S3.ink_gray(dump_font.atlas_gray(at), w, h)

    log('=' * 78)
    log('[法] 对每个 FT 记录矩形 (u0,v0,u1,v1): 数两种读法里矩形内的墨点数')
    for fi, (nm, fld, recs) in enumerate(font['faces']):
        if nm != 'default':
            continue
        n_pay = n_dmp = n_both_empty = n_bad = 0
        rows = []
        for code in range(0x21, 0x7F):
            r = recs[code - 0x20]
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            x1 = min(u1, w - 1)
            y1 = min(v1, h - 1)
            ip = int(i_pay[v0:y1, u0:x1].sum())
            idm = int(i_dmp[v0:y1, u0:x1].sum())
            rows.append((chr(code), u0, v0, u1, v1, ip, idm))
            if ip > 0:
                n_pay += 1
            if idm > 0:
                n_dmp += 1
            if ip == 0 and idm == 0:
                n_both_empty += 1
        log('[default] ASCII 0x21..0x7E 共 %d 条记录: 记录矩形内有墨 → payload 读法 %d 条 / flat 读法 %d 条'
            % (len(rows), n_pay, n_dmp))
        log('  前 20 条明细 (字, 记录矩形, payload 墨, flat 墨):')
        for r in rows[:20]:
            log('    %r rect=(%4d,%3d,%4d,%3d)  payload 墨=%-5d flat 墨=%-5d %s'
                % (r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                   '← payload 有墨' if r[5] > 0 and r[6] == 0 else ''))
        # 统计: payload 有墨而 flat 没墨的条数 (判据方向)
        only_pay = sum(1 for r in rows if r[5] > 0 and r[6] == 0)
        only_dmp = sum(1 for r in rows if r[6] > 0 and r[5] == 0)
        log('[default] **只有 payload 有墨** %d 条; **只有 flat 有墨** %d 条; 两边都空 %d 条'
            % (only_pay, only_dmp, n_both_empty))
        log('[default] ⇒ 结论: %s'
            % ('引擎口径 = payload (按 GIF 封包还原)' if only_pay > only_dmp and n_pay > n_dmp
               else ('引擎口径 = flat (现役 dump 读法)' if only_dmp > only_pay else '两边都不明显, 需再看')))
    with open(os.path.join(HERE, 's7_ascii.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
