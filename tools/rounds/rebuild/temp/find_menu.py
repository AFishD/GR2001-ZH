import hashlib,os,glob
def sh(p):
    return hashlib.sha256(open(p,'rb').read()).hexdigest()
menu=sh(r'work\builds\GR_FA2400_K2\temp\dump_final\snap_f00004500.png')
print('K2 中文主菜单截图 sha=%s'%menu[:16])
for tag,d in (('OURS',r'work\builds\GR_REBUILD\temp\dump_final'),
              ('HASHR_k2_base',r'work\builds\GR_HASHR\runs\k2_base'),
              ('HASHR2400',r'work\builds\GR_HASHR\runs\hashr2400'),
              ('K2_own_run',r'work\builds\GR_FA2400_K2\temp\dump_final')):
    fs=sorted(glob.glob(os.path.join(d,'snap_*.png')))
    hit=[os.path.basename(f) for f in fs if sh(f)==menu]
    # 也找包含中文底栏的近似：统计每张 png 的字节大小分布
    print('%-14s 截图 %d ; 与主菜单截图逐字节相同: %s'%(tag,len(fs),hit or '无'))
