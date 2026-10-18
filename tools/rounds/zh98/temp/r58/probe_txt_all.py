# -*- coding: utf-8 -*-
r"""r58 探针7: ① decode 速度基准; ② 5 个语言的 *_STRINGS.TXT (MENU#30..34 / GR#901,903,905,908,911) 有没有中文。
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

G0 = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46', 'charset_before_repack.json')
G1 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
G2 = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso'))

# ---- ① 速度基准 ----
blob = FC.Slot(iso, 'GR.IMG', FC.GR_LBA, 907).blob
cs = tcslib.Charset(G2)
t0 = time.time()
for _ in range(5):
    cs.decode(blob)
dt = (time.time() - t0) / 5
print('decode 基准: %.1f KB / %.3f s → %.1f MB/s  (全盘 1.66 GB 两代 ≈ %.0f s)'
      % (len(blob) / 1024, dt, len(blob) / 1e6 / dt, 1.66e9 / 1e6 / (len(blob) / 1e6 / dt) * 2))

# ---- ② 语言 TXT ----
CH = [tcslib.Charset(p) for p in (G0, G1, G2)]
NAMES = [('G0', CH[0]), ('G1', CH[1]), ('G2', CH[2])]
for tag, idx in (('MENU.IMG', 30), ('MENU.IMG', 31), ('MENU.IMG', 32), ('MENU.IMG', 33),
                 ('MENU.IMG', 34),
                 ('GR.IMG', 901), ('GR.IMG', 903), ('GR.IMG', 905), ('GR.IMG', 908),
                 ('GR.IMG', 911)):
    lba = FC.MENU_LBA if tag == 'MENU.IMG' else FC.GR_LBA
    s = FC.Slot(iso, tag, lba, idx)
    print('\n=== %s#%d %s (展开 %d B, %s) ===' % (tag, idx, s.name, len(s.blob), s.mode))
    for (gn, c) in NAMES:
        t, _ = c.decode(s.blob)
        cjk = sum(1 for ch in t if '\u4e00' <= ch <= '\u9fff')
        # 只打含汉字的行
        out = []
        for ln in t.split('\r\n'):
            if any('\u4e00' <= ch <= '\u9fff' for ch in ln) and len(out) < 6:
                out.append(ln[:70])
        print('   %s 汉字 %4d | %s' % (gn, cjk, '  ~~  '.join(repr(x) for x in out)))
iso.close()
