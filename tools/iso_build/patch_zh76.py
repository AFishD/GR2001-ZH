# -*- coding: utf-8 -*-
r"""patch_zh76.py — GR_ZH76 = ZH75 + 命令面板中文人名下移 2.5px (纯 ELF 补丁: 1 挂点 + 1 cave)

问题 (用户 2026-10-04 实测, 承接 ZH73 人名缩写轮):
  ZH73 把命令面板/小队名单的人名从"一个点"恢复成中文全名后, 用户指出**位置偏上**:
  同一队员框里, 原版英文名字块靠下 (为 g/y/p 等降部留白), 中文四字整块填满字格、墨自
  笔位 +0 起画 → 视觉上整体上抬, 上沿几乎贴住框线。

定量 (gsrunner 同 nav 同帧, GR_EN_ORIG vs GR_ZH75, 名字条逐行墨统计 tools/diag/ 同款方法):
  高亮框 (H. Dominguez / 霍勒多明格斯): EN 墨带 y129.1-143.4 质心 135.90;
                                        ZH 墨带 y126.0-140.4 质心 132.52 → **高 3.38px**
  右侧框 (G. Maxwell / 加纳马克斯威):   EN 墨带 y128.1-141.4 质心 135.91;
                                        ZH 墨带 y126.0-140.4 质心 133.45 → **高 2.46px**
  框内区 ≈ y126-144.5 (中心 135.25): EN 质心基本落中心, ZH 偏高 2-3px → 与用户观感一致。
  (注: ZH72 时框内画的是 "." 低位点号, 故当时看不出; ZH73 恢复全名后才暴露。)

根因: 命令面板 (CommandMapFrameModel::Draw 0x2B8300, 长 12736) 的人名**不走**菜单文字组件链
  (IkeBaseButton 的 CJK 居中补偿 0x21D940 K=21 覆盖不到它), 而是自己算好 f12/f13 直调
  DrawString v1 (0x219A70) —— 与 ZH74 修的 HUD 指示条同一性质 (任务内专用绘制链, 沿用
  英文版基线口径)。所以中文需要该路径自己的 CJK 补偿。

修复 (纯 ELF; 1 挂点 + 31 词 cave, 零寄存器泄漏; 仅对"本函数内且串含 ≥0xA1"的绘制生效):
  挂点 **0x219A74** (`sd ra,0xA0(sp)` = DrawString v1 序言第 2 条) → j cave(0x565930):
    - RA 落在 [0x2B8300, 0x2B8300+0x31C0) = 命令面板函数体内? (无符号减 + sltiu 一次判完)
    - 串内出现 ≥0xA1 字节 (中文名)? 否则原样放行;
    - 命中 → f13 += K;
    - 收尾: 补执行被顶掉的 `sd ra,0xa0(sp)`, 再回 0x219a7c。
  **K 的标定 (两枚实测盘)**: K=2.5f → 墨带 +1.3px; K=7.5f → +5.6px;
  即渲染增益 ≈0.86 (K 与最终墨迹位移非 1:1, 故不能直接取差值)。
  目标 = 与英文墨心对齐 (高亮框 Δ 3.05px / 右框 Δ 2.95px) → K = 4.5f (0x40900000)。
  **为何钩第 2 条而非函数首条 (延迟槽教训)**: `j` 的延迟槽(下一条指令)先于 cave 执行。
  若钩 0x219A70 (`addiu sp,sp,-224`), 延迟槽 0x219A74 的 `sd ra,0xA0(sp)` 会在 **sp 尚未下移**
  时写进调用方栈 → 栈损坏 → 开机后卡在档案屏 (首版实测: 第 2 个采样点起快照完全冻结,
  绘制日志仅 108k 行, 正确盘同期 314k 行)。改钩 0x219A74 后, 延迟槽 0x219A78 (`sq fp,0x90(sp)`)
  在 sp 已正确下移后执行且幂等, cave 再补回存 ra 并跳过 0x219A78 → 序言语义逐条不变。
  纯 ASCII 名字 (300+ 未译 ATR) 逐位不变 → 英文零回归; 弹药数字 26/- 30/- 1/5 等同函数内的
  ASCII 绘制不受影响 (RA 在范围内但串无高字节)。K=2.5 与 ZH74 HUD 指示条同口径。

cave 落点 0x565930-0x565984 ⊂ 0x565930-0x565C00 恒零区: **73 份 EE RAM 转储**
  (开机/菜单/小队/任务/简报各阶段) 该区间全零 (ZH73 用的 0x565760-0x5658C4 已占, 故下移)。

用法: python patch_zh76.py <src_iso> <dst_iso>   (基底 = GR_ZH75)
"""
import shutil
import struct
import sys

