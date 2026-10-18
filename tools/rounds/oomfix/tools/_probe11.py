import sys, os, struct, ctypes, zipfile
sys.path.insert(0, r"tools\rounds\oomfix\tools")
import oomfix_zstd as Z

lib = ctypes.CDLL(Z.ZSTD_DLL)
lib.ZSTD_getErrorName.restype = ctypes.c_char_p
lib.ZSTD_getErrorName.argtypes = [ctypes.c_size_t]

inp = r"work\builds\GR_OOMFIX\common\state_LAY_fix1_bytecount.p2s"
out = r"work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s"
print("out exists:", os.path.exists(out), os.path.getsize(out) if os.path.exists(out) else 0)
for p in (inp, out):
    print("==", p)
    try:
        ents = Z.zip_entries(p)
    except Exception as e:
        print("   zip_entries failed:", e); continue
    for e in ents[:4]:
        raw, nm = Z.read_raw(p, e)
        print("   %-30s flag=0x%X local_csize=%d cd_csize=%d payload[:8]=%s" % (nm, e.get('flag',-1), e.get('local_csize',-1), e['csize'], raw[:8].hex()))
        if e['method'] == 93:
            buf = ctypes.create_string_buffer(e['usize'])
            n = lib.ZSTD_decompress(buf, e['usize'], raw, len(raw))
            if lib.ZSTD_isError(n):
                print("        zstd err %d %s" % (n, lib.ZSTD_getErrorName(n)))
            else:
                print("        ok %d bytes, first8=%s" % (n, buf.raw[:8].hex()))
