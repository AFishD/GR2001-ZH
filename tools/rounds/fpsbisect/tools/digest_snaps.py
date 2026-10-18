# -*- coding: utf-8 -*-
r"""digest_snaps.py -- 每臂：把全部 snap_f*.png 的 (frame, size, sha1) 落盘成 SNAP_SHA1.txt，
然后（--delete）删掉 PNG 本身。

理由：本轮结论引用的"逐帧对照 / 画面段 / 同画面段"证据链需要的是 **sha1 序列**，
      PNG 本身体积大（23 臂 × ~14 MB ≈ 320 MB）且可随时重跑再生。
      落盘后，`DIGEST_CROSS.py` 仍可做任意两臂的逐帧对照（与前一位 cross_arm.py 同判据）。
"""
import hashlib
import io
import os
import re
import sys

RX = re.compile(r'^snap_f(\d+)\.png$')
BIS = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_FPSBISECT'
OUT = os.path.join(BIS, 'out')


def main():
    do_delete = '--delete' in sys.argv
    removed = 0
    freed = 0
    for name in sorted(os.listdir(OUT)):
        d = os.path.join(OUT, name)
        if not os.path.isdir(d) or name.startswith('_'):
            continue
        if not os.path.isfile(os.path.join(d, 'RUN.txt')):
            continue
        items = []
        for fn in os.listdir(d):
            m = RX.match(fn)
            if not m:
                continue
            p = os.path.join(d, fn)
            h = hashlib.sha1(open(p, 'rb').read()).hexdigest()
            items.append((int(m.group(1)), os.path.getsize(p), h))
        items.sort()
        with io.open(os.path.join(d, 'SNAP_SHA1.txt'), 'w', encoding='utf-8') as f:
            f.write('# arm=%s  n=%d  (frame, size, sha1)  -- 由 digest_snaps.py 生成\n'
                    % (name, len(items)))
            for fr, sz, h in items:
                f.write('%d %d %s\n' % (fr, sz, h))
        print('%-28s n=%3d  -> SNAP_SHA1.txt' % (name, len(items)), flush=True)
        if do_delete:
            for fn in list(os.listdir(d)):
                if RX.match(fn):
                    p = os.path.join(d, fn)
                    freed += os.path.getsize(p)
                    os.remove(p)
                    removed += 1
    print('deleted %d PNG, freed %.1f MB' % (removed, freed / 1048576.0))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
