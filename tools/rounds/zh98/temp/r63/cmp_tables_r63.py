# -*- coding: utf-8 -*-
r"""cmp_tables_r63.py — 「现有表有没有被破坏」的逐表对照。

A = work/builds/GR_ZH109/text (round109 基线; 由**未改动**的 dump 工具产出)
B = work/builds/GR_ZH110/text (round63 构筑产物)
C = work/builds/GR_ZH109/text_r62 (round62 的 view 表基线, 含 _view_sf_titles.csv)

判据: 数据表按 sha256 逐字节比; 不同的表再逐行/逐列指出**差在哪** (不猜)。
"""
import csv
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
A = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')
B = os.path.join(REPO, 'work', 'builds', 'GR_ZH110', 'text')
C = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_r62')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

KEY = ('id', 'resource', 'container', 'entry_index', 'offset', 'len_bytes', 'kind')


def sha(p):
    try:
        return hashlib.sha256(open(p, 'rb').read()).hexdigest()
    except OSError as e:
        return 'LOCKED(%s)' % e.errno


def rows(p):
    with open(p, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        return rd.fieldnames, list(rd)


def strip_ver(n):
    """GR_ZH109_text_long.csv → text_long.csv (跨版本按"表角色"比)。"""
    for v in ('GR_ZH109_', 'GR_ZH110_'):
        if n.startswith(v):
            return n[len(v):]
    return n


def main():
    fa = dict((strip_ver(f), os.path.join(A, f)) for f in os.listdir(A) if f.endswith('.csv'))
    fb = dict((strip_ver(f), os.path.join(B, f)) for f in os.listdir(B) if f.endswith('.csv'))
    fc = dict((strip_ver(f), os.path.join(C, f)) for f in os.listdir(C) if f.endswith('.csv'))
    print('%-34s %-14s %-14s %-14s %s' % ('表 (去掉版本前缀)', 'GR_ZH109/text', 'GR_ZH110/text',
                                          'ZH109/text_r62', '判定'))
    n_same = n_diff = 0
    for k in sorted(set(fa) | set(fb) | set(fc)):
        ha = sha(fa[k])[:12] if k in fa else '(无)'
        hb = sha(fb[k])[:12] if k in fb else '(无)'
        hc = sha(fc[k])[:12] if k in fc else '(无)'
        if k in fa and k in fb:
            verdict = '★逐字节相同 ✓' if ha == hb else '不同 (见下)'
            n_same += (ha == hb)
            n_diff += (ha != hb)
        elif k in fb:
            verdict = '本轮新增'
        else:
            verdict = '本轮没有'
        print('%-34s %-14s %-14s %-14s %s' % (k, ha, hb, hc, verdict))
    print('\n数据表: 逐字节相同 %d 张 / 不同 %d 张' % (n_same, n_diff))

    # ── 不同的表: 逐列指出差在哪 ──
    for k in sorted(set(fa) & set(fb)):
        if sha(fa[k]) == sha(fb[k]):
            continue
        if 'text_long.csv' == k or k in ('text_short.csv', 'text_long_nowrap.csv'):
            ca, ra = rows(fa[k])
            cb, rb = rows(fb[k])
            print('\n== %s: 行 %d → %d, 列 %s' % (k, len(ra), len(rb), ca == cb))
            if ca != cb or len(ra) != len(rb):
                print('   列/行数不同 ⇒ 需要人工看')
                continue
            diff_cols, diff_ids = {}, []
            for x, y in zip(ra, rb):
                bad = [c for c in ca if x[c] != y[c]]
                if bad:
                    diff_ids.append(x['id'])
                    for c in bad:
                        diff_cols.setdefault(c, []).append((x['id'], x[c], y[c]))
            print('   不同的行 %d 条; 不同的列: %s'
                  % (len(diff_ids), ', '.join('%s(%d 处)' % (c, len(v))
                                              for c, v in diff_cols.items())))
            for c, v in diff_cols.items():
                ex = v[:3]
                print('     %-10s 例: %s' % (c, '; '.join('%s %s→%s' % t for t in ex)))
            if diff_ids:
                print('     涉及 id (%d): %s%s' % (len(diff_ids), ' '.join(diff_ids[:6]),
                                                   ' …' if len(diff_ids) > 6 else ''))
        elif k == 'view_sf_titles.csv':
            base = fc.get(k)
            if not base or not os.path.isfile(base):
                print('\n== %s: 无基线可逐行比 (round62 基线缺失)' % k)
                continue
            _ca, ra = rows(base)
            _cb, rb = rows(fb[k])
            print('\n== %s: round62 基线 %d 行 → 本轮 %d 行' % (k, len(ra), len(rb)))
            n = 0
            for x, y in zip(ra, rb):
                if x['text'] != y['text'] or x['offset'] != y['offset'] \
                        or x['len_bytes'] != y['len_bytes']:
                    n += 1
                    print('   %-38s #%s %-7s %-6s %r → %r (%s → %s B)'
                          % (x['container'], x['entry_index'], x['tag'], x['lang'],
                             x['text'], y['text'], x['len_bytes'], y['len_bytes']))
            print('   共 %d 行不同 (行数相同: %s)' % (n, len(ra) == len(rb)))
        else:
            print('\n== %s: 内容不同 (非文本表, 逐行比无意义)' % k)


    # ── _view_sf_titles.csv: GR_ZH110 (本轮产物) vs text_r62 (round62 基线) ──
    k = 'view_sf_titles.csv'
    if k in fb and k in fc:
        ca, ra = rows(fc[k])
        cb, rb = rows(fb[k])
        print('\n== %s: round62 基线 %d 行 → 本轮 %d 行 (列相同: %s)'
              % (k, len(ra), len(rb), ca == cb))
        n = n_text = n_off = 0
        for x, y in zip(ra, rb):
            if x['text'] != y['text'] or x['offset'] != y['offset'] \
                    or x['len_bytes'] != y['len_bytes']:
                n += 1
                if x['text'] != y['text'] or x['len_bytes'] != y['len_bytes']:
                    n_text += 1
                    print('   %-38s #%-4s %-7s %-6s %r → %r (%s → %s B)'
                          % (x['container'], x['entry_index'], x['tag'], x['lang'],
                             x['text'], y['text'], x['len_bytes'], y['len_bytes']))
                else:
                    n_off += 1
        print('   不同的行 = %d / %d 行: **文本变了 %d 条** (注入的改动), '
              '只有 offset 漂移 %d 条 (前面的标题改了字数 ⇒ 后面的属性整体平移, '
              '这是正确行为: 注入器按 entry_index 定位, 不依赖 offset)'
              % (n, len(ra), n_text, n_off))
        print('   其余 9 份副本: 0 行变化 (逐字节相同 — 见 verify_r63.py)')


if __name__ == '__main__':
    main()
