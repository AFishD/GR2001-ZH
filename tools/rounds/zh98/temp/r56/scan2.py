# -*- coding: utf-8 -*-
r"""round56 侦察 ③: 优化版全盘"干净文本段"扫描 (只读)。

三件事:
  ① 用 numpy 找**无控制字节**的极大区间 (控制字节 = 0x00..0x08 / 0x0B..0x1F / 0x7F..0x9F);
  ② 只处理 (≥MINBYTES 且 含 ≥4 连续高位字节) 的区间 —— 真中文必然满足;
  ③ Python 用**引擎同款 greedy 解析**确认"干净 + ≥MINCJK 连续汉字"。
"""
import argparse
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402

LEAD_LO, LEAD_HI = tcslib.LEAD_LO, tcslib.LEAD_HI


def build_region_map(iso, limit=4096):
    regions = []
    lbas = {}
    for _rk, spec in tcslib.RES.items():
        for c in spec['copies']:
            lbas[c[0]] = c[1]
    for name, lba in sorted(lbas.items()):
        for idx in range(limit):
            try:
                e = iso.img_entry(lba, idx)
            except Exception:                                        # noqa: BLE001
                break
            if e['stored'] <= 0 or e['off'] <= 0:
                if idx == 0:
                    continue
                break
            regions.append((e['iso_off'], e['iso_off'] + e['stored'],
                            '%s#%d %s' % (name, idx, e['name'])))
    regions.sort()
    return regions


def who(regions, off):
    lo, hi = 0, len(regions) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        a, b, nm = regions[mid]
        if off < a:
            hi = mid - 1
        elif off >= b:
            lo = mid + 1
        else:
            return nm
    return '(IMG 之外 / 未归属)'


def clean_runs(buf, cs, min_cjk=4, want_text=True):
    """引擎同款 greedy 解析: 找"干净"子段 (无未映射回落字节) 且 ≥min_cjk 连续汉字。"""
    out = []
    n = len(buf)
    pair_of, codes = cs.pair_of, cs.codes
    i = 0
    while i < n:
        start = i
        chars = []
        while i < n:
            v = buf[i]
            if v < 0x80:
                chars.append(chr(v)); i += 1
            elif LEAD_LO <= v < LEAD_HI and i + 1 < n and (v, buf[i + 1]) in pair_of:
                chars.append(pair_of[(v, buf[i + 1])]); i += 2
            elif v in codes:
                chars.append(codes[v]); i += 1
            else:
                break
        if chars:
            text = ''.join(chars)
            best = cur = 0
            for ch in text:
                if '\u4e00' <= ch <= '\u9fff':
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 0
            if best >= min_cjk:
                out.append((start, i, text, best))
        if i == start:
            i += 1
    return out


def scan_iso(iso, cs, min_cjk=4, minbytes=16, chunk=1 << 24, runhi=4, verbose=True):
    badlut = np.ones(256, dtype=bool)
    for v in (9, 10, 13):
        badlut[v] = False
    badlut[0x20:0x7F] = False
    badlut[0xA0:0x100] = False          # ★ 高位字节 (汉字/对偶码) 一律"可能是文本"
    badlut[0x80:0xA0] = True            # C1 控制区 = 肯定不是文本
    hits = []
    n = iso.size
    off = 0
    t0 = time.time()
    nspan = nproc = 0
    while off < n:
        end = min(n, off + chunk)
        buf = bytes(iso.mm[off:end])
        arr = np.frombuffer(buf, dtype=np.uint8)
        good = ~badlut[arr]
        bad = np.flatnonzero(~good)
        hi = arr >= 0x80
        # ≥runhi 连续高位字节的起点
        rfull = hi.copy() if runhi <= 1 else np.zeros(len(arr), dtype=bool)
        if runhi > 1:
            r = hi[:-runhi + 1].copy()
            for k in range(1, runhi):
                r &= hi[k:len(hi) - runhi + 1 + k]
            rfull[:len(r)] = r
        csum = np.concatenate(([0], np.cumsum(rfull, dtype=np.int64)))
        # 区间 = 相邻 bad 之间 (含首尾)
        starts = np.concatenate(([0], bad + 1))
        ends = np.concatenate((bad, [len(arr)]))
        for s, e in zip(starts.tolist(), ends.tolist()):
            if e - s < minbytes:
                continue
            nspan += 1
            if csum[e] - csum[s] <= 0:
                continue
            nproc += 1
            for (r0, r1, text, best) in clean_runs(buf[s:e], cs, min_cjk):
                hits.append(dict(off=off + s + r0, nbytes=r1 - r0, text=text, maxcjk=best))
        off = end
    if verbose:
        print('  扫描 %.1fs: 候选区间 %d, 真解析 %d' % (time.time() - t0, nspan, nproc))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--charset', default=None)
    ap.add_argument('--json', default=None)
    ap.add_argument('--min-cjk', type=int, default=4)
    ap.add_argument('--minbytes', type=int, default=16)
    ap.add_argument('--runhi', type=int, default=4)
    a = ap.parse_args()
    cs = tcslib.Charset(a.charset) if a.charset else tcslib.Charset()
    iso = tcslib.Iso(a.iso)
    print('ISO %s  %.2f GB' % (a.iso, iso.size / 1e9))
    regions = build_region_map(iso)
    print('容器区间表 %d 条' % len(regions))
    hits = scan_iso(iso, cs, a.min_cjk, a.minbytes, runhi=a.runhi)
    iso.close()
    by = {}
    for h in hits:
        nm = who(regions, h['off'])
        by.setdefault(nm, []).append(h)
    print('干净文本段 (≥%d 连续汉字): **%d 段**, 落在 %d 个容器' % (a.min_cjk, len(hits), len(by)))
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1]))[:30]:
        mx = max(x['maxcjk'] for x in v)
        print('   %-34s %6d 段 (最长汉字串 %d) 例: %r'
              % (k, len(v), mx, v[0]['text'][:44]))
    doc = dict(iso=os.path.basename(a.iso), min_cjk=a.min_cjk, minbytes=a.minbytes,
               runs=len(hits), containers=len(by),
               by_container=dict((k, len(v)) for k, v in by.items()),
               hits=[dict(off=h['off'], nbytes=h['nbytes'], maxcjk=h['maxcjk'],
                          text=h['text'][:200], container=who(regions, h['off'])) for h in hits])
    if a.json:
        io.open(a.json, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % a.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
