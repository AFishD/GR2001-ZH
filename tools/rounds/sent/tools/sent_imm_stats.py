# -*- coding: utf-8 -*-
r"""sent_imm_stats.py —— 把普查 JSON 汇总成报告要用的统计（只读）。"""
import collections
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..'))
AUD = os.path.join(ROOT, 'work', 'builds', 'GR_SENT', 'audit')
FILES = (('ORIG   (CVAR_04 用的原盘 ELF)', 'D_imm_census_orig.json'),
         ('ZH113b (汉化盘内 ELF)', 'D_imm_census_zh113b.json'))

_OUT = open(os.path.join(AUD, 'J_imm_stats.txt'), 'w', encoding='utf-8')


def print(*a):                                                            # noqa: A001
    import sys as _s
    line = ' '.join(str(x) for x in a)
    _OUT.write(line + '\n')
    _s.stdout.write(line + '\n')


for (tag, fn) in FILES:
    d = json.load(open(os.path.join(AUD, fn), encoding='utf-8'))
    sites = d['i_type_sites']
    data = [s for s in sites if s['word'] in (0x000000B1, 0x000000B5)]
    print('=' * 88)
    print('== %s' % tag)
    print('   全 ELF imm16∈{00B1,00B5,FFB1,FFB5} 站点 = %d' % len(sites))
    print('   opcode 分布 : %s' % dict(collections.Counter(s['opname'] for s in sites).most_common(14)))
    print('   kind   分布 : %s' % dict(collections.Counter(s['kind'] for s in sites)))
    print('   lui+ori 拼出的 32 位常量 : %d' % len(d['lui_pairs']))
    print('   word 恰为 0x000000B1/B5（数据表里的 4 字节项，反汇编误读成 SPECIAL）: %d' % len(data))
    rng = collections.Counter()
    for s in data:
        rng['0x%05X000-0x%05XFFF' % (s['va'] >> 12, s['va'] >> 12)] += 1
    print('      按 4 KB 页聚类 : %s' % dict(sorted(rng.items())))
    # 「把常量装进寄存器」的 24/26 处细分
    mat = [s for s in sites if s['op'] in (0x08, 0x09) and s['rs'] == 0]
    others = [s for s in mat if not (0x219A70 <= s['va'] < 0x219E00)
              and not (0x21AD10 <= s['va'] < 0x21AE60)]
    print('   `addiu/addi rX,zero,imm` = %d 处（DrawString 8 + CharWidth 2 + 其它 %d）'
          % (len(mat), len(others)))
    for s in others:
        print('      0x%08X  0x%08X  %s' % (s['va'], s['word'], s['dis']))
    ori = [s for s in sites if s['op'] == 0x0D]
    for s in ori:
        print('   `ori` 0x%08X  0x%08X  %s' % (s['va'], s['word'], s['dis']))
    slt = [s for s in sites if s['op'] in (0x0A, 0x0B)]
    print('   `slti/sltiu` 区间边界 = %d 处：' % len(slt))
    for s in slt:
        print('      0x%08X  0x%08X  %s' % (s['va'], s['word'], s['dis']))
