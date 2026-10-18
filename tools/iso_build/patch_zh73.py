# -*- coding: utf-8 -*-
r"""patch_zh73.py — GR_ZH73 = ZH72 + 人名缩写 DBCS 化 (纯 ELF 补丁: 2 挂点 + 3 段 cave)

问题 (用户 2026-10-04 人工测试报障):
  小队/队伍状态界面里的人名显示异常 —— 训练关按 R1 调出命令面板时, 4 个队员框里的
  名字位置只剩一个孤立的 "."; 战役小队设置屏里"能显示的都是英文", 凡是已汉化的
  (ATR <ActorName> 为中文的) 人名不显示。

根因 (指令级, 见本轮报告):
  引擎有两份**同构的"缩写名"实现**, 都假设名字是 ASCII:
    A) ActorFile::GetActorNameAbbreviated  0x307090 (RSString)  — 菜单侧 34 个调用点
       (SPPlatoonScreen::SetRosterText / SPSoldierSelect / SPSoldierKit / AfterAction)
    B) GetUISoldierAbbreviateName          0x2ECDA0 (RSUIString) — 关卡内命令面板
       (CommandMapFrameModel::Draw 0x2BA754 调用)
  两者算法相同:
      tmp  = Left(name, 1)          ← 只取 **1 个字节** = 双字节汉字的孤 lead 字节
      tmp += "."
      idx  = FindChar(name, ' ')    ← 汉化时用尾随空格补齐长度 → 命中的是补位空格
      if found: tmp += Right(name, Length - idx - 1)   ← 只剩补位空格
  中文人名 (如 霍勒多明格斯 = AA B3 A9 C6 ...) 于是被折成 `AA 2E 20 20 20 20`
  = 一个渲染不出的孤 lead + "." + 若干空格 → 屏上只剩一个 "."。
  证据: drawlog F19002 PC=219A70 RA=2BA808/2BB070/2BB230/2BB40C
        | AA 2E 20 20 20 20 00 / A2 2E 20 20 00 …

修复 (零数据改动, 只改这两处显示逻辑):
  名字里出现任何 ≥0xA1 的字节 → 该名是中文, **不做 ASCII 缩写**, 直接返回
  去掉尾随空格的完整人名; 纯 ASCII 名字走原逻辑 (逐位不变, 300+ 英文 ATR 零回归)。

  实现 = 1 个共享子程序 + 2 段挂点 stub:
    helper 0x565760  (a0=chars, a1=len) → v0 = 去尾空后的长度, v1 = 1 表示含 ≥0xA1
    CaveA  0x5657C8  挂 0x3070B4 (把 Left(name,1) 之前拦下)
    CaveB  0x56583C  挂 0x2ECEC0 (同位置拦下)

  cave 落点 = 0x565760-0x5658C0 ⊂ 既有安全区 (ZH58 六转储验证 0x565670-0x5658B0 的
  延伸段): 本轮复核 **41 份 EE RAM 转储** 该区间全零 (含任务/小队/简报/开机各阶段)。

用法: python patch_zh73.py <src_iso> <dst_iso>   (基底 = work/builds/GR_ZH72)
"""
import shutil
import struct
import sys

ELF_LBA = 295
SEC_OFF, SEC_ADDR = 0x80, 0x00100000
HOOK_A, HOOK_A_ORIG = 0x3070B4, 0x27A40038      # addiu a0,sp,0x38
HOOK_B, HOOK_B_ORIG = 0x2ECEC0, 0x27A40088      # addiu a0,sp,0x88
HELPER, CAVE_A, CAVE_B = 0x565760, 0x5657C8, 0x56583C
CAVE_END = 0x5658C4
LEFT_RS, AS_RS, DTOR_RS = 0x53E2B0, 0x53E9E0, 0x53EAE0
LEFT_UI, AS_UI, DTOR_UI, LEN_UI = 0x540F30, 0x541CA0, 0x541E90, 0x53FD50
RESUME_A, RESUME_B = 0x3070BC, 0x2ECEC8        # 原 jal Left
TAIL_A, TAIL_B = 0x307140, 0x2ECF4C            # 原收尾 (result = tmp)

ZERO, AT, V0, V1, A0, A1, A2, A3 = 0, 1, 2, 3, 4, 5, 6, 7
T0, T1, T2, T3, S0, SP, RA = 8, 9, 10, 11, 16, 29, 31


