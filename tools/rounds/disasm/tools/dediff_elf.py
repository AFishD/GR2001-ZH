# -*- coding: utf-8 -*-
r"""dediff_elf.py —— 两个同血统 SLUS_206.13 ELF 的逐字节差异 → 按字归并成指令站点。

只读。用于把「基底盘 gate 0xB1 ELF」与「2400 盘 gate 0xBA ELF」的**全部**代码差异列成站点表，
从而回答"两条路径到底差在哪几条指令"。

用法：
  python dediff_elf.py <A.elf> <B.elf> [--va-lo H] [--va-hi H] [--json out.json]
  python dediff_elf.py <A.elf> <B.elf> --vadiff <VA> [--n 8]
  python dediff_elf.py <A.elf> <B.elf> --bytes <VA> <n>
"""
import importlib.util
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location('cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

GPR = CD.GPR


def dis1(w, pc):
    """在 cave_dis.dis 之上补齐 LQ/SQ（opcode 0x1E/0x1F）。"""
    op = (w >> 26) & 0x3F
    if op in (0x1E, 0x1F):
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0]
        return '%s $%s, %d($%s)' % ('lq' if op == 0x1E else 'sq', GPR[rt], imm, GPR[rs])
    return CD.dis(w, pc)


def off2va(segs, off):
    for (v, o, fs) in segs:
        if o <= off < o + fs:
            return v + (off - o)
    return None


def va2off(segs, va):
    for (v, o, fs) in segs:
        if v <= va < v + fs:
            return o + (va - v)
    return None


def load(p):
    with open(p, 'rb') as f:
        return f.read()


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap, bp = sys.argv[1], sys.argv[2]
    argd = {}
    i = 3
    while i < len(sys.argv):
        k = sys.argv[i]
        if k == '--json':
            argd['json'] = sys.argv[i + 1]; i += 2
        elif k == '--vadiff':
            argd['vadiff'] = int(sys.argv[i + 1], 16); i += 2
        elif k == '--n':
            argd['n'] = int(sys.argv[i + 1]); i += 2
        elif k == '--bytes':
            argd['bytes'] = int(sys.argv[i + 1], 16); argd['bn'] = int(sys.argv[i + 2]); i += 3
        elif k == '--va-lo':
            argd['lo'] = int(sys.argv[i + 1], 16); i += 2
        elif k == '--va-hi':
            argd['hi'] = int(sys.argv[i + 1], 16); i += 2
        else:
            raise SystemExit('未知参数 %s' % k)
    ea, eb = CD.Elf(ap), CD.Elf(bp)
    A, B = load(ap), load(bp)
    print('# A = %s' % ap)
    print('# B = %s' % bp)
    print('# size A/B = %d / %d ; segs A = %s' % (len(A), len(B), ea.segs))
    if 'bytes' in argd:
        o = va2off(ea.segs, argd['bytes'])
        n = argd['bn']
        print()
        print('VA 0x%08X  A = %s' % (argd['bytes'], A[o:o + n].hex()))
        print('VA 0x%08X  B = %s' % (argd['bytes'], B[o:o + n].hex()))
        return
    if 'vadiff' in argd:
        va = argd['vadiff']; cnt = argd.get('n', 8)
        oa = va2off(ea.segs, va)
        ob = va2off(eb.segs, va)
        print()
        print('=== VA 0x%08X（ELF 偏移 A/B 0x%X / 0x%X）前后 %d 条 ===' % (va, oa, ob, cnt))
        print('  %-10s %-10s %-10s %-26s | %-26s' % ('VA', 'A_word', 'B_word', 'A', 'B'))
        for k in range(-cnt, cnt + 1):
            wa = struct.unpack_from('<I', A, oa + k * 4)[0]
            wb = struct.unpack_from('<I', B, ob + k * 4)[0]
            mark = ' *' if wa != wb else '  '
            print('  %08x %08x %08x %-26s | %-26s%s'
                  % (va + k * 4, wa, wb, dis1(wa, va + k * 4), dis1(wb, va + k * 4), mark))
        return
    n = min(len(A), len(B))
    runs = []
    i = 0
    while i < n:
        if A[i] != B[i]:
            j = i
            while j < n and A[j] != B[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    if len(A) != len(B):
        runs.append((n, max(len(A), len(B))))
    print('# 差异 run = %d，差异字节 = %d' % (len(runs), sum(b - a for a, b in runs)))
    lo, hi = argd.get('lo', 0), argd.get('hi', 1 << 62)
    rows = []
    idx = 0
    print()
    print('| # | VA | ELF off | A words | B words | A 指令 | B 指令 | B |')
    print('|---|---|---|---|---|---|---|---|')
    for a, b in runs:
        va = off2va(ea.segs, a)
        if va is None or not (lo <= va < hi):
            if va is None:
                print('| - | [段外] | 0x%X | %d B | | | | %d |' % (a, b - a, b - a))
            continue
        idx += 1
        first = a & ~3
        words_a, words_b = [], []
        for o in range(first, min(b + 3, n), 4):
            words_a.append(struct.unpack_from('<I', A, o)[0])
            words_b.append(struct.unpack_from('<I', B, o)[0])
        vaa = va - (a - first)
        sa = ' / '.join(dis1(w, vaa + 4 * t) for t, w in enumerate(words_a))
        sb = ' / '.join(dis1(w, vaa + 4 * t) for t, w in enumerate(words_b))
        print('| %d | 0x%08X | 0x%X | %s | %s | `%s` | `%s` | %d |'
              % (idx, vaa, a, ' '.join('%08X' % w for w in words_a),
                 ' '.join('%08X' % w for w in words_b), sa, sb, b - a))
        rows.append({'va': vaa, 'off': a, 'len': b - a, 'a': words_a, 'b': words_b,
                     'a_dis': sa, 'b_dis': sb})
    if 'json' in argd:
        with open(argd['json'], 'w', encoding='utf-8') as f:
            json.dump({'a': ap, 'b': bp, 'segs_a': ea.segs, 'runs': rows}, f, indent=1)
        print()
        print('[out] %s' % argd['json'])


if __name__ == '__main__':
    main()
