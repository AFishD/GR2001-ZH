# -*- coding: utf-8 -*-
r"""r61_control_pos.py — 测试页载荷里"可疑控制字节"出现的位置。

动机: 已证实测试页正文**根本没进 RAM / 没进 drawlog** (解析/取文本阶段就失败)。
      现在找"最可能让引擎提前终止"的字节出现在**多靠前**的位置:
        · 0xFF  —— 很多 PS2 文本系统用它做串终止符
        · 0x80..0x9F —— 控制码常用区
      位置越靠前, 越能解释"整页空白"。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402
import inject_text_csv as inj                                            # noqa: E402

cs = T.Charset()
ITEM = re.compile(rb'<item\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')


def body_of(iso_path, want):
    iso = T.Iso(iso_path)
    c = inj.Container(iso, 'SFXML', T.RES['SFXML']['copies'][0], cs)
    out = None
    for m in ITEM.finditer(c.blob):
        nm = NAME.search(m.group(1))
        if nm and cs.decode(nm.group(1))[0] == want:
            mo = re.compile(rb'<text>').search(c.blob, m.start())
            mc = re.compile(rb'</text>').search(c.blob, mo.end())
            out = c.blob[mo.end():mc.end()]
            break
    iso.close()
    return out


def main():
    for ver, want in (('GR_TEST_FONT2', '开发访谈 1'), ('GR_ZH109', '开发访谈 1')):
        b = body_of(os.path.join(REPO, 'work', 'builds', ver, '%s.iso' % ver), want)
        print('\n===== %s / %s : 载荷 %d B =====' % (ver, want, len(b)))
        print('  开头 40 B hex : %s' % b[:40].hex(' '))
        print('  解码          : %r' % cs.decode(b[:40])[0])
        p1 = b.find(b'{p}')
        print('  第 1 个 {p} 在偏移 %d; 其后 27 B = %s'
              % (p1, b[p1:p1 + 27].hex(' ') if p1 >= 0 else '-'))
        ff = [i for i, x in enumerate(b) if x == 0xFF]
        lo = [i for i, x in enumerate(b) if 0x80 <= x <= 0x9F]
        print('  0xFF 位置 (前 12) = %s  共 %d 个' % (ff[:12], len(ff)))
        print('  0x80..0x9F 位置 (前 12) = %s  共 %d 个' % (lo[:12], len(lo)))
        # 连续段: 0x80..0x9F 的连续游程
        runs, cur = [], []
        for i, x in enumerate(b):
            if 0x80 <= x <= 0x9F:
                cur.append(i)
            else:
                if len(cur) >= 3:
                    runs.append((cur[0], len(cur)))
                cur = []
        if len(cur) >= 3:
            runs.append((cur[0], len(cur)))
        print('  0x80..0x9F 的连续游程 (>=3) = %s' % runs[:8])
    return 0


if __name__ == '__main__':
    sys.exit(main())
