# -*- coding: utf-8 -*-
r"""p21_pull.py — 把报告要引用的关键数字从各报告 JSON 里抽出来。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))


def show(p, keys):
    p = os.path.join(REPO, p)
    if not os.path.isfile(p):
        print('!! 缺 %s' % p)
        return None
    j = json.load(io.open(p, encoding='utf-8'))
    print('=' * 74)
    print('== %s' % os.path.relpath(p, REPO))
    for k in keys:
        cur = j
        ok = True
        for part in k.split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        print('   %-34s %s' % (k, cur if ok else '(无)'))
    return j


show('work/builds/GR_ZH95/temp/font_repack/repack_report.json',
     ['changed', 'pixels_changed', 'code_changes', 'atlas.ink_before', 'atlas.ink_after',
      'atlas.segments', 'cells.total', 'cells.usable', 'cells.record_cell', 'cells.ft_rect',
      'cells.ft_records', 'cells.forbidden_not_in_ft_rect',
      'glyphs.used', 'glyphs.moved', 'glyphs.kept', 'glyphs.dead_pairs', 'glyphs.dup_slots',
      'glyphs.on_bad_cell_before', 'glyphs.missing_glyph_before',
      'capacity.free_slots_before', 'capacity.free_usable_before',
      'capacity.blank_usable_before', 'capacity.dirty_usable_before',
      'capacity.remaining_capacity', 'capacity.blank_usable_after', 'capacity.freed',
      'cross_check_dump_font.vacuum_usable', 'cross_check_dump_font.strict_window_free',
      'iso_sha256', 'iso_sha256_after', 'order_key', 'seconds'])
show('work/builds/GR_ZH94/temp/r46/ft_single_glyph_fix.json', ['grid_row', 'y', 'fixed', 'skipped',
                                                               'pixels_written'])
show('work/builds/GR_ZH95/build_info.json',
     ['version', 'base', 'patch', 'iso_sha256', 'font_repack.changed', 'font_repack.moved',
      'font_repack.codes_changed', 'font_repack.remaining_capacity',
      'font_repack.blank_usable_before', 'font_repack.iso_unchanged',
      'font_dump.chars', 'font_dump.missing_glyph', 'font_dump.ft_records',
      'text_snapshot.entries', 'text_snapshot.cjk_chars'])
