# -*- coding: utf-8 -*-
r"""r57 标定: 「短串(=C 字符串)真文本 vs 二进制巧合」判据 —— 只读。

用**旧** charset 扫全盘, 但预筛换成"对偶码 LUT"(比 '≥4 连续高位字节' 精确得多),
于是能把 min_bytes 降到 4 (≥2 个汉字) 而不爆炸。

输出: work/builds/GR_ZH98/temp/r57/calib_r57.json —— 每个"含 ≥1 对偶码位置的无控制字节区间"里的
      ≥2 连续汉字段 + 判据特征。控制台只打汇总与通过各候选判据的段。
"""
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import numpy as np                                                     # noqa: E402
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
CS = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calib_r57.json')
CHUNK = 1 << 24
PAD = 4096

old = tcslib.Charset(CS)
new = tcslib.Charset()
iso = tcslib.Iso(ISO)
n = iso.size
print('ISO %s (%d B, sha %s)' % (ISO, n, tcslib.sha256_file(ISO)[:16]))

# ---- 旧码表的"对偶码" LUT: lut[(lead<<8)|trail] ----
lut = np.zeros(1 << 16, dtype=bool)
for (a, b) in old.pair_of:
    lut[(a << 8) | b] = True
print('旧 pair_of 条数 = %d' % len(old.pair_of))
# 单字节码集合 (这些字换码后**字节不变**)
print('旧 codes 条数 = %d' % len(old.codes))

containers = FC.enumerate_containers(iso)
regions = sorted((e['iso_off'], e['iso_off'] + e['stored'],
                  '%s#%d %s' % (t, i, e['name'])) for (t, _l, i, e) in containers)
print('容器 %d 个' % len(containers))


def in_img(off):
    lo, hi = 0, len(regions) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        a, b, _nm = regions[mid]
        if off < a:
            hi = mid - 1
        elif off >= b:
            lo = mid + 1
        else:
            return True
    return False


badlut = np.zeros(256, dtype=bool)
badlut[list(FC.BAD_TEXT_BYTES)] = True


def span_of(off):
    """off 所在的"无控制字节极大区间" (直接查 mmap, 不受分块影响)。"""
    s = off
    while s > 0 and not badlut[iso.mm[s - 1]]:
        s -= 1
    e = off
    while e < n and not badlut[iso.mm[e]]:
        e += 1
    return s, e


def cstr_of(off):
    """off 所在的、以 0x00 定界的 C 字符串 (不受控制字节限制)。"""
    s = off
    while s > 0 and iso.mm[s - 1] != 0:
        s -= 1
    e = off
    while e < n and iso.mm[e] != 0:
        e += 1
    return s, e


rows = []
t0 = time.time()
n_spans = n_runs = n_img = 0
pos = 0
while pos < n:
    end = min(n, pos + CHUNK)
    lo = max(0, pos - PAD)
    hi = min(n, end + PAD)
    buf = np.frombuffer(bytes(iso.mm[lo:hi]), dtype=np.uint8)
    m = buf.size
    pairpos = np.zeros(m, dtype=bool)
    if m >= 2:
        idx = (buf[:-1].astype(np.uint32) << 8) | buf[1:].astype(np.uint32)
        pairpos[:-1] = lut[idx]
    bad = badlut[buf]
    # 极大"无控制字节"区间 (buf 坐标)
    starts = np.concatenate(([0], np.flatnonzero(bad) + 1))
    ends = np.concatenate((np.flatnonzero(bad), [m]))
    csum = np.concatenate(([0], np.cumsum(pairpos, dtype=np.int64)))
    for s, e in zip(starts.tolist(), ends.tolist()):
        if e - s < 4 or csum[e] - csum[s] == 0:
            continue                                   # 无对偶码位置 ⇒ 换码后字节不变
        gs, ge = lo + s, lo + e
        if not (pos <= gs < end):
            continue                                   # 落在 padding 里 ⇒ 上一块已处理
        n_spans += 1
        seg = bytes(iso.mm[gs:ge])
        for h in FC.runs_in_span(seg, old, 2):
            off = gs + h['off']
            nb = h['nbytes']
            if in_img(off):
                n_img += 1
                continue
            n_runs += 1
            ss, se = span_of(off)
            cs0, ce = cstr_of(off)
            cstr = bytes(iso.mm[cs0:ce])
            units = FC.parse_units(cstr, old)
            consumed = units[-1][0] + units[-1][1] if units else 0
            rows.append(dict(
                off=off, nbytes=nb, text=h['text'], maxcjk=h['maxcjk'],
                pair_ratio=round(h['pair_ratio'], 3), span=[ss, se], span_len=se - ss,
                span_pre=iso.mm[ss - 1] if ss else None,
                span_post=iso.mm[se] if se < n else None,
                cstr=[cs0, ce], cstr_len=ce - cs0,
                cstr_clean=(consumed == len(cstr)),
                cstr_ctl=sum(1 for b in cstr if badlut[b]),
                cstr_ascii=sum(1 for b in cstr if 0x20 <= b <= 0x7E),
                span_ascii=sum(1 for b in bytes(iso.mm[ss:se]) if 0x20 <= b <= 0x7E),
                span_in_cstr=(ss >= cs0 and se <= ce),
                cstr_head=bytes(iso.mm[cs0:min(ce, cs0 + 40)]).hex(' '),
            ))
    pos = end
print('细扫(对偶码预筛) %.1fs: 候选区间 %d, IMG 之外 ≥2 汉字段 %d (IMG 内 %d)'
      % (time.time() - t0, n_spans, n_runs, n_img))

json.dump(rows, io.open(OUT, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
print('明细 → %s' % OUT)


def rule_a(r):
    """候选判据 A: span 两侧都是 0x00 + span 内有 ASCII 可打印字节 + span 干净解码."""
    return (r['span_pre'] == 0 and r['span_post'] == 0 and r['span_ascii'] >= 1)


def rule_b(r):
    """候选判据 B: C 字符串口径 (整条 NUL 串无控制字节 + 干净解码 + 含 ASCII 可打印)."""
    return (r['cstr_ctl'] == 0 and r['cstr_clean'] and r['cstr_ascii'] >= 1)


def rule_c(r):
    """候选判据 C: B + 串里至少有 1 个"对偶码"外的单字节汉字/ASCII (排除纯汉字巧合)."""
    return rule_b(r) and r['cstr_len'] >= r['nbytes'] + 1


for nm, fn in (('A', rule_a), ('B', rule_b), ('C', rule_c)):
    sel = [r for r in rows if fn(r)]
    print('\n判据 %s: 选中 %d 段' % (nm, len(sel)))
    for r in sel[:60]:
        print('   @0x%08X +%-3d %-14r pair=%.2f span=0x%X..0x%X(%d) cstr=%d ctl=%d asc=%d %s'
              % (r['off'], r['nbytes'], r['text'], r['pair_ratio'], r['span'][0], r['span'][1],
                 r['span_len'], r['cstr_len'], r['cstr_ctl'], r['cstr_ascii'],
                 r['cstr_head'][:66]))
    if len(sel) > 60:
        print('   … 还有 %d 段' % (len(sel) - 60))
iso.close()
