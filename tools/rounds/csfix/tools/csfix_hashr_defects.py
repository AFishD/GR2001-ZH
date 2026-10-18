# -*- coding: utf-8 -*-
r"""csfix_hashr_defects.py —— C（HASHR 报错归因）的定点取证：只读 GR_HASHR 的幸存产物。

检查三件事（本任务点名）：
  ① 被搬的 42 字的 FONT.RES 记录/矩形：基底 vs 产物是否出现**零宽度 / 零高度 / 零面积**记录；
  ② 「搬走字形后旧格清零」有没有留下**零矩形**（旧格是否真的变成确定性空模板）；
  ③ charset 与 gate_pairs 的同步状态 + 注销的 8 个占位码。
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..'))
H = os.path.join(ROOT, 'work', 'builds', 'GR_HASHR')


def jload(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def rect_of(rec):
    for k in ('rect', 'r', 'box', 'bbox'):
        if isinstance(rec, dict) and k in rec:
            v = rec[k]
            if isinstance(v, (list, tuple)) and len(v) == 4:
                return list(v)
    return None


def walk_records(o, out):
    """把 JSON 里所有像"记录"的 dict（含 rect/bbox 四元组）收集起来。"""
    if isinstance(o, dict):
        r = rect_of(o)
        if r is not None:
            out.append((o, r))
        for v in o.values():
            walk_records(v, out)
    elif isinstance(o, list):
        for v in o:
            walk_records(v, out)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    out = {}
    for tag, p in (('base_k2', os.path.join(H, 'font_base_k2',
                                            'GR_FA2400_K2_truncation_report.json')),
                   ('prod', os.path.join(H, 'font_prod',
                                         'GR_HASHR2400_truncation_report.json'))):
        if not os.path.exists(p):
            print('[缺] %s' % p)
            continue
        j = jload(p)
        print('=' * 88)
        print('[%s] %s  (%d B)' % (tag, os.path.relpath(p, ROOT), os.path.getsize(p)))
        print('  顶层键: %s' % list(j)[:14])
        recs = []
        walk_records(j, recs)
        zero_w = [r for (_o, r) in recs if r[2] - r[0] <= 0]
        zero_h = [r for (_o, r) in recs if r[3] - r[1] <= 0]
        print('  含 rect/bbox 的条目 = %d ; 零宽 = %d ; 零高 = %d ; 零面积 = %d'
              % (len(recs), len(zero_w), len(zero_h),
                 len([r for (_o, r) in recs if (r[2] - r[0]) * (r[3] - r[1]) <= 0])))
        if zero_w or zero_h:
            print('  ⚠ 零尺寸样例: %s' % (zero_w[:5] + zero_h[:5]))
        out[tag] = dict(n=len(recs), zero_w=len(zero_w), zero_h=len(zero_h))
    # charset 自检 / 同步
    for nm in ('charset_selfcheck.txt', 'gate_selfcheck.txt', 'charset_meta.txt'):
        p = os.path.join(H, 'audit', nm)
        if os.path.exists(p):
            print('=' * 88)
            print('[%s] %s' % (nm, os.path.relpath(p, ROOT)))
            print(''.join(open(p, encoding='utf-8', errors='replace').readlines()[:30]))
    print('=' * 88)
    for nm in ('tools\\text_csv\\gate_pairs.json',
               'tools\\font_pipeline\\data\\charset_compiled_zh16.json'):
        p = os.path.join(ROOT, nm)
        try:
            j = jload(p)
            n = len(j.get('pair_of') or j.get('pairs') or j) if isinstance(j, dict) else len(j)
            print('[tool ] %-56s 条目 %d' % (nm, n))
        except Exception as e:                                                # noqa: BLE001
            print('[tool ] %-56s 读取失败 %s' % (nm, e))
    for p in ('work\\builds\\GR_HASHR\\backup\\gate_pairs.json.before_hashr',
              'work\\builds\\GR_HASHR\\backup\\charset_compiled_zh16.json.before_hashr'):
        fp = os.path.join(ROOT, p)
        if os.path.exists(fp):
            j = jload(fp)
            n = len(j.get('pair_of') or j.get('pairs') or j) if isinstance(j, dict) else len(j)
            print('[bak  ] %-56s 条目 %d' % (p.replace('work\\builds\\GR_HASHR\\', ''), n))


if __name__ == '__main__':
    main()
