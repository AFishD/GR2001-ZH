# -*- coding: utf-8 -*-
r"""hgA10_strcheck.py — 只读: 检查 `TriggleForBlackCamera` 用 `huge` 面绘制的那三个字符串
在 EN / ZH 盘上分别是什么字节（决定中文是否会流经 huge 面）。

产出: work/builds/GR_HUGE/evidence/hgA10_strcheck.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

VAS = [0x585668, 0x585670, 0x585678, 0x585680, 0x585690, 0x5856A0]


def main():
    lines = []
    W = lines.append
    elfs = {}
    for tag in ('EN_ORIG', 'ZH113b', 'ZH113b_fix'):
        try:
            e, f = H.A.load_elf(tag)
        except Exception as ex:
            W('load %s 失败: %s' % (tag, ex))
            continue
        elfs[tag] = e
    for va in VAS:
        W('VA 0x%X  (ISO 0x%X)' % (va, H.VA2ISO))
        for tag, e in elfs.items():
            o = va - H.VA2FILE
            raw = e.b[o:o + 48]
            z = raw.find(b'\x00')
            s = raw[:z if z >= 0 else 48]
            asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in s)
            W('   %-12s %s   %r' % (tag, s.hex(' '), asc))
        W('')
    # ZH 里这些字符串是否被改成中文（含 >=0x80 字节）
    W('=' * 90)
    W('判定: ZH 盘中这些字节是否含 >= 0x80 的字节（= 会走 huge 面 idx>=96 的路径）')
    e = elfs.get('ZH113b')
    if e:
        for va in VAS:
            o = va - H.VA2FILE
            raw = e.b[o:o + 48]
            z = raw.find(b'\x00')
            s = raw[:z if z >= 0 else 48]
            hi = [c for c in s if c >= 0x80]
            W('  0x%X: len=%d  >=0x80 字节数=%d  %s' % (va, len(s), len(hi),
                                                        '★ 是（中文/全角会流经 huge）' if hi else '否'))
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA10_strcheck.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
