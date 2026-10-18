import sys
sys.path.insert(0, r"tools\rounds\oomfix\tools")
from oomfix_cave import read_elf, Elf
data, lba, size = read_elf(r"work\builds\GR_REBUILD\GR_REBUILD2400.iso")
e = Elf(data)
seg = e.loads[0]
blob = data[seg['off']:seg['off']+seg['filesz']]
runs=[]; i=0; n=len(blob)
while i<n:
    if blob[i]==0:
        j=i
        while j<n and blob[j]==0: j+=1
        if j-i>=0x30: runs.append((seg['va']+i, seg['va']+j))
        i=j
    else: i+=1
print("runs >= 0x30 :", len(runs))
for lo,hi in sorted(runs):
    print("  0x%08X..0x%08X  %6d B" % (lo,hi,hi-lo))
