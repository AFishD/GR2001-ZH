# -*- coding: utf-8 -*-
r"""nh_stage7_iso9660.py — ISO9660 层逐盘对比 + ZH113b vs ZH113b_fix (只读)

对照第三份盘: third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso (原始英文盘)
              third_party\orig\ps2\GR_K99.iso (另一份历史基底)
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
N.ISO['TRUE_ORIG'] = os.path.join(N.REPO, 'third_party', 'orig', 'ps2',
                                  "Tom Clancy's Ghost Recon (USA).iso")
N.ISO['GR_K99'] = os.path.join(N.REPO, 'third_party', 'orig', 'ps2', 'GR_K99.iso')
TAGS = ['TRUE_ORIG', 'EN_ORIG', 'GR_K99', 'ZH113b', 'ZH113b_fix']


def main():
    buf = io.StringIO()
    trees = {}
    for t in TAGS:
        if not os.path.exists(N.ISO[t]):
            buf.write('!! 缺文件 %s\n' % N.ISO[t])
            continue
        iso = N.Iso(N.ISO[t])
        pv = iso.pvd()
        fl = iso.files()
        trees[t] = dict(iso=iso, pv=pv, files=fl, size=iso.size)
        buf.write('%-12s size=%-12s vol_size=%-9s root=(%d,%d) path=(%d,%d) 文件数=%d\n'
                  % (t, N.fmt(iso.size), N.fmt(pv['vol_size']), pv['root_lba'],
                     pv['root_size'], pv['path_lba'], pv['path_size'], len(fl)))
    # 逐文件三方对比
    keys = sorted(set().union(*[set(v['files']) for v in trees.values()]))
    buf.write('\n%-34s %s\n' % ('文件', '  '.join('%-24s' % t for t in trees)))
    for k in keys:
        row = []
        for t in trees:
            f = trees[t]['files'].get(k)
            row.append('%-24s' % ('(缺)' if f is None else
                                  'LBA=%-7d sz=%-10d' % (f['lba'], f['size']) +
                                  ('' if f['dual_ok'] else ' DUALBAD')))
        buf.write('%-34s %s\n' % (k, '  '.join(row)))
    # 关键三方差异
    buf.write('\n== 关键差异 (相对 TRUE_ORIG) ==\n')
    base = trees['TRUE_ORIG']['files']
    for t in trees:
        if t == 'TRUE_ORIG':
            continue
        diffs = []
        for k in keys:
            a, b = base.get(k), trees[t]['files'].get(k)
            if a is None or b is None or (a['lba'], a['size']) != (b['lba'], b['size']):
                diffs.append((k, a, b))
        buf.write('  %-12s 与 TRUE_ORIG 目录记录不同的文件数 = %d %s\n'
                  % (t, len(diffs), [d[0] for d in diffs]))
        for (k, a, b) in diffs:
            buf.write('      %-30s TRUE_ORIG=%s  %s=%s\n'
                      % (k, (a['lba'], a['size']) if a else None,
                         t, (b['lba'], b['size']) if b else None))
    # 系统区/目录区 字节对比
    buf.write('\n== 系统区 / 目录区 / PVD 字节级对比 (相对 TRUE_ORIG) ==\n')
    ref = trees['TRUE_ORIG']['iso']
    for label, off, ln in (('LBA 0..16 (系统/授权)  ', 0, 16 * 2048),
                           ('LBA 16..64 (PVD+路径表)', 16 * 2048, 48 * 2048),
                           ('LBA 256..261 (路径表备)', 256 * 2048, 6 * 2048),
                           ('LBA 294 (SYSTEM.CNF)  ', 294 * 2048, 2048),
                           ('目录区 LBA 262..294    ', 262 * 2048, 32 * 2048)):
        xa = ref.rd(off, ln)
        row = []
        for t in trees:
            if t == 'TRUE_ORIG':
                continue
            xb = trees[t]['iso'].rd(off, ln)
            row.append('%s=%d' % (t, sum(1 for p, q in zip(xa, xb) if p != q)))
        buf.write('  %-26s %s\n' % (label, '  '.join(row)))
    for v in trees.values():
        v['iso'].close()
    print(buf.getvalue())
    with open(os.path.join(N.EVID, 'stage7_iso9660.txt'), 'w', encoding='utf-8') as f:
        f.write(buf.getvalue())


if __name__ == '__main__':
    main()
