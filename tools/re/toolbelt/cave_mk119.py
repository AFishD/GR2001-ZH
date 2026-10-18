# -*- coding: utf-8 -*-
r"""cave_mk119.py -- GR_ZH119 = GR_ZH113b + ONE instruction.

WHY (round79 audit, docs/REPORT_cave_count_vs_bytes.md §4)
---------------------------------------------------------
The localization's code cave at VA 0x5657C8 (entered by `j 0x5657C8` from the text
layout function at 0x3070B4) computes a string length and hands it to the helper
0x565760 ("trim trailing spaces + does the string contain a DBCS byte"):

    0x5657C8  lw   $t0, 72($s0)      ; t0 = RSString::p  = RSUIString::mImpl
    0x5657D4  lw   $a0,  4($t0)      ; a0 = mImpl->data            (char *)
    0x5657E0  lhu  $a1,  2($t0)      ; <-- BUG: mImpl+2 is a *u8 mode flag*
                                     ;          mImpl+0 is the *u16 length*
    0x5657E4  jal  0x565760          ; helper(data, len)

Layout proof (both instructions from the retail ELF, unmodified by the ZH patch):

    Length__10RSUIStringCFv  0x53FD58  lw v0,4(a0)   ; v0 = this->mImpl
                             0x53FD5C  lw a0,4(v0)   ; a0 = mImpl->data
                             0x53FD68  jal 0x406F28  ; strlen(data)   <- Length() is strlen
    __vc__10RSUIStringFi     0x5414C8  lw v0,4(a0)   ; v0 = this->mImpl
                             0x5414D4  lbu v0,2(v0)  ; <-- mImpl+2 read as a *single byte*
                             0x5414D8  slti at,v0,2
                             0x5414E4  addiu v0,v0,-1
                             0x5414E8  sb   v0,0(v1) ; <-- and written back as a single byte
                             0x54151C  sh   v0,0(s2) ; <-- mImpl+0 (u16) = strlen+1  (the length)
    (byte mImpl+3 is never written by that constructor => uninitialised heap residue)

So `lhu a1,2(t0)` reads {mode_u8, uninitialised_pad} as a 16-bit length.  When the pad
byte happens to be non-zero the helper scans up to 65535 bytes past the end of the
string and the result is used as the count for RSString::Left(count) -> nondeterministic
out-of-bounds read / oversized substring: exactly the "session dependent, only sometimes
bad" behaviour reported from the user's machine.

FIX: read the length field (+0, u16) instead of the mode byte (+2, u8):
     0x5657E0  0x95050002  lhu $a1, 2($t0)   ->   0x95050000  lhu $a1, 0($t0)

This is the *only* byte range this script touches (4 bytes of the ELF).  It does not
touch text, fonts, containers or the ISO layout.

A second, strictly-neutralising alternative (not applied here) is to make the cave fall
through to the original code unconditionally: 0x5657C8 0x081595F2 -> 0x081595E0
(`j 0x565828`), which restores `RSString::Left(1)` exactly as the retail game does.

usage: python cave_mk119.py <src_iso> <dst_iso>      (invoked by make_build.py --patch)
"""
import shutil
import struct
import sys

ELF_LBA = 295
ELF_OFF_BASE = 0x80          # ELF PT_LOAD[0].p_offset
ELF_VA_BASE = 0x00100000     # ELF PT_LOAD[0].p_vaddr

VA = 0x005657E0
OLD, NEW = 0x95050002, 0x95050000    # lhu a1,2(t0) -> lhu a1,0(t0)


def va2iso(va):
    return ELF_LBA * 2048 + ELF_OFF_BASE + (va - ELF_VA_BASE)


def main(src, dst):
    shutil.copyfile(src, dst)
    off = va2iso(VA)
    with open(dst, 'r+b') as f:
        f.seek(off)
        cur = struct.unpack('<I', f.read(4))[0]
        assert cur == OLD, '0x%08X 现值 0x%08X != 0x%08X (非 GR_ZH113b 基底?)' % (VA, cur, OLD)
        f.seek(off)
        f.write(struct.pack('<I', NEW))
        f.seek(off)
        assert struct.unpack('<I', f.read(4))[0] == NEW
    print('[ELF] 0x%08X: 0x%08X -> 0x%08X  (lhu a1,2(t0) -> lhu a1,0(t0)) OK' % (VA, OLD, NEW))

    # whole-image diff assertion: exactly 4 bytes changed (0x95 stays, 0x02->0x00)
    a = open(src, 'rb')
    b = open(dst, 'rb')
    pos, outside, total = 0, 0, 0
    while True:
        ca, cb = a.read(1 << 20), b.read(1 << 20)
        if not ca:
            break
        assert len(ca) == len(cb), 'size changed?'
        if ca != cb:
            for i in range(len(ca)):
                if ca[i] != cb[i]:
                    total += 1
                    if not (off <= pos + i < off + 4):
                        outside += 1
        pos += len(ca)
    a.close()
    b.close()
    assert outside == 0, '%d 处窗口外差异' % outside
    print('[diff] 全盘差异 %d 字节, 全部位于 ELF 0x%X..0x%X 4 字节窗口内 OK' % (total, off, off + 4))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
