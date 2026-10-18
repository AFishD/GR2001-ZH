import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work/builds/GR_EN_ORIG/GR_EN_ORIG.iso')
NEEDLES = [b'determine ranges out to approximately', b'accuracy of', b'+ or -', b'or -',
           b'approximately 10,000 meters', b'10,000 meters']
CHUNK = 1 << 22; OVER = 128
hits = {n: [] for n in NEEDLES}
pos = 0; tail = b''
with open(ISO, 'rb') as f:
    while True:
        buf = f.read(CHUNK)
        if not buf: break
        blob = tail + buf; base = pos - len(tail)
        for n in NEEDLES:
            st = 0
            while True:
                i = blob.find(n, st)
                if i < 0: break
                hits[n].append(base + i); st = i + 1
        tail = blob[-OVER:]; pos += len(buf)
for n in NEEDLES:
    print('%-40r -> %d 处 %s' % (n, len(hits[n]), hits[n][:5]))
if hits[b'determine ranges out to approximately']:
    off = hits[b'determine ranges out to approximately'][0]
    with open(ISO, 'rb') as f:
        f.seek(max(0, off-120)); ctx = f.read(400)
    print('ctx:', repr(ctx.decode('latin-1')))
