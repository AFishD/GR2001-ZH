# -*- coding: utf-8 -*-
r"""charset_probe.py — 读 charset 现状 (给报告用), 输出 JSON 到 temp/ 免得 GBK 控制台炸"""
import json
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def slot(v):
    return (v[0] - 0xA1) * 94 + (v[1] - 0xA1)


d = json.load(io.open(CS, encoding='utf-8'))
po, co = d['pair_of'], d['codes']
inv = {slot(v): (c, tuple(v)) for c, v in po.items()}
out = dict(path=CS, size=os.path.getsize(CS),
           mtime=os.path.getmtime(CS),
           pair_of=len(po), codes=len(co),
           slots_min=min(inv), slots_max=max(inv), unique_slots=len(inv),
           top=[dict(slot=s, ch=inv[s][0], pair=list(inv[s][1]),
                     cp='U+%04X' % ord(inv[s][0]) if len(inv[s][0]) == 1 else '?')
                for s in sorted(inv) if s >= 2340],
           codes_ge_a0={('0x%02X' % c): ch for ch, c in sorted(co.items(), key=lambda kv: kv[1])
                        if c >= 0xA0},
           codes_has_b6_b9={('0x%02X' % c): ch for ch, c in co.items() if 0xB6 <= c <= 0xB9},
           meta_keys=[k for k in d if k.startswith('_')])
# 反查: 5 个借槽字在 charset 里的"字符名"
for want in ('按', '时', '小', '击', '\u2715', '\ue0b5', '\u25b3'):
    s = po.get(want)
    out.setdefault('lookup', {})['U+%04X' % ord(want)] = (
        dict(slot=slot(s), pair=list(s)) if s else None)
json.dump(out, io.open(os.path.join(HERE, 'charset_probe.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('pair_of=%d codes=%d slots=%d..%d unique=%d'
      % (out['pair_of'], out['codes'], out['slots_min'], out['slots_max'], out['unique_slots']))
for t in out['top']:
    print('   slot %4d = %-4s %s  %s' % (t['slot'], t['cp'], t['pair'], repr(t['ch'])))
print('codes>=0xA0:', out['codes_ge_a0'])
print('codes 0xB6..0xB9:', out['codes_has_b6_b9'])
print('lookup:', json.dumps(out['lookup'], ensure_ascii=False))
print('meta keys:', out['meta_keys'])
