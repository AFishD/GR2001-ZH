import os,sys,struct
sys.path.insert(0, os.path.abspath(r'tools\re\toolbelt'))
sys.path.insert(0, os.path.abspath(r'tools\text_csv'))
import tcslib as T, zx_lib
for tag,iso in (('ORIG', r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"),
                ('K2PROBE', r'work\builds\GR_REBUILD\_probe_k2only.iso')):
    i = T.Iso(iso)
    ent = zx_lib.entries(i, zx_lib.MENU_LBA)
    print('==== %s : MENU 条目 %d' % (tag, len(ent)))
    want = ('COMMON.PAK','FONT.RES','MENU.PAK','LOADING.PAK','EN_STRINGS.RES','EN_SPECIAL_FEATURE.XML')
    for e in ent:
        if e['name'] in want:
            print('   %-4d %-26s off=0x%08X stored=%-9d real=%-9d iso=0x%08X..0x%08X' % (
                e['idx'], e['name'], e['off'], e['stored'], e['real'], e['iso_off'], e['iso_off']+e['stored']))
    i.close()
