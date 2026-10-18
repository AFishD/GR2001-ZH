# -*- coding: utf-8 -*-
r"""r58 探针1: GR_ZH107 里那批"含中文"容器到底处于哪个码表状态 (只读)。

GR_ZH105/106 的 ISO 已被删掉 (只留 GR_ZH107), 所以只能拿两个 charset 快照去解 GR_ZH107:
  旧 = work/builds/GR_ZH98/temp/r56/charset_before_r56.json   (r56 紧凑前)
  新 = tools/font_pipeline/data/charset_compiled_zh16.json     (现役 = r56 紧凑后)
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

CS_OLD = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
CS_NEW = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
ISO107 = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')

TARGETS = [
    ('GR.IMG', 907, 'FR_STRINGS.RES'), ('MENU.IMG', 28, 'MENU FR_STRINGS.RES'),
    ('GR.IMG', 904, 'ES_STRINGS.RES'), ('MENU.IMG', 27, 'MENU ES_STRINGS.RES'),
    ('GR.IMG', 900, 'DE_STRINGS.RES'), ('MENU.IMG', 26, 'MENU DE_STRINGS.RES'),
    ('GR.IMG', 910, 'IT_STRINGS.RES'), ('MENU.IMG', 29, 'MENU IT_STRINGS.RES'),
    ('GR.IMG', 4059, 'ES_SPECIAL_FEATURE.XML'), ('MENU.IMG', 285, 'MENU ES_SF.XML'),
    ('GR.IMG', 4061, 'FR_SPECIAL_FEATURE.XML'), ('MENU.IMG', 286, 'MENU FR_SF.XML'),
    ('GR.IMG', 4057, 'DE_SPECIAL_FEATURE.XML'), ('MENU.IMG', 284, 'MENU DE_SF.XML'),
    ('GR.IMG', 908, 'FR_STRINGS.TXT'), ('MENU.IMG', 33, 'MENU FR_STRINGS.TXT'),
    ('GR.IMG', 905, 'ES_STRINGS.TXT'), ('MENU.IMG', 32, 'MENU ES_STRINGS.TXT'),
    ('GR.IMG', 4062, 'IGORHELP.TXT'),
    ('MENU.IMG', 25, 'EN_STRINGS.RES(menu)'), ('GR.IMG', 902, 'EN_STRINGS.RES(gr)'),
    ('MENU.IMG', 283, 'EN_SPECIAL_FEATURE.XML'),
]

old = tcslib.Charset(CS_OLD)
new = tcslib.Charset(CS_NEW)
iso = tcslib.Iso(ISO107)
CJK = re.compile(r'[\u4e00-\u9fff]{2,}')


def find(tag, idx):
    lba = FC.MENU_LBA if tag == 'MENU.IMG' else FC.GR_LBA
    return FC.Slot(iso, tag, lba, idx)


def stats(cs, blob):
    t, mp = cs.decode(blob)
    runs, cur = [], 0
    for ch in t:
        if '\u4e00' <= ch <= '\u9fff':
            cur += 1
        else:
            if cur >= 2:
                runs.append(cur)
            cur = 0
    if cur >= 2:
        runs.append(cur)
    return dict(n_cjk=sum(1 for ch in t if '\u4e00' <= ch <= '\u9fff'),
                runs_ge2=len(runs), best_run=max(runs) if runs else 0, text=t, mp=mp)


print('%-30s %-9s %-6s | %-24s | %-24s' %
      ('container', 'mode', 'blob', '旧码表解 (CJK/段/最长)', '新码表解 (CJK/段/最长)'))
rows = []
for (tag, idx, nm) in TARGETS:
    s = find(tag, idx)
    a, b = stats(old, s.blob), stats(new, s.blob)
    rows.append((tag, idx, nm, s, a, b))
    print('%-30s %-9s %-6d | %6d %4d %6d      | %6d %4d %6d' %
          ('%s#%d %s' % (tag, idx, nm), s.mode, len(s.blob),
           a['n_cjk'], a['runs_ge2'], a['best_run'], b['n_cjk'], b['runs_ge2'], b['best_run']))

print('\n=== 样例: 前 3 段 >=2 连续汉字 (新解语境 + 原始字节) ===')
for (tag, idx, nm, s, a, b) in rows:
    hits = list(CJK.finditer(b['text']))[:3]
    print('\n--- %s#%d %s  (展开 %d B, mode=%s) ---' % (tag, idx, nm, len(s.blob), s.mode))
    for m in hits:
        lo, hi = max(0, m.start() - 30), min(len(b['text']), m.end() + 30)
        print('   新解 %r' % b['text'][lo:hi])
        print('   旧解 %r' % a['text'][lo:hi])
        i0 = b['mp'][m.start()]
        i1 = b['mp'][m.end()] if m.end() < len(b['mp']) else len(s.blob)
        print('   raw  %s' % s.blob[max(0, i0 - 10):i1 + 10].hex(' '))
    hits_o = list(CJK.finditer(a['text']))[:3]
    if not hits_o:
        continue
    print('   (旧解里的前 3 段)')
    for m in hits_o:
        lo, hi = max(0, m.start() - 30), min(len(a['text']), m.end() + 30)
        print('   旧解 %r' % a['text'][lo:hi])
        print('   新解 %r' % b['text'][lo:hi])
iso.close()
