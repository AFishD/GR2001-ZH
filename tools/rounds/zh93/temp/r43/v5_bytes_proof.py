# -*- coding: utf-8 -*-
r"""v5_bytes_proof.py — round43 的**字节级**证据 (不只看 sha256, 直接读盘上那两个条目的字节)

检三件事:
  ① 编码器等价: cell_to_bytes_text('Français') == cell_to_bytes_text('Fran{{BTN:E0E7}}ais')
                 == b'Fran\xE7ais'  (两种写法 → 同一个字节序列)
  ② 盘上真字节: GR_ZH93.iso 的 LANG 条目 G059.I028 = b'Fran\xE7ais' (0xE7 就是 ç 的字节),
                 G059.I031 = b'Espa\xF1ol'
  ③ 探针盘:     inj_probe_new.iso 与 inj_probe_old.iso 里同一条目都是
                 b'Fran\xE7ais!' / b'Espa\xF1ol!' —— 两种写法写出了**同一份盘**
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                   # noqa: E402

CS = T.Charset()
ok = True


def chk(cond, msg):
    global ok
    ok = ok and bool(cond)
    print('%s %s' % ('[ok]' if cond else '[!!]', msg))


# ① 编码器等价 ---------------------------------------------------------------
print('== ① 编码器等价 (两种写法 → 同一个字节序列) ==')
pairs = [('Français', 'Fran{{BTN:E0E7}}ais', b'Fran\xe7ais'),
         ('Español', 'Espa{{BTN:E0F1}}ol', b'Espa\xf1ol')]
for zh, old, want in pairs:
    a = T.cell_to_bytes_text(zh, CS)
    b = T.cell_to_bytes_text(old, CS)
    chk(a == b == want, 'cell_to_bytes_text(%r) == cell_to_bytes_text(%r) == %r'
        % (zh, old, want))
    chk(CS.encode_strict(zh) == CS.encode_strict(old) == want,
        'encode_strict 两条路也都是 %r' % want)

# ② 现役盘真字节 -------------------------------------------------------------
print('\n== ② GR_ZH93.iso 盘上那两个条目的真字节 ==')


def lang_entry_bytes(iso_path, g, i):
    iso = T.Iso(iso_path)
    try:
        e = iso.img_entry(T.MENU_LBA, T.LANG_MENU_IDX)
        blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
    finally:
        iso.close()
    for ent in T.parse_lang(blob)[0]:
        if ent.g == g - 1 and ent.i == i:
            return bytes(ent.data)
    return None


want93 = {'G059.I028': b'Fran\xe7ais', 'G059.I031': b'Espa\xf1ol'}
for rid, want in want93.items():
    g, i = [int(x) for x in rid[1:].split('.I')]
    got = lang_entry_bytes(os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'), g, i)
    chk(got == want, 'GR_ZH93.iso %s = %r  (hex %s)'
        % (rid, got, got.hex(' ') if got else '-'))
    back = CS.decode(got)[0] if got else ''
    chk(back == ('Français' if i == 28 else 'Español'), '  decode 回读 = %r' % back)

# ③ 探针盘: 两种写法 → 同一份盘 ----------------------------------------------
print('\n== ③ 探针盘 (真改一格!) 两写法产物对比 ==')
probe = {}
for tag in ('probe_new', 'probe_old'):
    p = os.path.join(HERE, 'inj_%s.iso' % tag)
    if not os.path.isfile(p):
        chk(False, '缺少探针盘 %s (先跑 v4 注入)' % p)
        continue
    probe[tag] = dict(
        sha=T.sha256_file(p),
        a=lang_entry_bytes(p, 59, 28),
        b=lang_entry_bytes(p, 59, 31))
    print('  %-10s sha256=%s' % (tag, probe[tag]['sha']))
for tag, d in probe.items():
    chk(d['a'] == b'Fran\xe7ais!' and d['b'] == b'Espa\xf1ol!',
        '%s: G059.I028=%r G059.I031=%r (真字母那一路写出来的字节)' % (tag, d['a'], d['b']))
if len(probe) == 2:
    chk(probe['probe_new']['sha'] == probe['probe_old']['sha'],
        '★ 两种写法 (真字母 ç/ñ  vs  {{BTN:E0E7}}/{{BTN:E0F1}}) 注入出的盘 **逐字节相同** '
        '(sha256 都是 %s)' % probe['probe_new']['sha'])
    chk(probe['probe_new']['a'] == probe['probe_old']['a'] == b'Fran\xe7ais!',
        '两条路写出的字节都含 0xE7 (ç)')

print('\n结论: %s' % ('[ok] 全部通过 ✓' if ok else '[!!] 有失败项'))
sys.exit(0 if ok else 1)
