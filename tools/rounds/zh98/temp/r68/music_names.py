# -*- coding: utf-8 -*-
"""What do the 9 blank 'Music' item names look like in each of the 10 SFXML copies?"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import tcslib as T                                               # noqa: E402
import dump_containers as DC                                     # noqa: E402
import font_usage as FU                                          # noqa: E402
from inject_text_csv import parse_xml_attrs                      # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH111', 'GR_ZH111.iso')
OUT = os.path.join(HERE, 'music_names.txt')
IDX = list(range(45, 54))          # A0045..A0053 (1-based)


def main():
    iso = T.Iso(ISO)
    cs = T.Charset()
    copies = DC.sfxml_copies_of(FU.build_container_list(iso))
    got = []
    for c in copies:
        blob, _raw = FU.container_blob(iso, c['c'])
        got.append((DC.cont_name(c['c']), c['lang'], c['role'], parse_xml_attrs(blob)))
    L = ['== A0045..A0053 (Music items) raw bytes + latin-1 + zh-charset decode ==']
    for k in IDX:
        L.append('A%04d' % k)
        for (name, lang, role, attrs) in got:
            v = attrs[k - 1][3]
            L.append('   %-40s raw=%-34s latin1=%-26r zh=%r'
                     % (name, v.hex(), v.decode('latin-1'), cs.decode(v)[0]))
    # also: the <text> of those items + the sound names, from the zh-main copy
    blob, _raw = FU.container_blob(iso, [c['c'] for c in copies if c['role'] == 'zh-main'][0])
    off = parse_xml_attrs(blob)[44][2]
    seg = blob[off - 40:off + 1500].decode('latin-1')
    L.append('')
    L.append('== zh-main raw window (latin-1) ==')
    L.append(seg)
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('wrote', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
