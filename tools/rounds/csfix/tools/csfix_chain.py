# -*- coding: utf-8 -*-
r"""csfix_chain.py —— 只读：把 work\builds\*\build_info.json 的「基底/补丁链」摘出来。

用途：ISO 产物被外部清理后，判断重建 K2/CSFIX 基底是否可行。
"""
import glob
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..'))


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    rows = []
    for p in sorted(glob.glob(os.path.join(REPO, 'work', 'builds', '*', 'build_info.json'))):
        ver = os.path.basename(os.path.dirname(p))
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception as e:                                                # noqa: BLE001
            rows.append((ver, 'PARSE-FAIL %s' % e, '', '', ''))
            continue
        base = d.get('base') or d.get('from') or d.get('base_iso') or ''
        if isinstance(base, dict):
            base = base.get('path') or base.get('name') or str(base)
        base = os.path.basename(str(base)) if base else ''
        pat = d.get('patch') or d.get('patches') or d.get('patch_script') or ''
        if isinstance(pat, list):
            pat = ' + '.join(os.path.basename(str(x)) for x in pat)
        else:
            pat = os.path.basename(str(pat)) if pat else ''
        inj = d.get('inject') or d.get('text_inject') or ''
        if isinstance(inj, list):
            inj = ' + '.join(os.path.basename(str(x)) for x in inj)
        else:
            inj = os.path.basename(str(inj)) if inj else ''
        sha = (d.get('sha256') or d.get('iso_sha256') or '')[:16]
        rows.append((ver, base, pat, inj, sha))
        # 把顶层键名也打出来，便于发现别的字段名
        rows.append(('  keys:%s' % ver, ','.join(sorted(d.keys()))[:400], '', '', ''))
    for r in rows:
        print('%-14s | base=%-22s | patch=%-34s | inject=%-24s | sha=%s'
              % (r[0], r[1], r[2], r[3], r[4]))


if __name__ == '__main__':
    main()
