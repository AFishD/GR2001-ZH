# -*- coding: utf-8 -*-
r"""r61_ctl_audit.py — 全语料审计: 已交付的 SFXML <text> 载荷里到底有没有 0x80..0x9F / 0xFF 这些字节?

这是"整页空白"根因假设的**直接判据**:
  若 58 个已交付载荷里**一个都不含** 0x80..0x9F, 而测试页在偏移 38 处**连续 20 个**,
  那么"0x80..0x9F 是引擎的控制码区, 出现在正文里会让整段文本取不出来"就有了实证基础
  (与"测试页正文在 RAM/drawlog 里完全不存在"这一实测完全吻合)。
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


def payloads(ver):
    iso = T.Iso(os.path.join(REPO, 'work', 'builds', ver, '%s.iso' % ver))
    c = inj.Container(iso, 'SFXML', T.RES['SFXML']['copies'][0], cs)
    out = []
    for m in ITEM.finditer(c.blob):
        nm = NAME.search(m.group(1))
        name = cs.decode(nm.group(1))[0] if nm else '?'
        mo = re.compile(rb'<text>').search(c.blob, m.start())
        if not mo:
            continue
        mc = re.compile(rb'</text>').search(c.blob, mo.end())
        b = c.blob[mo.end():mc.end()]
        if b:
            out.append((name, b))
    iso.close()
    return out


def main():
    for ver in ('GR_ZH109', 'GR_TEST_FONT2'):
        ps = payloads(ver)
        hit_ctl = [(n, sum(1 for x in b if 0x80 <= x <= 0x9F)) for n, b in ps
                   if any(0x80 <= x <= 0x9F for x in b)]
        hit_ff = [n for n, b in ps if 0xFF in b]
        print('\n===== %s: 非空 <text> 载荷 %d 个 =====' % (ver, len(ps)))
        print('  含 0x80..0x9F 的条目 = %d 个 %s' % (len(hit_ctl), hit_ctl[:8]))
        print('  含 0xFF 的条目      = %d 个 %s' % (len(hit_ff), hit_ff[:8]))
        # 最长连续游程
        worst = (0, '')
        for n, b in ps:
            run = best = 0
            for x in b:
                run = run + 1 if 0x80 <= x <= 0x9F else 0
                best = max(best, run)
            if best > worst[0]:
                worst = (best, n)
        print('  最长 0x80..0x9F 连续游程 = %d (条目: %s)' % worst)
    return 0


if __name__ == '__main__':
    sys.exit(main())
