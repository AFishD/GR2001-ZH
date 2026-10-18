# -*- coding: utf-8 -*-
r"""r62_recon_titles.py — 查"特别收录条目名"是否被 dump 漏扫

用户: 在 CSV 里搜「国会荣誉勋章」只搜到正文、没有标题 ⇒ 怀疑脚本漏扫了标题。
标题存在 SFXML 的 <item name="..."> / <group name="..."> / <studio name="..."> 属性里。
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')

c = json.load(io.open(CS, encoding='utf-8'))
M = {}
for ch, (b1, b2) in c['pair_of'].items():
    M[(b1, b2)] = ch
for ch, bb in c['codes'].items():
    if isinstance(bb, list):
        M[(bb[0], bb[1])] = ch
    else:
        M[('S', bb)] = ch


def dec(b):
    out = []
    i = 0
    while i < len(b):
        x = b[i]
        if x < 0x80:
            out.append(chr(x)); i += 1
        elif ('S', x) in M:
            out.append(M[('S', x)]); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in M:
            out.append(M[(b[i], b[i + 1])]); i += 2
        else:
            out.append('\u00b7'); i += 1
    return ''.join(out)


# ── 1. 从盘上取出所有中文属性名 ──────────────────────────────────────
iso = tcslib.Iso(ISO)
spec = tcslib.RES['SFXML']['copies'][0]
e = iso.img_entry(spec[1], spec[2])
blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(e['iso_off'], e['stored'])))
xml = dec(blob)

titles = []
for m in re.finditer(r'<(item|group|studio)\b[^>]*?name="([^"]*)"', xml):
    nm = m.group(2)
    if re.search(r'[\u4e00-\u9fff]', nm):
        titles.append((m.group(1), nm))
print('=== SFXML 里含中文的属性名: %d 个 ===' % len(titles))
for tag, nm in titles[:20]:
    print('   <%s name="%s">' % (tag, nm))
print('   ...' if len(titles) > 20 else '')
print()

# ── 2. 在全部 CSV 里搜这些标题 ───────────────────────────────────────
csvs = sorted(f for f in os.listdir(TXT) if f.endswith('.csv'))
print('=== 在 %d 个 CSV 里搜这些标题 ===' % len(csvs))
blob_all = {}
for f in csvs:
    try:
        blob_all[f] = io.open(os.path.join(TXT, f), encoding='utf-8-sig', errors='replace').read()
    except Exception as ex:
        print('   读不了 %s: %s' % (f, ex))
hit_total = 0
for tag, nm in titles:
    who = [f for f, t in blob_all.items() if nm in t]
    if who:
        hit_total += 1
    else:
        if len(titles) <= 30 or nm in ('国会最高勋章', '优异服役十字勋章', '何为幽灵？'):
            print('   ✗ 搜不到: <%s name="%s">' % (tag, nm))
print('   ⇒ %d / %d 个属性名能在某个 CSV 里搜到' % (hit_total, len(titles)))
print()

# ── 3. 用户点名的两个串 ─────────────────────────────────────────────
print('=== 用户点名的串 ===')
for w in ('国会荣誉勋章', '国会最高勋章', '优异服役十字勋章', '何为幽灵'):
    who = [f for f, t in blob_all.items() if w in t]
    print('   「%s」: %s' % (w, ('出现在 ' + ', '.join(who)) if who else '**所有 CSV 都搜不到**'))
