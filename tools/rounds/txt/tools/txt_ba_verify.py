# -*- coding: utf-8 -*-
r"""txt_ba_verify.py —— B 的三项硬校验（只读 ISO）。

1. 原盘 ELF vs 汉化盘 ELF 在崩溃相关区间（VA 0x540F00..0x541F50 + dlmalloc 0x101C00..0x102B00）
   是否逐字节相同 —— 需要 ISO 内 ELF 偏移 = VA − 0x6C780（ELV ISO base 0x93880 / VA base 0x100000）
2. 0x541038 / 0x541EB0 所在函数与块边界（与 emulog 的 addr 模式对照）
3. 0x5A72D8（RSUIString vtable）在 ELF 内的落点，以及它是不是 .data/.rodata 常量
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ISOS = (('EN_TRUE', r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"),
        ('CVAR04', r"work\builds\GR_CVAR\CVAR_04_text.iso"),
        ('ZH113b', r"work\builds\GR_ZH113b\GR_ZH113b.iso"))
ELF_ISO_BASE, ELF_VA_BASE = 0x93880, 0x100000   # PT_LOAD#0: file off 0x80, va 0x100000
K = ELF_ISO_BASE - ELF_VA_BASE                  # ISO = VA + K  (K = -0x6C780)

WINDOWS = ((0x540F00, 0x541F50, 'RSUIString 字符串类 (Substring/= /~dt/Left/Right/FindChar)'),
           (0x101C00, 0x102B00, 'dlmalloc (chunk_free/chunk_alloc/mmalloc_free/small_free)'),
           (0x219A00, 0x21AF40, 'RSFontMgr::DrawString + RSFont 度量/UV'),
           (0x21C280, 0x21D300, 'SetTextID / DoWordWrap / AddOneWord 邻域'),
           (0x2ECDA0, 0x2ECFC0, 'GetUISoldierAbbreviateName'),
           (0x307090, 0x307170, 'GetActorNameAbbreviated'))

data = {}
for tag, rel in ISOS:
    iso = T.Iso(os.path.join(ROOT, rel))
    data[tag] = iso
print('ELF: ISO = VA %+#x ; PT_LOAD#0 off=0x80 va=0x100000' % K)
print()
for (lo, hi, name) in WINDOWS:
    off = lo + K
    bs = {t: bytes(data[t].read(off, hi - lo)) for (t, _r) in ISOS}
    eq_cv = bs['EN_TRUE'] == bs['CVAR04']
    eq_zh = bs['EN_TRUE'] == bs['ZH113b']
    nd_cv = sum(1 for a, b in zip(bs['EN_TRUE'], bs['CVAR04']) if a != b)
    nd_zh = sum(1 for a, b in zip(bs['EN_TRUE'], bs['ZH113b']) if a != b)
    print('VA 0x%08X..0x%08X  %-52s  EN==CVAR04: %-5s (%d B 异)   EN==ZH113b: %-5s (%d B 异)'
          % (lo, hi, name, eq_cv, nd_cv, eq_zh, nd_zh))
print()

# 0x5A72D8 落点：ELF 内 VA 0x5A72D8 → ISO 偏移
for tag, rel in ISOS:
    iso = data[tag]
    va = 0x5A72D8
    try:
        w = bytes(iso.read(va + K, 16))
        print('%-8s VA 0x5A72D8 (RSUIString vtable) @ISO 0x%X : %s'
              % (tag, va + K, w.hex(' ')))
    except Exception as ex:                                               # noqa: BLE001
        print('%-8s VA 0x5A72D8 读取失败 %r' % (tag, ex))
print()
# 关键指令回读断言（原盘）
asm = {
    0x541038: 'lw $a0, 0($s1)          <- 崩溃块起点',
    0x54103c: 'lui $v0, 0x005A',
    0x541040: 'addiu $v1, $v0, 0x72D8',
    0x54104c: 'lw $a0, 4($a0)          <- obj->data',
    0x541050: 'addu $a0, $a0, $a1      <- +i',
    0x541054: 'sb $zero, 0($a0)        <- ★ TLB Miss addr=0x0 [store]',
    0x541eb0: 'lui $v0, 0x005A          <- 崩溃块起点 (intra-block)',
    0x541eb8: 'sw $v0, 0($s1)          <- ★ TLB Miss addr=<this> [store]',
    0x541ebc: 'lw $v1, 4($s1)          <- ★ TLB Miss addr=<this>+4 [load]',
}
print('原盘 ELF 指令字节回读:')
seen = set()
for va in sorted(asm):
    if va in seen:
        continue
    seen.add(va)
    w = struct.unpack('<I', data['EN_TRUE'].read(va + K, 4))[0]
    w2 = struct.unpack('<I', data['CVAR04'].read(va + K, 4))[0]
    print('  0x%08X  %08X (EN) / %08X (CVAR04)  %s' % (va, w, w2, asm[va]))
for (t, _r) in ISOS:
    data[t].close()
