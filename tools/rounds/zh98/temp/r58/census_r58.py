# -*- coding: utf-8 -*-
r"""r58 普查 v2 (只读; 优化版): 全盘 4690 个容器, 找**哪里的文本会因码表代际不同而变味**。

三代:
  G0 = round46 第一次紧凑重排之前 (work/builds/GR_ZH94/temp/r46/charset_before_repack.json)
  G1 = round46 之后 .. round56 之前 (work/builds/GR_ZH98/temp/r56/charset_before_r56.json)
  G2 = 现役 (tools/font_pipeline/data/charset_compiled_zh16.json)

逐容器:
  ① numpy 预筛: 该容器里有没有"**换代后会变的对偶码**"位置 (没有任何一个 ⇒ 换码也改不动它, 直接判 0);
  ② 有 ⇒ 三代各解一遍, 统计 >=2 连续汉字的段 (以及其中含对偶码的段);
  ③ "只重映射这些段" 与 "整容器逐字重映射" 各改多少字节 (G0→G2 / G1→G2)。
输出 census_r58.json / census_r58.log。
"""
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import numpy as np                                                     # noqa: E402
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')
CS = dict(
    G0=os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46',
                    'charset_before_repack.json'),
    G1=os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json'),
    G2=os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json'))
MAX_BLOB = 4 << 20
CH = dict((k, tcslib.Charset(v)) for k, v in CS.items())
CJK = lambda c: '\u4e00' <= c <= '\u9fff'


def changed_pair_lut(src, dst):
    """换代后会**变**的对偶码 (字节对) 查找表 —— numpy 预筛用。"""
    lut = np.zeros(1 << 16, dtype=bool)
    n = 0
    for p, ch in src.pair_of.items():
        if dst.pair_of.get(p) != ch:
            lut[(p[0] << 8) | p[1]] = True
            n += 1
    return lut, n


LUT = dict((g, changed_pair_lut(CH[g], CH['G2'])) for g in ('G0', 'G1'))


def has_changed_pair(buf, lut):
    a = np.frombuffer(buf, dtype=np.uint8)
    if a.size < 2:
        return 0
    idx = (a[:-1].astype(np.uint32) << 8) | a[1:].astype(np.uint32)
    return int(lut[idx].sum())


def runs_of(text, mp, n, min_cjk=2):
    out, cur = [], []
    for i, ch in enumerate(text):
        if CJK(ch):
            cur.append(i)
            continue
        if len(cur) >= min_cjk:
            out.append(cur)
        cur = []
    if len(cur) >= min_cjk:
        out.append(cur)
    res = []
    for idxs in out:
        a, b = idxs[0], idxs[-1] + 1
        lo = mp[a]
        hi = mp[b] if b < len(mp) else n
        n_pair = sum(1 for i in idxs if (mp[i + 1] if i + 1 < len(mp) else n) - mp[i] == 2)
        res.append((lo, hi, n_pair))
    return res


def remap_bytes(blob, src, dst, spans=None):
    """src 解 → dst 编; spans 给定时只改落在其中的字符 (spans 已排序, 指针推进)。"""
    t, mp = src.decode(blob)
    n = len(blob)
    out = bytearray(blob)
    nchg = nfail = nlen = 0
    si = 0
    nspans = len(spans) if spans is not None else 0
    for i, ch in enumerate(t):
        a = mp[i]
        b = mp[i + 1] if i + 1 < len(t) else n
        if spans is not None:
            while si < nspans and spans[si][1] <= a:
                si += 1
            if si >= nspans or not (spans[si][0] <= a < spans[si][1]):
                continue
        try:
            nb = dst.encode_strict(ch)
        except tcslib.CharsetError:
            nfail += 1
            continue
        if len(nb) != b - a:
            nlen += 1
            continue
        if nb != blob[a:b]:
            out[a:b] = nb
            nchg += len(nb)
    return nchg, nfail, nlen


