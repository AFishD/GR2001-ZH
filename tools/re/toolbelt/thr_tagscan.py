# -*- coding: utf-8 -*-
r"""thr_tagscan.py -- 精确打印容器每个 16 B 步进的 tag 解析 + 关键 u32 (READ-ONLY)

用法: python tools/re/toolbelt/thr_tagscan.py <iso> [--ct-only]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'tools', 'text_csv')))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

SEC = 2048
MENU_LBA = tcslib.MENU_LBA


def parse_tag(b, o):
    w0, w1 = struct.unpack_from('<II', b, o)
    nloop = w0 & 0x7FFF
    eop = (w0 >> 15) & 1
    flg = (w1 >> 26) & 3
    nreg_f = (w1 >> 28) & 0xF
    nreg = ((nreg_f - 1) & 0xF) + 1
    return dict(o=o, w0=w0, w1=w1, nloop=nloop, eop=eop, flg=flg, nreg=nreg, nreg_f=nreg_f)


def main(argv):
    ct_only = '--ct-only' in argv
    for path in [a for a in argv if not a.startswith('--')]:
        print('=' * 100)
        print(path)
        iso = tcslib.Iso(path)
        ents = zx_lib.entries(iso, MENU_LBA)
        e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
        pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
        recs = tcslib.parse_pak_records(pak)
        nm, psm, w, h, clut, px_size, px_off = recs[1]
        rec_off = px_off - 0x43C
        ct = bytes(pak[px_off:px_off + px_size])
        print('  容器 %d B (0x%X) ; w=%d h=%d' % (len(ct), len(ct), w, h))
        # 16 B 步进扫描全部 tag
        print('  --- 全部 16 B 步进 tag (只列可解析的) ---')
        o = 0
        segs = []
        while o + 16 <= len(ct):
            t = parse_tag(ct, o)
            if t['flg'] in (0, 1) and t['nloop'] == 1 and t['nreg'] == 1:
                ssay = struct.unpack_from('<I', ct, o + 20)[0]
                q1 = struct.unpack_from('<Q', ct, o + 24)[0]
                print('    0x%06X PT   NLOOP=1 EOP=%d FLG=%d NREG=%d REGS=0x%X'
                      % (o, t['eop'], t['flg'], t['nreg'], struct.unpack_from('<Q', ct, o + 8)[0]))
                print('            A+D: SSAX=%d SSAY(u32@+20)=%d ; TRXREG-like u64@+24=0x%X'
                      % (struct.unpack_from('<I', ct, o + 16)[0], ssay, q1))
                o += 32
                continue
            if t['flg'] == 2:
                ln = t['nloop'] * 16
                print('    0x%06X IMG  NLOOP=%-6d EOP=%d FLG=2 -> data 0x%06X..0x%06X (%d B)'
                      % (o, t['nloop'], t['eop'], o + 16, o + 16 + ln, ln))
                segs.append((o, ln))
                o += 16 + ln
                if t['nloop'] == 0:
                    break
                continue
            print('    0x%06X ?    NLOOP=%-6d EOP=%d FLG=%d NREG=%d w0=%08X w1=%08X'
                  % (o, t['nloop'], t['eop'], t['flg'], t['nreg'], t['w0'], t['w1']))
            o += 16
        print('  --- 末尾 64 B (u32) ---')
        base = len(ct) - 64
        for k in range(16):
            print('    0x%06X  %08X' % (base + 4 * k, struct.unpack_from('<I', ct, base + 4 * k)[0]))
        print('  --- tcslib 段表 ---')
        sg = tcslib.atlas_container_segments(ct, w // 2)
        print('    %s' % (sg,))
        print('  段数=%d 数据合计=%d 头合计=%d 差=%d'
              % (len(sg), sum(s[2] for s in sg), len(sg) * 48,
                 len(ct) - sum(s[2] for s in sg) - len(sg) * 48))
        iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
