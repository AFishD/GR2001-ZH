# -*- coding: utf-8 -*-
"""Evidence for the studio-name question (all 10 SFXML copies) on GR_ZH111."""
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
OUT = os.path.join(HERE, 'studio_evidence.txt')


def main():
    iso = T.Iso(ISO)
    cs = T.Charset()
    conts = FU.build_container_list(iso)
    copies = DC.sfxml_copies_of(conts)
    got = []
    for c in copies:
        blob, _raw = FU.container_blob(iso, c['c'])
        attrs = parse_xml_attrs(blob)
        got.append((DC.cont_name(c['c']), c['lang'], c['role'], c['c']['stored'],
                    len(blob), attrs))
    L = []
    L.append('copies=%d  attr counts=%s' % (len(got), [len(g[5]) for g in got]))
    tgt = [g for g in got if g[2] == 'zh-main'][0]
    ref = tgt[5]
    L.append('')
    L.append('== per-copy diff vs %s (attr values, charset-decoded) ==' % tgt[0])
    for g in got:
        if len(g[5]) != len(ref):
            L.append('%-40s ATTRIBUTE COUNT MISMATCH' % g[0])
            continue
        diff = [i for i in range(len(ref)) if g[5][i][3] != ref[i][3]]
        L.append('%-40s lang=%-3s role=%-9s stored=%-6d blob=%-7d diff_attrs=%-4d %s'
                 % (g[0], g[1], g[2], g[3], g[4], len(diff),
                    [cs.decode(ref[i][3])[0] for i in diff[:4]]))
    L.append('')
    L.append('== per-row: identical across all 10 copies? (grouped by tag) ==')
    stat = {}
    rows_same = []
    for i in range(len(ref)):
        vals = set(g[5][i][3] for g in got)
        tag = ref[i][1]
        stat.setdefault(tag, [0, 0])
        stat[tag][0] += 1
        if len(vals) == 1:
            stat[tag][1] += 1
            rows_same.append((i + 1, tag, vals.pop()))
    for tag in sorted(stat):
        L.append('  %-8s total=%-4d identical_across_10=%-4d' % (tag, stat[tag][0], stat[tag][1]))
    L.append('')
    L.append('== rows identical across all 10 copies ==')
    for (k, tag, v) in rows_same:
        L.append('  A%04d %-8s %r' % (k, tag, cs.decode(v)[0]))
    L.append('')
    L.append('== the 10 studio names, per copy ==')
    for i in range(len(ref)):
        if ref[i][1] != 'studio':
            continue
        vals = [cs.decode(g[5][i][3])[0] for g in got]
        L.append('A%04d identical=%-5s %s' % (i + 1, len(set(vals)) == 1, vals[0]))
        for n, v in enumerate(vals):
            L.append('        %-40s %r' % (got[n][0], v))
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('wrote', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
