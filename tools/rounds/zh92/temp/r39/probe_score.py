# -*- coding: utf-8 -*-
"""r39 探针 5: 容器级「文本分」闸门 —— 每 kind 保留容器/串数与样本。只读。"""
import collections
import os
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
cs = T.Charset()
idx = FU.CharsetIndex()

WORD = re.compile(r'[0-9A-Za-z]')
PUNCT = re.compile(r'[ \t\.\-_/\\:;,\'\"!?()\[\]<>+=*&%$#@~`^{}|]')
CJK = re.compile(r'[\u4e00-\u9fff]')
OKVIS = re.compile(r"[0-9A-Za-z \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
PRINTABLE = set(range(0x20, 0x7F)) | {0x09}

STRUCT = ('XML', 'TXT', 'MIS', 'ATR', 'RES')
MIN_RUN_STRUCT, MIN_RUN_BIN = 6, 12
WORD_MIN_ASCII, WORD_MIN_CJK = 0.70, 0.55
VIS_MIN = 0.85
MAX_CHAR_RUN, LONG_NEED_PUNCT = 8, 16
TEXT_SCORE_MIN = 10.0        # 文本分阈值 (每 MB)
CAP_PER_CONT = 2000


def rep4(t):
    """有没有长度 4 的子串在同一个串里出现 2 次以上 (数据流重复噪声的特征)"""
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
    mr = MIN_RUN_STRUCT if kind in STRUCT else MIN_RUN_BIN
    if len(sb) < mr:
        return False, 'short', None
    if all(b in PRINTABLE for b in sb):
        t = sb.decode('ascii')
        if sum(1 for c in t if WORD.match(c)) / len(t) < WORD_MIN_ASCII:
            return False, 'ascii-word', None
    else:
        t = cs.decode(sb)[0]
        if any(0xE000 <= ord(c) <= 0xF8FF for c in t):
            return False, 'pua', None
        if sum(1 for c in t if OKVIS.match(c)) / len(t) < VIS_MIN:
            return False, 'visible', None
        if sum(1 for c in t if WORD.match(c)) / len(t) < WORD_MIN_CJK:
            return False, 'cjk-word', None
        if not CJK.search(t):
            return False, 'no-cjk', None
    run = best = 1
    for i in range(1, len(t)):
        run = run + 1 if t[i] == t[i - 1] else 1
        best = max(best, run)
    if best > MAX_CHAR_RUN:
        return False, 'char-repeat', None
    if len(t) >= LONG_NEED_PUNCT and not PUNCT.search(t):
        return False, 'no-punct', None
    if rep4(t):
        return False, 'repeat4', None
    return True, None, t


iso = T.Iso(ZH)
conts = FU.build_container_list(iso)
rows = collections.Counter()
dist = collections.defaultdict(set)
ncont = collections.Counter()
ncap = collections.Counter()
samp = collections.defaultdict(list)
why = collections.Counter()
# 每个 kind 里「文本分」低于阈值的容器数 + 保留容器数
gate = collections.defaultdict(lambda: [0, 0])
per_cont_kept = collections.defaultdict(list)
for c in conts:
    if c['kind'] in ('LANG', 'SFXML'):
        continue
    b, _raw = FU.container_blob(iso, c)
    if len(b) < 64:
        continue
    mr = MIN_RUN_STRUCT if c['kind'] in STRUCT else MIN_RUN_BIN
    seen = set()
    kept_bytes = 0
    for m in idx.run_re(min(mr, 4)).finditer(b):
        ok, reason, t = judge(m.group(0), c['kind'])
        if not ok:
            why[(c['kind'], reason)] += 1
            continue
        rows[c['kind']] += 1
        kept_bytes += len(t)
        if t not in seen:
            seen.add(t)
            dist[c['kind']].add(t)
            if len(samp[c['kind']]) < 4:
                samp[c['kind']].append((c['name'], t))
    score = (kept_bytes + 20.0 * len(seen)) / max(1.0, len(b) / 1048576.0)
    if score < TEXT_SCORE_MIN or not seen:
        gate[c['kind']][0] += 1
        continue
    gate[c['kind']][1] += 1
    ncont[c['kind']] += 1
    per_cont_kept[c['kind']].append(len(seen))
    if len(seen) > CAP_PER_CONT:
        ncap[c['kind']] += 1

print('%-10s %10s %10s %9s %9s %8s %8s' %
      ('kind', 'rows', 'distinct', 'cont_ok', 'cont_skip', 'cap_hit', 'max/c'))
for k in sorted(rows):
    mx = max(per_cont_kept[k]) if per_cont_kept[k] else 0
    print('%-10s %10d %10d %9d %9d %8d %8d' %
          (k, rows[k], len(dist[k]), gate[k][1], gate[k][0], ncap[k], mx))
print('\n--- 样本 ---')
for k in sorted(samp):
    print('== %s ==' % k)
    for nm, t in samp[k]:
        print('     %-32s %r' % (nm[:32], t[:120]))
print('\n--- 丢弃原因 ---')
for (k, r), n in sorted(why.items(), key=lambda x: -x[1])[:16]:
    print('   %-10s %-14s %d' % (k, r, n))
print('\n--- 每 kind「去重后不同串」的分布 (保留容器) ---')
for k in sorted(per_cont_kept):
    v = sorted(per_cont_kept[k])
    if not v:
        continue
    q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
    print('   %-10s n=%4d  中位 %5d  p90 %6d  p99 %6d  最大 %6d' %
          (k, len(v), q(.5), q(.9), q(.99), v[-1]))
iso.close()
