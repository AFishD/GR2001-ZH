import os,sys,hashlib
sys.path.insert(0, os.path.abspath(r'tools\re\toolbelt')); sys.path.insert(0, os.path.abspath(r'tools\text_csv'))
import tcslib as T, zx_lib
ORIG=r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"
K2=r'work\builds\GR_REBUILD\_probe_k2only.iso'
def blob(iso,lba,name):
    e=[x for x in zx_lib.entries(iso,lba) if x['name']==name][0]
    slot=bytes(iso.read(e['iso_off'],e['stored']))
    return e, b''.join(s[0] for s in T.lzo_subs(slot))
o=T.Iso(ORIG); k=T.Iso(K2)
em,bm_en=blob(o,zx_lib.MENU_LBA,'EN_STRINGS.RES')
_,bm_k2=blob(k,zx_lib.MENU_LBA,'EN_STRINGS.RES')
eg,bg_en=blob(o,zx_lib.GR_LBA,'EN_STRINGS.RES')
_,bg_k2=blob(k,zx_lib.GR_LBA,'EN_STRINGS.RES')
print('MENU en len=%d k2 len=%d same=%s'%(len(bm_en),len(bm_k2),bm_en==bm_k2))
print('GR   en len=%d k2 len=%d same=%s'%(len(bg_en),len(bg_k2),bg_en==bg_k2))
def head(t,b): print('%s head64: %s'%(t,b[:64].hex()))
head('M_EN',bm_en); head('M_K2',bm_k2); head('G_EN',bg_en)
# 相同字节比例
def sim(a,b):
    n=min(len(a),len(b)); same=sum(1 for i in range(n) if a[i]==b[i])
    return same,n
print('MENU_EN vs GR_EN 相同字节 %d/%d'%sim(bm_en,bg_en))
print('MENU_K2 vs MENU_EN 相同字节 %d/%d'%sim(bm_k2,bm_en))
# 找最长公共子串的粗略代理: 5-gram 集合重合度
def grams(b,k=8): return {b[i:i+k] for i in range(0,len(b)-k)}
gm_en=grams(bm_en); gg_en=grams(bg_en); gm_k2=grams(bm_k2)
print('M_EN 8gram %d ; G_EN 8gram %d ; 交集 %d (%.1f%% of G)'%(len(gm_en),len(gg_en),len(gm_en&gg_en),100.0*len(gm_en&gg_en)/len(gg_en)))
print('M_EN 8gram vs M_K2 交集 %d (%.1f%% of M_K2)'%(len(gm_en&gm_k2),100.0*len(gm_en&gm_k2)/len(gm_k2)))
# 解析帧
import struct
for t,b in (('M_EN',bm_en),('M_K2',bm_k2),('G_EN',bg_en)):
    a,c,d=struct.unpack_from('<III',b,0)
    print('%s header: %d %d %d'%(t,a,c,d))
o.close(); k.close()
