import glob, os
def firstdiff(a,b):
    n=0; first=None
    with open(a,'rb') as fa, open(b,'rb') as fb:
        off=0
        while True:
            x=fa.read(1<<20); y=fb.read(1<<20)
            if not x: break
            if x!=y:
                for i in range(min(len(x),len(y))):
                    if x[i]!=y[i]:
                        n+=1
                        if first is None: first=off+i
            off+=len(x)
    return n, first
pairs = [
 (r'work\builds\GR_DFIX\runs\base\newfontrevisedrs_f00000260_eeram.bin',
  r'work\builds\GR_REBUILD\temp\dump_final\newfontrevisedrs_f00000260_eeram.bin','base vs rebuild dump_final (same ISO!)'),
 (r'work\builds\GR_DFIX\runs\base\newfontrevisedrs_f00000260_eeram.bin',
  r'work\builds\GR_DFIX\runs\DFIX_fp\newfontrevisedrs_f00000260_eeram.bin','base vs DFIX_fp'),
 (r'work\builds\GR_DFIX\runs\base\WPNRPK74_f00000144_eeram.bin',
  r'work\builds\GR_DFIX\runs\DFIX_pkt\WPNRPK74_f00000144_eeram.bin','base vs DFIX_pkt (frame144)'),
]
for a,b,label in pairs:
    if os.path.exists(a) and os.path.exists(b):
        n,first = firstdiff(a,b)
        print('%-46s differing_bytes=%d first_off=0x%X' % (label, n, first if first else 0))
    else:
        print(label, 'missing', os.path.exists(a), os.path.exists(b))
