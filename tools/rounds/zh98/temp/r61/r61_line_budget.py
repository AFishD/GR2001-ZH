# -*- coding: utf-8 -*-
r"""r61_line_budget.py — 检验"引擎行数上限"假设: 测试页是不是**唯一**超过某个行数的页面?

背景: 测试页 = 1285 字铺进「开发访谈 1」, 用引擎折行模型 (wrap_w=270) 折出 ~131 个视觉行。
      若已交付的**所有**页面都远低于某个整数阈值 (如 128), 而测试页刚好越过它,
      那就是"整页空白"的一个可检验解释 (固定长度行数组溢出 ⇒ 整段不画)。

用法: python work/builds/GR_ZH98/temp/r61/r61_line_budget.py
"""
import csv
import glob
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402


def vlines(t, w=270):
    n = 0
    for (_s, _e, seg) in T.segments(t):
        n += len(T.wrap_seg(seg, w)) if seg else 1
    return n


def rows_of(ver):
    out = []
    for p in sorted(glob.glob(os.path.join(REPO, 'work', 'builds', ver, 'text',
                                           '%s_text_*.csv' % ver))):
        if '_view_' in p:
            continue
        with io.open(p, encoding='utf-8-sig', newline='') as fh:
            for r in csv.DictReader(fh):
                r['_f'] = os.path.basename(p)
                out.append(r)
    return out


def find(ver, rid):
    for r in rows_of(ver):
        if r.get('id') == rid:
            return r
    return None


ref = rows_of('GR_ZH109')
print('GR_ZH109 文本条目 = %d' % len(ref))
sf = [(vlines(r.get('text_edited') or ''), r.get('id'), len(r.get('text_edited') or ''))
      for r in ref if r.get('resource') == 'SFXML']
sf.sort(reverse=True)
print('\nGR_ZH109 SFXML 条目按引擎视觉行数 (wrap_w=270) 降序, 前 12:')
for n, i, l in sf[:12]:
    print('   %4d 行  %-14s %d 字' % (n, i, l))
allr = [(vlines(r.get('text_edited') or ''), r.get('id'), r.get('resource'))
        for r in ref if r.get('text_edited')]
allr.sort(reverse=True)
print('\nGR_ZH109 全部条目降序 前 8:')
for n, i, res in allr[:8]:
    print('   %4d 行  %-14s %s' % (n, i, res))

r_old = find('GR_ZH109', 'SFXML:T0067')
r_new = find('GR_TEST_FONT2', 'SFXML:T0067')
print('\n「开发访谈 1」(SFXML:T0067):')
for tag, r in (('GR_ZH109 原版 ', r_old), ('GR_TEST_FONT2 测试页', r_new)):
    t = (r.get('text_edited') or '') if r else ''
    print('   %-22s 引擎视觉行 = %4d  CSV lines 字段 = %-5s 字符 = %d  B = %s'
          % (tag, vlines(t), r.get('lines') if r else '-', len(t), r.get('len_bytes') if r else '-'))

print('\n各整数阈值上方的条目数 (GR_ZH109, 仅 text_edited 非空):')
for th in (32, 64, 96, 100, 110, 120, 128, 131, 140, 160, 200):
    n = sum(1 for v, _i, _r in allr if v > th)
    print('   > %3d 行: %d 条' % (th, n))
print('\n★ 若 "> 128 行" 在 GR_ZH109 里是 0 条, 而测试页是 %d 行, 则该假设成立。' % vlines(
    (r_new.get('text_edited') or '') if r_new else ''))
