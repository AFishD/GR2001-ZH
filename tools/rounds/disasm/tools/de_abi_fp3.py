# -*- coding: utf-8 -*-
r"""de_abi_fp3.py —— 严谨的 $fp 活跃性分析：找出「被 DrawString 破坏后**直接使用**」的站点。

原理：
  * DrawString(0x219A70) 因拦截器跳过 `sq fp,144(sp)` 而**不保存/恢复 $fp**。
  * 于是：某函数把值放进 $fp → 调用 DrawString（值被破坏）→ **在重新写 $fp 之前读 $fp**
    ⇒ 读到的是垃圾（未初始化栈槽内容）⇒ 真正的 ABI 受害者。
  * 若中间有对 $fp 的**重新写入**（`lw/lq fp,N(sp)` 溢出重载、`pcpyld/or fp,...` 等），
    则破坏被"修好"，不算受害者。

只读。
用法： python de_abi_fp3.py <elf> <calleeVA> [<calleeVA> ...]
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
FP = 30

MEM_LD = {0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x37}
MEM_ST = {0x28, 0x29, 0x2A, 0x2B, 0x3F}
IMM_W = {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x18, 0x19, 0x1A, 0x1B}
ALU_R = {0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F}
MMI = {0x1C, 0x1D, 0x1E}


def txt(w, pc):
    op = (w >> 26) & 0x3F
    if op in (0x1E, 0x1F):
        rs, rt = (w >> 21) & 0x1F, (w >> 16) & 0x1F
        imm = struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0]
        return '%s $%s, %d($%s)' % ('lq' if op == 0x1E else 'sq', GPR[rt], imm, GPR[rs])
    return CD.dis(w, pc)


def fp_effect(w):
    """返回 ('W',None) 写 fp | ('R',None) 读 fp | (None,None)"""
    op = (w >> 26) & 0x3F
    funct = w & 0x3F
    rs, rt, rd = (w >> 21) & 0x1F, (w >> 16) & 0x1F, (w >> 11) & 0x1F
    if op in (0x1E, 0x1F):                       # lq/sq
        if rt == FP:
            return ('W', None)
        if rs == FP:
            return ('R', None)
        return (None, None)
    if op in MEM_LD:
        if rt == FP:
            return ('W', None)
        if rs == FP:
            return ('R', None)
        return (None, None)
    if op in MEM_ST:
        if rs == FP:
            return ('R', None)
        return (None, None)
    if op in IMM_W:
        if rt == FP:
            return ('W', None)
        if rs == FP:
            return ('R', None)
        return (None, None)
    if op in MMI:                                # pcpyld / pcpyud / pceqw ...
        if rd == FP:
            return ('W', None)
        if rs == FP or rt == FP:
            return ('R', None)
        return (None, None)
    if op == 0 and funct in ALU_R:
        if rd == FP:
            return ('W', None)
        if rs == FP or rt == FP:
            return ('R', None)
        return (None, None)
    if op == 0 and funct in (0x02, 0x03):
        if rd == FP:
            return ('W', None)
        if rt == FP:
            return ('R', None)
        return (None, None)
    if op == 0 and funct in (0x08,):
        return ('RET', None)
    return (None, None)


def func_start(elf, va, lo):
    """向前找函数起点：上一个 jr ra 之后。"""
    p = va
    while p > lo:
        w = elf.word(p - 8)
        if (w >> 26) == 0 and (w & 0x3F) == 0x08:
            return p - 4          # jr ra 的延迟槽之后
        w2 = elf.word(p - 4)
        if (w2 >> 26) == 0 and (w2 & 0x3F) == 0x08:
            return p
        p -= 4
    return lo


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = CD.Elf(sys.argv[1])
    targets = set(int(a, 16) for a in sys.argv[2:])
    va0, off0, fsz = elf.text()
    hi = va0 + fsz
    calls = []
    for va in range(va0, hi - 4, 4):
        w = elf.word(va)
        if ((w >> 26) & 0x3F) == 3:
            t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
            if t in targets:
                calls.append(va)
    print('# %s' % sys.argv[1])
    print('# 目标 %s ；调用点 %d 个' % (['0x%08X' % t for t in sorted(targets)], len(calls)))
    print()

    # 收集需要分析的函数（调用点所在函数）
    funcs = {}
    for c in calls:
        fs = func_start(elf, c, va0)
        funcs.setdefault(fs, []).append(c)
    victims = []
    for fs in sorted(funcs):
        # 简单线性流：live 状态
        live = False
        killed_at = None
        rows = []
        va = fs
        n = 0
        while va < hi and n < 20000:
            w = elf.word(va)
            if ((w >> 26) & 0x3F) == 3:
                t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                if t in targets and live:
                    killed_at = va
                    rows.append((va, w, txt(w, va), 'CALL(杀掉 $fp)'))
            eff, _b = fp_effect(w)
            if eff == 'W':
                live = True
                killed_at = None          # ★ 重新赋值 ⇒ 之前的破坏被修好
                rows.append((va, w, txt(w, va), 'W($fp 重新赋值 ⇒ 破坏被修好)'))
            elif eff == 'R':
                tag = 'R'
                if live:
                    if killed_at is not None:
                        tag = '★★ 受害者：读被杀掉的 $fp'
                        victims.append((fs, killed_at, va, w, txt(w, va)))
                    else:
                        tag = 'R(尚未被杀，良性)'
                else:
                    tag = 'R($fp 未赋值，不可达/其它)'
                rows.append((va, w, txt(w, va), tag))
            elif eff == 'RET':
                rows.append((va, w, txt(w, va), 'RET(函数结束)'))
                if va > max(funcs[fs]):
                    break
            va += 4
            n += 1
        has_v = any('受害者' in r[3] for r in rows)
        if has_v or any('CALL(杀掉' in r[3] for r in rows):
            print('--- 函数 @ 0x%08X（含调用点 %s）---'
                  % (fs, ', '.join('0x%08X' % c for c in sorted(funcs[fs]))))
            for r in rows:
                if 'CALL(杀掉' in r[3] or '受害者' in r[3] or r[3].startswith('W(') or 'RET' in r[3]:
                    print('      0x%08X  %08X  %-40s %s' % r)
            print()
    print('=== ★ 真受害者站点 %d 个 ===' % len(victims))
    for (fs, k, u, w, s) in victims:
        print('   函数 0x%08X : DrawString 调用 0x%08X 破坏 $fp ；之后 0x%08X 处直接使用： %s'
              % (fs, k, u, s))


if __name__ == '__main__':
    main()
