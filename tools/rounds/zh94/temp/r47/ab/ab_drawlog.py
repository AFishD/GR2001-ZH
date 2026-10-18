# -*- coding: utf-8 -*-
r"""ab_drawlog.py — 解析 -grdrawwin 的 drawlog: 得到"每一帧游戏画了哪些字"。

用法:
  python ab_drawlog.py <drawlog> [--chars 中斗训习] [--out <json>]

输出:
  · 首个含指定字的帧号 (逐字);
  · 页面特征 (何为幽灵 / 幽灵行动中 / 统计 / …) 的首现帧;
  · 每帧"新出现的文本"清单 (用来判断界面切换);
  · 指定字出现的帧号区间汇总。
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

CS = tcslib.Charset()

PAGE_SIGS = ['何为幽灵', '幽灵行动中', '顶级步兵部队', '特种部队群', '设定图', '屏幕截图',
             '预告片', '国会最高勋章', '优异服役十字', '灵敏度', '战术演习', '选择你的档案',
             '歼灭战', '制作组', '多人游戏']


def dec(b):
    out, i = [], 0
    while i < len(b):
        v = b[i]
        if v < 0x80:
            out.append(chr(v)); i += 1
        elif i + 1 < len(b) and (v, b[i + 1]) in CS.pair_of:
            out.append(CS.pair_of[(v, b[i + 1])]); i += 2
        elif v in CS.codes:
            out.append(CS.codes[v]); i += 1
        else:
            i += 1
    return ''.join(out)


def main():
    p = sys.argv[1]
    a = sys.argv[1:]
    chars = a[a.index('--chars') + 1] if '--chars' in a else '中斗训习'
    out = a[a.index('--out') + 1] if '--out' in a else None
    per_frame = {}                      # frame -> set(texts) 只留"与上一帧不同"的新文本
    prev = None
    char_frames = {c: [] for c in chars}
    sig_first = {}
    frames_seen = 0
    with io.open(p, encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = re.match(r'F(\d+) ', ln)
            fr = int(m.group(1)) if m else None
            if '|' not in ln:
                continue
            if fr is None:
                continue
            try:
                b = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:64])
            except Exception:                                      # noqa: BLE001
                continue
            t = dec(b)
            if not t.strip():
                continue
            frames_seen += 1
            for c in chars:
                if c in t:
                    if not char_frames[c] or char_frames[c][-1] != fr:
                        char_frames[c].append(fr)
            for s in PAGE_SIGS:
                if s in t and s not in sig_first:
                    sig_first[s] = fr
            cur = per_frame.get(fr)
            if cur is None:
                per_frame[fr] = set([t])
            else:
                cur.add(t)
    print('drawlog=%s  解析到 %d 条绘制文本; 涉及帧 %d..%d'
          % (os.path.basename(p), frames_seen,
             min(per_frame) if per_frame else -1, max(per_frame) if per_frame else -1))
    print()
    print('=== 指定字出现情况 ===')
    for c in chars:
        fl = char_frames[c]
        if fl:
            print('  「%s」 帧数 %d, 首现 f%d, 末现 f%d (前 12 帧: %s)'
                  % (c, len(fl), fl[0], fl[-1], fl[:12]))
        else:
            print('  「%s」 未出现' % c)
    print()
    print('=== 页面特征首现帧 ===')
    for s in PAGE_SIGS:
        if s in sig_first:
            print('  %-8s f%d' % (s, sig_first[s]))
    print()
    print('=== 逐帧绘制文本变化 (前 60 次变化) ===')
    n = 0
    last = None
    for fr in sorted(per_frame):
        key = '|'.join(sorted(per_frame[fr]))
        if key != last:
            print('  f%-6d %s' % (fr, ' ⟂ '.join(sorted(per_frame[fr]))[:150]))
            last = key
            n += 1
            if n >= 60:
                print('  ...(还有更多)')
                break
    if out:
        io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(
            dict(char_frames=char_frames, sig_first=sig_first,
                 frame_changes=len(per_frame)), ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % out)


if __name__ == '__main__':
    main()
