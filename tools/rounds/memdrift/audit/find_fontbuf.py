# -*- coding: utf-8 -*-
r"""find_fontbuf.py — 在 EE RAM 快照里找引擎**实际驻留**的 FONT.RES 展开态

要回答的问题
------------
汉化盘的 MENU.IMG/GR.IMG 条目把 FONT.RES 的 real 声明成 **7222**, 而 LZO 子流自己
只解出 **5942** (因为 huge face 的记录数被从 224 砍到 96)。原盘两者都是 7222。
⇒ 如果引擎按**条目的 real** 分配缓冲, 那 5942..7222 这 1280 B 就是**未初始化的堆**;
  引擎随后按 face 顺序解析完 3 个 face (到 0x1620) 再走"风格块", 就会踩进这 1280 B。
⇒ 本工具直接看**引擎驻留的那份字节**: 5942 之后是零 / 是原盘的旧数据 / 是垃圾?
"""
import glob
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
EE = 32 * 1024 * 1024
SIG = b'new_font_revised.rsb'


def samples(d, kind='eeram'):
    out = []
    for p in glob.glob(os.path.join(d, 'period_f*_%s.bin' % kind)):
        m = re.search(r'period_f(\d+)_', os.path.basename(p))
        if m:
            out.append((int(m.group(1)), p))
    out.sort()
    return out


def main():
    d = sys.argv[1]
    ss = samples(d)
    if not ss:
        sys.exit('无快照')
    f, p = ss[0]                       # 用最早那份 (资源早已驻留)
    print('快照 %s frame=%d' % (p, f))
    with open(p, 'rb') as fh:
        blob = fh.read()
    hits = []
    i = 0
    while True:
        j = blob.find(SIG, i)
        if j < 0:
            break
        hits.append(j)
        i = j + 1
    print('命中 "%s" 的位置 %d 处: %s' % (SIG.decode(), len(hits), ['0x%X' % h for h in hits[:20]]))
    for j in hits:
        # 头部: 前 4 字节 = namelen(20), 所以资源起点 = j-4
        s = j - 4
        namelen = struct.unpack_from('<I', blob, s)[0]
        nfaces = struct.unpack_from('<I', blob, s + 4 + namelen)[0]
        print('\n--- 资源起点 0x%06X (namelen=%d nfaces=%d) ---' % (s, namelen, nfaces))
        if namelen != 20 or nfaces != 3:
            print('    (不是 FONT.RES 头, 跳过)')
            continue
        # 解析 3 个 face
        off = s + 8 + namelen
        for k in range(nfaces):
            l = struct.unpack_from('<I', blob, off)[0]
            nm = blob[off + 4:off + 4 + l].split(b'\x00')[0].decode('latin-1')
            fld = struct.unpack_from('<14I', blob, off + 4 + l)
            nrec = fld[4] * fld[5]
            print('    face %-8s nrec=%-4d (fld4=%d fld5=%d) rec@0x%X'
                  % (nm, nrec, fld[4], fld[5], off + 4 + l + 56))
            off += 4 + l + 56 + nrec * 10
        print('    记录区结束 = 0x%X (= 0x%X + 0x%X)' % (off, s, off - s))
        # 打印 5900..7300 区间的字节
        print('    相对偏移 0x1700..0x1C50 的字节 (每行 16):')
        for o in range(0x1700, 0x1C50, 16):
            row = blob[s + o:s + o + 16]
            if len(row) < 16:
                break
            z = 'ZERO' if row == b'\x00' * 16 else ''
            print('      0x%04X  %s  %s %s' % (o, row.hex(' '),
                  ''.join(chr(c) if 32 <= c < 127 else '.' for c in row), z))


if __name__ == '__main__':
    main()
