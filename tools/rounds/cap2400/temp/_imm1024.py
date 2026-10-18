import os,sys
sys.path.insert(0, r'tools\re\toolbelt'); sys.path.insert(0, r'tools\text_csv')
import cave_dis
elf = cave_dis.Elf(r'work\builds\GR_CAP2400\temp\GR_ZH124_SLUS_206.13.elf')
for (wl,lo,hi) in [('RSFont',0x219A70,0x21D948),('caveA',0x416E00,0x417600),('caveB',0x565600,0x565A50),('loader',0x51B660,0x51E000)]:
    for va in range(lo,hi-4,4):
        w=elf.word(va); op=(w>>26)&0x3F
        if op in (0x08,0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F) and (w&0xFFFF)==1024:
            print('%s 0x%08X ISO 0x%08X %08X %s' % (wl,va,va-0x6C780,w,cave_dis.dis(w,va)))
