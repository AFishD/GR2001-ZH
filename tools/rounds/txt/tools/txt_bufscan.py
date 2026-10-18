# -*- coding: utf-8 -*-
r"""txt_bufscan.py —— 任务 B：在原盘 ELF 的文字/名字/折行路径上搜「固定容量缓冲」证据。

产出（写入 work\builds\GR_TXT\audit\）:
  B_funcfixed.txt   5 个指定函数的反汇编 + 帧大小 + 固定立即数
  B_fixedmem.txt    全 .text：调用 memcpy/memset/strcpy/strncpy/strcat/sprintf 之前
                    用 `addiu/li aK, zero, IMM` 写死的**常量长度**站点（目标若是 sp+off 即栈缓冲）
  B_stackbuf.txt    全 .text：`addiu sp,sp,-N` 帧 ≥ 256 的函数 + 帧内 `addiu aK,sp,off` 传送给
                    上述内存函数的目标缓冲（固定容量候选）

只读：ELF 从 third_party\orig\ps2\slus_out\SLUS_206.13（原盘解出，与 ISO 内逐字节相同）读出。
"""
import importlib.util
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUT = os.path.join(ROOT, 'work', 'builds', 'GR_TXT', 'audit')
ELF = os.path.join(ROOT, r'third_party\orig\ps2\slus_out\SLUS_206.13')

