# -*- coding: utf-8 -*-
r"""probe8.py — 交叉验证: E0 结构化解析 vs CSV text_zh, 到底差在哪"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import font_usage as F  # noqa: E402
import tcslib as T     # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
idx = F.CharsetIndex()
iso = T.Iso(ISO)

# E0 逐份
for c in F.build_container_list(iso):
    if c['kind'] in ('LANG', 'SFXML'):
        blob, _ = F.container_blob(iso, c)
        if c['kind'] == 'LANG':
            chars, note = F.parse_lang_chars(blob, idx)
            ents, used_end = T.parse_lang(blob)
            print('%s #%d blob=%d  %s' % (c['img'], c['idx'], len(blob), note))
            print('   parse_lang: ngroups=%d entries=%d used_end=%d' %
                  (ents[-1].g + 1 if ents else 0, len(ents), used_end))
            print('   E0 字 %d (其中非 ASCII %d)'
                  % (len(chars), len([x for x in chars if ord(x) >= 0x80])))
            empt = sum(1 for e in ents if not e.data)
            print('   空正文条目 %d 个' % empt)
        else:
            chars, note = F.parse_sfxml_chars(blob, idx)
            print('%s #%d blob=%d  %s' % (c['img'], c['idx'], len(blob), note))
            print('   E0 字 %d (其中非 ASCII %d)'
                  % (len(chars), len([x for x in chars if ord(x) >= 0x80])))

# CSV 侧
rows, files, notes = F.read_text_tables(os.path.join(REPO, 'work/builds/GR_ZH92/text'))
print('\nCSV: %d 张表 / %d 行' % (len(files), len(rows)))
per_res = {}
for r in rows:
    per_res[r['file']] = per_res.get(r['file'], 0) + 1
for k, v in per_res.items():
    print('   %-32s %d 行' % (k, v))
cur = set()
for r in rows:
    cur |= r['cur']
print('CSV text_zh 合计 %d 个不同字符 (非 ASCII %d)'
      % (len(cur), len([c for c in cur if ord(c) >= 0x80])))

# 逐字对比
e0 = set()
for c in F.build_container_list(iso):
    if c['kind'] in ('LANG', 'SFXML'):
        blob, _ = F.container_blob(iso, c)
        got = (F.parse_lang_chars(blob, idx) if c['kind'] == 'LANG'
               else F.parse_sfxml_chars(blob, idx))[0]
        if got:
            e0 |= got
font = set(idx.chars)
print('\nE0 合计 %d 字符; 其中在字库里 %d; 不在字库里 %d'
      % (len(e0), len(e0 & font), len(e0 - font)))
print('CSV text_zh 合计 %d; 其中在字库里 %d'
      % (len(cur), len(cur & font)))
print('字库 %d; 字库内 E0 用到的 %d ⇒ E0口径闲置 %d'
      % (len(font), len(font & e0), len(font - e0)))
print('字库内 CSV 用到的 %d ⇒ CSV口径闲置 %d' % (len(font & cur), len(font - cur)))
oe = sorted(font & e0 - cur)
oc = sorted(font & cur - e0)
print('\n只在 E0 不在 CSV 的字库字: %d 个' % len(oe))
print('   ', ''.join(oe[:200]))
print('只在 CSV 不在 E0 的字库字: %d 个' % len(oc))
print('   ', ''.join(oc[:200]))
# 这些"只在 E0"的字出现在哪些条目里?
cnt = {}
for c in F.build_container_list(iso):
    if c['kind'] != 'LANG':
        continue
    blob, _ = F.container_blob(iso, c)
    ents, _ = T.parse_lang(blob)
    for e in ents:
        s = set(idx.decode_chars(e.data))
        for ch in s & set(oe):
            cnt.setdefault(ch, []).append('G%03d.I%03d' % (e.g + 1, e.i))
for ch in sorted(cnt)[:30]:
    print('   %s ← %s' % (ch, ', '.join(cnt[ch][:3])))
iso.close()
