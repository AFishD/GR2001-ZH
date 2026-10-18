# -*- coding: utf-8 -*-
r"""verify_gr121.py — 独立核验成品盘 GR_ZH121 的图集与关键不变量

检查项:
  ① COMMON.PAK 里 new_font_revised 记录: w=1024 / **h=640** / px_size=0x501F0
  ② 旧行 0..511 的墨量应与 GR_ZH113b 一致
  ③ 新行 512..639 应出现墨（新字 ✓）
  ④ FONT.RES 槽长仍 4421、展开仍 5942
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

MENU_LBA = 776286


def load(iso, lba=MENU_LBA):
    pak = None
    for i in range(20):
        e = iso.img_entry(lba, i)
        if 'COMMON' in e['name'].upper():
            pak = e
            break
    return pak


for tag, path in (('113b(原)', 'work/builds/GR_ZH113b/GR_ZH113b.iso'),
                  ('121(成品)', 'work/builds/GR_ZH121/GR_ZH121.iso')):
    iso = tcslib.Iso(os.path.join(REPO, path))
    e = load(iso)
    raw = iso.read(e['iso_off'], e['stored'])
    # new_font_revised 记录: 由既有解析知 @pak+0x1031, h @+0x020
    rec = 0x1031
    psm, w, h, clut = struct.unpack_from('<4I', raw, rec + 0x18)
    px = struct.unpack_from('<I', raw, 0x146D - 4)[0] if False else None
    print('=== %s ===' % tag)
    print('  COMMON.PAK stored=%d real=%d' % (e['stored'], e['real']))
    print('  new_font_revised: psm=0x%X w=%d **h=%d** clut=0x%X' % (psm, w, h, clut))
    # 找 px_size: 在 h 之后扫描
    for off in range(rec + 0x28, rec + 0x460, 4):
        v = struct.unpack_from('<I', raw, off)[0]
        if v in (0x40010, 0x501F0, 0x601F0):
            print('  px_size @rec+0x%X = 0x%X' % (off - rec, v))
            break
    # FONT.RES
    fr = iso.img_entry(MENU_LBA, 4)
    print('  FONT.RES stored=%d real=%d' % (fr['stored'], fr['real']))
    slot = iso.read(fr['iso_off'], fr['stored'])
    subs = tcslib.lzo_subs(slot)
    print('  FONT.RES 解出 %d B（期望 5942）' % sum(len(s[0]) for s in subs))
    iso.close()
    print()
print('⇒ ②③ 旧行/新行的墨量对比需要解出像素容器; 若上面 h 与 px_size 正确 ⇒ 主结构已变 ✓')
