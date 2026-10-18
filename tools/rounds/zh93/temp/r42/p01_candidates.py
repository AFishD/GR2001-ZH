# -*- coding: utf-8 -*-
r"""p01_candidates.py — round42 步骤①: 枚举「候选图标字节」全集 (只读)

口径 (与 tcslib.Charset.decode 完全一致):
  引擎对字节 v:
    v < 0x80                     → ASCII
    0xA1 <= v < 0xB1 且 (v,v2) 在 pair_of → 对偶字 (吃 lead 那一位)
    v in codes                   → 单字节字
    否则                          → 本工具链回落成私有区 U+E0XX (= 引擎自己拿去画东西)

⇒ **候选图标字节** = 0xB1..0xFF 中「不在 codes 里」的那些。
   (0xA1..0xB0 是引擎的对偶 lead 区间, 把图标码写在那里会被当成 lead 吞掉后一个字,
    所以那不是合法图标码 —— 但为了完整, 这里也一并列出来标注。)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib  # noqa: E402

cs = tcslib.Charset()
codes = cs.codes                       # byte -> char  (单字节码)
pair_leads = set(b1 for (b1, _b2) in cs.enc_pair.values())
pair_trails = set(b2 for (_b1, b2) in cs.enc_pair.values())

print('=' * 78)
print('字符集现状 (charset_compiled_zh16.json)')
print('  单字节码 : %d 个' % len(codes))
print('  对偶码   : %d 个 (lead %d 种, trail %d 种)'
      % (len(cs.enc_pair), len(pair_leads), len(pair_trails)))
print('  引擎 lead 区间 (ELF sltiu gate): 0x%02X..0x%02X'
      % (tcslib.LEAD_LO, tcslib.LEAD_HI - 1))
lo = min(codes)
print('  单字节码区间: 0x%02X..0x%02X' % (lo, max(codes)))
missing = sorted(set(range(lo, max(codes) + 1)) - set(codes))
print('  区间内空缺  : %s' % (' '.join('%02X' % b for b in missing) or '无'))

print()
print('=' * 78)
print('候选图标字节 = 0xB1..0xFF 减掉字符集已占用')
cand = [b for b in range(0xB1, 0x100) if b not in codes]
print('  合计 %d 个:' % len(cand))
for i in range(0, len(cand), 16):
    row = cand[i:i + 16]
    print('    ' + ' '.join('%02X' % b for b in row))
print()
print('  其中**同时也是对偶 lead / trail** 的 (写出去会干扰对偶解码):')
bl = [b for b in cand if b in pair_leads]
bt = [b for b in cand if b in pair_trails]
print('    lead  : %s' % (' '.join('%02X' % b for b in bl) or '无'))
print('    trail : %s' % (' '.join('%02X' % b for b in bt) or '无'))

print()
print('=' * 78)
print('★ 「真正干净」的候选 = 既不在 codes、也不是任何对偶的 lead/trail')
clean = [b for b in cand if b not in pair_leads and b not in pair_trails]
print('  合计 %d 个:' % len(clean))
for i in range(0, len(clean), 16):
    print('    ' + ' '.join('%02X' % b for b in clean[i:i + 16]))

print()
print('=' * 78)
print('逐个候选的可见性检查 (toolchain 视角)')
print('  %-6s %-10s %-6s %-6s %s' % ('byte', 'PUA', 'is_lead', 'is_trail', 'tcslib 判据'))
for b in cand:
    pua = chr(0xE000 + b)
    mark = tcslib.BTN_FMT % (0xE000 + b)
    why = cs.btn_code_ok(0xE000 + b)
    print('  0x%02X   U+%04X    %-6s %-8s %s'
          % (b, 0xE000 + b, 'yes' if b in pair_leads else '-',
             'yes' if b in pair_trails else '-', why or 'OK (可当图标标记)'))

out = os.path.join(HERE, 'candidates.json')
json.dump(dict(candidates=cand, clean=clean,
               pair_leads=sorted(bl), pair_trails=sorted(bt),
               charset_single=len(codes), charset_pair=len(cs.enc_pair),
               lead_range=[tcslib.LEAD_LO, tcslib.LEAD_HI]),
          open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('[out] %s' % out)