def R(rs, rt, rd, sa, fn):
    return (rs << 21) | (rt << 16) | (rd << 11) | (sa << 6) | fn


def I(op, rs, rt, imm):
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def addu(rd, rs, rt):
    return R(rs, rt, rd, 0, 0x21)


def addiu(rt, rs, imm):
    return I(0x09, rs, rt, imm)


def sltiu(rt, rs, imm):
    return I(0x0B, rs, rt, imm)


def lw(rt, imm, rs):
    return I(0x23, rs, rt, imm)


def lhu(rt, imm, rs):
    return I(0x25, rs, rt, imm)


def lbu(rt, imm, rs):
    return I(0x24, rs, rt, imm)


def beq(rs, rt, off):
    return I(0x04, rs, rt, off)


def bne(rs, rt, off):
    return I(0x05, rs, rt, off)


NOP = 0
JR_RA = R(RA, 0, 0, 0, 0x08)


class Asm:
    """极简汇编器: 标签只记字索引 (不进指令流), 分支/跳转回填 + 反汇编回验。"""

    def __init__(self, base):
        self.base = base
        self.items = []          # 每项 = 指令字(int) 或 ('B', op, rs, rt, label) 或 ('J', op, target)
        self.labels = {}

    def label(self, name):
        assert name not in self.labels
        self.labels[name] = len(self.items)

    def emit(self, w):
        self.items.append(w)

    def b(self, op, rs, rt, label):
        self.items.append(('B', op, rs, rt, label))

    def j(self, op, target):
        self.items.append(('J', op, target))

    def addr_of(self, idx):
        return self.base + 4 * idx

    def assemble(self):
        out = []
        for i, it in enumerate(self.items):
            if isinstance(it, tuple):
                if it[0] == 'B':
                    _, op, rs, rt, label = it
                    tgt = self.addr_of(self.labels[label])
                    off = (tgt - (self.addr_of(i) + 4)) >> 2
                    out.append(I(op, rs, rt, off))
                else:
                    _, op, target = it
                    out.append((op << 26) | ((target >> 2) & 0x3FFFFFF))
            else:
                out.append(it)
        return out

    def verify(self):
        """反汇编回验: 每条分支/跳转的目标地址必须等于标签地址。"""
        words = self.assemble()
        assert len(words) == len(self.items)
        for i, it in enumerate(self.items):
            if not isinstance(it, tuple):
                continue
            w = words[i]
            if it[0] == 'B':
                _, op, rs, rt, label = it
                assert (w >> 26) == op, (i, hex(w))
                off = w & 0xFFFF
                off = off - 0x10000 if off & 0x8000 else off
                tgt = self.addr_of(i) + 4 + (off << 2)
                assert tgt == self.addr_of(self.labels[label]), \
                    '分支回验失败 @%08X: %08X != %08X' % (self.addr_of(i), tgt,
                                                          self.addr_of(self.labels[label]))
            else:
                _, op, target = it
                assert (w >> 26) == op, (i, hex(w))
                tgt = ((w & 0x3FFFFFF) << 2)
                assert tgt == target, '跳转回验失败 @%08X: %08X != %08X' % (self.addr_of(i), tgt, target)
        return words


