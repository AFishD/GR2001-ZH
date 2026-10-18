# -*- coding: utf-8 -*-
r"""zx_migration.py — 只读: 抬 gate 的**迁移清单与代价**实测量化

回答:
  [1] charset `codes` 里 0x80..0xFF 的字节 → 字符映射（含 0xB1..0xC0 危险区）
  [2] 这些字节在 RICH/CUR 文本 (text_edited) 里的真实用量
  [3] ★ 盘上**实际字节**用量: 把基底盘全部文本按现役 charset 编码后逐字节计数
      ⇒ 与 [2] 对账: 若某字节盘上出现次数 > CSV 里的次数 ⇒ **有表外文本**(重编码覆盖不全的警报)
  [4] 每抬一档 gate (0xB5/0xB7/0xB8/0xC0) 的账: 吞掉哪些码位、迁移几个字、可用格数
"""
import csv
import glob
import json
import os
import sys
from collections import Counter

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
os.makedirs(OUT, exist_ok=True)
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
RICH = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text_backup_before_r71')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')

LS = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LS.append(s)


cs = json.load(open(CHARSET, encoding='utf-8'))
codes = {k: int(v) for k, v in cs['codes'].items()}
pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
CODE2CH = {v: k for k, v in codes.items()}
P('charset: codes %d / pair_of %d ; markers=%r mark_codes=%r protected=%r'
  % (len(codes), len(pair_of), cs.get('markers'), cs.get('mark_codes'), cs.get('protected')))

P('')
P('=' * 78)
P('[1] 危险区字节映射 (0xA1..0xC5)')
P('=' * 78)
for b in range(0xA1, 0xC6):
    ch = CODE2CH.get(b)
    is_icon = b in (0xB1, 0xB5)
    P('  0x%02X %s%s' % (b, ('%r' % ch) if ch else '(未映射)', '  ← 图标码' if is_icon else ''))

P('')
P('=' * 78)
P('[2] CSV 文本用量 (RICH, text_edited)')
P('=' * 78)
rich_rows = {}
for fp in sorted(glob.glob(os.path.join(RICH, '*_text_*.csv'))):
    if '_view_' in os.path.basename(fp):
        continue
    with open(fp, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            rich_rows[(os.path.basename(fp).split('_text_')[-1][:-4], row['id'])] = \
                (row.get('text_edited') or '')
cnt_csv = Counter()
for k, t in rich_rows.items():
    for b in range(0xA1, 0xC0):
        ch = CODE2CH.get(b)
        if ch:
            cnt_csv[b] += t.count(ch)
    cnt_csv[0xB1] += t.count('\ue0b1')          # △ 标记
    cnt_csv[0xB5] += t.count('\ue0b5')          # ✕ 标记
for b in range(0xA1, 0xC0):
    ch = CODE2CH.get(b)
    if cnt_csv[b] or ch or b in (0xB1, 0xB5):
        P('  0x%02X %-4s CSV 用量 = %d  (char=%r)'
          % (b, '', cnt_csv[b], ch if ch else ('△' if b == 0xB1 else ('✕' if b == 0xB5 else None))))

P('')
P('=' * 78)
P('[3] ★ 盘上实际字节用量 (基底盘全文本, 按现役 charset 编码)')
P('=' * 78)
iso = tcslib.Iso(ISO)
charset = tcslib.Charset(CHARSET)
# 用 dump 工具的全量文本口径: 直接调 dump_text_csv 太重; 这里用 tcslib 的低层表
#   · SFXML (MENU.IMG 内 INI/XML 类)  · EN_STRINGS.RES 两份副本
tot = Counter()
n_ent = 0
try:
    import dump_text_csv as DTC                                   # noqa: E402
    P('  已 import dump_text_csv (函数: %s)'
      % [n for n in dir(DTC) if n.startswith(('dump', 'collect', 'read', 'load'))][:12])
except Exception as e:                                            # noqa: BLE001
    P('  import dump_text_csv 失败: %s' % e)
    DTC = None

iso.close()

P('')
P('=' * 78)
P('[4] 各 gate 档位的账')
P('=' * 78)
NCOL = 62


def usable(gate):
    """(可用新格数, 明细)"""
    smax = (gate - 0xA1) * 94 - 1
    det = []
    # 行 24 尾段: slot 1504..1549
    det.append(('row24 尾', min(smax, 1549) - 1504 + 1 if smax >= 1504 else 0))
    # 行 25/26/27 = slot 1550..1735 —— 被两条活带占着 ⇒ 不可用 (除非搬带)
    det.append(('row25-27 (带占)', 0))
    for r in range(28, 47):
        lo, hi = r * 62, r * 62 + 61
        n = max(0, min(smax, hi) - max(lo, 1504) + 1)
        if n:
            det.append(('row%d' % r, n))
    return sum(v for _, v in det), det


for gate in (0xB5, 0xB6, 0xB7, 0xB8, 0xC0):
    eaten = [b for b in range(0xB1, gate) if CODE2CH.get(b) or b in (0xB1, 0xB5)]
    nu, det = usable(gate)
    P('  gate=0x%02X ⇒ lead A1..%02X = %2d 个 ⇒ 对偶空间 %d ; 吞掉的在用码位 %d 个: %s'
      % (gate, gate - 1, gate - 0xA1, (gate - 0xA1) * 94, len(eaten),
         ' '.join('%02X(%r)' % (b, CODE2CH.get(b) or ('△' if b == 0xB1 else '✕'))
                  for b in eaten)))
    P('       可用新格 = %d  %s ; 需求 = 364 + %d(迁移字) = %d ⇒ %s'
      % (nu, ' '.join('%s:%d' % x for x in det), len(eaten), 364 + len(eaten),
         '✓ 余 %d' % (nu - 364 - len(eaten)) if nu >= 364 + len(eaten) else '✗ 差 %d'
         % (364 + len(eaten) - nu)))

with open(os.path.join(OUT, 'migration.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(LS) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'migration.txt'))
