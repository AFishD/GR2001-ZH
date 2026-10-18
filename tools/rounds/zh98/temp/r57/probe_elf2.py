# -*- coding: utf-8 -*-
r"""r57 探针: ELF (LBA295) 里"≥2 连续汉字"的段全清单 + 判据标定 (只读)。

用法: python work/builds/GR_ZH98/temp/r57/probe_elf2.py [iso路径] [charset路径]
"""
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

ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'work', 'builds', 'GR_ZH105',
                                                         'GR_ZH105.iso')
CS = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                        'temp', 'r56', 'charset_before_r56.json')

old = tcslib.Charset(CS)
new = tcslib.Charset()
iso = tcslib.Iso(ISO)
print('ISO   : %s' % ISO)
print('charset: %s' % CS)
print('ISO sha256: %s' % tcslib.sha256_file(ISO))

# ---- ELF 范围: 用 ELF 头自己算 ----
ELF_OFF = 295 * tcslib.SEC
hdr = bytes(iso.mm[ELF_OFF:ELF_OFF + 64])
print('\nELF @%d magic=%r class=%d data=%d' % (ELF_OFF, hdr[:4], hdr[4], hdr[5]))
# e_shoff(0x20) e_shentsize(0x2E) e_shnum(0x30) e_phoff(0x1C) e_phentsize(0x2A) e_phnum(0x2C)
import struct                                                          # noqa: E402
e_phoff, e_shoff = struct.unpack_from('<II', hdr, 0x1C)
e_phentsize, e_phnum, e_shentsize, e_shnum = struct.unpack_from('<HHHH', hdr, 0x2A)
print('  e_phoff=0x%X e_phnum=%d e_shoff=0x%X e_shnum=%d' % (e_phoff, e_phnum, e_shoff, e_shnum))
ELF_END = ELF_OFF + e_shoff + e_shentsize * e_shnum
print('  ⇒ ELF 范围 = %d..%d (%.1f MB)' % (ELF_OFF, ELF_END, (ELF_END - ELF_OFF) / 1e6))

# ---- 在 ELF 区间里找"≥2 连续汉字" ----
arr = np.frombuffer(bytes(iso.mm[ELF_OFF:ELF_END]), dtype=np.uint8)
runs = []
for (s, e) in FC.candidate_spans(arr, min_bytes=2, runhi=FC.SCAN_RUNHI):
    for h in FC.runs_in_span(bytes(iso.mm[ELF_OFF + s:ELF_OFF + e]), old, 2):
        h['off'] += ELF_OFF + s
        h['span'] = (ELF_OFF + s, ELF_OFF + e)
        runs.append(h)
print('\nELF 内 "≥2 连续汉字" 段: %d 个' % len(runs))
for h in runs:
    off, nb = h['off'], h['nbytes']
    pre = bytes(iso.mm[off - 16:off])
    post = bytes(iso.mm[off + nb:off + nb + 16])
    # enclosing NUL-delimited C string
    lo = off
    while lo > ELF_OFF and iso.mm[lo - 1] != 0:
        lo -= 1
    hi = off + nb
    while hi < ELF_END and iso.mm[hi] != 0:
        hi += 1
    cstr = bytes(iso.mm[lo:hi])
    t_cstr, _ = old.decode(cstr)
    # "整条 C 串是否干净解码" = 解码消耗的字节数 == len(cstr)?
    units = FC.parse_units(cstr, old)
    consumed = units[-1][0] + units[-1][1] if units else 0
    print('  @0x%06X (+%d B) %r  pair_ratio=%.2f maxcjk=%d' % (off, nb, h['text'],
                                                               h['pair_ratio'], h['maxcjk']))
    print('      pre = %s | %r' % (pre.hex(' '), pre))
    print('      post= %s | %r' % (post.hex(' '), post))
    print('      span= 0x%X..0x%X (%d B)  字节前=%02X 后=%02X'
          % (h['span'][0], h['span'][1], h['span'][1] - h['span'][0],
             iso.mm[off - 1], iso.mm[off + nb]))
    print('      C串 0x%X..0x%X (%d B) 干净解码=%s 解出=%r'
          % (lo, hi, len(cstr), consumed == len(cstr), t_cstr[:60]))
    print('      新 charset 解该段 = %r   新码 = %s'
          % (new.decode(bytes(iso.mm[off:off + nb]))[0],
             ' '.join(new.encode_strict(c).hex() for c in h['text'])))

# ---- 全盘 ≥2 的规模 (为了性能评估): 只统计 IMG 之外 ----
t0 = time.time()
containers = FC.enumerate_containers(iso)
regions = sorted((e['iso_off'], e['iso_off'] + e['stored']) for (_t, _l, _i, e) in containers)
print('\n容器 %d 个, 区间表就绪 %.1fs' % (len(containers), time.time() - t0))

def in_img(off):
    lo, hi = 0, len(regions) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        a, b = regions[mid]
        if off < a:
            hi = mid - 1
        elif off >= b:
            lo = mid + 1
        else:
            return True
    return False

_orig_runs_in_span = FC.runs_in_span
FC.runs_in_span = lambda seg, cs, min_cjk=2: _orig_runs_in_span(seg, cs, min_cjk)
t0 = time.time()
hits = FC.scan_raw_iso(iso, old, verbose=True)
outside = [h for h in hits if not in_img(h['off'])]
print('全盘 ≥2 命中 %d 段, 其中 IMG 之外 %d 段 (%.1fs)'
      % (len(hits), len(outside), time.time() - t0))
by = {}
for h in outside:
    if h['off'] < 16 * tcslib.SEC:
        key = 'ISO 系统区'
    elif ELF_OFF <= h['off'] < ELF_END:
        key = 'ELF'
    elif h['off'] >= 19175 * tcslib.SEC:
        key = 'IMG 空隙/尾部'
    else:
        key = '其它独立文件'
    by[key] = by.get(key, 0) + 1
for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
    print('   %-16s %d 段' % (k, v))
# 把 IMG 之外的逐段明细写出来 (报告用)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'probe_elf2_outside.json')
io_ = __import__('io')
io_.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
    iso=ISO, charset=CS, min_cjk=FC.SCAN_MIN_CJK,
    elf=(ELF_OFF, ELF_END), n_raw=len(hits), n_outside=len(outside),
    runs=[dict(off=h['off'], nbytes=h['nbytes'], text=h['text'],
               pair_ratio=h['pair_ratio'], span=list(h['span']),
               prev=iso.mm[h['off'] - 1], nxt=iso.mm[h['off'] + h['nbytes']]) for h in outside],
), ensure_ascii=False, indent=1) + '\n')
print('明细 → %s' % out)
iso.close()
