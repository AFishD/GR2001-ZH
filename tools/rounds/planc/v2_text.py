# -*- coding: utf-8 -*-
r"""v2_text.py — 验证新盘 (GR_ZH93) 上的文本:
  ① 三个文本容器按**新 charset** 解码后, 16 缺字 + 志/略 都真的在盘上;
  ② 每个条目 encode_strict(decode(bytes)) == bytes (字节级往返) —— 证明没有写坏/错位;
  ③ 与现役盘 GR_ZH92 的文本逐条对比: 差异只应出现在用户改过的行 + 的/你 的编码长度变化;
  ④ 统计 0xA1..0xB0 区间里"不该出现"的裸字节 (单字节 lead)。
只读。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import tcslib                                          # noqa: E402

NEW = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
OLD = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
TARGETS = '虽螺衍衣裂誉贡轮迟造钢题额鼓（）'
EXTRA = '志略的你荐'

cs = tcslib.Charset()
print('charset: %d 单字节 + %d 对偶 ; lead 上界 0x%02X'
      % (len(cs.enc_single), len(cs.enc_pair), tcslib.PAIR_LEAD_HI))

iso = tcslib.Iso(NEW)
blobs = {}
for (lba, idx, nm) in ((tcslib.MENU_LBA, 25, 'MENU#25 LANG'),
                       (tcslib.MENU_LBA, tcslib.XML_IDX, 'MENU#283 SFXML'),
                       (tcslib.GR_LBA, 902, 'GR#902 LANG')):
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    blobs[nm] = b''.join(s[0] for s in tcslib.lzo_subs(raw))
    print('%-16s stored=%-7d 展开=%-7d' % (nm, e['stored'], len(blobs[nm])))
iso.close()

print()
print('== ① 16 缺字 (+志略的你荐) 在新盘文本里的出现次数 (按新 charset 解码后统计) ==')
blobs_txt = {}
for nm, blob in blobs.items():
    if nm.endswith('SFXML'):
        items = [(k, body) for (k, off, ln, body) in tcslib.parse_sfxml(blob)]
    else:
        items = [('G%03d.I%03d' % (e.g, e.i), e.data) for e in tcslib.parse_lang(blob)[0]]
    txt = '\n'.join(cs.decode(b)[0] for _k, b in items)
    blobs_txt[nm] = (items, txt)
    print('  %-16s 条目 %d, 解码字符 %d' % (nm, len(items), len(txt)))
alltxt = '\n'.join(t for _i, t in blobs_txt.values())
for grp, name in ((TARGETS, '16 缺字'), (EXTRA, '其它关注')):
    print('  [%s]' % name)
    for ch in grp:
        print('    %s : %d' % (ch, alltxt.count(ch)), end='')
    print()

print()
print('== ② 字节级往返 (decode → encode_strict == 原字节) ==')
tot = bad = 0
for nm, (items, _t) in blobs_txt.items():
    nb = 0
    for (_k, body) in items:
        tot += 1
        t, _mp = cs.decode(body)
        try:
            if cs.encode_strict(t) != body:
                nb += 1
        except Exception:
            nb += 1
    bad += nb
    print('  %-16s 条目 %d, 往返不一致 %d' % (nm, len(items), nb))
print('  合计 %d 条, 不一致 %d  %s' % (tot, bad, '✓' if bad == 0 else '✗'))

print()
print('== ③ 与现役盘 GR_ZH92 的容器差异 (字节级) ==')
iso2 = tcslib.Iso(OLD)
for (lba, idx, nm) in ((tcslib.MENU_LBA, 25, 'MENU#25 LANG'),
                       (tcslib.MENU_LBA, tcslib.XML_IDX, 'MENU#283 SFXML'),
                       (tcslib.GR_LBA, 902, 'GR#902 LANG')):
    e2 = iso2.img_entry(lba, idx)
    old = b''.join(s[0] for s in tcslib.lzo_subs(iso2.read(e2['iso_off'], e2['stored'])))
    new = blobs[nm]
    d = sum(1 for a, b in zip(old, new) if a != b)
    print('  %-16s 现役 %d B → 新 %d B (Δ%d B), 不同字节 %d'
          % (nm, len(old), len(new), len(new) - len(old), d))
iso2.close()

print()
print('== ④ 裸 lead 字节扫描 (0xA1..0xB0 区间里不该有"单字节码") ==')
for nm, blob in blobs.items():
    # 按新语义解析: lead 0xA1..0xB0 + trail 0xA1..0xFE 成对; 剩下的裸 lead 字节 = 异常
    i, n, bare = 0, len(blob), {}
    while i < n:
        v = blob[i]
        if 0xA1 <= v < tcslib.PAIR_LEAD_HI and i + 1 < n and 0xA1 <= blob[i + 1] <= 0xFE:
            i += 2
            continue
        if 0xA1 <= v < tcslib.PAIR_LEAD_HI:
            bare[v] = bare.get(v, 0) + 1
        i += 1
    print('  %-16s 裸 lead 字节: %s' % (nm, {hex(k): v for k, v in sorted(bare.items())} or '{}'))

print()
print('== ⑤ 抽 4 条含新字的文本 (新盘解码) ==')
seen = 0
for nm, (items, _t) in blobs_txt.items():
    for (k, body) in items:
        t, _mp = cs.decode(body)
        if any(c in t for c in TARGETS):
            print('  %s:%s = %s' % (nm, k, t.replace('\n', '\\n')[:120]))
            seen += 1
            if seen >= 4:
                break
    if seen >= 4:
        break
