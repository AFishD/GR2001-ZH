# -*- coding: utf-8 -*-
"""r39 探针 7: 把「文本分」闸门钉死在实测噪声本底上 —— 随机数据 / PSS / 真文本 对照。只读。"""
import collections
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T
import font_usage as FU

ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
iso = T.Iso(ZH)
cs = T.Charset()
idx = FU.CharsetIndex()
conts = FU.build_container_list(iso)

WORD = re.compile(r'[0-9A-Za-z]')
PUNCT = re.compile(r"[ \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
CJK = re.compile(r'[\u4e00-\u9fff]')
OKVIS = re.compile(r"[0-9A-Za-z \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
PRINTABLE = set(range(0x20, 0x7F)) | {0x09}
STRUCT = ('XML', 'TXT', 'MIS', 'ATR', 'RES')
WORDSPACE = re.compile(r'[0-9A-Za-z][ \t][0-9A-Za-z]')
CJK2 = re.compile(r'[\u4e00-\u9fff]{2,}')


def rep4(t):
    if len(t) < 8:
        return False
    seen = set()
    for i in range(len(t) - 3):
        s = t[i:i + 4]
        if s in seen:
            return True
        seen.add(s)
    return False


def judge(sb, kind):
    mr = 6 if kind in STRUCT else 12
    if len(sb) < mr:
        return False, None
    if all(b in PRINTABLE for b in sb):
        t = sb.decode('ascii')
        if sum(1 for c in t if WORD.match(c)) / len(t) < 0.70:
            return False, None
    else:
        t = cs.decode(sb)[0]
        if any(0xE000 <= ord(c) <= 0xF8FF for c in t):
            return False, None
        if sum(1 for c in t if OKVIS.match(c)) / len(t) < 0.85:
            return False, None
        if sum(1 for c in t if WORD.match(c)) / len(t) < 0.55:
            return False, None
        if not CJK.search(t):
            return False, None
    run = best = 1
    for i in range(1, len(t)):
        run = run + 1 if t[i] == t[i - 1] else 1
        best = max(best, run)
    if best > 8:
        return False, None
    if len(t) >= 16 and not PUNCT.search(t):
        return False, None
    if rep4(t):
        return False, None
    # ★ 二进制容器加严: 必须有「词 空格 词」或「连续 2 个汉字」
    if kind not in STRUCT and not (WORDSPACE.search(t) or CJK2.search(t)):
        return False, None
    return True, t


def score_of(b, kind):
    mr = 6 if kind in STRUCT else 12
    seen = set()
    for m in idx.run_re(min(mr, 4)).finditer(b):
        ok, t = judge(m.group(0), kind)
        if ok:
            seen.add(t)
    mb = max(1.0, len(b) / 1048576.0)
    return len(seen) / mb, len(seen)


print('--- 随机数据本底 (criterion C 全开) ---')
random.seed(20261005)
for n_mb in (1, 4, 16):
    rnd = bytes(random.randrange(256) for _ in range(n_mb << 20))
    s, k = score_of(rnd, 'MEDIA')
    print('   纯随机 %2d MB: 保留不同串 %6d  → 文本分 %7.1f /MB' % (n_mb, k, s))

print('\n--- 全盘每容器文本分 (按 kind) ---')
sc = collections.defaultdict(list)
for c in conts:
    b, _raw = FU.container_blob(iso, c)
    if len(b) < 64:
        continue
    s, k = score_of(b, c['kind'])
    sc[c['kind']].append((s, k, c['name'], len(b)))

print('%-10s %5s %10s %10s %10s %10s' % ('kind', 'n', '中位', 'p10', 'p90', '最大'))
for k in sorted(sc):
    v = sorted(x[0] for x in sc[k])
    q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
    print('%-10s %5d %10.2f %10.2f %10.2f %10.2f' % (k, len(v), q(.5), q(.1), q(.9), v[-1]))

print('\n--- 各 kind 文本分 < 10 / 10~40 / >=40 的容器数 ---')
print('%-10s %8s %8s %8s' % ('kind', '<10', '10-40', '>=40'))
for k in sorted(sc):
    lo = sum(1 for x in sc[k] if x[0] < 10)
    mid = sum(1 for x in sc[k] if 10 <= x[0] < 40)
    hi = sum(1 for x in sc[k] if x[0] >= 40)
    print('%-10s %8d %8d %8d' % (k, lo, mid, hi))

print('\n--- 各 kind 在阈值下的去重串数 ---')
for thr in (0, 10, 40, 100):
    tot = collections.Counter()
    for k in sorted(sc):
        for (s, kk, nm, nb) in sc[k]:
            if s >= thr:
                tot[k] += kk
    print('  thr=%-4d %s' % (thr, dict(tot)))

print('\n--- MEDIA 里文本分最高的 10 个 (看看有没有真文本) ---')
for x in sorted(sc['MEDIA'], reverse=True)[:10]:
    print('   %8.2f  %6d 串  %-34s %9d B' % (x[0], x[1], x[2][:34], x[3]))
print('--- MEDIA 里文本分 >= 40 的容器 ---')
for x in sorted(sc['MEDIA'], reverse=True):
    if x[0] >= 40:
        print('   %8.2f  %6d 串  %-34s %9d B' % (x[0], x[1], x[2][:34], x[3]))
print('\n--- OTHER / RSB 里文本分最高的 5 个 ---')
for k in ('OTHER', 'RSB'):
    for x in sorted(sc[k], reverse=True)[:5]:
        print('   %-6s %8.2f  %6d 串  %-34s %9d B' % (k, x[0], x[1], x[2][:34], x[3]))
iso.close()