sys.path.insert(0, os.path.join(ROOT, 'tools', 're', 'toolbelt'))
_spec = importlib.util.spec_from_file_location('cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CD)
_spec2 = importlib.util.spec_from_file_location('cave_syms', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_syms.py'))
CS = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(CS)

MEMFUNS = ('memcpy', 'memset', 'memmove', 'strcpy', 'strncpy', 'strcat', 'strncat',
           'sprintf', 'snprintf', 'bcopy', 'strlen', 'strcmp', 'strncmp', 'wcstombs',
           'wctomb', 'mbstowcs')

TARGETS = [
    ('GetUISoldierAbbreviateName__Fii', 0x2ECDA0, 536),
    ('GetActorNameAbbreviated__9ActorFileCFv', 0x307090, 224),
    ('DoWordWrap__15RSTextComponentFRC10RSUIString', 0x21CC10, 936),
    ('AddOneWord__9RSFontMgrFRC9RSVector4RC9RSVector4RC7RSColorfb', 0x219F50, 572),
    ('DrawLetters__12IkeFontTableFv', 0x2164C0, 280),
    ('DrawString__9RSFontMgrFPCcffRC7RSColorP6RSFontPCiPCii', 0x219A70, 912),
    ('DrawTheString__15RSTextComponentFRC10RSUIString', 0x21C4C0, 1008),
    ('ComputeDrawXY__15RSTextComponentFRC10RSUIString', 0x21CA20, 488),
    ('Substring__10RSUIStringCFii', 0x540F60, 408),
    ('RSStringTable__ReadResource', 0x53EC50, 336),
]


def symmap():
    syms = CS.load_syms(ELF)
    byva, ranges = {}, []
    for (val, size, info, shndx, nm) in syms:
        if val and size:
            ranges.append((val, val + size, nm))
        if val:
            byva.setdefault(val, (size, nm))
    ranges.sort()
    return byva, ranges


def owner(ranges, va):
    best = None
    for (a, b, nm) in ranges:
        if a <= va < b:
            if best is None or a > best[0]:
                best = (a, b, nm)
    return best


def imm_of(w):
    op = w >> 26
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    imm = w & 0xFFFF
    if op == 0x09 and rs == 0:          # addiu rt, zero, imm
        return rt, imm if imm < 0x8000 else imm - 0x10000
    if op == 0x0D and rs == 0:          # ori rt, zero, imm
        return rt, imm
    return None, None


def spoff(w):
    """`addiu rt, sp, imm` → (rt, off)"""
    op = w >> 26
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    if op == 0x09 and rs == 29:
        imm = w & 0xFFFF
        return rt, (imm if imm < 0x8000 else imm - 0x10000)
    return None, None


def frame_size(elf, va):
    w = elf.word(va)
    op = w >> 26
    if op == 0x09 and ((w >> 21) & 0x1F) == 29 and ((w >> 16) & 0x1F) == 29:
        imm = w & 0xFFFF
        return -(imm - 0x10000) if imm >= 0x8000 else -imm
    return None


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    elf = CD.Elf(ELF)
    byva, ranges = symmap()
    va0, off0, fsz = elf.text()
    memva = {}
    for (val, size, info, shndx, nm) in CS.load_syms(ELF):
        base = nm.split('@')[-1]
        if base in MEMFUNS and val:
            memva.setdefault(val, base)

    L1 = ['# 原盘 ELF: %s' % ELF,
          '# PT_LOAD#0 va=0x%08X off=0x%08X filesz=0x%08X' % (va0, off0, fsz),
          '# 内存函数 VA: %s' % ', '.join('%s=0x%X' % (nm, v) for v, nm in
                                          sorted(memva.items())),
          '']
    for (nm, va, size) in TARGETS:
        fr = frame_size(elf, va)
        L1.append('==== %s   VA 0x%08X size %d  帧 addiu sp,sp,-%s ===='
                  % (nm, va, size, fr))
        for v, w in elf.iter_words(va, va + size):
            L1.append('  %08x  %08x  %s' % (v, w, CD.dis(w, v)))
        L1.append('')
    open(os.path.join(OUT, 'B_funcfixed.txt'), 'w', encoding='utf-8').write('\n'.join(L1))
    print('[out] B_funcfixed.txt  (%d lines)' % len(L1))

    # ── 全局: 常量长度的内存调用 ──
    rows = []
    va = va0
    end = va0 + fsz - 4
    while va < end:
        w = elf.word(va)
        if (w >> 26) == 3:                                    # jal
            tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
            if tgt in memva:
                # 回看 8 条指令
                size_rt, size_val, dst = {}, {}, None
                for k in range(1, 9):
                    pv = va - 4 * k
                    if pv < va0:
                        break
                    pw = elf.word(pv)
                    rt, iv = imm_of(pw)
                    if rt in (4, 5, 6, 7) and rt not in size_rt and iv is not None:
                        size_rt[rt] = (iv, pv)
                    drt, doff = spoff(pw)
                    if drt is not None and dst is None:
                        dst = (drt, doff, pv)
                own = owner(ranges, va)
                rows.append(dict(site=va, fn=(own[2] if own else '?'),
                                 fn_va=(own[0] if own else 0),
                                 callee=memva[tgt],
                                 a0=size_rt.get(4), a1=size_rt.get(5),
                                 a2=size_rt.get(6), a3=size_rt.get(7),
                                 dst=dst))
        va += 4
    with open(os.path.join(OUT, 'B_fixedmem.txt'), 'w', encoding='utf-8') as f:
        f.write('# site_va function function_va callee  const_a0 const_a1 const_a2 const_a3'
                '  stack_dst(reg,off)   [仅列出至少有一个常量长度参数的站点]\n')
        n = 0
        for r in rows:
            consts = [r['a0'], r['a1'], r['a2'], r['a3']]
            if not any(c is not None for c in consts):
                continue
            n += 1
            fmt = '0x%08X %-52s 0x%08X %-10s'
            vals = (r['site'], r['fn'][:52], r['fn_va'], r['callee'])
            cs = ' '.join('%6s' % (str(c[0]) if c else '-') for c in consts)
            ds = ('%d,sp%+d' % (r['dst'][0], r['dst'][1])) if r['dst'] else '-'
            f.write((fmt % vals) + ' ' + cs + '   ' + ds + '\n')
        print('[out] B_fixedmem.txt  (%d 站点, 共扫描 %d 个内存调用点)' % (n, len(rows)))

    # ── 大栈帧函数 ──
    frames = []
    for v in range(va0, end, 4):
        fr = frame_size(elf, v)
        if fr and fr >= 256:
            own = owner(ranges, v)
            frames.append((v, fr, own[2] if own else '?'))
    with open(os.path.join(OUT, 'B_stackbuf.txt'), 'w', encoding='utf-8') as f:
        f.write('# 帧 ≥ 256 B 且自身是函数入口 (addiu sp,sp,-N) 的函数\n')
        for (v, fr, nm) in frames:
            f.write('0x%08X  frame=%-6d %s\n' % (v, fr, nm))
    print('[out] B_stackbuf.txt  (%d 个函数帧 ≥256 B)' % len(frames))


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                                 # noqa: BLE001
        pass
    main()
