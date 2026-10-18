# -*- coding: utf-8 -*-
r"""verify_all.py — round51 全链路静态复验驱动 (只读盘; 只往 outdir 写报告)。

按验收单逐项跑:
  1 audit_inventory          缺失 0
  2 inject_text_csv --check-only  exit 0
  3 diff_text_versions <盘> GR_ZH98  修改 0 条
  4 dump_font                自查 1504/1504 / grid_row_alignment 全 0 / 缺字形 0 / 几何告警
  5 font_residue             残墨
  6 scan_glyph_geometry      几何体检
  7 受保护区差异 (ELF / PVD / 两个 IMG 条目表 / GR.IMG #551..#565 / PAK 包头 / FONT.RES)
  8 已有盘 sha256 逐一复核

用法: python verify_all.py <iso> <label> <outdir>
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
PY = sys.executable
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                             # noqa: E402

ISO = os.path.abspath(sys.argv[1])
LABEL = sys.argv[2]
OUT = os.path.abspath(sys.argv[3])
os.makedirs(OUT, exist_ok=True)
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')


def run(cmd, log):
    p = subprocess.run(cmd, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    txt = p.stdout.decode('utf-8', 'replace')
    io.open(os.path.join(OUT, log), 'w', encoding='utf-8', newline='\n').write(txt)
    return p.returncode, txt


doc = dict(iso=os.path.relpath(ISO, REPO).replace('\\', '/'), label=LABEL,
           sha256=tcslib.sha256_file(ISO))
print('=' * 78)
print('全链路静态复验  %s  (%s)' % (doc['iso'], LABEL))
print('  sha256 = %s' % doc['sha256'])
print('=' * 78)

# 1 audit_inventory
rc, t = run([PY, 'tools/iso_build/audit_inventory.py', doc['iso']], 'audit.log')
m = re.search(r'在役 (\d+) 条, \*\*缺失\(仍为 EN 词\) (\d+) 条\*\*, 其它 (\d+) 条', t)
doc['audit_inventory'] = dict(exit=rc, parsed=m.groups() if m else None,
                              missing=int(m.group(2)) if m else None,
                              line=[x for x in t.splitlines() if '在役' in x][-1:] or None)
print('[1] audit_inventory: exit=%d  %s' % (rc, doc['audit_inventory']['line']))

# 2 inject --check-only
rc, t = run([PY, 'tools/text_csv/inject_text_csv.py', '--csv',
             os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'text'),
             '--src', doc['iso'], '--check-only'], 'checkonly.log')
doc['inject_check_only'] = dict(exit=rc, tail=t.strip().splitlines()[-4:])
print('[2] inject --check-only: exit=%d  %s' % (rc, doc['inject_check_only']['tail'][-1:]))

# 3 文本: ① 与 GR_ZH98 的 LANG/SFXML 容器**逐字节**相同; ② diff_text_versions (若两边都是版本名)
iso_a = tcslib.Iso(ISO)
iso_b = tcslib.Iso(BASE)
tb = {}
for key in ('LANG', 'SFXML'):
    for ci, spec in enumerate(tcslib.RES[key]['copies']):
        lba, idx = spec[1], spec[2]
        e1, e2 = iso_a.img_entry(lba, idx), iso_b.img_entry(lba, idx)
        x1 = iso_a.read(e1['iso_off'], e1['stored'])
        x2 = iso_b.read(e2['iso_off'], e2['stored'])
        tb['%s#%d %s' % (key, ci, spec[3])] = dict(
            identical=(x1 == x2), bytes=len(x1),
            diff=sum(1 for i in range(len(x1)) if x1[i] != x2[i]))
iso_a.close()
iso_b.close()
doc['text_containers_vs_base'] = dict(copies=tb, all_identical=all(v['identical'] for v in tb.values()))
print('[3] 文本容器 vs GR_ZH98: %s'
      % ('全部逐字节相同 ✓' if doc['text_containers_vs_base']['all_identical']
         else json.dumps(tb, ensure_ascii=False)))
rc, t = run([PY, 'tools/text_csv/diff_text_versions.py', 'GR_ZH100', 'GR_ZH98',
             '--out', os.path.join(OUT, 'textdiff.txt')], 'textdiff.log')
doc['diff_text_versions'] = dict(exit=rc, log=os.path.relpath(
    os.path.join(OUT, 'textdiff.log'), REPO).replace('\\', '/'),
    lines=[x for x in t.splitlines() if ('修改' in x or '总计' in x or '相同' in x
                                         or '新增' in x or '删除' in x)][:10])
print('[3b] diff_text_versions GR_ZH100 GR_ZH98: exit=%d  %s'
      % (rc, doc['diff_text_versions']['lines'][:3]))


# 4 dump_font
fd = os.path.join(OUT, 'font')
rc, t = run([PY, 'tools/iso_build/dump_font.py', '--iso', doc['iso'], '--out', fd,
             '--prefix', LABEL, '--no-png'], 'dumpfont.log')
sm = json.load(io.open(os.path.join(fd, LABEL + '_font_summary.json'), encoding='utf-8'))
sc = sm.get('grid_selfcheck') or sm.get('selfcheck') or {}
gg = sm.get('glyph_geometry') or {}
doc['dump_font'] = dict(exit=rc,
                        selfcheck=dict(compared=sc.get('slots_compared'),
                                       mismatched=sc.get('mismatched'),
                                       duplicates=sc.get('duplicate_slots'),
                                       out_of_range=sc.get('out_of_range'),
                                       ok=sc.get('ok')),
                        grid_row_alignment_nonzero=[k for k, v in
                                                    (sm.get('grid_row_alignment') or {}).items()
                                                    if v],
                        missing_glyph=sm.get('charset', {}).get('missing')
                        if isinstance(sm.get('charset'), dict) else None,
                        geometry_one_line=gg.get('one_line'),
                        geometry_verdict=gg.get('verdict'))
print('[4] dump_font: 自查 %s / 不一致 %s; grid_row_alignment 非 0 行=%s'
      % (doc['dump_font']['selfcheck']['compared'], doc['dump_font']['selfcheck']['mismatched'],
         doc['dump_font']['grid_row_alignment_nonzero']))
print('    几何: %s' % (gg.get('one_line') or 'n/a'))

# 5 font_residue
rd = os.path.join(OUT, 'residue')
rc, t = run([PY, 'tools/iso_build/font_residue.py', '--iso', doc['iso'], '--out', rd,
             '--prefix', LABEL, '--no-png'], 'residue.log')
rj = None
for fn in os.listdir(rd):
    if fn.endswith('.json'):
        rj = json.load(io.open(os.path.join(rd, fn), encoding='utf-8'))
rs = (rj or {}).get('residue') or {}
doc['font_residue'] = dict(exit=rc, files=sorted(os.listdir(rd)),
                           residue=rs,
                           ink_total=(rj or {}).get('atlas', {}).get('ink_texels'),
                           md=[x for x in io.open(os.path.join(rd, 'residue_report.md'),
                                                  encoding='utf-8').read().splitlines()
                               if x.startswith('**引擎不会采样')][:1])
print('[5] font_residue: exit=%d  残墨=%s (图集墨 %s)'
      % (rc, json.dumps(rs, ensure_ascii=False)[:200], doc['font_residue']['ink_total']))


# 6 glyph geometry
gd = os.path.join(OUT, 'geom')
rc, t = run([PY, 'tools/iso_build/scan_glyph_geometry.py', '--iso', doc['iso'], '--out', gd,
             '--prefix', LABEL, '--quiet'], 'geom.log')
gj = json.load(io.open(os.path.join(gd, LABEL + '_truncation_report.json'), encoding='utf-8'))
doc['glyph_geometry'] = dict(exit=rc, one_line=gj['one_line'], verdict=gj['verdict'],
                             counts=gj['counts'])
print('[6] glyph_geometry: %s' % gj['one_line'])

# 7 受保护区差异
a = open(BASE, 'rb').read()
b = open(ISO, 'rb').read()
assert len(a) == len(b), 'ISO 尺寸不同'
prot = {}
# ELF (SLUS_206.13 @LBA 295) + PVD (@LBA 16)
for nm, off, ln in (('ELF(SLUS_206.13)@LBA295', 295 * 2048, 0x400000),
                    ('ISO PVD@LBA16', 16 * 2048, 2048)):
    d = sum(1 for i in range(off, min(off + ln, len(a))) if a[i] != b[i])
    prot[nm] = d
# 两个 IMG 的条目表 (前 0x8000) + 全部条目头
for nm, lba in (('MENU.IMG', 776286), ('GR.IMG', 19175)):
    base = lba * 2048
    d = sum(1 for i in range(base, base + 0x8000) if a[i] != b[i])
    prot[nm + ' 条目表/名表(前32KB)'] = d
# GR.IMG #551..#565 (制作组名单)
iso = tcslib.Iso(ISO)
iso2 = tcslib.Iso(BASE)
g = 0
for idx in range(551, 566):
    e1 = iso.img_entry(19175, idx)
    e2 = iso2.img_entry(19175, idx)
    g += sum(1 for i in range(e1['iso_off'], e1['iso_off'] + e1['stored'])
             if a[i] != b[i])
    if e1['off'] != e2['off'] or e1['stored'] != e2['stored']:
        g += 1
prot['GR.IMG #551..#565 (制作组名单)'] = g
# FONT.RES
e1 = iso.img_entry(776286, 4)
prot['FONT.RES (MENU.IMG#4)'] = sum(1 for i in range(e1['iso_off'], e1['iso_off'] + e1['stored'])
                                    if a[i] != b[i])
# PAK 包头 (COMMON.PAK new_font_revised 的 8×48B 段头)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import dump_font                                                          # noqa: E402

f = dump_font.load_font(ISO)
am = f['atlas']
segs = tcslib.atlas_container_segments(bytes(am['pak'][am['px_off']:am['px_off'] + am['px_size']]),
                                       am['w'] // 2)
hdr = 0
for (fr, doff, nb) in segs:
    s = am['px_off'] + doff - tcslib.ATLAS_PREFIX_BYTES
    hdr += sum(1 for i in range(s, s + tcslib.ATLAS_PREFIX_BYTES) if a[i] != b[i])
prot['COMMON.PAK 字库 48B 包头 ×%d' % len(segs)] = hdr
iso.close()
iso2.close()
doc['protected_regions'] = dict(diff=prot, all_zero=all(v == 0 for v in prot.values()))
print('[7] 受保护区差异: %s' % ('全部 0 ✓' if doc['protected_regions']['all_zero']
                                else json.dumps(prot, ensure_ascii=False)))

# 8 已有盘 sha256
expect = {
    'GR_EN_ORIG': '?', 'GR_ZH91': '?', 'GR_ZH92': '?', 'GR_ZH93': '?', 'GR_ZH94': '?',
    'GR_ZH95': 'c1f5d8498c66de2061346a75d482d5485105250a3a2984e8604a20b7eb5afafb',
    'GR_ZH96_fix': '4486d576', 'GR_ZH97': '6fc9661591509682e4079885f4e978310a25631e25f33a31213a947dceeb5098',
    'GR_ZH98': 'f0fc6d8fd00232dc6afe5237143cadef29fec2b1cbedfd0c416ce4b723992ac3',
    'GR_ZH99': 'f0fc6d8fd00232dc6afe5237143cadef29fec2b1cbedfd0c416ce4b723992ac3',
}
shas = {}
bd = os.path.join(REPO, 'work', 'builds')
for d in sorted(os.listdir(bd)):
    p = os.path.join(bd, d, d + '.iso')
    if os.path.isfile(p):
        shas[d] = tcslib.sha256_file(p)
doc['build_sha256'] = shas
print('[8] 已有盘 sha256:')
for k, v in shas.items():
    print('    %-12s %s' % (k, v))

io.open(os.path.join(OUT, LABEL + '_verify_all.json'), 'w', encoding='utf-8',
        newline='\n').write(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
print('[报告] %s' % os.path.relpath(os.path.join(OUT, LABEL + '_verify_all.json'), REPO))
