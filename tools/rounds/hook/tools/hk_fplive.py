# -*- coding: utf-8 -*-
r"""hk_fplive.py — 「DrawString 调用后仍在使用 $fp(=s8) 的值」的线性可达性扫描.

方法 (线性过近似, 不计控制流):
  * 对每个 DrawString(0x219A70) / 包装器(0x219EB0) 的调用者, 取其所在符号区间;
  * 线性扫一遍, 维护状态:
      LIVE  : $30 的值来自本次调用的赋值/保存 (可安全跨调用)
      DIRTY : 自最近一次"写 $30"之后发生过 jal/jalr ⇒ 此刻 $30 的值可能已被被调者破坏
  * 任一读 $30 (以 $30 为基址 / 源寄存器 / 分支条件) 发生在 DIRTY 状态 ⇒ 报为"受害者读点"。
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hk_lib as H     # noqa: E402

ZH = H.elf('ZH')

R = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3',
     't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
     's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7',
     't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']

# 读 rs 的 opcode (内存访问 / ALUI / 分支 / SPECIAL 三寄存器)
MEM = {0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x1E, 0x37, 0x28, 0x29, 0x2A,
       0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x1F, 0x3F, 0x31, 0x35, 0x39, 0x3D}
ALUI = {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F}
BR = {0x01, 0x04, 0x05, 0x06, 0x07}
# 写 rt 的 opcode
WRT = MEM | ALUI | {0x32, 0x36, 0x3A, 0x3E, 0x30, 0x34, 0x38, 0x3C}
THREE = {0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2A, 0x2B, 0x2C, 0x2D,
         0x2E, 0x2F}
SHIFT = {0x00, 0x02, 0x03, 0x04, 0x06, 0x07}
JUMPREG = {0x08, 0x09}


def scan(f, e):
    """线性扫描 [f,e), 返回 [(va, dis, lastdraw)]。

    判据 (只认 DrawString 造成的污染):
      corrupt = True  ⇔  自最近一次"写 $30"以来发生过对 0x219A70 / 0x219EB0 的调用
                         (被调者在本盘上会把 $fp 恢复成未初始化的 sp+144)
      其它被调者按 ABI 保存 $fp, 不改 corrupt。
    """
    corrupt = False
    lastdraw = None
    out = []
    for va in range(f, e, 4):
        o = va - H.VA2FILE
        if o < 0 or o + 4 > len(ZH.b):
            break
        w = struct.unpack_from('<I', ZH.b, o)[0]
        op = w >> 26
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        rd = (w >> 11) & 0x1F
        funct = w & 0x3F
        reads_fp = False
        writes_fp = False
        if op in MEM:
            # 存储类 (0x28..0x2F,0x1F,0x3F,0x39,0x3D) 把 rt 的**值**写出去 = 读 fp
            is_store = op in (0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F,
                              0x1F, 0x3F, 0x39, 0x3D)
            reads_fp = (rs == 30) or (is_store and rt == 30)
            writes_fp = (rt == 30) and not is_store
        elif op in ALUI:
            reads_fp = (rs == 30)
            writes_fp = (rt == 30)
        elif op in BR:
            reads_fp = (rs == 30) or (rt == 30 and op == 4)
        elif op == 0:
            if funct in THREE:
                reads_fp = (rs == 30) or (rt == 30)
                writes_fp = (rd == 30)
            elif funct in SHIFT:
                reads_fp = (rt == 30)
                writes_fp = (rd == 30)
            elif funct == 0x08:
                reads_fp = (rs == 30)
            elif funct == 0x09:
                reads_fp = (rs == 30)
                writes_fp = (rd == 30)
            elif funct in (0x10, 0x12):
                writes_fp = (rd == 30)
            elif funct in (0x11, 0x13):
                reads_fp = (rs == 30)
        elif op in (0x1C, 0x1D):
            if funct in (0x28, 0x2C, 0x2D, 0x2E, 0x2F) or 0x20 <= funct <= 0x27:
                reads_fp = (rs == 30) or (rt == 30)
                writes_fp = (rd == 30)
            elif funct in (0x10, 0x12):
                writes_fp = (rd == 30)
            elif funct in (0x11, 0x13):
                reads_fp = (rs == 30)
        if reads_fp and corrupt:
            out.append((va, H.dis1(w, va), lastdraw))
        if writes_fp:
            corrupt = False
            lastdraw = None
        elif op == 3 or (op == 0 and funct == 0x09):
            # jal 目标已知才判定; jalr 目标不可知 ⇒ 不置位 (记为未达成)
            if op == 3:
                tgt = ((w & 0x3FFFFFF) << 2) | (va & 0xF0000000)
                if tgt in (0x219A70, 0x219EB0):
                    corrupt = True
                    lastdraw = tgt
    return out


def main():
    # 收集调用者
    calls = []
    for a in range(0x100000, 0x5DED00, 4):
        o = a - H.VA2FILE
        w = struct.unpack_from('<I', ZH.b, o)[0]
        if (w >> 26) in (2, 3):
            tgt = ((w & 0x3FFFFFF) << 2) | (a & 0xF0000000)
            if tgt in (0x219A70, 0x219EB0):
                calls.append((a, tgt))
    seen = {}
    for (a, t) in calls:
        s = ZH.sym_at(a)
        if not s:
            continue
        key = (s['name'], s['value'], s['size'])
        seen.setdefault(key, []).append(a)
    L = []
    L.append('# DrawString 调用者的 $fp 存活分析')
    L.append('')
    L.append('判据: `corrupt = True` ⇔ 自最近一次"写 $30"以来调用过 `DrawString`(0x219A70) 或')
    L.append('其包装器(0x219EB0) —— 本盘上这两个入口会把 `$fp` 恢复成**本次调用从未初始化过的 sp+144**,')
    L.append('因此返回后 `$fp` 已不是调用者保存的值。此后**任何读 $fp** 都是受害者读点。')
    L.append('')
    L.append('局限(未达成): ① `jalr`(虚调用) 目标不可知, 不置位; ② 只做函数内线性可达, 未做 CFG/数据流;')
    L.append('③ 只扫"直接调用 DrawString/包装器"的调用者。')
    L.append('')
    L.append('调用者符号数 = %d ; 调用点 = %d' % (len(seen), len(calls)))
    L.append('')
    L.append('| 符号 | 帧范围 | DrawString 调用点 | corrupt 状态下的 $fp 读点 | 判定 |')
    L.append('|---|---|---|---|---|')
    nvic = 0
    for key in sorted(seen, key=lambda k: k[1]):
        nm, v, sz = key
        bad = scan(v, v + sz)
        if bad:
            nvic += 1
        L.append('| `%s` | 0x%X..0x%X | %s | %s | %s |'
                 % (nm.split('__')[0], v, v + sz,
                    ', '.join('0x%X' % x for x in seen[key]),
                    ' ; '.join('`0x%X %s`' % (x[0], x[1]) for x in bad) or '无',
                    '★ **受害**' if bad else 'OK'))
    L.append('')
    L.append('⇒ 受害候选(调用后仍读 $fp) = **%d** 个符号' % nvic)
    txt = '\n'.join(L)
    with io.open(os.path.join(H.EVID, 'hk_fplive.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print('wrote hk_fplive.md : 调用者符号 %d, 受害候选 %d' % (len(seen), nvic))
    for key in sorted(seen, key=lambda k: k[1]):
        nm, v, sz = key
        bad = scan(v, v + sz)
        if bad:
            print('  ★ %-34s 0x%X..0x%X  读点: %s'
                  % (nm.split('__')[0], v, v + sz,
                     ', '.join('0x%X %s' % (x[0], x[1]) for x in bad)))


if __name__ == '__main__':
    main()
