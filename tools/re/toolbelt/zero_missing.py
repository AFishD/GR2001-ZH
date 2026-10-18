# -*- coding: utf-8 -*-
r"""zero_missing.py — A1: 「现役字库之外的字」精确清单（只读）

口径（与注入器预检 tcslib.GlyphCache.check_text 一致）:
  · ord(ch) < 0x80  ⇒ 一律放行（ASCII + 控制）
  · 其余必须在 charset_compiled_zh16.json 的 codes/pair_of 里
  · 参与判定的文本列 = `text_edited`（为空则该条未改，跳过）

结果:
  · 落盘 CSV: work/builds/GR_ZH98/temp/r81/missing_chars.csv
      列 = char,codepoint,count,in_entries,entries,rank_count,in_font_zh113,slot_if_known
  · 落盘 CSV: work/builds/GR_ZH98/temp/r81/missing_entries.csv
      列 = source,id,resource,container,entry_index,missing_kinds,missing_occ
  · 落盘 JSON: work/builds/GR_ZH98/temp/r81/missing_summary.json

用法: python tools/re/toolbelt/zero_missing.py
"""
import csv
import glob
import json
import os
import sys
from collections import Counter, defaultdict

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
os.makedirs(OUT, exist_ok=True)

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
cs_raw = json.load(open(CHARSET, encoding='utf-8'))
codes = {k: int(v) for k, v in cs_raw['codes'].items()}       # char -> single byte
pair_of = {k: tuple(v) for k, v in cs_raw['pair_of'].items()}  # char -> (lead, trail)
AVAIL = set(codes) | set(pair_of)
print('[charset] 单字节 %d + 对偶 %d = %d 字' % (len(codes), len(pair_of), len(AVAIL)))

# 历史 329 入选清单（round67），用来区分"还没入字库" vs "已入字库"
EXPAND_CSV = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_expand_zh113.csv')
expand = set()
if os.path.exists(EXPAND_CSV):
    with open(EXPAND_CSV, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            ch = row.get('char') or ''
            if ch:
                expand.add(ch)
    print('[round67] charset_expand_zh113.csv 入选 %d 字' % len(expand))

SOURCES = [
    ('disc113b_cur', os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text')),
    ('113b_pre_r71', os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text_backup_before_r71')),
    ('109_post_reduce', os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')),
    ('109_pre_reduce', os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_reduce')),
    ('109_pre_wrapfix', os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_wrapfix')),
]


def load_texts(d):
    """返回 {id: dict(row)}，同 id 冲突时保留第一条并计数"""
    rows = {}
    files = sorted(glob.glob(os.path.join(d, '*_text_*.csv')))
    files = [f for f in files if '_view_' not in os.path.basename(f)]
    for fp in files:
        with open(fp, encoding='utf-8-sig', newline='') as f:
            rd = csv.DictReader(f)
            if not rd.fieldnames or 'text_edited' not in rd.fieldnames:
                continue
            for r in rd:
                i = r.get('id')
                if not i:
                    continue
                r['_file'] = os.path.basename(fp)
                rows.setdefault(i, r)
    return rows


def missing_of(text):
    return [c for c in text if ord(c) >= 0x80 and c not in AVAIL]


summary = {'charset': {'single': len(codes), 'pair': len(pair_of), 'total': len(AVAIL)},
           'sources': {}}
all_csv_rows = []
all_ent_rows = []

for tag, d in SOURCES:
    if not os.path.isdir(d):
        print('[%s] 目录不存在: %s' % (tag, d))
        continue
    rows = load_texts(d)
    cnt = Counter()
    ent = defaultdict(set)
    ent_occ = Counter()
    n_edited = 0
    n_chars = 0
    for i, r in rows.items():
        t = r.get('text_edited') or ''
        if not t or t == '[[empty]]':
            continue
        n_edited += 1
        n_chars += len(t)
        for c in missing_of(t):
            cnt[c] += 1
            ent[c].add(i)
            ent_occ[i] += 1
    per_entry = sum(1 for i in ent_occ if ent_occ[i])
    summary['sources'][tag] = {'dir': os.path.relpath(d, REPO), 'rows': len(rows),
                               'edited_rows': n_edited, 'chars': n_chars,
                               'missing_kinds': len(cnt), 'missing_occ': sum(cnt.values()),
                               'entries_with_missing': per_entry}
    print('[%s] %-42s 行 %-5d 已改 %-5d 字符 %-8d 缺字 %d 种 / %d 次 / %d 条'
          % (tag, os.path.relpath(d, REPO), len(rows), n_edited, n_chars,
             len(cnt), sum(cnt.values()), per_entry))
    if tag == '109_pre_reduce':
        for c, k in cnt.most_common():
            all_csv_rows.append(dict(char=c, codepoint='U+%04X' % ord(c), count=k,
                                     in_entries=len(ent[c]),
                                     entries=' '.join(sorted(ent[c])),
                                     in_font_zh113=('yes' if c in AVAIL else 'NO'),
                                     in_round67_329=('yes' if c in expand else 'no')))
        for i, k in sorted(ent_occ.items(), key=lambda x: (-x[1], x[0])):
            r = rows[i]
            all_ent_rows.append(dict(source=tag, id=i, resource=r.get('resource', ''),
                                     container=r.get('container', ''),
                                     entry_index=r.get('entry_index', ''),
                                     missing_kinds=len({c for c in missing_of(r.get('text_edited') or '')}),
                                     missing_occ=k))

# ---- 落盘 ----
f1 = os.path.join(OUT, 'missing_chars.csv')
with open(f1, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['char', 'codepoint', 'count', 'in_entries', 'entries',
                                      'in_font_zh113', 'in_round67_329'])
    w.writeheader()
    for r in all_csv_rows:
        w.writerow(r)
f2 = os.path.join(OUT, 'missing_entries.csv')
with open(f2, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['source', 'id', 'resource', 'container', 'entry_index',
                                      'missing_kinds', 'missing_occ'])
    w.writeheader()
    for r in all_ent_rows:
        w.writerow(r)
f3 = os.path.join(OUT, 'missing_summary.json')
json.dump(summary, open(f3, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n[OUT] %s' % f1)
print('[OUT] %s' % f2)
print('[OUT] %s' % f3)
