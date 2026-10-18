# -*- coding: utf-8 -*-
r"""phase_table.py -- 从 POST_SUMMARY.json 里抽 bands.py 的 8 个游戏阶段，按批算"相对同批 EN 的比值"。
用来回答"数据侧的成本落在哪些阶段"（决定机制：是每帧固定开销，还是随文字工作量增长）。"""
import io
import json
import os
import sys

BIS = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_FPSBISECT'
KEY = ['EN_ORIG', 'HK00_base', 'CVAR01_elf', 'CVAR02_atlas', 'CVAR04_text', 'CVAR05_elf_atlas',
       'TXT02_no_text', 'HK01_all']


def main():
    with io.open(os.path.join(BIS, 'POST_SUMMARY.json'), encoding='utf-8') as f:
        S = json.load(f)
    with io.open(os.path.join(BIS, 'ARM_TABLE.json'), encoding='utf-8') as f:
        T = json.load(f)
    meta = {r['name']: r for r in T['arms']}

    # 批次 -> 该批的 EN 基准
    en = {}
    for name, r in meta.items():
        if name.startswith('EN_ORIG'):
            en[r['batch']] = r['eff_fps']

    bandnames = None
    for name in sorted(S):
        if name.startswith('_'):
            continue
        b = (S[name].get('bands') or {}).get('bands')
        if b:
            bandnames = [x['band'] for x in b]
            break

    out = {}
    print('每格 = 该臂该阶段 fps / **同批 EN 同阶段** fps（<1 = 比英文原盘慢）')
    print('| 臂(批) | %s |' % ' | '.join(n[:14] for n in bandnames))
    print('|---%s|' % ('|---' * len(bandnames)))
    for name in sorted(S):
        if name.startswith('_'):
            continue
        m = meta.get(name)
        if not m or not any(name.startswith(k) for k in KEY):
            continue
        b = (S[name].get('bands') or {}).get('bands')
        if not b:
            continue
        bt = m['batch']
        # 找同批 EN 的阶段表
        enname = next((x for x in sorted(S) if x.startswith('EN_ORIG') and meta.get(x, {}).get('batch') == bt), None)
        if not enname or not (S[enname].get('bands') or {}).get('bands'):
            continue
        enb = {x['band']: x['fps'] for x in S[enname]['bands']['bands']}
        cells = []
        for x in b:
            e = enb.get(x['band'])
            cells.append(('%.3f' % (x['fps'] / e)) if (e and x['fps']) else '-')
        out[name] = {'batch': bt, 'eff': m['eff_fps'], 'cells': cells, 'bands': bandnames}
        print('| `%s`(%s) eff=%s | %s |' % (name, bt, m['eff_fps'], ' | '.join(cells)))
    with io.open(os.path.join(BIS, 'PHASE_TABLE.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
