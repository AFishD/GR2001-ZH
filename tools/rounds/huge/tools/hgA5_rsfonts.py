# -*- coding: utf-8 -*-
r"""hgA5_rsfonts.py — 只读: 解析 FONT.RES 展开态里 FontDefinition 之后的 RSFont 区。

块结构（口径来自反汇编 `RSFont::ReadResource` @0x21AB50 的读取顺序 + 盘上逐字节回读）:
  [u32 nameLen][nameLen B name]                  ← RSUIString::Read @0x53FE40
  [u32 -> +0x0C][u32 -> +0x10][u32 -> +0x14][u32 -> +0x18]
  [u8  -> +0x24]
  [u32 -> +0x1C][u32 -> +0x20]
  ⇒ 块长 = 4 + nameLen + 25   （**不是 4 字节对齐**）

产出: work/builds/GR_HUGE/evidence/hgA5_rsfonts.txt / .json
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

FLOAT = lambda u: struct.unpack('<f', struct.pack('<I', u))[0]


def parse_fonts(plain, off):
    n = struct.unpack_from('<I', plain, off)[0]
    p = off + 4
    out = []
    for i in range(n):
        ln = struct.unpack_from('<I', plain, p)[0]
        assert 0 < ln <= 64, 'nameLen=%d @0x%X' % (ln, p)
        nm = plain[p + 4:p + 4 + ln].decode('latin-1')
        q = p + 4 + ln
        f0c, f10, f14, f18 = struct.unpack_from('<4I', plain, q)
        b24 = plain[q + 16]
        f1c, f20 = struct.unpack_from('<2I', plain, q + 17)
        out.append(dict(idx=i, off=p, nameLen=ln, name=nm, block_len=4 + ln + 25,
                        f0c=f0c, f10=f10, f14=f14, f18=f18, b24=b24,
                        f1c=f1c, f1c_f=FLOAT(f1c), f20=f20, f20_f=FLOAT(f20)))
        p += 4 + ln + 25
    return out, p, n


def main():
    lines = []
    W = lines.append
    data = {}
    for tag in ('EN_ORIG', 'ZH113b'):
        for imgk in ('MENU', 'GR'):
            d = H.fontres(tag, imgk)
            plain = d['plain']
            off = d['styles_off']
            try:
                fonts, p, n = parse_fonts(plain, off)
                ok = (p == len(plain))
            except AssertionError as ex:
                W('%s/%s 解析失败: %s' % (tag, imgk, ex))
                continue
            W('=' * 100)
            W('%s/%s  font-section @0x%X len=%d  nFonts=%d  解析到 0x%X (plain_len=0x%X) 完全消费=%s'
              % (tag, imgk, off, len(plain) - off, n, p, len(plain), ok))
            W('  idx  @off    name      +0C +10 +14 +18 +24  +1C(scale_w)   +20(scale_h)')

            # 反查每个 RSFont 绑到哪个 FontDefinition（按名字）
            defs = {f['name']: f for f in d['faces']}
            for f in fonts:
                df = defs.get(f['name'])
                W('  [%d] 0x%04X  %-9s %3d %3d %3d %3d %3d  %-12.5f %-12.5f  -> face `%s` nrec=%s'
                  % (f['idx'], f['off'], f['name'], f['f0c'], f['f10'], f['f14'], f['f18'],
                     f['b24'], f['f1c_f'], f['f20_f'], f['name'],
                     df['nr'] if df else '**无同名 face**'))
            data['%s/%s' % (tag, imgk)] = dict(section_off=off, nfonts=n,
                                               parsed_end=p, plain_len=len(plain),
                                               fully_consumed=ok, fonts=fonts)
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA5_rsfonts.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    open(os.path.join(H.EVID, 'hgA5_rsfonts.json'), 'w', encoding='utf-8').write(
        json.dumps(data, ensure_ascii=False, indent=1))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
