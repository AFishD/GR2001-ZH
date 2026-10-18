# -*- coding: utf-8 -*-
r"""space_pal.py -- COMMON.PAK 内部贴图的调色板占用统计 + MENU/GR 两侧 PAK 差异（只读）。

回答: 8bpp 贴图能不能**无损**转 4bpp（= 实际用到的索引 ≤ 16）。
"""
import json
import os
import struct
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

SEC = 2048
MENU_LBA, GR_LBA = 776286, 19175


def parse_pak_full(pak):
    out, p = [], 0
    while p + 8 <= len(pak):
        ty, nl = struct.unpack_from('<II', pak, p)
        if ty == 0x63 or nl > 64:
            break
        nm = pak[p + 8:p + 8 + nl].decode('latin-1')
        q = p + 8 + nl
        psm, w, h, clut = struct.unpack_from('<4I', pak, q)
        px = struct.unpack_from('<I', pak, q + 16 + clut)[0]
        px_off = q + 20 + clut
        out.append(dict(name=nm, psm=psm, w=w, h=h, clut=clut, px=px,
                        hdr_off=p, clut_off=q + 20, px_off=px_off,
                        rec_end=px_off + px))
        p = px_off + px
    return out


def pak_at(iso, lba, name='COMMON.PAK'):
    for i in range(6000):
        e = iso.img_entry(lba, i)
        nm = e['name']
        if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
            return None
        if nm == name:
            return iso.read(e['iso_off'], e['stored']), e, i
    return None


def segs_flat(blob):
    """把 GIF 段容器的 payload 接起来 = 引擎看到的线性像素。"""
    sg = tcslib.atlas_container_segments(blob, 0)
    if sg is None:
        return None, None
    parts = [blob[o:o + ln] for (_y, o, ln) in sg if ln]
    return b''.join(parts), sg


def main():
    iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
    out = {}
    for tag, lba in (('MENU', MENU_LBA), ('GR', GR_LBA)):
        pak, e, idx = pak_at(iso, lba)
        out[tag] = dict(pak=pak, ents=parse_pak_full(pak), entry=e, idx=idx)
        print('=== %s COMMON.PAK idx=%d len=%d ===' % (tag, idx, len(pak)))
        for r in out[tag]['ents']:
            blob = pak[r['px_off']:r['rec_end']]
            info = dict(name=r['name'], psm=r['psm'], w=r['w'], h=r['h'],
                        clut=r['clut'], px=r['px'], rec_len=r['rec_end'] - r['hdr_off'])
            payload, sg = segs_flat(blob)
            if payload is None:
                payload = blob[:r['px'] - 16] if r['px'] > 16 else blob
            npx = r['w'] * r['h']
            if r['psm'] in (0x13, 0x14) and payload is not None and len(payload) >= npx:
                px_a = np.frombuffer(payload[:npx], dtype=np.uint8)
                vals, cnt = np.unique(px_a, return_counts=True)
                info['distinct_idx_used'] = int(vals.size)
                info['max_idx'] = int(vals.max())
                info['idx_hist_top'] = [[int(v), int(c)] for v, c in
                                        sorted(zip(vals, cnt), key=lambda z: -z[1])[:20]]
                info['fit4bpp'] = bool(vals.max() <= 15)
                info['nibble_align_ok'] = bool(vals.max() <= 15)
                if r['clut'] >= 16 and r['clut_off'] + r['clut'] <= len(pak):
                    cl = pak[r['clut_off']:r['clut_off'] + r['clut']]
                    info['clut_head'] = cl[:32].hex()
                    # 每个用到的索引的 CLUT 颜色
                    cols = []
                    for v in vals[:24]:
                        o = int(v) * 4
                        if o + 4 <= len(cl):
                            cols.append([int(v), cl[o:o + 4].hex()])
                    info['used_colors'] = cols
                    # 逐索引颜色去重
                    allc = set()
                    for v in vals:
                        o = int(v) * 4
                        if o + 4 <= len(cl):
                            allc.add(cl[o:o + 4])
                    info['distinct_colors_used'] = len(allc)
                    info['fit4bpp_by_color'] = len(allc) <= 16
            out[tag]['ents_info'] = out[tag].get('ents_info', []) + [info]
            print('   %-20s psm=0x%02X %dx%d clut=%d px=0x%X reclen=%d distinct_idx=%s max=%s fit4bpp=%s distinct_colors=%s'
                  % (r['name'], r['psm'], r['w'], r['h'], r['clut'], r['px'],
                     r['rec_end'] - r['hdr_off'], info.get('distinct_idx_used'),
                     info.get('max_idx'), info.get('fit4bpp_by_color'),
                     info.get('distinct_colors_used')))
            if 'idx_hist_top' in info:
                print('        top idx: %s' % info['idx_hist_top'][:12])
                print('        used colors: %s' % info.get('used_colors'))
    # MENU vs GR PAK 差异
    a, b = out['MENU']['pak'], out['GR']['pak']
    print('\n=== MENU vs GR PAK 差异 ===')
    print('len %d vs %d' % (len(a), len(b)))
    n = min(len(a), len(b))
    aa = np.frombuffer(a[:n], dtype=np.uint8)
    bb = np.frombuffer(b[:n], dtype=np.uint8)
    d = np.flatnonzero(aa != bb)
    print('differing bytes = %d' % d.size)
    if d.size:
        # 连续区段
        brk = np.flatnonzero(np.diff(d) > 1)
        starts = np.concatenate(([0], brk + 1))
        ends = np.concatenate((brk, [d.size - 1]))
        segs = [(int(d[s]), int(d[e]), int(d[e]) - int(d[s]) + 1) for s, e in zip(starts, ends)]
        print('runs = %d, largest 12:' % len(segs))
        for s, e, L in sorted(segs, key=lambda z: -z[2])[:12]:
            print('   0x%06X..0x%06X len=%d' % (s, e, L))
    out.pop('MENU'); out.pop('GR')
    iso.close()


main()
