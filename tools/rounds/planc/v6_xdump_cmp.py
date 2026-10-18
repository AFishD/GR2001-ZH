# -*- coding: utf-8 -*-
r"""v6_xdump_cmp.py — 跨转储、按**画面内容**对齐的回归比对 (帧号不可比, 故用缩略图指纹匹配):
  参考集 = GR_ZH92 的旧转储 (dump_base 等); 目标 = 我的新盘转储。
  对每对匹配上的画面做全分辨率逐像素 diff, 输出相同/不同像素数。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                     # noqa: E402
from PIL import Image                                  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
SIG = (48, 36)


def sig_of(p):
    im = Image.open(p).convert('L').resize(SIG)
    a = np.asarray(im, dtype=np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def load(d):
    out = []
    for fn in sorted(os.listdir(d)):
        if fn.startswith('snap_f') and fn.endswith('.png'):
            out.append((int(fn[6:14]), os.path.join(d, fn)))
    return out


def main():
    ref_dirs = sys.argv[1].split(',')
    new_dirs = sys.argv[2].split(',')
    refs, news = [], []
    for d in ref_dirs:
        p = d if os.path.isabs(d) else os.path.join(REPO, d)
        if os.path.isdir(p):
            refs += [(d, f, s) for (f, s) in load(p)]
    for d in new_dirs:
        p = d if os.path.isabs(d) else os.path.join(REPO, d)
        if os.path.isdir(p):
            news += [(d, f, s) for (f, s) in load(p)]
    print('参考帧 %d (来自 %s)' % (len(refs), ref_dirs))
    print('新盘帧 %d' % len(news))
    Rs = np.stack([sig_of(s) for (_d, _f, s) in refs])
    Ns = np.stack([sig_of(s) for (_d, _f, s) in news])
    Rf = Rs.reshape(len(refs), -1)
    Nf = Ns.reshape(len(news), -1)
    Rn = Rf / (np.linalg.norm(Rf, axis=1, keepdims=True) + 1e-9)
    Nn = Nf / (np.linalg.norm(Nf, axis=1, keepdims=True) + 1e-9)
    sim = Nn @ Rn.T                                    # (new, ref) 余弦相似度
    print()
    print('== 每个参考帧的最佳匹配 (只列相似度 > 0.98 的) ==')
    pairs = []
    for j in range(len(refs)):
        col = sim[:, j]
        i = int(np.argmax(col))
        best = float(col[i])
        if best > 0.98:
            pairs.append((best, j, i))
    pairs.sort(reverse=True)
    seen_new = set()
    print('  相似度  参考帧(盘:帧)                 新盘帧(盘:帧)')
    for (b, j, i) in pairs:
        if i in seen_new:
            continue
        seen_new.add(i)
        print('  %.4f  %-30s %s' % (b, '%s:F%d' % (refs[j][0].split('/')[-1], refs[j][1]),
                                   '%s:F%d' % (news[i][0].split('/')[-1], news[i][1])))
        if len(seen_new) >= 12:
            break
    print()
    print('== 逐像素复核 (全分辨率) ==')
    for (b, j, i) in pairs[:12]:
        ra = np.asarray(Image.open(refs[j][2]).convert('RGB'), dtype=np.int16)
        na = np.asarray(Image.open(news[i][2]).convert('RGB'), dtype=np.int16)
        if ra.shape != na.shape:
            print('  F%-6d vs F%-6d 尺寸不同 %s / %s' % (refs[j][1], news[i][1],
                                                        ra.shape, na.shape))
            continue
        n = int((np.abs(ra - na).max(axis=2) > 0).sum())
        print('  参考 F%-6d vs 新盘 F%-6d : 不同像素 %d %s'
              % (refs[j][1], news[i][1], n, '✓ 逐像素一致' if n == 0 else ''))


if __name__ == '__main__':
    main()
