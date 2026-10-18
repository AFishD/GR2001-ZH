# -*- coding: utf-8 -*-
"""r39 探针 9: 最终闸门设计 —— 每容器 (score, msg_ratio) 汇总表。只读。"""
import collections
import json
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
MSG = re.compile(r'[0-9A-Za-z]{2,}[ \t][0-9A-Za-z]{2,}')
CJK2 = re.compile(r'[\u4e00-\u9fff]{2,}')

# ★ 风险等级: binary=True 的 kind 需要 corpus 闸门
RISKY = ('MEDIA', 'OTHER', 'PAK', 'RSB')


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
    strict = True
    if all(b in PRINTABLE for b in sb):
        t = sb.decode('ascii')
        if sum(1 for c in t if WORD.match(c)) / len(t) < 0.70:
            return False, None
        if ' ' in t or '\t' in t:
            strict = False
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
        strict = False
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
    return True, (t, strict, bool(MSG.search(t) or CJK2.search(t)))


rows = []
for c in conts:
    if c['kind'] in ('LANG', 'SFXML'):
        continue
    b, _raw = FU.container_blob(iso, c)
    if len(b) < 64:
        continue
    mr = 6 if c['kind'] in STRUCT else 12
    seen, msg, strict = set(), 0, 0
    n = 0
    for m in idx.run_re(min(mr, 4)).finditer(b):
        ok, v = judge(m.group(0), c['kind'])
        if not ok:
            continue
        t, s, ismsg = v
        n += 1
        if t not in seen:
            seen.add(t)
            msg += 1 if ismsg else 0
            strict += 1 if s else 0
    mb = max(1.0, len(b) / 1048576.0)
    rows.append(dict(kind=c['kind'], name=c['name'], blob=len(b), raw=n,
                     distinct=len(seen), msg=msg, strict=strict,
                     score=len(seen) / mb, msg_ratio=msg / max(1, len(seen)),
                     strict_ratio=strict / max(1, len(seen))))

json.dump(rows, open(os.path.join(HERE, 'container_stats.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)

print('%-10s %5s %8s %9s %9s %9s %9s %9s' %
      ('kind', 'n', 'cont_ok', 'distinct', 'score_med', 'msgR_med', 'msgR_max', 'strict_med'))
for k in sorted(set(r['kind'] for r in rows)):
    rs = [r for r in rows if r['kind'] == k]
    ok = [r for r in rs if r['distinct'] >= 4]
    med = lambda f: sorted(f(x) for x in ok)[len(ok) // 2] if ok else 0.0
    print('%-10s %5d %8d %9d %9.2f %9.3f %9.3f %9.3f' %
          (k, len(rs), len(ok), sum(x['distinct'] for x in ok),
           med(lambda x: x['score']), med(lambda x: x['msg_ratio']),
           max([x['msg_ratio'] for x in ok] or [0]), med(lambda x: x['strict_ratio'])))

print('\n--- 高风险 kind 里 msg_ratio 最高的 8 个容器 ---')
for k in RISKY:
    rs = sorted([r for r in rows if r['kind'] == k], key=lambda x: -x['msg_ratio'])[:8]
    print('== %s ==' % k)
    for r in rs:
        print('   msgR=%.3f score=%7.2f distinct=%6d raw=%7d %-34s' %
              (r['msg_ratio'], r['score'], r['distinct'], r['raw'], r['name'][:34]))

print('\n--- 高风险 kind 在 (msg_ratio>=0.10 and score>=8) 下的保留量 ---')
for k in RISKY:
    rs = [r for r in rows if r['kind'] == k and r['msg_ratio'] >= 0.10 and r['score'] >= 8]
    print('   %-8s 保留 %4d / %4d 容器, 串 %6d' %
          (k, len(rs), len([r for r in rows if r['kind'] == k]),
           sum(r['distinct'] for r in rs)))

print('\n--- 各 kind 的去重串总数 (无闸门 vs 有闸门) ---')
for k in sorted(set(r['kind'] for r in rows)):
    rs = [r for r in rows if r['kind'] == k]
    base = sum(r['distinct'] for r in rs)
    if k in RISKY:
        g = sum(r['distinct'] for r in rs if r['msg_ratio'] >= 0.10 and r['score'] >= 8)
    else:
        g = base
    print('   %-10s %8d → %8d' % (k, base, g))
iso.close()
