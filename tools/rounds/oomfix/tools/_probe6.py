# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0, r"tools\rounds\oomfix\tools")
sys.path.insert(0, r"tools\re\toolbelt")
from oomfix_cave import read_elf, Elf, func_ranges, decode_target
from cave_dis import dis

data, lba, size = read_elf(r"work\builds\GR_REBUILD\GR_REBUILD2400.iso")
e = Elf(data)
seg = e.loads[0]; tlo, thi = seg['va'], seg['va']+seg['filesz']
fr = func_ranges(e)
LO, HI = 0x54FF00, 0x550200
print("--- lui+addiu/ori 合成到 0x%08X..0x%08X 的站点 ---" % (LO,HI))
lui = {}
hits=0
for (a,b) in fr:
    for va in range(a, min(b, thi)-4, 4):
        w = e.word(va); op=(w>>26)&0x3F; rs=(w>>21)&0x1F; rt=(w>>16)&0x1F
        if op==0x0F: lui[rt]=(va, w & 0xFFFF)
        elif op in (0x09,0x0D) and rs in lui:
            lva,hi16 = lui[rs]
            if va-lva>0x40: continue
            imm=w&0xFFFF
            if op==0x09:
                s=imm-0x10000 if imm&0x8000 else imm
                addr=((hi16<<16)+s)&0xFFFFFFFF
            else:
                addr=((hi16<<16)|imm)&0xFFFFFFFF
            if LO<=addr<HI:
                hits+=1
                if hits<=40:
                    print("   lui@0x%08X use@0x%08X -> 0x%08X   %s" % (lva,va,addr,dis(e.word(va),va)))
print("   total=%d" % hits)
print()
print("--- 全 .text（FUNC 覆盖）里控制转移到 0x550040..0x5500C0 的站点 ---")
n=0
for (a,b) in fr:
    for va in range(a, min(b, thi)-4, 4):
        w=e.word(va); t=decode_target(va,w)
        if t is not None and 0x550040 <= t < 0x5500C0:
            n+=1
            if n<=40: print("   0x%08X -> 0x%08X  %s" % (va,t,dis(w,va)))
print("   total=%d" % n)
print()
print("--- 0x5DEC00..0x5DED00 区域符号与重定位站点 ---")
for s in e.syms():
    if 0x5DEC00 <= s['val'] < 0x5DED40:
        print("   sym 0x%08X size=%-4d %s" % (s['val'], s['size'], s['name']))
