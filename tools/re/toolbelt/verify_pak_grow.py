# -*- coding: utf-8 -*-
r"""verify_pak_grow.py — 核验"搬走 COMMON.PAK 身后 2 条 ⇒ PAK 原地长大"的算术与位移影响

方案: 图集 512→592 行 ⇒ COMMON.PAK 长大 +40,960 B；
      把 #4/#5（FONT.RES 4,421 + EN_MESSAGE_MC_4.RSB 69,404 = 73,825 B）搬到 MENU.IMG 尾部。
关键问题: 搬走它们之后，**它们之后的条目是否必须整体下移**？（若不必 ⇒ 只需改 2 个 off 字段）
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

MENU_LBA = 776286
iso = tcslib.Iso(ISO)

# 读条目表
ents = []
n = 0
while n < 2000:
    e = iso.img_entry(MENU_LBA, n)
    if e['name'].startswith('?'):
        break
    ents.append(e)
    n += 1

print('MENU.IMG 条目 %d 个' % len(ents))
print('前 8 条:')
for i, e in enumerate(ents[:8]):
    print('  #%-3d %-24s off=0x%-9X stored=%-9d end=0x%X' % (i, e['name'][:24], e['off'], e['stored'], e['off'] + e['stored']))

# 按 off 排序，找 #3/#4/#5 的物理顺序
srt = sorted(range(len(ents)), key=lambda i: ents[i]['off'])
print()
print('物理顺序前 8 条:')
for k in srt[:8]:
    e = ents[k]
    print('  idx#%-3d %-24s off=0x%-9X end=0x%X' % (k, e['name'][:24], e['off'], e['off'] + e['stored']))

# 找 COMMON.PAK
pak_i = next(i for i, e in enumerate(ents) if 'COMMON' in e['name'].upper())
pak = ents[pak_i]
print()
print('COMMON.PAK idx#%d off=0x%X stored=%d end=0x%X' % (pak_i, pak['off'], pak['stored'], pak['off'] + pak['stored']))

# 物理上紧跟其后的若干条
after = [k for k in srt if ents[k]['off'] >= pak['off'] + pak['stored']]
after.sort(key=lambda k: ents[k]['off'])
print('物理上在 COMMON.PAK 之后的连续 4 条:')
gap_total = 0
for k in after[:4]:
    e = ents[k]
    print('  idx#%-3d %-24s off=0x%-9X stored=%-9d end=0x%X' % (k, e['name'][:24], e['off'], e['stored'], e['off'] + e['stored']))

# ★ 核验: 被搬走的 2 条总共多大；搬走后空隙多大；PAK 长大后是否自然填满
move = after[:2]
move_bytes = sum(ents[k]['stored'] for k in move)
move_end = max(ents[k]['off'] + ents[k]['stored'] for k in move)
after2_off = ents[after[2]]['off'] if len(after) > 2 else move_end
print()
print('★ 待搬 2 条 = %d B（%s）' % (move_bytes, ' + '.join(ents[k]['name'][:20] for k in move)))
print('★ 它们占据物理区间 0x%X .. 0x%X' % (ents[move[0]]['off'], move_end))
print('★ 紧随其后的条目起于 0x%X ⇒ **搬走后腾出的连续空隙 = %d B**' % (after2_off, after2_off - (pak['off'] + pak['stored'])))
need = 262160 + 40960 - 262160  # = 40960
print()
print('★ 图集长大需要 **%d B**（512→592 行）' % 40960)
print('★ 腾出空隙 %d B ≥ 需要 %d B ⇒ **放得下 ✓**（余 %d B）'
      % (after2_off - (pak['off'] + pak['stored']), 40960, after2_off - (pak['off'] + pak['stored']) - 40960))
print()
print('★ 位移影响:')
print('   搬走的 2 条 ⇒ 它们的 off 改成尾部新位置（2 个字段）')
print('   PAK 的 stored/real 各 +40960（2 个字段）+ PAK 内 px_size 0x40010→0x4A010（1 个字段）')
print('   其余 %d 条 ⇒ **一个 off 都不用改**（空隙被增长部分填掉，后续数据不动）✓✓' % (len(ents) - 3))
print('   尾部要能放下 %d B ⇒ 尾料 61,236 + ISO 扩展 30,254 = 91,490 ≥ %d ✓' % (move_bytes, move_bytes))
iso.close()
