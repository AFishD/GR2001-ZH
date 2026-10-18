# -*- coding: utf-8 -*-
"""txt_xmlview.py —— 看 EN/中文 EN_SPECIAL_FEATURE.XML 的真实结构（只读）。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

ISOS = (('EN_TRUE', r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"),
        ('CVAR04', r"work\builds\GR_CVAR\CVAR_04_text.iso"))


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for tag, rel in ISOS:
        iso = T.Iso(os.path.join(ROOT, rel))
        e = iso.img_entry(T.MENU_LBA, 283)
        raw = iso.read(e['iso_off'], e['stored'])
        blob = b''.join(s[0] for s in T.lzo_subs(raw))
        print('=' * 78)
        print('%s  %s  blob=%d  used=%d' % (tag, 'EN_SPECIAL_FEATURE.XML',
                                            len(blob), T.xml_tail_start(blob)))
        print('  头 320 B:')
        print('   ', blob[:320].decode('latin-1'))
        tags = {}
        for m in re.finditer(rb'<(\w+)([^>]*)>', blob):
            tags[m.group(1).decode('latin-1')] = tags.get(m.group(1).decode('latin-1'), 0) + 1
        print('  开标签统计: %s' % sorted(tags.items(), key=lambda kv: -kv[1])[:14])
        for pat in (rb'<text>([^<]*)</text>', rb'<text\s[^>]*>([^<]*)</text>',
                    rb'name="([^"]*)"'):
            n = len(re.findall(pat, blob))
            print('  %-34s 命中 %d' % (pat.decode('latin-1'), n))
        # 所有 "成对 >X<" 的文本节点（dump_all_text 的 RE_NODE 口径近似）
        nodes = [m for m in re.finditer(rb'>([^<>]{2,400})<', blob)
                 if m.group(1).strip()]
        print('  RE_NODE 口径 (>..<, 2..400B) 命中 %d' % len(nodes))
        big = [m for m in re.finditer(rb'>([^<>]{401,})<', blob)]
        print('  >400B 正文节点 %d 处, 最长 %d B'
              % (len(big), max([len(m.group(1)) for m in big] or [0])))
        iso.close()


if __name__ == '__main__':
    main()
