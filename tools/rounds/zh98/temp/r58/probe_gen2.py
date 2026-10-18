# -*- coding: utf-8 -*-
r"""r58 探针5: 每个候选容器的字节到底是**哪一代** charset 写下的?

代际 (从盘上的实证):
  G0 = round46 第一次紧凑重排**之前** (GR_ZH94 一带; 例: work/builds/GR_ZH94/temp/r46/charset_before_repack.json)
  G1 = round46 之后 .. round56 之前  (work/builds/GR_ZH98/temp/r56/charset_before_r56.json)
  G2 = round56 之后 = **现役**       (tools/font_pipeline/data/charset_compiled_zh16.json)
对每个容器, 用三代各解一遍, 打印关键片段 + PUA/未映射计数 + 汉字数, 看哪一代是人话。
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

GENS = [
    ('G0', os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46',
                        'charset_before_repack.json')),
    ('G0b', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'font',
                         'charset_matching_this_disk.json')),
    ('G1', os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                        'charset_before_r56.json')),
    ('G2', os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')),
]
CS = [(n, tcslib.Charset(p)) for (n, p) in GENS if os.path.isfile(p)]

ISO107 = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')
TARGETS = [
    ('MENU.IMG', 30, 'EN_STRINGS.TXT'), ('GR.IMG', 906, 'GR EN_STRINGS.TXT'),
    ('GR.IMG', 908, 'FR_STRINGS.TXT'), ('GR.IMG', 905, 'ES_STRINGS.TXT'),
    ('MENU.IMG', 33, 'MENU FR_STRINGS.TXT'), ('MENU.IMG', 32, 'MENU ES_STRINGS.TXT'),
    ('GR.IMG', 4062, 'IGORHELP.TXT'),
    ('GR.IMG', 900, 'DE_STRINGS.RES'), ('GR.IMG', 904, 'ES_STRINGS.RES'),
    ('GR.IMG', 907, 'FR_STRINGS.RES'), ('GR.IMG', 910, 'IT_STRINGS.RES'),
    ('GR.IMG', 4057, 'DE_SF.XML'), ('GR.IMG', 4059, 'ES_SF.XML'), ('GR.IMG', 4061, 'FR_SF.XML'),
]
ANCHORS = {
    'MENU.IMG#30': [r'WPN_EXTRAAMMO', r'ITM_BINOCULARS', r'ITM_SENSOR', r'Pistols Only'],
    'GR.IMG#906': [r'ITM_SENSOR', r'Pistols Only'],
    'GR.IMG#908': [r'[\u4e00-\u9fff]{1,}'],
    'GR.IMG#905': [r'[\u4e00-\u9fff]{1,}'],
    'MENU.IMG#33': [r'[\u4e00-\u9fff]{1,}'],
    'MENU.IMG#32': [r'[\u4e00-\u9fff]{1,}'],
    'GR.IMG#4062': [r'[\u4e00-\u9fff]{1,}'],
    'GR.IMG#900': [r'Hauptmen', r'Gr[\u4e00-\u9fff]{1,}'],
    'GR.IMG#904': [r'Men[\u4e00-\u9fff]{1,} Principal'],
    'GR.IMG#907': [r'th[\u4e00-\u9fff]{1,}tre', r'termin[\u4e00-\u9fff]{0,2}e'],
    'GR.IMG#910': [r'[\u4e00-\u9fff]{2,}'],
    'GR.IMG#4057': [r'Vergr[\u4e00-\u9fff]{1,}erung'],
    'GR.IMG#4059': [r'[\u4e00-\u9fff]{2,}'],
    'GR.IMG#4061': [r'd[\u4e00-\u9fff]{1,}sesp'],
}
PUA = re.compile(r'[\ue000-\uf8ff]')

iso = tcslib.Iso(ISO107)
for (tag, idx, nm) in TARGETS:
    lba = FC.MENU_LBA if tag == 'MENU.IMG' else FC.GR_LBA
    blob = FC.Slot(iso, tag, lba, idx).blob
    key = '%s#%d' % (tag, idx)
    print('\n=== %s#%d %s (展开 %d B) ===' % (tag, idx, nm, len(blob)))
    for (gname, cs) in CS:
        t, _ = cs.decode(blob)
        npua = len(PUA.findall(t))
        ncjk = sum(1 for ch in t if '\u4e00' <= ch <= '\u9fff')
        ex = []
        for a in ANCHORS.get(key, []):
            m = re.search(a, t)
            if m:
                ex.append(repr(t[max(0, m.start() - 12):m.end() + 14]))
        print('   %-4s 汉字%5d 未映射%4d | %s' % (gname, ncjk, npua, '  ||  '.join(ex[:4])))
iso.close()
