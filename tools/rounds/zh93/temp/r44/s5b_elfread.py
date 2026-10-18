# -*- coding: utf-8 -*-
r"""s5b_elfread.py — 正确地从 GR_ZH93.iso 里按 ELF 程序头取 VA→文件偏移, 顺便找 PHI 表。

(上一版硬编码 SEC_OFF=0x80 取错了; 这里读 PT_LOAD 表。)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(p):
    while True:
        if os.path.isfile(os.path.join(p, 'tools', 'text_csv', 'tcslib.py')):
            return p
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit('!! 找不到仓库根')
        p = q


REPO = find_repo(HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LOG = []


def log(s):
    print(s)
    LOG.append(s)


PHI = [6, 6, 6, 6, 12, 12, 12, 12, 18, 18, 18, 18, 24, 30, 30, 30, 30, 36, 36, 2, 2, 2, 2, 2, 0]


def main():
    iso = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
    with open(iso, 'rb') as f:
        f.seek(295 * 2048)
        eh = f.read(0x40)
        assert eh[:4] == b'\x7fELF'
        e_phoff, = struct.unpack_from('<I', eh, 0x1C)
        e_phentsize, e_phnum = struct.unpack_from('<HH', eh, 0x2A)
        log('[elf] phoff=0x%X phentsize=%d phnum=%d' % (e_phoff, e_phentsize, e_phnum))
        phs = []
        f.seek(295 * 2048 + e_phoff)
        for i in range(e_phnum):
            p = f.read(e_phentsize)
            p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<6I', p, 0)
            phs.append((p_type, p_offset, p_vaddr, p_filesz, p_memsz))
            log('  ph%d type=%d off=0x%-8X va=0x%08X filesz=0x%-7X memsz=0x%X'
                % (i, p_type, p_offset, p_vaddr, p_filesz, p_memsz))

        def va2off(va):
            for (t, off, vaddr, fsz, msz) in phs:
                if t == 1 and vaddr <= va < vaddr + fsz:
                    return off + (va - vaddr)
            return None
        o = va2off(0x417050)
        log('[elf] VA 0x417050 → 文件偏移 0x%X (LBA %d + 0x%X)'
            % (o, 295 + o // 2048, o % 2048))
        # cave 区
        f.seek(o - 0x100)
        blob = f.read(0x100 + 0x200)
        c0 = 0x100
        log('[cave] 0x417050..0x417150 原始字节:')
        for r in range(0, 0x100, 16):
            log('  0x%06X  %s' % (0x417050 + r, blob[c0 + r:c0 + r + 16].hex(' ')))

        # 全盘搜 PHI 表各种编码
        f.seek(0)
        data = f.read()
        log('[phi] 全盘搜 PHI 表 (u8/u16/u32, PHI 与 16*PHI):')
        pats = {
            'u8  PHI(25)': bytes(PHI),
            'u8  PHI(24)': bytes(PHI[:24]),
            'u8  PHI(19)': bytes(PHI[:19]),
            'u16 PHI(24)': b''.join(struct.pack('<H', v) for v in PHI[:24]),
            'u32 PHI(24)': b''.join(struct.pack('<I', v) for v in PHI[:24]),
            'u16 16*PHI(24)': b''.join(struct.pack('<H', 16 * v) for v in PHI[:24]),
            'u32 16*PHI(24)': b''.join(struct.pack('<I', 16 * v) for v in PHI[:24]),
            'u16 96*(k+1) 序列': b''.join(struct.pack('<H', 96 * (k + 1)) for k in range(8)),
            'u32 96*(k+1) 序列': b''.join(struct.pack('<I', 96 * (k + 1)) for k in range(8)),
        }
        for nm, pat in pats.items():
            hits, i = [], data.find(pat)
            while i >= 0 and len(hits) < 6:
                hits.append(i)
                i = data.find(pat, i + 1)
            log('  %-18s len=%2d → %s' % (nm, len(pat),
                ' '.join('0x%X' % h for h in hits) if hits else '**全盘无**'))
    with open(os.path.join(HERE, 's5b_elfread.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