def build_helper():
    a = Asm(HELPER)
    a.emit(addu(T0, A0, A1))            # end = chars + len
    a.emit(addu(T1, A0, ZERO))          # p = chars
    a.emit(addu(V1, ZERO, ZERO))        # flag = 0
    a.label('hscan')
    a.b(0x04, T1, T0, 'htrim')          # p == end → 去尾空
    a.emit(NOP)
    a.emit(lbu(T2, 0, T1))
    a.emit(sltiu(T3, T2, 0xA1))
    a.b(0x05, T3, ZERO, 'hnext')        # ASCII → 不进 flag
    a.emit(NOP)
    a.emit(addiu(V1, ZERO, 1))          # 高字节 → flag = 1
    a.label('hnext')
    a.emit(addiu(T1, T1, 1))
    a.j(0x02, a.addr_of(0))             # j hscan (回填用标签地址)
    a.items[-1] = ('J', 0x02, None)
    a.emit(NOP)
    a.label('htrim')
    a.emit(addu(V0, A1, ZERO))          # v0 = len
    a.label('htloop')
    a.b(0x04, V0, ZERO, 'hdone')
    a.emit(NOP)
    a.emit(addu(T0, A0, V0))
    a.emit(lbu(T1, -1, T0))
    a.emit(addiu(T2, ZERO, 0x20))
    a.b(0x05, T1, T2, 'hdone')
    a.emit(NOP)
    a.emit(addiu(V0, V0, -1))
    a.j(0x02, a.addr_of(0))
    a.items[-1] = ('J', 0x02, None)
    a.emit(NOP)
    a.label('hdone')
    a.emit(JR_RA)
    a.emit(NOP)
    # 回填两个自跳转 (目标 = hscan / htloop 标签地址)
    idx = 0
    for i, it in enumerate(a.items):
        if isinstance(it, tuple) and it[0] == 'J' and it[2] is None:
            tgt = a.addr_of(a.labels['hscan'] if idx == 0 else a.labels['htloop'])
            a.items[i] = ('J', 0x02, tgt)
            idx += 1
    assert idx == 2
    return a


def build_cave_a():
    a = Asm(CAVE_A)
    a.emit(lw(T0, 0x48, 16))            # t0 = name.impl   (RSString@ActorFile+0x44)
    a.b(0x04, T0, ZERO, 'asciiA')
    a.emit(NOP)
    a.emit(lw(A0, 4, T0))               # a0 = chars
    a.b(0x04, A0, ZERO, 'asciiA')
    a.emit(NOP)
    a.emit(lhu(A1, 2, T0))              # a1 = len
    a.j(0x03, HELPER)
    a.emit(NOP)
    a.b(0x04, V1, ZERO, 'asciiA')       # 纯 ASCII → 原逻辑
    a.emit(NOP)
    a.emit(addiu(A0, SP, 0x38))         # Left(dst = 生缓冲 sp+0x38)
    a.emit(addiu(A1, S0, 0x44))         # src = &name (s0)
    a.j(0x03, LEFT_RS)
    a.emit(addu(A2, V0, ZERO))          # 延迟槽: a2 = 去尾空长度
    a.emit(addiu(A0, SP, 0x30))         # tmp = left
    a.emit(addiu(A1, SP, 0x38))
    a.j(0x03, AS_RS)
    a.emit(NOP)
    a.emit(addiu(A0, SP, 0x38))         # dtor(left)
    a.j(0x03, DTOR_RS)
    a.emit(addiu(A1, ZERO, -1))
    a.j(0x02, TAIL_A)
    a.emit(NOP)
    a.label('asciiA')
    a.emit(addiu(A0, SP, 0x38))
    a.emit(addiu(A1, S0, 0x44))
    a.emit(addiu(A2, ZERO, 1))
    a.j(0x02, RESUME_A)
    a.emit(NOP)
    return a


def build_cave_b():
    a = Asm(CAVE_B)
    a.emit(lw(T0, 0x74, SP))            # t0 = tmp.impl    (RSUIString@sp+0x70)
    a.b(0x04, T0, ZERO, 'asciiB')
    a.emit(NOP)
    a.emit(lw(T1, 4, T0))               # t1 = chars
    a.b(0x04, T1, ZERO, 'asciiB')
    a.emit(NOP)
    a.emit(addiu(A0, SP, 0x70))
    a.j(0x03, LEN_UI)                   # v0 = Length(tmp)   (RSUIString 无长度字段, 取 strlen)
    a.emit(NOP)
    a.emit(lw(T0, 0x74, SP))            # 重新取 (Length/strlen 是 caller-saved t 寄存器的破坏者)
    a.emit(lw(A0, 4, T0))               # a0 = chars
    a.emit(addu(A1, V0, ZERO))          # a1 = len
    a.j(0x03, HELPER)
    a.emit(NOP)
    a.b(0x04, V1, ZERO, 'asciiB')
    a.emit(NOP)
    a.emit(addiu(A0, SP, 0x88))         # Left(dst = 生缓冲 sp+0x88)
    a.emit(addiu(A1, SP, 0x70))
    a.j(0x03, LEFT_UI)
    a.emit(addu(A2, V0, ZERO))          # 延迟槽: a2 = 去尾空长度
    a.emit(addiu(A0, SP, 0x78))         # left = raw
    a.emit(addiu(A1, SP, 0x88))
    a.j(0x03, AS_UI)
    a.emit(NOP)
    a.emit(addiu(A0, SP, 0x88))         # dtor(raw)
    a.j(0x03, DTOR_UI)
    a.emit(addiu(A1, ZERO, -1))
    a.j(0x02, TAIL_B)
    a.emit(NOP)
    a.label('asciiB')
    a.emit(addiu(A0, SP, 0x88))
    a.emit(addiu(A1, SP, 0x70))
    a.emit(addiu(A2, ZERO, 1))
    a.j(0x02, RESUME_B)
    a.emit(NOP)
    return a


