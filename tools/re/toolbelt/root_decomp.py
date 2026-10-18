# -*- coding: utf-8 -*-
r"""root_decomp.py -- PyGhidra 反编译指定 VA 所在函数（复用已有分析好的工程，不重跑分析）

环境重定向与 pygh_decomp.py 一致（必须在 import pyghidra 之前）。

用法:
  python tools/re/toolbelt/root_decomp.py 0x51C810 0x51D910 0x5176E0 ...
输出: stdout（同时写 work/tools/ghidra_out/root_decomp.txt）
"""
import io
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TOOLS = os.path.join(REPO, 'work', 'tools')

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

PROJ_DIR = os.path.join(TOOLS, 'ghidra_proj')
PROJ_NAME = 'GRLoc'
OUT = os.path.join(TOOLS, 'ghidra_out', 'root_decomp.txt')

VAS = [int(x, 16) for x in sys.argv[1:]] or [0x51C810, 0x51D910]

import pyghidra  # noqa: E402
from pyghidra.launcher import HeadlessPyGhidraLauncher  # noqa: E402

_l = HeadlessPyGhidraLauncher()
_l.start()

from ghidra.base.project import GhidraProject                      # noqa: E402
from ghidra.app.decompiler import DecompInterface                  # noqa: E402
from ghidra.util.task import ConsoleTaskMonitor                    # noqa: E402

os.makedirs(os.path.dirname(OUT), exist_ok=True)
fout = io.open(OUT, 'w', encoding='utf-8')


def W(s=''):
    print(s)
    fout.write(s + '\n')
    fout.flush()


proj = GhidraProject.openProject(PROJ_DIR, PROJ_NAME, True)
try:
    prog = proj.openProgram('/', 'SLUS_206.13.elf', True)
    try:
        fm = prog.getFunctionManager()
        dec = DecompInterface()
        dec.openProgram(prog)
        mon = ConsoleTaskMonitor()
        af = prog.getAddressFactory()
        done = set()
        for va in VAS:
            addr = af.getDefaultAddressSpace().getAddress(va)
            f = fm.getFunctionContaining(addr)
            W('=' * 78)
            if f is None:
                W('VA 0x%08X  不在任何函数内' % va)
                continue
            ent = f.getEntryPoint().getOffset()
            W('VA 0x%08X -> 函数 %s @0x%08X size=%d' % (va, f.getName(), ent, f.getBody().getNumAddresses()))
            if ent in done:
                W('  (已反编译过)')
                continue
            done.add(ent)
            res = dec.decompileFunction(f, 120, mon)
            if res is not None and res.decompileCompleted():
                W(res.getDecompiledFunction().getC())
            else:
                W('  (反编译失败: %s)' % (res.getErrorMessage() if res else 'null'))
        dec.dispose()
    finally:
        proj.closeProgram(prog, True)
finally:
    proj.close()
fout.close()
print('OK -> %s' % OUT)
