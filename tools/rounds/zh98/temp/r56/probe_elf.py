# -*- coding: utf-8 -*-
"""ELF (LBA295) 里那 1 段巧合是什么? 以及 IMG 之外命中的分区统计 (只读)。"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402
import font_compact as FC                                            # noqa: E402

old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                  'charset_before_r56.json'))
new = tcslib.Charset()
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH106', 'GR_ZH106.iso'))
regions = sorted((e['iso_off'], e['iso_off'] + e['stored'], 'x')
                 for (_t, _l, _i, e) in FC.enumerate_containers(iso))
hits = FC.scan_raw_iso(iso, old, verbose=False)
outside = [h for h in hits if FC.who(regions, h['off']) == '(IMG 之外 / 未归属)']
print('IMG 之外 %d 段' % len(outside))
# 分区: 系统区(0..15) / ELF(295..) / 其它独立文件 / IMG 空隙
sysar = [h for h in outside if h['off'] < 16 * 2048]
elf = [h for h in outside if 295 * 2048 <= h['off'] < 295 * 2048 + 0x180000]
img_gap = [h for h in outside if h['off'] >= 19175 * 2048]
standalone = [h for h in outside if h not in sysar and h not in elf and h not in img_gap]
print('  ISO 系统区 (LBA0..15): %d 段' % len(sysar))
print('  ELF (LBA295, 0x180000): %d 段' % len(elf))
print('  两个 IMG 的未分配空隙/尾部: %d 段' % len(img_gap))
print('  其它独立文件区: %d 段' % len(standalone))
for h in elf:
    seg = iso.read(h['off'] - 8, 48)
    print('  ★ ELF 段 @%d: %s' % (h['off'], seg.hex(' ')))
    print('     旧解得 %r' % old.decode(iso.read(h['off'], h['nbytes']))[0])
    print('     新解得 %r' % new.decode(iso.read(h['off'], h['nbytes']))[0])
# 统计"换码后意义变了"的段 (数字进报告)
chg = 0
for h in outside:
    b = iso.read(h['off'], h['nbytes'])
    if old.decode(b)[0] != new.decode(b)[0]:
        chg += 1
print('IMG 之外: 意义不变 %d / 意义变了 %d (全判为二进制巧合, 字节 0 改动)' % (len(outside) - chg, chg))
iso.close()
