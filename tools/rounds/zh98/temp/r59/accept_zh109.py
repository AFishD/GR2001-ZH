# -*- coding: utf-8 -*-
r"""round59 静态验收 (只读): GR_ZH109 的贴图右缘修复逐条核对。

判据 (全部与 GR_ZH108 基线/GR_ZH98 搬字前对照):
  ① 5 个码位 (0xAE/0xAF/0xB0/0xED/0xEE) + 17 条空记录组的新矩形: u1 ≤ 992 (x ≤ 976);
  ② 有墨的 2 条 (0xED 这 / 0xEE 个): GR_ZH109 新矩形的像素 == GR_ZH108 旧矩形 == GR_ZH98 搬字前位置 (逐像素);
  ③ 旧矩形在 GR_ZH109 上墨 = 0 (清空);
  ④ 3 个 face 全部非退化记录 max(u1) ≤ 992;
  ⑤ 全图集: GR_ZH108 → GR_ZH109 改动像素只落在 (旧 ∪ 新) 矩形内, 且 (在用的 1175 对偶格 ∪ 其它记录矩形) 丢失 0 / 新增 0;
  ⑥ 记录表: 被搬的 46 条只改 u/v; pad/advance 逐条原值; 其它记录逐字节不变;
  ⑦ dump_font 的 FT CSV: 544 行里只有 46 行的 u/v 变, has_ink/ink_px 逐条不变 (有墨 502 / 无墨 42);
  ⑧ 单格字库: 错误 0; 0xEC/0xED/0xEE 三条都 match (diff 0);
  ⑨ font_cell_map: 在用 1175 = slot 0..1174 连续; 可用 329 = 1175..1503 连续; held/recyclable/free_ft 全 0。

用法: python accept_zh109.py
"""
import csv
import io
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import tcslib                                                            # noqa: E402
from patch_zh109_edge_fix import load                                    # noqa: E402

ISO109 = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
ISO108 = os.path.join(REPO, 'work', 'builds', 'GR_ZH108', 'GR_ZH108.iso')
ISO98 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
FT108 = os.path.join(REPO, 'work', 'builds', 'GR_ZH108', 'font', 'GR_ZH108_font_ft.csv')
FT109 = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'font', 'GR_ZH109_font_ft.csv')
SCF109 = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'font_single_cell',
                      'GR_ZH109_single_cell_report.json')
FCM109 = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'temp', 'font_cell_map',
                      'GR_ZH109_font_cell_map.csv')
FACE_ORDER = ['large', 'default', 'huge']
LOG, OUT = [], {}
MOVE_CODES = [0xAE, 0xAF, 0xB0, 0xED, 0xEE]
BLANK_SHARED = [0x20, 0x7F] + list(range(0xA1, 0xAE)) + [0xB1, 0xB5]


def log(s=''):
    print(s)
    LOG.append(s)


def rect_of(r):
    return None if (r is None or r[4] <= r[2] or r[5] <= r[3]) else (r[2], r[3], r[4], r[5])


def all_rects(M, skip=()):
    out = []
    for nm in FACE_ORDER:
        for c, r in M['rec'][nm].items():
            if c in skip:
                continue
            rc = rect_of(r)
            if rc:
                out.append(rc)
    return out


def mask(rects, shape=(512, 1024)):
    m = np.zeros(shape, dtype=bool)
    for (u0, v0, u1, v1) in rects:
        m[v0:v1, u0:u1] = True
    return m


