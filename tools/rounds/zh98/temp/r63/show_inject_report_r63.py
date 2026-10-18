# -*- coding: utf-8 -*-
r"""show_inject_report_r63.py — 把注入报告里的关键字段打出来 (给人看的核对清单)。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH110', 'temp', 'inject1_report.json')


def main():
    d = json.load(open(P, encoding='utf-8'))
    print('报告: %s' % os.path.relpath(P, REPO).replace('\\', '/'))
    print('  format=%s  mode=%s' % (d.get('format'), d.get('mode')))
    print('  src sha=%s' % d['src_sha256'][:16])
    print('  dst sha=%s' % d['dst_sha256'][:16])
    print('  changed=%s' % d.get('changed'))
    print('  charset_precheck.verdict=%s (缺字 %s / 死 pair %s)'
          % (d['charset_precheck']['verdict'], d['charset_precheck']['missing_chars'],
             d['charset_precheck']['dead_pair_chars']))
    a = d.get('attr_channel') or {}
    print('  attr_channel:')
    for k in ('rows', 'candidates', 'changed', 'skipped_untouched', 'skipped_already',
              'grow', 'shrink', 'same', 'delta_total_bytes', 'long_titles_warned',
              'csv_offset_drifted', 'stale_charset_rows'):
        print('    %-22s %s' % (k, a.get(k)))
    print('    target               %s' % a.get('target'))
    print('    rows_detail:')
    for r in a.get('rows_detail') or []:
        print('      %-13s %-6s %-7s off=%-6d %2d→%-2d B (%+d)  %r → %r'
              % (r['id'], r['tag'], r['locator'], r['offset_before'], r['bytes_before'],
                 r['bytes_after'], r['delta'], r['text_before'], r['text_after']))


if __name__ == '__main__':
    main()
