# -*- coding: utf-8 -*-
r"""analyze_memdrift.py — EE/IOP RAM 定时快照的**累积漂移**比对 (只读)

输入: 两次回放的 <out>/period_f%08u_{eeram,iopram}.bin (每 2500 帧一份)
输出: 
  [1] 漂移曲线: 每对相邻样本之间"有多少字节变了" (ZH vs EN)
  [2] **只在汉化盘上出现的累积性变化**: 逐 32-bit 字统计 "在多少对相邻样本之间变过",
      取 ZH 变过 >= K 次而 EN **一次都没变** 的字 ⇒ 这些就是"汉化引入且随时间累积"的位置
  [3] 结构指针 → 0 / 野值: 首样本非 0、末样本为 0 的字 (EN 同址不变者优先)
  [4] malloc_state (VA 0x0055B7A0) 的逐样本解码表 —— 崩溃前 heap 的实时状态

用法:
  python analyze_memdrift.py --zh <dir> [--en <dir>] [--lo 0x100000] [--hi 0x64BE80] [--k 3]
"""
import argparse
import glob
import json
import os
import re
import struct
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
EE = 32 * 1024 * 1024
IOP = 2 * 1024 * 1024
OUT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_MEMDRIFT'


def samples(d, kind='eeram'):
    out = []
    for p in glob.glob(os.path.join(d, 'period_f*_%s.bin' % kind)):
        m = re.search(r'period_f(\d+)_', os.path.basename(p))
        if m:
            out.append((int(m.group(1)), p))
    out.sort()
    return out


def scan(ss, lo, hi, chunk=1 << 22):
    """→ (frames, chg[uint8 每字"变过的相邻对数"], first[uint32], last[uint32], nbytes_pair[])"""
    nw = (hi - lo) // 4
    chg = np.zeros(nw, dtype=np.uint16)
    first = np.zeros(nw, dtype=np.uint32)
    last = np.zeros(nw, dtype=np.uint32)
    pair_changed = []
    prev = None
    frames = [f for (f, _p) in ss]
    for k, (f, p) in enumerate(ss):
        mm = np.memmap(p, dtype=np.uint8, mode='r', offset=lo, shape=(hi - lo,))
        cur = np.frombuffer(np.asarray(mm), dtype='<u4').copy()
        del mm
        if prev is not None:
            neq = (cur != prev)
            chg += neq
            pair_changed.append(int(neq.sum()))
        else:
            first[:] = cur
            pair_changed.append(0)
        last[:] = cur
        prev = cur
    return frames, chg, first, last, pair_changed


