import os,sys,hashlib
sys.path.insert(0, os.path.abspath(r'tools\re\toolbelt')); sys.path.insert(0, os.path.abspath(r'tools\text_csv'))
import tcslib as T
base=r'docs\han_v2'
for nm in ('artifacts/COMMON_PAK.bin','COMMON_PAK_ZH3.bin','COMMON_PAK_ZH4.bin','COMMON_PAK_ZH5.bin','COMMON_PAK_ZH6.bin','COMMON_PAK_ZH12.bin','COMMON_PAK_pairs.bin','COMMON_PAK_pairs_expanded.bin'):
    p=os.path.join(base,nm.replace('/',os.sep))
    b=open(p,'rb').read()
    print('%-36s %d'%(nm,len(b)))
    for r in T.parse_pak_records(b):
        print('     %-20s o0=%-3d o1=%-5d o2=%-5d o3=%-5d stored=%-7d off=%-7d'%(r[0],r[1],r[2],r[3],r[4],r[5],r[6]))
