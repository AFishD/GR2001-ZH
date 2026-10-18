# -*- coding: utf-8 -*-
"""txt_a_detail.py —— A 的补充读数：所有增长条目全表 / 最长条目 / 长度直方图（只读）。

中文列用 tools/font_pipeline/data/charset_compiled_zh16.json 按**引擎口径**解码
（GR_ZH113b 的文本不是 GBK —— 它是游戏自带编码：单字节码 + 0xB1xx 对偶码），
这样才能对出人类可读的界面线索。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
AUD = os.path.join(ROOT, 'work', 'builds', 'GR_TXT', 'audit')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

EN = os.path.join(ROOT, r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso")
ZH = os.path.join(ROOT, r"work\builds\GR_ZH113b\GR_ZH113b.iso")


def dec(b):
    try:
        return b.decode('gbk')
    except UnicodeDecodeError:
        return b.decode('gbk', 'replace')


try:
    CS = T.Charset()
    print('# 中文列解码口径: charset_compiled_zh16.json  codes=%d pair_of=%d '
          'LEAD=[0x%02X,0x%02X)' % (len(CS.enc_single), len(CS.enc_pair),
                                    T.LEAD_LO, T.LEAD_HI))
except Exception as ex:                                                   # noqa: BLE001
    CS = None
    print('# charset 载入失败: %r（中文列退回 GBK，会是乱码）' % (ex,))


def zh_dec(b):
    if CS is None:
        return dec(b)
    try:
        return CS.decode(b)[0]
    except Exception:                                                     # noqa: BLE001
        return dec(b)


def cont(rel, lba, idx):
    iso = T.Iso(rel)
    e = iso.img_entry(lba, idx)
    blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
    iso.close()
    return T.parse_lang(blob)[0]


out = {}
for (lba, idx, tag) in ((T.MENU_LBA, 25, 'EN_STRINGS.RES@MENU'),
                        (T.GR_LBA, 902, 'EN_STRINGS.RES@GR')):
    en = cont(EN, lba, idx)
    zh = cont(ZH, lba, idx)
    rows = [(('G%02d.I%03d' % (en[i].g + 1, en[i].i)), en[i].length, zh[i].length,
             zh[i].data, en[i].data) for i in range(len(en))]
    grew = sorted([r for r in rows if r[2] > r[1]], key=lambda r: -(r[2] - r[1]))
    print('=' * 78)
    print('%s : 增长条目 %d 条（全部列出）' % (tag, len(grew)))
    for (k, le, lz, dz, de) in grew:
        print('   %-10s %3d -> %3d (%+d)  zh=%r  en=%r'
              % (k, le, lz, lz - le, zh_dec(dz)[:34], dec(de)[:34]))
    zl = sorted((r[2] for r in rows), reverse=True)
    el = sorted((r[1] for r in rows), reverse=True)
    print('   最长 ZH %s  最长 EN %s' % (zl[:8], el[:8]))
    print('   ZH 长度 == 768 的条数 = %d ; >= 700 = %d ; EN >= 1500 = %d'
          % (sum(1 for v in zl if v == 768), sum(1 for v in zl if v >= 700),
             sum(1 for v in el if v >= 1500)))
    for (k, le, lz, dz, de) in sorted(rows, key=lambda r: -r[2])[:5]:
        print('   最长 %-10s zh=%4d en=%4d  %r' % (k, lz, le, zh_dec(dz)[:70]))
    out[tag] = [dict(key=k, len_en=le, len_zh=lz, d=lz - le,
                     zh=zh_dec(dz), en=dec(de)) for (k, le, lz, dz, de) in rows]

with open(os.path.join(AUD, 'A_detail_rows.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('[out] %s' % os.path.join(AUD, 'A_detail_rows.json'))
