import os,sys
sys.path.insert(0, os.path.abspath(r'tools\re\toolbelt')); sys.path.insert(0, os.path.abspath(r'tools\text_csv'))
import tcslib as T, zx_lib
B=r'work\builds\GR_REBUILD\GR_REBUILD2400.iso'
b=T.Iso(B)
base=zx_lib.MENU_LBA*2048
ent=zx_lib.entries(b,zx_lib.MENU_LBA)
print('MENU base iso=0x%X (LBA %d)'%(base,zx_lib.MENU_LBA))
for lba in (779690,779697,779698,779699):
    off=lba*2048
    hits=[e for e in ent if e['iso_off']<=off<e['iso_off']+e['stored']]
    print('LBA %d (iso 0x%X, MENU+0x%X): %s'%(lba,off,off-base,
        [ '#%d %s +%d'%(e['idx'],e['name'],off-e['iso_off']) for e in hits] or ['<空隙>']))
# 最后一个 cdvd 事件之后 K2 跑里发生了什么
b.close()