ELF_LBA = 295
SEC_OFF, SEC_ADDR = 0x80, 0x00100000
HOOK, HOOK_ORIG = 0x219A74, 0xFFBF00A0       # sd ra, 0xA0(sp)  (序言第 2 条; 首条延迟槽教训见上)
RESUME = 0x219A7C
CAVE = 0x565930
CAVE_END = CAVE + 31 * 4
FUNC, FUNC_SIZE = 0x2B8300, 0x31C0           # CommandMapFrameModel::Draw
K_FLOAT = 0x40900000                         # 4.5f (标定: 渲染增益 ≈0.86; 见下"标定"注)

ZERO, AT, V0, V1, A0, A1, A2, T0, T1, T2, SP, RA = 0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 29, 31


def R(rs, rt, rd, sa, fn):
    return (rs << 21) | (rt << 16) | (rd << 11) | (sa << 6) | fn


def I(op, rs, rt, imm):
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def lui(rt, imm):
    return I(0x0F, 0, rt, imm)


def addiu(rt, rs, imm):
    return I(0x09, rs, rt, imm)


def sltiu(rt, rs, imm):
    return I(0x0B, rs, rt, imm)


def subu(rd, rs, rt):
    return R(rs, rt, rd, 0, 0x23)


def addu(rd, rs, rt):
    return R(rs, rt, rd, 0, 0x21)


def lbu(rt, imm, rs):
    return I(0x24, rs, rt, imm)


NOP = 0


class Asm:
    def __init__(self, base):
        self.base = base
        self.items = []
        self.labels = {}

    def label(self, n):
        self.labels[n] = len(self.items)

    def emit(self, w):
        self.items.append(w)

    def b(self, op, rs, rt, label):
        self.items.append(('B', op, rs, rt, label))

    def j(self, op, target):
        self.items.append(('J', op, target))

    def addr(self, i):
        return self.base + 4 * i

    def assemble(self):
        out = []
        for i, it in enumerate(self.items):
            if isinstance(it, tuple):
                if it[0] == 'B':
                    _, op, rs, rt, lab = it
                    off = (self.addr(self.labels[lab]) - (self.addr(i) + 4)) >> 2
                    out.append(I(op, rs, rt, off))
                else:
                    _, op, tgt = it
                    out.append((op << 26) | ((tgt >> 2) & 0x3FFFFFF))
            else:
                out.append(it)
        return out

    def verify(self):
        words = self.assemble()
        for i, it in enumerate(self.items):
            if not isinstance(it, tuple):
                continue
            w = words[i]
            if it[0] == 'B':
                _, op, rs, rt, lab = it
                assert (w >> 26) == op
                off = w & 0xFFFF
                off = off - 0x10000 if off & 0x8000 else off
                assert self.addr(i) + 4 + (off << 2) == self.addr(self.labels[lab]), \
                    '分支回验失败 @%08X' % self.addr(i)
            else:
                _, op, tgt = it
                assert (w >> 26) == op and ((w & 0x3FFFFFF) << 2) == tgt, \
                    '跳转回验失败 @%08X' % self.addr(i)
        return words


def cop1(fmt, ft, fs, fd, fn):
    """COP1: op=0x11 | fmt | ft | fs | fd | fn"""
    return (0x11 << 26) | (fmt << 21) | (ft << 16) | (fs << 11) | (fd << 6) | fn


def mtc1(rt, fs):
    return cop1(0x04, rt, fs, 0, 0)          # fmt=W


def add_s(fd, fs, ft):
    return cop1(0x10, ft, fs, fd, 0)         # fmt=S, fn=add


