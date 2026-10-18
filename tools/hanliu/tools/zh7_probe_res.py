# [hanliu 收编] 原件: C:/gr_build/tmp/zh7_probe_res.py (逐字复制 (RES 重编码探针, 顶层执行))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, json, sys
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'work', 'tmp'))
from lz77_decode import lzo1x_decompress
from lzo1x_c import compress as lzo_compress
ZH_DIR = os.path.join(REPO_ROOT, 'work', 'tmp', 'zh6')
V3 = os.path.join(REPO_ROOT, 'work', 'tmp', 'en_strings_zh_8sub_v3.bin')
REAL = 128545
CHUNKS = [16384] * 7 + [13857]
cs = json.load(open(ZH_DIR + r'\charset_zh6.json', encoding='utf-8'))
codes89 = cs['codes']
sel = json.load(open(os.path.join(REPO_ROOT, 'work', 'tmp', 'zh7_sel.json'), encoding='utf-8'))
dbcs = sel['dbcs_ordered']; entries = sel['entries']
pair_of = {}
for k, ch in enumerate(dbcs):
    pair_of[ch] = (0xA1 + k // 94, 0xA1 + k % 94)
def encode(text):
    out = bytearray()
    for ch in text:
        if ch in codes89:
            out.append(codes89[ch])
        elif ch in pair_of:
            l, t = pair_of[ch]
            out += bytes((l, t))
        else:
            o = ord(ch)
            assert 0x20 <= o < 0x7F, (repr(ch), text)
            out.append(o)
    return bytes(out)
def decode_blob(fr):
    p, out = 0, []
    while p + 8 <= len(fr):
        plen, o = struct.unpack_from('<II', fr, p)
        dec, err, _ = lzo1x_decompress(fr[p+8:p+8+plen], out_size=o)
        assert err is None and len(dec) == o
        out.append(dec)
        p += 8 + plen
    return b''.join(out)
def walk(data):
    p = 0
    ng = struct.unpack_from('<I', data, p)[0]
    p += 4
    groups = []
    for g in range(ng):
        if g > 0:
            p += 4
        cnt = struct.unpack_from('<I', data, p)[0]
        p += 4
        st = []
        for i in range(cnt):
            ln = struct.unpack_from('<I', data, p)[0]
            p += 4
            st.append(bytearray(data[p:p+ln]))
            p += ln + 2
        groups.append(st)
    return groups
def serialize(groups, total):
    out = bytearray()
    out += struct.pack('<I', len(groups))
    for gi, st in enumerate(groups):
        if gi:
            out += struct.pack('<I', 0)
        out += struct.pack('<I', len(st))
        for s in st:
            out += struct.pack('<I', len(s)) + bytes(s) + b'\x00\x00'
    out += b'\x00' * 8
    assert len(out) <= total
    out += b'\x00' * (total - len(out))
    return bytes(out)
cont = decode_blob(open(V3, 'rb').read())
groups = walk(cont)
n = 0
for c in entries:
    g = int(c['key'][1:c['key'].index('.')]) - 1
    i = int(c['key'][c['key'].index('.I') + 2:])
    groups[g][i] = encode(c['zh'])
    n += 1
cont2 = serialize(groups, REAL)
pos, blob = 0, b''
for csz in CHUNKS:
    chunk = cont2[pos:pos+csz]
    payload = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
    blob += struct.pack('<II', len(payload), csz) + payload
    pos += csz
print('entries=%d blob=%dB (limit 47570, margin %d)' % (n, len(blob), 47570 - len(blob)))
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'zh7_blob_probe.bin'), 'wb').write(blob)
