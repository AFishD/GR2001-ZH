# -*- coding: utf-8 -*-
"""r39 探针 4: 收紧后的保守判据 (criterion B) —— 各 kind 保留量与样本。只读。"""
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

TEXTCH = re.compile(r'[0-9A-Za-z]')
PUNCT = re.compile(r'[ \t\.\-_/\\:;,\'\"!?()\[\]<>+=*&%$#@~`^{}|]')
CJK = re.compile(r'[\u4e00-\u9fff]')
OKVIS = re.compile(r"[0-9A-Za-z \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
PRINTABLE = set(range(0x20, 0x7F)) | {0x09}

MIN_RUN = {'XML': 6, 'TXT': 6, 'MIS': 6, 'ATR': 6, 'RES': 8}
MIN_RUN_BIN = 12
VIS_MIN, VIS_MIN_STRUCT = 0.85, 0.80
WORD_MIN_ASCII = 0.70
WORD_MIN_CJK = 0.55
MAX_CHAR_RUN = 8
LONG_NEED_PUNCT = 16
MIN_SPACE_WORD_BIN = 2


def judge(sb, kind):
    """criterion B: 返回 (保留?, 原因, 文本)"""
    mr = MIN_RUN.get(kind, MIN_RUN_BIN)
    if len(sb) < mr:
        return False, 'short', None
    # 快速路: 全部 ASCII 可打印/制表
    if all(b in PRINTABLE for b in sb):
        t = sb.decode('ascii')
        w = sum(1 for c in t if TEXTCH.match(c))
        if w / len(t) < WORD_MIN_ASCII:
            return False, 'ascii-word-ratio', None
        nw = sum(1 for c in t if c == ' ' or TEXTCH.match(c))
        if len(t) >= LONG_NEED_PUNCT and nw < MIN_SPACE_WORD_BIN:
            return False, 'ascii-no-words', None
    else:
        # 含高位字节 → 用盘上字符集解码
        t = cs.decode(sb)[0]
        if any(0xE000 <= ord(c) <= 0xF8FF for c in t):
            return False, 'pua', None
        vis = sum(1 for c in t if OKVIS.match(c))
        vis_ratio = vis / len(t)
        if vis_ratio < VIS_MIN:
            return False, 'visible', None
        w = sum(1 for c in t if TEXTCH.match(c))
        if w / len(t) < WORD_MIN_CJK:
            return False, 'cjk-word-ratio', None
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
    return True, None, t


iso = T.Iso(ZH)
conts = FU.build_container_list(iso)
cnt = collections.Counter()
distinct = collections.defaultdict(set)
samples = collections.defaultdict(list)
why = collections.Counter()
nskip_cov = 0
cov_rows = []
for c in conts:
    if c['kind'] in ('LANG', 'SFXML'):
        continue
    b, _raw = FU.container_blob(iso, c)
    if len(b) < 256:
        continue
    cov = sum(m.end() - m.start() for m in idx.run_re(8).finditer(b)) / float(len(b))
    cov_rows.append((cov, c['kind'], c['name'], len(b)))
    if cov < 0.15 and len(b) >= 1 << 20 and c['kind'] not in ('XML', 'TXT', 'MIS', 'ATR', 'RES', 'ELF'):
        nskip_cov += 1
        continue
    mr = MIN_RUN.get(c['kind'], MIN_RUN_BIN)
    seen = set()
    for m in idx.run_re(min(mr, 4)).finditer(b):
        ok, reason, t = judge(m.group(0), c['kind'])
        if ok:
            if t not in seen:
                seen.add(t)
                distinct[c['kind']].add(t)
                if len(samples[c['kind']]) < 5:
                    samples[c['kind']].append((c['name'], t))
            cnt[c['kind']] += 1
        else:
            why[(c['kind'], reason)] += 1

print('# 因覆盖率<15%% 且 >=1MB 而整体跳过的容器数 = %d' % nskip_cov)
print('\n--- criterion B: 每 kind 保留行数 / 去重后不同串数 ---')
print('%-10s %10s %10s %8s %10s' % ('kind', 'rows', 'distinct', 'max/c', 'avg/c'))
for k in sorted(cnt):
    per = collections.Counter()
    print('%-10s %10d %10d' % (k, cnt[k], len(distinct[k])))
print('\n--- 样本 ---')
for k in sorted(samples):
    print('== %s ==' % k)
    for nm, t in samples[k]:
        print('     %-34s %r' % (nm[:34], t[:110]))
print('\n--- 丢弃原因 ---')
for (k, r), n in sorted(why.items(), key=lambda x: -x[1])[:24]:
    print('   %-10s %-18s %d' % (k, r, n))

cov_rows.sort(reverse=True)
print('\n--- 覆盖率 top20 ---')
for r in cov_rows[:20]:
    print('  %.3f %-9s %-44s %9d' % r)
print('\n--- 覆盖率 <0.15 的容器按 kind 计数 ---')
low = collections.Counter(r[1] for r in cov_rows if r[0] < 0.15)
big = collections.Counter(r[1] for r in cov_rows if r[0] < 0.15 and r[3] >= (1 << 20))
print('   全部: %s' % dict(low))
print('   >=1MB: %s' % dict(big))
iso.close()
