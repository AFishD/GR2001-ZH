# -*- coding: utf-8 -*-
r"""space_pak.py -- COMMON.PAK (MENU.IMG#3) 与 GR.IMG 侧拷贝的内部记录盘点（只读）。

回答三件事:
  1. PAK 内部目录有哪些记录 (name/psm/w/h/clut/px_size/px_off)，各占多少字节；
  2. 哪些是 8bpp (psm=0x13) 可以无损转 4bpp (psm=0x14)：像素字节减半 ⇒ 回收多少；
  3. PAK 记录的物理容器里有没有零填充洞。

用法:
  python tools/re/toolbelt/space_pak.py --iso <iso> --json <out.json> [--gr]
"""
import argparse
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

PSM_NAME = {0x13: 'PSMT8(8bpp)', 0x14: 'PSMT4(4bpp)', 0x00: 'PSMCT32', 0x02: 'PSMCT16'}


def parse_pak_full(pak):
    """解析 COMMON.PAK 记录链。返回 (records, end_off, tail)。
    wire: {u32 type}{u32 nameLen}{name}{u32 psm}{u32 w}{u32 h}{u32 clut_size}{clut}{u32 px_size}{px}
    结束哨兵 type=0x63。
    """
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
        rec_end = px_off + px
        if rec_end > len(pak):
            out.append(dict(name=nm, psm=psm, w=w, h=h, clut=clut, px=px,
                            hdr_off=p, px_off=px_off, rec_end=rec_end, truncated=True))
            break
        out.append(dict(name=nm, psm=psm, w=w, h=h, clut=clut, px=px,
                        hdr_off=p, px_off=px_off, rec_end=rec_end, truncated=False,
                        hdr_bytes=px_off - p))
        p = rec_end
    return out, p, len(pak) - p


def segs_of(blob):
    return tcslib.atlas_container_segments(blob, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
    ap.add_argument('--json', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                   'temp', 'r78', 'pak.json'))
    a = ap.parse_args()

    iso = tcslib.Iso(a.iso)
    rep = dict(iso=os.path.abspath(a.iso), paks={})

    for tag, lba, want in (('MENU', MENU_LBA, 'COMMON.PAK'), ('GR', GR_LBA, 'COMMON.PAK')):
        idx = None
        for i in range(5000):
            try:
                e = iso.img_entry(lba, i)
            except Exception:                                      # noqa: BLE001
                break
            nm = e['name']
            if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
                break
            if nm == want and idx is None:
                idx = i
                hit = e
        if idx is None:
            rep['paks'][tag] = None
            continue
        pak = iso.read(hit['iso_off'], hit['stored'])
        recs, endp, tail = parse_pak_full(pak)
        for r in recs:
            r['psm_name'] = PSM_NAME.get(r['psm'], '?0x%X' % r['psm'])
        # 每个记录的容器/尾部零
        for r in recs:
            blob = pak[r['px_off']:r['rec_end']]
            arr = np.frombuffer(blob, dtype=np.uint8)
            nz = np.flatnonzero(arr)
            r['px_zero_bytes'] = len(blob) - int(nz.size)
            sg = segs_of(blob)
            r['segs'] = None if sg is None else [[s[0], s[1], s[2]] for s in sg]
        # PAK 尾部
        tailz = int(np.count_nonzero(np.frombuffer(pak[endp:], dtype=np.uint8) == 0))
        rep['paks'][tag] = dict(entry_idx=idx, off=hit['off'], stored=hit['stored'],
                                real=hit['real'], iso_off=hit['iso_off'],
                                recs=recs, walk_end=endp, tail_bytes=tail,
                                tail_zero=tailz,
                                trailing20=pak[endp:endp + 24].hex())
    iso.close()
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, 'w', encoding='utf-8') as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    for tag, d in rep['paks'].items():
        if d is None:
            print('[%s] COMMON.PAK 未找到' % tag)
            continue
        print('=== %s COMMON.PAK idx=%d off=0x%X stored=%d real=%d walk_end=%d tail=%d(z=%d)'
              % (tag, d['entry_idx'], d['off'], d['stored'], d['real'], d['walk_end'],
                 d['tail_bytes'], d['tail_zero']))
        for r in d['recs']:
            print('   %-24s psm=0x%02X(%-11s) w=%-5d h=%-5d clut=%-5d px=0x%06X px_off=0x%06X rec_end=0x%06X zero=%d'
                  % (r['name'], r['psm'], r['psm_name'], r['w'], r['h'], r['clut'],
                     r['px'], r['px_off'], r['rec_end'], r['px_zero_bytes']))
    print('-> %s' % a.json)


main()
