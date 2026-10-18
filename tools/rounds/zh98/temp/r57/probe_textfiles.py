# -*- coding: utf-8 -*-
r"""r57 探针5: MENU.IMG#30 EN_STRINGS.TXT 这类"文本文件容器"里, 换码后有没有变味的行? (只读)"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_before_r56.json'))
new = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_after_r56.json'))
iso = tcslib.Iso(ISO)
LINE = re.compile(rb'"[^"\r\n]{1,80}"')
tot_lines = tot_bad = 0
bad_containers = []
for (tag, lba, idx, e) in FC.enumerate_containers(iso):
    if e['name'].upper().endswith(('.TXT', '.XML', '.CONFIG', '.SDF', '.MIS')) or \
            e['name'].upper() in ('Q.SAV',):
        slot = FC.Slot(iso, tag, lba, idx)
        blob = slot.blob
        if not blob:
            continue
        lines = LINE.findall(blob)
        nbad = 0
        for ln in lines:
            a = old.decode(ln)[0]
            b = new.decode(ln)[0]
            if a != b:
                nbad += 1
                if nbad <= 4:
                    print('   ✗ %s#%d %s  %s  旧=%r 新=%r'
                          % (tag, idx, e['name'], ln[:40], a[:34], b[:34]))
        tot_lines += len(lines)
        tot_bad += nbad
        if nbad:
            bad_containers.append(('%s#%d %s' % (tag, idx, e['name']), len(lines), nbad))
print('\n文本类容器: 引号串 %d 条, 换码后**文本变了**的 %d 条' % (tot_lines, tot_bad))
for (nm, n, nb) in sorted(bad_containers, key=lambda x: -x[2])[:20]:
    print('   %-34s 串 %-6d 变了 %d' % (nm, n, nb))
iso.close()
