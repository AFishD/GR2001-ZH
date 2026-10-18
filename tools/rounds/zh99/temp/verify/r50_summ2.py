import io, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH99\font\GR_ZH99_font_summary.json'
d = json.load(io.open(p, encoding='utf-8'))
ga = d['atlas_artifact']['grid_row_alignment']
print('grid_row_alignment 非 0:', {k: v for k, v in ga.items() if v})
print('grid_rows_misplaced:', d['atlas_artifact']['grid_rows_misplaced'])
print('grid_selfcheck:', d['grid_selfcheck']['slots_compared'], '/', d['grid_selfcheck']['slots_capacity'], 'ok=', d['grid_selfcheck']['ok'], 'mismatch=', d['grid_selfcheck']['mismatched'])
print('counts:', json.dumps(d['counts'], ensure_ascii=False))
gg = d['glyph_geometry']
print('geom:', gg['one_line'])
print('geom verdict:', json.dumps(gg['verdict'], ensure_ascii=False))
print('findings:', [(f['kind'], f.get('char') or f.get('code'), f['flags']) for f in gg['findings']])
print('truncated:', gg['truncated'], ' empty_by_design:', len(gg['empty_ft_by_design']))
print('capacity.verdict:', json.dumps(d['capacity']['verdict'], ensure_ascii=False))
print('capacity.pair.used/free/vacuum:', d['capacity']['pair']['used'], d['capacity']['pair']['free'], d['capacity']['pair']['vacuum_usable'])
print('notes:', d['notes'])
print('source_iso:', d['source_iso'], d['source_iso_sha256'][:16])
