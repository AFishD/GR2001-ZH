# -*- coding: utf-8 -*-
r"""reduce_titles.py — 从 view_xml.csv 里列出「特别收录」条目的中文标题 (item name=)

用途: 复核勋章/条目在**盘上**叫什么名字, 改写时跟盘上叫法保持一致 (不要新造名字)。
只读, 不写盘。
"""
import io
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text', 'GR_ZH109_view_xml.csv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    d = io.open(P, encoding='utf-8-sig', newline='').read()
    pat = re.compile(r'<item name=""([^"]{1,32})""')
    seen = {}
    for m in pat.finditer(d):
        v = m.group(1)
        seen[v] = seen.get(v, 0) + 1
    zh = [v for v in seen if re.search(r'[\u4e00-\u9fff]', v)]
    print('item name= 共 %d 种, 其中含中文的 %d 种:' % (len(seen), len(zh)))
    for v in sorted(zh):
        print('   %-28s x%d' % (v, seen[v]))
    print()
    en = [v for v in seen if not re.search(r'[\u4e00-\u9fff]', v)]
    print('非中文 (%d 种, 前 40): %s' % (len(en), ' | '.join(sorted(en)[:40])))


if __name__ == '__main__':
    main()