def main(src, dst):
    asms = [('helper', build_helper()), ('caveA', build_cave_a()), ('caveB', build_cave_b())]
    blocks = []
    for name, a in asms:
        w = a.verify()
        blocks.append((name, a.base, w))
    span = struct.pack('<I', (0x02 << 26) | ((CAVE_A >> 2) & 0x3FFFFFF))
    span_b = struct.pack('<I', (0x02 << 26) | ((CAVE_B >> 2) & 0x3FFFFFF))

    shutil.copyfile(src, dst)
    base = ELF_LBA * 2048
    with open(dst, 'r+b') as f:
        f.seek(base)
        assert f.read(4) == b'\x7fELF', 'ELF 魔数错位'
        f.seek(base + 0x1C)
        phoff = struct.unpack('<I', f.read(4))[0]
        f.seek(base + phoff)
        assert struct.unpack('<III', f.read(12)) == (1, SEC_OFF, SEC_ADDR), 'phdr0 不符'

        def off(va):
            return base + SEC_OFF + (va - SEC_ADDR)

        # 1) 挂点原值断言 + 写入
        for va, orig, new, tag in ((HOOK_A, HOOK_A_ORIG, span, 'A/RSString 0x3070B4'),
                                   (HOOK_B, HOOK_B_ORIG, span_b, 'B/RSUIString 0x2ECEC0')):
            f.seek(off(va))
            cur = struct.unpack('<I', f.read(4))[0]
            assert cur == orig, '%s 原值 0x%08X != 0x%08X' % (tag, cur, orig)
            f.seek(off(va))
            f.write(new)
            w = struct.unpack('<I', new)[0]
            print('[hook] %s → j 0x%06X' % (tag, ((w & 0x3FFFFFF) << 2)))

        # 2) cave 区必须全零 (原样) 后写入
        f.seek(off(HELPER))
        old = f.read(CAVE_END - HELPER)
        assert len(old) == CAVE_END - HELPER and set(old) == {0}, 'cave 区非零 (基底不符)'
        for name, base_va, words in blocks:
            f.seek(off(base_va))
            f.write(b''.join(struct.pack('<I', w) for w in words))
            print('[cave] %-6s @0x%06X %d 词 (%dB)' % (name, base_va, len(words), 4 * len(words)))

        # 3) 回读 + 反汇编回验
        for name, base_va, words in blocks:
            f.seek(off(base_va))
            back = list(struct.unpack('<%dI' % len(words), f.read(4 * len(words))))
            assert back == words, '%s 回读不符' % name
        for va, want in ((HOOK_A, span), (HOOK_B, span_b)):
            f.seek(off(va))
            assert f.read(4) == want

    # 4) 全盘差异白名单: 两个挂点 + cave 段
    win = [(off(HOOK_A), 4), (off(HOOK_B), 4), (off(HELPER), CAVE_END - HELPER)]
    a, b = open(src, 'rb'), open(dst, 'rb')
    pos, bad, words = 0, [], set()
    while True:
        ca, cb = a.read(1 << 20), b.read(1 << 20)
        if not ca:
            break
        for i in range(len(ca)):
            if ca[i] != cb[i]:
                p = pos + i
                words.add(p & ~3)
                if not any(o <= p < o + l for o, l in win):
                    bad.append(p)
        pos += len(ca)
    a.close()
    b.close()
    assert not bad, '窗口外差异: ' + repr([hex(x) for x in bad[:6]])
    print('[diff] 差异词 %d 个, 全部位于 2 挂点 + cave 段 ✓' % len(words))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
