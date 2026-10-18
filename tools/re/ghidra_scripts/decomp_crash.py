# -*- coding: utf-8 -*-
r"""decomp_crash.py — Ghidra headless 后处理脚本 (Jython / Python 2)

目标: 反编译 recLUT 崩溃链上的函数, 认出它们是什么。
用法: analyzeHeadless <proj_dir> <proj> -import <elf> -postScript decomp_crash.py -scriptPath <this dir>
输出: 写到 work/tools/ghidra_out/ 下的文本文件 (Ghidra 脚本里用 java.io)
"""
import os
import java.io

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.symbol import SourceType

# 崩溃链上的 VA (EE 物理地址 = 程序里的 VA, 因为主段加载在 0x100000)
VAS = [
    (0x00193E90, "访问器: addiu $2,$0,-1 ... 返回 0"),
    (0x00193EA4, "lw $2,192($4) / sll / addu / lw $2,0($2)"),
    (0x00193EB4, "bne $2,$0,00193EC4"),
    (0x00193EBC, "beq $0,$0,00193ECC (命中: 查不到 ⇒ v0=0)"),
    (0x00193ECC, "jr $31"),
    (0x003F602C, "beq $2,$0,003F6038 (v0==0 成立)"),
    (0x003F6038, "lw $25,0($2)  ← $2==0, 读 RAM[0]"),
    (0x003F6044, "lw $25,792($25) ← vtable 槽 0x318"),
    (0x003F6048, "jalr $31,$25  ← 跳到 0"),
    (0x0012BD00, "读垃圾指针 0xdb770d05 / 0x74d7432f / 0xd48a4250"),
    (0x0012BD2C, "读垃圾指针 0x02020202 / 0xc"),
    (0x00101DE4, "从 0x10b2bf00 load"),
    (0x00101E6C, "store 到 0x10b2bef8"),
    (0x00102220, "反复 store 到 0x10b2bef8 (主循环)"),
    (0x001024E8, "同上另一入口"),
]

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ghidra_out')
os.makedirs(OUT_DIR, exist_ok=True)

prog = currentProgram
fm = prog.getFunctionManager()
af = prog.getAddressFactory()
listing = prog.getListing()
decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()

fout = java.io.PrintWriter(java.io.FileWriter(os.path.join(OUT_DIR, 'decomp_crash.txt')))
try:
    fout.println("program: %s" % prog.getName())
    fout.println("image base: %s" % prog.getImageBase())
    fout.println("language: %s" % prog.getLanguageID())
    fout.println("functions: %d" % fm.getFunctionCount())
    fout.println("")

    # 先列出主段里前若干函数, 便于对号
    fout.println("=== 主段函数总览 (前 40 个, 按地址) ===")
    n = 0
    it = fm.getFunctions(True)
    while it.hasNext() and n < 40:
        f = it.next()
        mn = f.getEntryPoint().getOffset()
        if 0x100000 <= mn < 0x600000:
            fout.println("  0x%08X  %-28s  size=%d" % (mn, f.getName(), f.getBody().getNumAddresses()))
            n += 1
    fout.println("")

    for va, why in VAS:
        addr = af.getDefaultAddressSpace().getAddress(va)
        fout.println("=" * 78)
        fout.println("VA 0x%08X   (%s)" % (va, why))
        f = fm.getFunctionContaining(addr)
        if f is None:
            fout.println("  (该地址不在任何已知函数内)")
        else:
            fout.println("  函数: %s   入口 0x%08X   大小 %d" % (
                f.getName(), f.getEntryPoint().getOffset(), f.getBody().getNumAddresses()))
        # 反编译
        try:
            res = decomp.decompileFunction(f if f else fm.getFunctionAt(addr), 60, monitor)
            if res is not None and res.decompileCompleted():
                fout.println("  ---- 反编译 (%s) ----" % res.getDecompiledFunction().getSignature())
                fout.println(res.getDecompiledFunction().getC())
            else:
                fout.println("  (反编译未完成: %s)" % (res.getErrorMessage() if res else 'null'))
        except Exception as e:
            fout.println("  (反编译异常: %s)" % e)
        # 该地址的原始指令窗口
        fout.println("  ---- 该地址附近 16 条指令 ----")
        a = addr
        for k in range(16):
            ins = listing.getInstructionAt(a)
            if ins is None:
                fout.println("    %s  (无语义)" % a)
            else:
                fout.println("    %s  %-28s %s" % (a, ins.toString(), ins.getFlowType()))
            a = a.add(4)
        fout.println("")
finally:
    fout.close()
    decomp.dispose()

print("decomp_crash.py done -> %s" % os.path.join(OUT_DIR, 'decomp_crash.txt'))
