# -*- coding: utf-8 -*-
r"""bands_table.py -- 从 POST_SUMMARY.json 里抽子区间局部 fps（f300-540 = 只有静态记忆卡贴图的那一屏）
与 CDVD 总读数，按批排成一张小表。"""
import io
import json
import os
import sys

BIS = r'C:\Users\84363\Desktop\GoalPlaceholder'
BIS = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_FPSBISECT'


def main():
    with io.open(os.path.join(BIS, 'POST_SUMMARY.json'), encoding='utf-8') as f:
        S = json.load(f)
    with io.open(os.path.join(BIS, 'ARM_TABLE.json'), encoding='utf-8') as f:
        T = json.load(f)
    meta = {}
    for r in T['arms']:
        meta[r['name']] = r
    cdvd = S.get('_cdvd', {})

    print('| 臂 | eff fps | f300-540 fps | f660-2460 fps | CDVD 读次数 | 同批 base 的 f300-540 | EN 的 f300-540 |')
    print('|---|---|---|---|---|---|---|')
    rows = []
    for name in sorted(S):
        if name.startswith('_'):
            continue
        sub = S[name].get('subbands', {})
        a = sub.get('f300-540', {}).get('fps')
        b = sub.get('f660-2460', {}).get('fps')
        m = meta.get(name, {})
        rows.append({'name': name, 'batch': m.get('batch'), 'eff': m.get('eff_fps'),
                     'band': a, 'band2': b,
                     'reads': (cdvd.get(name) or {}).get('reads_total'),
                     'overlap': (m.get('_') or {}).get('overlap')})
    # 同批 base / EN 的 f300-540
    for r in rows:
        bb = next((x for x in rows if x['batch'] == r['batch'] and x['name'].startswith('HK00_base')), None)
        ee = next((x for x in rows if x['batch'] == r['batch'] and x['name'].startswith('EN_ORIG')), None)
        r['base_band'] = bb['band'] if bb else None
        r['en_band'] = ee['band'] if ee else None
    rows.sort(key=lambda r: (r['batch'] or 'Z', r['name']))
    for r in rows:
        rb = ('%.3f' % (r['band'] / r['base_band'])) if (r['band'] and r['base_band']) else '-'
        re_ = ('%.3f' % (r['band'] / r['en_band'])) if (r['band'] and r['en_band']) else '-'
        print('| `%s` | %s | %s | %s | %s | %s (vs base %s) | %s (vs EN %s) |' % (
            r['name'], r['eff'], r['band'], r['band2'], r['reads'], r['band'], rb,
            r['band'], re_))
    with io.open(os.path.join(BIS, 'BANDS_TABLE.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