def main():
    t0 = time.time()
    iso = tcslib.Iso(ISO)
    containers = FC.enumerate_containers(iso)
    print('容器 %d 个; 换代后可变的对偶码: %s; 展开态 > %d MB 的容器按"媒体数据"排除'
          % (len(containers), ', '.join('%s→G2 %d 个' % (g, LUT[g][1]) for g in ('G0', 'G1')),
             MAX_BLOB // (1 << 20)))
    rows, skipped, n_decoded, big = [], 0, 0, []
    for k, (tag, lba, idx, e) in enumerate(containers):
        key = '%s#%d %s' % (tag, idx, e['name'])
        try:
            blob = FC.Slot(iso, tag, lba, idx).blob
        except Exception as ex:                                        # noqa: BLE001
            print('  [!!] %s 解不开: %s' % (key, ex))
            continue
        if not blob:
            continue
        if len(blob) > MAX_BLOB:
            # 巨型媒体容器 (PSS/SS/BMZ/MIS...): 里面的"汉字"是压缩/像素数据里的巧合, 而逐代解码
            # 一个 100 MB 容器要几十分钟 ⇒ 按**展开态大小**排除 (只记账; 普查表那 117 个含中文
            # 容器里没有一个超过 200 KB)
            big.append(dict(container=key, blob=len(blob)))
            continue
        hit0 = has_changed_pair(blob, LUT['G0'][0])
        hit1 = has_changed_pair(blob, LUT['G1'][0])
        if not hit0 and not hit1:
            skipped += 1
            continue
        n_decoded += 1
        rec = dict(container=key, tag=tag, idx=idx, name=e['name'], blob=len(blob),
                   changed_pair_hits=dict(G0=hit0, G1=hit1), gen={})
        for g in ('G0', 'G1', 'G2'):
            t, mp = CH[g].decode(blob)
            rr = runs_of(t, mp, len(blob))
            rec['gen'][g] = dict(n_cjk=sum(1 for c in t if CJK(c)), runs=len(rr),
                                 pair_runs=sum(1 for x in rr if x[2] > 0),
                                 max_run=max([b - a for (a, b, _p) in rr] or [0]),
                                 cjk_text=''.join(c for c in t if CJK(c))[:80])
            if g != 'G2' and rr:
                spans = [(a, b) for (a, b, p) in rr if p > 0]
                d_runs = remap_bytes(blob, CH[g], CH['G2'], spans) if spans else (0, 0, 0)
                rec['gen'][g]['delta_runs_bytes'] = d_runs[0]
                rec['gen'][g]['delta_runs_fail'] = d_runs[1]
            elif g != 'G2':
                rec['gen'][g]['delta_runs_bytes'] = 0
                rec['gen'][g]['delta_runs_fail'] = 0
        if rec['gen']['G0']['delta_runs_bytes'] or rec['gen']['G1']['delta_runs_bytes']:
            rec['gen']['G0']['delta_all_bytes'] = remap_bytes(blob, CH['G0'], CH['G2'])[0]
            rec['gen']['G1']['delta_all_bytes'] = remap_bytes(blob, CH['G1'], CH['G2'])[0]
            rows.append(rec)
        if (k + 1) % 500 == 0:
            print('   ... %d/%d 容器; 需要解码 %d, 其中"段口径会变" %d; %.0fs'
                  % (k + 1, len(containers), n_decoded, len(rows), time.time() - t0))
    iso.close()
    rows.sort(key=lambda r: -(r['gen']['G0']['delta_runs_bytes']
                              + r['gen']['G1']['delta_runs_bytes']))
    doc = dict(iso=ISO, iso_sha256=tcslib.sha256_file(ISO), charsets=CS,
               containers_scanned=len(containers), containers_skipped_no_changed_pair=skipped,
               containers_skipped_oversize=len(big), max_blob=MAX_BLOB,
               oversize_sample=sorted(big, key=lambda x: -x['blob'])[:40],
               containers_decoded=n_decoded, containers_segment_delta=len(rows),
               seconds=round(time.time() - t0, 1), rows=rows)
    io.open(os.path.join(HERE, 'census_r58.json'), 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print('\n=== "≥2 连续汉字段换码后会变"的容器 %d 个 (按段口径改动字节降序) ===' % len(rows))
    print('%-38s %9s | %-28s | %-28s' % ('container', 'blob', 'G0→G2 段/全', 'G1→G2 段/全'))
    for r in rows:
        g0, g1 = r['gen']['G0'], r['gen']['G1']
        print('%-38s %9d | %6d B /%7s | %6d B /%7s  段 %d/%d'
              % (r['container'], r['blob'], g0['delta_runs_bytes'],
                 g0.get('delta_all_bytes'), g1['delta_runs_bytes'], g1.get('delta_all_bytes'),
                 g0['pair_runs'], g1['pair_runs']))
    print('跳过 (无"换代会变的对偶码") %d 个; 总耗时 %.0fs' % (skipped, time.time() - t0))


if __name__ == '__main__':
    main()
