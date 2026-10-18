# -*- coding: utf-8 -*-
r"""sent_tokprobe.py —— 探明 `0x126A20(x)` 的实参来源（原盘 ELF，只读）。

背景：全 ELF 立即数普查发现 `beq $a2, 0xB1/0xB5`（VA 0x5117CC / 0x5117DC）所在的
token 分发器 `0x511730` 用 `lhu $a2, 8($a1)` 取字段；而 `0x126A20(x)` 正是
「造对象并把 x 以 **16 位** 存到 +8」的构造函数（`sh $s1, 8($s0)` @0x126A4C）。

⇒ 要判定"这个 0xB1/0xB5 比较是不是**文本字节**的消费者"，只需看 650 个
`jal 0x126A20` 调用点里，实参 a0 是**从字符串里 lbu 出来的字节**，还是
另有来源（尺寸/枚举/指针/常量）。

用法：python sent_tokprobe.py [elf]
"""
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location(
    'cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

TARGET = 0x126A20
ELF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    ROOT, r'third_party\orig\ps2\slus_out\SLUS_206.13')

elf = CD.Elf(ELF)
va0, _off, fsz = elf.text()
sites = []
for va in range(va0, va0 + fsz - 4, 4):
    w = elf.word(va)
    if ((w >> 26) & 0x3F) == 3 and (((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)) == TARGET:
        sites.append(va)

print('jal 0x%08X 调用点 = %d 个' % (TARGET, len(sites)))
buckets = {}
rows = []
for va in sites:
    win = [(v, elf.word(v)) for v in range(max(va0, va - 16), va + 4, 4)]
    # a0 的最近一次定义
    src, defin = 'unk', None
    for (v, w) in reversed(win[:-1]):
        op, rs, rt, rd = (w >> 26) & 0x3F, (w >> 21) & 0x1F, (w >> 16) & 0x1F, (w >> 11) & 0x1F
        fn = w & 0x3F
        if op == 0x24 and rt == 4:                     # lbu a0
            src, defin = 'lbu->a0', v
            break
        if op == 0x20 and rt == 4:                     # lb a0
            src, defin = 'lb->a0', v
            break
        if op == 0x09 and rt == 4 and rs == 0:         # addiu a0,zero,imm
            src, defin = 'addiu_imm:%d' % (w & 0xFFFF), v
            break
        if op == 0x0F and rt == 4:                     # lui a0
            src, defin = 'lui', v
            break
        if op == 0x25 and rd == 4:                     # or a0,... (pcpyld 风格)
            src, defin = 'or->a0', v
            break
        if op == 0x21 and rd == 4:
            src, defin = 'addu->a0', v
            break
        if op == 0x23 and rt == 4:                     # lw a0
            src, defin = 'lw->a0', v
            break
        if op == 0x00 and fn in (0x02, 0x03) and rd == 4:
            src, defin = 'shift->a0', v
            break
    buckets[src.split(':')[0]] = buckets.get(src.split(':')[0], 0) + 1
    rows.append((va, src, defin))

print('\n== a0 来源直方图 ==')
for k in sorted(buckets, key=lambda z: -buckets[z]):
    print('  %-14s %d' % (k, buckets[k]))

print('\n== `addiu a0,zero,imm`（小整数实参）的取值分布 ==')
from collections import Counter                                                     # noqa: E402
c = Counter()
for (va, src, defin) in rows:
    if src.startswith('addiu_imm'):
        v = int(src.split(':')[1])
        c[v if v < 0x8000 else v - 0x10000] += 1
for v, n in sorted(c.items(), key=lambda z: -z[1]):
    print('  %6d (0x%04X)  x%d' % (v, v & 0xFFFF, n))

print('\n== 逐站点（前 80 行 + 全部 lbu/lb 来源）==')
n = 0
for (va, src, defin) in rows:
    if src.startswith(('lbu', 'lb')) or n < 80:
        print('  0x%08X  a0<-%-14s @0x%s   %s' % (
            va, src, ('%08X' % defin) if defin else '----',
            CD.dis(elf.word(va), va)))
    n += 1

print('\n== `lb/lbu -> a0` 的站点全表（判定"文本字节喂进 token"的关键）==')
for (va, src, defin) in rows:
    if src.startswith(('lbu', 'lb')):
        ctx = []
        for v in range(max(va0, defin - 8), defin + 8, 4):
            ctx.append('%08X:%s' % (v, CD.dis(elf.word(v), v)))
        print('  jal@0x%08X  %s   ctx: %s' % (va, src, ' | '.join(ctx)))
