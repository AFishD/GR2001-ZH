import sys, struct
sys.path.insert(0, r"tools\rounds\oomfix\tools")
from oomfix_cave import read_elf, Elf, decode_target
data, lba, size = read_elf(r"work\builds\GR_REBUILD\GR_REBUILD2400.iso")
e = Elf(data)
seg = e.loads[0]; lo, hi = seg['va'], seg['va']+seg['filesz']
for (a,b,tag) in [(0x565A48,0x56D7F0,'R_C'), (0x5637F4,0x565672,'R_B'), (0x561DD0,0x5637F0,'R_A')]:
    refs=[]
    for va in range(lo, hi-4, 4):
        w = e.word(va)
        t = decode_target(va, w)
        if t is not None and a <= t < b:
            refs.append((va, t, w))
    print("== %s 0x%08X..0x%08X : ctrl refs=%d" % (tag,a,b,len(refs)))
    for (va,t,w) in refs[:70]:
        print("    from 0x%08X -> 0x%08X  word=0x%08X" % (va,t,w))
