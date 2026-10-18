# -*- coding: utf-8 -*-
r"""digest_cross.py -- 用 SNAP_SHA1.txt（快照 sha1 清单）做任意两臂的逐帧对照。

判据与 `work\builds\GR_FPS\tools\cross_arm.py` **逐字同口径**（共同帧号 / 逐字节相同占比 /
首次分歧帧号 / "两臂同画面"连续区间），只是数据源从 PNG 换成 sha1 清单
—— 因为快照 PNG 在抽数后已删（见 digest_snaps.py）。

用法: python digest_cross.py <outdirA> <outdirB> [...]
      python digest_cross.py --all        # 跑 REPORT_FPS_BISECT.md 里引用的全部对
"""
import io
import os
import sys

BIS = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_FPSBISECT'
OUT = os.path.join(BIS, 'out')
GRFPS = os.path.join(BIS, '..', 'GR_FPS', 'out')

PAIRS = [
    ('HK00_base_fpsbisect', 'EN_ORIG_fpsbisect'),
    ('HK00_base_fpsbisect', 'HK01_all_fpsbisect'),
    ('HK00_base_fpsbisect', 'HK04_g3_r2_fpsbisect'),
    ('HK00_base_fpsbisect', 'HK05_g4_fpsbisect'),
    ('HK00_base_fpsbisect', 'HK00_base_b_fpsbisect'),
    ('EN_ORIG_fpsbisect', 'EN_ORIG_c_fpsbisect'),
    ('EN_ORIG_fpsbisect', 'CVAR01_elf_fpsbisect'),
    ('EN_ORIG_fpsbisect', 'CVAR02_atlas_fpsbisect'),
    ('EN_ORIG_fpsbisect', 'CVAR04_text_fpsbisect'),
    ('EN_ORIG_fpsbisect', 'TXT02_no_text_fpsbisect'),
    ('HK00_base_fpsbisect', 'TXT02_no_text_fpsbisect'),
]


def load(d):
    p = os.path.join(d, 'SNAP_SHA1.txt')
    out = {}
    for ln in io.open(p, encoding='utf-8', errors='replace'):
        if ln.startswith('#'):
            continue
        f = ln.split()
        if len(f) == 3:
            out[int(f[0])] = f[2]
    return out


def cross(a, b, verbose=True):
    A, B = load(a), load(b)
    frames = sorted(set(A) & set(B))
    same = [f for f in frames if A[f] == B[f]]
    diff = [f for f in frames if A[f] != B[f]]
    res = {'a': os.path.basename(a), 'b': os.path.basename(b), 'n_frames': len(frames),
           'n_same': len(same), 'n_diff': len(diff),
           'first_diff': diff[0] if diff else None, 'segments': []}
    if same:
        segs, cur = [], [same[0], same[0]]
        for f in same[1:]:
            if f == cur[1] + 60:
                cur[1] = f
            else:
                segs.append(tuple(cur))
                cur = [f, f]
        segs.append(tuple(cur))
        res['segments'] = [(s, e) for (s, e) in segs if e - s >= 180]
        res['n_segments'] = len(segs)
    if verbose:
        print('=== %s  vs  %s ===' % (res['a'], res['b']))
        print('  共同帧号 %d · 逐字节相同 %d (%.1f%%) · 不同 %d (%.1f%%)'
              % (len(frames), len(same), 100.0 * len(same) / max(1, len(frames)),
                 len(diff), 100.0 * len(diff) / max(1, len(frames))))
        if diff:
            print('  第一次分歧 @f%d' % diff[0])
            for (s, e) in res['segments']:
                print('     "两臂同画面" f%d..f%d (%d 帧)' % (s, e, e - s + 60))
        else:
            print('  ★ 两臂全部快照逐字节相同')
    return res


def main():
    if '--all' in sys.argv:
        todl = {'GR_ZH113b_v4': os.path.join(GRFPS, 'GR_ZH113b_v4'),
                'GR_EN_ORIG_v4': os.path.join(GRFPS, 'GR_EN_ORIG_v4')}
        pairs = [(os.path.join(OUT, a), os.path.join(OUT, b)) for a, b in PAIRS]
        # 跨轮：上一轮的臂没有 SNAP_SHA1.txt（PNG 还在），这里只比本轮内部
        for a, b in pairs:
            if os.path.isfile(os.path.join(a, 'SNAP_SHA1.txt')) and \
               os.path.isfile(os.path.join(b, 'SNAP_SHA1.txt')):
                cross(a, b)
        for k, v in todl.items():
            print('（跨轮对照 %s 需要 PNG 或它的 sha1 清单；本轮 base/EN 与它的 529/529 全同结论'
                  '已在 REPORT_FPS_BISECT.md §1.4 用 cross_arm.py 记录）' % k)
        return
    a, b = sys.argv[1], sys.argv[2]
    cross(a if os.path.isabs(a) else os.path.join(OUT, a),
          b if os.path.isabs(b) else os.path.join(OUT, b))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
