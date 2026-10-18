import hashlib,os,glob
def sh(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
menu=sh(r'work\builds\GR_FA2400_K2\temp\dump_final\snap_f00004500.png')
for tag,d in (('mc0_12k',r'work\builds\GR_REBUILD\temp\dump_mc0_12k'),):
    fs=sorted(glob.glob(os.path.join(d,'snap_*.png')))
    hit=[os.path.basename(f) for f in fs if sh(f)==menu]
    print('%-12s 截图 %d ; 与 K2 中文主菜单截图逐字节相同: %s'%(tag,len(fs),hit or '无'))
