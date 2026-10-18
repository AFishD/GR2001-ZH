# -*- coding: utf-8 -*-
r"""zx_textcheck.py — 只读: 对比 GR_ZH113b/text（缩减版）与 text_backup_before_r71（丰富版）

回答:
  [1] 两个目录的表结构是否一致 (文件 / 条目数 / id 集合)
  [2] 逐行 text_edited 差异 (哪些 id / 哪些 kind / 差异行数)
  [3] 丰富版里的缺字 (相对 charset) 种数/字次/条目数 —— 复现 364/386/25
  [4] 键/练/用/△ 的用量 (决定抬 gate 的代价): codes 里 B1..B4 对应哪些字;
      text_edited 里这些字出现多少次; \ue0b1 / {{BTN:E0B1}} 出现多少次
  [5] charset 现状: codes 里 B1..B4 的归属
"""
import csv
import glob
import json
import os
import sys
from collections import Counter, OrderedDict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
os.makedirs(OUT, exist_ok=True)
CUR = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text')
RICH = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text_backup_before_r71')
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
B1 = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_reduce')

LS = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LS.append(s)


def load_dir(d):
    """{kind: {id: (text_edited, text_zh, row)}}"""
    out = OrderedDict()
    for fp in sorted(glob.glob(os.path.join(d, '*_text_*.csv'))):
        bn = os.path.basename(fp)
        if '_view_' in bn:
            continue
        rows = OrderedDict()
        with open(fp, encoding='utf-8-sig', newline='') as f:
            rd = csv.DictReader(f)
            for row in rd:
                rows[row['id']] = dict(edited=(row.get('text_edited') or ''),
                                       zh=(row.get('text_zh') or ''),
                                       en=(row.get('text_en') or row.get('text') or ''))
        out[bn] = rows
    return out


cur = load_dir(CUR)
rich = load_dir(RICH)
b1 = load_dir(B1)

P('=' * 78)
P('[1] 目录结构')
P('=' * 78)
P('  CUR  %s : %d 张表, %d 行' % (os.path.basename(CUR), len(cur), sum(len(v) for v in cur.values())))
P('  RICH %s : %d 张表, %d 行' % (os.path.basename(RICH), len(rich), sum(len(v) for v in rich.values())))
P('  R64  %s : %d 张表, %d 行' % (os.path.basename(B1), len(b1), sum(len(v) for v in b1.values())))
P('  CUR 文件: %s' % list(cur))
P('  RICH 文件: %s' % list(rich))
P('  R64  文件: %s' % list(b1))

P('')
P('=' * 78)
P('[2] 逐行差异 (text_edited)')
P('=' * 78)
tot_diff = 0
diff_ids = []
for bn in cur:
    if bn not in rich:
        P('  !! RICH 缺这张表: %s' % bn)
        continue
    ids_c, ids_r = set(cur[bn]), set(rich[bn])
    if ids_c != ids_r:
        P('  !! %s id 集合不同: 仅 CUR %s ; 仅 RICH %s'
          % (bn, sorted(ids_c - ids_r)[:5], sorted(ids_r - ids_c)[:5]))
    nd = 0
    for i in cur[bn]:
        if i in rich[bn] and cur[bn][i]['edited'] != rich[bn][i]['edited']:
            nd += 1
            diff_ids.append((bn, i))
    tot_diff += nd
    P('  %-42s 行 %4d, text_edited 不同 %4d' % (bn, len(cur[bn]), nd))
P('  ★ text_edited 不同的行合计 = %d' % tot_diff)
P('  前 20 个不同的 id: %s' % diff_ids[:20])

P('')
P('=' * 78)
P('[3] 丰富版的缺字 (相对当前 charset)')
P('=' * 78)
cs = json.load(open(CHARSET, encoding='utf-8'))
codes = {k: int(v) for k, v in cs['codes'].items()}
pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
CODE2CH = {v: k for k, v in codes.items()}
AVAIL = set(codes) | set(pair_of)
P('  charset: codes %d, pair_of %d, 并集 %d' % (len(codes), len(pair_of), len(AVAIL)))

