# -*- coding: utf-8 -*-
r"""pygh_decomp.py — 用 PyGhidra 打开已分析好的项目, 反编译 recLUT 崩溃链上的函数

不重跑分析: 直接 openProject(ghidra_proj/GRLoc) 里的 SLUS_206.13.elf。
环境重定向写在脚本开头(必须在 import pyghidra 之前), 保证配置/临时目录都落在工作区内。
输出: work/tools/ghidra_out/decomp_crash.txt
"""
import io
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TOOLS = os.path.join(REPO, 'work', 'tools')

# ---- 环境重定向: 必须在 import pyghidra 之前 ----
os.environ['GHIDRA_INSTALL_DIR'] = os.path.join(TOOLS, 'ghidra')
os.environ['JAVA_HOME'] = os.path.join(TOOLS, 'jdk')
os.environ['APPDATA'] = os.path.join(TOOLS, 'appdata')
os.environ['LOCALAPPDATA'] = os.path.join(TOOLS, 'appdata')
os.environ['USERPROFILE'] = os.path.join(TOOLS, 'home')
os.environ['TEMP'] = os.path.join(TOOLS, 'temp')
os.environ['TMP'] = os.path.join(TOOLS, 'temp')
os.environ['PATH'] = os.path.join(TOOLS, 'jdk', 'bin') + os.pathsep + os.environ.get('PATH', '')
for d in ('appdata', 'home', 'temp'):
    os.makedirs(os.path.join(TOOLS, d), exist_ok=True)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyghidra  # noqa: E402
from pyghidra.launcher import HeadlessPyGhidraLauncher  # noqa: E402

# 用 HeadlessPyGhidraLauncher（pyghidra.start() 在本机会 RecursionError）
_l = HeadlessPyGhidraLauncher()
_l.start()

from ghidra.base.project import GhidraProject                      # noqa: E402
from ghidra.app.decompiler import DecompInterface                  # noqa: E402
from ghidra.util.task import ConsoleTaskMonitor                    # noqa: E402

PROJ_DIR = os.path.join(TOOLS, 'ghidra_proj')
PROJ_NAME = 'GRLoc'
OUT = os.path.join(TOOLS, 'ghidra_out', 'decomp_crash.txt')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

VAS = [
    (0x00193E90, '访问器: 查表查不到时如实返回 0'),
    (0x00193EA4, 'lw $2,192($4) / sll / addu / lw $2,0($2)'),
    (0x00193EBC, 'beq $0,$0,00193ECC (命中: 返回 0)'),
    (0x00193ECC, 'jr $31'),
    (0x003F5FD0, '虚函数入口 (开火后 5 帧进入)'),
    (0x003F602C, 'beq $2,$0,003F6038 (v0==0 成立)'),
    (0x003F6038, '★ lw $25,0($2)  -- 不判空就解引用'),
    (0x003F6044, 'lw $25,792($25) -- 虚表槽 0x318'),
    (0x003F6048, '★ jalr $31,$25 -- 跳到 0'),
    (0x0012BD00, '读垃圾指针 0xdb770d05 / 0x74d7432f / 0xd48a4250'),
    (0x0012BD2C, '读垃圾指针 0x02020202 / 0xc'),
    (0x00101DE4, '从 0x10b2bf00 load'),
    (0x00101E6C, 'store 到 0x10b2bef8'),
    (0x00102220, '反复 store 到 0x10b2bef8 (主循环)'),
    (0x000728C20 if False else 0x728C20, '被查表的对象 (运行时地址, ELF 里未必有)'),
]

fout = io.open(OUT, 'w', encoding='utf-8')
fout.write('project: %s / %s\n' % (PROJ_DIR, PROJ_NAME))
fout.write('\n')

proj = GhidraProject.openProject(PROJ_DIR, PROJ_NAME, True)   # read-only
try:
    files = [f.getPathname() for f in proj.getRootFolder().getFiles()]
    fout.write('project files: %s\n' % files)
    prog = proj.openProgram('/', 'SLUS_206.13.elf', True)
    try:
        fout.write('program: %s\n' % prog.getName())
        fout.write('image base: %s\n' % prog.getImageBase())
        fout.write('language: %s\n' % prog.getLanguageID())
        fm = prog.getFunctionManager()
        fout.write('function count: %d\n' % fm.getFunctionCount())
        fout.write('\n')

        # 主段函数总览 (前 60 个)
        fout.write('=== 主段函数总览 (0x100000..0x600000, 前 60) ===\n')
        n = 0
        it = fm.getFunctions(True)
        while it.hasNext() and n < 60:
            f = it.next()
            a = f.getEntryPoint().getOffset()
            if 0x100000 <= a < 0x600000:
                fout.write('  0x%08X  %-30s size=%d\n' % (a, f.getName(), f.getBody().getNumAddresses()))
                n += 1
        fout.write('\n')

        dec = DecompInterface()
        dec.openProgram(prog)
        mon = ConsoleTaskMonitor()
        af = prog.getAddressFactory()

        for va, why in VAS:
            addr = af.getDefaultAddressSpace().getAddress(va)
            fout.write('=' * 78 + '\n')
            fout.write('VA 0x%08X   (%s)\n' % (va, why))
            f = fm.getFunctionContaining(addr)
            if f is None:
                fout.write('  (不在任何已知函数内)\n')
            else:
                fout.write('  函数 %s  入口 0x%08X  大小 %d  调用者 %d\n' % (
                    f.getName(), f.getEntryPoint().getOffset(),
                    f.getBody().getNumAddresses(), f.getCallingFunctions(mon).size()))
                for cf in f.getCallingFunctions(mon):
                    fout.write('      <= 被 0x%08X %s 调用\n' % (cf.getEntryPoint().getOffset(), cf.getName()))
            if f is not None:
                try:
                    res = dec.decompileFunction(f, 90, mon)
                    if res is not None and res.decompileCompleted():
                        df = res.getDecompiledFunction()
                        fout.write('  ---- 反编译 (%s) ----\n' % df.getSignature())
                        fout.write(df.getC())
                        fout.write('\n')
                    else:
                        fout.write('  (反编译未完成: %s)\n' % (res.getErrorMessage() if res else 'null'))
                except Exception as e:
                    fout.write('  (反编译异常: %s)\n' % e)
            # 该地址附近 20 条指令
            fout.write('  ---- 附近 20 条指令 ----\n')
            a = addr
            for _ in range(20):
                ins = prog.getListing().getInstructionAt(a)
                fout.write('    %s  %s\n' % (a, ins.toString() if ins else '(无语义)'))
                a = a.add(4)
            fout.write('\n')
        dec.dispose()
    finally:
        proj.closeProgram(prog, True)
finally:
    proj.close()
fout.close()
print('OK -> %s' % OUT)
