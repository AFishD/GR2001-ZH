# -*- coding: utf-8 -*-
r"""de_dis.py —— 定向反汇编（含 LQ/SQ 等 SPECIAL3 补齐）+ 调用者/被调用者可达性。

只读。所有输出都直接来自 ELF 字节，报告里引用的每条指令都可用本工具复现。

用法：
  python de_dis.py <elf> dis <loVA> <hiVA> [--mark VA ...]     # 线性反汇编
  python de_dis.py <elf> word <VA> [VA ...]                    # 单字
  python de_dis.py <elf> callers <targetVA> [targetVA ...]     # 谁 jal/j 到它
  python de_dis.py <elf> callees <loVA> <hiVA>                 # 区间内所有 jal 目标
  python de_dis.py <elf> reach <loVA> <hiVA>                   # 区间外部入口 = 可达性
  python de_dis.py <elf> hex <VA> <n>
  python de_dis.py <elf> strings <loVA> <hiVA>
  python de_dis.py <elf> segs
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


def dis1(w, pc):
    op = (w >> 26) & 0x3F
    if op in (0x1E, 0x1F):
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0]
        return '%s $%s, %d($%s)' % ('lq' if op == 0x1E else 'sq', GPR[rt], imm, GPR[rs])
    if op == 0x1F and ((w >> 21) & 0x1F) == 0x10:
        return 'sqc2 vf%d, %d($%s)' % ((w >> 16) & 0x1F,
                                       struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0], GPR[(w >> 21) & 0x1F])
    return CD.dis(w, pc)


def target(w, va):
    op = (w >> 26) & 0x3F
    if op in (2, 3):
        return ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
    if op in (1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
        imm = struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0]
        return va + 4 + imm * 4
    if (w >> 26) == 0 and ((w >> 16) & 0x1F) == 8 and (w & 0x3F) == 8:  # jr
        return None
    if op in (0x11, 0x12, 0x13):  # cop1 bc
        imm = struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0]
        return va + 4 + imm * 4
    if op == 0x01 and ((w >> 16) & 0x1F) in (0, 1, 2, 3, 0x10, 0x11, 0x12, 0x13, 0x14, 0x16, 0x17):
        imm = struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0]
        return va + 4 + imm * 4
    return None


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = CD.Elf(sys.argv[1])
    cmd = sys.argv[2]
    va0, off0, fsz = elf.text()
    lo_all, hi_all = va0, va0 + fsz
    if cmd == 'segs':
        for (v, o, fs) in elf.segs:
            print('PT_LOAD va=0x%08X off=0x%X filesz=0x%X (%.2f MB)' % (v, o, fs, fs / 1048576.0))
        print('entry = 0x%08X' % elf.entry)
        return
    if cmd == 'dis':
        lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
        marks = []
        rest = sys.argv[5:]
        for i, a in enumerate(rest):
            if a == '--mark':
                continue
            if i and rest[i - 1] == '--mark':
                marks.append(int(a, 16))
        for va in range(lo, hi, 4):
            w = elf.word(va)
            mk = '  <<< ' if va in marks else ''
            t = target(w, va)
            tt = ''
            if t is not None and lo_all <= t < hi_all:
                tt = '  -> 0x%08X' % t
            print('  %08x  %08x  %-44s%s%s' % (va, w, dis1(w, va), tt, mk))
        return
    if cmd == 'word':
        for s in sys.argv[3:]:
            va = int(s, 16)
            w = elf.word(va)
            print('  %08x  %08x  %s' % (va, w, dis1(w, va)))
        return
    if cmd == 'hex':
        va, n = int(sys.argv[3], 16), int(sys.argv[4])
        print('  0x%08X: %s' % (va, elf.read(va, n).hex()))
        return
    if cmd == 'callers':
        want = [int(x, 16) for x in sys.argv[3:]]
        for va in range(lo_all, hi_all - 4, 4):
            w = elf.word(va)
            if ((w >> 26) & 0x3F) in (2, 3):
                t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                if t in want:
                    print('  0x%08X -> 0x%08X   %s' % (va, t, dis1(w, va)))
        return
    if cmd == 'callees':
        lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
        seen = {}
        for va in range(lo, hi, 4):
            w = elf.word(va)
            if ((w >> 26) & 0x3F) == 3:
                t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                seen.setdefault(t, []).append(va)
        for t in sorted(seen):
            print('  0x%08X  <- %s' % (t, ', '.join('0x%08X' % s for s in seen[t])))
        return
    if cmd == 'reach':
        lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
        hits = []
        for va in range(lo_all, hi_all - 4, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            if op in (2, 3):
                t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                if lo <= t < hi and not (lo <= va < hi):
                    hits.append((va, t, 'j' if op == 2 else 'jal'))
            elif op in (1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17, 0x11, 0x12, 0x13):
                imm = struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0]
                t = va + 4 + imm * 4
                if lo <= t < hi and not (lo <= va < hi):
                    hits.append((va, t, 'branch'))
        print('# 区间 [0x%08X, 0x%08X) 的外部入口 = %d 个' % (lo, hi, len(hits)))
        for (f, t, k) in hits:
            print('  0x%08X -> 0x%08X  (%s)  %s' % (f, t, k, dis1(elf.word(f), f)))
        return
    if cmd == 'strings':
        lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
        d = elf.read(lo, hi - lo)
        cur, st = b'', lo
        for i, b in enumerate(d):
            if 32 <= b < 127:
                if not cur:
                    st = lo + i
                cur += bytes([b])
            else:
                if len(cur) >= 4:
                    print('  0x%08X  %r' % (st, cur.decode('latin-1')))
                cur = b''
        if len(cur) >= 4:
            print('  0x%08X  %r' % (st, cur.decode('latin-1')))
        return
    raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
