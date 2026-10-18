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
def read_at(path,idx,off,size):
    l0=off//SEC; l1=(off+size-1)//SEC; buf=bytearray()
    with open(path,'rb') as f:
        for l in range(l0,l1+1):
            if l not in idx: return None
            f.seek(idx[l]); buf+=f.read(SEC)
    a=off-l0*SEC; return bytes(buf[a:a+size])
o=T.Iso(r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso")
e_g=[x for x in zx_lib.entries(o,zx_lib.GR_LBA) if x['name']=='COMMON.PAK'][0]
e_m=[x for x in zx_lib.entries(o,zx_lib.MENU_LBA) if x['name']=='COMMON.PAK'][0]
goff,gsz=e_g['iso_off'],e_g['stored']; moff,msz=e_m['iso_off'],e_m['stored']
k2p=[d for d in glob.glob(os.path.join(DD,'*.dump')) if 'GR_FA2400_K2' in os.path.basename(d)][0]
ki=idx_of(k2p)
head=None
for n in range(1,12):
    b=read_at(k2p,ki,goff,n*SEC)
    if b is None: break
    head=b
print('K2 GR#3451 真字节前缀 = %d B'%len(head))
candp=[d for d in glob.glob(os.path.join(DD,'*.dump')) if 'GR_ZH113b (2026-10-15 19-39-44)' in os.path.basename(d)][0]
ci=idx_of(candp)
cand=read_at(candp,ci,moff,msz)
print('候选 ZH113b MENU#3 sha=%s size=%d'%(hashlib.sha256(cand).hexdigest()[:16],len(cand)))
for lo,hi,lab in ((0,200,'PAK头+记录表'),(0,5229,'头+arrow+atlas头'),(0,16384,'K2 真字节全长'),(5229,16384,'atlas 像素开头')):
    n=min(hi,len(head)); same=sum(1 for i in range(lo,n) if cand[i]==head[i])
    print('  [%s] %d..%d : %d/%d = %.2f%%'%(lab,lo,n,same,n-lo,100.0*same/(n-lo)))
# 逐 512B 块
print('  逐 1KB 块相同率:')
for s in range(0,len(head),1024):
    e=min(s+1024,len(head)); same=sum(1 for i in range(s,e) if cand[i]==head[i])
    print('     %6d  %5.1f%%'%(s,100.0*same/(e-s)))
o.close()
