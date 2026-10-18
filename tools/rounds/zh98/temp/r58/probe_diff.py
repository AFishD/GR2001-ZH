# -*- coding: utf-8 -*-
r"""r58 探针2: 逐容器算"旧解 vs 新解"的**字符级差异** + "补码"会改多少字节 (只读)。

对每个候选容器:
  t_o = 旧 charset 解(盘上字节)   t_n = 新 charset 解(盘上字节)
  · n_diff  = t_o 与 t_n 不同的字符位置数 (这才是"换码后会不会变味"的口径)
  · 补码    = 用**旧解**的文本按**新** charset 编回去 (解码失败/长度不等的字符单独计数)
每种差异留 6 个样例 (上下文 + 原始字节)。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

CS_OLD = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
CS_NEW = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
ISO107 = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')

TARGETS = [
    ('MENU.IMG', 30, 'EN_STRINGS.TXT'), ('GR.IMG', 906, 'EN_STRINGS.TXT(gr)'),
    ('GR.IMG', 907, 'FR_STRINGS.RES'), ('MENU.IMG', 28, 'MENU FR_STRINGS.RES'),
    ('GR.IMG', 904, 'ES_STRINGS.RES'), ('MENU.IMG', 27, 'MENU ES_STRINGS.RES'),
    ('GR.IMG', 900, 'DE_STRINGS.RES'), ('MENU.IMG', 26, 'MENU DE_STRINGS.RES'),
    ('GR.IMG', 910, 'IT_STRINGS.RES'), ('MENU.IMG', 29, 'MENU IT_STRINGS.RES'),
    ('GR.IMG', 4059, 'ES_SPECIAL_FEATURE.XML'), ('MENU.IMG', 285, 'MENU ES_SF.XML'),
    ('GR.IMG', 4061, 'FR_SPECIAL_FEATURE.XML'), ('MENU.IMG', 286, 'MENU FR_SF.XML'),
    ('GR.IMG', 4057, 'DE_SPECIAL_FEATURE.XML'), ('MENU.IMG', 284, 'MENU DE_SF.XML'),
    ('GR.IMG', 908, 'FR_STRINGS.TXT'), ('MENU.IMG', 33, 'MENU FR_STRINGS.TXT'),
    ('GR.IMG', 905, 'ES_STRINGS.TXT'), ('MENU.IMG', 32, 'MENU ES_STRINGS.TXT'),
    ('GR.IMG', 4062, 'IGORHELP.TXT'),
    ('MENU.IMG', 25, 'EN_STRINGS.RES(menu)'), ('GR.IMG', 902, 'EN_STRINGS.RES(gr)'),
    ('MENU.IMG', 283, 'EN_SPECIAL_FEATURE.XML'),
]

old = tcslib.Charset(CS_OLD)
new = tcslib.Charset(CS_NEW)
iso = tcslib.Iso(ISO107)


def catchup(blob, samples):
    """旧解 → 新编: 返回 (改了多少字节, 编不出的字符数, 长度不等的字符数)。"""
    t_o, mp = old.decode(blob)
    out = bytearray(blob)
    nchg = nfail = nlen = 0
    for i, ch in enumerate(t_o):
        a = mp[i]
        b = mp[i + 1] if i + 1 < len(t_o) else len(blob)
        ob = blob[a:b]
        try:
            nb = new.encode_strict(ch)
        except tcslib.CharsetError:
            nfail += 1
            continue
        if len(nb) != len(ob):
            nlen += 1
            continue
        if nb != ob:
            out[a:b] = nb
            nchg += len(nb)
            if len(samples) < 8:
                samples.append((a, ob.hex(' '), nb.hex(' '), ch))
    return nchg, nfail, nlen


print('%-30s %-6s | %-7s %-7s %-8s %-7s | %s' %
      ('container', 'blob', 'diff_ch', 'diff_2B', '编不出', '长度!=', '补码改字节'))
for (tag, idx, nm) in TARGETS:
    lba = FC.MENU_LBA if tag == 'MENU.IMG' else FC.GR_LBA
    s = FC.Slot(iso, tag, lba, idx)
    blob = s.blob
    t_o, mp_o = old.decode(blob)
    t_n, _ = new.decode(blob)
    n = min(len(t_o), len(t_n))
    diff_pos = [i for i in range(n) if t_o[i] != t_n[i]]
    diff_pair = [i for i in diff_pos
                 if (mp_o[i + 1] if i + 1 < len(t_o) else len(blob)) - mp_o[i] == 2]
    samples = []
    nchg, nfail, nlen = catchup(blob, samples)
    print('%-30s %-6d | %-7d %-7d %-8d %-7d | %d%s' %
          ('%s#%d %s' % (tag, idx, nm), len(blob), len(diff_pos), len(diff_pair),
           nfail, nlen, nchg, '  !=len(text)' if len(t_o) != len(t_n) else ''))
    if diff_pos and len(diff_pos) <= 64:
        for i in diff_pos[:6]:
            lo, hi = max(0, i - 26), min(n, i + 26)
            print('        @%-7d 旧解 %r' % (i, t_o[lo:hi]))
            print('        %-8s 新解 %r' % ('', t_n[lo:hi]))
    for (a, ob, nb, ch) in samples[:6]:
        print('        补码 @%-7d %r  %s → %s' % (a, ch, ob, nb))
iso.close()
