# -*- coding: utf-8 -*-
"""Generate charset_89.json (final) and report.md from summary.json + re-derived data."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import json, sys, collections

sys.path.insert(0, os.path.join(REPO_ROOT, 'work', 'tmp', 'hanzi_demand'))
from bdict import translate

OUT = os.path.join(REPO_ROOT, 'work', 'tmp', 'hanzi_demand')
S = json.load(open(OUT + r'\summary.json', encoding='utf-8'))
res = json.load(open(OUT + r'\res_parsed.json', encoding='utf-8'))
G = res['groups']
POOL = [57, 58, 60, 61, 64]
def hanzi_of(s): return [c for c in s if '\u4e00' <= c <= '\u9fff']

b_entries = []
for gi in POOL:
    for e in G[gi]['entries']:
        if e['len'] <= 30:
            zh, cat = translate(e['text'])
            b_entries.append({'g': gi + 1, 'i': e['i'], 'len': e['len'], 'en': e['text'], 'zh': zh,
                              'cat': cat, 'set': frozenset(hanzi_of(zh or ''))})
need = [e for e in b_entries if e['set']]
freq = collections.Counter()
for e in need:
    freq.update(e['set'])
rank = [c for c, _ in freq.most_common()]

def full_count(chars):
    Ch = set(chars)
    return sum(1 for e in need if e['set'] <= Ch)

def status_counts(chars):
    Ch = set(chars)
    full = part = aban = 0
    for e in need:
        inb = len(e['set'] & Ch)
        if inb == len(e['set']): full += 1
        elif inb: part += 1
        else: aban += 1
    return full, part, aban

n89, n119 = rank[:89], rank[:119]
n94, n124 = rank[:94], rank[:124]
f89, p89c, a89c = status_counts(n89)
f119, p119, a119 = status_counts(n119)
f94, p94, a94 = status_counts(n94)
f124, p124, a124 = status_counts(n124)
la32 = list(S['la']['distinct_sorted'])
hyb89 = list(dict.fromkeys(la32 + [c for c in rank if c not in la32]))[:89]
hyb_full = full_count(hyb89)

# practical variant: force core button words, then fill by b frequency
FORCED = '确认继续取消返回是否开关保存载入退出地图设置开始暂停删除'
practical89 = list(dict.fromkeys(list(FORCED) + rank))[:89]
practical119 = list(dict.fromkeys(list(FORCED) + rank))[:119]
fpr89, ppr89, apr89 = status_counts(practical89)
fpr119, ppr119, apr119 = status_counts(practical119)
pr_ab = [(e['g'], e['i'], e['en'], e['zh'], ''.join(sorted(e['set'])))
         for e in need if not (e['set'] & set(practical89))]
# next chars of practical119 beyond 89
pr_next30 = [c for c in practical119 if c not in practical89]

def abandon_list(chars):
    Ch = set(chars)
    return [(e['g'], e['i'], e['en'], e['zh'], ''.join(sorted(e['set'])))
            for e in need if not (e['set'] & Ch)]
ab89 = abandon_list(n89)
ab_pr = abandon_list(practical89)

free_codes = [c for c in range(0xA1, 0x100) if c not in (0xAE, 0xB1, 0xB5, 0xE7, 0xF1)]

# regenerate levelb_entries.csv with recommended-set status columns
import csv
with open(OUT + r'\levelb_entries.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['group', 'idx', 'bytelen', 'en', 'zh', 'category', 'nh',
                'status@freq89', 'status@practical89(推荐)', 'status@practical119', 'miss_by_practical89'])
    for e in b_entries:
        def st(S):
            if not e['set']: return 'n/a(无需汉字)'
            inb = len(e['set'] & S)
            return 'FULL' if inb == len(e['set']) else ('PART %d/%d' % (inb, len(e['set'])) if inb else 'ABANDON')
        w.writerow(['G%02d' % e['g'], 'I%03d' % e['i'], e['len'], e['en'], e['zh'] or '', e['cat'], len(e['set']),
                    st(set(n89)), st(set(practical89)), st(set(practical119)),
                    ''.join(sorted(e['set'] - set(practical89)))])

def assign_of(chars):
    return {'0x%02X' % free_codes[i]: ch for i, ch in enumerate(chars)}

json.dump({
    'budget': 89,
    'model': '1字节=1汉字; 字库可重绘码位 0xA1-0xFF 共95格; 英文在用 0xAE/0xB1/0xB5/0xE7/0xF1 共5格 -> 实测可用90; 任务保守口径再扣 0xA0 -> 89',
    'selection_primary': '实用变体: 强制核心按钮词(确认继续取消返回是否开关保存载入退出地图设置开始暂停删除) + b级字频补足; b级完整覆盖203条',
    'chars_ordered_89': practical89,
    'assignment_89': assign_of(practical89),
    'chars_next_30_to_119': pr_next30,
    'task_greedy_variant_freq89': {
        'desc': '纯字频Top-89(任务口径); 完整覆盖200条, 但核心按钮词(确认/继续/取消等)被挤出',
        'chars': n89,
        'b_full': f89,
    },
    'recommended_variant_hybrid89': {
        'desc': '强制包含现有68条译文全部32字, 其余按b级字频补足; 68条原译文零改动, b级完整覆盖%d条' % hyb_full,
        'chars': hyb89,
        'assignment': assign_of(hyb89),
        'b_full': hyb_full,
    },
    'variants_full_coverage': {
        'freq89_task': f89, 'freq94': f94, 'freq119': f119, 'freq124': f124,
        'practical89_recommended': fpr89, 'practical119': fpr119,
        'hybrid89': hyb_full,
    },
    'free_codes_count': len(free_codes),
}, open(OUT + r'\charset_89.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------------- helpers ----------------
def freq_md(fr, label, n=150):
    tot = sum(c for _, c in fr)
    rows = ['| # | 字 | %s |' % label, '|---|---|---|']
    for i, (c, k) in enumerate(fr[:n], 1):
        rows.append('| %d | %s | %d |' % (i, c, k))
    if len(fr) > n:
        rows.append('| — | 其余 %d 字合计 | %d |' % (len(fr) - n, tot - sum(c for _, c in fr[:n])))
    return '\n'.join(rows)

def fmt10(chars):
    return '\n>\n'.join('> ' + '　'.join(chars[i:i+10]) for i in range(0, len(chars), 10))

pg = S['b']['per_group']
def pgv(g, w): return pg.get('%d|%s' % (g, w), 0)

b, la, l1, c, cr, sac = S['b'], S['la'], S['l1'], S['c'], S['cross'], S['sac']
curve = b['curve_every10']
curve_str = ', '.join('%d→%d' % (int(k), v) for k, v in sorted(curve.items(), key=lambda x: int(x[0])))
curve_str += ', 119→%d' % f119

# abandon table @89 (top by group)
ab_rows = []
for g, i, en, zh, miss in ab_pr:
    ab_rows.append('| G%02d.I%03d | %s | %s | %s |' % (g, i, en.replace('|', '\\|')[:40], zh.replace('|', '\\|'), miss))
ab_table = '\n'.join(ab_rows)

R = open(OUT + r'\report_template.md', encoding='utf-8').read()
rep = (R
 .replace('@@FREQ_L1@@', freq_md(l1['freq'], '出现次数'))
 .replace('@@FREQ_B@@', freq_md(b['freq'], '条目命中'))
 .replace('@@PG58@@', '| G58 主UI池 | %d | %d | %d | %d |' % (pgv(58,'full'), pgv(58,'part'), pgv(58,'aban'), pgv(58,'noneed')))
 .replace('@@PG59@@', '| G59 menu_mp_ui | %d | %d | %d | %d |' % (pgv(59,'full'), pgv(59,'part'), pgv(59,'aban'), pgv(59,'noneed')))
 .replace('@@PG61@@', '| G61 control_labels | %d | %d | %d | %d |' % (pgv(61,'full'), pgv(61,'part'), pgv(61,'aban'), pgv(61,'noneed')))
 .replace('@@PG62@@', '| G62 credits | %d | %d | %d | %d |' % (pgv(62,'full'), pgv(62,'part'), pgv(62,'aban'), pgv(62,'noneed')))
 .replace('@@PG65@@', '| G65 options_ui | %d | %d | %d | %d |' % (pgv(65,'full'), pgv(65,'part'), pgv(65,'aban'), pgv(65,'noneed')))
 .replace('@@F89@@', str(f89)).replace('@@P89@@', str(p89c)).replace('@@A89@@', str(a89c))
 .replace('@@FPR89@@', str(fpr89)).replace('@@PPR89@@', str(ppr89)).replace('@@APR89@@', str(apr89))
 .replace('@@FPR119@@', str(fpr119)).replace('@@APR119@@', str(apr119))
 .replace('@@NONEED@@', str(len(b_entries) - len(need)))
 .replace('@@F119@@', str(f119)).replace('@@P119@@', str(p119)).replace('@@A119@@', str(a119))
 .replace('@@F94@@', str(f94)).replace('@@F124@@', str(f124))
 .replace('@@SET89@@', fmt10(n89))
 .replace('@@NEXT30@@', fmt10(n119[89:]))
 .replace('@@MISSTOP@@', ''.join(ch for ch, _ in b['miss_top30@89']))
 .replace('@@CURVE@@', curve_str)
 .replace('@@K50@@', str(b['k50'])).replace('@@K80@@', str(b['k80'])).replace('@@K90@@', str(b['k90']))
 .replace('@@BTOK@@', '%.1f' % (100.0 * b['tok89'][0] / b['tok89'][1]))
 .replace('@@L1COV@@', '%d/165（32%%）' % cr['l1_cov89_distinct'])
 .replace('@@L1TOK@@', '%.1f' % (100.0 * cr['l1_tok89'][0] / cr['l1_tok89'][1]))
 .replace('@@LAFULL89@@', str(la['full_by_89']))
 .replace('@@LAMISS@@', '　'.join(ch for ch, _ in la['missing_chars']))
 .replace('@@HYBFULL@@', str(hyb_full))
 .replace('@@CEXACT@@', str(c['exact_entries'])).replace('@@CEXACTD@@', str(c['exact_distinct']))
 .replace('@@CUNION@@', str(c['union']))
 .replace('@@COFFTOK@@', '%.1f' % (100.0 * c['official_tok_cov89'][0] / c['official_tok_cov89'][1]))
 .replace('@@SET89FLAT@@', ''.join(n89))
 .replace('@@SETPR@@', fmt10(practical89))
 .replace('@@SETPRFLAT@@', ''.join(practical89))
 .replace('@@NEXTPR@@', fmt10(pr_next30))
 .replace('@@LA32@@', '　'.join(la['distinct_sorted']))
 .replace('@@LAFREQ@@', '、'.join('%s×%d' % (ch, n) for ch, n in la['freq']))
 .replace('@@ABTABLE@@', ab_table)
 .replace('@@AE_N@@', str(len(sac['0xae'])))
 .replace('@@GAIN94@@', '%.1f' % (100.0 * (f94 - f89) / f89))
 .replace('@@F124B@@', str(f124))
)
open(OUT + r'\report.md', 'w', encoding='utf-8').write(rep)
print('report.md written:', len(rep), 'bytes')
print('variants: 89->%d, 94->%d, 119->%d, 124->%d, hybrid89->%d' % (f89, f94, f119, f124, hyb_full))
print('abandon@89:', len(ab89))
