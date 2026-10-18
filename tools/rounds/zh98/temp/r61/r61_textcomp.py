# -*- coding: utf-8 -*-
r"""r61_textcomp.py — 对比两个盘上「开发访谈 1」页的**文本组件状态** (drawlog 站点 21C4C0)。

21C4C0 = RSTextComponent::DrawTheString 入口, 日志字段:
  COMP=组件指针 font=字体 style=样式 ax,ay=锚 W,H=组件尺寸 cx,cy f4 f8 top=裁剪上界 sw=字符串对象
  然后 "| " 后面是字符串数据的前 24 字节 (hex)。

想知道的事 (任务书 ③): 那一页到底建了哪些文本组件、尺寸/字符串是什么 ——
"解析失败"(组件在但字符串空/尺寸退化) 与 "渲染不出"(字符串在但没画出来) 的区别就在这里。

用法: python work/builds/GR_ZH98/temp/r61/r61_textcomp.py <drawlog> [标签]
"""
import io
import re
import sys

sys.path.insert(0, 'tools/capture')
import nav_hook as N                                                     # noqa: E402

RX = re.compile(
    r'F(\d+) PC=21C4C0 COMP=(\w+) font=(\w+) style=(\w+) ax=(-?\d+) ay=(-?\d+) '
    r'W=(-?\d+) H=(-?\d+) cx=(-?\d+) cy=(-?\d+) f4=(-?\d+) f8=(-?\d+) top=(-?\d+) sw=(\w+)')


def main():
    path = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else path
    comps = {}
    for ln in io.open(path, encoding='utf-8', errors='replace'):
        m = RX.search(ln)
        if not m:
            continue
        g = m.groups()
        comp = g[1]
        raw = b''
        if '|' in ln:
            try:
                raw = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:24])
            except Exception:                                        # noqa: BLE001
                raw = b''
        txt = N.dec_bytes(raw)
        rec = comps.setdefault(comp, {'n': 0, 'W': int(g[6]), 'H': int(g[7]),
                                      'ax': int(g[4]), 'ay': int(g[5]),
                                      'cx': int(g[8]), 'cy': int(g[9]),
                                      'f4': int(g[10]), 'f8': int(g[11]),
                                      'top': int(g[12]), 'font': g[2], 'style': g[3],
                                      'texts': set()})
        rec['n'] += 1
        if txt:
            rec['texts'].add(txt[:28])
    print('===== %s : 21C4C0 文本组件 %d 个 =====' % (tag, len(comps)))
    print('%-10s %-5s %-6s %-6s %-6s %-6s %-6s %-8s %s'
          % ('COMP', 'n', 'W', 'H', 'cx', 'cy', 'top', 'style', '文本(前28字)'))
    rows = sorted(comps.items(), key=lambda kv: -kv[1]['n'])
    for comp, r in rows:
        ts = ' / '.join(sorted(r['texts'])[:3])
        print('%-10s %-5d %-6d %-6d %-6d %-6d %-6d %-8s %s'
              % (comp, r['n'], r['W'], r['H'], r['cx'], r['cy'], r['top'], r['style'], ts))
    big = [c for c, r in comps.items() if r['W'] > 100 and r['H'] > 100]
    print('\n大组件 (W>100 且 H>100) = %d 个:' % len(big))
    for c in big:
        r = comps[c]
        print('   %s  W=%d H=%d top=%d style=%s  文本=%s'
              % (c, r['W'], r['H'], r['top'], r['style'],
                 sorted(r['texts'])[:2] or '**空**'))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
