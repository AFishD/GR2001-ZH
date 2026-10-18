# -*- coding: utf-8 -*-
r"""probe_ascii.py -- 把成品盘 ASCII 条带里指定码位的字形**直接画出来**看 (只读)。

用法: python probe_ascii.py [码位...]   默认 0x41..0x5A / 0x30..0x39
输出: work\builds\GR_RELEASE\temp\ascii_glyphs.png (每个 face 一行)
"""
import importlib.util
import io
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUT = os.path.join(REPO, 'work', 'builds', 'GR_RELEASE', 'temp')
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402
import cap_build as CB                                                # noqa: E402

W, H = 1024, 644


def open_font(iso_p):
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ent if e['name'] == 'COMMON.PAK'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    raw, segs = CB.container_to_plane(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    e_ft = [e for e in ent if e['name'] == 'FONT.RES'][0]
    ft = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    faces, _e = zx_lib.ft_records(b''.join(s[0] for s in T.lzo_subs(ft)), 28)
    iso.close()
    stride = W // 2
    a = np.frombuffer(bytes(raw[:stride * H]), dtype=np.uint8).reshape(H, stride)
    ink = np.zeros((H, W), dtype=bool)
    ink[:, 0::2] = (a & 0x0F) == 0
    ink[:, 1::2] = (a >> 4) == 0
    return ink, faces


def main(argv):
    iso = os.path.join(REPO, 'work', 'builds', 'GR_RELEASE', 'GR_ZH2400_FINAL.iso')
    codes = [int(x, 16) for x in argv] or (list(range(0x41, 0x5B)) + list(range(0x30, 0x3A)))
    ink, faces = open_font(iso)
    CELL, SC = 18, 5
    rows = len(faces)
    cols = len(codes)
    img = Image.new('RGB', (cols * CELL * SC, rows * CELL * SC), (255, 255, 255))
    px = img.load()
    report = []
    for r, (fn, _fld, ftrows) in enumerate(faces):
        for c, code in enumerate(codes):
            k = code - 0x20
            if k < 0 or k >= len(ftrows):
                continue
            _o, rect = ftrows[k]
            u0, v0, u1, v1 = rect[2], rect[3], rect[4], rect[5]
            g = ink[v0:v1, u0:u1]
            report.append((fn, '0x%02X' % code, list(rect), int(g.sum())))
            for yy in range(min(16, g.shape[0])):
                for xx in range(min(16, g.shape[1])):
                    col = (0, 0, 0) if g[yy, xx] else (255, 255, 255)
                    for dy in range(SC):
                        for dx in range(SC):
                            px[c * CELL * SC + xx * SC + dx,
                               r * CELL * SC + yy * SC + dy] = col
    p = os.path.join(OUT, 'ascii_glyphs.png')
    img.save(p)
    print('[out] %s  (%d rows x %d cols)' % (p, rows, cols))
    for it in report:
        print('   %-8s %s rect=%s ink=%d' % it)
    with io.open(os.path.join(OUT, 'ascii_glyphs.json'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        json.dump([dict(face=a1, code=a2, rect=a3, ink=a4) for a1, a2, a3, a4 in report],
                  fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
