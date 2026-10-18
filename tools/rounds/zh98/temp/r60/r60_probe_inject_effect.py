# -*- coding: utf-8 -*-
r"""r60_probe_inject_effect.py — 只读: 若把 GR_ZH109/text 注入回 GR_ZH109, 会写哪些行、
写出来的字节是否与盘上**逐字节相同** (即注入是不是 no-op)。

另外: 报 font_compact 在 GR_ZH109 上是否需要改动 (决定 --no-font-compact 是否等价)。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T  # noqa: E402
import inject_text_csv as inj  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
TDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')

cs = T.Charset()
paths, notes = T.expand_csv_inputs([TDIR])
print('表: %s' % [os.path.basename(p) for p in paths])
tables = []
for p in paths:
    rows, cols = T.read_table_rows(p)
    tables.append((p, rows))
merged, rep = T.merge_table_rows(tables)
print('合并后 %d 行; conflicts=%d' % (len(merged), len(rep['conflicts'])))

iso = T.Iso(ISO)
conts = {}
for r in merged:
    res = (r.get('resource') or '').strip()
    if res not in conts:
        spec = T.RES[res]['copies'][0]
        conts[res] = (inj.Container(iso, res, spec, cs),)
c = conts['SFXML'][0]
print('SFXML 容器: slot=%d frame=%d blob=%d' % (c.slot, c.frame_len, len(c.blob)))

n_would, n_same, n_diff = 0, 0, 0
diffs = []
for r in merged:
    cell = r['text_edited']
    if cell.strip() == inj.EMPTY_SENTINEL:
        cell = ''
    if cell == '' or cell == r['text_zh']:
        continue
    n_would += 1
    loc = r['entry_index'].strip()
    off, ln, old = c.locate(loc)
    st = {}
    new = T.cell_to_bytes_text(cell, cs, st)
    if new == old:
        n_same += 1
    else:
        n_diff += 1
        diffs.append((r['id'], loc, len(old), len(new),
                      cs.decode(old)[0][:24], cs.decode(new)[0][:24]))
print('会被写入 %d 行; 其中字节**完全相同** %d 行, 会真的改动 %d 行'
      % (n_would, n_same, n_diff))
for d in diffs[:20]:
    print('   %s %s  %d→%d B\n      盘上: %r\n      将写: %r' % d)
iso.close()

# ---- font_compact: 现在还需不需要改动 ----
try:
    import font_compact
    res = font_compact.plan_compact(ISO)
    s = res['summary']
    print('\n[font_compact] changed=%s moved=%s codes_changed=%s pixels_changed=%s'
          % (s['changed'], s['glyphs']['moved'], s['code_changes'], s['pixels_changed']))
    print('[font_compact] one_line=%s' % (s.get('one_line'),))
except Exception as e:                                                    # noqa: BLE001
    print('\n[font_compact] 计划失败: %r' % (e,))

bi = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'build_info.json'),
                       encoding='utf-8'))
print('\n[build_info] version=%s base=%s' % (bi.get('version'), bi.get('base')))
fc = bi.get('font_compact') or {}
print('[build_info] font_compact.changed=%s codes_changed=%s one_line=%s'
      % (fc.get('changed'), fc.get('codes_changed'), fc.get('one_line')))
print('[build_info] iso_sha256=%s' % bi.get('iso_sha256'))
print('[build_info] inject=%s' % json.dumps(bi.get('inject'), ensure_ascii=False)[:400])
