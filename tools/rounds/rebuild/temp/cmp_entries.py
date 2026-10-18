import os,sys
sys.path.insert(0, os.path.abspath(r'tools\re\toolbelt')); sys.path.insert(0, os.path.abspath(r'tools\text_csv'))
import tcslib as T, zx_lib
A=r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"
B=r'work\builds\GR_REBUILD\GR_REBUILD2400.iso'
a=T.Iso(A); b=T.Iso(B)
for lba,tag in ((zx_lib.MENU_LBA,'MENU'),(zx_lib.GR_LBA,'GR')):
    ea=zx_lib.entries(a,lba); eb=zx_lib.entries(b,lba)
    print('==== %s : 原盘 %d 条 / 成品 %d 条'%(tag,len(ea),len(eb)))
    n=0
    for x,y in zip(ea,eb):
        if x['name']!=y['name']:
            print('   !! 名字序列在 #%d 起不同: %r vs %r'%(x['idx'],x['name'],y['name'])); break
        if (x['off'],x['stored'],x['real'])!=(y['off'],y['stored'],y['real']):
            n+=1
            print('   #%-5d %-26s off 0x%08X→0x%08X  stored %d→%d  real %d→%d'%(
                x['idx'], x['name'], x['off'], y['off'], x['stored'], y['stored'], x['real'], y['real']))
    print('   ---- 条目字段有差异的条数 = %d'%n)
a.close(); b.close()
