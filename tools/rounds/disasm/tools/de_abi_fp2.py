# -*- coding: utf-8 -*-
r"""de_abi_fp2.py —— DrawString(0x219A70) 的 $fp ABI 违例：精确分类每个调用点的 $fp 用法。

分类：
  SAVE    sq/sw/lq/lw $fp, N($sp)   —— 保存/恢复自己帧里的 $fp（良性）
  WRITE   写 $fp（addiu/lui/daddu... rt/rd=fp）—— 调用者自己改 fp（之后再读才是问题）
  USE     以 $fp 作基址或源操作数（★ 真正的受害者）
  EPI     尾声恢复 $fp（良性，但恢复的是自己存的值 ⇒ 前提是调用者确实存过）

只读。
用法： python de_abi_fp2.py <elf> <calleeVA> [--stop N]
"""
import importlib.util
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location('cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)
GPR = CD.GPR


def txt(w, pc):
    op = (w >> 26) & 0x3F
    if op in (0x1E, 0x1F):
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0]
        return '%s $%s, %d($%s)' % ('lq' if op == 0x1E else 'sq', GPR[rt], imm, GPR[rs])
    return CD.dis(w, pc)


MEM_LD = {0x20, 0x21, 0x23, 0x24, 0x25}          # lb lh lw lbu lhu
MEM_ST = {0x28, 0x29, 0x2A, 0x2B}                # sb sh sw sd
MEM_LD64 = {0x37}                                 # ld
IMM_W = {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F}
ALU_R = {0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F}


def classify(w):
    op = (w >> 26) & 0x3F
    funct = w & 0x3F
    rs, rt, rd = (w >> 21) & 0x1F, (w >> 16) & 0x1F, (w >> 11) & 0x1F
    if op in (0x1E, 0x1F):                       # lq / sq
        base, rt2 = rs, rt
        if rt2 == 30:
            return ('EPI/S', base)
        if base == 30:
            return ('USE', None)
        return (None, None)
    if op in MEM_LD or op == MEM_LD64:
        if rt == 30:
            return ('EPI/S', rs)
        if rs == 30:
            return ('USE', None)
        return (None, None)
    if op in MEM_ST:
        if rt == 30:
            return ('EPI/S', rs)
        if rs == 30:
            return ('USE', None)
        return (None, None)
    if op in IMM_W:
        if rt == 30:
            return ('WRITE', None)
        if rs == 30:
            return ('USE', None)
        return (None, None)
    if op == 0 and funct in ALU_R:
        if rd == 30:
            return ('WRITE', None)
        if rs == 30 or rt == 30:
            return ('USE', None)
        return (None, None)
    if op == 0 and funct in (0x02, 0x03):        # srl/sra
        if rd == 30:
            return ('WRITE', None)
        if rt == 30:
            return ('USE', None)
        return (None, None)
    return (None, None)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = CD.Elf(sys.argv[1])
    tgt = int(sys.argv[2], 16)
    stop = 0x1000
    if '--stop' in sys.argv:
        stop = int(sys.argv[sys.argv.index('--stop') + 1], 16)
    va0, off0, fsz = elf.text()
    hi = va0 + fsz
    sites = []
    for va in range(va0, hi - 4, 4):
        w = elf.word(va)
        if ((w >> 26) & 0x3F) == 3:
            t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
            if t == tgt:
                sites.append(va)
    print('# %s' % sys.argv[1])
    print('# 0x%08X 的调用点 = %d 个；每个调用点向后扫 0x%X 字节' % (tgt, len(sites), stop))
    print()
    victims = []
    for cva in sites:
        va = cva + 8
        end = min(va + stop, hi)
        rows = []
        while va < end:
            w = elf.word(va)
            if (w >> 26) == 0 and (w & 0x3F) == 0x08:      # jr ra
                rows.append((va, w, txt(w, va), 'RET'))
                break
            kind, base = classify(w)
            if kind:
                rows.append((va, w, txt(w, va), kind + ('' if base is None else '(%s)' % GPR[base])))
            va += 4
        real = [r for r in rows if r[3].startswith('USE')]
        tag = '★★ 真受害者（$fp 被当地址用）' if real else ('(仅 保存/恢复，良性)' if rows else '(未触及 $fp)')
        print('  调用点 0x%08X   %s' % (cva, tag))
        for r in rows:
            print('        0x%08X  %08X  %-42s %s' % r)
        if real:
            victims.append((cva, real))
    print()
    print('# ★ 真受害者 = %d 个调用点：' % len(victims))
    for (c, real) in victims:
        print('   0x%08X  →  %s' % (c, ', '.join('0x%08X' % r[0] for r in real)))


if __name__ == '__main__':
    main()
