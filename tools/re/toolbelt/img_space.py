# -*- coding: utf-8 -*-
r"""img_space.py — 量 GR.IMG / MENU.IMG 的内部可用空间（容器条目表 + 尾料 + 零填充）

为什么: 目标要求"完全利用整个 ISO 的空位实现完全扩容不缺字"。
        已证明"把大字形贴图写进 GR.IMG 的条目"是最优路线（不动 ISO）⇒ 前提是 GR.IMG 内部有空位。
        本脚本用 tcslib.img_entry 逐条读 off/stored/real, 算出每条余量与容器尾料。
用法: python img_space.py [<iso>]
"""
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
IMG_LBA = {'GR.IMG': 19175, 'MENU.IMG': 776286}
IMG_SIZE = {'GR.IMG': 1550563328, 'MENU.IMG': 58300882}

iso = tcslib.Iso(ISO)
print('ISO %s' % ISO)
print()

for label, lba in IMG_LBA.items():
    print('=' * 84)
    print('%s  @LBA %d  大小 %d B' % (label, lba, IMG_SIZE[label]))
    n = 0
    ents = []
    while n < 4000:
        try:
            e = iso.img_entry(lba, n)
        except Exception:
            break
        if e['name'].startswith('?'):
            break
        ents.append(e)
        n += 1
    print('  条目数(解析到) %d' % len(ents))
    # 统计
    tot_stored = sum(e['stored'] for e in ents)
    tot_real = sum(e['real'] for e in ents)
    tot_slack = sum(max(0, e['stored'] - e['real']) for e in ents)
    # 末尾条目之后到容器结尾
    last_end = max((e['off'] + e['stored']) for e in ents) if ents else 0
    tail = IMG_SIZE[label] - last_end
    print('  合计 stored %d B ; real %d B ; **条目内余量 %d B**' % (tot_stored, tot_real, tot_slack))
    print('  最后一条结束于 0x%X ⇒ **容器尾料 %d B**' % (last_end, tail))
    print('  ⇒ 该容器可用: 条目内余量 + 尾料 = **%d B**' % (tot_slack + tail))
    # 最大的 15 条余量
    top = sorted(ents, key=lambda e: -(e['stored'] - e['real']))[:15]
    print('  余量最大的 15 条:')
    for e in top:
        if e['stored'] - e['real'] <= 0:
            continue
        print('      %-34s off=0x%-9X stored=%-9d real=%-9d 余 %d' % (
            e['name'][:34], e['off'], e['stored'], e['real'], e['stored'] - e['real']))
    print()

iso.close()
