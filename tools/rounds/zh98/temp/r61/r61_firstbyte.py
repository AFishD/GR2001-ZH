# -*- coding: utf-8 -*-
r"""r61_firstbyte.py — 检验"正文**开头字节**触发了引擎的提前终止"这一假设。

证据链现状:
  · 测试页 (GR_TEST_FONT2) 的正文编码字节**在 EE RAM 里完全不存在** (0 次), 也从未进 drawlog;
    而同页的 item 名「开发访谈 1」在 RAM 里有 4 份、标题正常渲染。
    ⇒ 失败发生在"引擎把 <text> 载荷变成可用字符串"这一步 (解析/取文本), 不是渲染。
  · 测试页正文按**编码字节升序**排列 ⇒ 开头就是码表里最小的那些码:
    《》享伞促凝双吸 = 单字节码 80 81 82 83 84 85 86 87。
  · 原版正文开头是 bd a1 b0 f0 … (正常的对偶码/较大单字节码)。

本脚本: 把 GR_ZH109 **全部 69 个 SFXML <text> 载荷**的"开头第一个字节"统计出来,
看 0x80..0xA0 这一带**有没有任何一个已交付文本是以它开头的**。
若一个都没有 (而测试页正是), 那"开头字节"就是最强嫌疑。

用法: python work/builds/GR_ZH98/temp/r61/r61_firstbyte.py
"""
import collections
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


def payloads(iso_path):
    iso = T.Iso(iso_path)
    spec = T.RES['SFXML']['copies'][0]
    c = inj.Container(iso, 'SFXML', spec, cs)
    out = []
    for m in ITEM.finditer(c.blob):
        nm = NAME.search(m.group(1))
        name = cs.decode(nm.group(1))[0] if nm else '?'
        mo = re.compile(rb'<text>').search(c.blob, m.start())
        if not mo:
            continue
        mc = re.compile(rb'</text>').search(c.blob, mo.end())
        body = c.blob[mo.end():mc.start()]
        if body:
            out.append((name, body))
    iso.close()
    return out


def main():
    for ver in ('GR_ZH109', 'GR_TEST_FONT2'):
        iso = os.path.join(REPO, 'work', 'builds', ver, '%s.iso' % ver)
        ps = payloads(iso)
        firsts = collections.Counter(b[0] for _n, b in ps)
        print('\n===== %s: 非空 <text> 载荷 %d 个 =====' % (ver, len(ps)))
        print('  开头字节分布 (按值升序): %s'
              % ' '.join('%02X×%d' % (k, v) for k, v in sorted(firsts.items())))
        low = [(n, b[0]) for n, b in ps if b[0] <= 0xA0]
        print('  ★ 开头字节 <= 0xA0 的条目 = %d 个 %s'
              % (len(low), ['%s(%02X)' % (n, x) for n, x in low[:12]]))
        t67 = [b for n, b in ps if n == '开发访谈 1']
        if t67:
            b = t67[0]
            print('  「开发访谈 1」开头 12 字节 = %s' % b[:12].hex(' '))
            print('     解码首行 = %r' % cs.decode(b[:60])[0][:24])
        mn = min(firsts)
        who = [n for n, b in ps if b[0] == mn]
        print('  全盘最小的开头字节 = %02X (出现在: %s)' % (mn, who[:5]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
