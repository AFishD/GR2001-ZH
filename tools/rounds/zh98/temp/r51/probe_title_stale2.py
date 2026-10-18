# -*- coding: utf-8 -*-
"""r51 探针⑯: SFXML 标题的"陈旧"量化 —— 用哪一版 charset 写的? 现在错成什么样? 能不能原位修? 只读。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

OLD = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'font',
                                  'charset_matching_this_disk.json'))
NEW = tcslib.Charset()
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso'))
spec = tcslib.RES['SFXML']['copies'][0]
e = iso.img_entry(spec[1], spec[2])
blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(e['iso_off'], e['stored'])))
iso.close()

ITEM = re.compile(rb'<(studio|item)\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')
rows = []
for m in ITEM.finditer(blob):
    nm = NAME.search(m.group(2))
    if not nm:
        continue
    v = nm.group(1)
    rows.append((m.group(1).decode(), v, OLD.decode(v)[0], NEW.decode(v)[0]))

diff = [r for r in rows if r[2] != r[3]]
print('属性总数 %d; 旧 charset 与现 charset 解出**不同**的: %d' % (len(rows), len(diff)))
print()
print('=== 全部不同的条目 (旧 = 当年写的正确文本 / 现 = 现在解出来的) ===')
for tag, v, o, n in diff:
    print('  %-6s 旧 %-28r 现 %r' % (tag, o[:28], n[:28]))

print()
print('=== 能不能"原位"修 (旧文本用现 charset 重编码, 字节长度必须不变) ===')
bad = []
for tag, v, o, n in diff:
    try:
        nb = NEW.encode_strict(o)
    except Exception as ex:                                               # noqa: BLE001
        bad.append((o[:16], 'encode 失败: %s' % ex))
        continue
    if len(nb) != len(v):
        bad.append((o[:16], '长度 %d→%d' % (len(v), len(nb))))
print('  长度不一致 / 编码失败: %d 条 %s' % (len(bad), bad[:6]))
print()
print('=== 反向: 现 charset 解出来的错字, 用旧 charset 重编码能否回到原字节? ===')
back = 0
for tag, v, o, n in diff:
    try:
        if OLD.encode_strict(n) == v:
            back += 1
    except Exception:                                                     # noqa: BLE001
        pass
print('  可以: %d / %d (⇒ 两个 charset 之间是一一对应的"改名")' % (back, len(diff)))
print()
print('=== 全盘对照: 用旧 charset 解码"非 <text>"的字节, 是否也影响别的字段? ===')
# 只看 name 属性之外的字节串 (pic/其它属性 / picname 等)
other = []
for m in re.finditer(rb'([A-Za-z_][\w:.-]*)\s*=\s*"([^"]*)"', blob):
    k = m.group(1).decode('latin-1')
    if k in ('name',):
        continue
    v = m.group(2)
    if any(b >= 0x80 for b in v):
        other.append((k, v, OLD.decode(v)[0], NEW.decode(v)[0]))
print('  非 name 属性里含非 ASCII 的: %d 条 (前 6: %s)'
      % (len(other), [(k, o[:12], n[:12]) for k, v, o, n in other[:6]]))
