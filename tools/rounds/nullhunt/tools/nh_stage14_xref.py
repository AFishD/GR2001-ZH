# -*- coding: utf-8 -*-
r"""nh_stage14_xref.py — 三项零成本静态验证 (只读)

A) cave 落点的调用者 xref 扫描: 谁 jal 到 sceRemove/sceMkdir/sceFormat/sceDopen/
   sceDclose/strlwr/strupr/sceIpuInit 的入口 (即汉化写代码的地方)
B) EN_STRINGS.TXT 旧位置 (MENU.IMG + 2,414,080 .. +2,416,829) 在汉化盘上是什么
C) 全盘搜 ELF 里是否存在指向 2,414,080 (0x24D400) 的立即数 (硬编码偏移)
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nh_lib as N   # noqa: E402
import nh_elf as E   # noqa: E402
import nh_stage3_elf as S3   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 汉化 cave 覆盖/使用的函数入口 VA (来自 stage4 的 run#48..#53, run#43..#47, run#62..#67)
CAVE_ENTRIES = [
    ('sceRemove', 0x416ED0), ('sceMkdir', 0x416EF0), ('sceFormat', 0x4170C0),
    ('sceDopen', 0x417470), ('sceDclose', 0x417538), ('sceIpuInit', 0x411458),
    ('strlwr', 0x407060), ('strupr', 0x408910),
    ('cave@417050', 0x417050), ('cave@417150', 0x417150), ('cave@417200', 0x417200),
    ('cave@417500', 0x417500), ('cave@417600', 0x417600), ('cave@416F40', 0x416F40),
    ('cave@565930', 0x565930), ('cave@565670', 0x565670), ('cave@565760', 0x565760),
]
# 汉化实际 jal/j 目标 (来自 stage4)
HOOK_TARGETS = [0x416ED0, 0x417050, 0x417150, 0x417200, 0x417500, 0x416F40,
                0x565930, 0x565670, 0x565760]


def main():
    e_en, _ = S3.load_elf('EN_ORIG')
    e_zh, _ = S3.load_elf('ZH113b_fix')
    buf = io.StringIO()

    # ---------- A) xref ----------
    def xrefs(e, target):
        """扫描 .text (main 段) 找 jal/j 到 target 的指令位置 (VA)"""
        hits = []
        ph = [p for p in e.phdrs if p['type'] == 1 and p['filesz'] > 0][0]
        o0, o1 = ph['off'], ph['off'] + ph['filesz']
        tgt26 = (target >> 2) & 0x3FFFFFF
        for o in range(o0 & ~3, o1 - 3, 4):
            w = struct.unpack_from('<I', e.b, o)[0]
            op = w >> 26
            if op in (2, 3) and (w & 0x3FFFFFF) == tgt26:
                va, _ = e.off2va(o)
                hits.append((va, 'jal' if op == 3 else 'j'))
        return hits

    buf.write('== A) cave 落点的调用者 xref (在英文原盘 ELF 上扫 jal/j) ==\n')
    buf.write('%-14s %-10s %-8s %s\n' % ('目标', 'VA', '调用数', '调用点 VA (最多 20 个)'))
    for (nm, va) in CAVE_ENTRIES + [('hook %s' % hex(t), t) for t in HOOK_TARGETS]:
        h = xrefs(e_en, va)
        buf.write('%-14s 0x%08X %-8d %s\n'
                  % (nm, va, len(h), ' '.join('0x%X' % x[0] for x in h[:20])))
    # 对汉化盘也扫一遍 (汉化新增的调用)
    buf.write('\n-- 同上, 但扫汉化盘 ZH113b_fix (差异 = 汉化新增的调用) --\n')
    for (nm, va) in CAVE_ENTRIES:
        a = set(x[0] for x in xrefs(e_en, va))
        b = set(x[0] for x in xrefs(e_zh, va))
        buf.write('%-14s 0x%08X  EN=%d ZH=%d  新增=%s  失去=%s\n'
                  % (nm, va, len(a), len(b),
                     ' '.join('0x%X' % x for x in sorted(b - a)) or '-',
                     ' '.join('0x%X' % x for x in sorted(a - b)) or '-'))

    # ---------- B) EN_STRINGS.TXT 旧位置 ----------
    buf.write('\n== B) EN_STRINGS.TXT 旧位置内容 (MENU.IMG off=2,414,080, stored 2,749) ==\n')
    for tag in ('EN_ORIG', 'ZH113b_fix'):
        iso = N.Iso(N.ISO[tag])
        f = iso.files()['/MENU.IMG;1']
        base = f['lba'] * N.SEC
        blob = iso.rd(base + 2414080, 2749)
        z = sum(1 for c in blob if c == 0)
        buf.write('  %-12s 全零字节 %d/%d ; 前 64 B: %s\n'
                  % (tag, z, len(blob), blob[:64].hex(' ')))
        buf.write('               可打印预览: %r\n'
                  % bytes(c if 32 <= c < 127 else 0x2E for c in blob[:96]))
        # 新位置
        ents, hdr, names = iso.img_entries(f['lba'], None)
        e = [x for x in ents if x['name'] == 'EN_STRINGS.TXT'][0]
        nb = iso.rd(base + e['off'], e['stored'])
        buf.write('               新位置 off=%d 前 64 B: %s\n' % (e['off'], nb[:64].hex(' ')))
        iso.close()

    # ---------- C) 硬编码偏移立即数搜索 ----------
    buf.write('\n== C) ELF 中是否存在指向 2,414,080 (=0x24D400) 的立即数 ==\n')
    for tag, e in (('EN_ORIG', e_en), ('ZH113b_fix', e_zh)):
        ph = [p for p in e.phdrs if p['type'] == 1 and p['filesz'] > 0][0]
        o0, o1 = ph['off'], ph['off'] + ph['filesz']
        hits = []
        for target in (0x24D400, 0x24D230, 0x258000, 0x57400):
            for o in range(o0 & ~3, o1 - 3, 4):
                w = struct.unpack_from('<I', e.b, o)[0]
                op = w >> 26
                if op in (0x0F, 0x0D, 0x09, 0x0C, 0x23, 0x2B):   # lui/ori/addiu/andi/lw/sw
                    imm = w & 0xFFFF
                    if imm == (target & 0xFFFF):
                        va, _ = e.off2va(o)
                        hits.append((target, va, w))
        buf.write('  %-12s imm==目标低16位 的指令数 = %d (仅供参考, 未做全局常量折叠)\n'
                  % (tag, len(hits)))
    print(buf.getvalue())
    with open(os.path.join(N.EVID, 'stage14_xref.txt'), 'w', encoding='utf-8') as fh:
        fh.write(buf.getvalue())


if __name__ == '__main__':
    main()