def main():
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    code2ch = {int(v): k for k, v in cs['codes'].items()}
    M108, M109, M98 = load(ISO108), load(ISO109), load(ISO98)
    D = {}
    log('=' * 96)
    log('GR_ZH109 贴图右缘修复 — 静态验收 (只读)')
    log('=' * 96)
    log('[盘] GR_ZH108 sha %s' % tcslib.sha256_file(ISO108))
    log('[盘] GR_ZH109 sha %s' % tcslib.sha256_file(ISO109))
    log('[盘] GR_ZH98  sha %s  (搬字前参照)' % tcslib.sha256_file(ISO98))

    # ---- ① 新矩形 ----
    log('')
    log('① 被搬的码位 (3 个 face 全部记录): 新矩形必须 u1 ≤ 992')
    rows, ok1 = [], True
    for c in MOVE_CODES + BLANK_SHARED[:1]:
        for nm in FACE_ORDER:
            r = M109['rec'][nm].get(c)
            if r is None:
                continue
            rc = rect_of(r)
            if rc is None:
                continue
            u0, v0, u1, v1 = rc
            ink = int(M109['ink'][v0:v1, u0:u1].sum())
            rows.append(dict(face=nm, code='0x%02X' % c, char=code2ch.get(c, ''), rect=list(rc),
                             ink=ink, ok=u1 <= 992))
            ok1 &= u1 <= 992
            log('   %-7s 0x%02X %-2s rect=(%4d,%3d,%4d,%4d) u1=%-4d 墨 %3d px  %s'
                % (nm, c, code2ch.get(c, '-'), u0, v0, u1, v1, u1, ink, '✓' if u1 <= 992 else '✗'))
    D['new_rects'] = rows
    D['ok_u1_le_992'] = bool(ok1)

    # ---- ② 像素逐像素保真 (三张盘对照) ----
    #   参照坐标**从 round54 的 layout.json 读**(不写死): 那张表记着每条搬字记录的 old/new。
    lay = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r54',
                                         'layout.json'), encoding='utf-8'))
    plan = {m['code']: m for m in lay['moves']}
    log('')
    log('② 有墨的两条: GR_ZH109 新矩形 vs GR_ZH108 旧矩形 vs GR_ZH98 搬字前位置')
    px, ok2 = [], True
    for c in (0xED, 0xEE):
        old1708 = tuple(plan[c]['new']) if 'new' in plan[c] else None      # 计划落点
        old108 = rect_of(M108['rec']['large'][c])                          # GR_ZH108 实际
        old98 = tuple(plan[c]['old'])                                      # 搬字前 (GR_ZH98)
        r109 = rect_of(M109['rec']['large'][c])
        a = M109['ink'][r109[1]:r109[3], r109[0]:r109[2]]
        b = M108['ink'][old108[1]:old108[3], old108[0]:old108[2]]
        z = M98['ink'][old98[1]:old98[3], old98[0]:old98[2]]
        same108 = bool(np.array_equal(a, b))
        same98 = bool(np.array_equal(a, z))
        ok2 &= same108 and same98
        px.append(dict(code='0x%02X' % c, char=code2ch[c], new=list(r109), old108=list(old108),
                       old98=list(old98), planned_new=list(old1708 or ()), ink=int(a.sum()),
                       equal_old108=same108, equal_pre_relocate_zh98=same98,
                       diff108=int((a ^ b).sum()), diff98=int((a ^ z).sum())))
        log('   0x%02X %s 新(%d,%d,%d,%d) 墨 %d | == GR_ZH108 旧矩形(%d,%d,%d,%d) %s (差 %d px) | '
            '== GR_ZH98 搬字前(%d,%d,%d,%d) %s (差 %d px)'
            % (c, code2ch[c], *r109, int(a.sum()), *old108, same108, int((a ^ b).sum()),
               *old98, same98, int((a ^ z).sum())))
    D['pixel_fidelity'] = px
    D['ok_pixels'] = bool(ok2)

    # ---- ③ 旧矩形清空 ----
    log('')
    log('③ 旧矩形在 GR_ZH109 上必须 0 墨')
    ok3 = True
    old_all = [(992, 195, 1008, 211), (1008, 195, 1024, 211), (1008, 0, 1024, 16),
               (1014, 0, 1024, 16)]
    for rc in old_all:
        n = int(M109['ink'][rc[1]:rc[3], rc[0]:rc[2]].sum())
        ok3 &= (n == 0)
        log('   (%4d,%3d,%4d,%4d) 墨 %d px  %s' % (*rc, n, '✓' if n == 0 else '✗'))
    D['old_rects_cleared'] = bool(ok3)

    # ---- ④ 全 face max(u1) ----
    log('')
    log('④ 3 个 face 全部非退化记录 max(u1)')
    m108 = max(rc[2] for rc in all_rects(M108))
    m109 = max(rc[2] for rc in all_rects(M109))
    log('   GR_ZH108 = %d  →  GR_ZH109 = %d   %s' % (m108, m109, '✓' if m109 <= 992 else '✗'))
    D['max_u1'] = dict(zh108=m108, zh109=m109, ok=m109 <= 992)

    # ---- ⑤ 全图集: 改动只落在 (旧 ∪ 新); 保护区 0 丢 0 增 ----
    log('')
    log('⑤ 全图集逐像素对照 GR_ZH108: 改动 ⊆ (旧 ∪ 新); 保护区 丢失 0 / 新增 0')
    used = np.zeros((512, 1024), dtype=bool)
    n_used = 0
    for ch, (b1, b2) in cs['pair_of'].items():
        if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
            x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(b1, b2))
            used[y:y + 16, x:x + 16] = True
            n_used += 1
    new_rects = sorted(set(tuple(rc) for rc in
                           [rect_of(M109['rec'][nm][c]) for c in MOVE_CODES + [0x20]
                            for nm in FACE_ORDER if c in M109['rec'][nm]
                            and rect_of(M109['rec'][nm][c])]))
    other = mask(all_rects(M109, skip=set(MOVE_CODES + BLANK_SHARED)))
    oldm, newm = mask(old_all), mask(new_rects)
    protect = used | other
    diff = M108['ink'] != M109['ink']
    lost = int((M108['ink'] & protect & ~M109['ink']).sum())
    added = int((M109['ink'] & protect & ~M108['ink']).sum())
    outside = int((diff & ~(oldm | newm)).sum())
    ok5 = (lost == 0 and added == 0 and outside == 0)
    log('   在用对偶格 %d 个 (%d px) ∪ 其它记录矩形 (%d px) = 保护区 %d px'
        % (n_used, int(used.sum()), int(other.sum()), int(protect.sum())))
    log('   改动像素 %d px (清 %d + 写 %d); 逸出 (旧 ∪ 新) 的 %d px; 保护区 丢失 %d / 新增 %d  %s'
        % (int(diff.sum()), int((oldm & diff).sum()), int((newm & diff).sum()),
           outside, lost, added, '✓' if ok5 else '✗'))
    D['atlas_compare'] = dict(used_slots=n_used, protect_px=int(protect.sum()),
                              changed_px=int(diff.sum()), cleared_px=int((oldm & diff).sum()),
                              written_px=int((newm & diff).sum()), outside_px=outside,
                              protect_lost=lost, protect_added=added, ok=bool(ok5))
    D['new_rects_distinct'] = [list(r) for r in new_rects]

    # ---- ⑥ 记录表逐条 ----
    log('')
    log('⑥ 记录表: 被搬的 u/v = 补丁报告里的落点; pad/advance 原值; 其它记录逐字节不变')
    fix = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH109',
                                         'GR_ZH109_edge_fix_report.json'), encoding='utf-8'))
    plan_new = {int(m['code'], 16): tuple(m['new']) for m in fix['moves']}
    bad = []
    n_moved = 0
    n_other = 0
    for nm in FACE_ORDER:
        for c in sorted(M109['rec'][nm]):
            a, b = M108['rec'][nm][c], M109['rec'][nm][c]
            if c in MOVE_CODES or c in BLANK_SHARED:
                n_moved += 1
                if (a[0], a[1]) != (b[0], b[1]):
                    bad.append(('pad/advance-changed', nm, '0x%02X' % c, a, b))
                    continue
                want = plan_new.get(c)
                if want is None:                       # 17 条空记录组: 共用一个空矩形
                    want = tuple(rect_of(M109['rec']['large'][0x20]))
                if tuple(b[2:6]) != want:
                    bad.append(('new-rect-mismatch', nm, '0x%02X' % c, a, b, list(want)))
                elif c in MOVE_CODES and b[4] > 992:
                    bad.append(('u1>992', nm, '0x%02X' % c, b))
            else:
                n_other += 1
                if a != b:
                    bad.append(('other-changed', nm, '0x%02X' % c, a, b))
    ok6 = not bad
    log('   被搬记录 %d 条 (pad/advance 原值 ✓, u/v = 计划落点 ✓, u1 ≤ 992 ✓); '
        '其它记录 %d 条逐字节不变 ✓  %s' % (n_moved, n_other, '✓' if ok6 else '✗'))
    if bad:
        log('   !! %s' % json.dumps(bad[:5], ensure_ascii=False))
    D['records'] = dict(moved=n_moved, unchanged=n_other, ok=bool(ok6))

    # ---- ⑦ dump_font 的 FT CSV 对照 ----
    log('')
    log('⑦ dump_font 的 FT CSV: 544 行里只有 46 行的 u/v 变, has_ink/ink_px 逐条不变')
    def csvrows(p):
        with io.open(p, encoding='utf-8-sig', newline='') as f:
            return {(r['face'], r['code']): r for r in csv.DictReader(f)}
    A, B = csvrows(FT108), csvrows(FT109)
    ch_rows, ch_ink, ch_has = [], 0, 0
    for k in A:
        if A[k] != B[k]:
            ch_rows.append(k)
            if A[k]['ink_px'] != B[k]['ink_px']:
                ch_ink += 1
            if A[k]['has_ink'] != B[k]['has_ink']:
                ch_has += 1
    n_has = sum(1 for k in B if B[k]['has_ink'] == '1')
    ok7 = (len(ch_rows) == 46 and ch_ink == 0 and ch_has == 0)
    log('   行数 %d/%d; 有变化 %d 行; 其中 ink_px 变 %d 行 / has_ink 变 %d 行; '
        'GR_ZH109 有墨 %d / 无墨 %d   %s'
        % (len(A), len(B), len(ch_rows), ch_ink, ch_has, n_has, len(B) - n_has,
           '✓' if ok7 else '✗'))
    D['ft_csv'] = dict(rows=len(B), changed=len(ch_rows), ink_changed=ch_ink,
                       has_ink_changed=ch_has, with_ink=n_has, without_ink=len(B) - n_has,
                       ok=bool(ok7))

    # ---- ⑧ 单格字库 ----
    log('')
    log('⑧ 单格字库 (single_cell_font): 错误 0; 0xEC/0xED/0xEE 三条 match')
    sc = json.load(io.open(SCF109, encoding='utf-8'))
    c = sc['counts']
    three = {}
    for cell in sc['cells']:
        if cell['kind'] == 'single' and cell['code'] in ('EC', 'ED', 'EE', 'AE', 'AF', 'B0'):
            three[cell['code']] = dict(char=cell['char'], cell=(cell['cell_x'], cell['cell_y']),
                                       verdict=cell['verdict'], diff=cell['diff_px'],
                                       ink=cell['disk_ink'])
    ok8 = (c['by_level'].get('error', 0) == 0 and c['matched'] == 1371
           and c['compared'] == 1373
           and all(three[k]['verdict'] == 'match' for k in ('EC', 'ED', 'EE')))
    log('   %s' % sc['one_line'])
    for k in sorted(three):
        t = three[k]
        log('   0x%s %-2s 格(%d,%d) %s diff=%s 墨=%d'
            % (k, t['char'], t['cell'][0], t['cell'][1], t['verdict'], t['diff'], t['ink']))
    log('   by_verdict = %s' % json.dumps(c['by_verdict'], ensure_ascii=False))
    D['single_cell'] = dict(counts=c, probe=three, ok=bool(ok8))

    # ---- ⑨ font_cell_map ----
    log('')
    log('⑨ font_cell_map: 在用 1175 = slot 0..1174 连续; 可用 329 = 1175..1503 连续')
    rows9 = list(csv.DictReader(io.open(FCM109, encoding='utf-8-sig', newline='')))
    st = {}
    for r in rows9:
        st.setdefault(r['status'], []).append(int(r['slot']))
    ok9 = (st.get('used') == list(range(1175)) and st.get('free_blank') == list(range(1175, 1504))
           and set(st) == {'used', 'free_blank'})
    log('   状态分布 = %s' % json.dumps({k: len(v) for k, v in sorted(st.items())},
                                        ensure_ascii=False))
    log('   used = 0..1174 连续 %s; free_blank = 1175..1503 连续 %s; 其它状态 %s  %s'
        % (st.get('used') == list(range(1175)), st.get('free_blank') == list(range(1175, 1504)),
           sorted(set(st) - {'used', 'free_blank'}), '✓' if ok9 else '✗'))
    D['font_cell_map'] = dict(status={k: len(v) for k, v in st.items()}, ok=bool(ok9))

    D['all_ok'] = all([D['ok_u1_le_992'], D['ok_pixels'], D['old_rects_cleared'],
                       D['max_u1']['ok'], D['atlas_compare']['ok'], D['records']['ok'],
                       D['ft_csv']['ok'], D['single_cell']['ok'], D['font_cell_map']['ok']])
    log('')
    log('=' * 96)
    log('总判: %s' % ('全绿 ✓' if D['all_ok'] else '★ 有不通过项 ✗'))
    log('=' * 96)
    io.open(os.path.join(HERE, 'accept_zh109.json'), 'w', encoding='utf-8', newline='\n').write(
        json.dumps(dict(checks=D, log=LOG), ensure_ascii=False, indent=1) + '\n')
    io.open(os.path.join(HERE, 'accept_zh109.log'), 'w', encoding='utf-8', newline='\n').write(
        '\n'.join(LOG) + '\n')
    print('[out] accept_zh109.json / accept_zh109.log')
    return 0 if D['all_ok'] else 3


if __name__ == '__main__':
    sys.exit(main())
