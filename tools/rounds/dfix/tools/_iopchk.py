import os
def diff(a,b):
    n=0; offs=[]
    off=0
    with open(a,'rb') as fa, open(b,'rb') as fb:
        while True:
            x=fa.read(1<<20); y=fb.read(1<<20)
            if not x and not y: break
            if x!=y:
                for i in range(min(len(x),len(y))):
                    if x[i]!=y[i]:
                        n+=1
                        if len(offs)<10: offs.append(off+i)
            off+=len(x)
    return n, offs
pairs = [
 ('newfontrevisedrs_f00000260_iopram.bin', 'base vs dump_final (SAME ISO)'),
 ('weaponsanditems_f00000390_iopram.bin',  'base vs dump_final (SAME ISO)'),
 ('newfontrevisedrs_f00000260_iopram.bin', 'base vs DFIX_pkt'),
]
A = r'work\builds\GR_DFIX\runs\base'
B = r'work\builds\GR_REBUILD\temp\dump_final'
C = r'work\builds\GR_DFIX\runs\DFIX_pkt'
for f,label in pairs:
    b = C if 'DFIX_pkt' in label else B
    p1, p2 = os.path.join(A,f), os.path.join(b,f)
    if os.path.exists(p1) and os.path.exists(p2):
        n,offs = diff(p1,p2)
        print('%-34s %-32s diff=%d %s' % (f, label, n, ['0x%X'%o for o in offs]))
    else:
        print(f, label, 'missing', os.path.exists(p1), os.path.exists(p2))
