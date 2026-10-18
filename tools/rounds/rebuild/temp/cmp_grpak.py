import os,sys,glob,struct,hashlib
sys.path.insert(0, os.path.abspath(r'tools\re\toolbelt')); sys.path.insert(0, os.path.abspath(r'tools\text_csv'))
import tcslib as T, zx_lib
SEC=2048
DD=os.path.join(os.environ['LOCALAPPDATA'],'PCSX2','cdvd-dump')
def idx_of(p):
    n=os.path.getsize(p); cnt,rem=divmod(n-16,2052)
    if rem: return None
    d={}
    with open(p,'rb') as f:
        for i in range(cnt):
            f.seek(16+i*2052); d[struct.unpack('<I',f.read(4))[0]]=16+i*2052+4
    return d
o=T.Iso(r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso")
e_g=[x for x in zx_lib.entries(o,zx_lib.GR_LBA) if x['name']=='COMMON.PAK'][0]
e_m=[x for x in zx_lib.entries(o,zx_lib.MENU_LBA) if x['name']=='COMMON.PAK'][0]
goff,gsz=e_g['iso_off'],e_g['stored']; moff,msz=e_m['iso_off'],e_m['stored']
def read_at(path,idx,off,size):
    l0=off//SEC; l1=(off+size-1)//SEC; buf=bytearray()
    with open(path,'rb') as f:
        for l in range(l0,l1+1):
            if l not in idx: return None
            f.seek(idx[l]); buf+=f.read(SEC)
    a=off-l0*SEC; return bytes(buf[a:a+size])
k2p=[d for d in glob.glob(os.path.join(DD,'*.dump')) if 'GR_FA2400_K2' in os.path.basename(d)][0]
ki=idx_of(k2p)
# 连续可读前缀
head=None
for n in range(1,12):
    b=read_at(k2p,ki,goff,n*SEC)
    if b is None: break
    head=b
print('K2 GR#3451 可读连续前缀 = %d B'%len(head))
print('  前32B:',head[:32].hex())
print('  parse_pak_records:',[(r[0],r[1],r[2],r[3],r[5]) for r in T.parse_pak_records(head)])
best=[]
for d in sorted(glob.glob(os.path.join(DD,'*.dump'))):
    nm=os.path.basename(d)
    if 'GR_FA2400_K2' in nm: continue
    di=idx_of(d)
    if not di: continue
    pak=read_at(d,di,moff,msz)
    if pak is None: continue
    r=[x for x in T.parse_pak_records(pak) if x[0]=='new_font_revised']
    if not r: continue
    r=r[0]
    n=len(head); same=sum(1 for i in range(n) if pak[i]==head[i])
    # 只比头部（PAK 记录表 + new_font_revised 头 + 像素开头）
    best.append((same,n,nm,(r[1],r[2],r[3],r[5]),hashlib.sha256(pak).hexdigest()[:16]))
best.sort(reverse=True)
print()
print('候选（按与 K2 真字节相同数排序）:')
for s,n,nm,hdr,h in best:
    print('   %-52s psm/w/h/stored=%-24s same %6d/%d (%.2f%%) sha=%s'%(nm[:52],hdr,s,n,100.0*s/n,h))
o.close()
