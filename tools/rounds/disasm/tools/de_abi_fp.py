# -*- coding: utf-8 -*-
r"""de_abi_fp.py —— 量化 DrawString 拦截器造成的 $fp(s8) 破坏：找出所有调用者中
「调用之后仍然使用 $fp」的站点（= 真实受害者候选）。

只读。

背景（实测）：汉化把 `0x219A74 sd ra,160(sp)` 换成 `j 0x565930`；拦截器结尾
`0x5659A4 j 0x219A7C` **跳过 `0x219A78 sq fp,144(sp)`**，而尾声 `0x219DC4 lq fp,144(sp)`
每次都执行 ⇒ DrawString 每次返回都把调用者的 `$fp` 变成**未初始化栈槽的内容**（ABI 违例）。

用法：
  python de_abi_fp.py <elf> <calleeVA> [<calleeVA> ...] [--prologue N] [--stop N]
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


def uses_fp(w):
    """该指令是否读/写 $fp(30)。"""
    op = (w >> 26) & 0x3F
    funct = w & 0x3F
    rs, rt, rd = (w >> 21) & 0x1F, (w >> 16) & 0x1F, (w >> 11) & 0x1F
    # 写入 fp 的常见形式
    if op in (0x09, 0x19, 0x0F, 0x08, 0x18, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E):  # addiu/ori/lui/daddiu...
        return rt == 30
    if op in (0x24, 0x25, 0x20, 0x21, 0x23, 0x2B, 0x28, 0x29, 0x2A):       # lbu/lhu/lb/lh/lw/sw/sb/sh/sd...
        return rs == 30 or rt == 30
    if op == 0 and funct in (0x20, 0x21, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2A, 0x2B):
        return rd == 30 or rs == 30 or rt == 30
    if op == 0 and funct in (0x02, 0x03, 0x06, 0x07):
        return rs == 30 or rd == 30
    if op in (0x1E, 0x1F):
        return ((w >> 21) & 0x1F) == 30 or ((w >> 16) & 0x1F) == 30
    if op in (2, 3):
        return False
    return False


def scan_caller(elf, call_va, ret_va, stop):
    """从 ret_va 往后扫到函数尾声，找 $fp 使用点。返回列表。"""
    out = []
    va = ret_va
    n = 0
    while va < stop and n < 4000:
        w = elf.word(va)
        op = (w >> 26) & 0x3F
        funct = w & 0x3F
        if op == 0 and funct == 0x08:      # jr ra
            break
        if op in (2,) and ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000) < va:
            pass
        if uses_fp(w):
            out.append((va, w, txt(w, va)))
        va += 4
        n += 1
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = CD.Elf(sys.argv[1])
    args = sys.argv[2:]
    stop = 0x1000
    if '--stop' in args:
        i = args.index('--stop'); stop = int(args[i + 1], 16); args = args[:i] + args[i + 2:]
    targets = [int(a, 16) for a in args]
    va0, off0, fsz = elf.text()
    hi = va0 + fsz
    sites = []
    for va in range(va0, hi - 4, 4):
        w = elf.word(va)
        if ((w >> 26) & 0x3F) == 3:
            t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
            if t in targets:
                sites.append((va, t))
    print('# %s' % sys.argv[1])
    print('# 目标函数 %s 的调用点 = %d 个' % (['0x%08X' % t for t in targets], len(sites)))
    bad = 0
    for (cva, t) in sites:
        ret = cva + 8                      # jal 的返回地址（延迟槽后）
        u = scan_caller(elf, cva, ret, min(ret + stop, hi))
        tag = '★ 调用后仍用 $fp' if u else 'ok'
        if u:
            bad += 1
        print('  调用点 0x%08X -> 0x%08X   返回后 %d 条内 $fp 使用 = %d   %s'
              % (cva, t, stop // 4, len(u), tag))
        for (va, w, s) in u:
            print('        0x%08X  %08X  %s' % (va, w, s))
    print()
    print('# 结论：%d / %d 个调用点在被调函数返回后仍使用 $fp ⇒ 会被 DrawString 的 ABI 违例破坏。'
          % (bad, len(sites)))


if __name__ == '__main__':
    main()
