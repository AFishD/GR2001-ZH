# -*- coding: utf-8 -*-
r"""round59 复核 step 2 (只读): FONT.RES 槽到底有没有余量 —— 为"补丁能不能落盘"定量。

现状: patch_zh109_edge_fix.py 改 46 条记录 (276 B) 后 LZO 重压 = 4433 B > 槽 4421 B ⇒ 落不下去。
本脚本只读量: 现役槽里那一帧的真实长度 / 余量, 以及**不同改动集 + 不同压缩参数**下的帧长,
用来挑"既能修好、又装得进 4421 B 槽"的最小方案。

用法: python measure_ft_slot.py
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import dump_font as D                                                    # noqa: E402
import tcslib                                                            # noqa: E402
import lzo1x_c                                                           # noqa: E402
from patch_zh104_relocate import face_tables                             # noqa: E402
from patch_zh109_edge_fix import load                                    # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH108', 'GR_ZH108.iso')

VARIANTS = {
    'V0 原样 (0 改动)': [],
    'V3 只搬 0xED+0xEE (4 条记录)': [0xED, 0xEE],
    'V2 搬 0xAE/0xAF/0xB0/0xED/0xEE (10 条记录)': [0xAE, 0xAF, 0xB0, 0xED, 0xEE],
    'V1 搬全部 22 条候选 (46 条记录)': [0x20, 0x7F] + list(range(0xA1, 0xAE))
                                       + [0xAE, 0xAF, 0xB0, 0xB1, 0xB5, 0xED, 0xEE],
}
# 落点 (与补丁一致: 有墨的先拿最靠左的空格)
NEW = {0xED: (320, 211, 336, 227), 0xEE: (336, 211, 352, 227),
       0xAE: (352, 211, 368, 227), 0xAF: (368, 211, 384, 227),
       0xB0: (384, 211, 400, 227)}
BLANK_NEW = (400, 211, 410, 227)
PARAMS = [dict(level=7, use_m1=True, use_m4=True),
          dict(level=7, use_m1=True, use_m4=True, hash_bits=19),
          dict(level=7, use_m1=True, use_m4=True, hash_bits=19, max_chain=8192),
          dict(level=7, use_m1=True, use_m4=True, hash_bits=20, max_chain=16384,
               nice_len=512, max_lazy=256, good_len=256),
          dict(level=7, use_m1=True, use_m4=True, max_back=32768, hash_bits=19,
               max_chain=8192)]


def main():
    M = load(ISO)
    ft = M['w']['ft_blob']
    ft_slot = M['w']['ft_slot']
    subs = tcslib.lzo_subs(ft_slot)
    print('=' * 100)
    print('FONT.RES 槽: stored = %d B; 子流 %d 个' % (len(ft_slot), len(subs)))
    for (raw, L, S, off) in subs:
        print('   子流 @%d: comp=%d real=%d  帧占 = 8+%d = %d B' % (off, L, S, L, 8 + L))
    tail = ft_slot[8 + subs[0][1]:]
    print('   槽尾零填充 = %d B (= 余量)' % len(tail))
    print('   展开态 blob = %d B' % len(ft))
    print('   ⇒ 新帧只要 ≤ %d B (含 8B 帧头) 就能原地放下' % (8 + subs[0][1] + len(tail)))

    off_of = {nm: off for (nm, fld, off, nrec) in M['tables']}
    nrec_of = {nm: nrec for (nm, fld, off, nrec) in M['tables']}
    codes_of = {}
    for nm in ('large', 'default', 'huge'):
        for c, r in M['rec'][nm].items():
            if r[4] > r[2] and r[5] > r[3] and r[2] >= 992:
                codes_of.setdefault(c, []).append(nm)

    out = {}
    for name, codes in VARIANTS.items():
        blob = bytearray(ft)
        n = 0
        for c in codes:
            for nm in codes_of.get(c, []):
                o = off_of[nm] + (c - 0x20) * 10
                b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', blob, o)
                if (u0, v0, u1, v1) == (1014, 0, 1024, 16):
                    new = BLANK_NEW
                else:
                    new = NEW[c]
                struct.pack_into('<BB4H', blob, o, b0, b1, *new)
                n += 1
        row = []
        for kw in PARAMS:
            cc = lzo1x_c.compress(bytes(blob), **kw)
            back, err, _ = tcslib.lzo1x_decompress(cc, out_size=len(blob))
            assert err is None and back == bytes(blob), '回环失败 %s' % kw
            row.append((kw, len(cc) + 8))
        out[name] = dict(records=n, sizes=[(str(k), v) for k, v in row])
        print('')
        print('%-46s 改 %2d 条记录' % (name, n))
        for (kw, sz) in row:
            tag = ' '.join('%s=%s' % (k, v) for k, v in sorted(kw.items())
                           if k not in ('use_m1', 'use_m4'))
            print('     %-72s 帧 = %5d B  %s' % (tag or '(默认 level7/m1/m4)', sz,
                                                 '✓ 装得下' if sz <= 4421 else '✗ 超槽'))
    io.open(os.path.join(HERE, 'measure_ft_slot.json'), 'w', encoding='utf-8',
            newline='\n').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print('')
    print('→ measure_ft_slot.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
