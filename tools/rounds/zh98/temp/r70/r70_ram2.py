# -*- coding: utf-8 -*-
r"""r70_ram2.py — 对已解出的 EE/IOP RAM 做探针（7z 解出的目录）
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
D = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r70', 'ram')
ee = open(os.path.join(D, 'eeMemory.bin'), 'rb').read()
iop = open(os.path.join(D, 'iopMemory.bin'), 'rb').read()
c = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                   'charset_compiled_zh16.json'), encoding='utf-8'))
pair = {(a, b): ch for ch, (a, b) in c['pair_of'].items()}
sing = {}
for ch, v in c['codes'].items():
    sing[v] = ch
print('EE %d B  IOP %d B  pair表 %d 单字节 %d' % (len(ee), len(iop), len(pair), len(sing)))


def enc(s):
    o = bytearray()
    for ch in s:
        if ord(ch) < 0x80:
            o.append(ord(ch))
        elif ch in c['pair_of']:
            o += bytes(c['pair_of'][ch])
        elif ch in sing_rev:
            o.append(sing_rev[ch])
        else:
            return None
    return bytes(o)


sing_rev = {v: k for k, v in sing.items()}

print()
print('=== 探针1: 盘代判定 (字符串在 RAM 里的出现次数) ===')
probes = ['战后回顾', '你胜利了', '任务目标', '营救飞行员', '营救武器官', '前往撤离区',
          '摧毁机载设备', '游戏类型', '难度', '新兵', '已过时间', '最佳时间', '继续', '退出',
          '查看结果', '接受', '荒漠围攻', '沙漠风暴', '斯科特', '拉米雷斯', '拉默雷斯',
          '破片手榴弹', '杀伤手雷', '伞兵型', '短型', '载入', '保存', '读取',
          '幽灵行动', '幽灵', '任务完成', '胜利']
for s in probes:
    b = enc(s)
    if b is None:
        print('  %-14s (charset 外, 跳过)' % s)
        continue
    n1 = ee.count(b)
    n2 = iop.count(b)
    mark = '★' if n1 else ' '
    print('  %s %-14s EE %4d 次   IOP %3d 次' % (mark, s, n1, n2))

print()
print('=== 探针2: EE RAM 里的中文串 (>=6 个汉字, 前 30 条) ===')
out = []
i = 0
n = len(ee)
while i < n - 1 and len(out) < 30:
    if 0xA1 <= ee[i] <= 0xB0 and (ee[i], ee[i + 1]) in pair:
        j = i
        buf = []
        while j < n - 1 and 0xA1 <= ee[j] <= 0xB0 and (ee[j], ee[j + 1]) in pair:
            buf.append(pair[(ee[j], ee[j + 1])]); j += 2
        if len(buf) >= 6:
            out.append((i, ''.join(buf)))
        i = j
    else:
        i += 1
for off, s in out:
    print('   0x%08X  %s' % (off, s[:70]))
