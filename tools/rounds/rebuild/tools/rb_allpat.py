# -*- coding: utf-8 -*-
r"""rb_allpat.py -- 造一张「全部 2,350 槽写可解码图案」的寻址证明盘（不跑模拟器）。

复用 `tools/re/toolbelt/cap_build.py` 的图案内核（slot_pattern / pattern_decode /
container_to_plane / plane_to_container / cell_read / cell_write），
只把几何换成 GR_REBUILD2400 的 h=644 / 64 列 / SKIP=2 / Y0=3。

用法: python rb_allpat.py [--iso <成品盘>] [--out <allpat.iso>]
"""
import argparse
import hashlib
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402
import cap_build as CB                                                # noqa: E402

W, H, NCOL, SKIP, Y0 = 1024, 644, 64, 2, 3
SLOT_LO, SLOT_HI = 0, 2349
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def yrow(row):
    return Y0 + 16 * (row + (SKIP if row >= 12 else 0))


def cell(slot):
    return 16 * (slot % NCOL), yrow(slot // NCOL)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                  'GR_REBUILD2400.iso'))
    ap.add_argument('--out', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                  'GR_REBUILD2400_allpat.iso'))
    a = ap.parse_args(argv)
    CB.SLOT_LO, CB.SLOT_HI = SLOT_LO, SLOT_HI

    iso = T.Iso(a.iso)
    e = [x for x in zx_lib.entries(iso, zx_lib.MENU_LBA) if x['name'] == 'COMMON.PAK'][0]
    pak = bytes(iso.read(e['iso_off'], e['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    r_off, r_stored = rec[6], rec[5]
    P('[in ] %s' % a.iso)
    P('     MENU#%d COMMON.PAK stored=%d ; new_font_revised psm=%d w=%d h=%d (px=%d) @+%d' %
      (e['idx'], e['stored'], rec[1], rec[2], rec[3], r_stored, r_off))
    assert (rec[1], rec[2], rec[3], r_stored) == (20, W, H, W * H // 2 + 16), rec
    payload = pak[r_off:r_off + r_stored]
    iso.close()

    plane, segs = CB.container_to_plane(payload, W, H)
    P('[seg] 段数 %d ; 覆盖 %d B ; 平面 %d B' %
      (len(segs), sum(s[2] for s in segs), len(plane)))
    assert len(plane) == W * H // 2
    plane = bytearray(plane)
    for s in range(SLOT_LO, SLOT_HI + 1):
        x, y = cell(s)
        assert 0 <= x and y + 16 <= H, (s, x, y)
        CB.cell_write(plane, x, y, CB.slot_pattern(s))
    P('[wrt] 槽 %d..%d 图案已写入' % (SLOT_LO, SLOT_HI))
    new_payload, segs2, covered = CB.plane_to_container(payload, bytes(plane), W)
    assert len(new_payload) == len(payload), (len(new_payload), len(payload))
    assert covered == sum(s[2] for s in segs2)
    P('[rep] 重封装 %d B（等长 %s）; 覆盖 %d B' %
      (len(new_payload), len(new_payload) == len(payload), covered))

    if os.path.exists(a.out):
        raise SystemExit('输出已存在: %s' % a.out)
    tmp = a.out + '.part'
    shutil.copyfile(a.iso, tmp)
    with open(tmp, 'r+b') as f:
        f.seek(e['iso_off'] + r_off)
        f.write(new_payload)
    P('[out] %s' % a.out)

    # ── 回读闭环 ──
    v = T.Iso(tmp)
    e2 = [x for x in zx_lib.entries(v, zx_lib.MENU_LBA) if x['name'] == 'COMMON.PAK'][0]
    pak2 = bytes(v.read(e2['iso_off'], e2['stored']))
    r2 = [r for r in T.parse_pak_records(pak2) if r[0] == 'new_font_revised'][0]
    pl2, _sg = CB.container_to_plane(pak2[r2[6]:r2[6] + r2[5]], W, H)
    ok = 0
    bad = []
    for s in range(SLOT_LO, SLOT_HI + 1):
        x, y = cell(s)
        g = CB.cell_read(bytes(pl2), x, y)
        good, got, why = CB.pattern_decode(g)
        if good and got == s:
            ok += 1
        else:
            bad.append((s, got, why))
    P('[R5] 回读闭环: %d / %d 槽图案解回槽号 ✓ ; 失败 %d' %
      (ok, SLOT_HI - SLOT_LO + 1, len(bad)))
    for b in bad[:10]:
        P('      %s' % (b,))
    # 越界 / 重格
    cells = {}
    dup = 0
    for s in range(SLOT_LO, SLOT_HI + 1):
        c = cell(s)
        if c in cells:
            dup += 1
        cells[c] = s
    P('[R6] 格位互不重复: %d 格 / %d 槽 ; 重复 %d' %
      (len(cells), SLOT_HI - SLOT_LO + 1, dup))
    v.close()
    assert ok == SLOT_HI - SLOT_LO + 1 and not bad, bad[:5]
    assert dup == 0
    os.replace(tmp, a.out)
    h = hashlib.sha256()
    with open(a.out, 'rb') as f:
        while True:
            d = f.read(1 << 22)
            if not d:
                break
            h.update(d)
    P('★ %s  %d B  sha256=%s' % (a.out, os.path.getsize(a.out), h.hexdigest()))
    os.makedirs(os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp'), exist_ok=True)
    with io.open(os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp',
                              'rb_allpat.log'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
