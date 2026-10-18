# -*- coding: utf-8 -*-
r"""ring_cover.py —— 【GR_SPINFIX / D】用用户两份 dump 的 ring.bin 算「钩子有效采样率 / 覆盖率」。

ring.bin 每条 24 B（小端，时间升序）：
  +0x00 u32 frame   +0x04 u32 pc   +0x08 u32 addr   +0x0C u64 value
  +0x14 u8 size_bits(32/64/128)  +0x15 u8 pad  +0x16 u8 dir('W'=0x57)  +0x17 u8 src

输出：每个 watch 方案的 记录/帧、给定 ring 容量下的覆盖帧数/秒数，
      以及「覆盖损坏窗口 (19701, 22094] 需要多大 ring」。
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402

ROOT = C.ROOT
DUMPS = {
    'OLD_f19701': (os.path.join(ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_19701_hotkey_f10'), 19701),
    'NEW_f23444': (os.path.join(ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_23444_hotkey_f10'), 23444),
}
SCHEMES = [
    ('现默认 0x00500000-0x00580000', 0x00500000, 0x00580000),
    ('候选 0x0055B7A0-0x0055C000（桶数组+哨兵）', 0x0055B7A0, 0x0055C000),
    ('页对齐 0x0055B000-0x0055C000', 0x0055B000, 0x0055C000),
    ('全桶数组 0x0055B7A8-0x0055BBA8', 0x0055B7A8, 0x0055BBA8),
]
FPS = 57.0          # 用户两次 dump 的实测帧率（19701@343.04s、23444@423.42s）
DAMAGE_WINDOW = (19701, 22094)      # 损坏窗口（REPORT_USERDUMP_ANALYSIS §2.3）


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    out, rep = [], {}
    for tag, (d, _trig) in DUMPS.items():
        f = os.path.join(d, 'ring.bin')
        blob = open(f, 'rb').read()
        n = len(blob) // 24
        assert len(blob) % 24 == 0
        frames, cnt = [], dict((s[0], 0) for s in SCHEMES)
        fmin, fmax = None, None
        for i in range(n):
            fr, pc, addr = struct.unpack_from('<III', blob, i * 24)
            if fmin is None or fr < fmin:
                fmin = fr
            if fmax is None or fr > fmax:
                fmax = fr
            for name, lo, hi in SCHEMES:
                if lo <= addr < hi:
                    cnt[name] += 1
        span = fmax - fmin + 1
        per_frame = n / float(span)
        r = dict(entries=n, frame_lo=fmin, frame_hi=fmax, span_frames=span,
                 rec_per_frame=round(per_frame, 2),
                 bytes_per_frame=round(per_frame * 24, 1),
                 scheme=dict((k, dict(hits=v, per_frame=round(v / float(span), 3),
                                      pct=round(100.0 * v / n, 2))) for k, v in cnt.items()))
        rep[tag] = r
        out.append('%s：ring %d 条，覆盖帧 %d..%d（%d 帧）' % (tag, n, fmin, fmax, span))
        out.append('  整体 %.2f 条/帧 = %.1f B/帧（这一档就是现默认 watch 的流量）'
                   % (per_frame, per_frame * 24))
        for name, _lo, _hi in SCHEMES:
            v = cnt[name]
            pf = v / float(span)
            out.append('  %-42s %7d 条  %7.3f 条/帧  %5.2f%%   '
                       '262144 条可覆盖 %s 帧' % (name, v, pf, 100.0 * v / n,
                                                 ('%.0f' % (262144 / pf)) if pf else '∞'))
        out.append('')

    # 覆盖损坏窗口需要多大 ring
    pf_full = max(rep[t]['rec_per_frame'] for t in rep)
    span_dmg = DAMAGE_WINDOW[1] - DAMAGE_WINDOW[0]
    out.append('损坏窗口 = (%d, %d]，共 %d 帧 ≈ %.1f s' % (DAMAGE_WINDOW[0], DAMAGE_WINDOW[1],
                                                          span_dmg, span_dmg / FPS))
    out.append('  用「现默认 watch（512KB）」：需要 %.0f 条 ring（%.0f MB ring.bin）'
               % (pf_full * span_dmg, pf_full * span_dmg * 24 / 1048576.0))
    out.append('  用「候选 0x0055B7A0-0x0055C000」：')
    for t in rep:
        pf = rep[t]['scheme']['候选 0x0055B7A0-0x0055C000（桶数组+哨兵）']['per_frame']
        if pf:
            out.append('     %s 采样率 %.3f 条/帧 ⇒ 覆盖该窗口需要 %.0f 条（%.1f MB）；'
                       '若保持 262144 条，可覆盖 %.0f 帧 ≈ %.1f s'
                       % (t, pf, pf * span_dmg, pf * span_dmg * 24 / 1048576.0,
                          262144 / pf, 262144 / pf / FPS))
    out.append('')
    out.append('ring 容量 → 两种 watch 的覆盖帧数/秒数：')
    for cap in (262144, 1048576, 1572864, 2097152):
        out.append('  ring = %8d 条（%5.1f MB）' % (cap, cap * 24 / 1048576.0))
        for t in rep:
            for name in ('现默认 0x00500000-0x00580000', '候选 0x0055B7A0-0x0055C000（桶数组+哨兵）'):
                pf = rep[t]['scheme'][name]['per_frame']
                if pf:
                    out.append('     %s / %-40s %8.0f 帧 ≈ %6.1f s'
                               % (t, name, cap / pf, cap / pf / FPS))
    txt = '\n'.join(out)
    print(txt)
    p = os.path.join(ROOT, 'work', 'builds', 'GR_SPINFIX', 'out')
    open(os.path.join(p, 'ring_cover.txt'), 'w', encoding='utf-8', newline='\n').write(txt + '\n')
    json.dump(rep, open(os.path.join(p, 'ring_cover.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
