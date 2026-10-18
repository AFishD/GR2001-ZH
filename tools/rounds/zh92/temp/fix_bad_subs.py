# -*- coding: utf-8 -*-
r"""fix_bad_subs.py — 修掉扩库代理那 4 处"机械换字"造成的坏词 (用字库里确实存在的字)"""
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'text_fix', 'GR_ZH92_text_long.csv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FIXES = [
    ('SFXML:T0012', '外壳碎破化作大量杀伤破片', '外壳破碎化作大量杀伤破片'),
    ('SFXML:T0028', '使射击声音更加微弱。{Warp}但牺牲部分威力以换取静音',
                     '使射击声音更加微弱。{Warp}牺牲部分威力以换取静音'),
    ('SFXML:T0032', '标标特征是配备了旋转弹筒', '主要特征是配备了旋转弹筒'),
    ('SFXML:T0034', '因存在诸多可靠性与结构脆弱问处', '因存在诸多可靠性与结构脆弱等缺陷'),
]


def main():
    cs = json.load(io.open(CS, encoding='utf-8'))
    font = set(cs['codes']) | set(cs['pair_of'])
    rows = list(csv.DictReader(io.open(P, encoding='utf-8-sig')))
    cols = list(rows[0].keys())
    idx = {r['id']: r for r in rows}
    ok = True
    for rid, old, new in FIXES:
        r = idx.get(rid)
        if r is None:
            print('[!!] 找不到 %s' % rid)
            ok = False
            continue
        if old not in r['text_edited']:
            print('[!!] %s 里找不到片段: %s' % (rid, old[:30]))
            ok = False
            continue
        # 校验新片段里每个非 ASCII 字都在字库里
        bad = [c for c in new if ord(c) >= 0x80 and c not in font]
        if bad:
            print('[!!] %s 的替代文字含字库没有的字: %s' % (rid, ''.join(bad)))
            ok = False
            continue
        r['text_edited'] = r['text_edited'].replace(old, new)
        print('[ok] %s: %s → %s' % (rid, old[-12:], new[-12:]))
    if not ok:
        print('\n有未通过项, **未写文件**')
        sys.exit(1)
    with io.open(P, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n', quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    print('\n已写回 %s' % os.path.relpath(P, REPO))
    # 复核
    rows2 = list(csv.DictReader(io.open(P, encoding='utf-8-sig')))
    need = set()
    import re
    WRAP = re.compile(r'\{\s*(?:WRAP|WARP)\s*\}', re.I)
    for r in rows2:
        for c in WRAP.sub('', r['text_edited']):
            if ord(c) >= 0x80 and c not in font:
                need.add(c)
    print('复核: 替代稿里仍缺字 %d 个 %s' % (len(need), ''.join(sorted(need)) or '(无 ✓)'))


if __name__ == '__main__':
    main()
