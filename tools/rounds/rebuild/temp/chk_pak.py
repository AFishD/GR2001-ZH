import os,sys,struct,json
sys.path.insert(0, os.path.abspath(r'tools\re\toolbelt'))
sys.path.insert(0, os.path.abspath(r'tools\text_csv'))
import tcslib as T, zx_lib
DUMP=os.path.join(os.environ['LOCALAPPDATA'],'PCSX2','cdvd-dump','GR_FA2400_K2 (2026-10-17 15-08-20).dump')
n=os.path.getsize(DUMP); cnt,rem=divmod(n-16,2052); assert rem==0
idx={}
with open(DUMP,'rb') as f:
    for i in range(cnt):
        f.seek(16+i*2052); idx[struct.unpack('<I',f.read(4))[0]]=16+i*2052+4
print('dump sectors',len(idx))
iso = T.Iso(r'work\builds\GR_REBUILD\_probe_k2only.iso')
ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
e=[x for x in ent if x['name']=='COMMON.PAK'][0]
print('K2 COMMON.PAK iso_off=0x%X stored=%d -> LBA %d..%d'%(e['iso_off'],e['stored'],e['iso_off']//2048,(e['iso_off']+e['stored']-1)//2048))
l0,l1=e['iso_off']//2048,(e['iso_off']+e['stored']-1)//2048
miss=[l for l in range(l0,l1+1) if l not in idx]
print('  K2-dump missing sectors:',len(miss), miss[:20])
ef=[x for x in ent if x['name']=='FONT.RES'][0]
l0,l1=ef['iso_off']//2048,(ef['iso_off']+ef['stored']-1)//2048
print('K2 FONT.RES iso_off=0x%X stored=%d LBA %d..%d miss=%s'%(ef['iso_off'],ef['stored'],l0,l1,[l for l in range(l0,l1+1) if l not in idx]))
pak=bytes(iso.read(e['iso_off'],e['stored']))
recs=T.parse_pak_records(pak)
for r in recs: print('  rec %-20s o0=%d o1=%d o2=%d stored=%d off=%d'%r[:6])
iso.close()
