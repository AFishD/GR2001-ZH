# -*- coding: utf-8 -*-
r"""root_gsup.py -- 解析 gsrunner 的 GIF-upload 转储 gsup_<hash>_<size>.bin（READ-ONLY）

格式（从 gsrunner.exe 的 `GIF upload: ee=%08x size=%u -> %s` / `gsup_%08x_%u.bin` 推断）：
  16 B 头（小端 u32 x4） + 其后是原始 GIF 包流（PT/A+D/IMAGE ...）。
本工具做两件事:
  1. 前 16 B 当 4 个 u32 打印，并尝试当作 (ee_addr, size, frame, tag) 解读
  2. 从 0x10 起按 GIF tag 口径走包流，统计 IMAGE 包数 / payload 字节 / TRXPOS(SSAY)
  3. 从 A+D 包里提取 TEX0/TEX1 相关的位域（A+D 寄存器号 = 0x06/0x07=TEX0, 0x08/0x09=CLAMP,
     0x0E=TRXPOS, 0x45=TEX1）

用法: python tools/re/toolbelt/root_gsup.py <dir_or_file> [...]
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REG = {0x00: 'PRIM', 0x01: 'RGBAQ', 0x02: 'ST', 0x03: 'UV', 0x04: 'XYZF2', 0x05: 'XYZ2',
       0x06: 'TEX0_1', 0x07: 'TEX0_2', 0x08: 'CLAMP_1', 0x09: 'CLAMP_2', 0x0A: 'FOG',
       0x0C: 'XYZF3', 0x0D: 'XYZ3', 0x0E: 'A+D', 0x0F: 'NOP', 0x13: 'FADE', 0x14: 'PRIM',
       0x45: 'TEX1_1', 0x46: 'TEX1_2', 0x47: 'TEX2_1', 0x48: 'TEX2_2', 0x49: 'XYOFFSET_1',
       0x4A: 'XYOFFSET_2', 0x4C: 'PRMODECONT', 0x4D: 'PRMODE', 0x4E: 'TEXCLUT',
       0x52: 'SCANMSK', 0x53: 'SCISSOR_1', 0x54: 'SCISSOR_2', 0x55: 'ALPHA_1', 0x56: 'ALPHA_2',
       0x59: 'DIMX', 0x5A: 'DTHE', 0x5B: 'COLCLAMP', 0x5C: 'TEST_1', 0x5D: 'TEST_2',
       0x5E: 'PABE', 0x5F: 'FBA_1', 0x60: 'FBA_2', 0x61: 'FRAME_1', 0x62: 'FRAME_2',
       0x63: 'ZBUF_1', 0x64: 'ZBUF_2', 0x65: 'BITBLTBUF', 0x66: 'SRCBUF', 0x67: 'TRXREG',
       0x68: 'TRXDIR', 0x69: 'HWREG', 0x6A: 'SIGNAL', 0x6B: 'FINISH', 0x6C: 'LABEL'}


def tex0_fields(v):
    tbp = v & 0x3FFF
    tbw = (v >> 14) & 0x3F
    psm = (v >> 20) & 0x3F
    tw = (v >> 26) & 0xF
    th = (v >> 30) & 0xF
    tcc = (v >> 34) & 1
    th_ = (v >> 35) & 0xF
    cbp = (v >> 37) & 0x3FFF
    cpsm = (v >> 51) & 0xF
    csm = (v >> 55) & 1
    csa = (v >> 56) & 0x1F
    cld = (v >> 61) & 7
    return dict(value='%016X' % v, TBP=tbp, TBW=tbw, PSM=psm, TW=tw, TH=th, TCC=tcc,
                TH_msb=th_, CBP=cbp, CPSM=cpsm, CSM=csm, CSA=csa, CLD=cld,
                w=1 << tw, h=1 << th)


def walk(b, off0=0x00):
    """走 GIF 包流（转储文件**无额外头**，文件本身就是包流）：返回 events"""
    ev = []
    off = off0
    n = len(b)
    while off + 16 <= n:
        lo, hi = struct.unpack_from('<II', b, off)
        nloop = lo & 0x7FFF
        eop = (lo >> 15) & 1
        pre = (lo >> 46) & 1
        prim = (lo >> 47) & 0x7FF
        flg = (lo >> 58) & 3
        nreg = (lo >> 60) & 0xF
        if flg != 0 or nreg == 0:
            # 不是 PACKED tag ⇒ 当作数据，停止
            break
        # 16 B tag 后跟 nloop × nreg × 16 B 数据
        nb = nloop * nreg * 16
        if off + 16 + nb > n:
            ev.append(dict(off=off, kind='TRUNC', nloop=nloop, nreg=nreg, flg=flg,
                           eop=eop, prim=prim, need=nb, have=n - off - 16, regs=hi))
            return ev, off
        ev.append(dict(off=off, kind='PACKED', nloop=nloop, nreg=nreg, flg=flg, eop=eop,
                       prim=prim, regs=hi, nb=nb))
        off += 16 + nb
    return ev, off


def dump_file(p):
    b = open(p, 'rb').read()
    ev, end = walk(b, 0x00)
    nimg = 0
    payload = 0
    ssay = []
    tex0 = []
    for e in ev:
        if e['kind'] != 'PACKED':
            continue
        if e['regs'] == 0x08000000 and e['nreg'] == 1:
            nimg += 1
            payload += e['nb']
            continue
        if e['regs'] == 0x00000000 and e['nreg'] == 1 and e['nloop'] >= 1:
            # A+D 数据行：每行 16 B，低字节 = 寄存器号
            for k in range(e['nloop']):
                o = e['off'] + 16 + k * 16
                if o + 16 > len(b):
                    break
                dlo, dhi = struct.unpack_from('<II', b, o)
                regno = dlo & 0xFF
                data = dlo >> 8
                if regno in (0x06, 0x07):
                    val = ((dlo >> 8) | (dhi << 24)) & 0xFFFFFFFFFFFFFFFF
                    tex0.append(tex0_fields(val))
                if regno == 0x0E:
                    ssay.append(((data) & 0x7FF, (data >> 11) & 0x7FF))
    print('=' * 100)
    print('%s  %d B' % (os.path.basename(p), len(b)))
    print('  头 16 B: %s' % b[:16].hex(' '))
    print('  包事件 %d ; IMAGE 包 %d ; IMAGE payload %d B (0x%X)'
          % (len(ev), nimg, payload, payload))
    if ssay:
        print('  TRXPOS SSAY (%d): %s' % (len(ssay), [y for (_x, y) in ssay[:24]]))
    for t in tex0:
        print('  TEX0: %s  PSM=0x%X TW=%d(=%d) TH=%d(=%d) TBW=%d TBP=0x%X CBP=0x%X CPSM=0x%X'
              % (t['value'], t['PSM'], t['TW'], t['w'], t['TH'], t['h'], t['TBW'], t['TBP'],
                 t['CBP'], t['CPSM']))
    trunc = [e for e in ev if e['kind'] == 'TRUNC']
    if trunc:
        print('  ★ 截断包 %d 个: 第一个 need=%d have=%d' % (len(trunc), trunc[0]['need'], trunc[0]['have']))
    return dict(n=len(b), tags=len(ev), img=nimg, payload=payload, tex0=tex0, ssay=ssay)


def main():
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            fs = sorted([os.path.join(a, f) for f in os.listdir(a) if f.startswith('gsup_')],
                        key=os.path.getsize)
            tot = 0
            rows = []
            for f in fs:
                r = dump_file(f)
                tot += r['payload']
                rows.append((os.path.basename(f), r))
            print('=' * 100)
            print('目录合计 %d 个转储 ; IMAGE payload 总计 %d B (0x%X)' % (len(fs), tot, tot))
            for (n, r) in rows:
                print('   %-26s size=%-6d tags=%-4d IMAGE=%-3d payload=%d'
                      % (n, r['n'], r['tags'], r['img'], r['payload']))
        else:
            dump_file(a)


main()
