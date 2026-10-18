# -*- coding: utf-8 -*-
r"""round56 侦察 ②: 全盘"干净文本段"扫描 (只读)。

与 repack_leak_scan 的粗口径 (高位字节聚簇 + ≥4 连续汉字) 不同, 这里用**干净解析**口径:
段内每个字节都能被**旧 charset** 解出来 (ASCII / 单字节码 / 合法对偶), 一个"未映射回落字节"
都没有 —— 这样才是"真文本", 而不是二进制垃圾的巧合。

用法: python scan_text_runs.py <iso> [--charset X.json] [--json out.json]
"""
import argparse
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402

LEAD_LO, LEAD_HI = tcslib.LEAD_LO, tcslib.LEAD_HI


def build_region_map(iso, limit=4096):
    """ISO 偏移 → 容器名 的区间表 (两个 IMG 的全部条目 + 独立文件)。"""
    regions = []
    lbas = {}
    for _rk, spec in tcslib.RES.items():
        for c in spec['copies']:
            lbas[c[0]] = c[1]
    # 再补上 ISO 里其它 IMG (PVD 里能找到目录记录; 这里只扫已知两个 + 常见文件)
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


def clean_runs(buf, cs):
    """在 buf 里找"干净可解"的极大子段 (greedy, 与引擎同规则)。

    返回 [(start, end, text)]; 段内无未映射回落字节。
    """
    out = []
    n = len(buf)
    i = 0
    pair_of, codes = cs.pair_of, cs.codes
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
        if chars and i - start >= 8:
            out.append((start, i, ''.join(chars)))
        if i == start:
            i += 1
    return out


def cjk_best(text):
    """最长连续汉字数。"""
    best = cur = 0
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--charset', default=None)
    ap.add_argument('--json', default=None)
    ap.add_argument('--min-cjk', type=int, default=4)
    ap.add_argument('--minbytes', type=int, default=8)
    ap.add_argument('--chunk', type=int, default=1 << 24)
    a = ap.parse_args()

    cs = tcslib.Charset(a.charset) if a.charset else tcslib.Charset()
    iso = tcslib.Iso(a.iso)
    print('ISO %s  %.2f GB' % (a.iso, iso.size / 1e9))
    regions = build_region_map(iso)
    print('容器区间表 %d 条' % len(regions))

    hits = []
    n = iso.size
    off = 0
    # 「肯定不是文本」的字节: 控制字符 (除 \t\n\r) / C1 控制区
    badlut = np.ones(256, dtype=bool)
    for v in (9, 10, 13):
        badlut[v] = False
    badlut[0x20:0x7F] = False
    badlut[0x80:0xA0] = True
    while off < n:
        end = min(n, off + a.chunk)
        buf = bytes(iso.mm[off:end])
        arr = np.frombuffer(buf, dtype=np.uint8)
        good = ~badlut[arr]
        if good.any():
            idx = np.flatnonzero(good)
            groups = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
            for g in groups:
                if len(g) < a.minbytes:
                    continue
                s0, s1 = int(g[0]), int(g[-1]) + 1
                seg = buf[s0:s1]
                for (r0, r1, text) in clean_runs(seg, cs):
                    if cjk_best(text) >= a.min_cjk:
                        hits.append(dict(off=off + s0 + r0, nbytes=r1 - r0,
                                         text=text, maxcjk=cjk_best(text)))
        off = end
    iso.close()

    by = {}
    for h in hits:
        nm = who(regions, h['off'])
        by.setdefault(nm.split(' ')[0], []).append(h)
    print('干净文本段 (无回落字节 + ≥%d 连续汉字): **%d 段**' % (a.min_cjk, len(hits)))
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print('   %-28s %6d 段   例: %s' % (k, len(v), v[0]['text'][:50].replace('\n', '\\n')))
    doc = dict(iso=os.path.basename(a.iso), min_cjk=a.min_cjk, runs=len(hits),
               by_container=dict((k, len(v)) for k, v in by.items()),
               hits=[dict(off=h['off'], nbytes=h['nbytes'], text=h['text'][:200],
                          container=who(regions, h['off'])) for h in hits])
    if a.json:
        io.open(a.json, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % a.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
