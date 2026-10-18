# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath('.')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import tcslib as T
import icon_table
cs = T.Charset()
print('charset 单字节码 =', len(cs.enc_single), ' 对偶 =', len(cs.enc_pair))
print('codes[0xE7] =', repr(cs.codes.get(0xE7)), ' codes[0xF1] =', repr(cs.codes.get(0xF1)))
print("decode(0xE7) =", repr(cs.decode(b'\xE7')[0]))
print("decode(Fran\\xE7ais) =", repr(cs.decode(b'Fran\xE7ais')[0]))
print("decode(Espa\\xF1ol) =", repr(cs.decode(b'Espa\xF1ol')[0]))
print("encode_strict('Français') =", cs.encode_strict('Français'))
print("encode_strict('{{BTN:E0E7}}') =", cs.encode_strict('{{BTN:E0E7}}'))
print("encode_strict('{{BTN:E0F1}}') =", cs.encode_strict('{{BTN:E0F1}}'))
print("scan_marks ok:", cs.scan_marks('Fran{{BTN:E0E7}}ais')[1])
print("is_icon(0xE7/0xF1) =", icon_table.is_icon(0xE7), icon_table.is_icon(0xF1))
print("candidate_bytes =", ['%02X'%b for b in icon_table.candidate_bytes(cs)])
ok, lines = icon_table.selfcheck(cs)
for ln in lines[-14:]: print(' ', ln)
print('icon_table 自检:', '通过' if ok else '失败')
for nm, fn in (('selfcheck_charset', lambda: T.selfcheck_charset(cs)),
               ('selfcheck_newlines', lambda: T.selfcheck_newlines(cs))):
    o, d = fn()
    print('%s: %s' % (nm, '通过' if o else '失败'))
    for ln in d:
        if ln.startswith('[!!]'): print('   ', ln)