def build_cave():
    """零寄存器泄漏版: 本引擎违反常规 ABI (调用方在 t0/v0 带活数据调 v1 —— 见探针 B 实证,
    clobber 它们会让菜单文字变色), 故所有触碰的寄存器先存到"序言稍后必然覆写的栈槽"
    (sp+0x10-0x1F: hook 之后 0x219A98 的 sq s0,0x10(sp) 会整槽重写), 用完恢复。"""
    a = Asm(CAVE)
    a.emit(I(0x2B, SP, T0, 0x10))                        # sw  t0,0x10(sp)  (s0 槽, 稍后被 sq 覆写)
    a.emit(I(0x2B, SP, T1, 0x14))                        # sw  t1,0x14(sp)
    a.emit(I(0x2B, SP, T2, 0x18))                        # sw  t2,0x18(sp)
    a.emit(I(0x2B, SP, V0, 0x1C))                        # sw  v0,0x1C(sp)
    a.emit(lui(T0, ((FUNC + 0x8000) >> 16) & 0xFFFF))    # 标准 lui/addiu: (addr+0x8000)>>16
    a.emit(addiu(T0, T0, FUNC & 0xFFFF))                 # → 0x2C0000 - 32000 = 0x2B8300 (函数起)
    a.emit(subu(T0, RA, T0))                             # d = ra - start (ra<start → 回绕成大数)
    a.emit(sltiu(V0, T0, FUNC_SIZE))                     # d < 函数长?
    a.b(0x04, V0, ZERO, 'done')
    a.emit(NOP)
    a.emit(addu(T1, A1, ZERO))                           # p = 串
    a.label('scan')
    a.emit(lbu(T2, 0, T1))
    a.b(0x04, T2, ZERO, 'done')                          # 串尾 → 纯 ASCII
    a.emit(NOP)
    a.emit(sltiu(V0, T2, 0xA1))
    a.b(0x04, V0, ZERO, 'hit')                           # ≥0xA1 → 中文名
    a.emit(addiu(T1, T1, 1))
    a.j(0x02, CAVE)                                      # 占位, 末尾回填 j scan
    a.items[-1] = ('J', 0x02, None)
    a.emit(NOP)
    a.label('hit')
    a.emit((0x39 << 26) | (29 << 21) | (0 << 16) | 0x20)  # swc1 f0,0x20(sp) (s1 槽, 稍后被 sq 覆写)
    a.emit(lui(T0, K_FLOAT >> 16))
    a.emit(mtc1(T0, 0))                                  # f0 = K
    a.emit(add_s(13, 13, 0))                             # f13 += f0  (唯一故意修改)
    a.emit((0x31 << 26) | (29 << 21) | (0 << 16) | 0x20)  # lwc1 f0,0x20(sp)
    a.label('done')
    a.emit(I(0x23, SP, T0, 0x10))                        # lw  t0,0x10(sp)  (rs=sp, rt=t0)
    a.emit(I(0x23, SP, T1, 0x14))                        # lw  t1,0x14(sp)
    a.emit(I(0x23, SP, T2, 0x18))                        # lw  t2,0x18(sp)
    a.emit(I(0x23, SP, V0, 0x1C))                        # lw  v0,0x1C(sp)
    a.emit(I(0x3F, SP, RA, 0xA0))                        # 补执行被顶掉的 sd ra,0xA0(sp) (SP 已下移)
    a.j(0x02, RESUME)                                    # 回 0x219A7C (0x219A78 已作延迟槽执行且幂等)
    a.emit(NOP)
    # 回填 j scan
    for i, it in enumerate(a.items):
        if isinstance(it, tuple) and it[0] == 'J' and it[2] is None:
            a.items[i] = ('J', 0x02, a.addr(a.labels['scan']))
    return a


def word_of_fmt(fmt, ft, fs, fd, fn):
    """COP1 fmt 型编码: op=0x11, fmt<<21, ft<<16, fs<<11, fd<<6, fn"""
    return (0x11 << 26) | (fmt << 21) | (ft << 16) | (fs << 11) | (fd << 6) | fn


def main(src, dst):
    a = build_cave()
    words = a.verify()
    assert len(words) == 31, len(words)
    span = struct.pack('<I', (0x02 << 26) | ((CAVE >> 2) & 0x3FFFFFF))
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

        f.seek(off(HOOK))
        cur = struct.unpack('<I', f.read(4))[0]
        assert cur == HOOK_ORIG, '挂点原值 %08X != %08X' % (cur, HOOK_ORIG)
        f.seek(off(CAVE))
        old = f.read(CAVE_END - CAVE)
        assert len(old) == CAVE_END - CAVE and set(old) == {0}, 'cave 区非零'
        f.seek(off(HOOK))
        f.write(span)
        f.seek(off(CAVE))
        f.write(b''.join(struct.pack('<I', w) for w in words))
        f.seek(off(CAVE))
        assert list(struct.unpack('<%dI' % len(words), f.read(4 * len(words)))) == words
        f.seek(off(HOOK))
        assert f.read(4) == span
        print('[elf] DrawString 序言挂点 0x%06X → j 0x%06X; cave 31 词零泄漏 (K=4.5f)' % (HOOK, CAVE))

    win = [(off(HOOK), 4), (off(CAVE), CAVE_END - CAVE)]
    x, y = open(src, 'rb'), open(dst, 'rb')
    pos, bad, n = 0, [], 0
    while True:
        ca, cb = x.read(1 << 20), y.read(1 << 20)
        if not ca:
            break
        for i in range(len(ca)):
            if ca[i] != cb[i]:
                p = pos + i
                n += 1
                if not any(o <= p < o + l for o, l in win):
                    bad.append(p)
        pos += len(ca)
    x.close()
    y.close()
    assert not bad, '窗口外差异: ' + repr([hex(v) for v in bad[:6]])
    print('[diff] 差异 %d B, 全部位于 1 挂点 + cave 段 ✓' % n)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