def malloc_state_table(d, va=0x0055B7A0):
    ss = samples(d)
    rows = []
    for (f, p) in ss:
        with open(p, 'rb') as fh:
            fh.seek(va)
            b = fh.read(0x40)
        if len(b) < 0x40:
            continue
        u = struct.unpack_from('<16I', b, 0)
        rows.append(dict(frame=f, smallmap='%08X' % u[0], treemap='%08X' % u[1],
                         dvsize='%08X' % u[2], topsize='%08X' % u[3],
                         least_addr='%08X' % u[4], dv='%08X' % u[5], top='%08X' % u[6],
                         trim_check='%08X' % u[7],
                         tree0_fd='%08X' % u[10], tree0_bk='%08X' % u[11],
                         tree1_fd='%08X' % u[12], tree1_bk='%08X' % u[13]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zh', required=True)
    ap.add_argument('--en', default=None)
    ap.add_argument('--lo', default='0x100000')
    ap.add_argument('--hi', default='0x64BE80')
    ap.add_argument('--k', type=int, default=3, help='ZH 至少变过几对才报')
    ap.add_argument('--topn', type=int, default=40)
    ap.add_argument('--out', default=os.path.join(OUT, 'drift.json'))
    a = ap.parse_args()
    lo, hi = int(a.lo, 0), int(a.hi, 0)

    zs = samples(a.zh)
    print('ZH 快照 %d 份: frames %s' % (len(zs), [f for (f, _) in zs]))
    if not zs:
        sys.exit('没有 ZH 快照')
    zf, zc, zfirst, zlast, zpair = scan(zs, lo, hi)
    print('\n[1] ZH 漂移曲线 (相邻样本间变化字节数, 区域 0x%X..0x%X):' % (lo, hi))
    for i in range(1, len(zf)):
        print('    f%-8d -> f%-8d : %10d B 变化' % (zf[i - 1], zf[i], zpair[i]))

    ef = ec = efirst = elast = epair = None
    if a.en:
        es = samples(a.en)
        print('\nEN 快照 %d 份: frames %s' % (len(es), [f for (f, _) in es]))
        if es:
            # ★ 必须**对齐到共同帧**: 否则 ZH 的 11 对 vs EN 的 3 对, "ZH 变过而 EN 没变"
            #   只是样本数不同造成的假阳性。
            common = sorted(set(f for (f, _) in zs) & set(f for (f, _) in es))
            if len(common) < len(zs):
                print('  ★ 对齐到共同帧 %s (ZH %d 份 / EN %d 份 ⇒ 各自重采)'
                      % (common, len(zs), len(es)))
                zs = [(f, p) for (f, p) in zs if f in set(common)]
                es = [(f, p) for (f, p) in es if f in set(common)]
                zf, zc, zfirst, zlast, zpair = scan(zs, lo, hi)
                print('  [1] ZH 漂移曲线 (对齐后):')
                for i in range(1, len(zf)):
                    print('    f%-8d -> f%-8d : %10d B 变化' % (zf[i - 1], zf[i], zpair[i]))
            ef, ec, efirst, elast, epair = scan(es, lo, hi)
            print('[1] EN 漂移曲线:')
            for i in range(1, len(ef)):
                print('    f%-8d -> f%-8d : %10d B 变化' % (ef[i - 1], ef[i], epair[i]))

    # ---- [2] ZH-only 累积变化 ----
    idx = np.arange((hi - lo) // 4)
    mask = (zc >= a.k)
    if ec is not None:
        mask &= (ec == 0)
    hits = idx[mask]
    print('\n[2] **只在汉化盘上变化**的 32-bit 字: ZH 变过 >= %d 对, %s'
          % (a.k, 'EN 一次未变' if ec is not None else '(未给 EN, 只按 ZH 频次筛)'))
    print('    命中 %d 个字 (区域 0x%X..0x%X)' % (len(hits), lo, hi))
    # 按变化次数降序
    order = hits[np.argsort(-zc[hits])]
    shown = []
    for w in order[:a.topn]:
        va = lo + int(w) * 4
        rec = dict(va='0x%08X' % va, chg_zh=int(zc[w]),
                   chg_en=(int(ec[w]) if ec is not None else None),
                   first_zh='0x%08X' % int(zfirst[w]), last_zh='0x%08X' % int(zlast[w]))
        if ec is not None:
            rec['first_en'] = '0x%08X' % int(efirst[w])
            rec['last_en'] = '0x%08X' % int(elast[w])
        shown.append(rec)
        print('    0x%08X  ZH 变 %2d/%-2d 次  %08X -> %08X%s'
              % (va, int(zc[w]), len(zf) - 1, int(zfirst[w]), int(zlast[w]),
                 ('   EN %08X -> %08X (变 %d)' % (int(efirst[w]), int(elast[w]), int(ec[w])))
                 if ec is not None else ''))

    # ---- [3] 结构指针 -> 0 ----
    zero = idx[(zfirst != 0) & (zlast == 0)]
    if ec is not None:
        zero = zero[(efirst[zero] != 0) & (elast[zero] == 0)]
    print('\n[3] 首样本非 0、末样本为 0 的字 (结构指针被清零): %d 个' % len(zero))
    zo = []
    for w in zero[:a.topn]:
        va = lo + int(w) * 4
        zo.append(dict(va='0x%08X' % va, first='0x%08X' % int(zfirst[w]),
                       last='0x%08X' % int(zlast[w]), chg_zh=int(zc[w])))
        print('    0x%08X  %08X -> 00000000  (ZH 变 %d 次)' % (va, int(zfirst[w]), int(zc[w])))

    # ---- [4] malloc_state ----
    print('\n[4] malloc_state @ VA 0x0055B7A0 (反汇编 lui 0x56; addiu -18528)')
    ms_zh = malloc_state_table(a.zh)
    hdr = ('frame', 'smallmap', 'treemap', 'dvsize', 'topsize', 'least', 'dv', 'top',
           'tree0_fd', 'tree0_bk')
    print('    %-7s %-9s %-9s %-9s %-9s %-9s %-9s %-9s %-9s %-9s' % hdr)
    for r in ms_zh:
        print('    %-7d %-9s %-9s %-9s %-9s %-9s %-9s %-9s %-9s %-9s'
              % (r['frame'], r['smallmap'], r['treemap'], r['dvsize'], r['topsize'],
                 r['least_addr'], r['dv'], r['top'], r['tree0_fd'], r['tree0_bk']))
    ms_en = malloc_state_table(a.en) if a.en else []

    res = dict(zh=a.zh, en=a.en, lo='0x%X' % lo, hi='0x%X' % hi, k=a.k,
               zh_frames=zf, zh_pair_changed=zpair,
               en_frames=ef, en_pair_changed=epair,
               zh_only_drift=shown, ptr_to_zero=zo,
               malloc_state_zh=ms_zh, malloc_state_en=ms_en)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print('\n写出 %s' % a.out)


if __name__ == '__main__':
    main()
