# -*- coding: utf-8 -*-
r"""r69_brief_cmp.py — 用两份 drawlog 反推**简报正文组件**的折行宽度。

原理: GR_ZH112 = GR_ZH111 + "全局关自动折行"(wrapW=∞, `patch_zh112_noautowrap.py`)。
  · ZH111 的简报正文行 = 引擎按**简报组件宽度**折出来的行;
  · ZH112 的简报正文行 = **不折** ⇒ 每段就是原文一整段;
  ⇒ 拿 ZH111 每行去 ZH112 的段里找前缀, 就能算出"这一行最多塞了多少宽" ⇒ wrapW 区间。

用法: python r69_brief_cmp.py <A.drawlog(ZH111)> <B.drawlog(ZH112)> [--site 219EB0] [--top 20]
"""
import argparse
import io
import re
import sys

HERE = __import__('os').path.dirname(__import__('os').path.abspath(__file__))
REPO = HERE
while not __import__('os').path.isdir(__import__('os').path.join(REPO, 'tools', 'capture')):
    REPO = __import__('os').path.dirname(REPO)
sys.path.insert(0, __import__('os').path.join(REPO, 'tools', 'capture'))
import nav_hook as N                                                    # noqa: E402

RX = re.compile(r'F(\d+) PC=(\w+) RA=(\w+) x=(-?\d+) y=(-?\d+)')


def char_w(ch):
    o = ord(ch)
    if ch == ' ':
        return 3
    return 8 if 0x21 <= o <= 0x7E else 16


def width(s):
    return sum(char_w(c) + 1 for c in s.strip())


def load(path, site):
    out = []
    for ln in io.open(path, encoding='utf-8', errors='replace'):
        m = RX.search(ln)
        if not m or m.group(2) != site:
            continue
        raw = b''
        if '|' in ln:
            try:
                raw = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:96])
            except Exception:                                           # noqa: BLE001
                continue
        t = N.dec_bytes(raw)
        if t:
            out.append((int(m.group(1)), int(m.group(4)), int(m.group(5)), t))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--site', default='219EB0')
    ap.add_argument('--top', type=int, default=20)
    a = ap.parse_args()
    A = load(a.a, a.site)
    B = load(a.b, a.site)
    print('site=%s : A(ZH111) %d 行 ; B(ZH112) %d 行' % (a.site, len(A), len(B)))
    if not A or not B:
        return 1
    # 按帧对齐: 取两边都有的帧, 比较该帧的行集合
    fa = {}
    for fr, x, y, t in A:
        fa.setdefault(fr, []).append((y, x, t))
    fb = {}
    for fr, x, y, t in B:
        fb.setdefault(fr, []).append((y, x, t))
    common = sorted(set(fa) & set(fb))
    print('共同帧 %d (A %d / B %d)' % (len(common), len(fa), len(fb)))
    shown = 0
    for fr in common:
        la = sorted(fa[fr])
        lb = sorted(fb[fr])
        ta = [t for _y, _x, t in la]
        tb = [t for _y, _x, t in lb]
        if ta == tb:
            continue
        if shown >= a.top:
            break
        shown += 1
        print('\n===== F%d =====' % fr)
        print('  A(ZH111, 折行开) %d 行:' % len(ta))
        for _y, _x, t in la[:14]:
            print('     y=%-4d x=%-4d w=%-4d %s' % (_y, _x, width(t), t[:44]))
        print('  B(ZH112, 折行关) %d 行:' % len(tb))
        for _y, _x, t in lb[:14]:
            print('     y=%-4d x=%-4d w=%-4d %s' % (_y, _x, width(t), t[:44]))
    if not shown:
        print('两盘的该站点行集合**完全相同** —— 说明这个站点不参与折行差异')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
