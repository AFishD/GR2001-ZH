# -*- coding: utf-8 -*-
r"""verify_elf_segments.py — 用 ELF 的 program header 严格校验 ISO↔VA 映射

背景: 我先前用 "ISO = 0x937A0 + 0xE0 + (VA − 0x100000)" 反汇编并打了 gate 补丁，
      该式只由"gate 站点处恰为 sltiu…0xB1"自校验过 ⇒ 不能证明它**对所有段**成立 ✗
本脚本: 读 ELF 头 + program header，按段算出每个 VA 的真实 ISO 偏移，并与我的式子对照 ✓
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
ELF_ISO = 0x295 * 2048          # SLUS_206.13;1 @LBA 295
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

data = open(ISO, 'rb').read()
eh = data[ELF_ISO:ELF_ISO + 52]
magic = eh[:4]
print('ELF magic = %s  %s' % (magic, '✓' if magic == b'\x7fELF' else '✗'))
if magic != b'\x7fELF':
    # 也许有 CD 头偏移
    for probe in (0x80, 0, 0x20):
        m = data[ELF_ISO + probe:ELF_ISO + probe + 4]
        print('  试探 +0x%X: %s' % (probe, m))
    sys.exit(1)

e_type, e_machine = struct.unpack_from('<HH', eh, 16)
e_entry = struct.unpack_from('<I', eh, 24)[0]
e_phoff = struct.unpack_from('<I', eh, 28)[0]
e_phentsize, e_phnum = struct.unpack_from('<HH', eh, 42)
print('type=%d machine=%d entry=0x%X phoff=0x%X phentsize=%d phnum=%d'
      % (e_type, e_machine, e_entry, e_phoff, e_phentsize, e_phnum))
print()
print('program headers（VA→文件偏移）:')
segs = []
for i in range(e_phnum):
    o = ELF_ISO + e_phoff + i * e_phentsize
    p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<6I', data, o)
    segs.append((p_type, p_offset, p_vaddr, p_filesz, p_memsz))
    print('  #%d type=0x%X file_off=0x%-8X vaddr=0x%-8X filesz=0x%-8X memsz=0x%X'
          % (i, p_type, p_offset, p_vaddr, p_filesz, p_memsz))
print()


def iso_of(va):
    for p_type, p_offset, p_vaddr, p_filesz, p_memsz in segs:
        if p_type == 1 and p_vaddr <= va < p_vaddr + p_filesz:
            return ELF_ISO + p_offset + (va - p_vaddr)
    return None


print('★ 用 program header 校验我的映射式: ISO = 0x937A0 + 0xE0 + (VA − 0x100000)')
for va in (0x416EE8, 0x417160, 0x41751C, 0x5656A4, 0x416ED0, 0x219C08, 0x219C14):
    real = iso_of(va)
    mine = 0x937A0 + 0xE0 + (va - 0x100000)
    tag = '一致 ✓' if real == mine else ('**不一致** ✗ 真实=0x%X' % real if real else '**不在任何 LOAD 段** ✗')
    val = struct.unpack_from('<I', data, real)[0] if real else None
    print('  VA 0x%08X  真实 ISO 0x%X  我的式子 0x%X  %s  该处字=%s'
          % (va, real or 0, mine, tag, ('%08X' % val) if val is not None else '-'))
print()
print('  ⇒ 若"真实 == 我的式子"对以上全部成立 ⇒ 我之前下的 4 个 gate 补丁**位置正确** ✓')
