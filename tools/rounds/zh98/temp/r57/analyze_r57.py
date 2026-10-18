# -*- coding: utf-8 -*-
r"""r57 判据分析: 在 calib_r57.json 上试各种规则 (只读, 秒级)。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(io.open(os.path.join(HERE, 'calib_r57.json'), encoding='utf-8'))
old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_before_r56.json'))
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso'))

TRUE_OFFS = {0x50B820, 0x50B858, 0x50B870, 0x50B8A8, 0x50B8D8,
             0x50B840, 0x50B860, 0x50B890, 0x50B8C0, 0x50B8E8}
BAD = set(range(0x00, 0x20)) | set(range(0x7F, 0xA0))
BAD -= {9, 10, 13}

# ---- 每行的扩展特征 ----
code_hi = dict(old.codes)                     # byte -> char
print('单字节码: %d 个; 0xF0..0xFF 的单字节码 = %s'
      % (len(old.codes), {hex(b): code_hi[b] for b in range(0xF0, 0x100) if b in code_hi}))

# 全盘同串重复统计: 用 cstr_head 的前 24 字节 hex 当 key 太短; 用 (cstr_len, cstr_head)
key_count = {}
for r in rows:
    k = (r['cstr_len'], r['cstr_head'])
    key_count[k] = key_count.get(k, 0) + 1

for r in rows:
    off, nb = r['off'], r['nbytes']
    raw = bytes(iso.mm[off:off + nb])
    r['raw'] = raw.hex(' ')
    r['is_true'] = off in TRUE_OFFS
    r['dup'] = key_count[(r['cstr_len'], r['cstr_head'])]
    cs0, ce = r['cstr']
    cstr = bytes(iso.mm[cs0:ce])
    r['cstr_hex'] = cstr.hex(' ')
    r['cstr_text'] = old.decode(cstr)[0]
    # 串里 ASCII 字节分类
    asc = [b for b in cstr if b < 0x80]
    r['asc_letters'] = sum(1 for b in asc if chr(b).isalnum())
    r['asc_punct'] = sum(1 for b in asc if not chr(b).isalnum() and 0x20 <= b <= 0x7E)
    # 段内的"单字节码字"里有没有 0xF0+ 的高位码 (著/…)
    units = []
    i = 0
    while i < len(raw):
        v = raw[i]
        if v < 0x80:
            units.append((1, chr(v), v)); i += 1
        elif i + 1 < len(raw) and (v, raw[i + 1]) in old.pair_of:
            units.append((2, old.pair_of[(v, raw[i + 1])], v)); i += 2
        elif v in old.codes:
            units.append((1, old.codes[v], v)); i += 1
        else:
            break
    r['code_bytes'] = [u[2] for u in units]
    r['has_hi_code'] = any(u[0] == 1 and u[2] >= 0xF0 for u in units)
    r['n_pair'] = sum(1 for u in units if u[0] == 2)
    r['cstr_cjk'] = sum(1 for c in r['cstr_text'] if '\u4e00' <= c <= '\u9fff')
    r['cstr_units'] = len(old.decode(cstr)[0])
    r['cstr_pair_ratio'] = (sum(1 for u in [1] if True) and 0)
    t, offs2 = old.decode(cstr)
    npair = sum(1 for k in range(len(t)) if k + 1 < len(offs2) and (offs2[k + 1] - offs2[k]) == 2) if t else 0
    r['cstr_pair_ratio'] = round(npair / max(1, len(t)), 3)

print('\n==== 5 条载入提示条 (真文本) 的完整特征 ====')
for r in rows:
    if r['is_true']:
        print('  @0x%06X +%-2d %-8r pair=%.2f dup=%d span=0x%X..0x%X pre=%s post=%s'
              % (r['off'], r['nbytes'], r['text'], r['pair_ratio'], r['dup'],
                 r['span'][0], r['span'][1], r['span_pre'], r['span_post']))
        print('      raw=%s' % r['raw'])
        print('      cstr(%d) %r  hex=%s' % (r['cstr_len'], r['cstr_text'], r['cstr_hex']))
        print('      cstr_cjk=%d units=%d pair_ratio=%.2f asc_letters=%d asc_punct=%d dup=%d'
              % (r['cstr_cjk'], r['cstr_units'], r['cstr_pair_ratio'], r['asc_letters'],
                 r['asc_punct'], r['dup']))

RULES = {}


def add(name, fn):
    RULES[name] = fn


def base(r):
    return r['cstr_ctl'] == 0 and r['cstr_clean'] and r['cstr_ascii'] >= 1


add('B  (ctl=0 & clean & ascii>=1)', base)
add('B + 含对偶码', lambda r: base(r) and r['pair_ratio'] > 0)
add('B + pair>0 + 无0xF0+单字节码', lambda r: base(r) and r['pair_ratio'] > 0 and not r['has_hi_code'])
add('B + pair>0 + 整串对偶比>=0.5', lambda r: base(r) and r['pair_ratio'] > 0 and r['cstr_pair_ratio'] >= 0.5)
add('B + pair>0 + 同串重复>=2', lambda r: base(r) and r['pair_ratio'] > 0 and r['dup'] >= 2)
add('B + pair>0 + 同串重复>=4', lambda r: base(r) and r['pair_ratio'] > 0 and r['dup'] >= 4)
add('B + pair>0 + 同串重复>=4 + 串含>=2汉字段', lambda r: base(r) and r['pair_ratio'] > 0
    and r['dup'] >= 4 and r['cstr_cjk'] >= 6)
add('B + pair>0 + 无0xF0+ + 同串重复>=2', lambda r: base(r) and r['pair_ratio'] > 0
    and not r['has_hi_code'] and r['dup'] >= 2)

for nm, fn in RULES.items():
    sel = [r for r in rows if fn(r)]
    hit = sum(1 for r in sel if r['is_true'])
    print('\n判据 %-40s 选中 %5d (其中真文本 %d/10)' % (nm, len(sel), hit))
    fp = [r for r in sel if not r['is_true']]
    for r in fp[:12]:
        print('    ✗ @0x%06X +%-2d %-10r raw=%-22s cstr(%d)=%r'
              % (r['off'], r['nbytes'], r['text'], r['raw'], r['cstr_len'], r['cstr_text']))
    if len(fp) > 12:
        print('    … 假阳还有 %d 段' % (len(fp) - 12))

# ---- 真文本的 5 个 C 串, 在盘上各出现几次? ----
print('\n==== 真文本 C 串在全盘的重复次数 (前 24B hex 口径) ====')
for r in rows:
    if r['is_true']:
        print('  @0x%06X len=%d dup=%d %r' % (r['off'], r['cstr_len'], r['dup'], r['cstr_text']))
iso.close()
