# -*- coding: utf-8 -*-
r"""p22_icon_table_selfcheck.py — round42: icon_table 自检 (不需要 ISO)"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import icon_table as IT                                          # noqa: E402
import tcslib                                                    # noqa: E402

ok = 0
bad = []


def chk(c, msg):
    global ok
    if c:
        ok += 1
        print('  [ok] %s' % msg)
    else:
        bad.append(msg)
        print('  [!!] %s' % msg)


print('=== 1) 码位归一化 ===')
for x, want in ((0xB1, 0xE0B1), (0xE0B1, 0xE0B1), ('{{BTN:E0B1}}', 0xE0B1),
                ('{{btn:e0b5}}', 0xE0B5), ('\ue0b1', 0xE0B1), ('B5', 0xE0B5),
                ('E0B5', 0xE0B5)):
    got = IT.code_of(x)
    chk(got == want, 'code_of(%r) = %s (期望 U+%04X)' % (x, 'None' if got is None else 'U+%04X' % got, want))
for x in (0x41, 0xFF):
    chk(IT.code_of(x) == IT.PUA_BASE + x,
        'code_of(%r) = U+%04X (0x00..0xFF 一律按**字节**解释)' % (x, IT.PUA_BASE + x))
for x in ('abc', 0x1234, 0x100):
    chk(IT.code_of(x) is None, 'code_of(%r) = None (认不出来不抛异常)' % (x,))
chk(IT.code_of('{{BTN:1234}}') == 0x1234 and IT.icon_info('{{BTN:1234}}') is None,
    "语法合法但**不是图标码**的 {{BTN:1234}} ⇒ code_of=0x1234, icon_info=None "
    "(格式合法 ≠ 引擎认得)")

print()
print('=== 2) 图标判定 (只有 0xB1/0xB5) ===')
for b in range(0x80, 0x100):
    want = b in (0xB1, 0xB5)
    if IT.is_icon(b) != want:
        bad.append('is_icon(0x%02X) 错了' % b)
chk(not any('is_icon(0x%02X)' % b in bad for b in range(0x80, 0x100)),
    '0x80..0xFF 里 is_icon() 为真的**只有** 0xB1/0xB5 (穷举 128 个字节)')
chk(IT.icon_name(0xB1) == '△ 三角键', 'icon_name(0xB1) = %r' % IT.icon_name(0xB1))
chk(IT.icon_name(0xB5) == '✕ 叉键', 'icon_name(0xB5) = %r' % IT.icon_name(0xB5))
chk(IT.icon_key(0xB1) == 'triangle' and IT.icon_key(0xB5) == 'cross',
    'icon_key: 0xB1=triangle, 0xB5=cross')
chk(IT.icon_info(0xE7) is None and IT.is_known_not_icon(0xE7),
    '0xE7 不是图标, 而是 ç (Latin-1)')
chk(IT.icon_info(0xF1) is None and IT.is_known_not_icon(0xF1),
    '0xF1 不是图标, 而是 ñ (Latin-1)')
chk(IT.engine_icon_bytes() == (0xB1, 0xB5), 'engine_icon_bytes() = %s' % (IT.engine_icon_bytes(),))
chk(len(IT.all_icons()) == 2, 'all_icons() 共 %d 个' % len(IT.all_icons()))

print()
print('=== 3) 候选枚举 (本盘字符集) ===')
cs = tcslib.Charset()
cands = IT.candidate_bytes(cs)
print('  候选字节 %d 个: %s' % (len(cands), ' '.join('%02X' % b for b in cands)))
chk(cands == [0xB1, 0xB5, 0xE7, 0xF1], '候选 = B1 B5 E7 F1 (与现役盘一致)')
chk(set(IT.engine_icon_bytes()) <= set(cands), '引擎认的图标码都在候选里')
chk(IT.candidate_bytes()[:3] == [0xB1, 0xB2, 0xB3], '不传 charset ⇒ 只按区间返回')

print()
print('=== 4) 标记格式与 tcslib 兼容 (格式零变化) ===')
for b in (0xB1, 0xB5):
    m = IT.MARK_FMT % (IT.PUA_BASE + b)
    chk(tcslib.BTN_FMT % (0xE000 + b) == m, '标记格式与 tcslib 一致: %s' % m)
    chk(cs.marks_to_pua(m) == chr(0xE000 + b), '%s ↔ U+%04X' % (m, 0xE000 + b))
    chk(cs.encode_strict(m) == bytes([b]), '%s 编码为字节 0x%02X' % (m, b))
    chk(tcslib.is_btn_mark(m) and cs.is_placeholder(m), '%s 仍被 tcslib 认作合法标记' % m)

print()
print('=== 5) describe / summary_lines ===')
for b in (0xB1, 0xB5, 0xE7, 0xF1, 0xB2):
    print('  0x%02X → %s' % (b, IT.describe(b, cs)))
print()
for ln in IT.summary_lines(cs):
    print('  %s' % ln)

print()
print('=' * 72)
print('icon_table 自检: %d 通过 / %d 失败' % (ok, len(bad)))
if bad:
    for b in bad:
        print('  [!!] %s' % b)
sys.exit(1 if bad else 0)
