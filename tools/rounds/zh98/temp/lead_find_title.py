# -*- coding: utf-8 -*-
r"""lead_find_title.py — 决定性实验: 在盘上搜索 SFXML:T0063 标题的"新编码"与"重排前旧编码"字节

若旧编码字节仍存在于盘上某处 ⇒ 那里就是 repack 重编码的漏网容器(重排后画错字的根因)。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
CUR = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
OLD = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46', 'charset_before_repack.json')

cur = json.load(io.open(CUR, encoding='utf-8'))
old = json.load(io.open(OLD, encoding='utf-8')) if os.path.isfile(OLD) else None
print('当前 charset pair_of=%d ; 重排前备份=%s pair_of=%d'
      % (len(cur['pair_of']), '有' if old else '无', len(old['pair_of']) if old else 0))


def enc(cs, s):
    out = bytearray()
    miss = []
    for ch in s:
        if ch in cs['pair_of']:
            b1, b2 = cs['pair_of'][ch]
            out += bytes([b1, b2])
        elif ch in cs.get('codes', {}):
            out.append(cs['codes'][ch])
        else:
            miss.append(ch)
    return bytes(out), miss


TITLE = '何为幽灵'
cur_b, m1 = enc(cur, TITLE)
old_b, m2 = enc(old, TITLE) if old else (None, [])
print('  标题「%s」' % TITLE)
print('    当前编码 : %s   (缺字 %s)' % (cur_b.hex(' '), m1 or '无'))
if old_b:
    print('    重排前编码: %s   (缺字 %s)' % (old_b.hex(' '), m2 or '无'))
    print('    两者相同 ? %s' % (cur_b == old_b))

data = open(ISO, 'rb').read()
print()
print('盘上搜索 (GR_ZH98, %d 字节):' % len(data))


def find_all(pat, label):
    hits = []
    i = data.find(pat)
    while i >= 0 and len(hits) < 12:
        hits.append(i)
        i = data.find(pat, i + 1)
    print('  %-16s %s  → %d 处 %s' % (label, pat.hex(' '), len(hits),
          ['0x%X' % h for h in hits[:8]]))
    return hits


h_new = find_all(cur_b, '当前编码')
if old_b and old_b != cur_b:
    h_old = find_all(old_b, '重排前编码')
    print('  ⇒ 旧编码在盘上%s' % ('**仍然存在** ⇒ 找到漏网容器!' if h_old else '已不存在(说明重编码覆盖到了)'))
# 单个字也搜一遍 (标题可能被拆开存)
for ch in TITLE:
    if ch in cur['pair_of']:
        b = bytes(cur['pair_of'][ch])
        ob = bytes(old['pair_of'][ch]) if old and ch in old['pair_of'] else None
        n_new = data.count(b)
        n_old = data.count(ob) if ob and ob != b else -1
        print('    %s 当前 %s 出现 %d 次%s' % (ch, b.hex(' '), n_new,
              ('; 旧 %s 出现 %d 次' % (ob.hex(' '), n_old)) if n_old >= 0 else ''))
# 定位命中处属于哪个容器
if h_new:
    import struct
    off = h_new[0]
    print()
    print('首个命中在 0x%X ; 该扇区号 %d ; 附近 64 字节:' % (off, off // 2048))
    print('   ', data[max(0, off - 32):off + 64].hex(' '))
