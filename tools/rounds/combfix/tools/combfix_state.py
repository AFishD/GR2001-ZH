# -*- coding: utf-8 -*-
r"""combfix_state.py —— 【GR_COMBFIX】造本轮的现场存档：把「64KB 请求自己的桶」也毒化。

为什么这样做
------------
本轮新卡死的指令级病灶 = malloc 的「请自己的桶」快路径（0x10216C → 0x102180 → 0x1021D0
→ 0x1021D4，无校验）。这条路径只有请求的 nb 落在**该桶的尺寸区间**时才会被走到：
  nb = 0x10020（64KB 级）→ idx = (nb>>15)+119 = **121**（dispatch：0x102130/0x102134/0x102140）
  nb = 0x80010（512KB 级）→ idx = **126**（0x102144/0x102148）
SPINFIX 的 S1 只毒化了桶 126，本机 L1 场景的请求（nb=0x10020）落在桶 121，
⇒ 本机原来看不到 own-bin 自旋。本脚本在 S1 的基础上**再毒化桶 121**，
让「同一条指令链」在本机可复现（用户真机是 512KB 请求直接落在桶 126）。

变体（单变量）：
  S1b_bin121_bad      : S1（桶126=用户坏值）+ 桶121 fd/bk = 0x6ED47823
  S1b_bin121_0xA73D   : 同上，但用存档自带的 0xA73D37F0（KSEG1 别名型，不 TLB Miss）
额外记录：0x0..0x40 的低端 RAM 内容（决定「v0 归 0 之后」本机是否也自旋）。

READ-ONLY 打开输入存档；只写 --outdir。
"""
import argparse
import hashlib
import os
import struct
import sys

ROOT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(ROOT, 'tools', 'rounds', 'spinfix', 'tools'))
import importlib.util
_s = importlib.util.spec_from_file_location(
    'sf_common', os.path.join(ROOT, 'work', 'builds', 'GR_SPINFIX', 'tools', 'sf_common.py'))
C = importlib.util.module_from_spec(_s)
sys.modules['sf_common'] = C
_s.loader.exec_module(C)

ENTRY = 'eeMemory.bin'
BIN126_FD, BIN126_BK = 0x0055BB98, 0x0055BB9C
BIN121_FD, BIN121_BK = 0x0055BB70, 0x0055BB74      # 0x55B7A8 + 8*121 / +4
BAD_USER = 0x6ED47823
BAD_SAVE = 0xA73D37F0


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', default=os.path.join(ROOT, r'work\builds\GR_SPINFIX\states\S1_bin126_user.p2s'))
    ap.add_argument('--outdir', default=os.path.join(ROOT, r'work\builds\GR_COMBFIX\states'))
    a = ap.parse_args()
    z = C.load_zstd_tool()
    ram0 = z.decompress_entry(a.state, ENTRY)
    assert len(ram0) == 32 << 20
    os.makedirs(a.outdir, exist_ok=True)
    rep = dict(tool=r'work\builds\GR_COMBFIX\tools\combfix_state.py', src=a.state,
               src_sha256=C.sha256_file(a.state), variants=[])

    def dump_low(ram, n=0x40):
        return ram[0:n].hex()

    for tag, bad, low0 in (('S1b_bin121_bad', BAD_USER, False),
                           ('S1b_bin121_0xA73D', BAD_SAVE, False),
                           ('S1b_bin121_low0', BAD_USER, True)):
        ram = bytearray(ram0)
        struct.pack_into('<II', ram, BIN121_FD, bad, bad)
        if low0:
            # 复现用户真机「低端 0x8 / 0x14 未映射 ⇒ 读回 0」这一条件：
            # 本机 gsrunner 里低端页是**映射**的（SPINFIX §7 未达成项 1），
            # 不把这些字节清零，`ld v1,8(0)` 会读到低端 RAM 的 0x07EA090E0F2B1F00
            # ⇒ size=0x0F2B1F00 远大于 nb ⇒ 循环从 0x102198 直接跳出去、**看不到自旋**。
            for off in range(0x8, 0x10):
                ram[off] = 0
            for off in range(0x14, 0x18):
                ram[off] = 0
        out = os.path.join(a.outdir, tag + '.p2s')
        z.rewrite(a.state, out, ENTRY, bytes(ram))
        chk = z.decompress_entry(out, ENTRY)
        fd1, bk1 = struct.unpack_from('<II', chk, BIN126_FD)
        fd2, bk2 = struct.unpack_from('<II', chk, BIN121_FD)
        diffs = [i for i in range(len(chk)) if chk[i] != ram0[i]]
        d = dict(tag=tag, path=out, bytes=os.path.getsize(out), sha256=C.sha256_file(out),
                 bad_value='0x%08X' % bad,
                 bin126_readback=['0x%08X' % fd1, '0x%08X' % bk1],
                 bin121_readback=['0x%08X' % fd2, '0x%08X' % bk2],
                 diff_bytes_vs_S1=len(diffs),
                 low_ram_0x00_0x40=dump_low(chk),
                 low_ram_0x00_0x20_be32=[struct.unpack_from('<I', chk, o)[0] for o in range(0, 0x20, 4)],
                 size32mb_ok=(len(chk) == 32 << 20))
        assert d['size32mb_ok'] and 8 <= d['diff_bytes_vs_S1'] <= (8 + 12 if low0 else 8)
        rep['variants'].append(d)
        print('%-20s %s  %d B sha256=%s' % (tag, os.path.basename(out), d['bytes'], d['sha256']))
        print('    bin126=%s bin121=%s diff_vs_S1=%d B' % (d['bin126_readback'], d['bin121_readback'], len(diffs)))
        print('    low RAM 0x00..0x20 (u32): %s' % ['0x%08X' % v for v in d['low_ram_0x00_0x20_be32']])
    rep['s1_bin126'] = ['0x%08X' % v for v in struct.unpack_from('<II', ram0, BIN126_FD)]
    rep['low_ram_S1'] = dump_low(ram0)
    mp = os.path.join(a.outdir, 'combfix_states.meta.json')
    with open(mp, 'w', encoding='utf-8', newline='\n') as f:
        import json
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print('[meta] %s' % mp)
    return 0


if __name__ == '__main__':
    sys.exit(main())
