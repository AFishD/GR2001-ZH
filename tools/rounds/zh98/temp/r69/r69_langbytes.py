# -*- coding: utf-8 -*-
r"""r69_langbytes.py — 直接读盘上 LANG 条目 (LANG:G048.I008 = 战术演习练习1 简报正文) 的原始字节。

目的: 证明简报正文里是**真标签** `{p}` / `{br}` (0x7B .. 0x7D), 而不是裸 0x0A。
因为 `{`/`}` 标签扫描**只存在于 RSHTML::CreateStrings** (标签串 "br"@0x578678 / "p"@0x578680),
所以"简报正文吃 {p}/{br}"⇒ 简报正文组件也是 RSHTML ⇒ 光判类型不够, 必须加宽度判据。

用法: python r69_langbytes.py <iso> [条目序号]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, 'tools', 'text_csv')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))


def main():
    iso_path = sys.argv[1]
    import inject_text_csv as inj                                          # noqa: E402
    import tcslib as T                                                     # noqa: E402
    cs = T.Charset()
    iso = T.Iso(iso_path)
    spec = T.RES['LANG']['copies'][0]                     # MENU.IMG #25
    c = inj.Container(iso, 'LANG', spec, cs)
    blob = c.blob
    print('LANG@MENU payload = %d B' % len(blob))
    # 头部: {u32 组数} -> 每组 {u32 条数} -> 每条 {u32 len}{data}{u16 attr}
    p = 0
    ngroups = struct.unpack_from('<I', blob, p)[0]
    p += 4
    print('组数 = %d' % ngroups)
    g48 = None
    for g in range(ngroups):
        n = struct.unpack_from('<I', blob, p)[0]
        p += 4
        if g == 48:
            g48 = (p, n)
        for i in range(n):
            ln = struct.unpack_from('<I', blob, p)[0]
            if g == 48 and i == 8:
                data = blob[p + 4:p + 4 + ln]
                attr = struct.unpack_from('<H', blob, p + 4 + ln)[0]
                print('\nG048.I008: offset=%d len=%d attr=%04X' % (p, ln, attr))
                print('  hex : %s' % data.hex(' '))
                print('  文本: %r' % cs.decode(data)[0])
                bs = sorted(set(data))
                print('  用到 <0x20 的字节: %s' % ['%02X' % b for b in bs if b < 0x20])
                for tag in (b'{p}', b'{br}', b'{Warp}', b'{WRAP}'):
                    print('  含 %-8s : %s' % (tag.decode(), tag in data))
                return 0
            p += 4 + ln + 2
    print('没找到 G048.I008')
    return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
