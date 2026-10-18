# -*- coding: utf-8 -*-
r"""cross_arm.py -- 逐帧比较两个手臂的快照, 证明 A/B 是"同一段轨迹"。

用途: 这是"两臂可比"的前提证据。汉化盘的菜单/HUD 文本不同 ⇒ 帧字节**本来就会不同**;
      真正要证明的是**分歧出现的位置与数量是"只有文本层"**, 而不是"一臂进关卡一臂没进"。
      判据:
        · 完全相同的帧数占比 (3D 场景里没有文字的帧应该逐字节相同)
        · 第一次分歧的帧号, 以及分歧是否"一直持续到最后"
        · 分歧帧数 / 总帧数

用法: python work\builds\GR_FPS\tools\cross_arm.py <dirA> <dirB>
"""
import hashlib
import io
import os
import re
import sys

RX = re.compile(r'^snap_f(\d+)\.png$')


def load(d):
    out = {}
    for fn in os.listdir(d):
        m = RX.match(fn)
        if m:
            out[int(m.group(1))] = hashlib.sha1(
                open(os.path.join(d, fn), 'rb').read()).hexdigest()
    return out


def main():
    a, b = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    A, B = load(a), load(b)
    frames = sorted(set(A) & set(B))
    same = [f for f in frames if A[f] == B[f]]
    diff = [f for f in frames if A[f] != B[f]]
    print('=== %s  vs  %s ===' % (os.path.basename(a), os.path.basename(b)))
    print('  A 快照 %d · B 快照 %d · 共同帧号 %d' % (len(A), len(B), len(frames)))
    print('  ★ 逐字节相同 = %d (%.1f%%) · 不同 = %d (%.1f%%)'
          % (len(same), 100.0 * len(same) / max(1, len(frames)),
             len(diff), 100.0 * len(diff) / max(1, len(frames))))
    if diff:
        print('  第一次分歧 @f%d' % diff[0])
        # 分歧的连续性: 从第一次分歧起, 后面有多少帧还是不同
        tail = [f for f in frames if f >= diff[0]]
        tail_diff = [f for f in tail if f not in set(same)]
        print('  从 f%d 起共 %d 帧, 其中不同 %d 帧 (%.1f%%)'
              % (diff[0], len(tail), len(tail_diff),
                 100.0 * len(tail_diff) / max(1, len(tail))))
        # 把相同的帧压成"两臂同画面"的区间 (证明轨迹没分叉)
        segs, cur = [], [same[0], same[0]]
        for f in same[1:]:
            if f == cur[1] + 60:
                cur[1] = f
            else:
                segs.append(tuple(cur))
                cur = [f, f]
        segs.append(tuple(cur))
        print('  "两臂逐字节同画面"的连续区间 (%d 段, 只列 >=180 帧的):' % len(segs))
        for (s, e) in segs:
            if e - s >= 180:
                print('     f%d..f%d  (%d 帧)' % (s, e, e - s + 60))
    else:
        print('  ★ 两臂全部快照逐字节相同')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
