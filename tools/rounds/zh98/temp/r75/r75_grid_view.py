# -*- coding: utf-8 -*-
"""r75_grid_view.py -- print the measured part of grid.json (helper, read-only)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'grid.json'), encoding='utf-8'))
a = d['partA_measured']
print('atlas', a['atlas'])
print('en_band_ink', a['en_band_ink'], 'icon_window_ink', a['icon_window_ink'])
for r in a['rows']:
    print('row %2d y=%3d  filled=%2d [%s..%s]  ink x=[%s..%s]  edges mod CW=%s'
          % (r['row'], r['y'], r['filled_cells'], r['first_filled'], r['last_filled'],
             r['first_ink_x'], r['last_ink_x'], r['left_edge_mod_CW']))
    print('    bbox_in_cell:', r['bbox_in_cell_hist'])
    print('    first blank runs:', r['blank_runs'][:6])
