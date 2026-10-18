# -*- coding: utf-8 -*-
r"""cvar_meta_runs.py — 把"相对原盘的差异区间清单"写进每个 CVAR_*.meta.json

要求原文: 每张盘给一个 CVAR_xx.meta.json: 相对原盘的差异区间清单 (证明"只含该部件")。
本脚本把 components.json 里该部件的全部 [start, end) 区间, 以及按结构的分组摘要,
追加进对应 meta.json 的 `diff_runs` / `diff_by_structure` 字段。

用法: python cvar_meta_runs.py --dir . --components components.json
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PARTS = {
    'CVAR_01_elf': ['P1_elf'],
    'CVAR_02_atlas': ['P2_atlas'],
    'CVAR_03_ft': ['P3_ft'],
    'CVAR_04_text': ['P4_text'],
    'CVAR_05_elf_atlas': ['P1_elf', 'P2_atlas'],
    'CVAR_06_rest': ['P5_book', 'P6_other'],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='.')
    ap.add_argument('--components', default='components.json')
    x = ap.parse_args()
    C = json.load(open(os.path.join(x.dir, x.components), encoding='utf-8'))
    for name, parts in PARTS.items():
        p = os.path.join(x.dir, '%s.meta.json' % name)
        with open(p, encoding='utf-8') as f:
            j = json.load(f)
        runs = []
        bystruct = []
        for pt in parts:
            c = C['components'][pt]
            runs.extend(tuple(r) for r in c['runs'])
            for k, it in c['items'].items():
                bystruct.append({'component': pt, 'structure': k,
                                 'runs': it['runs'], 'bytes': it['bytes'],
                                 'iso_lo': it['iso_lo'], 'iso_hi': it['iso_hi'],
                                 'kind': it['kind']})
        runs.sort()
        merged = []
        for s, e in runs:
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        bystruct.sort(key=lambda z: -z['bytes'])
        j['diff_runs_format'] = '[iso_start, iso_end) 半开区间, 相对 work/builds/GR_EN_ORIG/GR_EN_ORIG.iso'
        j['diff_runs_count'] = len(merged)
        j['diff_runs_bytes'] = sum(e - s for s, e in merged)
        j['diff_runs'] = merged
        j['diff_by_structure'] = bystruct
        j['diff_by_structure_count'] = len(bystruct)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(j, f, indent=1, ensure_ascii=False)
        print('  %-22s 部件=%-22s 区间=%-6d 字节=%-8d 结构=%d  (meta %.1f KB)'
              % (name, '+'.join(parts), len(merged),
                 sum(e - s for s, e in merged), len(bystruct),
                 os.path.getsize(p) / 1024.0))
    print('== 回读校验 ==')
    for name in PARTS:
        p = os.path.join(x.dir, '%s.meta.json' % name)
        with open(p, encoding='utf-8') as f:
            j = json.load(f)
        print('  %-22s JSON OK  diff_runs=%d/%dB  sha256=%s  单变量=%s'
              % (name, j['diff_runs_count'], j['diff_runs_bytes'], j['sha256'][:16],
                 j['checks']['5_exact_single_variable']['pass']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
