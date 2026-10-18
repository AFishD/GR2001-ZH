# -*- coding: utf-8 -*-
r"""round56 侦察 ⑤: 「真文本 vs 二进制巧合」判别指标的实测标定 (只读)。

对每个容器 blob / 每个全盘原始段, 算:
  n_chars, maxcjk, max_hi_repeat (同一个汉字最多连排几次), distinct_hi / n_hi,
  ctrl_ratio (控制字节占比), ascii_print_ratio
已知真文本: SFXML(#283) / LANG(#25, GR#902); 已知巧合: IKE.RES、.BMZ、.PSS。
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402
from scan2 import clean_runs                                          # noqa: E402

cs = tcslib.Charset()
BAD = set(range(0x00, 0x20)) - {9, 10, 13}
BAD |= set(range(0x7F, 0xA0))


def stats(text):
    n = len(text)
    if not n:
        return None
    hi = [c for c in text if ord(c) >= 0x80]
    cjk = [c for c in hi if '\u4e00' <= c <= '\u9fff']
    maxrep = 0
    rep = 1
    for i in range(1, n):
        if text[i] == text[i - 1]:
            rep += 1
            maxrep = max(maxrep, rep)
        else:
            rep = 1
    hirep, r2 = 0, 1
    for i in range(1, len(hi)):
        if hi[i] == hi[i - 1]:
            r2 += 1
            hirep = max(hirep, r2)
        else:
            r2 = 1
    return dict(n=n, n_hi=len(hi), n_cjk=len(cjk),
                distinct_hi=(len(set(hi)) / len(hi)) if hi else 0.0,
                distinct_all=len(set(text)) / n,
                maxrep=maxrep, hi_maxrep=hirep,
                cjk_ratio=(len(cjk) / n) if n else 0.0)


def analyse(blob, label, min_cjk=4, min_chars=8):
    """返回 (runs, agg) —— agg = 最"像文本"的那一段的统计。"""
    # ① 控制字节切段
    runs = []
    n = len(blob)
    i = 0
    while i < n:
        if blob[i] in BAD:
            i += 1
            continue
        j = i
        while j < n and blob[j] not in BAD:
            j += 1
        seg = blob[i:j]
        if len(seg) >= 4:
            for (a, b, t, best) in clean_runs(seg, cs, min_cjk):
                if len(t) >= min_chars:
                    st = stats(t)
                    st.update(off=i + a, nbytes=b - a, maxcjk=best, text=t)
                    runs.append(st)
        i = j
    return runs


def show(label, runs, top=6):
    print('%-34s 段 %5d' % (label, len(runs)))
    for r in sorted(runs, key=lambda x: (-x['maxcjk'], -x['n']))[:top]:
        print('     off=%-8d n=%-6d cjk=%-5d maxcjk=%-4d hi_maxrep=%-3d dist_hi=%.2f '
              'dist=%.2f %r' % (r['off'], r['n'], r['n_cjk'], r['maxcjk'], r['hi_maxrep'],
                                r['distinct_hi'], r['distinct_all'], r['text'][:48]))


iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso'))


def blob_of(lba, idx):
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    subs = tcslib.lzo_subs(raw)
    return e, (b''.join(s[0] for s in subs) if subs else raw)


for (tag, lba, idx) in (('REAL SFXML', 776286, 283), ('REAL LANG', 776286, 25),
                        ('REAL LANG@GR', 19175, 902), ('NOISE IKE.RES', 776286, 282),
                        ('NOISE BNK_01.IDC', 19175, 552), ('NOISE BMZ', 19175, 86),
                        ('NOISE M12_DOCKS.BMZ', 19175, 251), ('NOISE EN_STRINGS.TXT', 776286, 30)):
    e, blob = blob_of(lba, idx)
    runs = analyse(blob, tag)
    show('%s #%d %s' % (tag, idx, e['name']), runs)
iso.close()
