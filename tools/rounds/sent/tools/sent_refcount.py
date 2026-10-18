# -*- coding: utf-8 -*-
r"""sent_refcount.py —— 候选 C（RSString 的 u8 引用计数 255 回卷）静态跟进。只读。

问题：是否存在一条路径，会让**同一个 RSString 节点**的 refcount 在**一次界面刷新**里
      被 +1 累计到 ≥255（u8 回卷 ⇒ `sb` 写 0 ⇒ 后续析构提前 free ⇒ 悬垂/双 free）？

做法（全部只读 ELF）：
  1. 列出 RSUIString / RSString 的全部成员函数（.symtab）；
  2. 在 RSUIString 代码区逐指令找对对象 +2（refcount）的读-改-写；
  3. 全 .text 扫 `jal <RSUIString 成员>` 的调用点，按调用者归组；
  4. 对每个调用点找**最内层闭合循环**（向后分支且跨度覆盖该点），报出循环上界比较；
  5. 判断调用结果是否被**存起来**（sw v0 到栈/对象/数组）——只有存活拷贝才会累加 refcount。

输出：work\builds\GR_SENT\audit\B_refcount.txt
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
AUD = os.path.join(ROOT, 'work', 'builds', 'GR_SENT', 'audit')
ELF = os.path.join(ROOT, r'third_party\orig\ps2\slus_out\SLUS_206.13')

_s = importlib.util.spec_from_file_location('cd', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)
_s2 = importlib.util.spec_from_file_location('cs', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_syms.py'))
CS = importlib.util.module_from_spec(_s2)
_s2.loader.exec_module(CS)

RS_LO, RS_HI = 0x540EA0, 0x542100          # RSUIString 代码区
RSSTR_LO, RSSTR_HI = 0x53D600, 0x53EC60    # RSString 代码区
BRANCH_OPS = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
              0x14, 0x15, 0x16, 0x17}


def syms():
    return CS.load_syms(ELF)


def owner(rng, va):
    best = None
    for (a, b, n) in rng:
        if a <= va < b and (best is None or a > best[0]):
            best = (a, b, n)
    return best[2] if best else '?'


def ins(el, va):
    w = el.word(va)
    return w, CD.dis(w, va)


def branch_target(w, va):
    op = w >> 26
    if op in BRANCH_OPS:
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        return va + 4 + simm * 4
    if op in (0x02, 0x03):                       # j / jal
        return ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
    return None


def main():
    os.makedirs(AUD, exist_ok=True)
    el = CD.Elf(ELF)
    S = syms()
    rng = sorted([(v, v + s, n) for (v, s, _i, _x, n) in S if v and s])
    out = []
    W = out.append

    W('=' * 100)
    W('B. 候选 C —— RSString u8 引用计数回卷：静态跟进（只读 ELF %s）' % os.path.relpath(ELF, ROOT))
    W('=' * 100)

    # ── 1. RSUIString / RSString 成员函数 ──
    W('')
    W('【1】RSUIString / RSString 成员函数（.symtab，size>0）')
    rs_syms, rss_syms = [], []
    for (v, s, _i, _x, n) in S:
        if not v or not s:
            continue
        if n.startswith('_') or '__' in n[:4]:
            pass
        if 'RSUIString' in n and not n.startswith('@EX@'):
            rs_syms.append((v, s, n))
        elif '8RSString' in n and 'RSStringTable' not in n and 'RSStringHash' not in n \
                and 'RSStringTokenizer' not in n and not n.startswith('@EX@'):
            rss_syms.append((v, s, n))
    for (v, s, n) in sorted(rs_syms):
        W('  0x%08X size=%4d  %s' % (v, s, n))
    W('  --- RSString（共享节点本体）---')
    for (v, s, n) in sorted(rss_syms):
        W('  0x%08X size=%4d  %s' % (v, s, n))

    # ── 2. refcount（对象 +2）读-改-写 ──
    W('')
    W('【2】对象 +2（refcount）的 读-改-写 指令（RSUIString 区 0x%X..0x%X）' % (RS_LO, RS_HI))
    rc_ops = []
    for va in range(RS_LO, RS_HI - 4, 4):
        w, txt = ins(el, va)
        op, rs, rt, imm = w >> 26, (w >> 21) & 0x1F, (w >> 16) & 0x1F, w & 0xFFFF
        if (op == 0x24 and imm == 2) or (op == 0x28 and imm == 2):      # lbu / sb
            rc_ops.append((va, txt, owner(rng, va)))
    for (va, txt, ow) in rc_ops:
        W('  0x%08X  %-34s in %s' % (va, txt, ow))
    W('  （共 %d 条；`lbu …,2(…)` = 读 refcount，`sb …,2(…)` = 写回）' % len(rc_ops))

    W('')
    W('  RSString 区里的同类指令：')
    for va in range(RSSTR_LO, RSSTR_HI - 4, 4):
        w, txt = ins(el, va)
        op, imm = w >> 26, w & 0xFFFF
        if (op == 0x24 and imm == 2) or (op == 0x28 and imm == 2):
            W('    0x%08X  %-34s in %s' % (va, txt, owner(rng, va)))

    # ── 3. 调用点普查 ──
    targets = [(v, n) for (v, s, n) in sorted(rs_syms)
               if n.startswith('Substring__10RSUIString') or
               n.startswith('__as__10RSUIString') or
               n.startswith('__ct__10RSUIString') or
               n.startswith('__dt__10RSUIString') or
               n.startswith('__pl__') or n.startswith('__apl__10RSUIString') or
               n.startswith('__vc__10RSUIString')]
    tmap = dict(targets)
    W('')
    W('【3】全 .text 里 jal 这些成员的调用点（按调用者归组）')
    va0, _off, fsz = el.text()
    calls = {v: [] for v in tmap}
    for va in range(va0, va0 + fsz - 4, 4):
        w = el.word(va)
        if (w >> 26) == 0x03:                     # jal
            tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
            if tgt in calls:
                calls[tgt].append(va)
    for v in sorted(calls):
        cs_ = calls[v]
        W('')
        W('  ▶ 0x%08X %s  —— 调用点 %d 个' % (v, tmap[v], len(cs_)))
        by = {}
        for site in cs_:
            by.setdefault(owner(rng, site), []).append(site)
        for k in sorted(by, key=lambda k: -len(by[k])):
            W('      %-58s x%d  %s' % (k[:58], len(by[k]),
                                       ' '.join('0x%X' % x for x in by[k][:14]) +
                                       (' …' if len(by[k]) > 14 else '')))

    # ── 4/5. 循环归属 + 结果是否被存起来 ──
    W('')
    W('【4】「在循环里」的调用点（紧凑表）：只列 Substring / 拷贝构造 / operator=，'
      '并给出最内层回跳分支与「返回值是否被存起来」')
    W('    列义: 目标 | 站点VA | 调用者 | 最内层循环[起..回跳] | 循环上界比较 | 返回值存档')
    W('')
    rows = []
    for v in sorted(calls):
        if not (tmap[v].startswith('Substring') or tmap[v].startswith('__ct__10RSUIStringFRC')
                or tmap[v].startswith('__as__10RSUIString')):
            continue
        for site in calls[v]:
            loop_br, loop_tgt = None, None
            for cand in range(site, min(site + 4096, va0 + fsz - 4), 4):
                w = el.word(cand)
                if (w >> 26) in BRANCH_OPS:
                    t = branch_target(w, cand)
                    if t is not None and t < cand and t <= site:
                        loop_br, loop_tgt = cand, t
                        break
            if loop_br is None:
                continue
            # 循环上界比较：回跳前 12 条里的 slt/slti/sltu + 分支
            bound = ''
            for k in range(max(loop_tgt, loop_br - 44), loop_br + 4, 4):
                w, txt = ins(el, k)
                if (w >> 26) in (0x0A, 0x0B, 0x2A, 0x2B) or txt.startswith('slt'):
                    bound = '0x%X %s' % (k, txt)
            stored = []
            for k in range(site + 4, site + 4 + 28, 4):
                w, txt = ins(el, k)
                if (w >> 26) == 0x2B and ((w >> 16) & 0x1F) == 2:
                    stored.append('0x%X' % k)
            rows.append((tmap[v], site, owner(rng, site), loop_tgt, loop_br, bound,
                         ','.join(stored) or '-'))
    for r in sorted(rows, key=lambda r: (r[2], r[1])):
        W('    %-34s @0x%08X %-46s [0x%X..0x%X] %-40s %s'
          % (r[0][:34], r[1], r[2][:46], r[3], r[4], r[5][:40], r[6]))
    W('')
    W('  循环内的 Substring/拷贝/赋值 调用点共 %d 个（其中返回值被 `sw $v0` 存起来的见上表末列）'
      % len(rows))

    # ── 5. 重点函数的全文（含 RSUIString 调用点标注）──
    WL = [(0x21CC10, 0x21D2A0, 'DoWordWrap__15RSTextComponent'),
          (0x2ECDA0, 0x2ECF00, 'GetUISoldierAbbreviateName__Fii'),
          (0x307090, 0x307170, 'GetActorNameAbbreviated__9ActorFileCFv'),
          (0x21C600, 0x21CC10, 'RSTextComponent 区（SetText/ComputeDrawXY/DrawTheString）')]
    W('')
    W('【5】重点函数全文（标注 RSUIString 调用点 ★）')
    for (lo, hi, nm) in WL:
        W('')
        W('  ── %s  0x%X..0x%X ──' % (nm, lo, hi))
        for va in range(lo, hi, 4):
            w, txt = ins(el, va)
            tag = ''
            if (w >> 26) == 0x03:
                tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                if tgt in tmap:
                    tag = '   ★ %s' % tmap[tgt]
            if tag or (va % 16 == 0):
                W('    %08X  %s%s' % (va, txt, tag))

    W('')
    W('【6】结论（口径与局限见 docs\\REPORT_SENTINEL.md §B）')
    W('  · refcount 是 u8：`lbu …,2(…)` 读、`sb …,2(…)` 写；+1 出现在拷贝构造 / Substring 结果 / operator=。')
    W('  · 只有**同时存活**的拷贝才会让计数累加不回落；因此"能否到 255"等价于'
      '"是否存在一处把 >255 个共享同一 RSString 的拷贝同时存活的代码"。')
    W('  · 本脚本给出的是调用点与循环归属的**清单与界**，不是可达性证明：'
      '要证实回卷必须实机在 RSString+2 上设**写监视**。')

    txt = '\n'.join(out) + '\n'
    with open(os.path.join(AUD, 'B_refcount.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    print(txt)
    print('[out] %s' % os.path.join(AUD, 'B_refcount.txt'))


def site_key(d, v):
    return v


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
