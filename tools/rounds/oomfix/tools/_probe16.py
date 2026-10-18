import struct, os, hashlib
p = r"work\builds\GR_OOMFIX\runs\smoke_OOMFIX2400\win_f00005970_eeram.bin"
d = open(p,'rb').read()
print("%s  %d B  sha256=%s" % (os.path.basename(p), len(d), hashlib.sha256(d).hexdigest()))
print("--- 冷启动 6000 帧后，补丁站点在 EE RAM 里的实际内容 ---")
exp = {0x539174:0x08154012, 0x550048:0x10400005, 0x55004C:0x00000000, 0x550050:0xAE620004,
       0x550054:0xAE620008, 0x550058:0x0814E45F, 0x55005C:0x00000000, 0x550060:0xAE600004,
       0x550064:0xAE600008, 0x550068:0x0000802D, 0x55006C:0x0814E4A8, 0x550070:0x00000000}
ok = True
for va,w in sorted(exp.items()):
    got = struct.unpack_from('<I', d, va)[0]
    good = (got == w)
    ok = ok and good
    print("   0x%08X = %08X  期望 %08X  %s" % (va, got, w, 'OK' if good else 'FAIL'))
print("   ⇒ 补丁在冷启动 6000 帧后%s" % ('完好（ISO 装载生效、无人改写）' if ok else '被改写！'))
print("--- 低端内存抽样 ---")
for va in (0x0, 0x80, 0x180, 0x1300, 0x1310):
    print("   0x%08X = %s" % (va, d[va:va+16].hex()))
