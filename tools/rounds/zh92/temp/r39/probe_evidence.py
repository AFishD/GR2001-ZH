# -*- coding: utf-8 -*-
"""r39 探针 3: 逐 kind 的中文证据 (与英文原盘逐容器集合减法) + 保守判据的候选样本。只读。"""
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
EN = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
cs = T.Charset()
idx = FU.CharsetIndex()
CJK = re.compile(r'[\u4e00-\u9fff]')
VIS = re.compile(r'[0-9A-Za-z \.\-_/\\:;,\'\"!?()\[\]<>+=*&%$#@~`^{}|]')
WORDCH = re.compile(r'[0-9A-Za-z]')

# ── 保守判据 (候选) ──
MIN_RUN_BIN = 12          # 二进制容器: 串长 >= 12 B
MIN_RUN_STRUCT = 6        # 结构化容器 (XML/TXT/MIS/ATR/RES): 串长 >= 6 B
VIS_MIN = 0.85            # 「可见字符率」>= 85%
MAX_CHAR_RUN = 8          # 同一字符连续出现 <= 8
NEED_SPACE_CH = 2         # 至少 2 个字母/数字


def keep(s_bytes, min_run, structured=False):
    """返回 (是否保留, 为什么丢, 解出的文本)"""
    L = len(s_bytes)
    if L < min_run:
        return False, 'too-short', None
    t = cs.decode(s_bytes)[0]
    if any(0xE000 <= ord(c) <= 0xF8FF for c in t):
        return False, 'has-pua', None
    vis = sum(1 for c in t if VIS.match(c))
    if vis / len(t) < VIS_MIN:
        return False, 'low-visible(%.2f)' % (vis / len(t)), None
    # 同一字符连续
    run = best = 1
    for i in range(1, len(t)):
        run = run + 1 if t[i] == t[i - 1] else 1
        best = max(best, run)
    if best > MAX_CHAR_RUN:
        return False, 'char-repeat(%d)' % best, None
    if sum(1 for c in t if WORDCH.match(c)) < NEED_SPACE_CH:
        return False, 'no-word-char', None
    return True, None, t


def survey(path, tag):
    iso = T.Iso(path)
    conts = FU.build_container_list(iso)
    per = {}
    for c in conts:
        b, _raw = FU.container_blob(iso, c)
        s = set()
        for m in idx.run_re(MIN_RUN_BIN).finditer(b):
            s |= set(CJK.findall(cs.decode(m.group(0))[0]))
        per[(c['img'], c['idx'], c['name'])] = (s, c['kind'])
    iso.close()
    return per, conts


print('# 逐容器中文证据: 中文盘命中 − 英文盘**同一个容器**的命中')
zh_per, zh_conts = survey(ZH, 'ZH')
en_per, _ = survey(EN, 'EN')
print('# 中文盘容器 %d 个; 英文盘容器 %d 个' % (len(zh_per), len(en_per)))
same = sum(1 for k in zh_per if k in en_per and zh_per[k][0] == en_per[k][0])
print('# 命中集合逐元素相同的容器 = %d; 不同的 = %d'
      % (same, len(zh_per) - same))

ev = collections.defaultdict(set)
delta_cont = []
for k, (s, kind) in zh_per.items():
    e = en_per.get(k, (set(), None))[0]
    d = s - e
    if d:
        ev[kind] |= d
        delta_cont.append((kind, k[2], ''.join(sorted(d))[:40]))
print('\n--- 每个 kind 的**真实中文证据** (减完英文盘后) ---')
for kind in sorted(ev):
    print('%-10s %4d 字: %s' % (kind, len(ev[kind]), ''.join(sorted(ev[kind]))[:60]))
print('\n--- 有差异的容器 (除 LANG/SFXML 外) ---')
for kind, nm, ch in sorted(delta_cont):
    if kind not in ('LANG', 'SFXML'):
        print('   %-9s %-42s %s' % (kind, nm, ch))

# ── 保守判据下的候选量 ──
print('\n--- 保守判据下的候选串数 (每 kind) ---')
iso = T.Iso(ZH)
conts = FU.build_container_list(iso)
cnt = collections.Counter()
why = collections.Counter()
samples = collections.defaultdict(list)
for c in conts:
    if c['kind'] in ('LANG', 'SFXML'):
        continue
    b, _raw = FU.container_blob(iso, c)
    struct = c['kind'] in ('XML', 'TXT', 'MIS', 'ATR', 'RES')
    mr = MIN_RUN_STRUCT if struct else MIN_RUN_BIN
    for m in idx.run_re(min(mr, 4)).finditer(b):
        ok, reason, t = keep(m.group(0), mr, struct)
        if ok:
            cnt[c['kind']] += 1
            if len(samples[c['kind']]) < 6:
                samples[c['kind']].append((c['name'], t))
        else:
            why[(c['kind'], reason.split('(')[0])] += 1
for k in sorted(cnt):
    print('%-10s %8d 条候选' % (k, cnt[k]))
    for nm, t in samples[k]:
        print('      %-38s %r' % (nm[:38], t[:90]))
print('\n--- 被丢掉的原因分布 (top) ---')
for (k, r), n in sorted(why.items(), key=lambda x: -x[1])[:20]:
    print('   %-10s %-18s %d' % (k, r, n))
iso.close()
