# -*- coding: utf-8 -*-
r"""s11_check_summary.py — 打印新 summary.json 的 atlas_artifact 一节 (自检用)。"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = os.path.join(HERE, 'g1', 'GR_ZH93_font_summary.json')
d = json.load(io.open(p, encoding='utf-8'))
a = d['atlas_artifact']
print('[summary] %s' % p)
print('  one_line       : %s' % a['one_line'])
print('  container      : %s, %s B/row' % (a['container']['container'], a['container']['row_bytes']))
print('  segments       : %s' % [(s['first_row'], s['rows'], s['tail']) for s in a['container']['segments']])
print('  view/grid/label: %s / %s / %s' % (a['view'], a['grid'], a['labels']))
print('  flat_vs_engine : %s' % a['flat_vs_engine'])
print('  y0_artifacts   : %s' % a['y0_artifacts'])
print('  never_sampled  : %s' % a['never_sampled_pixels'])
print('  alignment      : %s' % a['grid_row_alignment'])
print('  misplaced rows : %s' % a['grid_rows_misplaced'])
print('  csv note       : %s' % a['csv_cell_xy_note'])
print('  files          : %s' % ', '.join(sorted(d['files'])))
print('  png            : %s' % {k: d['png'][k] for k in ('scale', 'view', 'grid', 'labels')})
print('  how_to_read    : %s' % ', '.join(sorted(d['how_to_read'])))