for tag, dat in (('CUR', cur), ('RICH', rich), ('R64', b1)):
    miss = Counter()
    per_entry = Counter()
    n_rows = 0
    for bn, rows in dat.items():
        for i, r in rows.items():
            t = r['edited']
            if not t:
                continue
            n_rows += 1
            m = sorted({c for c in t if ord(c) >= 0x80 and c not in AVAIL})
            if m:
                per_entry[(bn, i)] += 1
                for c in m:
                    miss[c] += t.count(c)
    P('  %-5s 已改行 %-5d 缺字 %3d 种 / %4d 字次 / %3d 条目'
      % (tag, n_rows, len(miss), sum(miss.values()), len(per_entry)))
    if tag == 'RICH':
        P('        top10: %s' % miss.most_common(10))
        P('        条目: %s' % sorted('%s:%s(%d)' % (k[0].split('_text_')[-1], k[1], v)
                                     for k, v in per_entry.items()))

P('')
P('=' * 78)
P('[4] 键/练/用/△ 的归属与用量')
P('=' * 78)
for b in (0xB1, 0xB2, 0xB3, 0xB4, 0xB5):
    P('  codes[0x%02X] = %r' % (b, CODE2CH.get(b)))
MARK_KEYS = {}
for b in (0xB1, 0xB2, 0xB3, 0xB4):
    ch = CODE2CH.get(b)
    if ch:
        MARK_KEYS[ch] = b
P('  需要统计的字符: %s' % {k: hex(v) for k, v in MARK_KEYS.items()})
for tag, dat in (('CUR', cur), ('RICH', rich)):
    cnt = Counter()
    for bn, rows in dat.items():
        for i, r in rows.items():
            t = r['edited']
            if not t:
                continue
            for ch, b in MARK_KEYS.items():
                c = t.count(ch)
                if c:
                    cnt['char:' + ch] += c
            for probe in ('\ue0b1', '\ue0b5', '{{BTN:E0B1}}', '{{BTN:E0B5}}', '\u25b3', '\u2715'):
                c = t.count(probe)
                if c:
                    cnt['mark:' + repr(probe)] += c
    P('  %-5s %s' % (tag, dict(cnt)))

P('')
P('=' * 78)
P('[5] RICH 里"新增字"在 charset 里的现状 / 是否与已有字冲突')
P('=' * 78)
richmiss = Counter()
for bn, rows in rich.items():
    for i, r in rows.items():
        t = r['edited']
        if not t:
            continue
        for c in t:
            if ord(c) >= 0x80 and c not in AVAIL:
                richmiss[c] += 1
P('  缺字种数 %d ; 与 codes/pair_of 冲突 0 (按定义)' % len(richmiss))
P('  缺字里是否有 ASCII 或已映射字符: %s'
  % [c for c in richmiss if ord(c) < 0x80])
json.dump(dict(rich_missing={c: n for c, n in richmiss.items()},
               cur_missing={}, diff_rows=[list(x) for x in diff_ids]),
          open(os.path.join(OUT, 'textcheck.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# 缺字清单 CSV（丰富版口径）——用与 r81 相同的口径重算，便于交叉核对
with open(os.path.join(OUT, 'rich_missing_chars.csv'), 'w', encoding='utf-8',
          newline='\n') as f:
    w = csv.writer(f)
    w.writerow(['char', 'codepoint', 'count', 'in_entries', 'entries'])
    ent = {}
    for bn, rows in rich.items():
        for i, r in rows.items():
            t = r['edited']
            if not t:
                continue
            for c in set(t):
                if ord(c) >= 0x80 and c not in AVAIL:
                    ent.setdefault(c, set()).add('%s:%s' % (bn.split('_text_')[-1][:-4], i))
    for c, n in sorted(richmiss.items(), key=lambda kv: (-kv[1], kv[0])):
        w.writerow([c, 'U+%04X' % ord(c), n, len(ent[c]), '|'.join(sorted(ent[c]))])
P('  → %s' % os.path.join(OUT, 'rich_missing_chars.csv'))

with open(os.path.join(OUT, 'textcheck.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(LS) + '\n')
